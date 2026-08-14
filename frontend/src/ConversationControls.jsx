function ConversationControls({
  conversations,
  selectedConversationId,
  onSelect,
  onDelete,
  isDeleting,
  hasMore,
  onLoadMore,
  isLoadingMore,
}) {
  return (
    <div className="conversation-controls">
      <label htmlFor="conversation-select">历史对话</label>
      <select
        id="conversation-select"
        value={selectedConversationId}
        onChange={(event) => onSelect(event.target.value)}
      >
        <option value="">新建对话</option>
        {conversations.map((conversation) => (
          <option key={conversation.id} value={conversation.id}>
            {conversation.label}
          </option>
        ))}
      </select>
      {selectedConversationId && (
        <button
          type="button"
          className="delete-button"
          disabled={isDeleting}
          onClick={onDelete}
        >
          {isDeleting ? "正在删除..." : "删除当前对话"}
        </button>
      )}
      {hasMore && (
        <button type="button" disabled={isLoadingMore} onClick={onLoadMore}>
          {isLoadingMore ? "正在加载..." : "加载更多对话"}
        </button>
      )}
    </div>
  );
}

export default ConversationControls;
