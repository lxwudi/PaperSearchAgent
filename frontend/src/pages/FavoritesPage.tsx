import { useEffect, useState } from 'react';

import type { FavoriteDetail } from '../api/types';
import { useAuth } from '../contexts/AuthContext';

export function FavoritesPage() {
  const { authFetch, activeTeamId } = useAuth();
  const [favorites, setFavorites] = useState<FavoriteDetail[]>([]);

  const load = () => {
    if (!activeTeamId) {
      return;
    }
    authFetch<FavoriteDetail[]>(`/library/favorites?team_id=${activeTeamId}`).then(setFavorites);
  };

  useEffect(() => {
    load();
  }, [activeTeamId]);

  const removeFavorite = async (id: string) => {
    await authFetch(`/library/favorites/${id}`, { method: 'DELETE' });
    load();
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>收藏夹</h2>
        <span>共 {favorites.length} 条</span>
      </div>
      {favorites.length === 0 ? (
        <div className="empty">暂无收藏</div>
      ) : (
        <div className="results">
          {favorites.map((paper) => (
            <article key={paper.id} className="paper-card">
              <div className="paper-title">
                <h4>{paper.title}</h4>
                <button className="btn ghost" onClick={() => removeFavorite(paper.id)}>
                  取消收藏
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
      )}
    </div>
  );
}

