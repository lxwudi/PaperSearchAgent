import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../contexts/AuthContext';

export function AuthPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register(email, password, displayName || email.split('@')[0]);
      }
      navigate('/workspace');
    } catch (err) {
      setError((err as Error).message || '操作失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>PaperSearch Agent</h1>
        <p className="auth-sub">一站式科学文献检索与智能综述</p>
        <div className="auth-toggle">
          <button
            className={mode === 'login' ? 'active' : ''}
            onClick={() => setMode('login')}
            type="button"
          >
            登录
          </button>
          <button
            className={mode === 'register' ? 'active' : ''}
            onClick={() => setMode('register')}
            type="button"
          >
            注册
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          {mode === 'register' && (
            <label>
              昵称
              <input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="如：张三"
              />
            </label>
          )}
          <label>
            邮箱
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@example.com"
              required
            />
          </label>
          <label>
            密码
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="至少 8 位"
              required
            />
          </label>
          {error && <div className="error">{error}</div>}
          <button className="btn primary" type="submit" disabled={loading}>
            {loading ? '处理中...' : mode === 'login' ? '登录' : '创建账号'}
          </button>
        </form>
      </div>
      <div className="auth-side">
        <h2>探索更快的文献检索流程</h2>
        <ul>
          <li>多智能体自动检索与评分</li>
          <li>实时事件流与可视化分析</li>
          <li>团队协作、收藏与导出中心</li>
        </ul>
      </div>
    </div>
  );
}

