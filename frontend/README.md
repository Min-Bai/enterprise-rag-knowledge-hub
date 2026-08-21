# RAG 知识库问答系统前端

`frontend` 是基于 React 和 Vite 构建的知识库工作台。它提供登录、知识库切换、文档管理、标签筛选、检索、流式问答、来源引用、多轮对话、角色协作和审计日志等界面。

## 本地开发

先安装依赖：

```bash
npm install
```

启动本地开发服务器：

```bash
npm run dev
```

开发服务器会将 `/api` 请求代理到后端服务。请同时启动后端、Redis、Qdrant 和数据库，才能使用完整功能。

## 常用命令

```bash
npm run lint
npm run format:check
npm run format
npm run build
```

- `lint`：检查前端代码规范。
- `format:check`：检查代码格式是否符合 Prettier 规则。
- `format`：自动格式化 `src` 下的前端代码。
- `build`：构建生产环境静态资源。
