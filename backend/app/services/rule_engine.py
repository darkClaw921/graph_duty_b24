from typing import List, Dict, Any, Set, Optional
from app.models import UpdateRule
import json
import logging

logger = logging.getLogger(__name__)


class RuleEngine:
    """Движок выполнения правил обновления для фильтрации сущностей"""
    
    def __init__(self, rules: List[UpdateRule]):
        """
        Инициализация движка правил
        
        Args:
            rules: Список правил, отсортированных по приоритету (меньше = выше приоритет)
        """
        self.rules = sorted(rules, key=lambda r: r.priority)
    
    def apply_rules(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Применить правила к списку сущностей
        
        Правила применяются последовательно по приоритету.
        Каждое правило фильтрует список сущностей.
        
        Args:
            entities: Список сущностей из Bitrix24
            
        Returns:
            Отфильтрованный список сущностей для обновления
        """
        filtered_entities = entities.copy()
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                condition_config = json.loads(rule.condition_config) if isinstance(rule.condition_config, str) else rule.condition_config
                logger.info(f"Применение правила {rule.id} ({rule.entity_name}, тип: {rule.rule_type}): было {len(filtered_entities)} сущностей")
                filtered_entities = self._apply_rule(filtered_entities, rule.rule_type, condition_config)
                logger.info(f"Правило {rule.id} ({rule.rule_type}) отфильтровало до {len(filtered_entities)} сущностей")
            except Exception as e:
                logger.error(f"Ошибка при применении правила {rule.id}: {e}", exc_info=True)
                continue
        
        return filtered_entities
    
    def _apply_rule(
        self,
        entities: List[Dict[str, Any]],
        rule_type: str,
        condition_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Применить одно правило к списку сущностей
        
        Args:
            entities: Список сущностей
            rule_type: Тип правила
            condition_config: Конфигурация условий
            
        Returns:
            Отфильтрованный список сущностей
        """
        logger.debug(f"Применение правила типа {rule_type} с конфигурацией: {condition_config}")
        
        if rule_type == 'assigned_by_condition':
            return self._apply_assigned_by_condition(entities, condition_config)
        elif rule_type == 'field_condition':
            return self._apply_field_condition(entities, condition_config)
        elif rule_type == 'combined':
            return self._apply_combined_condition(entities, condition_config)
        else:
            logger.warning(f"Неизвестный тип правила: {rule_type}, возвращаем все сущности")
            return entities
    
    def _apply_assigned_by_condition(
        self,
        entities: List[Dict[str, Any]],
        condition_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Применить условие по текущему ответственному
        
        condition_config: {
            "operator": "equals|not_equals|in|not_in",
            "user_ids": [1, 2, 3]
        }
        """
        operator = condition_config.get('operator', 'in')
        user_ids_raw = condition_config.get('user_ids', [])
        # Преобразуем user_ids в множество строк, так как ASSIGNED_BY_ID из Bitrix24 приходит как строка
        user_ids = {str(uid) for uid in user_ids_raw}
        
        logger.debug(f"Применение assigned_by_condition: operator={operator}, user_ids={user_ids}, entities_count={len(entities)}")
        
        if operator == 'equals' or operator == 'in':
            filtered = [e for e in entities if str(e.get('ASSIGNED_BY_ID', '')) in user_ids]
            logger.debug(f"Фильтрация по {operator}: {len(filtered)} из {len(entities)} сущностей")
            return filtered
        elif operator == 'not_equals' or operator == 'not_in':
            filtered = [e for e in entities if str(e.get('ASSIGNED_BY_ID', '')) not in user_ids]
            logger.debug(f"Фильтрация по {operator}: {len(filtered)} из {len(entities)} сущностей")
            return filtered
        else:
            logger.warning(f"Неизвестный оператор для assigned_by_condition: {operator}")
            return entities
    
    def _apply_field_condition(
        self,
        entities: List[Dict[str, Any]],
        condition_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Применить условие по полю сущности
        
        condition_config может быть в двух форматах:
        1. Стандартный: {"field_id": "ASSIGNED_BY_ID", "operator": "equals", "value": "..."}
        2. Для категорий/стадий: {"field_id": "CATEGORY_ID", "category_id": 2, "stage_ids": ["C2:PREPARATION"]}
        3. Для множественных воронок: {"field_id": "CATEGORY_ID", "category_ids": [2, 3], "stage_ids": ["C2:PREPARATION"]}
        """
        field_id = condition_config.get('field_id')
        
        if not field_id:
            logger.warning("Не указано поле для условия field_condition")
            return entities
        
        # Проверяем, есть ли специальные поля для категорий/стадий
        # Поддержка обратной совместимости: если есть category_id, преобразуем в category_ids
        category_id = condition_config.get('category_id')
        category_ids = condition_config.get('category_ids', [])
        stage_ids = condition_config.get('stage_ids', [])
        
        # Если есть category_id (старый формат), преобразуем в category_ids для обратной совместимости
        if category_id is not None and not category_ids:
            category_ids = [category_id]
        
        # Если есть category_ids или stage_ids, используем специальную обработку
        if category_ids or stage_ids:
            return self._apply_category_stage_condition(entities, condition_config, field_id, category_ids, stage_ids)
        
        # Стандартная обработка с operator и value
        operator = condition_config.get('operator', 'equals')
        value = condition_config.get('value')
        
        logger.info(f"Применение field_condition: field_id={field_id}, operator={operator}, value={value}, entities_count={len(entities)}")
        
        filtered = []
        for entity in entities:
            field_value = entity.get(field_id)
            
            # Логируем первые несколько значений для отладки
            if len(filtered) < 3:
                logger.debug(f"Сущность ID={entity.get('ID')}, поле {field_id}={field_value}, сравниваем с {value}")
            
            if operator == 'equals':
                if str(field_value) == str(value):
                    filtered.append(entity)
            elif operator == 'not_equals':
                if str(field_value) != str(value):
                    filtered.append(entity)
            elif operator == 'contains':
                if field_value and str(value) in str(field_value):
                    filtered.append(entity)
            elif operator == 'greater_than':
                try:
                    if float(field_value) > float(value):
                        filtered.append(entity)
                except (ValueError, TypeError):
                    pass
            elif operator == 'less_than':
                try:
                    if float(field_value) < float(value):
                        filtered.append(entity)
                except (ValueError, TypeError):
                    pass
            else:
                logger.warning(f"Неизвестный оператор для field_condition: {operator}")
        
        logger.info(f"Фильтрация по field_condition ({field_id} {operator} {value}): {len(filtered)} из {len(entities)} сущностей")
        return filtered
    
    def _apply_category_stage_condition(
        self,
        entities: List[Dict[str, Any]],
        condition_config: Dict[str, Any],
        field_id: str,
        category_ids: List[int],
        stage_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Применить условие по категории и/или стадиям
        
        Логика:
        - Если указаны category_ids: фильтруем сущности из любой из указанных категорий (воронок)
        - Если указаны stage_ids: дополнительно фильтруем по стадиям (применяется ко всем выбранным воронкам)
        - Если stage_ids пустой: берем ВСЕ сделки из указанных категорий (все стадии)
        
        Args:
            entities: Список сущностей
            condition_config: Конфигурация условий
            field_id: ID поля (обычно CATEGORY_ID)
            category_ids: Список ID категорий для фильтрации (пустой список = все категории)
            stage_ids: Список ID стадий для фильтрации (пустой список = все стадии в категориях)
        """
        logger.info(f"Применение category_stage_condition: category_ids={category_ids}, stage_ids={stage_ids} (пустой = все стадии), entities_count={len(entities)}")
        
        # Преобразуем category_ids в множество строк для быстрого поиска
        category_ids_set = {str(cid) for cid in category_ids} if category_ids else None
        
        filtered = []
        for entity in entities:
            entity_category_id = entity.get('CATEGORY_ID')
            entity_stage_id = entity.get('STAGE_ID')
            
            # Фильтруем по категориям, если указаны
            if category_ids_set is not None:
                if str(entity_category_id) not in category_ids_set:
                    continue
            
            # Фильтруем по стадиям, если указаны
            # Если stage_ids пустой - НЕ фильтруем по стадиям (берем все стадии в категориях)
            if stage_ids:
                if not entity_stage_id or entity_stage_id not in stage_ids:
                    continue
            
            filtered.append(entity)
        
        stage_info = stage_ids if stage_ids else "все стадии"
        category_info = category_ids if category_ids else "все категории"
        logger.info(f"Фильтрация по category_stage_condition (category_ids={category_info}, stage_ids={stage_info}): {len(filtered)} из {len(entities)} сущностей")
        return filtered
    
    def _apply_combined_condition(
        self,
        entities: List[Dict[str, Any]],
        condition_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Применить комбинированное условие
        
        condition_config: {
            "logic": "AND|OR",
            "conditions": [
                {"type": "assigned_by_condition", ...},
                {"type": "field_condition", ...}
            ]
        }
        """
        logic = condition_config.get('logic', 'AND')
        conditions = condition_config.get('conditions', [])
        
        if not conditions:
            return entities
        
        if logic == 'AND':
            # Все условия должны выполняться
            result = entities
            for condition in conditions:
                condition_type = condition.get('type')
                if condition_type == 'assigned_by_condition':
                    result = self._apply_assigned_by_condition(result, condition)
                elif condition_type == 'field_condition':
                    result = self._apply_field_condition(result, condition)
            return result
        elif logic == 'OR':
            # Хотя бы одно условие должно выполняться
            result_set = set()
            for condition in conditions:
                condition_type = condition.get('type')
                if condition_type == 'assigned_by_condition':
                    filtered = self._apply_assigned_by_condition(entities, condition)
                elif condition_type == 'field_condition':
                    filtered = self._apply_field_condition(entities, condition)
                else:
                    continue
                
                for entity in filtered:
                    result_set.add(entity.get('ID'))
            
            return [e for e in entities if e.get('ID') in result_set]
        else:
            logger.warning(f"Неизвестная логика для combined: {logic}")
            return entities
