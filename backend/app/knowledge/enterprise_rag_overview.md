# RAG 知识库问答系统项目知识

## 身份认证

用户通过 `POST /auth/login` 提交用户名和密码登录。登录成功后会返回 JWT 访问令牌。受保护接口使用 `Authorization: Bearer <token>` 请求头；无效令牌返回 HTTP 401，权限不足返回 HTTP 403。

## 知识库与文档

每个知识库都属于一个用户。文档会上传到选定的知识库中，持久化保存后由 Celery Worker 后台处理，依次完成文本分块、向量嵌入和 Qdrant 索引。文档状态依次为 `uploaded`、`processing`、`ready` 或 `failed`。

## RAG 回答

文档问答接口会从 Qdrant 检索相关文本块，应用最低相似度阈值，再利用命中的上下文生成回答。响应会包含来源文本块，用户可以核实回答依据。

## 运维

MySQL 保存关系型应用数据；Redis 提供 Celery 队列和限流；Qdrant 保存向量数据。`/health` 接口会检查 MySQL、Redis 和 Qdrant 是否就绪。
