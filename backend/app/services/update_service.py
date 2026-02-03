from sqlalchemy.orm import Session
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from typing import List, Optional, Set, Dict, Generator, AsyncGenerator
from app.models import UpdateRule, DutySchedule, User, UpdateHistory, UpdateSource
from app.services.bitrix_client import get_bitrix_client
from app.services.rule_engine import RuleEngine
from app.services.schedule_service import ScheduleService
import logging
import json
import asyncio

# Московский часовой пояс (MSK, UTC+3)
MSK_TIMEZONE = ZoneInfo("Europe/Moscow")

logger = logging.getLogger(__name__)


def get_today_msk() -> date:
    """Получить текущую дату в московском часовом поясе"""
    return datetime.now(MSK_TIMEZONE).date()


class UpdateService:
    """Сервис для обновления ответственных в сущностях Bitrix24"""
    
    def __init__(self, db: Session):
        self.db = db
        self.bitrix_client = get_bitrix_client()
        self.schedule_service = ScheduleService(db)
    
    async def update_entities_for_date(self, update_date: date) -> dict:
        """
        Обновить ответственных в сущностях на указанную дату
        
        Args:
            update_date: Дата для обновления
            
        Returns:
            Словарь с результатами обновления
        """
        # Получаем пользователей на дежурстве
        duty_users = self.schedule_service.get_duty_users_for_date(update_date)
        if not duty_users:
            logger.warning(f"Нет пользователей на дежурстве на дату {update_date}")
            return {
                "date": str(update_date),
                "duty_user_ids": [],
                "duty_user_names": [],
                "updated_entities": 0,
                "errors": []
            }
        
        duty_user_ids = {u.id for u in duty_users}
        
        # Получаем все включенные правила
        rules = self.db.query(UpdateRule).filter(
            UpdateRule.enabled == True
        ).all()
        
        total_updated = 0
        errors = []
        
        for rule in rules:
            try:
                # Проверяем, что пользователи из правила находятся на дежурстве
                rule_user_ids = {ru.user_id for ru in rule.rule_users}
                if not rule_user_ids:
                    logger.warning(f"Правило {rule.id} не имеет пользователей, пропускаем")
                    continue
                
                # Проверяем пересечение пользователей правила и дежурных
                if not rule_user_ids.intersection(duty_user_ids):
                    logger.debug(f"Пользователи правила {rule.id} не на дежурстве, пропускаем")
                    continue
                
                # Фильтруем дежурных пользователей - оставляем только тех, кто есть в правиле
                rule_duty_users = [u for u in duty_users if u.id in rule_user_ids]
                
                updated_count = await self._update_rule(
                    rule,
                    rule_duty_users,
                    update_date
                )
                total_updated += updated_count
                logger.info(
                    f"Обновлено {updated_count} сущностей типа {rule.entity_type} "
                    f"для правила {rule.id} ({rule.entity_name}) "
                    f"для {len(rule_duty_users)} пользователей на дату {update_date}"
                )
            except Exception as e:
                error_msg = f"Ошибка при обновлении правила {rule.id} ({rule.entity_name}): {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return {
            "date": str(update_date),
            "duty_user_ids": [u.id for u in duty_users],
            "duty_user_names": [f"{u.name} {u.last_name}".strip() for u in duty_users],
            "updated_entities": total_updated,
            "errors": errors
        }
    
    def _get_required_fields_for_rule(self, rule: UpdateRule) -> List[str]:
        """
        Определить необходимые поля для запроса сущностей на основе правила
        
        Args:
            rule: Правило обновления
            
        Returns:
            Список полей для запроса
        """
        fields = {'ID', 'ASSIGNED_BY_ID'}  # Базовые поля всегда нужны
        
        try:
            condition_config = json.loads(rule.condition_config) if isinstance(rule.condition_config, str) else rule.condition_config
            
            if rule.rule_type == 'field_condition':
                field_id = condition_config.get('field_id')
                if field_id:
                    fields.add(field_id)
                    logger.debug(f"Добавлено поле {field_id} для фильтрации правила {rule.id}")
                
                # Если есть category_id, category_ids или stage_ids, добавляем необходимые поля
                # Поддержка обратной совместимости: если есть category_id, преобразуем в category_ids
                category_id = condition_config.get('category_id')
                category_ids = condition_config.get('category_ids', [])
                stage_ids = condition_config.get('stage_ids', [])
                
                # Если есть category_id (старый формат), преобразуем в category_ids для обратной совместимости
                if category_id is not None and not category_ids:
                    category_ids = [category_id]
                
                if category_ids:
                    fields.add('CATEGORY_ID')
                    logger.debug(f"Добавлено поле CATEGORY_ID для фильтрации по категориям {category_ids}")
                    # Если указаны категории, всегда запрашиваем STAGE_ID для корректной фильтрации
                    # даже если stage_ids пустой (в этом случае правило применяется ко всем воронкам)
                    fields.add('STAGE_ID')
                    logger.debug(f"Добавлено поле STAGE_ID для фильтрации по категориям {category_ids}")
                
                if stage_ids:
                    # Если stage_ids указан явно, это уже добавлено выше, но логируем для ясности
                    logger.debug(f"Фильтрация по стадиям {stage_ids}")
                    
            elif rule.rule_type == 'combined':
                conditions = condition_config.get('conditions', [])
                for condition in conditions:
                    if condition.get('type') == 'field_condition':
                        field_id = condition.get('field_id')
                        if field_id:
                            fields.add(field_id)
                            logger.debug(f"Добавлено поле {field_id} для фильтрации правила {rule.id}")
                        
                        # Проверяем category_id, category_ids и stage_ids в комбинированных условиях
                        # Поддержка обратной совместимости: если есть category_id, преобразуем в category_ids
                        category_id = condition.get('category_id')
                        category_ids = condition.get('category_ids', [])
                        stage_ids = condition.get('stage_ids', [])
                        
                        # Если есть category_id (старый формат), преобразуем в category_ids для обратной совместимости
                        if category_id is not None and not category_ids:
                            category_ids = [category_id]
                        
                        if category_ids:
                            fields.add('CATEGORY_ID')
                            # Если указаны категории, всегда запрашиваем STAGE_ID для корректной фильтрации
                            # даже если stage_ids пустой (в этом случае правило применяется ко всем воронкам)
                            fields.add('STAGE_ID')
                        elif stage_ids:
                            # Если stage_ids указан без category_ids (маловероятно, но на всякий случай)
                            fields.add('STAGE_ID')
        except Exception as e:
            logger.warning(f"Ошибка при определении полей для правила {rule.id}: {e}")
        
        return list(fields)
    
    async def _update_rule(
        self,
        rule: UpdateRule,
        duty_users: List[User],
        update_date: date,
        progress_callback: Optional[callable] = None
    ) -> int:
        """
        Обновить ответственных для конкретного правила с распределением по пользователям
        
        Args:
            rule: Правило обновления
            duty_users: Список пользователей на дежурстве (отфильтрованные по правилу)
            update_date: Дата обновления
            progress_callback: Опциональный callback для отправки прогресса (current_count, total_count)
            
        Returns:
            Количество обновленных сущностей
        """
        # Определяем необходимые поля для запроса на основе правила
        required_fields = self._get_required_fields_for_rule(rule)
        
        # Если правило для сделок и включено обновление связанных контактов и компаний,
        # добавляем поля CONTACT_ID и COMPANY_ID для получения связанных сущностей
        if rule.entity_type == 'deal' and rule.update_related_contacts_companies:
            required_fields.extend(['CONTACT_ID', 'COMPANY_ID'])
        
        logger.debug(f"Правило {rule.id} требует поля: {required_fields}")
        
        # Для сделок добавляем фильтр по STAGE_SEMANTIC_ID - только сделки "в работе"
        filter_dict = None
        if rule.entity_type == 'deal':
            # STAGE_SEMANTIC_ID = 'P' означает "первичный контакт" (в работе)
            # Также можно использовать 'W' для "winning" (в работе)
            filter_dict = {'STAGE_SEMANTIC_ID': 'P'}
            logger.info(f"Применение фильтра для сделок: только STAGE_SEMANTIC_ID='P' (в работе)")
        
        # Получаем все сущности этого типа из Bitrix24 с необходимыми полями
        entities = await self.bitrix_client.get_entities_list(
            rule.entity_type,
            select=required_fields,
            filter_dict=filter_dict
        )
        
        if not entities:
            return 0
        
        # Применяем правило для фильтрации (используем одно правило)
        logger.info(f"Применение правила {rule.id} ({rule.entity_name}): получено {len(entities)} сущностей типа {rule.entity_type}")
        rule_engine = RuleEngine([rule])
        filtered_entities = rule_engine.apply_rules(entities)
        logger.info(f"После фильтрации правилом {rule.id}: осталось {len(filtered_entities)} сущностей")
        
        if not filtered_entities:
            logger.info(f"Нет сущностей типа {rule.entity_type}, прошедших фильтрацию по правилу {rule.id}")
            return 0
        
        # Распределяем сущности между пользователями
        user_assignments = self._distribute_entities(
            filtered_entities,
            duty_users,
            rule.distribution_percentage
        )
        
        # Если правило для сделок и включено обновление связанных контактов и компаний,
        # получаем все данные заранее через batch запросы
        deals_contacts_dict = {}
        deals_companies_dict = {}
        contacts_data_dict = {}
        companies_data_dict = {}
        
        if rule.entity_type == 'deal' and rule.update_related_contacts_companies:
            try:
                # Получаем все ID сделок из assignments
                all_deal_ids = []
                for entity_ids in user_assignments.values():
                    for entity_id in entity_ids:
                        entity = next((e for e in filtered_entities if e['ID'] == entity_id), None)
                        if entity:
                            try:
                                all_deal_ids.append(int(entity_id))
                            except (ValueError, TypeError):
                                pass
                
                if all_deal_ids:
                    # Получаем контакты для всех сделок одним batch запросом
                    deals_contacts_dict = await self.bitrix_client.get_deals_related_contacts_batch(all_deal_ids)
                    
                    # Собираем все уникальные ID контактов
                    all_contact_ids = set()
                    for contact_ids in deals_contacts_dict.values():
                        all_contact_ids.update(contact_ids)
                    
                    # Получаем информацию о всех контактах одним запросом
                    if all_contact_ids:
                        contacts_data_dict = await self.bitrix_client.get_entities_batch(
                            'contact',
                            list(all_contact_ids),
                            select=['ID', 'ASSIGNED_BY_ID']
                        )
                    
                    # Получаем компании для всех сделок одним batch запросом
                    deals_companies_dict = await self.bitrix_client.get_deals_companies_batch(all_deal_ids)
                    
                    # Собираем все уникальные ID компаний
                    all_company_ids = {cid for cid in deals_companies_dict.values() if cid is not None}
                    
                    # Получаем информацию о всех компаниях одним запросом
                    if all_company_ids:
                        companies_data_dict = await self.bitrix_client.get_entities_batch(
                            'company',
                            list(all_company_ids),
                            select=['ID', 'ASSIGNED_BY_ID']
                        )
            except Exception as e:
                logger.warning(f"Ошибка при batch получении связанных сущностей для обновления: {e}")
        
        # Подготавливаем обновления
        updates = []
        related_updates = []  # Обновления для связанных контактов и компаний
        history_entries = []  # Записи истории для сохранения после обновления
        
        for user_id, entity_ids in user_assignments.items():
            for entity_id in entity_ids:
                entity = next((e for e in filtered_entities if e['ID'] == entity_id), None)
                if entity:
                    # Сохраняем старый ответственный для истории
                    current_assigned = entity.get('ASSIGNED_BY_ID')
                    old_assigned_id = None
                    if current_assigned:
                        try:
                            old_assigned_id = int(current_assigned)
                        except (ValueError, TypeError):
                            pass
                    
                    # Всегда обновляем сущность для перераспределения по правилам распределения
                    updates.append({
                        'ID': entity_id,
                        'fields': {
                            'ASSIGNED_BY_ID': user_id
                        }
                    })
                    
                    # Подготавливаем запись истории для основной сущности
                    history_entries.append({
                        'entity_type': rule.entity_type,
                        'entity_id': int(entity_id),
                        'old_assigned_by_id': old_assigned_id,
                        'new_assigned_by_id': user_id,
                        'update_source': UpdateSource.SCHEDULED if update_date == get_today_msk() else UpdateSource.MANUAL,
                        'rule_id': rule.id
                    })
                    
                    # Если правило для сделок и включено обновление связанных контактов и компаний
                    logger.debug(f"Проверка обновления связанных сущностей для сущности {entity_id}: entity_type={rule.entity_type}, update_related={rule.update_related_contacts_companies}")
                    if rule.entity_type == 'deal' and rule.update_related_contacts_companies:
                        deal_id = int(entity_id)
                        logger.info(f"Обработка связанных сущностей для сделки {deal_id}, правило {rule.id}, update_related={rule.update_related_contacts_companies}")
                        
                        # Используем заранее полученные данные о контактах
                        contact_ids = deals_contacts_dict.get(deal_id, [])
                        logger.info(f"Получено {len(contact_ids)} связанных контактов для сделки {deal_id}: {contact_ids}")
                        for contact_id in contact_ids:
                            contact_data = contacts_data_dict.get(contact_id)
                            if contact_data:
                                current_contact_assigned = contact_data.get('ASSIGNED_BY_ID')
                                logger.info(f"Контакт {contact_id}: текущий ответственный = {current_contact_assigned}, новый = {user_id}")
                                if current_contact_assigned != str(user_id):
                                    old_contact_assigned = current_contact_assigned
                                    old_contact_assigned_id = None
                                    if old_contact_assigned:
                                        try:
                                            old_contact_assigned_id = int(old_contact_assigned)
                                        except (ValueError, TypeError):
                                            pass
                                    
                                    related_updates.append({
                                        'ID': contact_id,
                                        'fields': {
                                            'ASSIGNED_BY_ID': user_id
                                        },
                                        'entity_type': 'contact',
                                        'old_assigned_by_id': old_contact_assigned_id
                                    })
                                    
                                    # Подготавливаем запись истории для связанного контакта
                                    history_entries.append({
                                        'entity_type': 'contact',
                                        'entity_id': contact_id,
                                        'old_assigned_by_id': old_contact_assigned_id,
                                        'new_assigned_by_id': user_id,
                                        'update_source': UpdateSource.SCHEDULED if update_date == get_today_msk() else UpdateSource.MANUAL,
                                        'rule_id': rule.id,
                                        'related_entity_type': 'deal',
                                        'related_entity_id': deal_id
                                    })
                                    logger.info(f"Добавлено обновление контакта {contact_id} для сделки {deal_id} (старый: {old_contact_assigned_id}, новый: {user_id})")
                                else:
                                    logger.info(f"Контакт {contact_id} уже имеет правильного ответственного {user_id}, пропускаем")
                            else:
                                logger.warning(f"Контакт {contact_id} не найден в batch данных")
                        
                        # Используем заранее полученные данные о компаниях
                        company_id = deals_companies_dict.get(deal_id)
                        logger.info(f"Получена связанная компания для сделки {deal_id}: {company_id}")
                        if company_id:
                            company_data = companies_data_dict.get(company_id)
                            if company_data:
                                current_company_assigned = company_data.get('ASSIGNED_BY_ID')
                                logger.info(f"Компания {company_id}: текущий ответственный = {current_company_assigned}, новый = {user_id}")
                                if current_company_assigned != str(user_id):
                                    old_company_assigned = current_company_assigned
                                    old_company_assigned_id = None
                                    if old_company_assigned:
                                        try:
                                            old_company_assigned_id = int(old_company_assigned)
                                        except (ValueError, TypeError):
                                            pass
                                    
                                    related_updates.append({
                                        'ID': company_id,
                                        'fields': {
                                            'ASSIGNED_BY_ID': user_id
                                        },
                                        'entity_type': 'company',
                                        'old_assigned_by_id': old_company_assigned_id
                                    })
                                    
                                    # Подготавливаем запись истории для связанной компании
                                    history_entries.append({
                                        'entity_type': 'company',
                                        'entity_id': company_id,
                                        'old_assigned_by_id': old_company_assigned_id,
                                        'new_assigned_by_id': user_id,
                                        'update_source': UpdateSource.SCHEDULED if update_date == get_today_msk() else UpdateSource.MANUAL,
                                        'rule_id': rule.id,
                                        'related_entity_type': 'deal',
                                        'related_entity_id': deal_id
                                    })
                                    logger.info(f"Добавлено обновление компании {company_id} для сделки {deal_id} (старый: {old_company_assigned_id}, новый: {user_id})")
                                else:
                                    logger.info(f"Компания {company_id} уже имеет правильного ответственного {user_id}, пропускаем")
                            else:
                                logger.warning(f"Компания {company_id} не найдена в batch данных")
        
        logger.info(f"Подготовлено {len(updates)} обновлений для правила {rule.id}")
        if related_updates:
            logger.info(f"Подготовлено {len(related_updates)} обновлений связанных контактов и компаний для правила {rule.id}")
        
        if not updates and not related_updates:
            logger.info(f"Нет сущностей для обновления для правила {rule.id} (нет распределенных сущностей)")
            return 0
        
        # Вычисляем общее количество сущностей для обновления
        total_to_update = len(updates) + len(related_updates)
        
        # Выполняем массовое обновление через batch
        total_updated = 0
        current_count = 0
        try:
            if updates:
                await self.bitrix_client.update_entities_batch(
                    rule.entity_type,
                    updates
                )
                total_updated += len(updates)
                current_count += len(updates)
                
                # Отправляем прогресс после обновления основных сущностей
                if progress_callback:
                    await progress_callback(current_count, total_to_update)
            
            # Обновляем связанные контакты и компании
            if related_updates:
                # Группируем обновления по типу сущности
                contact_updates = [u for u in related_updates if u.get('entity_type') == 'contact']
                company_updates = [u for u in related_updates if u.get('entity_type') == 'company']
                
                if contact_updates:
                    contact_batch = [{'ID': u['ID'], 'fields': u['fields']} for u in contact_updates]
                    await self.bitrix_client.update_entities_batch('contact', contact_batch)
                    total_updated += len(contact_updates)
                    current_count += len(contact_updates)
                    logger.info(f"Обновлено {len(contact_updates)} связанных контактов для правила {rule.id}")
                    
                    # Отправляем прогресс после обновления контактов
                    if progress_callback:
                        await progress_callback(current_count, total_to_update)
                
                if company_updates:
                    company_batch = [{'ID': u['ID'], 'fields': u['fields']} for u in company_updates]
                    await self.bitrix_client.update_entities_batch('company', company_batch)
                    total_updated += len(company_updates)
                    current_count += len(company_updates)
                    logger.info(f"Обновлено {len(company_updates)} связанных компаний для правила {rule.id}")
                    
                    # Отправляем прогресс после обновления компаний
                    if progress_callback:
                        await progress_callback(current_count, total_to_update)
            
            # Сохраняем историю изменений после успешного обновления
            if history_entries:
                for entry in history_entries:
                    history = UpdateHistory(**entry)
                    self.db.add(history)
                self.db.commit()
                logger.info(f"Сохранено {len(history_entries)} записей истории для правила {rule.id}")
            
            return total_updated
        except Exception as e:
            logger.error(f"Ошибка при batch обновлении сущностей {rule.entity_type} для правила {rule.id}: {e}")
            self.db.rollback()
            raise
    
    def _distribute_entities(
        self,
        entities: List[dict],
        duty_users: List[User],
        distribution_percentage: int
    ) -> dict:
        """
        Распределить сущности между пользователями согласно процентному соотношению
        
        Args:
            entities: Список сущностей для распределения
            duty_users: Список пользователей на дежурстве
            distribution_percentage: Процент распределения (100 = равномерно)
            
        Returns:
            Словарь {user_id: [entity_ids]}
        """
        if not duty_users or not entities:
            return {}
        
        user_assignments = {user.id: [] for user in duty_users}
        
        # Если процент 100 или больше - равномерное распределение
        if distribution_percentage >= 100:
            entities_per_user = len(entities) // len(duty_users)
            remainder = len(entities) % len(duty_users)
            
            entity_index = 0
            for i, user in enumerate(duty_users):
                count = entities_per_user + (1 if i < remainder else 0)
                user_assignments[user.id] = [
                    entities[j]['ID'] for j in range(entity_index, entity_index + count)
                ]
                entity_index += count
        else:
            # Процентное распределение
            # Вычисляем количество сущностей для каждого пользователя
            total_percentage = distribution_percentage * len(duty_users) / 100
            if total_percentage > 1:
                total_percentage = 1
            
            entities_to_distribute = int(len(entities) * total_percentage)
            entities_per_user = entities_to_distribute // len(duty_users)
            remainder = entities_to_distribute % len(duty_users)
            
            entity_index = 0
            for i, user in enumerate(duty_users):
                count = entities_per_user + (1 if i < remainder else 0)
                user_assignments[user.id] = [
                    entities[j]['ID'] for j in range(entity_index, entity_index + count)
                ]
                entity_index += count
        
        return user_assignments
    
    async def update_entities_now(self) -> dict:
        """
        Принудительное обновление ответственных на текущую дату (в московском времени)
        
        Returns:
            Словарь с результатами обновления
        """
        # Используем московское время для определения текущей даты
        now_msk = datetime.now(MSK_TIMEZONE)
        today = now_msk.date()
        return await self.update_entities_for_date(today)
    
    def should_update_rule(self, rule: UpdateRule, check_datetime: datetime) -> bool:
        """
        Проверить, нужно ли обновлять сущности для данного правила в указанное время
        
        Args:
            rule: Правило обновления
            check_datetime: Дата и время для проверки (должно быть в московском времени)
            
        Returns:
            True если нужно обновлять, False иначе
        """
        # Убеждаемся, что время в московском часовом поясе
        if check_datetime.tzinfo is None:
            # Если время без часового пояса, считаем его московским
            check_datetime_msk = check_datetime.replace(tzinfo=MSK_TIMEZONE)
        elif check_datetime.tzinfo != MSK_TIMEZONE:
            # Если время в другом часовом поясе, конвертируем в московское
            check_datetime_msk = check_datetime.astimezone(MSK_TIMEZONE)
        else:
            check_datetime_msk = check_datetime
        
        # Проверяем время обновления (сравниваем время в московском часовом поясе)
        update_time = rule.update_time
        check_time = check_datetime_msk.time()
        
        if check_time < update_time:
            return False
        
        # Проверяем дни недели (используем московское время)
        if rule.update_days:
            try:
                update_days = json.loads(rule.update_days) if isinstance(rule.update_days, str) else rule.update_days
                weekday = check_datetime_msk.weekday() + 1  # Python weekday: 0=Monday, Bitrix: 1=Monday
                if weekday not in update_days:
                    return False
            except Exception as e:
                logger.error(f"Ошибка при проверке дней недели для правила {rule.id}: {e}")
        
        return True
    
    async def get_entities_count_for_date(self, update_date: date) -> dict:
        """
        Получить количество сущностей, которые будут обновлены на указанную дату (без реального обновления)
        
        Args:
            update_date: Дата для проверки
            
        Returns:
            Словарь с информацией о количестве сущностей для каждого правила
        """
        # Получаем пользователей на дежурстве
        duty_users = self.schedule_service.get_duty_users_for_date(update_date)
        if not duty_users:
            return {
                "date": str(update_date),
                "total_count": 0,
                "rules": []
            }
        
        duty_user_ids = {u.id for u in duty_users}
        
        # Получаем все включенные правила
        rules = self.db.query(UpdateRule).filter(
            UpdateRule.enabled == True
        ).all()
        
        rules_info = []
        total_count = 0
        
        for rule in rules:
            try:
                # Проверяем, что пользователи из правила находятся на дежурстве
                rule_user_ids = {ru.user_id for ru in rule.rule_users}
                if not rule_user_ids:
                    continue
                
                # Проверяем пересечение пользователей правила и дежурных
                if not rule_user_ids.intersection(duty_user_ids):
                    continue
                
                # Фильтруем дежурных пользователей - оставляем только тех, кто есть в правиле
                rule_duty_users = [u for u in duty_users if u.id in rule_user_ids]
                
                # Получаем количество сущностей для этого правила
                count = await self._get_rule_entities_count(rule, rule_duty_users)
                total_count += count
                
                rules_info.append({
                    "rule_id": rule.id,
                    "rule_name": rule.entity_name,
                    "entity_type": rule.entity_type,
                    "count": count
                })
            except Exception as e:
                logger.error(f"Ошибка при подсчете сущностей для правила {rule.id}: {e}")
        
        return {
            "date": str(update_date),
            "total_count": total_count,
            "rules": rules_info
        }
    
    async def _get_rule_entities_count(self, rule: UpdateRule, duty_users: List[User]) -> int:
        """
        Получить количество сущностей, которые будут обновлены для конкретного правила
        
        Args:
            rule: Правило обновления
            duty_users: Список пользователей на дежурстве (отфильтрованные по правилу)
            
        Returns:
            Количество сущностей для обновления
        """
        # Определяем необходимые поля для запроса на основе правила
        required_fields = self._get_required_fields_for_rule(rule)
        
        # Для сделок добавляем фильтр по STAGE_SEMANTIC_ID - только сделки "в работе"
        filter_dict = None
        if rule.entity_type == 'deal':
            # STAGE_SEMANTIC_ID = 'P' означает "первичный контакт" (в работе)
            filter_dict = {'STAGE_SEMANTIC_ID': 'P'}
            logger.info(f"Применение фильтра для сделок: только STAGE_SEMANTIC_ID='P' (в работе)")
        
        # Получаем все сущности этого типа из Bitrix24 с необходимыми полями
        entities = await self.bitrix_client.get_entities_list(
            rule.entity_type,
            select=required_fields,
            filter_dict=filter_dict
        )
        
        if not entities:
            return 0
        
        # Применяем правило для фильтрации
        rule_engine = RuleEngine([rule])
        filtered_entities = rule_engine.apply_rules(entities)
        
        if not filtered_entities:
            return 0
        
        # Распределяем сущности между пользователями
        user_assignments = self._distribute_entities(
            filtered_entities,
            duty_users,
            rule.distribution_percentage
        )
        
        # Подсчитываем количество сущностей, которые нужно обновить
        count = 0
        for user_id, entity_ids in user_assignments.items():
            for entity_id in entity_ids:
                entity = next((e for e in filtered_entities if e['ID'] == entity_id), None)
                if entity:
                    # Считаем только те, которые нужно обновить
                    if entity.get('ASSIGNED_BY_ID') != str(user_id):
                        count += 1
        
        return count
    
    async def get_preview_updates(self, update_date: date) -> dict:
        """
        Получить предпросмотр сущностей, которые будут обновлены на указанную дату (без реального обновления)
        
        Args:
            update_date: Дата для проверки
            
        Returns:
            Словарь с информацией о сущностях для каждого правила
        """
        # Получаем пользователей на дежурстве
        duty_users = self.schedule_service.get_duty_users_for_date(update_date)
        if not duty_users:
            return {
                "date": str(update_date),
                "total_count": 0,
                "entities": []
            }
        
        duty_user_ids = {u.id for u in duty_users}
        
        # Получаем все включенные правила
        rules = self.db.query(UpdateRule).filter(
            UpdateRule.enabled == True
        ).all()
        
        all_preview_entities = []
        total_count = 0
        
        for rule in rules:
            try:
                # Проверяем, что пользователи из правила находятся на дежурстве
                rule_user_ids = {ru.user_id for ru in rule.rule_users}
                if not rule_user_ids:
                    continue
                
                # Проверяем пересечение пользователей правила и дежурных
                if not rule_user_ids.intersection(duty_user_ids):
                    continue
                
                # Фильтруем дежурных пользователей - оставляем только тех, кто есть в правиле
                rule_duty_users = [u for u in duty_users if u.id in rule_user_ids]
                
                # Получаем предпросмотр сущностей для этого правила
                rule_preview = await self._get_rule_preview_updates(rule, rule_duty_users)
                all_preview_entities.extend(rule_preview)
                total_count += len(rule_preview)
            except Exception as e:
                logger.error(f"Ошибка при получении предпросмотра для правила {rule.id}: {e}")
        
        return {
            "date": str(update_date),
            "total_count": total_count,
            "entities": all_preview_entities
        }
    
    async def _get_rule_preview_updates(self, rule: UpdateRule, duty_users: List[User]) -> List[dict]:
        """
        Получить предпросмотр сущностей, которые будут обновлены для конкретного правила
        
        Args:
            rule: Правило обновления
            duty_users: Список пользователей на дежурстве (отфильтрованные по правилу)
            
        Returns:
            Список словарей с информацией о сущностях для обновления
        """
        # Определяем необходимые поля для запроса на основе правила
        required_fields = self._get_required_fields_for_rule(rule)
        
        # Если правило для сделок и включено обновление связанных контактов и компаний,
        # добавляем поля CONTACT_ID и COMPANY_ID для получения связанных сущностей
        if rule.entity_type == 'deal' and rule.update_related_contacts_companies:
            required_fields.extend(['CONTACT_ID', 'COMPANY_ID'])
        
        # Для сделок добавляем фильтр по STAGE_SEMANTIC_ID - только сделки "в работе"
        filter_dict = None
        if rule.entity_type == 'deal':
            # STAGE_SEMANTIC_ID = 'P' означает "первичный контакт" (в работе)
            filter_dict = {'STAGE_SEMANTIC_ID': 'P'}
            logger.info(f"Применение фильтра для сделок в предпросмотре: только STAGE_SEMANTIC_ID='P' (в работе)")
        
        # Получаем все сущности этого типа из Bitrix24 с необходимыми полями
        entities = await self.bitrix_client.get_entities_list(
            rule.entity_type,
            select=required_fields,
            filter_dict=filter_dict
        )
        
        if not entities:
            return []
        
        # Применяем правило для фильтрации
        rule_engine = RuleEngine([rule])
        filtered_entities = rule_engine.apply_rules(entities)
        
        if not filtered_entities:
            return []
        
        # Распределяем сущности между пользователями
        user_assignments = self._distribute_entities(
            filtered_entities,
            duty_users,
            rule.distribution_percentage
        )
        
        # Получаем всех пользователей из БД для получения имен текущих ответственных
        # Сначала собираем ID пользователей из основных сущностей
        all_user_ids = set()
        for entity in filtered_entities:
            current_assigned = entity.get('ASSIGNED_BY_ID')
            if current_assigned:
                try:
                    all_user_ids.add(int(current_assigned))
                except (ValueError, TypeError):
                    pass
        
        # Если правило для сделок и включено обновление связанных контактов и компаний,
        # собираем ID пользователей из связанных сущностей через batch запросы
        if rule.entity_type == 'deal' and rule.update_related_contacts_companies:
            try:
                # Получаем все ID сделок
                deal_ids = []
                for entity in filtered_entities:
                    entity_id = entity.get('ID')
                    if entity_id:
                        try:
                            deal_ids.append(int(entity_id))
                        except (ValueError, TypeError):
                            pass
                
                if deal_ids:
                    # Получаем контакты для всех сделок одним batch запросом
                    deals_contacts = await self.bitrix_client.get_deals_related_contacts_batch(deal_ids)
                    
                    # Собираем все уникальные ID контактов
                    all_contact_ids = set()
                    for contact_ids in deals_contacts.values():
                        all_contact_ids.update(contact_ids)
                    
                    # Получаем информацию о всех контактах одним запросом
                    if all_contact_ids:
                        contacts_dict = await self.bitrix_client.get_entities_batch(
                            'contact',
                            list(all_contact_ids),
                            select=['ID', 'ASSIGNED_BY_ID']
                        )
                        
                        # Добавляем ID пользователей из контактов
                        for contact_data in contacts_dict.values():
                            current_contact_assigned = contact_data.get('ASSIGNED_BY_ID')
                            if current_contact_assigned:
                                try:
                                    all_user_ids.add(int(current_contact_assigned))
                                except (ValueError, TypeError):
                                    pass
                    
                    # Получаем компании для всех сделок одним batch запросом
                    deals_companies = await self.bitrix_client.get_deals_companies_batch(deal_ids)
                    
                    # Собираем все уникальные ID компаний
                    all_company_ids = {cid for cid in deals_companies.values() if cid is not None}
                    
                    # Получаем информацию о всех компаниях одним запросом
                    if all_company_ids:
                        companies_dict = await self.bitrix_client.get_entities_batch(
                            'company',
                            list(all_company_ids),
                            select=['ID', 'ASSIGNED_BY_ID']
                        )
                        
                        # Добавляем ID пользователей из компаний
                        for company_data in companies_dict.values():
                            current_company_assigned = company_data.get('ASSIGNED_BY_ID')
                            if current_company_assigned:
                                try:
                                    all_user_ids.add(int(current_company_assigned))
                                except (ValueError, TypeError):
                                    pass
            except Exception as e:
                logger.warning(f"Ошибка при batch получении связанных сущностей при сборе ID пользователей: {e}")
        
        # Получаем пользователей из БД
        from app.models import User
        users_dict = {}
        if all_user_ids:
            users = self.db.query(User).filter(User.id.in_(all_user_ids)).all()
            found_user_ids = {u.id for u in users}
            missing_user_ids = all_user_ids - found_user_ids
            
            # Заполняем словарь найденными пользователями
            for u in users:
                users_dict[u.id] = f"{u.name} {u.last_name}".strip() or u.email or f"ID: {u.id}"
            
            # Для пользователей, которых нет в БД, получаем имена из Bitrix24
            if missing_user_ids:
                logger.debug(f"Получение имен пользователей из Bitrix24 для ID: {missing_user_ids}")
                try:
                    bitrix_users = await self.bitrix_client.get_all_users()
                    for bitrix_user in bitrix_users:
                        user_id = int(bitrix_user.get('ID', 0))
                        if user_id in missing_user_ids:
                            name = bitrix_user.get('NAME', '')
                            last_name = bitrix_user.get('LAST_NAME', '')
                            email = bitrix_user.get('EMAIL', '')
                            user_name = f"{name} {last_name}".strip() or email or f"ID: {user_id}"
                            users_dict[user_id] = user_name
                except Exception as e:
                    logger.warning(f"Ошибка при получении пользователей из Bitrix24: {e}")
        
        # Если правило для сделок и включено обновление связанных контактов и компаний,
        # получаем все данные заранее через batch запросы
        deals_contacts_dict = {}
        deals_companies_dict = {}
        contacts_data_dict = {}
        companies_data_dict = {}
        
        if rule.entity_type == 'deal' and rule.update_related_contacts_companies:
            try:
                # Получаем все ID сделок из preview
                all_preview_deal_ids = []
                for entity_ids in user_assignments.values():
                    for entity_id in entity_ids:
                        entity = next((e for e in filtered_entities if e['ID'] == entity_id), None)
                        if entity:
                            try:
                                all_preview_deal_ids.append(int(entity_id))
                            except (ValueError, TypeError):
                                pass
                
                if all_preview_deal_ids:
                    # Получаем контакты для всех сделок одним batch запросом
                    deals_contacts_dict = await self.bitrix_client.get_deals_related_contacts_batch(all_preview_deal_ids)
                    logger.info(f"Получены контакты для {len(deals_contacts_dict)} сделок через batch")
                    for deal_id, contact_ids in deals_contacts_dict.items():
                        logger.debug(f"Сделка {deal_id}: контакты {contact_ids}")
                    
                    # Собираем все уникальные ID контактов
                    all_contact_ids = set()
                    for contact_ids in deals_contacts_dict.values():
                        all_contact_ids.update(contact_ids)
                    logger.debug(f"Собрано {len(all_contact_ids)} уникальных ID контактов: {all_contact_ids}")
                    
                    # Получаем информацию о всех контактах одним запросом
                    if all_contact_ids:
                        contacts_data_dict = await self.bitrix_client.get_entities_batch(
                            'contact',
                            list(all_contact_ids),
                            select=['ID', 'ASSIGNED_BY_ID']
                        )
                        logger.debug(f"Получены данные для {len(contacts_data_dict)} контактов")
                    
                    # Получаем компании для всех сделок одним batch запросом
                    deals_companies_dict = await self.bitrix_client.get_deals_companies_batch(all_preview_deal_ids)
                    logger.debug(f"Получены компании для {len(deals_companies_dict)} сделок: {deals_companies_dict}")
                    
                    # Собираем все уникальные ID компаний
                    all_company_ids = {cid for cid in deals_companies_dict.values() if cid is not None}
                    logger.debug(f"Собрано {len(all_company_ids)} уникальных ID компаний: {all_company_ids}")
                    
                    # Получаем информацию о всех компаниях одним запросом
                    if all_company_ids:
                        companies_data_dict = await self.bitrix_client.get_entities_batch(
                            'company',
                            list(all_company_ids),
                            select=['ID', 'ASSIGNED_BY_ID']
                        )
                        logger.debug(f"Получены данные для {len(companies_data_dict)} компаний")
            except Exception as e:
                logger.warning(f"Ошибка при batch получении связанных сущностей для preview: {e}", exc_info=True)
        
        # Формируем список предпросмотра обновлений
        preview_entities = []
        
        for user_id, entity_ids in user_assignments.items():
            user = next((u for u in duty_users if u.id == user_id), None)
            user_name = f"{user.name} {user.last_name}".strip() if user else f"ID: {user_id}"
            
            for entity_id in entity_ids:
                entity = next((e for e in filtered_entities if e['ID'] == entity_id), None)
                if entity:
                    current_assigned = entity.get('ASSIGNED_BY_ID')
                    # Показываем только те, которые нужно обновить
                    if current_assigned != str(user_id):
                        current_assigned_id = None
                        current_assigned_name = None
                        if current_assigned:
                            try:
                                current_assigned_id = int(current_assigned)
                                current_assigned_name = users_dict.get(current_assigned_id, f"ID: {current_assigned_id}")
                            except (ValueError, TypeError):
                                current_assigned_name = str(current_assigned)
                        
                        preview_entry = {
                            "entity_id": int(entity_id),
                            "entity_type": rule.entity_type,
                            "rule_id": rule.id,
                            "rule_name": rule.entity_name,
                            "current_assigned_by_id": current_assigned_id,
                            "new_assigned_by_id": user_id,
                            "current_assigned_by_name": current_assigned_name,
                            "new_assigned_by_name": user_name,
                            "related_entities": []
                        }
                        
                        # Если правило для сделок и включено обновление связанных контактов и компаний
                        if rule.entity_type == 'deal' and rule.update_related_contacts_companies:
                            deal_id = int(entity_id)
                            related_entities = []
                            
                            # Используем заранее полученные данные о контактах
                            contact_ids = deals_contacts_dict.get(deal_id, [])
                            logger.info(f"Preview для сделки {deal_id}: получено {len(contact_ids)} контактов из словаря: {contact_ids}")
                            for contact_id in contact_ids:
                                contact_data = contacts_data_dict.get(contact_id)
                                if contact_data:
                                    current_contact_assigned = contact_data.get('ASSIGNED_BY_ID')
                                    logger.info(f"Preview для сделки {deal_id}, контакт {contact_id}: текущий = {current_contact_assigned}, новый = {user_id}, нужно обновить = {current_contact_assigned != str(user_id)}")
                                    # В preview показываем ВСЕ связанные сущности, даже если обновление не требуется
                                    # Это позволяет пользователю видеть полную картину
                                    current_contact_assigned_id = None
                                    current_contact_assigned_name = None
                                    if current_contact_assigned:
                                        try:
                                            current_contact_assigned_id = int(current_contact_assigned)
                                            current_contact_assigned_name = users_dict.get(current_contact_assigned_id, f"ID: {current_contact_assigned_id}")
                                        except (ValueError, TypeError):
                                            current_contact_assigned_name = str(current_contact_assigned)
                                    
                                    related_entities.append({
                                        "entity_id": contact_id,
                                        "entity_type": "contact",
                                        "current_assigned_by_id": current_contact_assigned_id,
                                        "current_assigned_by_name": current_contact_assigned_name,
                                        "new_assigned_by_id": user_id,
                                        "new_assigned_by_name": user_name
                                    })
                                    logger.info(f"Добавлен контакт {contact_id} в related_entities для сделки {deal_id}")
                                else:
                                    logger.warning(f"Preview для сделки {deal_id}: контакт {contact_id} не найден в contacts_data_dict (всего в словаре: {len(contacts_data_dict)} контактов)")
                            
                            # Используем заранее полученные данные о компаниях
                            company_id = deals_companies_dict.get(deal_id)
                            logger.info(f"Preview для сделки {deal_id}: получена компания {company_id} из словаря")
                            if company_id:
                                company_data = companies_data_dict.get(company_id)
                                if company_data:
                                    current_company_assigned = company_data.get('ASSIGNED_BY_ID')
                                    logger.info(f"Preview для сделки {deal_id}, компания {company_id}: текущий = {current_company_assigned}, новый = {user_id}, нужно обновить = {current_company_assigned != str(user_id)}")
                                    # В preview показываем ВСЕ связанные сущности, даже если обновление не требуется
                                    current_company_assigned_id = None
                                    current_company_assigned_name = None
                                    if current_company_assigned:
                                        try:
                                            current_company_assigned_id = int(current_company_assigned)
                                            current_company_assigned_name = users_dict.get(current_company_assigned_id, f"ID: {current_company_assigned_id}")
                                        except (ValueError, TypeError):
                                            current_company_assigned_name = str(current_company_assigned)
                                    
                                    related_entities.append({
                                        "entity_id": company_id,
                                        "entity_type": "company",
                                        "current_assigned_by_id": current_company_assigned_id,
                                        "current_assigned_by_name": current_company_assigned_name,
                                        "new_assigned_by_id": user_id,
                                        "new_assigned_by_name": user_name
                                    })
                                    logger.info(f"Добавлена компания {company_id} в related_entities для сделки {deal_id}")
                                else:
                                    logger.warning(f"Preview для сделки {deal_id}: компания {company_id} не найдена в companies_data_dict (всего в словаре: {len(companies_data_dict)} компаний)")
                            
                            preview_entry["related_entities"] = related_entities
                            logger.info(f"Preview для сделки {deal_id}: добавлено {len(related_entities)} связанных сущностей")
                        
                        preview_entities.append(preview_entry)
        
        return preview_entities
    
    async def update_entities_for_date_with_progress(
        self, 
        update_date: date
    ) -> AsyncGenerator[Dict, None]:
        """
        Обновить ответственных в сущностях на указанную дату с прогрессом
        
        Args:
            update_date: Дата для обновления
            
        Yields:
            Словари с информацией о прогрессе обновления
        """
        try:
            # Получаем пользователей на дежурстве
            duty_users = self.schedule_service.get_duty_users_for_date(update_date)
            if not duty_users:
                yield {
                    "type": "complete",
                    "date": str(update_date),
                    "duty_user_ids": [],
                    "duty_user_names": [],
                    "updated_entities": 0,
                    "errors": []
                }
                return
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей на дежурстве: {e}")
            yield {
                "type": "error",
                "date": str(update_date),
                "error": f"Ошибка при получении пользователей на дежурстве: {str(e)}",
                "updated_entities": 0,
                "errors": [str(e)]
            }
            return
        
        duty_user_ids = {u.id for u in duty_users}
        
        # Получаем все включенные правила
        rules = self.db.query(UpdateRule).filter(
            UpdateRule.enabled == True
        ).all()
        
        total_updated = 0
        errors = []
        processed_rules = 0
        
        # Получаем общее количество сущностей для обновления
        total_entities_count = await self.get_entities_count_for_date(update_date)
        total_count = total_entities_count.get("total_count", 0)
        current_entity_count = 0
        
        # Сначала отправляем информацию о начале
        yield {
            "type": "start",
            "date": str(update_date),
            "total_rules": len(rules),
            "total_count": total_count,
            "duty_user_ids": [u.id for u in duty_users],
            "duty_user_names": [f"{u.name} {u.last_name}".strip() for u in duty_users]
        }
        
        for rule in rules:
            try:
                # Проверяем, что пользователи из правила находятся на дежурстве
                rule_user_ids = {ru.user_id for ru in rule.rule_users}
                if not rule_user_ids:
                    processed_rules += 1
                    yield {
                        "type": "progress",
                        "rule_id": rule.id,
                        "rule_name": rule.entity_name,
                        "status": "skipped",
                        "reason": "Нет пользователей в правиле",
                        "processed_rules": processed_rules,
                        "total_rules": len(rules),
                        "current_count": current_entity_count,
                        "total_count": total_count
                    }
                    continue
                
                # Проверяем пересечение пользователей правила и дежурных
                if not rule_user_ids.intersection(duty_user_ids):
                    processed_rules += 1
                    yield {
                        "type": "progress",
                        "rule_id": rule.id,
                        "rule_name": rule.entity_name,
                        "status": "skipped",
                        "reason": "Пользователи правила не на дежурстве",
                        "processed_rules": processed_rules,
                        "total_rules": len(rules),
                        "current_count": current_entity_count,
                        "total_count": total_count
                    }
                    continue
                
                # Фильтруем дежурных пользователей - оставляем только тех, кто есть в правиле
                rule_duty_users = [u for u in duty_users if u.id in rule_user_ids]
                
                # Получаем количество сущностей для этого правила
                rule_entities_count = await self._get_rule_entities_count(rule, rule_duty_users)
                
                yield {
                    "type": "progress",
                    "rule_id": rule.id,
                    "rule_name": rule.entity_name,
                    "entity_type": rule.entity_type,
                    "status": "processing",
                    "processed_rules": processed_rules,
                    "total_rules": len(rules),
                    "current_count": current_entity_count,
                    "total_count": total_count,
                    "rule_total_count": rule_entities_count
                }
                
                # Создаем очередь для передачи прогресса из callback в генератор
                progress_queue = asyncio.Queue()
                
                # Создаем callback для отправки прогресса после каждого batch обновления
                rule_start_count = current_entity_count
                # Используем список для хранения счетчика, чтобы избежать проблем с nonlocal в async функции
                current_count_ref = [current_entity_count]
                
                async def progress_callback(batch_updated: int, rule_total: int):
                    new_count = rule_start_count + batch_updated
                    current_count_ref[0] = new_count
                    logger.debug(f"Callback прогресса: batch_updated={batch_updated}, current_count={new_count}, rule_total={rule_total}")
                    # Добавляем прогресс в очередь для отправки через генератор
                    await progress_queue.put({
                        "current_count": new_count,
                        "batch_updated": batch_updated
                    })
                    logger.debug(f"Прогресс добавлен в очередь: current_count={new_count}")
                
                # Сохраняем начальное значение для правила
                rule_start_entity_count = current_entity_count
                
                # Запускаем обновление правила в фоне
                update_task = asyncio.create_task(
                    self._update_rule(
                        rule,
                        rule_duty_users,
                        update_date,
                        progress_callback=progress_callback
                    )
                )
                
                # Отслеживаем прогресс и отправляем обновления
                last_sent_count = current_entity_count
                logger.debug(f"Начало отслеживания прогресса для правила {rule.id}, начальный счетчик: {last_sent_count}")
                
                # Используем более надежный механизм - ждем завершения задачи, но периодически проверяем очередь
                while not update_task.done():
                    try:
                        # Ждем прогресс с таймаутом
                        progress_data = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
                        new_count = progress_data["current_count"]
                        logger.debug(f"Получен прогресс из очереди: current_count={new_count}, last_sent={last_sent_count}")
                        
                        # Отправляем прогресс только если он изменился
                        if new_count != last_sent_count:
                            logger.info(f"Отправка прогресса для правила {rule.id}: {new_count}/{total_count}")
                            yield {
                                "type": "progress",
                                "rule_id": rule.id,
                                "rule_name": rule.entity_name,
                                "entity_type": rule.entity_type,
                                "status": "processing",
                                "processed_rules": processed_rules,
                                "total_rules": len(rules),
                                "current_count": new_count,
                                "total_count": total_count
                            }
                            last_sent_count = new_count
                    except asyncio.TimeoutError:
                        # Если нет нового прогресса, продолжаем ждать
                        # Даем небольшую задержку, чтобы не нагружать CPU
                        await asyncio.sleep(0.01)
                        continue
                
                # Обрабатываем оставшиеся элементы из очереди после завершения задачи
                logger.debug(f"Задача завершена, обработка оставшихся элементов из очереди (размер очереди: {progress_queue.qsize()})")
                while not progress_queue.empty():
                    try:
                        progress_data = progress_queue.get_nowait()
                        new_count = progress_data["current_count"]
                        logger.debug(f"Обработка оставшегося прогресса: current_count={new_count}, last_sent={last_sent_count}")
                        if new_count != last_sent_count:
                            logger.info(f"Отправка финального прогресса для правила {rule.id}: {new_count}/{total_count}")
                            yield {
                                "type": "progress",
                                "rule_id": rule.id,
                                "rule_name": rule.entity_name,
                                "entity_type": rule.entity_type,
                                "status": "processing",
                                "processed_rules": processed_rules,
                                "total_rules": len(rules),
                                "current_count": new_count,
                                "total_count": total_count
                            }
                            last_sent_count = new_count
                    except asyncio.QueueEmpty:
                        break
                
                # Получаем результат обновления
                updated_count = await update_task
                logger.debug(f"Правило {rule.id} завершено, обновлено сущностей: {updated_count}")
                
                # Обновляем счетчик после завершения правила
                # Используем значение из callback, если оно было обновлено, иначе вычисляем
                final_count = current_count_ref[0] if current_count_ref[0] > rule_start_count else rule_start_count + updated_count
                current_entity_count = final_count
                
                total_updated += updated_count
                processed_rules += 1
                
                # Отправляем финальный прогресс с правильным счетчиком
                logger.info(f"Отправка финального прогресса для правила {rule.id}: {current_entity_count}/{total_count}")
                yield {
                    "type": "progress",
                    "rule_id": rule.id,
                    "rule_name": rule.entity_name,
                    "entity_type": rule.entity_type,
                    "status": "completed",
                    "updated_count": updated_count,
                    "processed_rules": processed_rules,
                    "total_rules": len(rules),
                    "current_count": current_entity_count,
                    "total_count": total_count
                }
                
                logger.info(
                    f"Обновлено {updated_count} сущностей типа {rule.entity_type} "
                    f"для правила {rule.id} ({rule.entity_name}) "
                    f"для {len(rule_duty_users)} пользователей на дату {update_date}"
                )
            except Exception as e:
                error_msg = f"Ошибка при обновлении правила {rule.id} ({rule.entity_name}): {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                processed_rules += 1
                
                yield {
                    "type": "progress",
                    "rule_id": rule.id,
                    "rule_name": rule.entity_name,
                    "status": "error",
                    "error": error_msg,
                    "processed_rules": processed_rules,
                    "total_rules": len(rules)
                }
        
        # Отправляем финальный результат
        try:
            yield {
                "type": "complete",
                "date": str(update_date),
                "duty_user_ids": [u.id for u in duty_users],
                "duty_user_names": [f"{u.name} {u.last_name}".strip() for u in duty_users],
                "updated_entities": total_updated,
                "errors": errors
            }
        except Exception as e:
            logger.error(f"Ошибка при отправке финального результата: {e}")
            yield {
                "type": "error",
                "date": str(update_date),
                "error": f"Ошибка при отправке результата: {str(e)}",
                "updated_entities": total_updated,
                "errors": errors + [str(e)]
            }
