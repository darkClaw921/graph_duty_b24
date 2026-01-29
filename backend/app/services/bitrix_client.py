from fast_bitrix24 import Bitrix
from typing import List, Dict, Any, Optional
from app.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)


class BitrixClient:
    """Клиент для работы с Bitrix24 REST API через библиотеку fast_bitrix24"""
    
    def __init__(self):
        """Инициализация клиента Bitrix24"""
        webhook = settings.bitrix24_webhook or settings.bitrix24_access_token
        if not webhook:
            raise ValueError("Необходимо указать BITRIX24_WEBHOOK или BITRIX24_ACCESS_TOKEN в переменных окружения")
        
        self.client = Bitrix(webhook)
        logger.info("Bitrix24 клиент инициализирован")
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Получить всех пользователей из Bitrix24
        
        Returns:
            Список пользователей с полями ID, NAME, LAST_NAME, EMAIL, ACTIVE
        """
        try:
            users = await self.client.get_all(
                'user.get',
                params={
                    'select': ['ID', 'NAME', 'LAST_NAME', 'EMAIL', 'ACTIVE']
                }
            )
            logger.info(f"Получено {len(users)} пользователей из Bitrix24")
            return users
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей: {e}")
            raise
    
    async def get_entity_fields(self, entity_type: str) -> Dict[str, Any]:
        """
        Получить поля сущности из Bitrix24
        
        Args:
            entity_type: Тип сущности (deal, contact, company, lead и т.д.)
            
        Returns:
            Словарь с полями сущности
        """
        try:
            method = f'crm.{entity_type}.fields'
            fields = await self.client.get_all(method)
            logger.info(f"Получено {len(fields)} полей для сущности {entity_type}")
            return fields
        except Exception as e:
            logger.error(f"Ошибка при получении полей сущности {entity_type}: {e}")
            raise
    
    async def get_entities_list(
        self,
        entity_type: str,
        select: Optional[List[str]] = None,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Получить список сущностей из Bitrix24
        
        Args:
            entity_type: Тип сущности (deal, contact, company, lead и т.д.)
            select: Список полей для выборки (по умолчанию ['ID', 'ASSIGNED_BY_ID'])
            filter_dict: Словарь фильтров для выборки
            
        Returns:
            Список сущностей
        """
        try:
            if select is None:
                select = ['ID', 'ASSIGNED_BY_ID']
            
            params = {'select': select}
            if filter_dict:
                params['filter'] = filter_dict
            
            method = f'crm.{entity_type}.list'
            # Используем get_all для автоматической обработки пагинации и получения всех данных
            entities = await self.client.get_all(method, params=params)
            
            logger.info(f"Получено {len(entities)} сущностей типа {entity_type}")
            return entities
        except Exception as e:
            logger.error(f"Ошибка при получении списка сущностей {entity_type}: {e}")
            raise
    
    async def update_entities_batch(
        self,
        entity_type: str,
        updates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Массовое обновление сущностей через batch запросы
        
        Args:
            entity_type: Тип сущности (deal, contact, company, lead и т.д.)
            updates: Список словарей с обновлениями в формате [{'ID': id, 'fields': {...}}, ...]
            
        Returns:
            Список результатов обновления
        """
        try:
            method = f'crm.{entity_type}.update'
            results = await self.client.call(method, updates)
            logger.info(f"Обновлено {len(updates)} сущностей типа {entity_type}")
            return results
        except Exception as e:
            logger.error(f"Ошибка при обновлении сущностей {entity_type}: {e}")
            raise
    
    async def get_entity(
        self,
        entity_type: str,
        entity_id: int,
        select: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Получить одну сущность из Bitrix24 по ID
        
        Args:
            entity_type: Тип сущности (deal, contact, company, lead и т.д.)
            entity_id: ID сущности
            select: Список полей для выборки (если не указан, возвращаются все поля)
            
        Returns:
            Словарь с данными сущности или None если не найдена
        """
        try:
            # Используем get_all с фильтром по ID - это работает синхронно
            # get_all автоматически обрабатывает batch запросы и возвращает список
            method = f'crm.{entity_type}.list'
            params = {
                'filter': {'ID': entity_id}
            }
            if select:
                params['select'] = select
            
            # get_all работает синхронно и возвращает список результатов
            entities = await self.client.get_all(method, params=params)
            
            if entities and len(entities) > 0:
                entity_data = entities[0]
                logger.debug(f"Получена сущность {entity_type} с ID {entity_id}")
                return entity_data
            else:
                logger.warning(f"Сущность {entity_type} с ID {entity_id} не найдена")
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении сущности {entity_type} с ID {entity_id}: {e}")
            raise
    
    async def update_entity(
        self,
        entity_type: str,
        entity_id: int,
        fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Обновить одну сущность
        
        Args:
            entity_type: Тип сущности
            entity_id: ID сущности
            fields: Словарь полей для обновления
            
        Returns:
            Результат обновления
        """
        try:
            method = f'crm.{entity_type}.update'
            result = await self.client.call(method, [{'ID': entity_id, 'fields': fields}])
            logger.info(f"Обновлена сущность {entity_type} с ID {entity_id}")
            return result
        except Exception as e:
            logger.error(f"Ошибка при обновлении сущности {entity_type} с ID {entity_id}: {e}")
            raise
    
    async def get_status_list(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Получить список статусов для указанного типа
        
        Args:
            entity_id: ID типа статуса (например, 'DEAL_STAGE', 'DEAL_TYPE', 'STATUS')
            
        Returns:
            Список статусов
        """
        try:
            statuses = await self.client.get_all(
                'crm.status.list',
                params={'filter': {'ENTITY_ID': entity_id}}
            )
            logger.info(f"Получено {len(statuses)} статусов для {entity_id}")
            return statuses
        except Exception as e:
            logger.error(f"Ошибка при получении статусов {entity_id}: {e}")
            raise
    
    async def get_category_list(self, entity_type_id: int) -> List[Dict[str, Any]]:
        """
        Получить список категорий (воронок) для типа сущности
        
        Args:
            entity_type_id: ID типа сущности (1 - Лиды, 2 - Сделки, 3 - Контакты, 4 - Компании)
            
        Returns:
            Список категорий
        """
        try:
            # Используем get_all для автоматической обработки batch запросов
            categories = await self.client.get_all('crm.category.list', params={'entityTypeId': entity_type_id})
            logger.info(f"Получено {len(categories)} категорий для entityTypeId {entity_type_id}")
            return categories
        except Exception as e:
            logger.error(f"Ошибка при получении категорий для entityTypeId {entity_type_id}: {e}")
            raise
    
    async def get_category_stages(self, entity_type_id: int, category_id: int) -> List[Dict[str, Any]]:
        """
        Получить стадии для конкретной категории (воронки)
        
        Args:
            entity_type_id: ID типа сущности (1 - Лиды, 2 - Сделки, 3 - Контакты, 4 - Компании)
            category_id: ID категории
            
        Returns:
            Список стадий
        """
        try:
            # Для нулевой категории используем DEAL_STAGE
            if category_id == 0:
                entity_id = 'DEAL_STAGE'
            else:
                # Для остальных категорий используем формат DEAL_STAGE_{category_id}
                entity_id = f'DEAL_STAGE_{category_id}'
            
            stages = await self.client.get_all(
                'crm.status.list',
                params={'filter': {'ENTITY_ID': entity_id}}
            )
            logger.info(f"Получено {len(stages)} стадий для категории {category_id} (ENTITY_ID: {entity_id})")
            return stages
        except Exception as e:
            logger.error(f"Ошибка при получении стадий для категории {category_id}: {e}")
            raise
    
    async def get_deal_related_contacts(self, deal_id: int) -> List[int]:
        """
        Получить список ID контактов, связанных со сделкой
        
        Args:
            deal_id: ID сделки
            
        Returns:
            Список ID контактов
        """
        try:
            result = await self.client.call('crm.deal.contact.items.get', {'id': deal_id})
            contact_ids = []
            
            # Библиотека fast_bitrix24 уже обрабатывает batch формат и может вернуть:
            # 1. Список контактов: [{'CONTACT_ID': 6, ...}, ...]
            # 2. Один контакт как словарь: {'CONTACT_ID': 6, ...}
            # 3. Batch формат: {'result': {'result': {'order0000000000': [...]}}}
            
            contacts = []
            
            if isinstance(result, list):
                # Если это список контактов
                contacts = result
            elif isinstance(result, dict):
                # Проверяем, это batch формат или уже обработанный контакт
                if 'CONTACT_ID' in result:
                    # Это уже один контакт как словарь
                    contacts = [result]
                elif 'result' in result:
                    result_data = result['result']
                    # Проверяем batch формат
                    if isinstance(result_data, dict) and 'result' in result_data:
                        batch_result = result_data['result']
                        # Извлекаем данные из первого order
                        if batch_result:
                            first_order = list(batch_result.values())[0]
                            contacts = first_order if isinstance(first_order, list) else [first_order]
                    elif isinstance(result_data, list):
                        contacts = result_data
                    elif isinstance(result_data, dict) and 'CONTACT_ID' in result_data:
                        # Один контакт в result
                        contacts = [result_data]
            
            if contacts:
                for contact in contacts:
                    contact_id = contact.get('CONTACT_ID')
                    if contact_id:
                        contact_ids.append(int(contact_id))
            
            logger.debug(f"Получено {len(contact_ids)} контактов для сделки {deal_id}")
            return contact_ids
        except Exception as e:
            logger.error(f"Ошибка при получении контактов для сделки {deal_id}: {e}", exc_info=True)
            return []
    
    async def get_deal_company(self, deal_id: int) -> Optional[int]:
        """
        Получить ID компании, связанной со сделкой
        
        Args:
            deal_id: ID сделки
            
        Returns:
            ID компании или None
        """
        try:
            deal_data = await self.get_entity('deal', deal_id, select=['COMPANY_ID'])
            if deal_data:
                company_id = deal_data.get('COMPANY_ID')
                if company_id:
                    return int(company_id)
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении компании для сделки {deal_id}: {e}")
            return None
    
    async def get_deals_related_contacts_batch(self, deal_ids: List[int]) -> Dict[int, List[int]]:
        """
        Получить связанные контакты для множества сделок через параллельные запросы
        
        Args:
            deal_ids: Список ID сделок
            
        Returns:
            Словарь {deal_id: [contact_ids]}
        """
        if not deal_ids:
            return {}
        
        result_dict = {deal_id: [] for deal_id in deal_ids}
        
        try:
            # Используем параллельные запросы через asyncio.gather
            # Группируем запросы по батчам для контроля нагрузки
            batch_size = 50
            
            # Обрабатываем все сделки батчами
            for i in range(0, len(deal_ids), batch_size):
                batch_deal_ids = deal_ids[i:i + batch_size]
                
                # Создаем задачи для параллельного выполнения
                batch_tasks = [
                    self.get_deal_related_contacts(deal_id) 
                    for deal_id in batch_deal_ids
                ]
                
                # Выполняем batch запросов параллельно
                contact_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Обрабатываем результаты
                for deal_id, contact_ids in zip(batch_deal_ids, contact_results):
                    if isinstance(contact_ids, Exception):
                        logger.warning(f"Ошибка при получении контактов для сделки {deal_id}: {contact_ids}")
                        result_dict[deal_id] = []
                    else:
                        result_dict[deal_id] = contact_ids
                        logger.debug(f"Сделка {deal_id}: получено {len(contact_ids)} контактов: {contact_ids}")
            
            logger.info(f"Получены контакты для {len(deal_ids)} сделок через параллельные запросы. Результат: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Ошибка при batch получении контактов для сделок: {e}", exc_info=True)
            return result_dict
    
    async def get_deals_companies_batch(self, deal_ids: List[int]) -> Dict[int, Optional[int]]:
        """
        Получить связанные компании для множества сделок через batch запросы
        
        Args:
            deal_ids: Список ID сделок
            
        Returns:
            Словарь {deal_id: company_id или None}
        """
        if not deal_ids:
            return {}
        
        result_dict = {deal_id: None for deal_id in deal_ids}
        
        try:
            # Получаем все сделки одним запросом с фильтром по ID
            # Используем get_all с фильтром IN для получения всех сделок сразу
            deals = await self.client.get_all(
                'crm.deal.list',
                params={
                    'select': ['ID', 'COMPANY_ID'],
                    'filter': {'ID': deal_ids}
                }
            )
            
            # Формируем словарь результатов
            for deal in deals:
                deal_id = int(deal.get('ID'))
                company_id = deal.get('COMPANY_ID')
                if company_id:
                    result_dict[deal_id] = int(company_id)
            
            logger.info(f"Получены компании для {len(deal_ids)} сделок через batch")
            return result_dict
        except Exception as e:
            logger.error(f"Ошибка при batch получении компаний для сделок: {e}", exc_info=True)
            return result_dict
    
    async def get_entities_batch(
        self,
        entity_type: str,
        entity_ids: List[int],
        select: Optional[List[str]] = None
    ) -> Dict[int, Dict[str, Any]]:
        """
        Получить информацию о множестве сущностей одним запросом
        
        Args:
            entity_type: Тип сущности (contact, company и т.д.)
            entity_ids: Список ID сущностей
            select: Список полей для выборки
            
        Returns:
            Словарь {entity_id: entity_data}
        """
        if not entity_ids:
            return {}
        
        if select is None:
            select = ['ID', 'ASSIGNED_BY_ID']
        
        result_dict = {}
        
        try:
            # Получаем все сущности одним запросом с фильтром по ID
            entities = await self.client.get_all(
                f'crm.{entity_type}.list',
                params={
                    'select': select,
                    'filter': {'ID': entity_ids}
                }
            )
            
            # Формируем словарь результатов
            for entity in entities:
                entity_id = int(entity.get('ID'))
                result_dict[entity_id] = entity
            
            logger.info(f"Получено {len(result_dict)} сущностей типа {entity_type} через batch")
            return result_dict
        except Exception as e:
            logger.error(f"Ошибка при batch получении сущностей {entity_type}: {e}", exc_info=True)
            return result_dict


# Singleton экземпляр клиента
_bitrix_client: Optional[BitrixClient] = None


def get_bitrix_client() -> BitrixClient:
    """Получить экземпляр Bitrix24 клиента (singleton)"""
    global _bitrix_client
    if _bitrix_client is None:
        _bitrix_client = BitrixClient()
    return _bitrix_client
