from fastapi import APIRouter, HTTPException, Request
from datetime import date
from typing import Dict, Any, List, Optional
from app.database import session_scope
from app.services.schedule_service import ScheduleService
from app.services.bitrix_client import get_bitrix_client
from app.services.update_service import get_today_msk, UpdateService
from app.services.rule_engine import RuleEngine
from app.models import UpdateRule, User, UpdateHistory, UpdateSource
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


@router.post("/bitrix")
async def handle_bitrix_webhook(request: Request):
    """
    Обработчик входящих webhook событий от Bitrix24

    Ожидает события OnCrmDealAdd или OnCrmDealUpdate.
    При получении события обновляет ответственного в сделке на пользователя,
    который стоит в графике дежурств на текущий день.

    Работа с БД разбита на короткие сессии: данные читаются и записываются
    короткоживущими сессиями, а длительные вызовы к Bitrix24 выполняются БЕЗ
    удержания соединения из пула.
    """
    try:
        # Получаем данные из запроса
        # Bitrix24 может отправлять данные как form-data или как JSON
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            data = await request.json()
        else:
            form_data = await request.form()
            # Преобразуем form-data в словарь
            data = dict(form_data)

        # Логируем полученные данные для отладки
        logger.info(f"Получено webhook событие от Bitrix24: {data}")

        # Извлекаем информацию о документе из данных события
        # Формат: document_id[0]='crm', document_id[1]='CCrmDocumentDeal', document_id[2]='DEAL_1'
        document_type = data.get('document_id[1]', '')
        deal_id_str = data.get('document_id[2]', '')

        # Проверяем, что это событие для сделки
        if not document_type.startswith('CCrmDocumentDeal') or not deal_id_str.startswith('DEAL_'):
            logger.warning(f"Событие не относится к сделке: document_type={document_type}, deal_id={deal_id_str}")
            return {"status": "ignored", "reason": "Not a deal event"}

        # Извлекаем ID сделки из строки вида 'DEAL_1'
        try:
            deal_id = int(deal_id_str.replace('DEAL_', ''))
        except ValueError:
            logger.error(f"Не удалось извлечь ID сделки из строки: {deal_id_str}")
            return {"status": "error", "reason": "Invalid deal ID format"}

        # Получаем текущую дату в московском времени
        today = get_today_msk()

        # ======================================================================
        # Фаза 1: чтение из БД короткой сессией (соединение освобождается до HTTP)
        # ======================================================================
        with session_scope() as db:
            schedule_service = ScheduleService(db)
            duty_users: List[User] = schedule_service.get_duty_users_for_date(today)

            if not duty_users:
                logger.info(f"Нет пользователей на дежурстве на дату {today}, пропускаем обновление сделки {deal_id}")
                return {
                    "status": "skipped",
                    "reason": "No duty users for today",
                    "deal_id": deal_id,
                    "date": str(today)
                }

            duty_user_ids = {u.id for u in duty_users}

            # Получаем активные правила обновления для сделок
            rules = db.query(UpdateRule).filter(
                UpdateRule.enabled == True,
                UpdateRule.entity_type == 'deal'
            ).all()

            if not rules:
                logger.info(f"Нет активных правил для сделок, пропускаем обновление сделки {deal_id}")
                return {
                    "status": "skipped",
                    "reason": "No active rules for deals",
                    "deal_id": deal_id,
                    "date": str(today)
                }

            # Проверяем, какие правила применимы (пользователи правила должны быть на дежурстве)
            applicable_rules: List[UpdateRule] = []
            for rule in rules:
                # Обращение к rule.rule_users подгружает связь, пока сессия жива
                rule_user_ids = {ru.user_id for ru in rule.rule_users}
                if rule_user_ids and rule_user_ids.intersection(duty_user_ids):
                    applicable_rules.append(rule)

            if not applicable_rules:
                logger.info(f"Нет применимых правил для сделки {deal_id} (пользователи правил не на дежурстве)")
                return {
                    "status": "skipped",
                    "reason": "No applicable rules (rule users not on duty)",
                    "deal_id": deal_id,
                    "date": str(today)
                }

            # Определяем необходимые поля для правил
            update_service = UpdateService(db)
            required_fields = ['ID', 'ASSIGNED_BY_ID']
            for rule in applicable_rules:
                rule_fields = update_service._get_required_fields_for_rule(rule)
                required_fields.extend([f for f in rule_fields if f not in required_fields])

            # Последний обновленный через webhook ответственный для этой сделки (для ротации)
            last_history = db.query(UpdateHistory).filter(
                UpdateHistory.entity_type == 'deal',
                UpdateHistory.entity_id == deal_id,
                UpdateHistory.update_source == UpdateSource.WEBHOOK
            ).order_by(UpdateHistory.created_at.desc()).first()
            last_assigned_id: Optional[int] = last_history.new_assigned_by_id if last_history else None

            # Отвязываем объекты от сессии, чтобы пользоваться ими после её закрытия
            db.expunge_all()

        # ======================================================================
        # Фаза 2: работа с Bitrix24 БЕЗ удержания соединения из пула
        # ======================================================================
        bitrix_client = get_bitrix_client()
        # Записи истории, которые нужно сохранить в БД в фазе 3
        history_entries: List[Dict[str, Any]] = []

        try:
            # Получаем сделку напрямую через crm.deal.get (для одной сделки это правильнее)
            deal_data = await bitrix_client.get_entity(
                'deal',
                deal_id,
                select=required_fields
            )

            if not deal_data:
                logger.warning(f"Сделка {deal_id} не найдена в Bitrix24")
                return {
                    "status": "error",
                    "reason": "Deal not found",
                    "deal_id": deal_id
                }

            deal = deal_data

            # Применяем правила для проверки, нужно ли обновлять эту сделку
            rule_engine = RuleEngine(applicable_rules)
            filtered_deals = rule_engine.apply_rules([deal])

            if not filtered_deals:
                logger.info(f"Сделка {deal_id} не соответствует правилам фильтрации")
                return {
                    "status": "skipped",
                    "reason": "Deal does not match rule filters",
                    "deal_id": deal_id,
                    "date": str(today)
                }

            # Проверяем, есть ли текущий ответственный в графике дежурств
            current_assigned_str = deal.get('ASSIGNED_BY_ID')
            if current_assigned_str:
                try:
                    current_assigned_id = int(current_assigned_str)
                    if current_assigned_id in duty_user_ids:
                        # Ответственный уже в графике - не обновляем, но записываем в историю
                        rule = applicable_rules[0]
                        history_entries.append({
                            "entity_type": 'deal',
                            "entity_id": deal_id,
                            "old_assigned_by_id": current_assigned_id,
                            "new_assigned_by_id": current_assigned_id,
                            "update_source": UpdateSource.WEBHOOK,
                            "rule_id": rule.id,
                        })
                        _save_history(history_entries)

                        logger.info(
                            f"Сделка {deal_id} уже имеет ответственного {current_assigned_id}, "
                            f"который есть в графике дежурств. Обновление не требуется."
                        )
                        return {
                            "status": "skipped",
                            "reason": "Already assigned to duty user",
                            "deal_id": deal_id,
                            "assigned_user_id": current_assigned_id,
                            "date": str(today)
                        }
                except (ValueError, TypeError):
                    # Если не удалось преобразовать в int, продолжаем обычную логику
                    pass

            # Определяем пользователя для назначения
            # Используем первое применимое правило и дежурных пользователей из этого правила
            rule = applicable_rules[0]
            rule_duty_users = [u for u in duty_users if u.id in {ru.user_id for ru in rule.rule_users}]

            if not rule_duty_users:
                logger.warning(f"Нет дежурных пользователей для правила {rule.id}")
                return {
                    "status": "error",
                    "reason": "No duty users for rule",
                    "deal_id": deal_id,
                    "rule_id": rule.id
                }

            # Выбираем пользователя поочередно на основе последнего обновленного пользователя из истории
            # Сортируем пользователей по ID для стабильности выбора
            rule_duty_users_sorted = sorted(rule_duty_users, key=lambda u: u.id)
            rule_duty_user_ids = {u.id for u in rule_duty_users_sorted}

            if last_assigned_id is not None and last_assigned_id in rule_duty_user_ids:
                # Находим индекс последнего пользователя в текущем списке дежурных
                last_user_index = next(
                    (i for i, u in enumerate(rule_duty_users_sorted)
                     if u.id == last_assigned_id),
                    0
                )
                # Выбираем следующего пользователя по кругу
                user_index = (last_user_index + 1) % len(rule_duty_users_sorted)
            else:
                # Если последнего пользователя нет в графике или записей нет, выбираем первого
                user_index = 0

            assigned_user = rule_duty_users_sorted[user_index]

            # Проверяем, нужно ли обновлять ответственного
            current_assigned = deal.get('ASSIGNED_BY_ID')
            if current_assigned == str(assigned_user.id):
                logger.info(f"Сделка {deal_id} уже имеет правильного ответственного {assigned_user.id}")
                return {
                    "status": "skipped",
                    "reason": "Already assigned correctly",
                    "deal_id": deal_id,
                    "assigned_user_id": assigned_user.id
                }

            # Получаем старый ответственный для истории
            old_assigned_id = None
            if current_assigned:
                try:
                    old_assigned_id = int(current_assigned)
                except (ValueError, TypeError):
                    pass

            # Обновляем ответственного в сделке
            # ВРЕМЕННОЕ РЕШЕНИЕ: также обновляем поле UF_CRM_1770115634
            await bitrix_client.update_entity(
                'deal',
                deal_id,
                {
                    'ASSIGNED_BY_ID': assigned_user.id,
                    'UF_CRM_1770115634': assigned_user.id  # Временное поле, будет удалено позже
                }
            )

            # Записываем историю изменения
            history_entries.append({
                "entity_type": 'deal',
                "entity_id": deal_id,
                "old_assigned_by_id": old_assigned_id,
                "new_assigned_by_id": assigned_user.id,
                "update_source": UpdateSource.WEBHOOK,
                "rule_id": rule.id,
            })

            # Если правило для сделок и включено обновление связанных контактов и компаний
            updated_contacts = []
            updated_company = None

            if rule.entity_type == 'deal' and rule.update_related_contacts_companies:
                # Получаем связанные контакты
                try:
                    contact_ids = await bitrix_client.get_deal_related_contacts(deal_id)
                    logger.info(f"Получено {len(contact_ids)} связанных контактов для сделки {deal_id}: {contact_ids}")
                    for contact_id in contact_ids:
                        # Получаем текущего ответственного контакта через get_entity для более надежного получения
                        contact_data = await bitrix_client.get_entity(
                            'contact',
                            contact_id,
                            select=['ID', 'ASSIGNED_BY_ID']
                        )
                        logger.debug(f"Получены данные контакта {contact_id}: {contact_data}")
                        if not contact_data:
                            logger.warning(f"Контакт {contact_id} не найден в Bitrix24")
                            continue

                        current_contact_assigned = contact_data.get('ASSIGNED_BY_ID')
                        logger.info(f"Контакт {contact_id}: текущий ответственный = {current_contact_assigned}, новый = {assigned_user.id}")

                        if current_contact_assigned != str(assigned_user.id):
                            old_contact_assigned = current_contact_assigned
                            old_contact_assigned_id = None
                            if old_contact_assigned:
                                try:
                                    old_contact_assigned_id = int(old_contact_assigned)
                                except (ValueError, TypeError):
                                    pass

                            # Обновляем ответственного в контакте
                            # ВРЕМЕННОЕ РЕШЕНИЕ: также обновляем поле UF_CRM_1770115634
                            await bitrix_client.update_entity(
                                'contact',
                                contact_id,
                                {
                                    'ASSIGNED_BY_ID': assigned_user.id,
                                    'UF_CRM_1770115634': assigned_user.id  # Временное поле, будет удалено позже
                                }
                            )

                            # Записываем историю изменения для связанного контакта
                            history_entries.append({
                                "entity_type": 'contact',
                                "entity_id": contact_id,
                                "old_assigned_by_id": old_contact_assigned_id,
                                "new_assigned_by_id": assigned_user.id,
                                "update_source": UpdateSource.WEBHOOK,
                                "rule_id": rule.id,
                                "related_entity_type": 'deal',
                                "related_entity_id": deal_id,
                            })
                            updated_contacts.append(contact_id)
                            logger.info(
                                f"Обновлен ответственный в контакте {contact_id} для сделки {deal_id} "
                                f"на пользователя {assigned_user.id}"
                            )
                        else:
                            logger.info(
                                f"Контакт {contact_id} уже имеет правильного ответственного {assigned_user.id}, пропускаем обновление"
                            )
                except Exception as e:
                    logger.error(f"Ошибка при обновлении контактов для сделки {deal_id}: {e}", exc_info=True)

                # Получаем связанную компанию
                try:
                    company_id = await bitrix_client.get_deal_company(deal_id)
                    if company_id:
                        # Получаем текущего ответственного компании через get_entity для более надежного получения
                        company_data = await bitrix_client.get_entity(
                            'company',
                            company_id,
                            select=['ID', 'ASSIGNED_BY_ID']
                        )
                        logger.debug(f"Получены данные компании {company_id}: {company_data}")
                        if not company_data:
                            logger.warning(f"Компания {company_id} не найдена в Bitrix24")
                        else:
                            current_company_assigned = company_data.get('ASSIGNED_BY_ID')
                            logger.info(f"Компания {company_id}: текущий ответственный = {current_company_assigned}, новый = {assigned_user.id}")

                            if current_company_assigned != str(assigned_user.id):
                                old_company_assigned = current_company_assigned
                                old_company_assigned_id = None
                                if old_company_assigned:
                                    try:
                                        old_company_assigned_id = int(old_company_assigned)
                                    except (ValueError, TypeError):
                                        pass

                                # Обновляем ответственного в компании
                                # ВРЕМЕННОЕ РЕШЕНИЕ: также обновляем поле UF_CRM_1770115634
                                await bitrix_client.update_entity(
                                    'company',
                                    company_id,
                                    {
                                        'ASSIGNED_BY_ID': assigned_user.id,
                                        'UF_CRM_1770115634': assigned_user.id  # Временное поле, будет удалено позже
                                    }
                                )

                                # Записываем историю изменения для связанной компании
                                history_entries.append({
                                    "entity_type": 'company',
                                    "entity_id": company_id,
                                    "old_assigned_by_id": old_company_assigned_id,
                                    "new_assigned_by_id": assigned_user.id,
                                    "update_source": UpdateSource.WEBHOOK,
                                    "rule_id": rule.id,
                                    "related_entity_type": 'deal',
                                    "related_entity_id": deal_id,
                                })
                                updated_company = company_id
                                logger.info(
                                    f"Обновлен ответственный в компании {company_id} для сделки {deal_id} "
                                    f"на пользователя {assigned_user.id}"
                                )
                            else:
                                logger.info(
                                    f"Компания {company_id} уже имеет правильного ответственного {assigned_user.id}, пропускаем обновление"
                                )
                except Exception as e:
                    logger.warning(f"Ошибка при обновлении компании для сделки {deal_id}: {e}")

            # ==================================================================
            # Фаза 3: запись истории короткой сессией
            # ==================================================================
            _save_history(history_entries)

            logger.info(
                f"Обновлен ответственный в сделке {deal_id} на пользователя {assigned_user.id} "
                f"({assigned_user.name} {assigned_user.last_name})"
            )

            result = {
                "status": "success",
                "deal_id": deal_id,
                "assigned_user_id": assigned_user.id,
                "assigned_user_name": f"{assigned_user.name} {assigned_user.last_name}".strip(),
                "date": str(today),
                "rule_id": rule.id
            }

            if updated_contacts:
                result["updated_contacts"] = updated_contacts
            if updated_company:
                result["updated_company"] = updated_company

            return result

        except Exception as e:
            logger.error(f"Ошибка при обновлении сделки {deal_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "reason": str(e),
                "deal_id": deal_id
            }

    except Exception as e:
        logger.error(f"Ошибка при обработке webhook события: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка обработки webhook: {str(e)}")


def _save_history(history_entries: List[Dict[str, Any]]) -> None:
    """Сохранить записи истории короткоживущей сессией БД."""
    if not history_entries:
        return
    with session_scope() as db:
        for entry in history_entries:
            db.add(UpdateHistory(**entry))
