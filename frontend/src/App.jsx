import { useEffect, useState } from "react";
import "./App.css";
import {
  addKnowledgeBaseMember,
  createKnowledgeBase,
  deleteDocument,
  deleteConversation,
  downloadDocument,
  deleteKnowledgeBase,
  getApiHealth,
  getDocumentConversations,
  getKnowledgeBaseConversations,
  getKnowledgeBaseAuditLogs,
  getKnowledgeBaseFeedbackSummary,
  getKnowledgeBaseMembers,
  getKnowledgeBases,
  getMyDocuments,
  login,
  logout,
  removeKnowledgeBaseMember,
  reindexDocument,
  retryDocument,
  searchDocuments,
  streamDocumentAnswer,
  streamKnowledgeBaseAnswer,
  submitAnswerFeedback,
  uploadDocument,
  updateDocumentTags,
  updateKnowledgeBase,
} from "./api.js";
import LoginForm from "./LoginForm.jsx";
import ConversationControls from "./ConversationControls.jsx";
import WorkspaceHeader from "./WorkspaceHeader.jsx";

function getConversationLabel(conversation) {
  const question = conversation.messages
    ?.find((message) => message.role === "user")
    ?.content?.trim();
  if (!question) return `Conversation ${conversation.id}`;
  return question.length > 48 ? `${question.slice(0, 48)}...` : question;
}

function getRoleLabel(role) {
  return { owner: "所有者", editor: "编辑者", viewer: "查看者" }[role] || role;
}

function getDocumentStatusLabel(status) {
  return (
    {
      uploaded: "待处理",
      processing: "处理中",
      ready: "已就绪",
      failed: "处理失败",
    }[status] || status
  );
}

