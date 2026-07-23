import { useEffect, useState } from 'react'
import './App.css'
import {
  createTask,
  deleteTask,
  getApiHealth,
  getMyTasks,
  login,
  logout,
  rewriteTaskTitle,
  setTaskDone,
  suggestTaskPlan,
  updateTaskTitle,
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
  const [apiStatus, setApiStatus] = useState({
    message: '正在检查 API...',
    isError: false,
  })
  const unfinishedTasks = tasks.filter((task) => !task.done)
  const completedTasks = tasks.filter((task) => task.done)

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
