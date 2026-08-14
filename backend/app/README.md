# 企业级 RAG 知识库问答系统后端

`backend/app` 是企业级 RAG 知识库问答系统的 FastAPI 后端应用。

```text
backend/app/
|- main.py                 FastAPI 应用入口
|- config.py               环境配置
|- database.py             SQLAlchemy 数据库引擎和会话
|- auth.py                 身份认证依赖项
|- security.py             密码哈希和 JWT 工具
|- rate_limit.py           基于 Redis 的限流
|- models/                 SQLAlchemy ORM 模型
|- schemas/                Pydantic 请求与响应模型
|- routers/                HTTP 接口
|- services/               业务逻辑和 RAG 处理逻辑
|- migrations/             Alembic 数据库迁移
|- knowledge/              可被 RAG 检索的项目知识
|- celery_app.py           Celery 应用和 Worker 启动恢复逻辑
|- tasks/                  Celery 后台任务
`- tests/                  自动化测试
```

## 本地运行

```bash
uvicorn backend.app.main:app --reload
```

## 运行测试

```bash
python -m pytest backend/app/tests -q
```
