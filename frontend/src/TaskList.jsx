import TaskItem from './TaskItem.jsx'

function TaskList({
  deletingTaskId,
  listId,
  onDelete,
  onRewriteTitle,
  onToggle,
  onUpdateTitle,
  tasks,
  title,
  updatingTaskId,
}) {
  return (
    <section className="task-group" aria-labelledby={listId}>
      <h2 id={listId}>{title}</h2>
      {tasks.length === 0 ? (
        <p className="empty-state">暂无任务</p>
      ) : (
        <ul>
          {tasks.map((task) => (
            <TaskItem
              key={task.id}
              task={task}
              isDeleting={deletingTaskId === task.id}
              isUpdating={updatingTaskId === task.id}
              onDelete={onDelete}
              onRewriteTitle={onRewriteTitle}
              onToggle={onToggle}
              onUpdateTitle={onUpdateTitle}
            />
          ))}
        </ul>
      )}
    </section>
  )
}

export default TaskList
