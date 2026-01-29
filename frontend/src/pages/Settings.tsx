import React, { useState } from 'react';
import UpdateRulesSettings from '../components/settings/UpdateRulesSettings';
import WebhookSettings from '../components/settings/WebhookSettings';

const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'rules' | 'webhook'>('rules');

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold text-gray-900">Настройки</h2>

      {/* Табы */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('rules')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'rules'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Правила обновления
          </button>
          <button
            onClick={() => setActiveTab('webhook')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'webhook'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Webhook
          </button>
        </nav>
      </div>

      {/* Контент табов */}
      <div>
        {activeTab === 'rules' && <UpdateRulesSettings />}
        {activeTab === 'webhook' && <WebhookSettings />}
      </div>
    </div>
  );
};

export default Settings;
