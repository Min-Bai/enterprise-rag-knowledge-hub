function ConversationControls({
  conversations,
  selectedConversationId,
  onSelect,
  onDelete,
  isDeleting,
}) {
  return (
    <div className="conversation-controls">
      <label htmlFor="conversation-select">Conversation</label>
      <select
        id="conversation-select"
        value={selectedConversationId}
        onChange={(event) => onSelect(event.target.value)}
      >
        <option value="">New conversation</option>
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
          {isDeleting ? "Deleting..." : "Delete conversation"}
        </button>
      )}
    </div>
  );
}

export default ConversationControls;
