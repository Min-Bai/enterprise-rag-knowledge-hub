# 企业级 RAG 知识库问答系统

> FastAPI + Vue 3 + MySQL + Redis + Celery + Qdrant + DeepSeek

## API 与工作区

- 用户工作台：`/app/chat`
- 管理工作台：`/admin/users`
- Client API：`/api/v1/client`，文档：`/api/v1/client/docs`
- Admin API：`/api/v1/admin`，文档：`/api/v1/admin/docs`

新版认证使用短期 Access Token 和 HttpOnly Refresh Cookie。两个 API 使用不同 audience，用户令牌不能调用管理端接口，刷新令牌不会被写入浏览器存储。

这是一个面向企业内部资料的知识库问答系统，采用 FastAPI、React、MySQL、Redis、Celery、Qdrant 和 Docker Compose 构建。系统支持私有文档处理、LangChain 递归文本切分、向量检索，以及带 PDF 页码引用的可信 RAG 回答。

用户可以在一个知识库的全部就绪文档中提问，也可以将问题限定在单篇文档。LangChain 提示词模板会将检索到的参考资料与模型指令隔离后再发送给 DeepSeek；多轮对话始终绑定当前选择的知识库或文档。

## 已实现功能

- 私有知识库，包含所有者、编辑者和查看者三种协作角色。
- PDF、Word（DOCX）、Excel（XLSX）、TXT、Markdown、CSV 格式校验，同知识库内的 SHA-256 重复文件检测，以及受权限保护的原文件下载。
- 后台文档文本与表格提取、LangChain 递归分块、向量嵌入、Qdrant 混合检索索引，以及失败重试和重新索引。
- 文档标签：用于分类、向量检索过滤和 RAG 回答过滤。修改已就绪文档的标签会自动重建向量，保证元数据与检索结果一致。
- 文档列表展示处理状态、分块数量和最近一次成功索引时间。
- 基于 DeepSeek 的知识库问答和单文档问答，支持 SSE 流式输出、来源引用、多轮对话和引用追问。
- 检索结果支持标签过滤、命中片段、页码和相关性分数。
- 回答反馈汇总、检索质量评估、结构化审计日志，以及 MySQL 备份和恢复验证脚本。

## 核心流程

### 文档处理流程

```text
上传文档 -> SHA-256 重复检查 -> uploaded -> Redis/Celery
    -> processing -> 内容/表格提取与分块 -> 向量嵌入 -> Qdrant -> ready
                                              \-> failed -> 重试
```

文档列表会显示最终分块数量和索引完成时间。对已就绪文档重新索引或修改标签时，系统会先删除旧向量，再由后台任务创建新的索引。

### 可信问答流程

```text
问题 + 可选标签 -> 权限验证 -> Qdrant 过滤检索
    -> 相关性阈值 -> LangChain 提示词 -> DeepSeek SSE 流式回答
    -> 对话记录和引用来源写入 MySQL
```

来源信息包含可用的 PDF 页码。用户可以搜索匹配的文本片段、打开自己有权访问的原始 PDF，或直接切换到被引用的文档继续针对性追问。

## 系统架构

```text
React 前端
    |
    v
Nginx /api 代理
    |
    v
FastAPI API ---- MySQL
    |               |
    |               +-- 用户、知识库、文档
    |
+-- Redis / Celery 队列 --> Celery Worker --> Qdrant
```

文档状态流转：

```text
上传 -> uploaded -> Redis 队列 -> processing -> ready / failed
```

后台 Worker 会校验文档、提取文本、切分文本块、生成向量，并将向量写入 Qdrant。失败的文档可以重试。编辑者在修改文档处理或嵌入相关设置后，可以重新索引已就绪文档；重新索引会清除该文档的旧向量并创建新的后台处理任务。

上传时会对 PDF 内容计算指纹，并拒绝同一知识库中的相同文件，从而避免重复向量和重复检索结果。每次提问都会保存问题、回答和引用来源；追问只使用该用户在当前知识库或文档范围内最近的对话历史。

知识库默认私有。所有者可按用户名共享知识库：编辑者可以上传、重试和删除文档；查看者只能阅读、搜索和提问。API 会对每次知识库、文档和检索请求执行角色权限校验。

## 服务说明

| 服务 | 职责 |
| --- | --- |
| `frontend` | 由 Nginx 提供服务的 React 前端 |
| `api` | FastAPI REST API 和 Alembic 数据库迁移 |
| `worker` | Celery 文档后台处理进程 |
| `mysql` | 持久化关系型数据 |
| `redis` | Celery 队列和限流数据 |
| `qdrant` | 文档向量检索 |

## 配置

将根目录 `.env.example` 复制为根目录 `.env`，然后填写真实的密钥和密码。不要提交 `.env` 文件。前端开发代理可选配置位于 `frontend/.env.example`，复制为 `frontend/.env.local` 后按需修改。

生产数据库必填配置：

```env
MYSQL_DATABASE=enterprise_rag
MYSQL_USER=enterprise_rag
MYSQL_PASSWORD=replace-with-a-private-password
MYSQL_ROOT_PASSWORD=replace-with-a-different-private-password
DATABASE_URL=mysql+pymysql://enterprise_rag:replace-with-a-private-password@mysql:3306/enterprise_rag?charset=utf8mb4
MAX_DOCUMENT_SIZE_MB=10
```

PDF 上传大小默认限制为 10 MB。只有在确认 API、Worker 和存储资源能够承载更大文件时，才提高 `MAX_DOCUMENT_SIZE_MB`。

