import { useState, type ReactNode } from 'react';
import { NavLink } from 'react-router-dom';

import { useAuth } from '../contexts/AuthContext';

export function AppLayout({ children }: { children: ReactNode }) {
  const { user, teams, activeTeamId, selectTeam, createTeam, logout } = useAuth();
  const [newTeamName, setNewTeamName] = useState('');

  const handleCreateTeam = async () => {
    if (!newTeamName.trim()) {
      return;
    }
    await createTeam(newTeamName.trim());
    setNewTeamName('');
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">PS</div>
          <div>
            <div className="brand-title">PaperSearch</div>
            <div className="brand-sub">多智能体文献检索</div>
          </div>
        </div>
        <nav className="nav">
          <NavLink to="/workspace">工作台</NavLink>
          <NavLink to="/history">历史记录</NavLink>
          <NavLink to="/favorites">收藏夹</NavLink>
          <NavLink to="/exports">导出中心</NavLink>
          <NavLink to="/team">团队管理</NavLink>
        </nav>
        <div className="sidebar-footer">
          <div className="user-badge">
            <div className="user-name">{user?.display_name || '访客'}</div>
            <div className="user-email">{user?.email}</div>
          </div>
          <button className="btn ghost" onClick={logout}>退出登录</button>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="team-switch">
            <label htmlFor="team-switch">当前团队</label>
            <select id="team-switch" aria-label="当前团队" value={activeTeamId || ''} onChange={(e) => selectTeam(e.target.value)}>
              <option value="" disabled>
                请选择团队
              </option>
              {teams.map((team) => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))}
            </select>
          </div>
          <div className="team-create">
            <input
              value={newTeamName}
              onChange={(e) => setNewTeamName(e.target.value)}
              placeholder="新团队名称"
              aria-label="新团队名称"
            />
            <button className="btn" onClick={handleCreateTeam}>创建团队</button>
          </div>
        </header>
        <div className="content">{children}</div>
      </main>
    </div>
  );
}


