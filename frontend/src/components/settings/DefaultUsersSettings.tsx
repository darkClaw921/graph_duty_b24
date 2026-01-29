import React, { useEffect, useState } from 'react';
import { useSettingsStore } from '../../store/settingsStore';
import { useUsersStore } from '../../store/usersStore';
import { Button } from '../common/Button';
import { Modal } from '../common/Modal';

const DefaultUsersSettings: React.FC = () => {
  const { defaultUsers, loading, error, fetchDefaultUsers, createDefaultUser, deleteDefaultUser, reorderDefaultUsers } = useSettingsStore();
  const { users, fetchUsers } = useUsersStore();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<number | ''>('');

  useEffect(() => {
    fetchDefaultUsers();
    fetchUsers();
  }, [fetchDefaultUsers, fetchUsers]);

  const handleAdd = async () => {
    if (!selectedUserId) return;
    try {
      await createDefaultUser({ user_id: Number(selectedUserId) });
      setIsModalOpen(false);
      setSelectedUserId('');
    } catch (error) {
      console.error('Ошибка добавления:', error);
    }
  };

  const handleDelete = async (id: number) => {
    if (confirm('Удалить пользователя из списка дефолтных?')) {
      await deleteDefaultUser(id);
    }
  };

  const handleMoveUp = async (index: number) => {
    if (index === 0) return;
    const newOrder = [...defaultUsers];
    [newOrder[index], newOrder[index - 1]] = [newOrder[index - 1], newOrder[index]];
    await reorderDefaultUsers(newOrder.map((u) => u.user_id));
  };

  const handleMoveDown = async (index: number) => {
    if (index === defaultUsers.length - 1) return;
    const newOrder = [...defaultUsers];
    [newOrder[index], newOrder[index + 1]] = [newOrder[index + 1], newOrder[index]];
    await reorderDefaultUsers(newOrder.map((u) => u.user_id));
  };

  const availableUsers = users.filter(
    (u) => u.active && !defaultUsers.some((du) => du.user_id === u.id)
  );

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      <div className="flex justify-end">
        <Button onClick={() => setIsModalOpen(true)}>
          Добавить пользователя
        </Button>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Список дефолтных пользователей</h3>
          <p className="text-sm text-gray-600 mt-1">
            Порядок пользователей определяет последовательность дежурств при генерации графика
          </p>
        </div>
        <div className="p-6">
          {loading ? (
            <p className="text-gray-500">Загрузка...</p>
          ) : defaultUsers.length === 0 ? (
            <p className="text-gray-500">Нет дефолтных пользователей</p>
          ) : (
            <div className="space-y-2">
              {defaultUsers.map((defaultUser, index) => {
                const user = users.find((u) => u.id === defaultUser.user_id);
                return (
                  <div
                    key={defaultUser.id}
                    className="flex items-center justify-between py-3 px-4 border border-gray-200 rounded-lg hover:bg-gray-50"
                  >
                    <div className="flex items-center gap-4">
                      <span className="text-gray-500 font-medium w-8">{index + 1}</span>
                      <div>
                        <p className="font-medium text-gray-900">
                          {defaultUser.user_name || user?.email || `ID: ${defaultUser.user_id}`}
                        </p>
                        {defaultUser.user_email && (
                          <p className="text-sm text-gray-600">{defaultUser.user_email}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="secondary"
                        onClick={() => handleMoveUp(index)}
                        disabled={index === 0}
                      >
                        ↑
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => handleMoveDown(index)}
                        disabled={index === defaultUsers.length - 1}
                      >
                        ↓
                      </Button>
                      <Button variant="danger" onClick={() => handleDelete(defaultUser.id)}>
                        Удалить
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedUserId('');
        }}
        title="Добавить дефолтного пользователя"
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
              {availableUsers.map((user) => (
                <option key={user.id} value={user.id}>
                  {[user.name, user.last_name].filter(Boolean).join(' ') || user.email || `ID: ${user.id}`}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2 justify-end">
            <Button
              variant="secondary"
              onClick={() => {
                setIsModalOpen(false);
                setSelectedUserId('');
              }}
            >
              Отмена
            </Button>
            <Button onClick={handleAdd} disabled={!selectedUserId}>
              Добавить
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default DefaultUsersSettings;
