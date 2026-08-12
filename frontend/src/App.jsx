import { useEffect, useState } from 'react'
import './App.css'
import {
  createTask,
  answerProjectQuestion,
  askAssistant,
  clearAssistantHistory,
  deleteTask,
  getApiHealth,
  getAssistantHistory,
  getMyTasks,
  login,
  logout,
  rewriteTaskTitle,
  setTaskDone,
  suggestTaskPlan,
  updateTaskTitle,
  getMyDocuments,
  answerDocument,
  uploadDocument,
  deleteDocument,
  retryDocument,
  createKnowledgeBase,
  deleteKnowledgeBase,
  getKnowledgeBases,
} from './api.js'
import LoginForm from './LoginForm.jsx'
import TaskList from './TaskList.jsx'

function App() {
  const [tasks, setTasks] = useState([])
  const [accessToken, setAccessToken] = useState(() =>
    sessionStorage.getItem('access_token'),
  )
  const [draftTitle, setDraftTitle] = useState('')
  const [taskPlan, setTaskPlan] = useState(null)
  const [isCreating, setIsCreating] = useState(false)
  const [isSuggestingPlan, setIsSuggestingPlan] = useState(false)
  const [deletingTaskId, setDeletingTaskId] = useState(null)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [updatingTaskId, setUpdatingTaskId] = useState(null)
  const [taskMessage, setTaskMessage] = useState('')
  const [assistantMessage, setAssistantMessage] = useState('')
  const [assistantHistory, setAssistantHistory] = useState([])
  const [assistantError, setAssistantError] = useState('')
  const [assistantLoading, setAssistantLoading] = useState(false)
  const [assistantCooldown, setAssistantCooldown] = useState(0)
  const [isClearingAssistantHistory, setIsClearingAssistantHistory] = useState(false)
  const [usedTools, setUsedTools] = useState([])
  const [projectQuestion, setProjectQuestion] = useState('')
  const [projectAnswer, setProjectAnswer] = useState(null)
  const [projectQuestionError, setProjectQuestionError] = useState('')
  const [isAnsweringProjectQuestion, setIsAnsweringProjectQuestion] = useState(false)
  const [apiStatus, setApiStatus] = useState({
    message: '正在检查 API...',
    isError: false,
  })
  const unfinishedTasks = tasks.filter((task) => !task.done)
  const completedTasks = tasks.filter((task) => task.done)
  const [documents, setDocuments] = useState([])
  const [selectedDocumentId, setSelectedDocumentId] = useState('')
  const [documentQuestion, setDocumentQuestion] = useState('')
  const [documentAnswer, setDocumentAnswer] = useState(null)
  const [documentAnswerError, setDocumentAnswerError] = useState('')
  const [isAnsweringDocument, setIsAnsweringDocument] = useState(false)
  const [documentFile, setDocumentFile] = useState(null)
  const [documentUploadError, setDocumentUploadError] = useState('')
  const [isUploadingDocument, setIsUploadingDocument] = useState(false)
  const [deletingDocumentId, setDeletingDocumentId] = useState(null)
  const [retryingDocumentId, setRetryingDocumentId] = useState(null)
  const [knowledgeBases, setKnowledgeBases] = useState([])
  const [selectedKnowledgeBaseId, setSelectedKnowledgeBaseId] = useState('')
  const [knowledgeBaseName, setKnowledgeBaseName] = useState('')
  const [knowledgeBaseDescription, setKnowledgeBaseDescription] = useState('')
  const [knowledgeBaseError, setKnowledgeBaseError] = useState('')
  const [isCreatingKnowledgeBase, setIsCreatingKnowledgeBase] = useState(false)
  const [deletingKnowledgeBaseId, setDeletingKnowledgeBaseId] = useState(null)
  const readyDocuments = documents.filter(
    (document) => document.status === 'ready',
  )

  const hasPendingDocuments = documents.some(
    (document) =>
      document.status === 'uploaded' ||
      document.status === 'processing',
  )

  useEffect(() => {
    async function checkApiHealth() {
      try {
        const data = await getApiHealth()
        setApiStatus({
          message: `API 已连接，数据库：${data.database}`,
          isError: false,
        })
      } catch {
        setApiStatus({ message: '无法连接 API', isError: true })
      }
    }

    checkApiHealth()
  }, [])

  useEffect(() => {
    if (!accessToken) {
      setTasks([])
      return
    }

    async function loadTasks() {
      setTaskMessage('正在加载任务...')

      try {
        const [unfinishedTasks, completedTasks] = await Promise.all([
          getMyTasks(accessToken, false),
          getMyTasks(accessToken, true),
        ])
        setTasks([...unfinishedTasks, ...completedTasks])
        setTaskMessage('')
      } catch (error) {
        if (error.status === 401) {
          sessionStorage.removeItem('access_token')
          setAccessToken(null)
          return
        }

        setTaskMessage(error.message)
      }
    }

    loadTasks()
  }, [accessToken])

  useEffect(() => {
    if (!accessToken) {
      setAssistantHistory([])
      return
    }

    async function loadAssistantHistory() {
      try {
        const data = await getAssistantHistory(accessToken)
        setAssistantHistory(data.items)
      } catch (error) {
        if (error.status === 401) {
          clearSession()
          return
        }
        setAssistantError(error.message)
      }
    }

    loadAssistantHistory()
  }, [accessToken])

  useEffect(() => {
    if (assistantCooldown <= 0) return undefined

    const timerId = window.setInterval(() => {
      setAssistantCooldown((seconds) => Math.max(seconds - 1, 0))
    }, 1000)

    return () => window.clearInterval(timerId)
  }, [assistantCooldown])

  useEffect(() => {
    if (!accessToken) {
      setDocuments([])
      setSelectedDocumentId('')
      setKnowledgeBases([])
      setSelectedKnowledgeBaseId('')
      return
    }

    async function loadKnowledgeBases() {
      try {
        const data = await getKnowledgeBases(accessToken)
        setKnowledgeBases(data)
        if (data.length > 0) {
          setSelectedKnowledgeBaseId((currentKnowledgeBaseId) =>
            currentKnowledgeBaseId || String(data[0].id),
          )
        }
      } catch (error) {
        if (error.status === 401) {
          clearSession()
          return
        }

        setKnowledgeBaseError(error.message)
      }
    }

    loadKnowledgeBases()
  }, [accessToken])

  useEffect(() => {
    if (!accessToken || !selectedKnowledgeBaseId) {
      setDocuments([])
      setSelectedDocumentId('')
      return
    }

    async function loadDocuments() {
      try {
        const data = await getMyDocuments(accessToken, selectedKnowledgeBaseId)
        setDocuments(data)
        setSelectedDocumentId((currentDocumentId) => {
          if (data.some((document) => String(document.id) === currentDocumentId)) {
            return currentDocumentId
          }
          const firstReadyDocument = data.find(
            (document) => document.status === 'ready',
          )
          return firstReadyDocument ? String(firstReadyDocument.id) : ''
        })
      } catch (error) {
        if (error.status === 401) {
          clearSession()
          return
        }
        setDocumentAnswerError(error.message)
      }
    }

    loadDocuments()
  }, [accessToken, selectedKnowledgeBaseId])

  useEffect(() => {
    if (!accessToken || !hasPendingDocuments) {
      return undefined
    }

    const timerId = window.setInterval(async () => {
      try {
        const data = await getMyDocuments(accessToken, selectedKnowledgeBaseId)
        setDocuments(data)

        const firstReadyDocument = data.find(
          (document) => document.status === 'ready',
        )

        if (firstReadyDocument) {
          setSelectedDocumentId(
            (currentDocumentId) =>
              currentDocumentId || String(firstReadyDocument.id),
          )
        }
      } catch (error) {
        if (error.status === 401) {
          clearSession()
          return
        }

        setDocumentUploadError(error.message)
      }
    }, 3000)

    return () => window.clearInterval(timerId)
  }, [accessToken, hasPendingDocuments, selectedKnowledgeBaseId])

  async function handleLogin(username, password) {
    const data = await login(username, password)
    sessionStorage.setItem('access_token', data.access_token)
    setAccessToken(data.access_token)
  }

  function clearSession() {
    sessionStorage.removeItem('access_token')
    setAccessToken(null)
  }

  async function handleSuggestTaskPlan() {
    const title = draftTitle.trim()

    if (!title) {
      setTaskMessage('Please enter a task title first')
      return
    }

    setIsSuggestingPlan(true)
    setTaskMessage('AI is creating a task suggestion...')

    try {
      const suggestion = await suggestTaskPlan(accessToken, title)
      setTaskPlan(suggestion)
      setTaskMessage('')
    } catch (error) {
      if (error.status === 401) {
        clearSession()
        return
      }

      setTaskMessage(error.message)
    } finally {
      setIsSuggestingPlan(false)
    }
  }

  async function handleCreateTask(event) {
    event.preventDefault()

    const title = draftTitle.trim()
    if (!title) {
      setTaskMessage('任务标题不能为空')
      return
    }

    setIsCreating(true)
    setTaskMessage('正在创建任务...')

    try {
      const newTask = await createTask(accessToken, title)
      setTasks((currentTasks) => [newTask, ...currentTasks])
      setDraftTitle('')
      setTaskPlan(null)
      setTaskMessage('')
    } catch (error) {
      if (error.status === 401) {
        clearSession()
        return
      }

      setTaskMessage(error.message)
    } finally {
      setIsCreating(false)
    }
  }

  async function handleToggleTask(taskId, done) {
    setUpdatingTaskId(taskId)
    setTaskMessage('正在更新任务...')

    try {
      const updatedTask = await setTaskDone(accessToken, taskId, done)
      setTasks((currentTasks) =>
        currentTasks.map((task) =>
          task.id === taskId ? updatedTask : task,
        ),
      )
      setTaskMessage('')
    } catch (error) {
      if (error.status === 401) {
        clearSession()
        return
      }

      setTaskMessage(error.message)
    } finally {
      setUpdatingTaskId(null)
    }
  }

  async function handleDeleteTask(task) {
    if (!window.confirm(`确定删除“${task.title}”吗？`)) {
      return
    }

    setDeletingTaskId(task.id)
    setTaskMessage('正在删除任务...')

    try {
      await deleteTask(accessToken, task.id)
      setTasks((currentTasks) =>
        currentTasks.filter((currentTask) => currentTask.id !== task.id),
      )
      setTaskMessage('')
    } catch (error) {
      if (error.status === 401) {
        clearSession()
        return
      }

      setTaskMessage(error.message)
    } finally {
      setDeletingTaskId(null)
    }
  }

  async function handleUpdateTaskTitle(taskId, title) {
    setUpdatingTaskId(taskId)
    setTaskMessage('正在更新任务...')

    try {
      const updatedTask = await updateTaskTitle(accessToken, taskId, title)
      setTasks((currentTasks) =>
        currentTasks.map((task) => (task.id === taskId ? updatedTask : task)),
      )
      setTaskMessage('')
    } catch (error) {
      if (error.status === 401) {
        clearSession()
      } else {
        setTaskMessage(error.message)
      }

      throw error
    } finally {
      setUpdatingTaskId(null)
    }
  }

  async function handleRewriteTitle(title) {
    try {
      return await rewriteTaskTitle(accessToken, title)
    } catch (error) {
      if (error.status === 401) {
        clearSession()
      }

      throw error
    }
  }

  async function handleLogout() {
    setIsLoggingOut(true)

    try {
      await logout(accessToken)
      clearSession()
    } catch (error) {
      setTaskMessage(error.message)
    } finally {
      setIsLoggingOut(false)
    }
  }

  async function handleAssistantSubmit(event) {
    event.preventDefault()
    const message = assistantMessage.trim()
    if (!message || assistantLoading) return

    setAssistantLoading(true)
    setAssistantError('')
    try {
      const data = await askAssistant(accessToken, message)
      setAssistantHistory((currentHistory) => [
        ...currentHistory,
        { role: 'user', content: message },
        { role: 'assistant', content: data.reply },
      ])
      setUsedTools(data.used_tools)
      setAssistantMessage('')
      setAssistantCooldown(0)
    } catch (error) {
      if (error.status === 401) {
        clearSession()
        return
      }
      if (error.status === 429 && error.retryAfter) {
        setAssistantCooldown(error.retryAfter)
        return
      }
      setAssistantError(error.message)
    } finally {
      setAssistantLoading(false)
    }
  }

  async function handleClearAssistantHistory() {
    setIsClearingAssistantHistory(true)
    setAssistantError('')

    try {
      await clearAssistantHistory(accessToken)
      setAssistantMessage('')
      setAssistantHistory([])
      setUsedTools([])
      setAssistantCooldown(0)
    } catch (error) {
      if (error.status === 401) {
        clearSession()
        return
      }
      setAssistantError(error.message)
    } finally {
      setIsClearingAssistantHistory(false)
    }
  }

  async function handleProjectQuestionSubmit(event) {
    event.preventDefault()
    const question = projectQuestion.trim()
    if (!question || isAnsweringProjectQuestion) return

    setIsAnsweringProjectQuestion(true)
    setProjectQuestionError('')
    setProjectAnswer(null)
    try {
      const data = await answerProjectQuestion(accessToken, question)
      setProjectAnswer(data)
    } catch (error) {
      if (error.status === 401) {
        clearSession()
        return
      }
      setProjectQuestionError(error.message)
    } finally {
      setIsAnsweringProjectQuestion(false)
    }
  }

  async function handleDocumentUpload(event) {
    event.preventDefault()
    const form = event.currentTarget

    if (!documentFile || !selectedKnowledgeBaseId || isUploadingDocument) {
      return
    }

    if (!documentFile.name.toLowerCase().endsWith('.pdf')) {
      setDocumentUploadError('Only PDF files are allowed.')
      return
    }

    if (documentFile.size > 10 * 1024 * 1024) {
      setDocumentUploadError('File size must not exceed 10 MB.')
      return
    }
    setIsUploadingDocument(true)
    setDocumentUploadError('')

    try {
      const document = await uploadDocument(
        accessToken,
        documentFile,
        selectedKnowledgeBaseId,
      )

      setDocuments((currentDocuments) => [
        document,
        ...currentDocuments,
      ])

      setDocumentFile(null)
      form.reset()
    } catch (error) {
      if (error.status === 401) {
        clearSession()
        return
      }

      setDocumentUploadError(error.message)
    } finally {
      setIsUploadingDocument(false)
    }
  }

  async function handleCreateKnowledgeBase(event) {
    event.preventDefault()
    const name = knowledgeBaseName.trim()
    if (!name || isCreatingKnowledgeBase) {
      return
    }

    setIsCreatingKnowledgeBase(true)
    setKnowledgeBaseError('')
    try {
      const knowledgeBase = await createKnowledgeBase(
        accessToken,
        name,
        knowledgeBaseDescription.trim(),
      )
      setKnowledgeBases((currentKnowledgeBases) => [
        knowledgeBase,
        ...currentKnowledgeBases,
      ])
      setSelectedKnowledgeBaseId(String(knowledgeBase.id))
      setKnowledgeBaseName('')
      setKnowledgeBaseDescription('')
    } catch (error) {
      if (error.status === 401) {
        clearSession()
        return
      }
      setKnowledgeBaseError(error.message)
    } finally {
      setIsCreatingKnowledgeBase(false)
    }
  }

  async function handleDeleteKnowledgeBase() {
    if (!selectedKnowledgeBaseId || deletingKnowledgeBaseId !== null) {
      return
    }
    const knowledgeBase = knowledgeBases.find(
      (item) => String(item.id) === selectedKnowledgeBaseId,
    )
    if (!window.confirm(`Delete knowledge base "${knowledgeBase?.name}"?`)) {
      return
    }

    setDeletingKnowledgeBaseId(Number(selectedKnowledgeBaseId))
    setKnowledgeBaseError('')
    try {
      await deleteKnowledgeBase(accessToken, selectedKnowledgeBaseId)
      setKnowledgeBases((currentKnowledgeBases) => {
        const remainingKnowledgeBases = currentKnowledgeBases.filter(
          (item) => String(item.id) !== selectedKnowledgeBaseId,
        )
        setSelectedKnowledgeBaseId(
          remainingKnowledgeBases[0] ? String(remainingKnowledgeBases[0].id) : '',
        )
        return remainingKnowledgeBases
      })
    } catch (error) {
      if (error.status === 401) {
        clearSession()
        return
      }
      setKnowledgeBaseError(error.message)
    } finally {
      setDeletingKnowledgeBaseId(null)
    }
  }

  async function handleDeleteDocument(documentId) {
    if (!window.confirm('Delete this document?')) {
      return
    }

    setDeletingDocumentId(documentId)

    try {
      await deleteDocument(accessToken, documentId)

      setDocuments((currentDocuments) =>
        currentDocuments.filter((document) => document.id !== documentId),
      )

      if (selectedDocumentId === String(documentId)) {
        setSelectedDocumentId('')
        setDocumentAnswer(null)
        setDocumentAnswerError('')
      }
    } catch (error) {
      if (error.status === 401) {
        clearSession()
        return
      }

      setDocumentAnswerError(error.message)
    } finally {
      setDeletingDocumentId(null)
    }
  }

  async function handleRetryDocument(documentId) {
    if (retryingDocumentId !== null) {
      return
    }

    setRetryingDocumentId(documentId)
    setDocumentUploadError('')

    try {
      const document = await retryDocument(accessToken, documentId)

      setDocuments((currentDocuments) =>
        currentDocuments.map((currentDocument) =>
          currentDocument.id === document.id ? document : currentDocument,
        ),
      )
    } catch (error) {
      if (error.status === 401) {
        clearSession()
        return
      }

      setDocumentUploadError(error.message)
    } finally {
      setRetryingDocumentId(null)
    }
  }

  async function handleDocumentQuestionSubmit(event) {
    event.preventDefault()

    const question = documentQuestion.trim()

    if (!selectedDocumentId || !question || isAnsweringDocument) {
      return
    }

    setIsAnsweringDocument(true)
    setDocumentAnswerError('')
    setDocumentAnswer(null)

    try {
      const data = await answerDocument(
        accessToken,
        Number(selectedDocumentId),
        question,
      )

      setDocumentAnswer(data)
    } catch (error) {
      if (error.status === 401) {
        clearSession()
        return
      }

      setDocumentAnswerError(error.message)
    } finally {
      setIsAnsweringDocument(false)
    }
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <h1>我的任务</h1>
          <p className={apiStatus.isError ? 'api-status error' : 'api-status'}>
            {apiStatus.message}
          </p>
        </div>
        {accessToken && (
          <button
            className="logout-button"
            type="button"
            disabled={isLoggingOut}
            onClick={handleLogout}
          >
            注销
          </button>
        )}
      </header>

      {!accessToken ? (
        <LoginForm onLogin={handleLogin} />
      ) : (
        <>
          <form className="task-form" onSubmit={handleCreateTask}>
            <label className="screen-reader-only" htmlFor="new-task-title">
              新任务标题
            </label>
            <input
              id="new-task-title"
              value={draftTitle}
              placeholder="输入任务标题"
              onChange={(event) => {
                setDraftTitle(event.target.value)
                setTaskPlan(null)
              }}
            />
            <button type="submit" disabled={isCreating}>
              添加任务
            </button>
            <button
              className="ai-plan-button"
              type="button"
              disabled={isCreating || isSuggestingPlan}
              onClick={handleSuggestTaskPlan}
            >
              {isSuggestingPlan ? 'AI generating...' : 'AI suggest'}
            </button>
          </form>
          {taskPlan && (
            <section className="ai-plan-preview" aria-label="AI task suggestion">
              <h2>AI task suggestion</h2>
              <p className="plan-title">{taskPlan.title}</p>
              <p>{taskPlan.description}</p>
              <div className="tag-list">
                {taskPlan.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
              <button
                type="button"
                onClick={() => {
                  setDraftTitle(taskPlan.title)
                  setTaskPlan(null)
                }}
              >
                Use suggested title
              </button>
            </section>
          )}
          <p className="task-message" role="status">{taskMessage}</p>
          <section className="assistant-panel" aria-label="AI assistant">
            <div className="assistant-panel-header">
              <h2>AI assistant</h2>
              <button
                className="assistant-clear-button"
                type="button"
                disabled={assistantLoading || isClearingAssistantHistory}
                onClick={handleClearAssistantHistory}
              >
                {isClearingAssistantHistory ? 'Clearing...' : 'Clear conversation'}
              </button>
            </div>
            {assistantHistory.length > 0 && (
              <div className="assistant-history">
                {assistantHistory.map((item, index) => (
                  <p className={`assistant-message ${item.role}`} key={`${item.role}-${index}`}>
                    {item.content}
                  </p>
                ))}
              </div>
            )}
            {usedTools.includes('list_my_open_tasks') && (
              <p className="assistant-source">Used your current task data</p>
            )}
            {assistantCooldown > 0 ? (
              <p className="assistant-error">Too many requests. Try again in {assistantCooldown} seconds.</p>
            ) : (
              assistantError && <p className="assistant-error">{assistantError}</p>
            )}
            <form onSubmit={handleAssistantSubmit}>
              <textarea value={assistantMessage} maxLength={500} placeholder="Ask about your tasks" onChange={(event) => setAssistantMessage(event.target.value)} />
              <button type="submit" disabled={assistantLoading || assistantCooldown > 0 || !assistantMessage.trim()}>
                {assistantLoading ? 'Thinking...' : assistantCooldown > 0 ? `Retry in ${assistantCooldown}s` : 'Send'}
              </button>
            </form>
          </section>
          <section className="knowledge-panel" aria-label="Project knowledge assistant">
            <h2>Project knowledge</h2>
            <form onSubmit={handleProjectQuestionSubmit}>
              <textarea
                value={projectQuestion}
                maxLength={500}
                placeholder="Ask about this project's API or deployment"
                onChange={(event) => setProjectQuestion(event.target.value)}
              />
              <button
                type="submit"
                disabled={isAnsweringProjectQuestion || !projectQuestion.trim()}
              >
                {isAnsweringProjectQuestion ? 'Searching...' : 'Ask'}
              </button>
            </form>
            {projectQuestionError && (
              <p className="assistant-error">{projectQuestionError}</p>
            )}
            {projectAnswer && (
              <div className="knowledge-answer">
                <p>{projectAnswer.answer}</p>
                {projectAnswer.sources.length > 0 && (
                  <ul className="knowledge-sources" aria-label="Answer sources">
                    {projectAnswer.sources.map((source) => (
                      <li key={source}>{source}</li>
                    ))}
                  </ul>
                )}
                {projectAnswer.retrieval_mode === 'keyword_fallback' && (
                  <p className="knowledge-mode">Keyword retrieval fallback</p>
                )}
              </div>
            )}
          </section>
          <section className="document-answer-panel" aria-label="Document question">
            <div className="knowledge-base-header">
              <div>
                <h2>Knowledge bases</h2>
                <p>Organize documents before asking questions.</p>
              </div>
              {selectedKnowledgeBaseId && (
                <button
                  type="button"
                  className="delete-button"
                  disabled={deletingKnowledgeBaseId !== null}
                  onClick={handleDeleteKnowledgeBase}
                >
                  {deletingKnowledgeBaseId !== null ? 'Deleting...' : 'Delete knowledge base'}
                </button>
              )}
            </div>

            <label htmlFor="knowledge-base-select">Current knowledge base</label>
            <select
              id="knowledge-base-select"
              value={selectedKnowledgeBaseId}
              onChange={(event) => {
                setSelectedKnowledgeBaseId(event.target.value)
                setDocumentAnswer(null)
                setDocumentAnswerError('')
              }}
            >
              <option value="">Choose a knowledge base</option>
              {knowledgeBases.map((knowledgeBase) => (
                <option key={knowledgeBase.id} value={knowledgeBase.id}>
                  {knowledgeBase.name}
                </option>
              ))}
            </select>

            <form className="knowledge-base-form" onSubmit={handleCreateKnowledgeBase}>
              <label htmlFor="knowledge-base-name">New knowledge base</label>
              <input
                id="knowledge-base-name"
                value={knowledgeBaseName}
                maxLength={100}
                placeholder="For example: Employee handbook"
                onChange={(event) => setKnowledgeBaseName(event.target.value)}
              />
              <label htmlFor="knowledge-base-description">Description</label>
              <textarea
                id="knowledge-base-description"
                value={knowledgeBaseDescription}
                maxLength={2000}
                placeholder="Optional description"
                onChange={(event) => setKnowledgeBaseDescription(event.target.value)}
              />
              <button type="submit" disabled={!knowledgeBaseName.trim() || isCreatingKnowledgeBase}>
                {isCreatingKnowledgeBase ? 'Creating...' : 'Create knowledge base'}
              </button>
            </form>

            {knowledgeBaseError && (
              <p className="assistant-error">{knowledgeBaseError}</p>
            )}

            <h2>Documents</h2>
            <form
              className="document-upload-form"
              onSubmit={handleDocumentUpload}
            >
              <label htmlFor="document-file">Upload PDF</label>

              <input
                id="document-file"
                type="file"
                accept="application/pdf,.pdf"
                onChange={(event) => {
                  setDocumentFile(event.target.files?.[0] ?? null)
                  setDocumentUploadError('')
                }}
              />

              <button
                type="submit"
                disabled={!documentFile || !selectedKnowledgeBaseId || isUploadingDocument}
              >
                {isUploadingDocument ? 'Uploading...' : 'Upload document'}
              </button>
            </form>

            {documentUploadError && (
              <p className="assistant-error">{documentUploadError}</p>
            )}

            {documents.length > 0 && (
              <ul className="document-list" aria-label="Uploaded documents">
                {documents.map((document) => (
                  <li key={document.id} className="document-list-item">
                    <div>
                      <strong>{document.filename}</strong>
                      <span className={`document-status ${document.status}`}>
                        {document.status}
                      </span>
                      {document.error_message && (
                        <p className="document-error">{document.error_message}</p>
                      )}
                    </div>

                    <div className="document-actions">
                      {document.status === 'failed' && (
                        <button
                          type="button"
                          className="retry-button"
                          disabled={
                            deletingDocumentId !== null ||
                            retryingDocumentId !== null
                          }
                          onClick={() => handleRetryDocument(document.id)}
                        >
                          {retryingDocumentId === document.id ? 'Retrying...' : 'Retry'}
                        </button>
                      )}

                      <button
                        type="button"
                        className="delete-button"
                        disabled={
                          deletingDocumentId !== null ||
                          retryingDocumentId !== null
                        }
                        onClick={() => handleDeleteDocument(document.id)}
                      >
                        {deletingDocumentId === document.id ? 'Deleting...' : 'Delete'}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {documents.length === 0 ? (
              <p>No documents uploaded yet.</p>
            ) : readyDocuments.length === 0 ? (
              <p>No documents are ready for questions yet.</p>
            ) : (
              <form onSubmit={handleDocumentQuestionSubmit}>
                <label htmlFor="document-select">Document</label>
                <select
                  id="document-select"
                  value={selectedDocumentId}
                  onChange={(event) => {
                    setSelectedDocumentId(event.target.value)
                    setDocumentAnswer(null)
                    setDocumentAnswerError('')
                  }}
                >
                  <option value="">Choose a ready document</option>
                  {
                    readyDocuments.map((document) => (
                      <option key={document.id} value={document.id}>
                        {document.filename}
                      </option>
                    ))}
                </select>

                <label htmlFor="document-question">Question</label>
                <textarea
                  id="document-question"
                  value={documentQuestion}
                  maxLength={2000}
                  placeholder="Ask about the selected document"
                  onChange={(event) => setDocumentQuestion(event.target.value)}
                />

                <button
                  type="submit"
                  disabled={
                    isAnsweringDocument ||
                    !selectedDocumentId ||
                    !documentQuestion.trim()
                  }
                >
                  {isAnsweringDocument ? 'Answering...' : 'Ask document'}
                </button>
              </form>
            )}

            {documentAnswerError && (
              <p className="assistant-error">{documentAnswerError}</p>
            )}

            {documentAnswer && (
              <div className="document-answer">
                <p>{documentAnswer.answer}</p>

                {documentAnswer.sources.length > 0 && (
                  <ul className="knowledge-sources" aria-label="Document sources">
                    {documentAnswer.sources.map((source) => (
                      <li key={`${source.document_id}-${source.chunk_index}`}>
                        {source.filename} - chunk {source.chunk_index}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </section>
          <TaskList
            title="未完成"
            listId="unfinished-title"
            tasks={unfinishedTasks}
            deletingTaskId={deletingTaskId}
            updatingTaskId={updatingTaskId}
            onDelete={handleDeleteTask}
            onRewriteTitle={handleRewriteTitle}
            onToggle={handleToggleTask}
            onUpdateTitle={handleUpdateTaskTitle}
          />

          <TaskList
            title="已完成"
            listId="completed-title"
            tasks={completedTasks}
            deletingTaskId={deletingTaskId}
            updatingTaskId={updatingTaskId}
            onDelete={handleDeleteTask}
            onRewriteTitle={handleRewriteTitle}
            onToggle={handleToggleTask}
            onUpdateTitle={handleUpdateTaskTitle}
          />
        </>
      )}
    </main>
  )
}

export default App
