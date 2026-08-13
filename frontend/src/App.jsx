import { useEffect, useState } from 'react'
import './App.css'
import {
  answerDocument,
  createKnowledgeBase,
  deleteDocument,
  deleteKnowledgeBase,
  getApiHealth,
  getKnowledgeBases,
  getMyDocuments,
  login,
  logout,
  retryDocument,
  uploadDocument,
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
  const [isCreatingKnowledgeBase, setIsCreatingKnowledgeBase] = useState(false)
  const [deletingKnowledgeBaseId, setDeletingKnowledgeBaseId] = useState(null)
  const [documents, setDocuments] = useState([])
  const [documentFile, setDocumentFile] = useState(null)
  const [documentUploadError, setDocumentUploadError] = useState('')
  const [isUploadingDocument, setIsUploadingDocument] = useState(false)
  const [deletingDocumentId, setDeletingDocumentId] = useState(null)
  const [retryingDocumentId, setRetryingDocumentId] = useState(null)
  const [selectedDocumentId, setSelectedDocumentId] = useState('')
  const [documentQuestion, setDocumentQuestion] = useState('')
  const [documentAnswer, setDocumentAnswer] = useState(null)
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

  async function handleUpload(event) {
    event.preventDefault()
    if (!documentFile) return
    setIsUploadingDocument(true)
    setDocumentUploadError('')
    try {
      const document = await uploadDocument(accessToken, documentFile, Number(selectedKnowledgeBaseId))
      setDocuments((current) => [document, ...current])
      setDocumentFile(null)
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
    setIsAnsweringDocument(true)
    setDocumentAnswerError('')
    try { setDocumentAnswer(await answerDocument(accessToken, Number(selectedDocumentId), documentQuestion.trim())) }
    catch (error) { setDocumentAnswerError(error.message) } finally { setIsAnsweringDocument(false) }
  }

  return <main className="app-shell">
    <header className="app-header"><div><h1>Enterprise Knowledge Hub</h1><p className={apiStatus.isError ? 'api-status error' : 'api-status'}>{apiStatus.message}</p></div>{accessToken && <button className="logout-button" type="button" disabled={isLoggingOut} onClick={handleLogout}>Log out</button>}</header>
    {!accessToken ? <LoginForm onLogin={handleLogin} /> : <section className="document-answer-panel" aria-label="Knowledge base documents">
      <div className="knowledge-base-header"><div><h2>Knowledge bases</h2><p>Organize private documents and ask grounded questions.</p></div>{selectedKnowledgeBaseId && <button type="button" className="delete-button" disabled={deletingKnowledgeBaseId !== null} onClick={handleDeleteKnowledgeBase}>Delete knowledge base</button>}</div>
      <label htmlFor="knowledge-base-select">Current knowledge base</label><select id="knowledge-base-select" value={selectedKnowledgeBaseId} onChange={(event) => { setSelectedKnowledgeBaseId(event.target.value); setDocumentAnswer(null) }}><option value="">Choose a knowledge base</option>{knowledgeBases.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
      <form className="knowledge-base-form" onSubmit={handleCreateKnowledgeBase}><label htmlFor="knowledge-base-name">New knowledge base</label><input id="knowledge-base-name" value={knowledgeBaseName} maxLength={100} placeholder="For example: Employee handbook" onChange={(event) => setKnowledgeBaseName(event.target.value)} /><label htmlFor="knowledge-base-description">Description</label><textarea id="knowledge-base-description" value={knowledgeBaseDescription} maxLength={2000} placeholder="Optional description" onChange={(event) => setKnowledgeBaseDescription(event.target.value)} /><button type="submit" disabled={!knowledgeBaseName.trim() || isCreatingKnowledgeBase}>{isCreatingKnowledgeBase ? 'Creating...' : 'Create knowledge base'}</button></form>
      {knowledgeBaseError && <p className="form-error">{knowledgeBaseError}</p>}
      <h2>Documents</h2><form className="document-upload-form" onSubmit={handleUpload}><label htmlFor="document-file">Upload PDF</label><input id="document-file" type="file" accept="application/pdf,.pdf" onChange={(event) => { setDocumentFile(event.target.files?.[0] ?? null); setDocumentUploadError('') }} /><button type="submit" disabled={!documentFile || !selectedKnowledgeBaseId || isUploadingDocument}>{isUploadingDocument ? 'Uploading...' : 'Upload document'}</button></form>
      {documentUploadError && <p className="form-error">{documentUploadError}</p>}
      {documents.length > 0 && <ul className="document-list" aria-label="Uploaded documents">{documents.map((document) => <li key={document.id} className="document-list-item"><div><strong>{document.filename}</strong><span className={`document-status ${document.status}`}>{document.status}</span>{document.error_message && <p className="document-error">{document.error_message}</p>}</div><div className="document-actions">{document.status === 'failed' && <button type="button" className="retry-button" disabled={retryingDocumentId !== null} onClick={() => handleRetryDocument(document.id)}>{retryingDocumentId === document.id ? 'Retrying...' : 'Retry'}</button>}<button type="button" className="delete-button" disabled={deletingDocumentId !== null} onClick={() => handleDeleteDocument(document.id)}>{deletingDocumentId === document.id ? 'Deleting...' : 'Delete'}</button></div></li>)}</ul>}
      {documents.length === 0 ? <p>No documents uploaded yet.</p> : readyDocuments.length === 0 ? <p>No documents are ready for questions yet.</p> : <form onSubmit={handleQuestion}><label htmlFor="document-select">Document</label><select id="document-select" value={selectedDocumentId} onChange={(event) => { setSelectedDocumentId(event.target.value); setDocumentAnswer(null) }}><option value="">Choose a ready document</option>{readyDocuments.map((document) => <option key={document.id} value={document.id}>{document.filename}</option>)}</select><label htmlFor="document-question">Question</label><textarea id="document-question" value={documentQuestion} maxLength={2000} placeholder="Ask about the selected document" onChange={(event) => setDocumentQuestion(event.target.value)} /><button type="submit" disabled={isAnsweringDocument || !selectedDocumentId || !documentQuestion.trim()}>{isAnsweringDocument ? 'Answering...' : 'Ask document'}</button></form>}
      {documentAnswerError && <p className="form-error">{documentAnswerError}</p>}{documentAnswer && <div className="document-answer"><p>{documentAnswer.answer}</p>{documentAnswer.sources.length > 0 && <ul className="knowledge-sources" aria-label="Document sources">{documentAnswer.sources.map((source) => <li key={`${source.document_id}-${source.chunk_index}`}>{source.filename} - chunk {source.chunk_index}</li>)}</ul>}</div>}
    </section>}
  </main>
}

export default App
