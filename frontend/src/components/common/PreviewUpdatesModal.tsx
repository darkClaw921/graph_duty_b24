import React, { useState, useMemo } from 'react';
import { Modal } from './Modal';
import { PreviewEntity } from '../../services/utilsApi';

interface PreviewUpdatesModalProps {
  isOpen: boolean;
  onClose: () => void;
  entities: PreviewEntity[];
  totalCount: number;
  date: string;
}

export const PreviewUpdatesModal: React.FC<PreviewUpdatesModalProps> = ({
  isOpen,
  onClose,
  entities,
  totalCount,
  date,
}) => {
  const [filterEntityType, setFilterEntityType] = useState<string>('all');
  const [filterRuleId, setFilterRuleId] = useState<number | 'all'>('all');
  const [expandedEntities, setExpandedEntities] = useState<Set<number>>(new Set());

  // Получаем уникальные типы сущностей и правила
  const entityTypes = useMemo(() => {
    const types = new Set(entities.map(e => e.entity_type));
    return Array.from(types);
  }, [entities]);

  const rules = useMemo(() => {
    const rulesMap = new Map<number, string>();
    entities.forEach(e => {
      if (!rulesMap.has(e.rule_id)) {
        rulesMap.set(e.rule_id, e.rule_name);
      }
    });
    return Array.from(rulesMap.entries()).map(([id, name]) => ({ id, name }));
  }, [entities]);

  // Фильтруем сущности
  const filteredEntities = useMemo(() => {
    return entities.filter(entity => {
      if (filterEntityType !== 'all' && entity.entity_type !== filterEntityType) {
        return false;
      }
      if (filterRuleId !== 'all' && entity.rule_id !== filterRuleId) {
        return false;
      }
      return true;
    });
  }, [entities, filterEntityType, filterRuleId]);

  const toggleExpand = (entityId: number) => {
    const newExpanded = new Set(expandedEntities);
    if (newExpanded.has(entityId)) {
      newExpanded.delete(entityId);
    } else {
      newExpanded.add(entityId);
    }
    setExpandedEntities(newExpanded);
  };

  const getEntityTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      deal: 'Сделка',
      contact: 'Контакт',
      company: 'Компания',
      lead: 'Лид',
    };
    return labels[type] || type;
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Предпросмотр обновлений на ${date}`}
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-600">
            Всего сущностей для обновления: <span className="font-semibold">{totalCount}</span>
          </p>
        </div>

        {/* Фильтры */}
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Тип сущности
            </label>
            <select
              value={filterEntityType}
              onChange={(e) => setFilterEntityType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">Все типы</option>
              {entityTypes.map(type => (
                <option key={type} value={type}>
                  {getEntityTypeLabel(type)}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Правило
            </label>
            <select
              value={filterRuleId}
              onChange={(e) => setFilterRuleId(e.target.value === 'all' ? 'all' : Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">Все правила</option>
              {rules.map(rule => (
                <option key={rule.id} value={rule.id}>
                  {rule.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Таблица сущностей */}
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <div className="max-h-[60vh] overflow-y-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Тип
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Правило
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Текущий ответственный
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Новый ответственный
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Связанные
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredEntities.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                      Нет сущностей для обновления
                    </td>
                  </tr>
                ) : (
                  filteredEntities.map((entity) => {
                    const isExpanded = expandedEntities.has(entity.entity_id);
                    const hasRelated = entity.related_entities && entity.related_entities.length > 0;
                    
                    return (
                      <React.Fragment key={`${entity.entity_type}-${entity.entity_id}`}>
                        <tr className="hover:bg-gray-50">
                          <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                            {entity.entity_id}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                            {getEntityTypeLabel(entity.entity_type)}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                            {entity.rule_name}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                            {entity.current_assigned_by_name || (entity.current_assigned_by_id ? `ID: ${entity.current_assigned_by_id}` : 'Не назначен')}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-blue-600">
                            {entity.new_assigned_by_name}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                            {hasRelated ? (
                              <button
                                onClick={() => toggleExpand(entity.entity_id)}
                                className="text-blue-600 hover:text-blue-800 font-medium"
                              >
                                {isExpanded ? 'Скрыть' : `Показать (${entity.related_entities!.length})`}
                              </button>
                            ) : (
                              '-'
                            )}
                          </td>
                        </tr>
                        {isExpanded && hasRelated && (
                          <tr className="bg-blue-50">
                            <td colSpan={6} className="px-4 py-3">
                              <div className="space-y-2">
                                <p className="text-sm font-medium text-gray-700 mb-2">
                                  Связанные сущности:
                                </p>
                                {entity.related_entities!.map((related, idx) => (
                                  <div
                                    key={`${related.entity_type}-${related.entity_id}-${idx}`}
                                    className="bg-white rounded border border-gray-200 p-2"
                                  >
                                    <div className="flex items-center gap-2 text-sm whitespace-nowrap">
                                      <span className="font-medium text-gray-900">
                                        {getEntityTypeLabel(related.entity_type)} #{related.entity_id}
                                      </span>
                                      <span className="text-gray-500">
                                        {related.current_assigned_by_name || (related.current_assigned_by_id ? `ID: ${related.current_assigned_by_id}` : 'Не назначен')}
                                      </span>
                                      <span className="text-gray-400">→</span>
                                      <span className="font-medium text-blue-600">
                                        {related.new_assigned_by_name}
                                      </span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 transition-colors"
          >
            Закрыть
          </button>
        </div>
      </div>
    </Modal>
  );
};
