function WorkspaceHeader({
  apiStatus,
  isAuthenticated,
  isLoggingOut,
  onLogout,
}) {
  return (
    <header className="app-header">
      <div>
        <p className="product-kicker">企业知识库</p>
        <h1>RAG 智能问答工作台</h1>
        <p className={apiStatus.isError ? "api-status error" : "api-status"}>
          {apiStatus.message}
        </p>
      </div>
      {isAuthenticated && (
        <button
          className="logout-button"
          type="button"
          disabled={isLoggingOut}
          onClick={onLogout}
        >
          {isLoggingOut ? "正在退出..." : "退出登录"}
        </button>
      )}
    </header>
  );
}

export default WorkspaceHeader;
