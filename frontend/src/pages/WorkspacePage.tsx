import { useCallback, useEffect, useMemo, useState } from 'react';

import { getApiBase, getWsBase } from '../api/client';
import type { ExportJob, SearchEvent, SearchJob, SearchResult } from '../api/types';
import { useAuth } from '../contexts/AuthContext';
import { useWorkspace } from '../contexts/WorkspaceContext';

export function WorkspacePage() {
  const { authFetch, activeTeamId } = useAuth();
  const { activeJobId, setActiveJobId } = useWorkspace();
  const [query, setQuery] = useState('');
  const [minScore, setMinScore] = useState(0);
  const [job, setJob] = useState<SearchJob | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [events, setEvents] = useState<SearchEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [exports, setExports] = useState<ExportJob[]>([]);

  const sourceFacets = useMemo(() => {
    const counts: Record<string, number> = {};
    results.forEach((item) => {
      const key = item.source || 'unknown';
      counts[key] = (counts[key] || 0) + 1;
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [results]);

  const loadJob = useCallback(async () => {
    if (!activeJobId) {
      return;
    }
    const data = await authFetch<SearchJob>(`/search/jobs/${activeJobId}`);
    setJob(data);
  }, [activeJobId, authFetch]);

  const loadResults = useCallback(async () => {
    if (!activeJobId) {
      return;
    }
    const data = await authFetch<SearchResult[]>(`/search/jobs/${activeJobId}/results?min_score=${minScore}`);
    setResults(data);
  }, [activeJobId, authFetch, minScore]);

  const loadEvents = useCallback(async () => {
    if (!activeJobId) {
      return;
    }
    const data = await authFetch<SearchEvent[]>(`/search/jobs/${activeJobId}/events`);
    setEvents(data);
  }, [activeJobId, authFetch]);

  const loadExports = useCallback(async () => {
    if (!activeTeamId) {
      return;
    }
    const data = await authFetch<ExportJob[]>(`/search/exports?team_id=${activeTeamId}`);
    setExports(data);
  }, [activeTeamId, authFetch]);

  useEffect(() => {
    if (!activeJobId) {
      setJob(null);
      setResults([]);
      setEvents([]);
      return;
    }
    loadJob();
    loadResults();
    loadEvents();
  }, [activeJobId, loadJob, loadResults, loadEvents]);

  useEffect(() => {
    if (!activeJobId) {
      return;
    }
    const ws = new WebSocket(`${getWsBase()}/ws/jobs/${activeJobId}`);
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as SearchEvent;
        setEvents((prev) => {
          if (prev.find((item) => item.id === payload.id)) {
            return prev;
          }
          return [...prev, payload].sort((a, b) => a.created_at.localeCompare(b.created_at));
        });
      } catch {
        // ignore
      }
    };
    ws.onerror = () => {
      ws.close();
    };
    return () => ws.close();
  }, [activeJobId]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (activeJobId) {
        loadJob();
        loadResults();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [activeJobId, loadJob, loadResults]);

  useEffect(() => {
    loadExports();
  }, [loadExports]);

  const handleCreateJob = async () => {
    if (!activeTeamId) {
      setError('请先选择团队');
      return;
    }
    if (!query.trim()) {
      setError('请输入检索主题');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const payload = await authFetch<SearchJob>('/search/jobs', {
        method: 'POST',
        body: JSON.stringify({ team_id: activeTeamId, query }),
      });
      setActiveJobId(payload.id);
      setQuery('');
    } catch (err) {
      setError((err as Error).message || '创建任务失败');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (type: 'pdf' | 'csv') => {
    if (!activeTeamId || !activeJobId) {
      return;
    }
    const payload = await authFetch<ExportJob>('/search/exports', {
      method: 'POST',
      body: JSON.stringify({ team_id: activeTeamId, job_id: activeJobId, export_type: type }),
    });
    setExports((prev) => [payload, ...prev]);
  };

  const handleFavorite = async (resultId: string) => {
    if (!activeTeamId) {
      return;
    }
    await authFetch('/library/favorites', {
      method: 'POST',
      body: JSON.stringify({ team_id: activeTeamId, result_id: resultId }),
    });
  };

  return (
    <div className="workspace">
      <section className="panel search-panel">
        <div className="panel-header">
          <div>
            <h2>文献检索工作台</h2>
            <p>定义检索主题、监控智能体流程，并实时查看结果。</p>
          </div>
          <div className="score-filter">
            <label htmlFor="min-score">最低相关度</label>
            <input
              id="min-score"
              type="range"
              min={0}
              max={100}
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              aria-label="最低相关度"
            />
            <span>{minScore}</span>
          </div>
        </div>
        <div className="search-input">
          <input
            id="search-query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入研究主题，例如：多智能体文献检索" 
            aria-label="检索主题"
          />
          <button className="btn primary" onClick={handleCreateJob} disabled={loading}>
            {loading ? '创建中...' : '创建检索任务'}
          </button>
        </div>
        {error && <div className="error">{error}</div>}
      </section>

      <section className="panel job-panel">
        <div className="panel-header">
          <h3>任务状态</h3>
          <div className="job-actions">
            <button className="btn" onClick={() => handleExport('pdf')} disabled={!activeJobId}>
              导出 PDF
            </button>
            <button className="btn" onClick={() => handleExport('csv')} disabled={!activeJobId}>
              导出 CSV
            </button>
          </div>
        </div>
        {job ? (
          <div className="job-meta">
            <div>
              <span>状态</span>
              <strong>{job.status}</strong>
            </div>
            <div>
              <span>迭代次数</span>
              <strong>{job.iteration_count}</strong>
            </div>
            <div>
              <span>查询</span>
              <strong>{job.query}</strong>
            </div>
          </div>
        ) : (
          <div className="empty">暂无任务，请创建检索任务。</div>
        )}
        {job?.final_output && (
          <div className="summary">
            <h4>总结输出</h4>
            <pre>{job.final_output}</pre>
          </div>
        )}
      </section>

      <section className="grid">
        <div className="panel results-panel">
          <div className="panel-header">
            <h3>检索结果</h3>
            <span>共 {results.length} 条</span>
          </div>
          <div className="results">
            {results.map((paper) => (
              <article key={paper.id} className="paper-card">
                <div className="paper-title">
                  <h4>{paper.title}</h4>
                  <button className="btn ghost" onClick={() => handleFavorite(paper.id)}>
                    收藏
                  </button>
                </div>
                <div className="paper-meta">
                  <span>{paper.year || '未知年份'}</span>
                  <span>{paper.source || '来源未知'}</span>
                  <span>评分 {paper.score}</span>
                </div>
                <p className="paper-authors">{paper.authors.join(', ')}</p>
                {paper.abstract && <p className="paper-abstract">{paper.abstract}</p>}
                {paper.url && (
                  <a href={paper.url} target="_blank" rel="noreferrer">
                    查看原文
                  </a>
                )}
              </article>
            ))}
          </div>
        </div>
        <div className="panel sidebar-panel">
          <h3>来源统计</h3>
          <div className="facet-list">
            {sourceFacets.map((item) => (
              <div key={item.name} className="facet-item">
                <span>{item.name}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
          <div className="events">
            <h3>智能体过程</h3>
            {events.length === 0 ? (
              <div className="empty">等待事件流...</div>
            ) : (
              events.map((event) => (
                <div key={event.id} className="event-item">
                  <div className="event-type">{event.event_type}</div>
                  <div className="event-reason">{event.reason || '执行中'}</div>
                  <div className="event-time">{event.created_at}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <section className="panel export-panel">
        <h3>最近导出</h3>
        {exports.length === 0 ? (
          <div className="empty">暂无导出记录</div>
        ) : (
          <div className="export-list">
            {exports.map((item) => (
              <div key={item.id} className="export-item">
                <div>
                  <strong>{item.export_type.toUpperCase()}</strong>
                  <span>{item.status}</span>
                </div>
                {item.file_path && (
                  <a href={`${getApiBase()}/search/exports/${item.id}/download`} target="_blank" rel="noreferrer">
                    下载
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}






