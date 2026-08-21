# 企业级 RAG 知识库问答系统

基于 FastAPI、Vue 3、MySQL、Redis、Celery、Qdrant 和 DeepSeek 构建的企业内部知识库问答平台。支持文档异步解析、向量检索、权限隔离、来源引用、SSE 流式对话和 GHCR 自动部署。

## 功能

- 客户端与管理端独立登录、会话刷新和权限校验
- 用户注册申请、管理员审批、角色和账号状态管理
- 知识库、文档、成员权限和标签管理
- 所有者、编辑者、查看者三种知识库角色
- PDF、DOCX、XLSX、TXT、Markdown、CSV 文档处理
- 旧版 Office 兼容解析、图片 OCR 和音频转写适配
- SHA-256 去重、大小校验、失败重试和批量重建索引
- Celery + Redis 异步处理、LangChain 文本切分、Qdrant 向量检索
- DeepSeek/OpenAI-compatible 问答、SSE 流式输出、多轮会话和来源引用
- 摘要、信息抽取、表格问答、审计日志和生产健康检查
- 模型调用 Token、耗时、成功率和人民币预估成本统计
- 管理端邀请记录、注册申请和密码重置申请批量删除
- GitHub Actions CI、GHCR 镜像发布和 Ubuntu 虚拟机部署

DeepSeek 只负责文本生成，不提供音频转写。音频必须配置独立的 Whisper 或 OpenAI-compatible 转写服务。RAG 通过来源引用、相似度阈值和无依据拒答降低幻觉，不能宣称绝对杜绝幻觉。

## 架构

```text
浏览器 -> Vue 3 -> Nginx /api 代理 -> FastAPI -> MySQL
                                      -> Redis -> Celery Worker/Beat
                                      -> Qdrant
                                      -> DeepSeek / 转写服务
```

| 服务 | 职责 | 默认端口 |
| --- | --- | --- |
| frontend | Nginx 托管前端并代理 API | 8080 |
| api | FastAPI API 和数据库迁移 | 8000 |
| worker | 文档解析、切分、向量化和索引 | 无 |
| beat | Celery 定时任务 | 无 |
| mysql | 业务数据 | 本机 3306 |
| redis | 队列、缓存和限流 | 内部 |
| qdrant | 向量存储和检索 | 内部 |

## 核心流程

文档：`上传 -> 校验/去重 -> uploaded -> Celery -> processing -> 文本/OCR/转写 -> 切分 -> Embedding -> Qdrant -> ready/failed`

问答：`问题 + 知识库 + 标签 -> 权限校验 -> 向量召回 -> 相似度过滤/Top-K -> DeepSeek SSE -> 来源和会话持久化`

## 目录

`backend/` 后端、迁移、任务和测试；`frontend/` Vue 3 前端；`scripts/` 部署、备份和检查脚本；`docs/` 项目文档；`compose.yaml` Docker 服务定义；`Dockerfile` API 镜像；`.env.example` 配置模板。

## 本地开发

项目开发基线为 Python 3.12。创建环境：`py -3.12 -m venv .venv312`，激活后执行 `python -m pip install -r requirements-dev.txt`。复制 `.env.example` 为 `.env`，再执行 `docker compose up -d mysql redis qdrant`。API 使用 `python -m uvicorn backend.app.main:app --reload --port 8000`，Worker 使用 `celery -A backend.app.celery_app:celery_app worker --loglevel=INFO --concurrency=1`，前端进入 `frontend` 后执行 `npm ci && npm run dev`。

## 配置

图片 OCR 已在生产环境验证，配置为 `OCR_ENABLED=true`、`OCR_LANGUAGES=chi_sim+eng`。音频转写仍需独立服务：`TRANSCRIPTION_ENABLED=true`、`TRANSCRIPTION_BASE_URL=https://服务地址/v1`、`TRANSCRIPTION_API_KEY=真实密钥`、`TRANSCRIPTION_MODEL=whisper-1`。完整说明见 [`docs/部署与运维手册.md`](docs/部署与运维手册.md)。真实 `.env` 不得提交。

## 测试

后端：`python -m pytest backend/app/tests -q`。前端：进入 `frontend` 执行 `npm run typecheck` 和 `npm run build`。检索评测使用 `python scripts/evaluate_retrieval.py backend/app/evaluations/retrieval_cases.example.json --k 3 --output reports/retrieval-baseline.json`。

## 生产部署

生产发布以 GitHub Actions 工作流为准：PR 合并到 `main` 后构建不可变 SHA 镜像，并由 Runner 连接 Ubuntu VM 更新服务。虚拟机不在本地构建镜像。仅在故障恢复时手工执行 Compose，且必须显式传入已发布的 `API_IMAGE` 和 `WEB_IMAGE`，避免回退到 Docker Hub 默认镜像名。检查服务：`sudo bash scripts/check_production.sh`，健康接口：`curl -fsS http://localhost:8000/health`。创建首个管理员：`sudo docker compose exec -it api python scripts/create_admin.py --username admin`。

客户端入口为 `/login`，管理端入口为 `/admin/login`。注册和密码重置默认需要管理员审批。生产备份使用 `sudo bash scripts/backup_mysql.sh`；数据库备份不能替代文档卷和 Qdrant 卷备份。

## CI/CD

`Pull Request -> CI 测试/构建 -> 合并 main -> 构建并发布 GHCR -> Windows Runner SSH 到 Ubuntu VM -> 拉取 SHA 镜像 -> Compose 更新 -> /health 验证`。发布前确认 Runner 在线、SSH 别名 `enterprise-rag-vm` 可用、GHCR 令牌有效、虚拟机 `.env` 和外部卷存在。镜像下载依赖 VM 到 GHCR 的网络连通性；部署脚本会先探测仓库连接，并限制每次拉取的超时与重试次数。

## 文档索引

- [`docs/需求与实施计划.md`](docs/需求与实施计划.md)：需求清单、实现范围、实施阶段和后续边界
- [`docs/开发测试与验收报告.md`](docs/开发测试与验收报告.md)：开发流程、测试证据、验收项和当前结论
- [`docs/部署与运维手册.md`](docs/部署与运维手册.md)：环境配置、GHCR 发布、生产部署、备份、回滚和故障处理
- [`docs/架构与接口说明.md`](docs/架构与接口说明.md)：服务架构、文档与问答流程、权限模型和 API 边界

## 许可证

本项目使用 [MIT License](LICENSE) 发布。
