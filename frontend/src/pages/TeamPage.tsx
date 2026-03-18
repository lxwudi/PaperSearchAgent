import { useEffect, useState } from 'react';

import type { TeamMember } from '../api/types';
import { useAuth } from '../contexts/AuthContext';

export function TeamPage() {
  const { authFetch, activeTeamId } = useAuth();
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [newUserId, setNewUserId] = useState('');
  const [newRole, setNewRole] = useState<TeamMember['role']>('viewer');

  const loadMembers = () => {
    if (!activeTeamId) {
      return;
    }
    authFetch<TeamMember[]>(`/teams/${activeTeamId}/members`).then(setMembers);
  };

  useEffect(() => {
    loadMembers();
  }, [activeTeamId]);

  const addMember = async () => {
    if (!activeTeamId || !newUserId.trim()) {
      return;
    }
    await authFetch<TeamMember>(`/teams/${activeTeamId}/members`, {
      method: 'POST',
      body: JSON.stringify({ user_id: newUserId.trim(), role: newRole }),
    });
    setNewUserId('');
    loadMembers();
  };

  const updateRole = async (userId: string, role: TeamMember['role']) => {
    if (!activeTeamId) {
      return;
    }
    await authFetch<TeamMember>(`/teams/${activeTeamId}/members/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    });
    loadMembers();
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>团队成员与角色</h2>
        <span>共 {members.length} 人</span>
      </div>
      <div className="team-add">
        <input
          value={newUserId}
          onChange={(e) => setNewUserId(e.target.value)}
          placeholder="输入用户 ID"
          aria-label="用户 ID"
        />
        <select
          value={newRole}
          onChange={(e) => setNewRole(e.target.value as TeamMember['role'])}
          aria-label="成员角色"
        >
          <option value="viewer">viewer</option>
          <option value="editor">editor</option>
          <option value="admin">admin</option>
          <option value="owner">owner</option>
        </select>
        <button className="btn" onClick={addMember}>添加成员</button>
      </div>
      <div className="list">
        {members.map((member) => (
          <div key={member.id} className="list-item">
            <div>
              <strong>{member.user_id}</strong>
              <div className="muted">角色：{member.role}</div>
            </div>
            <select
              value={member.role}
              onChange={(e) => updateRole(member.user_id, e.target.value as TeamMember['role'])}
              aria-label={`成员角色：${member.user_id}`}
            >
              <option value="viewer">viewer</option>
              <option value="editor">editor</option>
              <option value="admin">admin</option>
              <option value="owner">owner</option>
            </select>
          </div>
        ))}
      </div>
    </div>
  );
}

