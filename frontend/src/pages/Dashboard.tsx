import React, { useEffect } from 'react';
import { useScheduleStore } from '../store/scheduleStore';
import { useUsersStore } from '../store/usersStore';
import { format, startOfMonth, endOfMonth } from 'date-fns';
import ru from 'date-fns/locale/ru';

const Dashboard: React.FC = () => {
  const { schedules, fetchSchedules, loading } = useScheduleStore();
  const { users, fetchUsers } = useUsersStore();

  useEffect(() => {
    const now = new Date();
    const start = format(startOfMonth(now), 'yyyy-MM-dd');
    const end = format(endOfMonth(now), 'yyyy-MM-dd');
    
    fetchSchedules(start, end);
    fetchUsers();
  }, [fetchSchedules, fetchUsers]);

  const today = format(new Date(), 'yyyy-MM-dd');
  const todaySchedule = schedules.find((s) => s.date === today);
  const upcomingSchedules = schedules
    .filter((s) => s.date >= today)
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(0, 5);

  // Форматируем список дежурных на сегодня
  const getTodayOnDutyText = () => {
    if (!todaySchedule || todaySchedule.users.length === 0) {
      return 'Не назначен';
    }
    const names = todaySchedule.users
      .map((u) => u.user_name || u.user_email || `ID: ${u.user_id}`)
      .filter(Boolean);
    return names.join(', ') || 'Не назначен';
  };

  const stats = {
    totalUsers: users.length,
    activeUsers: users.filter((u) => u.active).length,
    schedulesThisMonth: schedules.length,
    todayOnDuty: getTodayOnDutyText(),
  };

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold text-gray-900">Главная</h2>

      {/* Статистика */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Всего пользователей</h3>
          <p className="text-3xl font-bold text-gray-900 mt-2">{stats.totalUsers}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Активных пользователей</h3>
          <p className="text-3xl font-bold text-gray-900 mt-2">{stats.activeUsers}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Дежурств в этом месяце</h3>
          <p className="text-3xl font-bold text-gray-900 mt-2">{stats.schedulesThisMonth}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Дежурный сегодня</h3>
          <p className="text-lg font-semibold text-gray-900 mt-2">{stats.todayOnDuty}</p>
        </div>
      </div>

      {/* Ближайшие дежурства */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Ближайшие дежурства</h3>
        </div>
        <div className="p-6">
          {loading ? (
            <p className="text-gray-500">Загрузка...</p>
          ) : upcomingSchedules.length === 0 ? (
            <p className="text-gray-500">Нет запланированных дежурств</p>
          ) : (
            <ul className="space-y-3">
              {upcomingSchedules.map((schedule) => {
                const userNames = schedule.users
                  .map((u) => u.user_name || u.user_email || `ID: ${u.user_id}`)
                  .filter(Boolean);
                const displayName = userNames.length > 0 
                  ? userNames.join(', ') 
                  : 'Не назначен';
                
                return (
                  <li key={schedule.id} className="flex justify-between items-center py-2 border-b border-gray-100 last:border-0">
                    <div>
                      <p className="font-medium text-gray-900">{displayName}</p>
                      <p className="text-sm text-gray-500">
                        {format(new Date(schedule.date), 'd MMMM yyyy', { locale: ru })}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
