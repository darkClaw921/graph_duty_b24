import React, { useEffect, useState, useMemo } from 'react';
import { historyApi } from '../services/historyApi';
import { UpdateHistory, UpdateHistoryFilters, UpdateSource } from '../types/history';
import { Input } from '../components/common/Input';
import { Button } from '../components/common/Button';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

const History: React.FC = () => {
  const [history, setHistory] = useState<UpdateHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [filters, setFilters] = useState<UpdateHistoryFilters>({
    skip: 0,
    limit: 50,
  });
  const [localFilters, setLocalFilters] = useState({
    entity_type: '',
    entity_id: '',
    start_date: '',
    end_date: '',
    update_source: '',
  });

  useEffect(() => {
    fetchHistory();
    fetchCount();
  }, [filters]);

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await historyApi.getAll(filters);
      setHistory(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка при загрузке истории');
    } finally {
      setLoading(false);
    }
  };

  const fetchCount = async () => {
    try {
      const countData = await historyApi.getCount({
        entity_type: filters.entity_type,
        entity_id: filters.entity_id,
        start_date: filters.start_date,
        end_date: filters.end_date,
        update_source: filters.update_source,
      });
      setTotalCount(countData.count);
    } catch (err) {
      console.error('Ошибка при получении количества:', err);
    }
  };

  const handleApplyFilters = () => {
    setFilters({
      skip: 0,
      limit: 50,
      entity_type: localFilters.entity_type || undefined,
      entity_id: localFilters.entity_id ? parseInt(localFilters.entity_id) : undefined,
      start_date: localFilters.start_date || undefined,
      end_date: localFilters.end_date || undefined,
      update_source: localFilters.update_source ? localFilters.update_source as UpdateSource : undefined,
    });
  };

  const handleResetFilters = () => {
    setLocalFilters({
      entity_type: '',
      entity_id: '',
      start_date: '',
      end_date: '',
      update_source: '',
    });
    setFilters({
      skip: 0,
      limit: 50,
    });
  };

  const handlePageChange = (newSkip: number) => {
    setFilters({ ...filters, skip: newSkip });
  };

  const getUpdateSourceLabel = (source: UpdateSource): string => {
    switch (source) {
      case UpdateSource.WEBHOOK:
        return 'Webhook';
      case UpdateSource.SCHEDULED:
        return 'Планировщик';
      case UpdateSource.MANUAL:
        return 'Вручную';
      default:
        return source;
    }
  };

  const getEntityTypeLabel = (type: string): string => {
    const labels: Record<string, string> = {
      deal: 'Сделка',
      contact: 'Контакт',
      company: 'Компания',
      lead: 'Лид',
    };
    return labels[type] || type;
  };

  const currentPage = Math.floor((filters.skip || 0) / (filters.limit || 50)) + 1;
  const totalPages = Math.ceil(totalCount / (filters.limit || 50));

  // Подсчитываем статистику по менеджерам (по полю "На кого")
  const managerStats = useMemo(() => {
    const stats = new Map<number, { name: string; count: number }>();
    
    history.forEach((item) => {
      const managerId = item.new_assigned_by_id;
      const managerName = item.new_user_name || `ID: ${managerId}`;
      
      if (stats.has(managerId)) {
        const existing = stats.get(managerId)!;
        stats.set(managerId, { ...existing, count: existing.count + 1 });
      } else {
        stats.set(managerId, { name: managerName, count: 1 });
      }
    });
    
    // Преобразуем в массив и сортируем по количеству (по убыванию)
    return Array.from(stats.entries())
      .map(([id, data]) => ({ id, ...data }))
      .sort((a, b) => b.count - a.count);
  }, [history]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-gray-900">История изменений</h2>
      </div>

      {/* Фильтры */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Фильтры</h3>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Тип сущности
            </label>
            <select
              value={localFilters.entity_type}
              onChange={(e) => setLocalFilters({ ...localFilters, entity_type: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Все</option>
              <option value="deal">Сделка</option>
              <option value="contact">Контакт</option>
              <option value="company">Компания</option>
              <option value="lead">Лид</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              ID сущности
            </label>
            <Input
              type="number"
              value={localFilters.entity_id}
              onChange={(e) => setLocalFilters({ ...localFilters, entity_id: e.target.value })}
              placeholder="ID сущности"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Дата начала
            </label>
            <Input
              type="date"
              value={localFilters.start_date}
              onChange={(e) => setLocalFilters({ ...localFilters, start_date: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Дата окончания
            </label>
            <Input
              type="date"
              value={localFilters.end_date}
              onChange={(e) => setLocalFilters({ ...localFilters, end_date: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Источник
            </label>
            <select
              value={localFilters.update_source}
              onChange={(e) => setLocalFilters({ ...localFilters, update_source: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Все</option>
              <option value={UpdateSource.WEBHOOK}>Webhook</option>
              <option value={UpdateSource.SCHEDULED}>Планировщик</option>
              <option value={UpdateSource.MANUAL}>Вручную</option>
            </select>
          </div>
        </div>
        <div className="flex gap-2 mt-4 items-start">
          <div className="flex gap-2">
            <Button onClick={handleApplyFilters}>Применить</Button>
            <Button onClick={handleResetFilters} variant="secondary">
              Сбросить
            </Button>
          </div>
          
          {/* Статистика по менеджерам */}
          {managerStats.length > 0 && (
            <div className="ml-auto flex flex-col gap-2 min-w-0 flex-1">
              <div className="text-sm font-semibold text-gray-700">
                Статистика по менеджерам (На кого):
                <span className="ml-2 text-xs font-normal text-gray-500">
                  (на текущей странице)
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {managerStats.map((stat) => (
                  <div
                    key={stat.id}
                    className="px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-md text-sm whitespace-nowrap"
                    title={`${stat.name}: ${stat.count} сущностей`}
                  >
                    <span className="font-medium text-gray-900">{stat.name}:</span>
                    <span className="ml-1 text-blue-700 font-semibold">{stat.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Таблица истории */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <p className="text-sm text-gray-600">
            Всего записей: {totalCount}
          </p>
        </div>
        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-6 text-center text-gray-500">Загрузка...</div>
          ) : history.length === 0 ? (
            <div className="p-6 text-center text-gray-500">История изменений пуста</div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Дата
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Тип сущности
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    ID сущности
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    От кого
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    На кого
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Источник
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Связанная сущность
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {history.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {format(new Date(item.created_at), 'dd.MM.yyyy HH:mm:ss', { locale: ru })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {getEntityTypeLabel(item.entity_type)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {item.entity_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {item.old_user_name || (item.old_assigned_by_id ? `ID: ${item.old_assigned_by_id}` : '—')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {item.new_user_name || `ID: ${item.new_assigned_by_id}`}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {getUpdateSourceLabel(item.update_source)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {item.related_entity_type && item.related_entity_id ? (
                        <span>
                          {getEntityTypeLabel(item.related_entity_type)} #{item.related_entity_id}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Пагинация */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
            <div className="text-sm text-gray-600">
              Страница {currentPage} из {totalPages}
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => handlePageChange(Math.max(0, (filters.skip || 0) - (filters.limit || 50)))}
                disabled={currentPage === 1}
                variant="secondary"
              >
                Назад
              </Button>
              <Button
                onClick={() => handlePageChange((filters.skip || 0) + (filters.limit || 50))}
                disabled={currentPage >= totalPages}
                variant="secondary"
              >
                Вперед
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default History;
