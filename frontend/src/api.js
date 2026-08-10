const API_PREFIX = '/api'

async function readJson(response, fallbackMessage) {
  const data = await response.json()

  if (!response.ok) {
    const error = new Error(data.detail || fallbackMessage)
    error.status = response.status
    const retryAfter = Number(response.headers.get('Retry-After'))
    if (Number.isFinite(retryAfter) && retryAfter > 0) {
      error.retryAfter = retryAfter
    }
    throw error
  }

  return data
}

export async function getApiHealth() {
  const response = await fetch(`${API_PREFIX}/health`)

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  return response.json()
}

export async function login(username, password) {
  const response = await fetch(`${API_PREFIX}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  })

  return readJson(response, '登录失败')
}

export async function getMyTasks(accessToken, done) {
  const response = await fetch(
    `${API_PREFIX}/tasks/me?done=${done}&archived=false&limit=100`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  )

  const data = await readJson(response, '读取任务失败')
  return data.items
}

export async function createTask(accessToken, title) {
  const response = await fetch(`${API_PREFIX}/tasks`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  })

  return readJson(response, '创建任务失败')
}

export async function setTaskDone(accessToken, taskId, done) {
  const action = done ? 'done' : 'undone'
  const response = await fetch(`${API_PREFIX}/tasks/${taskId}/${action}`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })

  return readJson(response, '更新任务失败')
}

export async function deleteTask(accessToken, taskId) {
  const response = await fetch(`${API_PREFIX}/tasks/${taskId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })

  return readJson(response, '删除任务失败')
}

export async function updateTaskTitle(accessToken, taskId, title) {
  const response = await fetch(`${API_PREFIX}/tasks/${taskId}`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  })

  return readJson(response, '更新任务失败')
}

export async function logout(accessToken) {
  const response = await fetch(`${API_PREFIX}/users/me/logout`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })

  if (!response.ok) {
    return readJson(response, '注销失败')
  }
}

export async function rewriteTaskTitle(accessToken, title) {
  const response = await fetch(`${API_PREFIX}/ai/rewrite-task-title`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  })

  const data = await readJson(response, 'AI 标题优化失败')
  return data.reply
}

export async function suggestTaskPlan(accessToken, title) {
  const response = await fetch(`${API_PREFIX}/ai/suggest-task-plan`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  })

  return readJson(response, 'AI task plan suggestion failed')
}

export async function askAssistant(accessToken, message) {
  const response = await fetch(`${API_PREFIX}/ai/assistant`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message }),
  })

  return readJson(response, 'AI assistant request failed')
}

export async function answerProjectQuestion(accessToken, question) {
  const response = await fetch(`${API_PREFIX}/ai/answer-project-question`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question }),
  })

  return readJson(response, 'Project question request failed')
}

export async function clearAssistantHistory(accessToken) {
  const response = await fetch(`${API_PREFIX}/ai/assistant/history`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })

  if (!response.ok) {
    return readJson(response, 'Could not clear AI conversation')
  }
}

export async function getAssistantHistory(accessToken) {
  const response = await fetch(`${API_PREFIX}/ai/assistant/history`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })

  return readJson(response, 'Could not load AI conversation')
}

export async function answerDocument(accessToken, documentId, question) {
  const response = await fetch(`${API_PREFIX}/ai/document-answer`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      document_id: documentId,
      question,
    }),
  })

  return readJson(response, 'Document answer request failed')
}

export async function getMyDocuments(accessToken) {
  const response = await fetch(`${API_PREFIX}/documents`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })

  return readJson(response, 'Failed to load documents')
}

export async function deleteDocument(accessToken, documentId) {
  const response = await fetch(`${API_PREFIX}/documents/${documentId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })

  if (response.status === 204) {
    return
  }

  return readJson(response, 'Failed to delete document')
}