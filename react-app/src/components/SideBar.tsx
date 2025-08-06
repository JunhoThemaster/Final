// src/components/SideBar.tsx (기존 스타일 유지 + AI 면접 추가)
import React from 'react';
import { NavLink } from 'react-router-dom';
import '../Sidebar.css'; // CSS 분리 추천

const SideBar: React.FC = () => {
  return (
    <aside className="sidebar">
      <nav>
        <ul>
          <li>
            <NavLink
              to="/dashboard"
              className={({ isActive }: { isActive: boolean }) => (isActive ? 'active' : '')}
            >
              📺 Dashboard
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/interview"
              className={({ isActive }: { isActive: boolean }) => (isActive ? 'active' : '')}
            >
              🤖 AI 면접
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/settings"
              className={({ isActive }: { isActive: boolean }) => (isActive ? 'active' : '')}
            >
              ⚙️ 환경 설정
            </NavLink>
          </li>
        </ul>
      </nav>
    </aside>
  );
};

export default SideBar;