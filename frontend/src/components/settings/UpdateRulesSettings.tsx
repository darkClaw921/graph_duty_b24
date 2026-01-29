import React, { useEffect, useState } from 'react';
import { rulesApi } from '../../services/rulesApi';
import { settingsApi } from '../../services/settingsApi';
import { useUsersStore } from '../../store/usersStore';
import { UpdateRule, UpdateRuleCreate } from '../../types/rule';
import { EntityField } from '../../types/entity';
import { Button } from '../common/Button';
import { Modal } from '../common/Modal';

const STORAGE_KEY = 'updateRulesSettings_formState';

// Компонент для подсказки с иконкой вопроса
const HelpTooltip: React.FC<{ content: React.ReactNode }> = ({ content }) => {
  return (
    <div className="relative group">
      <svg
        className="w-4 h-4 text-gray-400 cursor-help"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <div className="absolute left-0 bottom-full mb-2 w-80 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
        <div className="space-y-2">
          {content}
        </div>
        <div className="absolute top-full left-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
      </div>
    </div>
  );
};

const UpdateRulesSettings: React.FC = () => {
  const [rules, setRules] = useState<UpdateRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<UpdateRule | null>(null);
  const { users, fetchUsers } = useUsersStore();
  const [entityFields, setEntityFields] = useState<EntityField | null>(null);
  const [loadingFields, setLoadingFields] = useState(false);
  const [fieldValues, setFieldValues] = useState<Array<{ id: string; name: string; semantics?: string }>>([]);
  const [loadingFieldValues, setLoadingFieldValues] = useState(false);
  const [selectedFieldData, setSelectedFieldData] = useState<{ type?: string; statusType?: string } | null>(null);
  const [categoryStages, setCategoryStages] = useState<Array<{ id: string; name: string; semantics?: string }>>([]);
  const [loadingCategoryStages, setLoadingCategoryStages] = useState(false);
  
  const [formData, setFormData] = useState<UpdateRuleCreate>({
    entity_type: '',
    entity_name: '',
    rule_type: 'assigned_by_condition',
    condition_config: {},
    priority: 0,
    enabled: true,
    update_time: '09:00',
    update_days: null,
    user_distributions: [],
    user_ids: [],
    update_related_contacts_companies: false,
  });

  const fetchRules = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await rulesApi.getAll();
      setRules(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки правил');
    } finally {
      setLoading(false);
    }
  };

  const entityTypes = [
    { value: 'deal', label: 'Сделки' },
    { value: 'contact', label: 'Контакты' },
    { value: 'company', label: 'Компании' },
    { value: 'lead', label: 'Лиды' },
  ];

  const weekDays = [
    { value: 1, label: 'Понедельник' },
    { value: 2, label: 'Вторник' },
    { value: 3, label: 'Среда' },
    { value: 4, label: 'Четверг' },
    { value: 5, label: 'Пятница' },
    { value: 6, label: 'Суббота' },
    { value: 7, label: 'Воскресенье' },
  ];

  const ruleTypeLabels: Record<string, string> = {
    'assigned_by_condition': 'По текущему ответственному',
    'field_condition': 'По полю',
    'combined': 'Комбинированное',
  };

  const getRuleTypeLabel = (ruleType: string): string => {
    return ruleTypeLabels[ruleType] || ruleType;
  };

  const fetchEntityFields = async (entityType: string) => {
    if (!entityType) {
      setEntityFields(null);
      return;
    }
    
    setLoadingFields(true);
    try {
      const data = await settingsApi.getEntityFieldsByType(entityType);
      setEntityFields(data.fields);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки полей');
      setEntityFields(null);
    } finally {
      setLoadingFields(false);
    }
  };

  const fetchFieldValues = async (entityType: string, fieldId: string, fieldsData?: EntityField | null) => {
    const fieldsToUse = fieldsData || entityFields;
    if (!entityType || !fieldId || !fieldsToUse) {
      setFieldValues([]);
      setSelectedFieldData(null);
      setCategoryStages([]);
      return;
    }
    
    const fieldData = fieldsToUse[fieldId];
    if (!fieldData) {
      setFieldValues([]);
      setSelectedFieldData(null);
      return;
    }
    
    setSelectedFieldData({
      type: fieldData.type,
      statusType: fieldData.statusType
    });
    
    // Для категорий загружаем список категорий
    if (fieldData.type === 'crm_category') {
      setLoadingFieldValues(true);
      try {
        const data = await settingsApi.getFieldValues(entityType, fieldId);
        setFieldValues(data.values);
        setCategoryStages([]);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Ошибка загрузки категорий');
        setFieldValues([]);
      } finally {
        setLoadingFieldValues(false);
      }
    }
    // Для статусов загружаем список статусов
    else if (fieldData.type === 'crm_status' && fieldData.statusType) {
      setLoadingFieldValues(true);
      try {
        const data = await settingsApi.getFieldValues(entityType, fieldId);
        setFieldValues(data.values);
        setCategoryStages([]);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Ошибка загрузки статусов');
        setFieldValues([]);
      } finally {
        setLoadingFieldValues(false);
      }
    } else {
      setFieldValues([]);
      setCategoryStages([]);
    }
  };

  const fetchMultipleCategoryStages = async (entityType: string, fieldId: string, categoryIds: number[]) => {
    if (!categoryIds || categoryIds.length === 0) {
      setCategoryStages([]);
      return;
    }
    
    setLoadingCategoryStages(true);
    try {
      // Загружаем стадии для всех выбранных воронок параллельно
      const stagePromises = categoryIds.map(categoryId => 
        settingsApi.getCategoryStages(entityType, fieldId, categoryId)
      );
      const stageResults = await Promise.all(stagePromises);
      
      // Объединяем все стадии, убирая дубликаты по ID
      const allStagesMap = new Map<string, { id: string; name: string; semantics?: string }>();
      stageResults.forEach(result => {
        result.values.forEach(stage => {
          if (!allStagesMap.has(stage.id)) {
            allStagesMap.set(stage.id, stage);
          }
        });
      });
      
      setCategoryStages(Array.from(allStagesMap.values()));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки стадий');
      setCategoryStages([]);
    } finally {
      setLoadingCategoryStages(false);
    }
  };

  // Флаг для отслеживания восстановления состояния
  const [isRestoring, setIsRestoring] = useState(false);

  // Восстановление состояния из sessionStorage при монтировании
  useEffect(() => {
    const savedState = sessionStorage.getItem(STORAGE_KEY);
    if (savedState) {
      try {
        const parsed = JSON.parse(savedState);
        if (parsed.formData && parsed.isModalOpen) {
          setFormData(parsed.formData);
          setIsModalOpen(true);
          setIsRestoring(true);
          
          // Восстанавливаем связанные данные если есть entity_type
          if (parsed.formData.entity_type) {
            if (parsed.formData.rule_type === 'field_condition') {
              const restoreFieldData = async () => {
                try {
                  // Загружаем поля сущности
                  const fieldsData = await settingsApi.getEntityFieldsByType(parsed.formData.entity_type);
                  setEntityFields(fieldsData.fields);
                  
                  // Загружаем значения полей если есть field_id
                  const fieldId = parsed.formData.condition_config?.field_id;
                  if (fieldId && fieldsData.fields) {
                    await fetchFieldValues(parsed.formData.entity_type, fieldId, fieldsData.fields);
                    
                    // Загружаем стадии если есть category_id или category_ids
                    const categoryId = parsed.formData.condition_config?.category_id;
                    const categoryIds = parsed.formData.condition_config?.category_ids || [];
                    let finalCategoryIds = categoryIds;
                    if (categoryId !== null && categoryId !== undefined && categoryIds.length === 0) {
                      finalCategoryIds = [categoryId];
                    }
                    if (finalCategoryIds && finalCategoryIds.length > 0 && fieldId) {
                      await fetchMultipleCategoryStages(parsed.formData.entity_type, fieldId, finalCategoryIds);
                    }
                  }
                } catch (err) {
                  // Игнорируем ошибки загрузки полей при восстановлении - пользователь может загрузить их вручную
                  console.warn('Не удалось восстановить поля сущности:', err);
                } finally {
                  setIsRestoring(false);
                }
              };
              restoreFieldData();
            } else {
              setIsRestoring(false);
            }
          } else {
            setIsRestoring(false);
          }
        }
      } catch (err) {
        console.error('Ошибка восстановления состояния формы:', err);
        sessionStorage.removeItem(STORAGE_KEY);
        setIsRestoring(false);
      }
    }
    
    fetchRules();
    fetchUsers();
  }, []);

  // Сохранение состояния формы в sessionStorage при изменении (только если не восстанавливаем)
  useEffect(() => {
    if (isModalOpen && !isRestoring) {
      const stateToSave = {
        formData,
        isModalOpen,
      };
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
    }
  }, [formData, isModalOpen, isRestoring]);

  const handleOpenModal = (rule?: UpdateRule) => {
    if (rule) {
      setEditingRule(rule);
      setFormData({
        entity_type: rule.entity_type,
        entity_name: rule.entity_name,
        rule_type: rule.rule_type,
        condition_config: rule.condition_config,
        priority: rule.priority,
        enabled: rule.enabled,
        update_time: rule.update_time,
        update_days: rule.update_days,
        user_distributions: rule.user_distributions || [],
        user_ids: rule.user_ids || [],
        update_related_contacts_companies: rule.update_related_contacts_companies || false,
      });
      if (rule.entity_type && rule.rule_type === 'field_condition') {
        const loadFieldData = async () => {
          try {
            // Загружаем поля сущности
            const fieldsData = await settingsApi.getEntityFieldsByType(rule.entity_type);
            setEntityFields(fieldsData.fields);
            
            const fieldId = (rule.condition_config as any)?.field_id;
            if (fieldId && fieldsData.fields) {
              await fetchFieldValues(rule.entity_type, fieldId, fieldsData.fields);
              
              // Обратная совместимость: преобразуем category_id в category_ids если нужно
              const categoryId = (rule.condition_config as any)?.category_id;
              const categoryIds = (rule.condition_config as any)?.category_ids || [];
              
              let finalCategoryIds = categoryIds;
              if (categoryId !== null && categoryId !== undefined && categoryIds.length === 0) {
                // Преобразуем старый формат в новый
                finalCategoryIds = [categoryId];
                setFormData(prev => ({
                  ...prev,
                  condition_config: {
                    ...prev.condition_config,
                    category_ids: finalCategoryIds,
                    category_id: undefined, // Удаляем старое поле
                  },
                }));
              }
              
              if (finalCategoryIds && finalCategoryIds.length > 0 && fieldId) {
                await fetchMultipleCategoryStages(rule.entity_type, fieldId, finalCategoryIds);
                // Конвертируем stage_id в stage_ids для обратной совместимости
                const stageId = (rule.condition_config as any)?.stage_id;
                if (stageId && !(rule.condition_config as any)?.stage_ids) {
                  setFormData(prev => ({
                    ...prev,
                    condition_config: {
                      ...prev.condition_config,
                      stage_ids: [stageId],
                      stage_id: undefined,
                    },
                  }));
                }
              }
            }
          } catch (err) {
            console.error('Ошибка загрузки данных полей:', err);
            setError(err instanceof Error ? err.message : 'Ошибка загрузки полей');
          }
        };
        loadFieldData();
      } else {
        setEntityFields(null);
        setFieldValues([]);
        setCategoryStages([]);
        setSelectedFieldData(null);
      }
    } else {
      setEditingRule(null);
      setFormData({
        entity_type: '',
        entity_name: '',
        rule_type: 'assigned_by_condition',
        condition_config: {},
        priority: 0,
        enabled: true,
        update_time: '09:00',
        update_days: null,
        user_distributions: [],
        user_ids: [],
        update_related_contacts_companies: false,
      });
      setEntityFields(null);
      setFieldValues([]);
      setCategoryStages([]);
      setSelectedFieldData(null);
    }
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    if (!formData.entity_type) {
      setError('Заполните тип сущности');
      return;
    }
    
    // Проверяем, что для типа правила "По полю" выбрано поле и значение
    if (formData.rule_type === 'field_condition') {
      const fieldId = (formData.condition_config as any)?.field_id;
      if (!fieldId) {
        setError('Выберите поле сущности для типа правила "По полю"');
        return;
      }
      
      // Для категорий проверяем, что выбрана хотя бы одна воронка (стадии опциональны)
      if (selectedFieldData?.type === 'crm_category') {
        const categoryIds = (formData.condition_config as any)?.category_ids || [];
        if (categoryIds.length === 0) {
          setError('Выберите хотя бы одну воронку для поля категории');
          return;
        }
        // Стадии не обязательны - если не выбраны, правило применяется ко всем выбранным воронкам
      }
      // Для статусов проверяем, что выбрано значение
      else if (selectedFieldData?.type === 'crm_status') {
        const statusId = (formData.condition_config as any)?.status_id;
        if (!statusId) {
          setError('Выберите значение статуса');
          return;
        }
      }
    }
    
    // Проверяем, что сумма процентов не превышает 100%
    const totalPercentage = getTotalDistributionPercentage();
    if (totalPercentage > 100) {
      setError(`Сумма процентов распределения (${totalPercentage}%) не может превышать 100%`);
      return;
    }
    
    // Автоматически генерируем название на основе типа сущности
    if (!formData.entity_name) {
      const entityTypeLabel = entityTypes.find(t => t.value === formData.entity_type)?.label || formData.entity_type;
      formData.entity_name = entityTypeLabel;
    }
    
    try {
      if (editingRule) {
        await rulesApi.update(editingRule.id, formData);
      } else {
        await rulesApi.create(formData);
      }
      await fetchRules();
      setIsModalOpen(false);
      setEditingRule(null);
      setError(null);
      // Очищаем сохраненное состояние после успешного сохранения
      sessionStorage.removeItem(STORAGE_KEY);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка сохранения правила');
    }
  };

  const handleDelete = async (id: number) => {
    if (confirm('Удалить правило?')) {
      try {
        await rulesApi.delete(id);
        await fetchRules();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Ошибка удаления правила');
      }
    }
  };

  const handleDayToggle = (day: number) => {
    setFormData((prev) => {
      const days = prev.update_days || [];
      if (days.includes(day)) {
        return { ...prev, update_days: days.filter((d) => d !== day).length > 0 ? days.filter((d) => d !== day) : null };
      } else {
        return { ...prev, update_days: [...days, day] };
      }
    });
  };

  const handleUserToggle = (userId: number) => {
    setFormData((prev) => {
      const distributions = prev.user_distributions || [];
      const existingIndex = distributions.findIndex(d => d.user_id === userId);
      
      if (existingIndex >= 0) {
        // Удаляем пользователя
        const newDistributions = distributions.filter(d => d.user_id !== userId);
        const newUserIds = (prev.user_ids || []).filter(id => id !== userId);
        return { 
          ...prev, 
          user_distributions: newDistributions,
          user_ids: newUserIds
        };
      } else {
        // Вычисляем максимально доступный процент для нового пользователя
        const currentTotal = distributions.reduce((sum, dist) => sum + dist.distribution_percentage, 0);
        const maxAvailable = Math.max(1, 100 - currentTotal);
        const defaultPercentage = Math.min(100, maxAvailable);
        
        // Добавляем пользователя с процентом по умолчанию (не превышающим доступный лимит)
        const newDistributions = [...distributions, { user_id: userId, distribution_percentage: defaultPercentage }];
        const newUserIds = [...(prev.user_ids || []), userId];
        return { 
          ...prev, 
          user_distributions: newDistributions,
          user_ids: newUserIds
        };
      }
    });
  };

  const handleDistributionPercentageChange = (userId: number, percentage: number) => {
    setFormData((prev) => {
      const distributions = prev.user_distributions || [];
      const existingIndex = distributions.findIndex(d => d.user_id === userId);
      
      // Вычисляем максимально доступный процент
      const otherUsersTotal = distributions
        .filter(d => d.user_id !== userId)
        .reduce((sum, dist) => sum + dist.distribution_percentage, 0);
      const maxAvailable = 100 - otherUsersTotal;
      
      // Ограничиваем процент максимально доступным значением
      const clampedPercentage = Math.max(1, Math.min(percentage, maxAvailable));
      
      if (existingIndex >= 0) {
        // Обновляем процент для существующего пользователя
        const newDistributions = [...distributions];
        newDistributions[existingIndex] = { ...newDistributions[existingIndex], distribution_percentage: clampedPercentage };
        return { ...prev, user_distributions: newDistributions };
      } else {
        // Добавляем пользователя с указанным процентом
        const newDistributions = [...distributions, { user_id: userId, distribution_percentage: clampedPercentage }];
        const newUserIds = [...(prev.user_ids || []), userId];
        return { 
          ...prev, 
          user_distributions: newDistributions,
          user_ids: newUserIds
        };
      }
    });
  };

  const getUserDistributionPercentage = (userId: number): number => {
    const distribution = formData.user_distributions?.find(d => d.user_id === userId);
    return distribution?.distribution_percentage || 100;
  };

  const getTotalDistributionPercentage = (): number => {
    return formData.user_distributions?.reduce((sum, dist) => sum + dist.distribution_percentage, 0) || 0;
  };

  const getMaxDistributionPercentage = (userId: number): number => {
    const otherUsersTotal = formData.user_distributions
      ?.filter(d => d.user_id !== userId)
      .reduce((sum, dist) => sum + dist.distribution_percentage, 0) || 0;
    const maxAvailable = 100 - otherUsersTotal;
    return Math.max(1, Math.min(100, maxAvailable));
  };

  const handleDistributeEvenly = () => {
    const selectedUserIds = formData.user_ids || [];
    if (selectedUserIds.length === 0) {
      return;
    }
    
    // Вычисляем равномерное распределение
    const basePercentage = Math.floor(100 / selectedUserIds.length);
    const remainder = 100 % selectedUserIds.length;
    
    // Распределяем проценты равномерно, остаток добавляем к первым пользователям
    const newDistributions = selectedUserIds.map((userId, index) => {
      const percentage = basePercentage + (index < remainder ? 1 : 0);
      return { user_id: userId, distribution_percentage: percentage };
    });
    
    setFormData({
      ...formData,
      user_distributions: newDistributions,
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900">Правила обновления сущностей</h3>
        <Button onClick={() => handleOpenModal()}>Добавить правило</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm">Загрузка...</p>
      ) : rules.length === 0 ? (
        <p className="text-gray-500 text-sm">Нет правил</p>
      ) : (
        <div className="space-y-4">
          {rules.map((rule) => (
            <div
              key={rule.id}
              className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h4 className="text-lg font-semibold text-gray-900">{rule.entity_name}</h4>
                    <span className="text-sm text-gray-500">({rule.entity_type})</span>
                    <span
                      className={`px-2 py-1 text-xs font-semibold rounded-full ${
                        rule.enabled
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {rule.enabled ? 'Включено' : 'Отключено'}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 space-y-1">
                    <p>Время обновления: {rule.update_time} (MSK)</p>
                    <p>
                      Дни недели:{' '}
                      {rule.update_days && rule.update_days.length > 0
                        ? rule.update_days
                            .sort()
                            .map((d) => weekDays.find((wd) => wd.value === d)?.label)
                            .join(', ')
                        : 'Ежедневно'}
                    </p>
                    <p>Тип правила: {getRuleTypeLabel(rule.rule_type)}</p>
                    <p>
                      Пользователи и распределение:{' '}
                      {rule.user_distributions && rule.user_distributions.length > 0
                        ? rule.user_distributions
                            .map((dist) => {
                              const user = users.find((u) => u.id === dist.user_id);
                              const userName = user ? `${user.name || ''} ${user.last_name || ''}`.trim() : `ID: ${dist.user_id}`;
                              return `${userName} (${dist.distribution_percentage}%)`;
                            })
                            .join(', ')
                        : rule.user_ids && rule.user_ids.length > 0
                        ? rule.user_ids
                            .map((uid) => {
                              const user = users.find((u) => u.id === uid);
                              return user ? `${user.name || ''} ${user.last_name || ''}`.trim() : `ID: ${uid}`;
                            })
                            .join(', ')
                        : 'Не указаны'}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => handleOpenModal(rule)}>
                    Редактировать
                  </Button>
                  <Button variant="danger" onClick={() => handleDelete(rule.id)}>
                    Удалить
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingRule(null);
          setError(null);
          // Очищаем сохраненное состояние при закрытии модального окна
          sessionStorage.removeItem(STORAGE_KEY);
        }}
        title={editingRule ? 'Редактировать правило' : 'Добавить правило'}
      >
        <div className="space-y-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Тип сущности
              </label>
              <HelpTooltip
                content={
                  <div className="space-y-2">
                    <p className="font-semibold mb-2">Тип сущности:</p>
                    <p>
                      Выберите тип сущности Bitrix24, к которой будет применяться правило обновления ответственного. 
                      Доступны: Сделки, Контакты, Компании, Лиды.
                    </p>
                    <p className="mt-2 text-gray-300">
                      После создания правила тип сущности нельзя изменить.
                    </p>
                  </div>
                }
              />
            </div>
            <select
              value={formData.entity_type}
              onChange={(e) => {
                const entityType = e.target.value;
                const entityTypeLabel = entityTypes.find(t => t.value === entityType)?.label || entityType;
                setFormData({ ...formData, entity_type: entityType, entity_name: entityTypeLabel, condition_config: {} });
                setEntityFields(null);
                if (entityType && formData.rule_type === 'field_condition') {
                  fetchEntityFields(entityType);
                }
              }}
              disabled={!!editingRule}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Выберите тип</option>
              {entityTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Время обновления
              </label>
              <HelpTooltip
                content={
                  <div className="space-y-2">
                    <p className="font-semibold mb-2">Время обновления:</p>
                    <p>
                      Укажите время суток, когда должно происходить автоматическое обновление ответственного 
                      для сущностей, соответствующих условиям правила.
                    </p>
                    <p className="mt-2 font-semibold">
                      ⏰ Время указывается в московском часовом поясе (MSK, UTC+3).
                    </p>
                    <p className="mt-2">
                      Обновление выполняется по расписанию согласно настройкам системы.
                    </p>
                  </div>
                }
              />
            </div>
            <div className="relative">
              <input
                type="time"
                value={formData.update_time}
                onChange={(e) => setFormData({ ...formData, update_time: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-500 pointer-events-none">
                MSK
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Время указывается в московском часовом поясе (MSK, UTC+3)
            </p>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Дни недели
              </label>
              <HelpTooltip
                content={
                  <div className="space-y-2">
                    <p className="font-semibold mb-2">Дни недели:</p>
                    <p>
                      Выберите дни недели, когда должно выполняться обновление ответственного. 
                      Если не выбрано ни одного дня, правило будет применяться ежедневно.
                    </p>
                    <p className="mt-2">
                      Например, можно настроить обновление только в рабочие дни (понедельник-пятница).
                    </p>
                  </div>
                }
              />
            </div>
            <p className="text-xs text-gray-500 mb-2">Оставьте пустым для ежедневного обновления</p>
            <div className="flex flex-wrap gap-2">
              {weekDays.map((day) => (
                <button
                  key={day.value}
                  type="button"
                  onClick={() => handleDayToggle(day.value)}
                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                    formData.update_days?.includes(day.value)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  {day.label}
                </button>
              ))}
            </div>
            {formData.update_days && formData.update_days.length > 0 && (
              <button
                type="button"
                onClick={() => setFormData({ ...formData, update_days: null })}
                className="mt-2 text-sm text-blue-600 hover:text-blue-800"
              >
                Сбросить (ежедневно)
              </button>
            )}
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Пользователи и процент распределения
                  </label>
                  <HelpTooltip
                    content={
                      <div className="space-y-2">
                        <p className="font-semibold mb-2">Как работает процент распределения:</p>
                        <p>
                          Проценты определяют вероятность назначения ответственного из списка пользователей правила. 
                          Например, если у пользователя А - 60%, а у пользователя Б - 40%, то в 60% случаев будет назначен А, в 40% - Б.
                        </p>
                        <p className="font-semibold mt-3 mb-2">Если в правиле больше пользователей, чем в смене:</p>
                        <p>
                          Система использует только тех пользователей из правила, которые есть в текущей смене дежурства. 
                          Проценты пересчитываются пропорционально между доступными пользователями. 
                          Например, если в правиле 10 пользователей (по 10% каждый), а в смене только 2 из них, 
                          то эти 2 пользователя получат по 50% каждый.
                        </p>
                      </div>
                    }
                  />
                </div>
                {(formData.user_ids && formData.user_ids.length > 0) && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleDistributeEvenly}
                    title="Равномерно распределить проценты между выбранными пользователями"
                  >
                    Распределить равномерно
                  </Button>
                )}
              </div>
              <span className={`text-xs font-medium ${
                getTotalDistributionPercentage() > 100 
                  ? 'text-red-600' 
                  : getTotalDistributionPercentage() === 100 
                    ? 'text-green-600' 
                    : 'text-gray-500'
              }`}>
                Всего: {getTotalDistributionPercentage()}%
              </span>
            </div>
            <div className="max-h-48 overflow-y-auto border border-gray-300 rounded-md p-2">
              {users.filter(user => user.active).length === 0 ? (
                <p className="text-sm text-gray-500">Нет активных пользователей</p>
              ) : (
                <div className="space-y-3">
                  {users.filter(user => user.active).map((user) => {
                    const isSelected = formData.user_ids?.includes(user.id) || false;
                    return (
                      <div
                        key={user.id}
                        className={`p-3 rounded border ${isSelected ? 'border-blue-300 bg-blue-50' : 'border-gray-200'}`}
                      >
                        <div className="flex items-center gap-3">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleUserToggle(user.id)}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded flex-shrink-0"
                          />
                          <span className="text-sm text-gray-900 flex-1 min-w-0">
                            {[user.name, user.last_name].filter(Boolean).join(' ') || user.email || `ID: ${user.id}`}
                          </span>
                          {isSelected && (() => {
                            const currentPercentage = getUserDistributionPercentage(user.id);
                            const maxPercentage = getMaxDistributionPercentage(user.id);
                            // Вычисляем процент заполнения относительно максимального доступного значения
                            const fillPercentage = maxPercentage > 0 ? (currentPercentage / maxPercentage) * 100 : 0;
                            
                            return (
                              <div className="flex items-center gap-3 flex-shrink-0">
                                <input
                                  type="range"
                                  min="1"
                                  max={maxPercentage}
                                  value={currentPercentage}
                                  onChange={(e) => handleDistributionPercentageChange(user.id, Number(e.target.value))}
                                  className="w-32 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                                  style={{
                                    background: `linear-gradient(to right, rgb(37, 99, 235) 0%, rgb(37, 99, 235) ${fillPercentage}%, rgb(229, 231, 235) ${fillPercentage}%, rgb(229, 231, 235) 100%)`
                                  }}
                                />
                                <span className={`text-sm font-semibold min-w-[2.5rem] text-right ${
                                  getTotalDistributionPercentage() > 100 
                                    ? 'text-red-600' 
                                    : getTotalDistributionPercentage() === 100 
                                      ? 'text-green-600' 
                                      : 'text-blue-600'
                                }`}>
                                  {currentPercentage}%
                                </span>
                              </div>
                            );
                          })()}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Чекбокс для обновления связанных контактов и компаний (только для сделок) */}
          {formData.entity_type === 'deal' && (
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="update_related_contacts_companies"
                checked={formData.update_related_contacts_companies || false}
                onChange={(e) => setFormData({ ...formData, update_related_contacts_companies: e.target.checked })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <div className="flex items-center gap-2 flex-1">
                <label htmlFor="update_related_contacts_companies" className="text-sm font-medium text-gray-700 cursor-pointer">
                  Обновлять также связанные контакты и компании привязанные к сделке
                </label>
                <HelpTooltip
                  content={
                    <div className="space-y-2">
                      <p className="font-semibold mb-2">Обновление связанных сущностей:</p>
                      <p>
                        При включении этой опции, при обновлении ответственного на сделке, 
                        также будет обновляться ответственный на связанных с этой сделкой контактах и компаниях.
                      </p>
                      <p className="mt-2">
                        Это позволяет синхронизировать ответственных между связанными сущностями автоматически.
                      </p>
                    </div>
                  }
                />
              </div>
            </div>
          )}

          <div>
            <div className="flex items-center gap-2 mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Тип правила
              </label>
              <HelpTooltip
                content={
                  <div className="space-y-2">
                    <p className="font-semibold mb-2">Типы правил:</p>
                    <div className="space-y-2">
                      <p>
                        <span className="font-semibold">По текущему ответственному</span> - правило применяется к сущностям, где текущий ответственный соответствует условиям распределения пользователей в правиле. (В разработке)
                      </p>
                      <p>
                        <span className="font-semibold">По полю</span> - правило применяется к сущностям, у которых выбранное поле имеет указанное значение (например, воронка, стадия, статус).
                      </p>
                      <p>
                        <span className="font-semibold">Комбинированное</span> - правило применяется при выполнении нескольких условий одновременно (например, по текущему ответственному И по полю). (В разработке)
                      </p>
                    </div>
                  </div>
                }
              />
            </div>
            <select
              value={formData.rule_type}
              onChange={(e) => {
                const newRuleType = e.target.value as UpdateRuleCreate['rule_type'];
                setFormData({
                  ...formData,
                  rule_type: newRuleType,
                  condition_config: {},
                });
                if (newRuleType === 'field_condition' && formData.entity_type) {
                  fetchEntityFields(formData.entity_type);
                } else {
                  setEntityFields(null);
                }
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="assigned_by_condition">По текущему ответственному</option>
              <option value="field_condition">По полю</option>
              <option value="combined">Комбинированное</option>
            </select>
          </div>

          {formData.rule_type === 'field_condition' && (
            <>
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Поле сущности
                  </label>
                  <HelpTooltip
                    content={
                      <div className="space-y-2">
                        <p className="font-semibold mb-2">Поле сущности:</p>
                        <p>
                          Выберите поле сущности, по значению которого будет определяться применение правила. 
                          Доступны поля типа воронка (crm_category), статус (crm_status) и другие.
                        </p>
                        <p className="mt-2">
                          После выбора поля станут доступны дополнительные настройки для выбора конкретных значений.
                        </p>
                      </div>
                    }
                  />
                </div>
                {loadingFields ? (
                  <p className="text-sm text-gray-500">Загрузка полей...</p>
                ) : entityFields ? (
                  <select
                    value={(formData.condition_config as any)?.field_id || ''}
                    onChange={(e) => {
                      const fieldId = e.target.value;
                      const newConfig: any = { field_id: fieldId };
                      setFormData({
                        ...formData,
                        condition_config: newConfig,
                      });
                      if (fieldId && formData.entity_type) {
                        fetchFieldValues(formData.entity_type, fieldId);
                      } else {
                        setFieldValues([]);
                        setCategoryStages([]);
                        setSelectedFieldData(null);
                      }
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Выберите поле</option>
                    {Object.entries(entityFields).map(([fieldId, fieldData]) => (
                      <option key={fieldId} value={fieldId}>
                        {fieldData.listLabel || fieldData.title || fieldId}
                      </option>
                    ))}
                  </select>
                ) : formData.entity_type ? (
                  <p className="text-sm text-gray-500">Выберите тип сущности для загрузки полей</p>
                ) : (
                  <p className="text-sm text-gray-500">Сначала выберите тип сущности</p>
                )}
              </div>

              {/* Выбор категорий (воронок) для полей типа crm_category - множественный выбор */}
              {selectedFieldData?.type === 'crm_category' && (formData.condition_config as any)?.field_id && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Воронки
                    </label>
                    <HelpTooltip
                      content={
                        <div className="space-y-2">
                          <p className="font-semibold mb-2">Воронки:</p>
                          <p>
                            Выберите одну или несколько воронок продаж, к сделкам которых будет применяться правило. 
                            Можно выбрать несколько воронок одновременно.
                          </p>
                          <p className="mt-2">
                            После выбора воронок станут доступны стадии сделок для более точной настройки правила.
                          </p>
                        </div>
                      }
                    />
                  </div>
                  <p className="text-xs text-gray-500 mb-2">Можно выбрать несколько</p>
                  {loadingFieldValues ? (
                    <p className="text-sm text-gray-500">Загрузка воронок...</p>
                  ) : fieldValues.length > 0 ? (
                    <div className="max-h-48 overflow-y-auto border border-gray-300 rounded-md p-3 space-y-2">
                      {fieldValues.map((value) => {
                        const categoryIds = (formData.condition_config as any)?.category_ids || [];
                        const isSelected = categoryIds.includes(Number(value.id));
                        return (
                          <label
                            key={value.id}
                            className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-2 rounded"
                          >
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => {
                                const fieldId = (formData.condition_config as any)?.field_id;
                                const currentCategoryIds = (formData.condition_config as any)?.category_ids || [];
                                let newCategoryIds: number[];
                                
                                if (e.target.checked) {
                                  newCategoryIds = [...currentCategoryIds, Number(value.id)];
                                } else {
                                  newCategoryIds = currentCategoryIds.filter((id: number) => id !== Number(value.id));
                                }
                                
                                setFormData({
                                  ...formData,
                                  condition_config: {
                                    ...formData.condition_config,
                                    category_ids: newCategoryIds.length > 0 ? newCategoryIds : undefined,
                                    category_id: undefined, // Удаляем старое поле для обратной совместимости
                                    stage_ids: undefined, // Сбрасываем стадии при изменении воронок
                                    stage_id: undefined, // Для обратной совместимости
                                  },
                                });
                                
                                // Загружаем стадии для всех выбранных воронок
                                if (newCategoryIds.length > 0 && fieldId && formData.entity_type) {
                                  fetchMultipleCategoryStages(formData.entity_type, fieldId, newCategoryIds);
                                } else {
                                  setCategoryStages([]);
                                }
                              }}
                              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            />
                            <span className="text-sm text-gray-900 flex-1">
                              {value.name}
                            </span>
                          </label>
                        );
                      })}
                      {(formData.condition_config as any)?.category_ids && 
                       Array.isArray((formData.condition_config as any)?.category_ids) &&
                       (formData.condition_config as any)?.category_ids.length > 0 && (
                        <button
                          type="button"
                          onClick={() => {
                            setFormData({
                              ...formData,
                              condition_config: {
                                ...formData.condition_config,
                                category_ids: undefined,
                                category_id: undefined,
                                stage_ids: undefined,
                                stage_id: undefined,
                              },
                            });
                            setCategoryStages([]);
                          }}
                          className="mt-2 text-sm text-blue-600 hover:text-blue-800"
                        >
                          Сбросить выбор воронок
                        </button>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">Нет доступных воронок</p>
                  )}
                </div>
              )}

              {/* Выбор стадий для категорий (множественный выбор) */}
              {selectedFieldData?.type === 'crm_category' && (formData.condition_config as any)?.category_ids && Array.isArray((formData.condition_config as any)?.category_ids) && (formData.condition_config as any)?.category_ids.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Стадии сделки
                    </label>
                    <HelpTooltip
                      content={
                        <div className="space-y-2">
                          <p className="font-semibold mb-2">Стадии сделки:</p>
                          <p>
                            Выберите конкретные стадии сделок, к которым будет применяться правило. 
                            Можно выбрать несколько стадий одновременно.
                          </p>
                          <p className="mt-2">
                            Если стадии не выбраны, правило будет применяться ко всем стадиям выбранных воронок. 
                            Это позволяет настроить правило как для конкретных стадий, так и для всех стадий воронки.
                          </p>
                        </div>
                      }
                    />
                  </div>
                  <p className="text-xs text-gray-500 mb-2">Необязательно - если не выбраны, правило применяется ко всем выбранным воронкам</p>
                  {loadingCategoryStages ? (
                    <p className="text-sm text-gray-500">Загрузка стадий...</p>
                  ) : categoryStages.length > 0 ? (
                    <div className="max-h-48 overflow-y-auto border border-gray-300 rounded-md p-3 space-y-2">
                      {categoryStages.map((stage) => {
                        const stageIds = (formData.condition_config as any)?.stage_ids || [];
                        const isSelected = Array.isArray(stageIds) && stageIds.includes(stage.id);
                        return (
                          <label
                            key={stage.id}
                            className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-2 rounded"
                          >
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => {
                                const currentStageIds = (formData.condition_config as any)?.stage_ids || [];
                                let newStageIds: string[];
                                if (e.target.checked) {
                                  newStageIds = [...currentStageIds, stage.id];
                                } else {
                                  newStageIds = currentStageIds.filter((id: string) => id !== stage.id);
                                }
                                setFormData({
                                  ...formData,
                                  condition_config: {
                                    ...formData.condition_config,
                                    stage_ids: newStageIds.length > 0 ? newStageIds : undefined,
                                  },
                                });
                              }}
                              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            />
                            <span className="text-sm text-gray-900 flex-1">
                              {stage.name}
                            </span>
                          </label>
                        );
                      })}
                      {(formData.condition_config as any)?.stage_ids && 
                       Array.isArray((formData.condition_config as any)?.stage_ids) &&
                       (formData.condition_config as any)?.stage_ids.length > 0 && (
                        <button
                          type="button"
                          onClick={() => {
                            setFormData({
                              ...formData,
                              condition_config: {
                                ...formData.condition_config,
                                stage_ids: undefined,
                              },
                            });
                          }}
                          className="mt-2 text-sm text-blue-600 hover:text-blue-800"
                        >
                          Сбросить выбор (применить ко всем выбранным воронкам)
                        </button>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">Нет доступных стадий</p>
                  )}
                </div>
              )}

              {/* Выбор значения для полей типа crm_status */}
              {selectedFieldData?.type === 'crm_status' && (formData.condition_config as any)?.field_id && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Значение статуса
                    </label>
                    <HelpTooltip
                      content={
                        <div className="space-y-2">
                          <p className="font-semibold mb-2">Значение статуса:</p>
                          <p>
                            Выберите конкретное значение статуса, при котором будет применяться правило. 
                            Правило будет применяться только к сущностям с выбранным статусом.
                          </p>
                          <p className="mt-2">
                            Это позволяет настроить разные правила для разных статусов сущностей.
                          </p>
                        </div>
                      }
                    />
                  </div>
                  {loadingFieldValues ? (
                    <p className="text-sm text-gray-500">Загрузка статусов...</p>
                  ) : fieldValues.length > 0 ? (
                    <select
                      value={(formData.condition_config as any)?.status_id || ''}
                      onChange={(e) => {
                        const statusId = e.target.value || null;
                        setFormData({
                          ...formData,
                          condition_config: {
                            ...formData.condition_config,
                            status_id: statusId,
                          },
                        });
                      }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Выберите значение</option>
                      {fieldValues.map((value) => (
                        <option key={value.id} value={value.id}>
                          {value.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <p className="text-sm text-gray-500">Нет доступных значений</p>
                  )}
                </div>
              )}
            </>
          )}

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="rule-enabled"
              checked={formData.enabled}
              onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <div className="flex items-center gap-2 flex-1">
              <label htmlFor="rule-enabled" className="block text-sm text-gray-900 cursor-pointer">
                Включено
              </label>
              <HelpTooltip
                content={
                  <div className="space-y-2">
                    <p className="font-semibold mb-2">Включено:</p>
                    <p>
                      Определяет, активно ли правило. Только включенные правила применяются при обновлении ответственных.
                    </p>
                    <p className="mt-2">
                      Отключенные правила сохраняются, но не выполняются. Это позволяет временно отключить правило без его удаления.
                    </p>
                  </div>
                }
              />
            </div>
          </div>

          <div className="flex gap-2 justify-end">
            <Button
              variant="secondary"
              onClick={() => {
                setIsModalOpen(false);
                setEditingRule(null);
                setError(null);
                // Очищаем сохраненное состояние при отмене
                sessionStorage.removeItem(STORAGE_KEY);
              }}
            >
              Отмена
            </Button>
            <Button onClick={handleSave}>Сохранить</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default UpdateRulesSettings;
