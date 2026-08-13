import { useEffect, useState } from 'react'
import './App.css'
import {
  addKnowledgeBaseMember,
  createKnowledgeBase,
  deleteDocument,
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
} from './api.js'
import LoginForm from './LoginForm.jsx'

function App() {
  const [accessToken, setAccessToken] = useState(() => sessionStorage.getItem('access_token'))
  const [apiStatus, setApiStatus] = useState({ message: 'Checking API...', isError: false })
  const [knowledgeBases, setKnowledgeBases] = useState([])
  const [selectedKnowledgeBaseId, setSelectedKnowledgeBaseId] = useState('')
  const [knowledgeBaseName, setKnowledgeBaseName] = useState('')
  const [knowledgeBaseDescription, setKnowledgeBaseDescription] = useState('')
  const [knowledgeBaseError, setKnowledgeBaseError] = useState('')
  const [knowledgeBaseMembers, setKnowledgeBaseMembers] = useState([])
  const [auditLogs, setAuditLogs] = useState([])
  const [feedbackSummary, setFeedbackSummary] = useState(null)
  const [memberUsername, setMemberUsername] = useState('')
  const [memberRole, setMemberRole] = useState('viewer')
  const [isCreatingKnowledgeBase, setIsCreatingKnowledgeBase] = useState(false)
  const [deletingKnowledgeBaseId, setDeletingKnowledgeBaseId] = useState(null)
  const [documents, setDocuments] = useState([])
  const [documentFile, setDocumentFile] = useState(null)
  const [documentTags, setDocumentTags] = useState('')
  const [documentUploadError, setDocumentUploadError] = useState('')
  const [searchQuestion, setSearchQuestion] = useState('')
  const [searchTags, setSearchTags] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searchError, setSearchError] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [isUploadingDocument, setIsUploadingDocument] = useState(false)
  const [deletingDocumentId, setDeletingDocumentId] = useState(null)
  const [retryingDocumentId, setRetryingDocumentId] = useState(null)
  const [reindexingDocumentId, setReindexingDocumentId] = useState(null)
  const [selectedDocumentId, setSelectedDocumentId] = useState('')
  const [answerScope, setAnswerScope] = useState('knowledge-base')
  const [documentQuestion, setDocumentQuestion] = useState('')
  const [answerTags, setAnswerTags] = useState('')
  const [documentAnswer, setDocumentAnswer] = useState(null)
  const [conversations, setConversations] = useState([])
  const [selectedConversationId, setSelectedConversationId] = useState('')
  const [documentAnswerError, setDocumentAnswerError] = useState('')
  const [isAnsweringDocument, setIsAnsweringDocument] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  const readyDocuments = documents.filter((document) => document.status === 'ready')
  const hasPendingDocuments = documents.some((document) => ['uploaded', 'processing'].includes(document.status))

  function clearSession() {
    sessionStorage.removeItem('access_token')
    setAccessToken(null)
  }

  useEffect(() => {
    getApiHealth()
      .then((data) => setApiStatus({ message: `API connected. Database: ${data.database}`, isError: false }))
      .catch(() => setApiStatus({ message: 'API is unavailable', isError: true }))
  }, [])

  useEffect(() => {
    if (!accessToken) {
      setKnowledgeBases([])
      setDocuments([])
      return
    }
    getKnowledgeBases(accessToken)
      .then((data) => {
        setKnowledgeBases(data)
        setSelectedKnowledgeBaseId((current) => current || (data[0] ? String(data[0].id) : ''))
      })
      .catch((error) => {
        if (error.status === 401) clearSession()
        else setKnowledgeBaseError(error.message)
      })
  }, [accessToken])

  useEffect(() => {
    if (!accessToken || !selectedKnowledgeBaseId) {
      setDocuments([])
      return
    }
    let cancelled = false
    async function loadDocuments() {
      try {
        const data = await getMyDocuments(accessToken, selectedKnowledgeBaseId)
        if (cancelled) return
        setDocuments(data)
        setSelectedDocumentId((current) => data.some((document) => String(document.id) === current) ? current : String(data.find((document) => document.status === 'ready')?.id ?? ''))
      } catch (error) {
        if (error.status === 401) clearSession()
        else setDocumentUploadError(error.message)
      }
    }
    loadDocuments()
    return () => { cancelled = true }
  }, [accessToken, selectedKnowledgeBaseId])

  useEffect(() => {
    if (!accessToken || !selectedKnowledgeBaseId) {
      setFeedbackSummary(null)
      return
    }
    getKnowledgeBaseFeedbackSummary(accessToken, selectedKnowledgeBaseId)
      .then(setFeedbackSummary)
      .catch((error) => {
        if (error.status === 401) clearSession()
        else if (error.status === 403) setFeedbackSummary(null)
        else setKnowledgeBaseError(error.message)
      })
  }, [accessToken, selectedKnowledgeBaseId])

  useEffect(() => {
    if (!accessToken || !selectedKnowledgeBaseId) {
      setAuditLogs([])
      return
    }
    getKnowledgeBaseAuditLogs(accessToken, selectedKnowledgeBaseId)
      .then(setAuditLogs)
      .catch((error) => {
        if (error.status === 401) clearSession()
        else if (error.status === 403) setAuditLogs([])
        else setKnowledgeBaseError(error.message)
      })
  }, [accessToken, selectedKnowledgeBaseId])

  useEffect(() => {
    if (!accessToken || !selectedKnowledgeBaseId) {
      setKnowledgeBaseMembers([])
      return
    }
    getKnowledgeBaseMembers(accessToken, selectedKnowledgeBaseId)
      .then(setKnowledgeBaseMembers)
      .catch((error) => {
        if (error.status === 401) clearSession()
        else if (error.status !== 403) setKnowledgeBaseError(error.message)
        else setKnowledgeBaseMembers([])
      })
  }, [accessToken, selectedKnowledgeBaseId])

  useEffect(() => {
    if (!accessToken || !selectedKnowledgeBaseId || !hasPendingDocuments) return undefined
    const timer = window.setInterval(async () => {
      try {
        const data = await getMyDocuments(accessToken, selectedKnowledgeBaseId)
        setDocuments(data)
      } catch (error) {
        if (error.status === 401) clearSession()
      }
    }, 3000)
    return () => window.clearInterval(timer)
  }, [accessToken, selectedKnowledgeBaseId, hasPendingDocuments])

  useEffect(() => {
    const scopeId = answerScope === 'knowledge-base' ? selectedKnowledgeBaseId : selectedDocumentId
    if (!accessToken || !scopeId) {
      setConversations([])
      setSelectedConversationId('')
      return
    }
    const loadConversations = answerScope === 'knowledge-base' ? getKnowledgeBaseConversations : getDocumentConversations
    loadConversations(accessToken, scopeId)
      .then((data) => setConversations(data))
      .catch((error) => {
        if (error.status === 401) clearSession()
        else setDocumentAnswerError(error.message)
      })
  }, [accessToken, answerScope, selectedDocumentId, selectedKnowledgeBaseId])

  async function handleLogin(username, password) {
    const data = await login(username, password)
    sessionStorage.setItem('access_token', data.access_token)
    setAccessToken(data.access_token)
  }

  async function handleLogout() {
    setIsLoggingOut(true)
    try { await logout(accessToken) } finally { clearSession(); setIsLoggingOut(false) }
  }

  async function handleCreateKnowledgeBase(event) {
    event.preventDefault()
    setIsCreatingKnowledgeBase(true)
    setKnowledgeBaseError('')
    try {
      const knowledgeBase = await createKnowledgeBase(accessToken, knowledgeBaseName.trim(), knowledgeBaseDescription.trim())
      setKnowledgeBases((current) => [...current, knowledgeBase])
      setSelectedKnowledgeBaseId(String(knowledgeBase.id))
      setKnowledgeBaseName('')
      setKnowledgeBaseDescription('')
    } catch (error) { setKnowledgeBaseError(error.message) } finally { setIsCreatingKnowledgeBase(false) }
  }

  async function handleDeleteKnowledgeBase() {
    const knowledgeBase = knowledgeBases.find((item) => String(item.id) === selectedKnowledgeBaseId)
    if (!knowledgeBase || !window.confirm(`Delete knowledge base "${knowledgeBase.name}"?`)) return
    setDeletingKnowledgeBaseId(knowledgeBase.id)
    try {
      await deleteKnowledgeBase(accessToken, knowledgeBase.id)
      const remaining = knowledgeBases.filter((item) => item.id !== knowledgeBase.id)
      setKnowledgeBases(remaining)
      setSelectedKnowledgeBaseId(remaining[0] ? String(remaining[0].id) : '')
    } catch (error) { setKnowledgeBaseError(error.message) } finally { setDeletingKnowledgeBaseId(null) }
  }

  async function handleAddMember(event) {
    event.preventDefault()
    setKnowledgeBaseError('')
    try {
      await addKnowledgeBaseMember(accessToken, Number(selectedKnowledgeBaseId), memberUsername.trim(), memberRole)
      setKnowledgeBaseMembers(await getKnowledgeBaseMembers(accessToken, selectedKnowledgeBaseId))
      setMemberUsername('')
    } catch (error) { setKnowledgeBaseError(error.message) }
  }

  async function handleRemoveMember(userId) {
    try {
      await removeKnowledgeBaseMember(accessToken, Number(selectedKnowledgeBaseId), userId)
      setKnowledgeBaseMembers(await getKnowledgeBaseMembers(accessToken, selectedKnowledgeBaseId))
    } catch (error) { setKnowledgeBaseError(error.message) }
  }

  async function handleUpload(event) {
    event.preventDefault()
    if (!documentFile) return
    setIsUploadingDocument(true)
    setDocumentUploadError('')
    try {
      const tags = documentTags.split(',').map((tag) => tag.trim()).filter(Boolean)
      const document = await uploadDocument(accessToken, documentFile, Number(selectedKnowledgeBaseId), tags)
      setDocuments((current) => [document, ...current])
      setDocumentFile(null)
      setDocumentTags('')
      event.currentTarget.reset()
    } catch (error) { setDocumentUploadError(error.message) } finally { setIsUploadingDocument(false) }
  }

  async function handleDeleteDocument(documentId) {
    if (!window.confirm('Delete this document?')) return
    setDeletingDocumentId(documentId)
    try { await deleteDocument(accessToken, documentId); setDocuments((current) => current.filter((item) => item.id !== documentId)) }
    catch (error) { setDocumentUploadError(error.message) } finally { setDeletingDocumentId(null) }
  }

  async function handleRetryDocument(documentId) {
    setRetryingDocumentId(documentId)
    try {
      const document = await retryDocument(accessToken, documentId)
      setDocuments((current) => current.map((item) => item.id === documentId ? document : item))
    } catch (error) { setDocumentUploadError(error.message) } finally { setRetryingDocumentId(null) }
  }

  async function handleQuestion(event) {
    event.preventDefault()
    const question = documentQuestion.trim()
    setIsAnsweringDocument(true)
    setDocumentAnswerError('')
    setDocumentAnswer({ answer: '', sources: [] })
    try {
      let conversationId = selectedConversationId
      let sources = []
      let answer = ''
      const streamAnswer = answerScope === 'knowledge-base' ? streamKnowledgeBaseAnswer : streamDocumentAnswer
      const scopeId = answerScope === 'knowledge-base' ? selectedKnowledgeBaseId : selectedDocumentId
      const tags = answerScope === 'knowledge-base' ? answerTags.split(',').map((tag) => tag.trim()).filter(Boolean) : []
      const streamArgs = answerScope === 'knowledge-base'
        ? [accessToken, Number(scopeId), question, selectedConversationId, tags]
        : [accessToken, Number(scopeId), question, selectedConversationId]
      await streamAnswer(...streamArgs, {
        onMetadata: (data) => {
          conversationId = String(data.conversation_id)
          sources = data.sources || []
          setSelectedConversationId(conversationId)
          setDocumentAnswer({ answer: '', sources })
        },
        onToken: (text) => {
          answer += text
          setDocumentAnswer((current) => ({ answer, sources: current?.sources || sources }))
        },
      })
      const loadConversations = answerScope === 'knowledge-base' ? getKnowledgeBaseConversations : getDocumentConversations
      setConversations(await loadConversations(accessToken, scopeId))
    }
    catch (error) { setDocumentAnswerError(error.message) } finally { setIsAnsweringDocument(false) }
  }

  async function handleReindexDocument(documentId) {
    setReindexingDocumentId(documentId)
    setDocumentUploadError('')
    try {
      const document = await reindexDocument(accessToken, documentId)
      setDocuments((current) => current.map((item) => item.id === documentId ? document : item))
    } catch (error) { setDocumentUploadError(error.message) } finally { setReindexingDocumentId(null) }
  }

  async function handleEditDocumentTags(document) {
    const value = window.prompt('Tags, separated by commas', document.tags?.join(', ') || '')
    if (value === null) return
    setDocumentUploadError('')
    try {
      const tags = value.split(',').map((tag) => tag.trim()).filter(Boolean)
      const updated = await updateDocumentTags(accessToken, document.id, tags)
      setDocuments((current) => current.map((item) => item.id === document.id ? updated : item))
    } catch (error) { setDocumentUploadError(error.message) }
  }

  async function handleDownloadDocument(document) {
    setDocumentUploadError('')
    try { await downloadDocument(accessToken, document) }
    catch (error) { setDocumentUploadError(error.message) }
  }

  async function handleSearch(event) {
    event.preventDefault()
    const question = searchQuestion.trim()
    if (!question || !selectedKnowledgeBaseId) return
    setIsSearching(true)
    setSearchError('')
    try {
      const tags = searchTags.split(',').map((tag) => tag.trim()).filter(Boolean)
      const data = await searchDocuments(accessToken, Number(selectedKnowledgeBaseId), question, tags)
      setSearchResults(data.items || [])
    } catch (error) { setSearchError(error.message) } finally { setIsSearching(false) }
  }

  function askAboutSearchResult(documentId) {
    setAnswerScope('document')
    setSelectedDocumentId(String(documentId))
    setSelectedConversationId('')
    setDocumentAnswer(null)
  }

  function askAboutSource(documentId) {
    askAboutSearchResult(documentId)
    setDocumentQuestion('')
  }

  async function handleFeedback(messageId, feedback) {
    setDocumentAnswerError('')
    const comment = feedback === 'unhelpful' ? window.prompt('What should be improved?') : null
    if (comment === null && feedback === 'unhelpful') return
    try {
      const updated = await submitAnswerFeedback(accessToken, messageId, feedback, comment)
      setConversations((current) => current.map((conversation) => ({
        ...conversation,
        messages: conversation.messages.map((message) => message.id === updated.id ? updated : message),
      })))
    } catch (error) { setDocumentAnswerError(error.message) }
  }

  return <main className="app-shell">
    <header className="app-header"><div><h1>Enterprise Knowledge Hub</h1><p className={apiStatus.isError ? 'api-status error' : 'api-status'}>{apiStatus.message}</p></div>{accessToken && <button className="logout-button" type="button" disabled={isLoggingOut} onClick={handleLogout}>Log out</button>}</header>
    {!accessToken ? <LoginForm onLogin={handleLogin} /> : <section className="document-answer-panel" aria-label="Knowledge base documents">
      <div className="knowledge-base-header"><div><h2>Knowledge bases</h2><p>Organize private documents and ask grounded questions.</p></div>{selectedKnowledgeBaseId && <button type="button" className="delete-button" disabled={deletingKnowledgeBaseId !== null} onClick={handleDeleteKnowledgeBase}>Delete knowledge base</button>}</div>
      <label htmlFor="knowledge-base-select">Current knowledge base</label><select id="knowledge-base-select" value={selectedKnowledgeBaseId} onChange={(event) => { setSelectedKnowledgeBaseId(event.target.value); setDocumentAnswer(null) }}><option value="">Choose a knowledge base</option>{knowledgeBases.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
      <form className="knowledge-base-form" onSubmit={handleCreateKnowledgeBase}><label htmlFor="knowledge-base-name">New knowledge base</label><input id="knowledge-base-name" value={knowledgeBaseName} maxLength={100} placeholder="For example: Employee handbook" onChange={(event) => setKnowledgeBaseName(event.target.value)} /><label htmlFor="knowledge-base-description">Description</label><textarea id="knowledge-base-description" value={knowledgeBaseDescription} maxLength={2000} placeholder="Optional description" onChange={(event) => setKnowledgeBaseDescription(event.target.value)} /><button type="submit" disabled={!knowledgeBaseName.trim() || isCreatingKnowledgeBase}>{isCreatingKnowledgeBase ? 'Creating...' : 'Create knowledge base'}</button></form>
      {knowledgeBaseMembers.length > 0 && <section className="knowledge-base-members"><h2>Members</h2><form className="knowledge-base-form" onSubmit={handleAddMember}><label htmlFor="member-username">Username</label><input id="member-username" value={memberUsername} maxLength={50} onChange={(event) => setMemberUsername(event.target.value)} /><label htmlFor="member-role">Role</label><select id="member-role" value={memberRole} onChange={(event) => setMemberRole(event.target.value)}><option value="viewer">Viewer</option><option value="editor">Editor</option></select><button type="submit" disabled={!memberUsername.trim()}>Add member</button></form><ul className="document-list">{knowledgeBaseMembers.map((member) => <li key={member.user_id} className="document-list-item"><span>{member.username} ({member.role})</span>{member.role !== 'owner' && <button type="button" className="delete-button" onClick={() => handleRemoveMember(member.user_id)}>Remove</button>}</li>)}</ul></section>}
      {auditLogs.length > 0 && <section className="knowledge-base-members"><h2>Audit log</h2><ul className="document-list">{auditLogs.map((event) => <li key={event.id} className="document-list-item"><span>{event.action} · {event.target_type}{event.target_id ? ` #${event.target_id}` : ''}</span><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time></li>)}</ul></section>}
      {feedbackSummary && <section className="knowledge-base-members"><h2>Answer quality</h2><p>{feedbackSummary.total_feedback} ratings · {feedbackSummary.helpful_count} helpful · {feedbackSummary.unhelpful_count} not helpful{feedbackSummary.helpful_rate !== null ? ` · ${Math.round(feedbackSummary.helpful_rate * 100)}% helpful` : ''}</p>{feedbackSummary.recent_unhelpful.length > 0 && <ul className="document-list">{feedbackSummary.recent_unhelpful.map((item) => <li key={item.message_id} className="document-list-item"><span>{item.comment || item.answer}</span></li>)}</ul>}</section>}
      {knowledgeBaseError && <p className="form-error">{knowledgeBaseError}</p>}
      <h2>Documents</h2><form className="document-upload-form" onSubmit={handleUpload}><label htmlFor="document-file">Upload PDF</label><input id="document-file" type="file" accept="application/pdf,.pdf" onChange={(event) => { setDocumentFile(event.target.files?.[0] ?? null); setDocumentUploadError('') }} /><label htmlFor="document-tags">Tags</label><input id="document-tags" value={documentTags} maxLength={500} placeholder="HR, policy, engineering" onChange={(event) => setDocumentTags(event.target.value)} /><button type="submit" disabled={!documentFile || !selectedKnowledgeBaseId || isUploadingDocument}>{isUploadingDocument ? 'Uploading...' : 'Upload document'}</button></form>
      {documentUploadError && <p className="form-error">{documentUploadError}</p>}
      <section className="document-search" aria-label="Search document content"><h2>Search content</h2><form onSubmit={handleSearch}><label htmlFor="search-question">Search question</label><input id="search-question" value={searchQuestion} maxLength={300} placeholder="Find relevant policy content" onChange={(event) => setSearchQuestion(event.target.value)} /><label htmlFor="search-tags">Filter by tags</label><input id="search-tags" value={searchTags} maxLength={500} placeholder="HR, policy" onChange={(event) => setSearchTags(event.target.value)} /><button type="submit" disabled={isSearching || !selectedKnowledgeBaseId || !searchQuestion.trim()}>{isSearching ? 'Searching...' : 'Search documents'}</button></form>{searchError && <p className="form-error">{searchError}</p>}{searchResults.length > 0 && <ul className="document-search-results">{searchResults.map((result) => <li key={`${result.document_id}-${result.chunk_index}`}><div><strong>{result.filename}</strong><span>{result.page ? `Page ${result.page}` : 'Document content'} · relevance {Number(result.score).toFixed(2)}</span><p>{result.text}</p></div><button type="button" onClick={() => askAboutSearchResult(result.document_id)}>Ask about document</button></li>)}</ul>}{!isSearching && searchQuestion.trim() && searchResults.length === 0 && !searchError && <p>No matching content found.</p>}</section>
      {documents.length > 0 && <ul className="document-list" aria-label="Uploaded documents">{documents.map((document) => <li key={document.id} className="document-list-item"><div><strong>{document.filename}</strong><span className={`document-status ${document.status}`}>{document.status}</span>{document.tags?.length > 0 && <small className="document-tags">{document.tags.join(' · ')}</small>}{document.status === 'ready' && <small className="document-processing">{document.chunk_count} chunks{document.processed_at ? ` · indexed ${new Date(document.processed_at).toLocaleString()}` : ''}</small>}{document.error_message && <p className="document-error">{document.error_message}</p>}</div><div className="document-actions"><button type="button" onClick={() => handleDownloadDocument(document)}>Download</button><button type="button" onClick={() => handleEditDocumentTags(document)}>Edit tags</button>{document.status === 'ready' && <button type="button" disabled={reindexingDocumentId !== null} onClick={() => handleReindexDocument(document.id)}>{reindexingDocumentId === document.id ? 'Reindexing...' : 'Reindex'}</button>}{document.status === 'failed' && <button type="button" className="retry-button" disabled={retryingDocumentId !== null} onClick={() => handleRetryDocument(document.id)}>{retryingDocumentId === document.id ? 'Retrying...' : 'Retry'}</button>}<button type="button" className="delete-button" disabled={deletingDocumentId !== null} onClick={() => handleDeleteDocument(document.id)}>{deletingDocumentId === document.id ? 'Deleting...' : 'Delete'}</button></div></li>)}</ul>}
      {documents.length === 0 ? <p>No documents uploaded yet.</p> : readyDocuments.length === 0 ? <p>No documents are ready for questions yet.</p> : <><form onSubmit={handleQuestion}><label htmlFor="answer-scope">Question scope</label><select id="answer-scope" value={answerScope} onChange={(event) => { setAnswerScope(event.target.value); setSelectedConversationId(''); setDocumentAnswer(null) }}><option value="knowledge-base">Entire knowledge base</option><option value="document">One document</option></select>{answerScope === 'document' && <><label htmlFor="document-select">Document</label><select id="document-select" value={selectedDocumentId} onChange={(event) => { setSelectedDocumentId(event.target.value); setDocumentAnswer(null) }}><option value="">Choose a ready document</option>{readyDocuments.map((document) => <option key={document.id} value={document.id}>{document.filename}</option>)}</select></>}{answerScope === 'knowledge-base' && <><label htmlFor="answer-tags">Filter by tags</label><input id="answer-tags" value={answerTags} maxLength={500} placeholder="HR, policy" onChange={(event) => setAnswerTags(event.target.value)} /></>}<div className="conversation-controls"><label htmlFor="conversation-select">Conversation</label><select id="conversation-select" value={selectedConversationId} onChange={(event) => { setSelectedConversationId(event.target.value); setDocumentAnswer(null) }}><option value="">New conversation</option>{conversations.map((conversation) => <option key={conversation.id} value={conversation.id}>Conversation {conversation.id}</option>)}</select></div><label htmlFor="document-question">Question</label><textarea id="document-question" value={documentQuestion} maxLength={2000} placeholder="Ask about the selected knowledge base" onChange={(event) => setDocumentQuestion(event.target.value)} /><button type="submit" disabled={isAnsweringDocument || (answerScope === 'document' && !selectedDocumentId) || !documentQuestion.trim()}>{isAnsweringDocument ? 'Answering...' : 'Ask knowledge base'}</button></form>{selectedConversationId && conversations.find((item) => String(item.id) === selectedConversationId)?.messages.length > 0 && <div className="conversation-history">{conversations.find((item) => String(item.id) === selectedConversationId).messages.map((message) => <div key={message.id} className={`conversation-message ${message.role}`}><p><strong>{message.role === 'user' ? 'You' : 'Assistant'}:</strong> {message.content}</p>{message.role === 'assistant' && <>{message.sources?.length > 0 && <ul className="knowledge-sources" aria-label="Answer sources">{message.sources.map((source) => <li key={`${message.id}-${source.document_id}-${source.chunk_index}`}><span>{source.filename}{source.page ? ` - page ${source.page}` : ''} - chunk {source.chunk_index}</span>{readyDocuments.some((document) => document.id === source.document_id) && <button type="button" onClick={() => askAboutSource(source.document_id)}>Ask about source</button>}</li>)}</ul>}<div className="answer-feedback"><button type="button" onClick={() => handleFeedback(message.id, 'helpful')}>Helpful</button><button type="button" className="delete-button" onClick={() => handleFeedback(message.id, 'unhelpful')}>Not helpful</button>{message.feedback && <span>{message.feedback}</span>}</div></>}</div>)}</div>}</>}
      {documentAnswerError && <p className="form-error">{documentAnswerError}</p>}{documentAnswer && <div className="document-answer"><p>{documentAnswer.answer}</p>{documentAnswer.sources.length > 0 && <ul className="knowledge-sources" aria-label="Document sources">{documentAnswer.sources.map((source) => <li key={`${source.document_id}-${source.chunk_index}`}><span>{source.filename}{source.page ? ` - page ${source.page}` : ''} - chunk {source.chunk_index}</span>{readyDocuments.some((document) => document.id === source.document_id) && <button type="button" onClick={() => askAboutSource(source.document_id)}>Ask about source</button>}</li>)}</ul>}</div>}
    </section>}
  </main>
}

export default App
