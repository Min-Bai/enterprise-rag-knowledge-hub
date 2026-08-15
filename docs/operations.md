# 生产环境运维手册

所有命令都应在生产环境仓库目录 `~/enterprise-rag-knowledge-hub` 中执行。

## 每日检查

```bash
sudo bash scripts/check_production.sh
```

该检查会验证 Docker Compose 服务状态、Celery Worker、队列积压、API 依赖、磁盘容量和最新备份。

## 部署

CI 通过后，部署当前检出的 `main` 分支：

```bash
sudo bash scripts/deploy_enterprise_rag.sh
```

脚本会重新构建 API、Worker 和前端，然后等待 `/health` 健康检查通过。部署失败时，优先查看 API 和 Worker 日志：

```bash
sudo docker compose logs api --tail 100
sudo docker compose logs worker --tail 100
```

### 从 RQ 首次切换到 Celery

部署包含 Celery 的第一个版本前，先停止旧 RQ Worker。然后使用 `scripts/requeue_uploaded_documents.py` 预览状态为 `uploaded` 的文档；确认旧 Worker 已停止后，使用 `--execute` 将这些文档投递到 Celery。旧 RQ 队列任务不会被 Celery 自动消费，因此该步骤不能跳过。

## 备份与恢复验证

手动或通过定时任务创建备份：

```bash
sudo bash scripts/backup_mysql.sh
```

在依赖备份进行恢复前，应先将备份恢复到临时数据库验证。测试时绝不能覆盖生产数据库。

## 常见故障处理

| 现象 | 首先执行的操作 |
| --- | --- |
| API 健康检查失败 | 查看 API 日志，以及 MySQL、Redis、Qdrant 服务状态。 |
| 文档长期处于 `uploaded` 或 `processing` | 查看 Celery Worker 日志和 Celery 队列；Worker 恢复后在工作台中重试。 |
| 文档状态为 `failed` | 阅读文档错误信息，修复输入文件或依赖问题后重试。 |
| 检索质量下降 | 修改分块、嵌入模型或分数阈值前，先运行已版本控制的检索评估。 |
| 磁盘空间不足 | 删除任何内容前，先检查 Docker 镜像、备份保留策略和文档卷占用。 |

## 安全操作

- `backend/app/.env` 必须排除在 Git 之外；MySQL 应用账户和 root 账户必须使用不同密码。
- 默认禁止自助注册。使用 `scripts/create_admin.py` 创建首个管理员；确认身份后使用 `scripts/promote_user.py` 提升已有用户。
- 不要将 MySQL 暴露到公网。数据库管理访问应通过 SSH 隧道完成。
# Enterprise RAG operations

## Authentication configuration

Set `APP_ENV=production` and `AUTH_COOKIE_SECURE=true` in production. The v1 APIs issue
short-lived Bearer access tokens and keep refresh tokens only in HttpOnly cookies. Never copy
refresh cookies, JWTs, or `.env` values into tickets, browser storage, or logs.

## API boundaries

- Client API and documentation: `/api/v1/client`, `/api/v1/client/docs`, `/openapi/client.json`
- Admin API and documentation: `/api/v1/admin`, `/api/v1/admin/docs`, `/openapi/admin.json`
- Liveness: `/health/live`; readiness: `/health/ready`

`flower` is an optional operations profile and binds only to `127.0.0.1:5555`:

```bash
docker compose --profile operations up -d flower
```

Do not expose Flower through a public port. Use a private tunnel or reverse proxy with explicit
administrator authentication when operational access is required.
