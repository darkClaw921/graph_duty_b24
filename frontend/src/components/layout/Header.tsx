import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { Button } from '../common/Button';

const Header: React.FC = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="px-6 py-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Graph Duty B24
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Управление графиком дежурств Bitrix24
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={handleLogout}>
          Выход
        </Button>
      </div>
    </header>
  );
};

export default Header;
