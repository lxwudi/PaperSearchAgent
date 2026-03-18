# Papersearch Agent

面向科研论文检索与协作的多智能体系统，包含 FastAPI 后端与 React 前端，支持团队协作、检索任务编排、收藏导出与 WebSocket 实时事件推送。

**功能概览**
- 账号注册/登录与 JWT 鉴权
- 团队与成员管理
- 论文检索任务创建、状态追踪与事件流
- 收藏与导出（CSV/PDF）
- WebSocket 实时推送任务事件
- MCP 科学论文工具接入

**技术栈**
- 后端：FastAPI + SQLAlchemy + SQLite（默认）+ LangGraph + LangChain + MCP
- 前端：React + Vite + React Router + Recharts
- 运行环境：Python 3.11+，Node.js 18+

**环境要求**
- Windows 10/11
- Python 3.11+
- Node.js 18+（建议 LTS 版本）

**目录结构**
- `backend`：后端服务
- `frontend`：前端应用
- `scripts`：一键启动/停止脚本（Windows）
- `docs`：设计与说明文档

**一定能启动的最稳流程（Windows，推荐）**
说明：不依赖管理员权限，不走脚本，按顺序执行即可稳定启动。

1. 后端依赖与配置
```powershell
cd .\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```
把 `backend/.env` 里的 `APP_HOST` 改为 `127.0.0.1`，`APP_PORT` 改为 `8001`。

2. 启动后端（保持此终端不关闭）
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

3. 前端依赖与配置
```powershell
cd ..\frontend
npm install
echo VITE_API_BASE_URL=http://127.0.0.1:8001 > .env
echo VITE_DEV_PORT=5173 >> .env
```

4. 启动前端（新开一个终端）
```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

5. 验证启动
```powershell
Invoke-WebRequest http://127.0.0.1:8001/healthz
```
前端访问：`http://127.0.0.1:5173`

**一键脚本（可选）**
如果你确认脚本可用，可以直接用脚本启动；脚本失败时请回到上面的“最稳流程”。

```bat
scripts\app.cmd start
scripts\app.cmd status
scripts\app.cmd stop
scripts\app.cmd restart
```

**环境变量**
后端 `backend/.env`：
- `APP_ENV`：环境标识，默认 `dev`
- `APP_DEBUG`：调试开关，默认 `true`
- `APP_HOST`：服务绑定地址
- `APP_PORT`：服务端口
- `DATABASE_URL`：数据库连接串，默认 `sqlite+aiosqlite:///./papersearch.db`
- `REDIS_URL`：Redis 连接串（可选）
- `SECRET_KEY`：JWT 签名密钥，生产环境必须修改
- `JWT_ALGORITHM`：JWT 算法，默认 `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES`：访问令牌过期分钟数
- `REFRESH_TOKEN_EXPIRE_MINUTES`：刷新令牌过期分钟数
- `OPENAI_API_KEY`：OpenAI Key（可为空）
- `DEFAULT_MODEL`：默认模型名
- `LLM_FALLBACK_MODE`：`graceful` / `hard_fail`
- `LLM_FORCE_HEURISTIC`：是否强制启发式策略
- `MCP_COMMAND` / `MCP_ARGS`：MCP 启动命令与参数
- `MCP_SERVER_NAME` / `MCP_SEARCH_TOOL`：MCP 服务与工具名
- `MCP_TIMEOUT_SEC` / `MCP_CACHE_TTL_SEC`：超时与缓存
- `JOB_EXECUTOR_MODE`：`inline` 为内嵌执行
- `WORKER_POLL_INTERVAL` / `WS_POLL_INTERVAL_SEC`：轮询周期

前端 `frontend/.env`：
- `VITE_API_BASE_URL`：后端 API 地址
- `VITE_DEV_PORT`：前端开发端口（脚本读取）

**API 概览**
认证：
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/refresh`
- `POST /auth/logout`

团队：
- `GET /teams`
- `POST /teams`
- `GET /teams/{team_id}/members`
- `POST /teams/{team_id}/members`
- `PATCH /teams/{team_id}/members/{user_id}`

检索：
- `POST /search/jobs`
- `GET /search/jobs/{job_id}`
- `GET /search/jobs/{job_id}/results`
- `GET /search/jobs/{job_id}/events`
- `POST /search/jobs/{job_id}/retry`
- `POST /search/jobs/{job_id}/cancel`
- `GET /search/history`
- `POST /search/favorites`
- `GET /search/favorites`
- `DELETE /search/favorites/{favorite_id}`
- `POST /search/exports`
- `GET /search/exports`
- `GET /search/exports/{export_id}`
- `GET /search/exports/{export_id}/download`

收藏库：
- `GET /library/history`
- `POST /library/favorites`
- `GET /library/favorites`
- `DELETE /library/favorites/{favorite_id}`

WebSocket：
- `WS /ws/jobs/{job_id}`
- `WS /ws/teams/{team_id}/streams`

**使用流程示例**
1. 注册/登录获取 `access_token`
2. 创建团队
3. 创建检索任务
4. 轮询任务状态与结果

**测试**
后端：
```powershell
cd .\backend
.\.venv\Scripts\python.exe -m pip install pytest pytest-asyncio
.\.venv\Scripts\python.exe -m pytest
```

前端：
```powershell
cd .\frontend
npm run build
```

**常见问题与必过排障**
- 前端 `spawn EPERM`：请确保用“最稳流程”手动启动前端；若仍出现，建议把项目目录加入 Windows Defender 排除项后再试。
- 端口被占用：用 `netstat -ano | findstr ":8001"` 或 `":5173"` 找到 PID，再用 `taskkill /PID <pid> /F` 释放端口。
- 后端启动后立即退出：检查终端错误输出，或查看 `backend/logs/backend.err.log`（若使用脚本）。

**生产部署（Linux / Docker / Windows）**
Linux（systemd 示例）：
```bash
cd backend
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
前端构建：
```bash
cd frontend
npm install
npm run build
```

Docker（示例思路）：
- 本项目未内置 Dockerfile，可自行编写并分别构建前后端镜像
- 如使用 Postgres，请安装 `asyncpg` 并修改 `DATABASE_URL`

Windows 服务器：
- 后端可用 NSSM 或任务计划运行 `python -m uvicorn`
- 前端构建 `dist` 后用 IIS 或 Nginx 托管

**安全与生产建议**
- 修改 `SECRET_KEY` 并收紧 CORS
- 不要在仓库中提交真实密钥
- 生产环境建议使用 Postgres 替换 SQLite

**日志与 PID（脚本模式）**
- 后端：`backend/logs/backend.out.log`，`backend/logs/backend.err.log`，`backend/logs/backend.pid`
- 前端：`frontend/logs/frontend.out.log`，`frontend/logs/frontend.err.log`，`frontend/logs/frontend.pid`