function App() {
  const [accessToken, setAccessToken] = useState(() =>
    sessionStorage.getItem("access_token"),
  );
  const [apiStatus, setApiStatus] = useState({
    message: "正在检查 API 状态...",
    isError: false,
  });
  const [knowledgeBases, setKnowledgeBases] = useState([]);
  const [selectedKnowledgeBaseId, setSelectedKnowledgeBaseId] = useState("");
  const [knowledgeBaseName, setKnowledgeBaseName] = useState("");
  const [knowledgeBaseDescription, setKnowledgeBaseDescription] = useState("");
  const [knowledgeBaseError, setKnowledgeBaseError] = useState("");
  const [knowledgeBaseMembers, setKnowledgeBaseMembers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [hasMoreAuditLogs, setHasMoreAuditLogs] = useState(false);
  const [isLoadingMoreAuditLogs, setIsLoadingMoreAuditLogs] = useState(false);
  const [feedbackSummary, setFeedbackSummary] = useState(null);
  const [memberUsername, setMemberUsername] = useState("");
  const [memberRole, setMemberRole] = useState("viewer");
  const [isCreatingKnowledgeBase, setIsCreatingKnowledgeBase] = useState(false);
  const [isEditingKnowledgeBase, setIsEditingKnowledgeBase] = useState(false);
  const [editingKnowledgeBase, setEditingKnowledgeBase] = useState(false);
  const [editKnowledgeBaseName, setEditKnowledgeBaseName] = useState("");
  const [editKnowledgeBaseDescription, setEditKnowledgeBaseDescription] =
    useState("");
  const [deletingKnowledgeBaseId, setDeletingKnowledgeBaseId] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [hasMoreDocuments, setHasMoreDocuments] = useState(false);
  const [isLoadingMoreDocuments, setIsLoadingMoreDocuments] = useState(false);
  const [documentFile, setDocumentFile] = useState(null);
  const [documentTags, setDocumentTags] = useState("");
  const [documentUploadError, setDocumentUploadError] = useState("");
  const [searchQuestion, setSearchQuestion] = useState("");
  const [searchTags, setSearchTags] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searchError, setSearchError] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [isUploadingDocument, setIsUploadingDocument] = useState(false);
  const [deletingDocumentId, setDeletingDocumentId] = useState(null);
  const [retryingDocumentId, setRetryingDocumentId] = useState(null);
  const [reindexingDocumentId, setReindexingDocumentId] = useState(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [answerScope, setAnswerScope] = useState("knowledge-base");
  const [documentQuestion, setDocumentQuestion] = useState("");
  const [answerTags, setAnswerTags] = useState("");
  const [documentAnswer, setDocumentAnswer] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [hasMoreConversations, setHasMoreConversations] = useState(false);
  const [isLoadingMoreConversations, setIsLoadingMoreConversations] =
    useState(false);
  const [selectedConversationId, setSelectedConversationId] = useState("");
  const [deletingConversationId, setDeletingConversationId] = useState(null);
  const [documentAnswerError, setDocumentAnswerError] = useState("");
  const [isAnsweringDocument, setIsAnsweringDocument] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const readyDocuments = documents.filter(
    (document) => document.status === "ready",
  );
  const hasPendingDocuments = documents.some((document) =>
    ["uploaded", "processing"].includes(document.status),
  );
  const selectedKnowledgeBase = knowledgeBases.find(
    (item) => String(item.id) === selectedKnowledgeBaseId,
  );
  const selectedKnowledgeBaseRole = selectedKnowledgeBase?.role || "viewer";
  const canManageKnowledgeBase = selectedKnowledgeBaseRole === "owner";
  const canManageDocuments = ["owner", "editor"].includes(
    selectedKnowledgeBaseRole,
  );

  function clearSession() {
    sessionStorage.removeItem("access_token");
    setAccessToken(null);
  }

  async function refreshAuditLogs(knowledgeBaseId = selectedKnowledgeBaseId) {
    if (!accessToken || !knowledgeBaseId) return;
    try {
      const data = await getKnowledgeBaseAuditLogs(
        accessToken,
        knowledgeBaseId,
      );
      setAuditLogs(data);
      setHasMoreAuditLogs(data.length === 100);
    } catch (error) {
      if (error.status === 401) clearSession();
    }
  }

  async function handleLoadMoreAuditLogs() {
    setIsLoadingMoreAuditLogs(true);
    try {
      const data = await getKnowledgeBaseAuditLogs(
        accessToken,
        selectedKnowledgeBaseId,
        auditLogs.length,
      );
      setAuditLogs((current) => [
        ...current,
        ...data.filter(
          (item) => !current.some((event) => event.id === item.id),
        ),
      ]);
      setHasMoreAuditLogs(data.length === 100);
    } catch (error) {
      setKnowledgeBaseError(error.message);
    } finally {
      setIsLoadingMoreAuditLogs(false);
    }
  }

  useEffect(() => {
    getApiHealth()
      .then((data) =>
        setApiStatus({
          message: `服务正常，数据库：${data.database}`,
          isError: false,
        }),
      )
      .catch(() =>
        setApiStatus({ message: "API 服务暂不可用", isError: true }),
      );
  }, []);

  useEffect(() => {
    if (!accessToken) {
      setKnowledgeBases([]);
      setDocuments([]);
      return;
    }
    getKnowledgeBases(accessToken)
      .then((data) => {
        setKnowledgeBases(data);
        setSelectedKnowledgeBaseId(
          (current) => current || (data[0] ? String(data[0].id) : ""),
        );
      })
      .catch((error) => {
        if (error.status === 401) clearSession();
        else setKnowledgeBaseError(error.message);
      });
  }, [accessToken]);

  useEffect(() => {
    if (!accessToken || !selectedKnowledgeBaseId) {
      setDocuments([]);
      setHasMoreDocuments(false);
      return;
    }
    let cancelled = false;
    async function loadDocuments() {
      try {
        const data = await getMyDocuments(accessToken, selectedKnowledgeBaseId);
        if (cancelled) return;
        setDocuments(data);
        setHasMoreDocuments(data.length === 100);
        setSelectedDocumentId((current) =>
          data.some((document) => String(document.id) === current)
            ? current
            : String(
                data.find((document) => document.status === "ready")?.id ?? "",
              ),
        );
      } catch (error) {
        if (error.status === 401) clearSession();
        else setDocumentUploadError(error.message);
      }
    }
    loadDocuments();
    return () => {
      cancelled = true;
    };
  }, [accessToken, selectedKnowledgeBaseId]);

  useEffect(() => {
    if (!accessToken || !selectedKnowledgeBaseId) {
      setFeedbackSummary(null);
      return;
    }
    getKnowledgeBaseFeedbackSummary(accessToken, selectedKnowledgeBaseId)
      .then(setFeedbackSummary)
      .catch((error) => {
        if (error.status === 401) clearSession();
        else if (error.status === 403) setFeedbackSummary(null);
        else setKnowledgeBaseError(error.message);
      });
  }, [accessToken, selectedKnowledgeBaseId]);

  useEffect(() => {
    if (!accessToken || !selectedKnowledgeBaseId) {
      setAuditLogs([]);
      return;
    }
    getKnowledgeBaseAuditLogs(accessToken, selectedKnowledgeBaseId)
      .then(setAuditLogs)
      .catch((error) => {
        if (error.status === 401) clearSession();
        else if (error.status === 403) setAuditLogs([]);
        else setKnowledgeBaseError(error.message);
      });
  }, [accessToken, selectedKnowledgeBaseId]);

  useEffect(() => {
    if (!accessToken || !selectedKnowledgeBaseId) {
      setKnowledgeBaseMembers([]);
      return;
    }
    getKnowledgeBaseMembers(accessToken, selectedKnowledgeBaseId)
      .then(setKnowledgeBaseMembers)
      .catch((error) => {
        if (error.status === 401) clearSession();
        else if (error.status !== 403) setKnowledgeBaseError(error.message);
        else setKnowledgeBaseMembers([]);
      });
  }, [accessToken, selectedKnowledgeBaseId]);

  useEffect(() => {
    if (!accessToken || !selectedKnowledgeBaseId || !hasPendingDocuments)
      return undefined;
    const timer = window.setInterval(async () => {
      try {
        const data = await getMyDocuments(accessToken, selectedKnowledgeBaseId);
        setDocuments(data);
      } catch (error) {
        if (error.status === 401) clearSession();
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [accessToken, selectedKnowledgeBaseId, hasPendingDocuments]);

  useEffect(() => {
    const scopeId =
      answerScope === "knowledge-base"
        ? selectedKnowledgeBaseId
        : selectedDocumentId;
    if (!accessToken || !scopeId) {
      setConversations([]);
      setSelectedConversationId("");
      setHasMoreConversations(false);
      return;
    }
    const loadConversations =
      answerScope === "knowledge-base"
        ? getKnowledgeBaseConversations
        : getDocumentConversations;
    loadConversations(accessToken, scopeId)
      .then((data) => {
        setConversations(data);
        setHasMoreConversations(data.length === 100);
      })
      .catch((error) => {
        if (error.status === 401) clearSession();
        else setDocumentAnswerError(error.message);
      });
  }, [accessToken, answerScope, selectedDocumentId, selectedKnowledgeBaseId]);

  async function handleLogin(username, password) {
    const data = await login(username, password);
    sessionStorage.setItem("access_token", data.access_token);
    setAccessToken(data.access_token);
  }

  async function handleLogout() {
    setIsLoggingOut(true);
    try {
      await logout(accessToken);
    } finally {
      clearSession();
      setIsLoggingOut(false);
    }
  }

  async function handleLoadMoreConversations() {
    const scopeId =
      answerScope === "knowledge-base"
        ? selectedKnowledgeBaseId
        : selectedDocumentId;
    const loadConversations =
      answerScope === "knowledge-base"
        ? getKnowledgeBaseConversations
        : getDocumentConversations;
    setIsLoadingMoreConversations(true);
    try {
      const data = await loadConversations(
        accessToken,
        scopeId,
        conversations.length,
      );
      setConversations((current) => [
        ...current,
        ...data.filter(
          (item) =>
            !current.some((conversation) => conversation.id === item.id),
        ),
      ]);
      setHasMoreConversations(data.length === 100);
    } catch (error) {
      setDocumentAnswerError(error.message);
    } finally {
      setIsLoadingMoreConversations(false);
    }
  }

  async function handleCreateKnowledgeBase(event) {
    event.preventDefault();
    setIsCreatingKnowledgeBase(true);
    setKnowledgeBaseError("");
    try {
      const knowledgeBase = await createKnowledgeBase(
        accessToken,
        knowledgeBaseName.trim(),
        knowledgeBaseDescription.trim(),
      );
      setKnowledgeBases((current) => [...current, knowledgeBase]);
      setSelectedKnowledgeBaseId(String(knowledgeBase.id));
      await refreshAuditLogs(knowledgeBase.id);
      setKnowledgeBaseName("");
      setKnowledgeBaseDescription("");
    } catch (error) {
      setKnowledgeBaseError(error.message);
    } finally {
      setIsCreatingKnowledgeBase(false);
    }
  }

  async function handleDeleteKnowledgeBase() {
    const knowledgeBase = knowledgeBases.find(
      (item) => String(item.id) === selectedKnowledgeBaseId,
    );
    if (
      !knowledgeBase ||
      !window.confirm(`确定删除知识库“${knowledgeBase.name}”吗？`)
    )
      return;
    setDeletingKnowledgeBaseId(knowledgeBase.id);
    try {
      await deleteKnowledgeBase(accessToken, knowledgeBase.id);
      const remaining = knowledgeBases.filter(
        (item) => item.id !== knowledgeBase.id,
      );
      setKnowledgeBases(remaining);
      setSelectedKnowledgeBaseId(remaining[0] ? String(remaining[0].id) : "");
    } catch (error) {
      setKnowledgeBaseError(error.message);
    } finally {
      setDeletingKnowledgeBaseId(null);
    }
  }

  function startEditingKnowledgeBase() {
    const knowledgeBase = knowledgeBases.find(
      (item) => String(item.id) === selectedKnowledgeBaseId,
    );
    if (!knowledgeBase) return;
    setEditKnowledgeBaseName(knowledgeBase.name);
    setEditKnowledgeBaseDescription(knowledgeBase.description || "");
    setEditingKnowledgeBase(true);
    setKnowledgeBaseError("");
  }

  async function handleUpdateKnowledgeBase(event) {
    event.preventDefault();
    if (!selectedKnowledgeBaseId) return;
    setIsEditingKnowledgeBase(true);
    setKnowledgeBaseError("");
    try {
      const updated = await updateKnowledgeBase(
        accessToken,
        Number(selectedKnowledgeBaseId),
        editKnowledgeBaseName.trim(),
        editKnowledgeBaseDescription.trim(),
      );
      setKnowledgeBases((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setEditingKnowledgeBase(false);
      await refreshAuditLogs(updated.id);
    } catch (error) {
      setKnowledgeBaseError(error.message);
    } finally {
      setIsEditingKnowledgeBase(false);
    }
  }

  async function handleAddMember(event) {
    event.preventDefault();
    setKnowledgeBaseError("");
    try {
      await addKnowledgeBaseMember(
        accessToken,
        Number(selectedKnowledgeBaseId),
        memberUsername.trim(),
        memberRole,
      );
      setKnowledgeBaseMembers(
        await getKnowledgeBaseMembers(accessToken, selectedKnowledgeBaseId),
      );
      setMemberUsername("");
      await refreshAuditLogs();
    } catch (error) {
      setKnowledgeBaseError(error.message);
    }
  }

  async function handleRemoveMember(userId) {
    try {
      await removeKnowledgeBaseMember(
        accessToken,
        Number(selectedKnowledgeBaseId),
        userId,
      );
      setKnowledgeBaseMembers(
        await getKnowledgeBaseMembers(accessToken, selectedKnowledgeBaseId),
      );
      await refreshAuditLogs();
    } catch (error) {
      setKnowledgeBaseError(error.message);
    }
  }

  async function handleUpload(event) {
    event.preventDefault();
    if (!documentFile) return;
    setIsUploadingDocument(true);
    setDocumentUploadError("");
    try {
      const tags = documentTags
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean);
      const document = await uploadDocument(
        accessToken,
        documentFile,
        Number(selectedKnowledgeBaseId),
        tags,
      );
      setDocuments((current) => [document, ...current]);
      await refreshAuditLogs(document.knowledge_base_id);
      setDocumentFile(null);
      setDocumentTags("");
      event.currentTarget.reset();
    } catch (error) {
      setDocumentUploadError(error.message);
    } finally {
      setIsUploadingDocument(false);
    }
  }

  async function handleDeleteDocument(documentId) {
    if (!window.confirm("确定删除这份文档吗？")) return;
    setDeletingDocumentId(documentId);
    try {
      await deleteDocument(accessToken, documentId);
      setDocuments((current) =>
        current.filter((item) => item.id !== documentId),
      );
      await refreshAuditLogs();
    } catch (error) {
      setDocumentUploadError(error.message);
    } finally {
      setDeletingDocumentId(null);
    }
  }

  async function handleRetryDocument(documentId) {
    setRetryingDocumentId(documentId);
    try {
      const document = await retryDocument(accessToken, documentId);
      setDocuments((current) =>
        current.map((item) => (item.id === documentId ? document : item)),
      );
      await refreshAuditLogs(document.knowledge_base_id);
    } catch (error) {
      setDocumentUploadError(error.message);
    } finally {
      setRetryingDocumentId(null);
    }
  }

  async function handleQuestion(event) {
    event.preventDefault();
    const question = documentQuestion.trim();
    setIsAnsweringDocument(true);
    setDocumentAnswerError("");
    setDocumentAnswer({ answer: "", sources: [] });
    try {
      let conversationId = selectedConversationId;
      let sources = [];
      let answer = "";
      const streamAnswer =
        answerScope === "knowledge-base"
          ? streamKnowledgeBaseAnswer
          : streamDocumentAnswer;
      const scopeId =
        answerScope === "knowledge-base"
          ? selectedKnowledgeBaseId
          : selectedDocumentId;
      const tags =
        answerScope === "knowledge-base"
          ? answerTags
              .split(",")
              .map((tag) => tag.trim())
              .filter(Boolean)
          : [];
      const streamArgs =
        answerScope === "knowledge-base"
          ? [
              accessToken,
              Number(scopeId),
              question,
              selectedConversationId,
              tags,
            ]
          : [accessToken, Number(scopeId), question, selectedConversationId];
      await streamAnswer(...streamArgs, {
        onMetadata: (data) => {
          conversationId = String(data.conversation_id);
          sources = data.sources || [];
          setSelectedConversationId(conversationId);
          setDocumentAnswer({ answer: "", sources });
        },
        onToken: (text) => {
          answer += text;
          setDocumentAnswer((current) => ({
            answer,
            sources: current?.sources || sources,
          }));
        },
      });
      const loadConversations =
        answerScope === "knowledge-base"
          ? getKnowledgeBaseConversations
          : getDocumentConversations;
      setConversations(await loadConversations(accessToken, scopeId));
    } catch (error) {
      setDocumentAnswerError(error.message);
    } finally {
      setIsAnsweringDocument(false);
    }
  }

  async function handleDeleteConversation() {
    const conversationId = Number(selectedConversationId);
    if (!conversationId || !window.confirm("确定删除当前对话及其全部消息吗？"))
      return;
    setDeletingConversationId(conversationId);
    setDocumentAnswerError("");
    try {
      await deleteConversation(accessToken, conversationId);
      setConversations((current) =>
        current.filter((conversation) => conversation.id !== conversationId),
      );
      setSelectedConversationId("");
      setDocumentAnswer(null);
    } catch (error) {
      setDocumentAnswerError(error.message);
    } finally {
      setDeletingConversationId(null);
    }
  }

  async function handleReindexDocument(documentId) {
    setReindexingDocumentId(documentId);
    setDocumentUploadError("");
    try {
      const document = await reindexDocument(accessToken, documentId);
      setDocuments((current) =>
        current.map((item) => (item.id === documentId ? document : item)),
      );
      await refreshAuditLogs(document.knowledge_base_id);
    } catch (error) {
      setDocumentUploadError(error.message);
    } finally {
      setReindexingDocumentId(null);
    }
  }

  async function handleEditDocumentTags(document) {
    const value = window.prompt(
      "请输入标签，多个标签请用英文逗号分隔",
      document.tags?.join(", ") || "",
    );
    if (value === null) return;
    setDocumentUploadError("");
    try {
      const tags = value
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean);
      const updated = await updateDocumentTags(accessToken, document.id, tags);
      setDocuments((current) =>
        current.map((item) => (item.id === document.id ? updated : item)),
      );
      await refreshAuditLogs(updated.knowledge_base_id);
    } catch (error) {
      setDocumentUploadError(error.message);
    }
  }

  async function handleDownloadDocument(document) {
    setDocumentUploadError("");
    try {
      await downloadDocument(accessToken, document);
    } catch (error) {
      setDocumentUploadError(error.message);
    }
  }

  async function handleLoadMoreDocuments() {
    setIsLoadingMoreDocuments(true);
    try {
      const data = await getMyDocuments(
        accessToken,
        selectedKnowledgeBaseId,
        documents.length,
      );
      setDocuments((current) => [
        ...current,
        ...data.filter(
          (item) => !current.some((document) => document.id === item.id),
        ),
      ]);
      setHasMoreDocuments(data.length === 100);
    } catch (error) {
      setDocumentUploadError(error.message);
    } finally {
      setIsLoadingMoreDocuments(false);
    }
  }

  async function handleSearch(event) {
    event.preventDefault();
    const question = searchQuestion.trim();
    if (!question || !selectedKnowledgeBaseId) return;
    setIsSearching(true);
    setSearchError("");
    try {
      const tags = searchTags
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean);
      const data = await searchDocuments(
        accessToken,
        Number(selectedKnowledgeBaseId),
        question,
        tags,
      );
      setSearchResults(data.items || []);
    } catch (error) {
      setSearchError(error.message);
    } finally {
      setIsSearching(false);
    }
  }

  function askAboutSearchResult(documentId) {
    setAnswerScope("document");
    setSelectedDocumentId(String(documentId));
    setSelectedConversationId("");
    setDocumentAnswer(null);
  }

  function askAboutSource(documentId) {
    askAboutSearchResult(documentId);
    setDocumentQuestion("");
  }

  async function handleFeedback(messageId, feedback) {
    setDocumentAnswerError("");
    const comment =
      feedback === "unhelpful" ? window.prompt("请说明需要改进的地方") : null;
    if (comment === null && feedback === "unhelpful") return;
    try {
      const updated = await submitAnswerFeedback(
        accessToken,
        messageId,
        feedback,
        comment,
      );
      setConversations((current) =>
        current.map((conversation) => ({
          ...conversation,
          messages: conversation.messages.map((message) =>
            message.id === updated.id ? updated : message,
          ),
        })),
      );
    } catch (error) {
      setDocumentAnswerError(error.message);
    }
  }

  return (
    <main className="app-shell">
      <WorkspaceHeader
        apiStatus={apiStatus}
        isAuthenticated={Boolean(accessToken)}
        isLoggingOut={isLoggingOut}
        onLogout={handleLogout}
      />
      {!accessToken ? (
        <LoginForm onLogin={handleLogin} />
      ) : (
        <section className="workspace" aria-label="知识库工作台">
          <div className="workspace-layout">
            <aside className="workspace-sidebar">
              <div className="knowledge-base-header">
                <div>
                  <h2>知识库</h2>
                  <p>管理私有资料，并基于来源进行可信问答。</p>
                </div>
                {canManageKnowledgeBase && (
                  <div className="knowledge-base-actions">
                    <button type="button" onClick={startEditingKnowledgeBase}>
                      编辑知识库
                    </button>
                    <button
                      type="button"
                      className="delete-button"
                      disabled={deletingKnowledgeBaseId !== null}
                      onClick={handleDeleteKnowledgeBase}
                    >
                      删除知识库
                    </button>
                  </div>
                )}
              </div>
              <div className="knowledge-base-select-row">
                <label htmlFor="knowledge-base-select">当前知识库</label>
                {selectedKnowledgeBase && (
                  <span className={`role-badge ${selectedKnowledgeBaseRole}`}>
                    {getRoleLabel(selectedKnowledgeBaseRole)}
                  </span>
                )}
              </div>
              <select
                id="knowledge-base-select"
                value={selectedKnowledgeBaseId}
                onChange={(event) => {
                  setSelectedKnowledgeBaseId(event.target.value);
                  setDocumentAnswer(null);
                }}
              >
                <option value="">请选择知识库</option>
                {knowledgeBases.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
              {canManageKnowledgeBase && editingKnowledgeBase && (
                <form
                  className="knowledge-base-form"
                  onSubmit={handleUpdateKnowledgeBase}
                >
                  <label htmlFor="edit-knowledge-base-name">知识库名称</label>
                  <input
                    id="edit-knowledge-base-name"
                    value={editKnowledgeBaseName}
                    maxLength={100}
                    onChange={(event) =>
                      setEditKnowledgeBaseName(event.target.value)
                    }
                  />
                  <label htmlFor="edit-knowledge-base-description">描述</label>
                  <textarea
                    id="edit-knowledge-base-description"
                    value={editKnowledgeBaseDescription}
                    maxLength={2000}
                    onChange={(event) =>
                      setEditKnowledgeBaseDescription(event.target.value)
                    }
                  />
                  <div className="knowledge-base-actions">
                    <button
                      type="submit"
                      disabled={
                        !editKnowledgeBaseName.trim() || isEditingKnowledgeBase
                      }
                    >
                      {isEditingKnowledgeBase ? "正在保存..." : "保存修改"}
                    </button>
                    <button
                      type="button"
                      className="logout-button"
                      disabled={isEditingKnowledgeBase}
                      onClick={() => setEditingKnowledgeBase(false)}
                    >
                      取消
                    </button>
                  </div>
                </form>
              )}
              <form
                className="knowledge-base-form"
                onSubmit={handleCreateKnowledgeBase}
              >
                <label htmlFor="knowledge-base-name">新建知识库</label>
                <input
                  id="knowledge-base-name"
                  value={knowledgeBaseName}
                  maxLength={100}
                  placeholder="例如：员工手册"
                  onChange={(event) => setKnowledgeBaseName(event.target.value)}
                />
                <label htmlFor="knowledge-base-description">描述</label>
                <textarea
                  id="knowledge-base-description"
                  value={knowledgeBaseDescription}
                  maxLength={2000}
                  placeholder="可选说明"
                  onChange={(event) =>
                    setKnowledgeBaseDescription(event.target.value)
                  }
                />
                <button
                  type="submit"
                  disabled={
                    !knowledgeBaseName.trim() || isCreatingKnowledgeBase
                  }
                >
                  {isCreatingKnowledgeBase ? "正在创建..." : "创建知识库"}
                </button>
              </form>
              {knowledgeBaseMembers.length > 0 && (
                <section className="knowledge-base-members">
                  <h2>成员协作</h2>
                  <form
                    className="knowledge-base-form"
                    onSubmit={handleAddMember}
                  >
                    <label htmlFor="member-username">用户名</label>
                    <input
                      id="member-username"
                      value={memberUsername}
                      maxLength={50}
                      onChange={(event) =>
                        setMemberUsername(event.target.value)
                      }
                    />
                    <label htmlFor="member-role">权限角色</label>
                    <select
                      id="member-role"
                      value={memberRole}
                      onChange={(event) => setMemberRole(event.target.value)}
                    >
                      <option value="viewer">查看者</option>
                      <option value="editor">编辑者</option>
                    </select>
                    <button type="submit" disabled={!memberUsername.trim()}>
                      添加成员
                    </button>
                  </form>
                  <ul className="document-list">
                    {knowledgeBaseMembers.map((member) => (
                      <li key={member.user_id} className="document-list-item">
                        <span>
                          {member.username}（{getRoleLabel(member.role)}）
                        </span>
                        {member.role !== "owner" && (
                          <button
                            type="button"
                            className="delete-button"
                            onClick={() => handleRemoveMember(member.user_id)}
                          >
                            移除
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                  {hasMoreAuditLogs && (
                    <button
                      type="button"
                      disabled={isLoadingMoreAuditLogs}
                      onClick={handleLoadMoreAuditLogs}
                    >
                      {isLoadingMoreAuditLogs
                        ? "正在加载..."
                        : "加载更多审计记录"}
                    </button>
                  )}
                </section>
              )}
              {auditLogs.length > 0 && (
                <section className="knowledge-base-members">
                  <h2>审计记录</h2>
                  <ul className="document-list">
                    {auditLogs.map((event) => (
                      <li key={event.id} className="document-list-item">
                        <div>
                          <strong>{event.action}</strong>
                          <span className="audit-actor">
                            {event.actor_username} · {event.target_type}
                            {event.target_id ? ` #${event.target_id}` : ""}
                          </span>
                          {event.details && (
                            <small className="audit-details">
                              {Object.entries(event.details)
                                .map(([key, value]) => `${key}: ${value}`)
                                .join(" · ")}
                            </small>
                          )}
                        </div>
                        <time dateTime={event.created_at}>
                          {new Date(event.created_at).toLocaleString()}
                        </time>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
              {feedbackSummary && (
                <section className="knowledge-base-members">
                  <h2>回答质量</h2>
                  <p>
                    共 {feedbackSummary.total_feedback} 次反馈，有帮助{" "}
                    {feedbackSummary.helpful_count} 次，无帮助{" "}
                    {feedbackSummary.unhelpful_count} 次
                    {feedbackSummary.helpful_rate !== null
                      ? `，好评率 ${Math.round(feedbackSummary.helpful_rate * 100)}%`
                      : ""}
                  </p>
                  {feedbackSummary.recent_unhelpful.length > 0 && (
                    <ul className="document-list">
                      {feedbackSummary.recent_unhelpful.map((item) => (
                        <li
                          key={item.message_id}
                          className="document-list-item"
                        >
                          <span>{item.comment || item.answer}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              )}
              {knowledgeBaseError && (
                <p className="form-error">{knowledgeBaseError}</p>
              )}
            </aside>
            <section className="workspace-documents" aria-label="文档与检索">
              <h2>文档与检索</h2>
              {canManageDocuments && (
                <form className="document-upload-form" onSubmit={handleUpload}>
                  <label htmlFor="document-file">上传 PDF</label>
                  <input
                    id="document-file"
                    type="file"
                    accept="application/pdf,.pdf"
                    onChange={(event) => {
                      setDocumentFile(event.target.files?.[0] ?? null);
                      setDocumentUploadError("");
                    }}
                  />
                  <label htmlFor="document-tags">标签</label>
                  <input
                    id="document-tags"
                    value={documentTags}
                    maxLength={500}
                    placeholder="人事制度, 员工手册, 技术规范"
                    onChange={(event) => setDocumentTags(event.target.value)}
                  />
                  <button
                    type="submit"
                    disabled={
                      !documentFile ||
                      !selectedKnowledgeBaseId ||
                      isUploadingDocument
                    }
                  >
                    {isUploadingDocument ? "正在上传..." : "上传文档"}
                  </button>
                </form>
              )}
              {documentUploadError && (
                <p className="form-error">{documentUploadError}</p>
              )}
              <section className="document-search" aria-label="搜索文档内容">
                <h2>检索内容</h2>
                <form onSubmit={handleSearch}>
                  <label htmlFor="search-question">检索问题</label>
                  <input
                    id="search-question"
                    value={searchQuestion}
                    maxLength={300}
                    placeholder="例如：查找与报销制度相关的内容"
                    onChange={(event) => setSearchQuestion(event.target.value)}
                  />
                  <label htmlFor="search-tags">按标签筛选</label>
                  <input
                    id="search-tags"
                    value={searchTags}
                    maxLength={500}
                    placeholder="人事制度, 员工手册"
                    onChange={(event) => setSearchTags(event.target.value)}
                  />
                  <button
                    type="submit"
                    disabled={
                      isSearching ||
                      !selectedKnowledgeBaseId ||
                      !searchQuestion.trim()
                    }
                  >
                    {isSearching ? "正在检索..." : "检索文档"}
                  </button>
                </form>
                {searchError && <p className="form-error">{searchError}</p>}
                {searchResults.length > 0 && (
                  <ul className="document-search-results">
                    {searchResults.map((result) => (
                      <li key={`${result.document_id}-${result.chunk_index}`}>
                        <div>
                          <strong>{result.filename}</strong>
                          <span>
                            {result.page ? `第 ${result.page} 页` : "文档内容"}{" "}
                            · 相关度 {Number(result.score).toFixed(2)}
                          </span>
                          <p>{result.text}</p>
                        </div>
                        <button
                          type="button"
                          onClick={() =>
                            askAboutSearchResult(result.document_id)
                          }
                        >
                          针对本文提问
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                {!isSearching &&
                  searchQuestion.trim() &&
                  searchResults.length === 0 &&
                  !searchError && <p>未找到匹配内容。</p>}
              </section>
              {documents.length > 0 && (
                <ul className="document-list" aria-label="已上传文档">
                  {documents.map((document) => (
                    <li key={document.id} className="document-list-item">
                      <div>
                        <strong>{document.filename}</strong>
                        <span className={`document-status ${document.status}`}>
                          {getDocumentStatusLabel(document.status)}
                        </span>
                        {document.tags?.length > 0 && (
                          <small className="document-tags">
                            {document.tags.join(" · ")}
                          </small>
                        )}
                        {document.status === "ready" && (
                          <small className="document-processing">
                            {document.chunk_count} 个文本块
                            {document.processed_at
                              ? ` · 已索引 ${new Date(document.processed_at).toLocaleString()}`
                              : ""}
                          </small>
                        )}
                        {document.error_message && (
                          <p className="document-error">
                            {document.error_message}
                          </p>
                        )}
                      </div>
                      <div className="document-actions">
                        <button
                          type="button"
                          onClick={() => handleDownloadDocument(document)}
                        >
                          下载
                        </button>
                        {canManageDocuments && (
                          <>
                            <button
                              type="button"
                              onClick={() => handleEditDocumentTags(document)}
                            >
                              编辑标签
                            </button>
                            {document.status === "ready" && (
                              <button
                                type="button"
                                disabled={reindexingDocumentId !== null}
                                onClick={() =>
                                  handleReindexDocument(document.id)
                                }
                              >
                                {reindexingDocumentId === document.id
                                  ? "正在重建..."
                                  : "重新索引"}
                              </button>
                            )}
                            {document.status === "failed" && (
                              <button
                                type="button"
                                className="retry-button"
                                disabled={retryingDocumentId !== null}
                                onClick={() => handleRetryDocument(document.id)}
                              >
                                {retryingDocumentId === document.id
                                  ? "正在重试..."
                                  : "重试"}
                              </button>
                            )}
                            <button
                              type="button"
                              className="delete-button"
                              disabled={deletingDocumentId !== null}
                              onClick={() => handleDeleteDocument(document.id)}
                            >
                              {deletingDocumentId === document.id
                                ? "正在删除..."
                                : "删除"}
                            </button>
                          </>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              {hasMoreDocuments && (
                <button
                  type="button"
                  disabled={isLoadingMoreDocuments}
                  onClick={handleLoadMoreDocuments}
                >
                  {isLoadingMoreDocuments ? "正在加载..." : "加载更多文档"}
                </button>
              )}
            </section>
            <section className="workspace-answer" aria-label="智能问答">
              {documents.length === 0 ? (
                <p>还没有上传文档。</p>
              ) : readyDocuments.length === 0 ? (
                <p>当前没有可用于问答的已就绪文档。</p>
              ) : (
                <>
                  <form onSubmit={handleQuestion}>
                    <label htmlFor="answer-scope">问答范围</label>
                    <select
                      id="answer-scope"
                      value={answerScope}
                      onChange={(event) => {
                        setAnswerScope(event.target.value);
                        setSelectedConversationId("");
                        setDocumentAnswer(null);
                      }}
                    >
                      <option value="knowledge-base">整个知识库</option>
                      <option value="document">指定一份文档</option>
                    </select>
                    {answerScope === "document" && (
                      <>
                        <label htmlFor="document-select">文档</label>
                        <select
                          id="document-select"
                          value={selectedDocumentId}
                          onChange={(event) => {
                            setSelectedDocumentId(event.target.value);
                            setDocumentAnswer(null);
                          }}
                        >
                          <option value="">请选择已就绪文档</option>
                          {readyDocuments.map((document) => (
                            <option key={document.id} value={document.id}>
                              {document.filename}
                            </option>
                          ))}
                        </select>
                      </>
                    )}
                    {answerScope === "knowledge-base" && (
                      <>
                        <label htmlFor="answer-tags">按标签筛选</label>
                        <input
                          id="answer-tags"
                          value={answerTags}
                          maxLength={500}
                          placeholder="人事制度, 员工手册"
                          onChange={(event) =>
                            setAnswerTags(event.target.value)
                          }
                        />
                      </>
                    )}
                    <ConversationControls
                      conversations={conversations.map((conversation) => ({
                        ...conversation,
                        label: getConversationLabel(conversation),
                      }))}
                      selectedConversationId={selectedConversationId}
                      onSelect={(conversationId) => {
                        setSelectedConversationId(conversationId);
                        setDocumentAnswer(null);
                      }}
                      onDelete={handleDeleteConversation}
                      isDeleting={deletingConversationId !== null}
                      hasMore={hasMoreConversations}
                      onLoadMore={handleLoadMoreConversations}
                      isLoadingMore={isLoadingMoreConversations}
                    />
                    <label htmlFor="document-question">问题</label>
                    <textarea
                      id="document-question"
                      value={documentQuestion}
                      maxLength={2000}
                      placeholder="请基于已选择的知识库提出问题"
                      onChange={(event) =>
                        setDocumentQuestion(event.target.value)
                      }
                    />
                    <button
                      type="submit"
                      disabled={
                        isAnsweringDocument ||
                        (answerScope === "document" && !selectedDocumentId) ||
                        !documentQuestion.trim()
                      }
                    >
                      {isAnsweringDocument ? "正在生成回答..." : "开始问答"}
                    </button>
                  </form>
                  {selectedConversationId &&
                    conversations.find(
                      (item) => String(item.id) === selectedConversationId,
                    )?.messages.length > 0 && (
                      <div className="conversation-history">
                        {conversations
                          .find(
                            (item) =>
                              String(item.id) === selectedConversationId,
                          )
                          .messages.map((message) => (
                            <div
                              key={message.id}
                              className={`conversation-message ${message.role}`}
                            >
                              <p>
                                <strong>
                                  {message.role === "user" ? "我" : "智能助手"}
                                  ：
                                </strong>{" "}
                                {message.content}
                              </p>
                              {message.role === "assistant" && (
                                <>
                                  {message.sources?.length > 0 && (
                                    <ul
                                      className="knowledge-sources"
                                      aria-label="回答来源"
                                    >
                                      {message.sources.map((source) => (
                                        <li
                                          key={`${message.id}-${source.document_id}-${source.chunk_index}`}
                                        >
                                          <span>
                                            {source.filename}
                                            {source.page
                                              ? ` · 第 ${source.page} 页`
                                              : ""}{" "}
                                            · 文本块 {source.chunk_index}
                                          </span>
                                          {readyDocuments.some(
                                            (document) =>
                                              document.id ===
                                              source.document_id,
                                          ) && (
                                            <button
                                              type="button"
                                              onClick={() =>
                                                askAboutSource(
                                                  source.document_id,
                                                )
                                              }
                                            >
                                              针对来源提问
                                            </button>
                                          )}
                                        </li>
                                      ))}
                                    </ul>
                                  )}
                                  <div className="answer-feedback">
                                    <button
                                      type="button"
                                      onClick={() =>
                                        handleFeedback(message.id, "helpful")
                                      }
                                    >
                                      有帮助
                                    </button>
                                    <button
                                      type="button"
                                      className="delete-button"
                                      onClick={() =>
                                        handleFeedback(message.id, "unhelpful")
                                      }
                                    >
                                      无帮助
                                    </button>
                                    {message.feedback && (
                                      <span>{message.feedback}</span>
                                    )}
                                  </div>
                                </>
                              )}
                            </div>
                          ))}
                      </div>
                    )}
                </>
              )}
              {documentAnswerError && (
                <p className="form-error">{documentAnswerError}</p>
              )}
              {documentAnswer && (
                <div className="document-answer">
                  <p>{documentAnswer.answer}</p>
                  {documentAnswer.sources.length > 0 && (
                    <ul className="knowledge-sources" aria-label="文档来源">
                      {documentAnswer.sources.map((source) => (
                        <li key={`${source.document_id}-${source.chunk_index}`}>
                          <span>
                            {source.filename}
                            {source.page ? ` · 第 ${source.page} 页` : ""} ·
                            文本块 {source.chunk_index}
                          </span>
                          {readyDocuments.some(
                            (document) => document.id === source.document_id,
                          ) && (
                            <button
                              type="button"
                              onClick={() => askAboutSource(source.document_id)}
                            >
                              针对来源提问
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </section>
          </div>
        </section>
      )}
    </main>
  );
}

export default App;
