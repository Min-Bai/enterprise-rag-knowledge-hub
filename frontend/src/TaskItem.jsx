import { useEffect, useRef, useState } from 'react'

function TaskItem({
  task,
  isDeleting,
  isUpdating,
  onDelete,
  onRewriteTitle,
  onToggle,
  onUpdateTitle,
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [title, setTitle] = useState(task.title)
  const [message, setMessage] = useState('')
  const [isRewriting, setIsRewriting] = useState(false)
  const titleInputRef = useRef(null)

  useEffect(() => {
    if (isEditing) {
      titleInputRef.current?.focus()
    }
  }, [isEditing])

  async function handleSave() {
    const nextTitle = title.trim()
    if (!nextTitle) {
      setMessage('标题不能为空')
      return
    }

    try {
      await onUpdateTitle(task.id, nextTitle)
      setIsEditing(false)
      setMessage('')
    } catch (error) {
      setMessage(error.message)
    }
  }

  function cancelEdit() {
    setTitle(task.title)
    setMessage('')
    setIsEditing(false)
  }

  async function handleRewriteTitle() {
    const currentTitle = title.trim()
    if (!currentTitle) {
      setMessage('请先输入任务标题')
      return
    }

    setIsRewriting(true)
    setMessage('AI 正在优化标题...')

    try {
      const reply = await onRewriteTitle(currentTitle)
      setTitle(reply)
      setMessage('')
    } catch (error) {
      setMessage(error.message)
    } finally {
      setIsRewriting(false)
    }
  }

  return (
    <li className="task-item">
      <div className="task-row">
        <label className={task.done ? 'task-label done' : 'task-label'}>
          <input
            type="checkbox"
            checked={task.done}
            disabled={isUpdating || isDeleting}
            onChange={(event) => onToggle(task.id, event.target.checked)}
          />
          {isEditing ? (
            <input
              className="inline-edit-input"
              ref={titleInputRef}
              value={title}
              disabled={isRewriting}
              onChange={(event) => setTitle(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  handleSave()
                }

                if (event.key === 'Escape') {
                  cancelEdit()
                }
              }}
            />
          ) : (
            <span>{task.title}</span>
          )}
        </label>
        {isEditing ? (
          <>
            <button
              className="ai-button"
              type="button"
              disabled={isRewriting}
              onClick={handleRewriteTitle}
            >
              AI 优化
            </button>
            <button
              className="edit-button"
              type="button"
              disabled={isRewriting}
              onClick={handleSave}
            >
              保存
            </button>
            <button
              className="cancel-button"
              type="button"
              disabled={isRewriting}
              onClick={cancelEdit}
            >
              取消
            </button>
          </>
        ) : (
          <>
            <button className="edit-button" type="button" onClick={() => setIsEditing(true)}>
              编辑
            </button>
            <button
              className="delete-button"
              type="button"
              disabled={isDeleting}
              onClick={() => onDelete(task)}
            >
              删除
            </button>
          </>
        )}
      </div>
      {message && <p className="item-message">{message}</p>}
    </li>
  )
}

export default TaskItem
