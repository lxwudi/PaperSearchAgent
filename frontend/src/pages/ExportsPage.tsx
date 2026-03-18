import { useEffect, useState } from 'react';

import { getApiBase } from '../api/client';
import type { ExportJob } from '../api/types';
import { useAuth } from '../contexts/AuthContext';

export function ExportsPage() {
  const { authFetch, activeTeamId } = useAuth();
  const [exports, setExports] = useState<ExportJob[]>([]);

  useEffect(() => {
    if (!activeTeamId) {
      return;
    }
    authFetch<ExportJob[]>(`/search/exports?team_id=${activeTeamId}`).then(setExports);
  }, [activeTeamId, authFetch]);

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>导出中心</h2>
        <span>共 {exports.length} 条</span>
      </div>
      {exports.length === 0 ? (
        <div className="empty">暂无导出</div>
      ) : (
        <div className="list">
          {exports.map((item) => (
            <div key={item.id} className="list-item">
              <div>
                <strong>{item.export_type.toUpperCase()}</strong>
                <div className="muted">状态：{item.status}</div>
              </div>
              {item.file_path ? (
                <a href={`${getApiBase()}/search/exports/${item.id}/download`} target="_blank" rel="noreferrer">
                  下载
                </a>
              ) : (
                <span className="muted">暂无文件</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