`RAG_QUERY_REWRITE_ENABLED` 默认是 `false`。只有在评估集上测量过检索质量后才开启：开启后，每个问题在向量检索前会额外调用一次 DeepSeek；改写失败时会安全地回退到原问题。

## 使用 Docker Compose 运行

首次在生产环境启动前，需要先创建持久化卷：

```bash
for volume in \
  enterprise-rag-api-data \
  enterprise-rag-document-data \
  enterprise-rag-model-cache \
  enterprise-rag-mysql-data \
  enterprise-rag-redis-data \
  enterprise-rag-qdrant-data; do
  docker volume create "$volume"
done
```

然后启动所有服务：

```bash
docker compose up -d --build
docker compose ps
```

新部署完成且 API 已启动后，请在交互式终端创建第一个管理员。命令会提示输入密码，因此密码不会出现在命令行历史中：

```bash
docker compose exec -it api python scripts/create_admin.py --username admin
```

确认身份后，可将已有用户提升为管理员：

```bash
docker compose exec -it api python scripts/promote_user.py --username username
```

客户端注册会创建待审批申请，不会直接创建账号。管理员在管理端“账户审批”中批准后，系统才会创建普通成员账号和默认知识库。客户端密码重置同样先提交申请，再由管理员生成一次性限时链接。`ALLOW_REGISTRATION_REQUESTS=true` 控制是否接受新的注册申请；遗留 `/users` 接口的 `ALLOW_SELF_REGISTRATION` 必须保持 `false`，不要用它开放账号创建。

API 会在启动时执行 Alembic 数据库迁移。健康检查接口：

```text
GET /health/live
GET /health/ready
GET /health
```

前端服务端口是 `8080`，API 服务端口是 `8000`。

## 测试

```bash
python -m pytest backend/app/tests -q
```

测试使用隔离的 SQLite 数据库；开发和生产环境的应用数据使用 MySQL。

## 检索评估

在修改分块策略、嵌入模型或相关性阈值之前，应使用一组小规模、已版本控制的代表性问题评估检索质量。复制 `backend/app/evaluations/retrieval_cases.example.json`，将示例 ID 替换为非生产评估知识库中的文档，并为每个问题标记预期的文档页码或准确文本块。

在可访问 Qdrant 和嵌入模型的环境中执行评估：

```bash
python scripts/evaluate_retrieval.py path/to/retrieval_cases.json --k 3 \
  --output reports/retrieval-baseline.json \
  --min-recall-at-k 0.8 --min-mrr-at-k 0.6
```

报告包含 `recall_at_k`、`mrr_at_k` 和失败用例名称。该工具只读取向量，不会修改文档、Qdrant 或 MySQL；它会记录评估数据集哈希值，使不同报告可比较。可选的最低指标参数会在检索质量下降时使命令失败。

## 备份

部署、备份、恢复验证、故障处理和安全操作请查看[生产运维手册](docs/operations.md)。

在生产服务器上手动创建 MySQL 备份：

```bash
set -a
source .env
set +a

sudo docker compose exec -T -e MYSQL_PWD="$MYSQL_PASSWORD" mysql \
  mysqldump --no-tablespaces --single-transaction \
  -u"$MYSQL_USER" "$MYSQL_DATABASE" \
  > ~/backups/enterprise-rag/enterprise_rag-mysql-$(date +%F).sql
```

日常检查请在生产环境仓库目录执行辅助脚本：

```bash
sudo bash scripts/check_production.sh
sudo bash scripts/backup_mysql.sh
```

生产检查会确认 Celery 文档 Worker 容器正在运行，并输出已注册的 Celery Worker 数量和待处理文档任务数，随后检查 API 健康状态和备份。

## 从 RQ 切换到 Celery

首次部署包含 Celery 的版本前，应先停止旧 RQ Worker，并检查是否存在状态为 `uploaded` 的文档。旧 RQ 队列中的任务不会被 Celery 自动读取。使用下列命令先预览待迁移文档；确认旧 Worker 已停止后，再加上 `--execute` 将文档重新投递到 Celery：

```bash
sudo docker compose run --rm --no-deps api \
  python scripts/requeue_uploaded_documents.py

sudo docker compose run --rm --no-deps api \
  python scripts/requeue_uploaded_documents.py --execute
```

该脚本应只在 RQ 到 Celery 的首次切换时执行一次。日常部署不需要运行它。

应定期将最新备份恢复到临时数据库并比较表记录数量。单独的 `mysqldump` 成功并不能证明恢复一定成功。

## 生产资源迁移

仓库提供 `scripts/migrate_production_resources.sh`，用于从旧 Todo 部署一次性迁移到本项目。脚本会创建新的 `enterprise-rag-*` Docker 卷和 `enterprise_rag` MySQL 数据库，复制 MySQL、文档、Qdrant 和模型缓存数据，并保留旧资源以便回退。Redis 会有意以空队列启动。

只应在该版本已合并、且自动部署工作流已关闭后，在生产虚拟机运行此脚本。迁移前不要更新旧的 `~/todo-api` 仓库，因为脚本需要读取旧 Compose 资源。请将当前仓库克隆到临时目录后再执行：

```bash
git clone https://github.com/Min-Bai/enterprise-rag-knowledge-hub.git \
  ~/enterprise-rag-migration

cd ~/enterprise-rag-migration
bash scripts/migrate_production_resources.sh
```

迁移完成后，更新 Windows Runner 的 SSH 配置，使同一台虚拟机可通过 `enterprise-rag-vm` 主机别名访问。部署工作流使用该别名和 `~/deploy-enterprise-rag.sh`。
