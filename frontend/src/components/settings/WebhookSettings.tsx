import React, { useEffect, useState } from 'react';
import { settingsApi } from '../../services/settingsApi';
import { Button } from '../common/Button';

const WebhookSettings: React.FC = () => {
  const [webhookUrl, setWebhookUrl] = useState<string>('');
  const [_loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchWebhookUrl();
  }, []);

  const fetchWebhookUrl = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await settingsApi.getWebhookUrl();
      setWebhookUrl(data.webhook_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки URL webhook');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(webhookUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Ошибка копирования:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Настройки Webhook</h3>
        
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              URL для настройки webhook в Bitrix24
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={webhookUrl}
                readOnly
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-700"
              />
              <Button onClick={handleCopy} variant="secondary">
                {copied ? 'Скопировано!' : 'Копировать'}
              </Button>
            </div>
            <p className="mt-2 text-sm text-gray-600">
              Используйте этот URL для настройки входящего webhook в Bitrix24. 
              При создании или изменении сделки ответственный будет автоматически обновлен на пользователя, 
              который стоит в графике дежурств на текущий день.
            </p>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 mb-2">Как настроить:</h4>
            <ol className="list-decimal list-inside space-y-1 text-sm text-blue-800">
              <li>Скопируйте URL выше</li>
              <li>В Bitrix24 перейдите в раздел "Приложения" → "Входящий webhook"</li>
              <li>Создайте новый webhook и укажите скопированный URL</li>
              <li>Выберите события: OnCrmDealAdd, OnCrmDealUpdate</li>
              <li>Сохраните настройки</li>
            </ol>
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h4 className="font-medium text-yellow-900 mb-2">Важно:</h4>
            <ul className="list-disc list-inside space-y-1 text-sm text-yellow-800">
              <li>Webhook будет работать только если в графике дежурств есть пользователь на текущий день</li>
              <li>Ответственный обновляется только для сделок, соответствующих активным правилам обновления</li>
              <li>Если на дежурстве несколько пользователей, ответственный выбирается согласно распределению в правилах</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WebhookSettings;
