import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import type { SearchJob } from '../api/types';
import { useAuth } from '../contexts/AuthContext';
import { useWorkspace } from '../contexts/WorkspaceContext';

export function HistoryPage() {
  const { authFetch, activeTeamId } = useAuth();
  const { setActiveJobId } = useWorkspace();
  const [history, setHistory] = useState<SearchJob[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (!activeTeamId) {
      return;
    }
    setLoading(true);
    authFetch<SearchJob[]>(`/library/history?team_id=${activeTeamId}`)
      .then(setHistory)
      .finally(() => setLoading(false));
  }, [activeTeamId, authFetch]);

  const openJob = (jobId: string) => {
    setActiveJobId(jobId);
    navigate('/workspace');
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>历史记录</h2>
        <span>共 {history.length} 条</span>
      </div>
      {loading ? (
        <div className="empty">加载中...</div>
      ) : history.length === 0 ? (
        <div className="empty">暂无历史任务</div>
      ) : (
        <div className="list">
          {history.map((job) => (
            <div key={job.id} className="list-item">
              <div>
                <strong>{job.query}</strong>
                <div className="muted">状态：{job.status} · {job.created_at}</div>
              </div>
              <button className="btn ghost" onClick={() => openJob(job.id)}>
                打开
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

