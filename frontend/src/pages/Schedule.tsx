import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useScheduleStore } from '../store/scheduleStore';
import { useUsersStore } from '../store/usersStore';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay, parseISO } from 'date-fns';
import ru from 'date-fns/locale/ru';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { Input } from '../components/common/Input';
import { PreviewUpdatesModal } from '../components/common/PreviewUpdatesModal';
import { utilsApi, UpdateProgress, PreviewEntity } from '../services/utilsApi';

const Schedule: React.FC = () => {
  const { schedules, fetchSchedules, createSchedule, updateSchedule, deleteSchedule, generateSchedule, loading } = useScheduleStore();
  const { users, fetchUsers } = useUsersStore();
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<number | ''>('');
  const [generateYear, setGenerateYear] = useState(new Date().getFullYear());
  const [generateMonth, setGenerateMonth] = useState(new Date().getMonth() + 1);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const [updateProgress, setUpdateProgress] = useState<{
    isUpdating: boolean;
    totalCount: number;
    currentCount: number;
    currentRule?: string;
    status?: string;
  } | null>(null);
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);
  const [previewEntities, setPreviewEntities] = useState<PreviewEntity[]>([]);
  const [previewTotalCount, setPreviewTotalCount] = useState(0);
  const [previewDate, setPreviewDate] = useState('');
  const [loadingPreview, setLoadingPreview] = useState(false);
  const lastProgressRef = useRef<{ currentCount: number; timestamp: number } | null>(null);

  useEffect(() => {
    const start = format(startOfMonth(currentMonth), 'yyyy-MM-dd');
    const end = format(endOfMonth(currentMonth), 'yyyy-MM-dd');
    const loadData = async () => {
      await fetchSchedules(start, end);
      await fetchUsers();
      setLastUpdateTime(new Date());
    };
    loadData();
  }, [currentMonth, fetchSchedules, fetchUsers]);

  const monthStart = startOfMonth(currentMonth);
  const monthEnd = endOfMonth(currentMonth);
  const days = eachDayOfInterval({ start: monthStart, end: monthEnd });

  // Получаем активных пользователей
  const activeUsers = useMemo(() => {
    return users.filter((u) => u.active).sort((a, b) => {
      const nameA = [a.name, a.last_name].filter(Boolean).join(' ') || a.email || '';
      const nameB = [b.name, b.last_name].filter(Boolean).join(' ') || b.email || '';
      return nameA.localeCompare(nameB);
    });
  }, [users]);

  // Получаем дежурство для конкретной даты
  const getScheduleForDate = (date: Date) => {
    return schedules.find((s) => isSameDay(parseISO(s.date), date));
  };

  // Проверяем, есть ли пользователь в дежурстве на дату
  const isUserOnDuty = (userId: number, date: Date) => {
    const schedule = getScheduleForDate(date);
    return schedule?.users.some(u => u.user_id === userId) || false;
  };

  // Получаем список пользователей на дежурстве на дату
  const getUsersOnDuty = (date: Date) => {
    const schedule = getScheduleForDate(date);
    return schedule?.users || [];
  };

  // Подсчет дней дежурства для пользователя
  const getDutyDaysCount = (userId: number) => {
    return schedules.filter((s) => {
      const scheduleDate = parseISO(s.date);
      return s.users.some(u => u.user_id === userId) && 
             scheduleDate >= monthStart && 
             scheduleDate <= monthEnd;
    }).length;
  };

  const handleCellClick = async (date: Date, userId: number) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    const schedule = getScheduleForDate(date);
      const start = format(startOfMonth(currentMonth), 'yyyy-MM-dd');
      const end = format(endOfMonth(currentMonth), 'yyyy-MM-dd');
      
    try {
      const currentUserIds = schedule?.users.map(u => u.user_id) || [];
      const isUserInDuty = currentUserIds.includes(userId);
      
      if (isUserInDuty) {
        // Убираем пользователя из дежурства
        const newUserIds = currentUserIds.filter(id => id !== userId);
        if (newUserIds.length === 0) {
          // Если больше нет пользователей - удаляем запись
          if (schedule && confirm(`Убрать всех пользователей с дежурства на ${format(date, 'd MMMM yyyy', { locale: ru })}?`)) {
            await deleteSchedule(schedule.id, start, end);
            setLastUpdateTime(new Date());
          }
        } else {
          // Обновляем список пользователей
          if (schedule) {
            await updateSchedule(schedule.id, { user_ids: newUserIds }, start, end);
            setLastUpdateTime(new Date());
          }
        }
      } else {
        // Добавляем пользователя к дежурству
        const newUserIds = [...currentUserIds, userId];
        if (schedule) {
          await updateSchedule(schedule.id, { user_ids: newUserIds }, start, end);
          setLastUpdateTime(new Date());
        } else {
          await createSchedule({ date: dateStr, user_ids: [userId] }, start, end);
          setLastUpdateTime(new Date());
        }
      }
    } catch (error) {
      console.error('Ошибка при обновлении дежурства:', error);
    }
  };

  const handleSave = async () => {
    if (!selectedDate || !selectedUserId) return;

    const start = format(startOfMonth(currentMonth), 'yyyy-MM-dd');
    const end = format(endOfMonth(currentMonth), 'yyyy-MM-dd');

    try {
      const existingSchedule = schedules.find((s) => s.date === selectedDate);
      const currentUserIds = existingSchedule?.users.map(u => u.user_id) || [];
      const userId = Number(selectedUserId);
      
      // Добавляем пользователя, если его еще нет
      if (!currentUserIds.includes(userId)) {
        const newUserIds = [...currentUserIds, userId];
        if (existingSchedule) {
          await updateSchedule(existingSchedule.id, { user_ids: newUserIds }, start, end);
        } else {
          await createSchedule({ date: selectedDate, user_ids: [userId] }, start, end);
        }
        setLastUpdateTime(new Date());
      }
      
      setIsModalOpen(false);
      setSelectedDate(null);
      setSelectedUserId('');
    } catch (error) {
      console.error('Ошибка сохранения:', error);
    }
  };

  const handleDelete = async () => {
    if (!selectedDate) return;
    const schedule = schedules.find((s) => s.date === selectedDate);
    if (schedule) {
      const start = format(startOfMonth(currentMonth), 'yyyy-MM-dd');
      const end = format(endOfMonth(currentMonth), 'yyyy-MM-dd');
      if (confirm('Удалить запись дежурства?')) {
        await deleteSchedule(schedule.id, start, end);
        setLastUpdateTime(new Date());
        setIsModalOpen(false);
        setSelectedDate(null);
      }
    }
  };

  const handleGenerate = async () => {
    if (confirm(`Сгенерировать график на ${generateMonth}/${generateYear}? Существующие записи будут перезаписаны.`)) {
      await generateSchedule(generateYear, generateMonth);
      setLastUpdateTime(new Date());
    }
  };

  const handleRefresh = async () => {
    const start = format(startOfMonth(currentMonth), 'yyyy-MM-dd');
    const end = format(endOfMonth(currentMonth), 'yyyy-MM-dd');
    await fetchSchedules(start, end);
    await fetchUsers();
    setLastUpdateTime(new Date());
  };

  const handlePreviewUpdates = async () => {
    try {
      setLoadingPreview(true);
      const today = format(new Date(), 'yyyy-MM-dd');
      const previewData = await utilsApi.getPreviewUpdates(today);
      setPreviewEntities(previewData.entities);
      setPreviewTotalCount(previewData.total_count);
      setPreviewDate(previewData.date);
      setIsPreviewModalOpen(true);
    } catch (error) {
      console.error('Ошибка при получении предпросмотра:', error);
      alert(`Ошибка при получении предпросмотра: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleForceUpdate = async () => {
    try {
      console.log('Начало принудительного обновления...');
      // Получаем количество сущностей для обновления
      const today = format(new Date(), 'yyyy-MM-dd');
      console.log('Получение количества сущностей для даты:', today);
      const countResponse = await utilsApi.getUpdateCount(today);
      console.log('Получен ответ о количестве:', countResponse);
      
      let totalRules = 0;
      let processedRules = 0;
      let totalUpdatedEntities = 0;
      
      // Устанавливаем начальное состояние прогресса
      // Если сущностей нет, все равно показываем прогресс
      const totalCount = countResponse.total_count || 0;
      lastProgressRef.current = null; // Сбрасываем ref при начале нового обновления
      setUpdateProgress({
        isUpdating: true,
        totalCount: totalCount,
        currentCount: 0,
        status: 'starting'
      });
      
      if (totalCount === 0) {
        // Если сущностей нет, все равно запускаем обновление для проверки правил
        console.log('Сущностей для обновления нет, но запускаем проверку правил...');
      }
      
      console.log('Запуск streaming обновления...');
      // Запускаем обновление с прогрессом
      await utilsApi.updateNowStream((progress: UpdateProgress) => {
        console.log('Получен прогресс:', progress);
        if (progress.type === 'start') {
          totalRules = progress.total_rules || 0;
          setUpdateProgress({
            isUpdating: true,
            totalCount: totalCount,
            currentCount: 0,
            status: 'processing'
          });
        } else if (progress.type === 'progress') {
          processedRules = progress.processed_rules || processedRules;
          if (progress.updated_count) {
            totalUpdatedEntities += progress.updated_count;
          }
          
          console.log('Получен прогресс:', {
            type: progress.type,
            updated_entities: progress.updated_entities,
            processed_rules: progress.processed_rules,
            status: progress.status,
            rule_name: progress.rule_name
          });
          
          // Используем requestAnimationFrame для плавного обновления
          requestAnimationFrame(() => {
            setUpdateProgress(prev => {
              if (!prev) return prev;
              // Используем updated_entities из бэкенда, если он есть
              // Иначе вычисляем прогресс на основе обработанных правил
              let newCurrentCount = prev.currentCount;
              if (progress.updated_entities !== undefined && progress.updated_entities !== null) {
                // Используем точное значение из бэкенда
                newCurrentCount = progress.updated_entities;
              } else {
                // Fallback: вычисляем прогресс на основе обработанных правил
                const progressPercent = totalRules > 0 
                  ? (processedRules / totalRules) * 100 
                  : 0;
                const estimatedCount = totalCount > 0
                  ? Math.floor((totalCount * progressPercent) / 100)
                  : Math.floor(progressPercent);
                newCurrentCount = Math.max(prev.currentCount, estimatedCount);
              }
              
              // Проверяем, изменилось ли значение, чтобы избежать дублирующих обновлений
              const now = Date.now();
              const lastProgress = lastProgressRef.current;
              if (lastProgress && lastProgress.currentCount === newCurrentCount && (now - lastProgress.timestamp) < 100) {
                // Значение не изменилось и прошло менее 100мс - пропускаем обновление
                return prev;
              }
              
              // Обновляем ref с новым значением
              lastProgressRef.current = { currentCount: newCurrentCount, timestamp: now };
              console.log(`Обновление currentCount с ${prev.currentCount} на ${newCurrentCount}`);
              
              return {
                ...prev,
                currentRule: progress.rule_name || prev.currentRule,
                status: progress.status || prev.status,
                currentCount: newCurrentCount
              };
            });
          });
        } else if (progress.type === 'complete') {
          console.log('Обновление завершено');
          const finalCount = progress.updated_entities || totalUpdatedEntities;
          setUpdateProgress({
            isUpdating: false,
            totalCount: totalCount,
            currentCount: finalCount,
            status: 'completed'
          });
          
          // Обновляем график после завершения
          const start = format(startOfMonth(currentMonth), 'yyyy-MM-dd');
          const end = format(endOfMonth(currentMonth), 'yyyy-MM-dd');
          fetchSchedules(start, end);
          setLastUpdateTime(new Date());
          
          // Если сущностей не было обновлено, показываем сообщение
          if (finalCount === 0) {
            setTimeout(() => {
              setUpdateProgress({
                isUpdating: false,
                totalCount: 0,
                currentCount: 0,
                status: 'completed',
                currentRule: 'Нет сущностей для обновления'
              });
              setTimeout(() => {
                setUpdateProgress(null);
              }, 3000);
            }, 500);
          } else {
            // Скрываем прогресс через 3 секунды
            setTimeout(() => {
              setUpdateProgress(null);
            }, 3000);
          }
        } else if (progress.type === 'error') {
          console.error('Ошибка при обновлении:', progress.error);
          setUpdateProgress({
            isUpdating: false,
            totalCount: totalCount,
            currentCount: progress.updated_entities || 0,
            status: 'error'
          });
          alert(`Ошибка при обновлении: ${progress.error || 'Неизвестная ошибка'}`);
          setTimeout(() => {
            setUpdateProgress(null);
          }, 5000);
        }
      }, today);
      console.log('Streaming обновление завершено');
    } catch (error) {
      console.error('Ошибка при обновлении:', error);
      alert(`Ошибка при обновлении: ${error instanceof Error ? error.message : String(error)}`);
      setUpdateProgress({
        isUpdating: false,
        totalCount: 0,
        currentCount: 0,
        status: 'error'
      });
      setTimeout(() => {
        setUpdateProgress(null);
      }, 3000);
    }
  };

  const nextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1));
  };

  const prevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1));
  };

  return (
    <div className="space-y-6">
      {/* Прогресс бар обновления сущностей */}
      {updateProgress && updateProgress.isUpdating && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              <span className="text-sm font-medium text-blue-900">
                Обновление сущностей...
              </span>
              {updateProgress.currentRule && (
                <span className="text-sm text-blue-700">
                  ({updateProgress.currentRule})
                </span>
              )}
            </div>
            <span className="text-sm text-blue-700">
              {updateProgress.totalCount > 0 
                ? `${updateProgress.currentCount} / ${updateProgress.totalCount}`
                : 'Проверка правил...'}
            </span>
          </div>
          {updateProgress.totalCount > 0 && (
            <div className="w-full bg-blue-200 rounded-full h-2 overflow-hidden">
              <div
                key={`progress-${updateProgress.currentCount}`}
                className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
                style={{
                  width: `${Math.min((updateProgress.currentCount / updateProgress.totalCount) * 100, 100)}%`,
                  willChange: 'width'
                }}
              ></div>
            </div>
          )}
        </div>
      )}
      
      {updateProgress && !updateProgress.isUpdating && updateProgress.status === 'completed' && (
        <div className={`border rounded-lg p-4 ${
          updateProgress.currentCount === 0 
            ? 'bg-yellow-50 border-yellow-200' 
            : 'bg-green-50 border-green-200'
        }`}>
          <div className="flex items-center justify-between">
            <span className={`text-sm font-medium ${
              updateProgress.currentCount === 0 
                ? 'text-yellow-900' 
                : 'text-green-900'
            }`}>
              {updateProgress.currentCount === 0 
                ? 'Обновление завершено: нет сущностей для обновления на сегодня'
                : `Обновление завершено: обновлено ${updateProgress.currentCount} сущностей`}
            </span>
          </div>
        </div>
      )}
      
      {updateProgress && !updateProgress.isUpdating && updateProgress.status === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-red-900">
              Ошибка при обновлении сущностей
            </span>
          </div>
        </div>
      )}
      
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-gray-900">График дежурств</h2>
        <div className="flex gap-4">
          <Button 
            onClick={handleRefresh} 
            isLoading={loading}
            variant="secondary"
            title="Обновить данные графика"
          >
            <svg 
              className="w-5 h-5 inline-block mr-2" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" 
              />
            </svg>
            Обновить график
          </Button>
          <Button 
            onClick={handlePreviewUpdates} 
            isLoading={loadingPreview}
            variant="secondary"
            title="Посмотреть какие сущности будут обновлены без реального обновления"
            disabled={loadingPreview || updateProgress?.isUpdating}
          >
            <svg 
              className="w-5 h-5 inline-block mr-2" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" 
              />
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" 
              />
            </svg>
            Предпросмотр обновлений
          </Button>
          <Button 
            onClick={handleForceUpdate} 
            isLoading={updateProgress?.isUpdating}
            variant="primary"
            title="Принудительно обновить сущности Bitrix24"
            disabled={updateProgress?.isUpdating}
          >
            <svg 
              className="w-5 h-5 inline-block mr-2" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M13 10V3L4 14h7v7l9-11h-7z" 
              />
            </svg>
            Обновить сущности
          </Button>
          <div className="flex gap-2">
            <Input
              type="number"
              value={generateYear}
              onChange={(e) => setGenerateYear(Number(e.target.value))}
              className="w-24"
            />
            <Input
              type="number"
              value={generateMonth}
              onChange={(e) => setGenerateMonth(Number(e.target.value))}
              min={1}
              max={12}
              className="w-20"
            />
            <Button onClick={handleGenerate} isLoading={loading}>
              Сгенерировать график
            </Button>
          </div>
        </div>
      </div>

      {/* Таблица графика */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-6">
          <Button variant="secondary" onClick={prevMonth}>
            ← Предыдущий месяц
          </Button>
          <div className="flex flex-col items-center">
            <h3 className="text-xl font-semibold text-gray-900">
              {format(currentMonth, 'MMMM yyyy', { locale: ru })}
            </h3>
            {lastUpdateTime && (
              <span className="text-xs text-gray-500 mt-1">
                Обновлено: {format(lastUpdateTime, 'dd.MM.yyyy HH:mm:ss', { locale: ru })}
              </span>
            )}
          </div>
          <Button variant="secondary" onClick={nextMonth}>
            Следующий месяц →
          </Button>
        </div>

        {loading ? (
          <div className="text-center py-8 text-gray-500">Загрузка...</div>
        ) : (
          <div className="w-full overflow-x-auto" style={{ maxWidth: '100%', boxSizing: 'border-box' }}>
            <table className="border-collapse" style={{ width: '100%', tableLayout: 'fixed' }}>
              <colgroup>
                <col style={{ width: '160px', minWidth: '160px' }} />
                {days.map(() => (
                  <col key={Math.random()} style={{ width: '28px', minWidth: '28px' }} />
                ))}
                <col style={{ width: '55px', minWidth: '55px' }} />
              </colgroup>
              <thead>
                <tr>
                  <th className="sticky left-0 z-10 bg-white border border-gray-300 px-2 py-2 text-left font-semibold text-gray-900">
                    Пользователь
                  </th>
                  {days.map((day) => {
                    const isToday = isSameDay(day, new Date());
                    return (
                      <th
                        key={day.toISOString()}
                        className={`border border-gray-300 px-0 py-1.5 text-center text-xs font-semibold text-gray-700 ${
                          isToday ? 'bg-blue-50 border-blue-300' : ''
                        }`}
                      >
                        <div className="font-medium leading-tight text-sm">{format(day, 'd', { locale: ru })}</div>
                        <div className="text-[10px] text-gray-500 font-normal leading-tight">
                          {format(day, 'EEE', { locale: ru }).slice(0, 2)}
                        </div>
                      </th>
                    );
                  })}
                  <th className="border border-gray-300 px-1 py-2 text-center font-semibold text-gray-900 bg-gray-50 text-xs">
                    Всего
                  </th>
                </tr>
              </thead>
              <tbody>
                {activeUsers.length === 0 ? (
                  <tr>
                    <td colSpan={days.length + 2} className="text-center py-8 text-gray-500">
                      Нет активных пользователей
                    </td>
                  </tr>
                ) : (
                  activeUsers.map((user) => {
                    const dutyDaysCount = getDutyDaysCount(user.id);
                    const userName = [user.name, user.last_name].filter(Boolean).join(' ') || user.email || `ID: ${user.id}`;
                    return (
                      <tr key={user.id} className="hover:bg-gray-50">
                        <td className="sticky left-0 z-10 bg-white border border-gray-300 px-2 py-2 font-medium text-gray-900">
                          <div className="truncate text-sm" title={userName}>
                            {userName}
                          </div>
                        </td>
                        {days.map((day) => {
                          const hasDuty = isUserOnDuty(user.id, day);
                          const usersOnDuty = getUsersOnDuty(day);
                          const dutyCount = usersOnDuty.length;
                          const isMultipleUsers = dutyCount > 1;
                          
                          return (
                            <td
                              key={day.toISOString()}
                              onClick={() => handleCellClick(day, user.id)}
                              className={`border border-gray-300 px-0 py-1 text-center cursor-pointer transition-colors w-[32px] ${
                                hasDuty
                                  ? isMultipleUsers
                                    ? 'bg-green-200 hover:bg-green-300'
                                    : 'bg-green-100 hover:bg-green-200'
                                  : 'bg-white hover:bg-gray-100'
                              }`}
                              title={`${format(day, 'd MMMM yyyy', { locale: ru })} - ${userName}. ${hasDuty ? `Дежурство (${dutyCount} ${dutyCount === 1 ? 'пользователь' : 'пользователей'})` : 'Клик для назначения'}`}
                            >
                              {hasDuty ? (
                                <div className="flex items-center justify-center">
                                  <div className="w-3.5 h-3.5 rounded-full bg-green-500 flex items-center justify-center">
                                    <svg
                                      className="w-2 h-2 text-white"
                                      fill="none"
                                      stroke="currentColor"
                                      viewBox="0 0 24 24"
                                    >
                                      <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={3}
                                        d="M5 13l4 4L19 7"
                                      />
                                    </svg>
                                  </div>
                                </div>
                              ) : (
                                <div className="w-3.5 h-3.5 mx-auto rounded-full border-2 border-gray-300"></div>
                              )}
                            </td>
                          );
                        })}
                        <td className="border border-gray-300 px-1 py-2 text-center font-semibold text-gray-900 bg-gray-50 text-sm">
                          {dutyDaysCount}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Модальное окно редактирования */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedDate(null);
          setSelectedUserId('');
        }}
        title={selectedDate ? `Дежурство на ${format(parseISO(selectedDate), 'd MMMM yyyy', { locale: ru })}` : 'Новое дежурство'}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Пользователь
            </label>
            <select
              value={selectedUserId}
              onChange={(e) => setSelectedUserId(e.target.value ? Number(e.target.value) : '')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Выберите пользователя</option>
              {activeUsers.map((user) => (
                <option key={user.id} value={user.id}>
                  {[user.name, user.last_name].filter(Boolean).join(' ') || user.email || `ID: ${user.id}`}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            {schedules.find((s) => s.date === selectedDate) && (
              <div>
                <p className="text-sm text-gray-600 mb-2">Пользователи на дежурстве:</p>
                <div className="space-y-1 mb-3">
                  {schedules.find((s) => s.date === selectedDate)?.users.map((user) => (
                    <div key={user.user_id} className="flex items-center justify-between px-2 py-1 bg-gray-50 rounded">
                      <span className="text-sm">
                        {user.user_name || user.user_email || `ID: ${user.user_id}`}
                      </span>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={async () => {
                          const schedule = schedules.find((s) => s.date === selectedDate);
                          if (schedule) {
                            const start = format(startOfMonth(currentMonth), 'yyyy-MM-dd');
                            const end = format(endOfMonth(currentMonth), 'yyyy-MM-dd');
                            const newUserIds = schedule.users.filter(u => u.user_id !== user.user_id).map(u => u.user_id);
                            if (newUserIds.length === 0) {
                              await deleteSchedule(schedule.id, start, end);
                            } else {
                              await updateSchedule(schedule.id, { user_ids: newUserIds }, start, end);
                            }
                            setLastUpdateTime(new Date());
                          }
                        }}
                      >
                        Удалить
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="flex gap-2 justify-end">
              {schedules.find((s) => s.date === selectedDate) && (
                <Button variant="danger" onClick={handleDelete}>
                  Удалить всех
                </Button>
              )}
              <Button onClick={handleSave} disabled={!selectedUserId}>
                Добавить пользователя
              </Button>
            </div>
          </div>
        </div>
      </Modal>

      {/* Модальное окно предпросмотра обновлений */}
      <PreviewUpdatesModal
        isOpen={isPreviewModalOpen}
        onClose={() => setIsPreviewModalOpen(false)}
        entities={previewEntities}
        totalCount={previewTotalCount}
        date={previewDate}
      />
    </div>
  );
};

export default Schedule;
