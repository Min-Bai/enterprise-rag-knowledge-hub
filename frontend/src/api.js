const API_PREFIX = '/api'

async function readJson(response, fallbackMessage) {
  const contentType = response.headers.get('Content-Type') || ''
  const data = contentType.includes('application/json') ? await response.json() : null
  if (!response.ok) {
    const error = new Error(data?.detail || fallbackMessage)
    error.status = response.status
    throw error
  }
  if (data === null) throw new Error(`${fallbackMessage} (invalid server response)`)
  return data
}

export async function getApiHealth() {
  const response = await fetch(`${API_PREFIX}/health`)
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

export async function login(username, password) {
  const response = await fetch(`${API_PREFIX}/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) })
  return readJson(response, 'Login failed')
}

export async function logout(accessToken) {
  const response = await fetch(`${API_PREFIX}/users/me/logout`, { method: 'POST', headers: { Authorization: `Bearer ${accessToken}` } })
  if (!response.ok) return readJson(response, 'Logout failed')
}

export async function answerDocument(accessToken, documentId, question, conversationId) {
  const body = { document_id: documentId, question }
  if (conversationId) body.conversation_id = Number(conversationId)
  const response = await fetch(`${API_PREFIX}/ai/document-answer`, { method: 'POST', headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  return readJson(response, 'Document answer request failed')
}

export async function streamDocumentAnswer(accessToken, documentId, question, conversationId, handlers) {
  const body = { document_id: documentId, question }
  if (conversationId) body.conversation_id = Number(conversationId)
  return streamAnswer(`${API_PREFIX}/ai/document-answer/stream`, accessToken, body, handlers)
}

export async function streamKnowledgeBaseAnswer(accessToken, knowledgeBaseId, question, conversationId, tags, handlers) {
  const body = { knowledge_base_id: knowledgeBaseId, question }
  if (conversationId) body.conversation_id = Number(conversationId)
  if (tags?.length) body.tags = tags
  return streamAnswer(`${API_PREFIX}/ai/knowledge-base-answer/stream`, accessToken, body, handlers)
}

async function streamAnswer(url, accessToken, body, handlers) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) return readJson(response, 'Document answer request failed')
  if (!response.body) throw new Error('Document answer stream is unavailable')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let completed = false
  function handleFrame(frame) {
    const event = frame.match(/^event: (.+)$/m)?.[1]
    const payload = frame.match(/^data: (.+)$/m)?.[1]
    if (!event || payload === undefined) return
    const data = JSON.parse(payload)
    if (event === 'metadata') handlers.onMetadata?.(data)
    if (event === 'token') handlers.onToken?.(data.text || '')
    if (event === 'error') throw new Error(data.detail || 'Document answer stream failed')
    if (event === 'done') completed = true
  }
  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const frames = buffer.split('\n\n')
    buffer = frames.pop()
    for (const frame of frames) handleFrame(frame)
    if (done) break
  }
  if (buffer) handleFrame(buffer)
  if (!completed) throw new Error('Document answer stream ended unexpectedly')
}

export async function getDocumentConversations(accessToken, documentId) {
  return readJson(await fetch(`${API_PREFIX}/ai/documents/${documentId}/conversations`, { headers: { Authorization: `Bearer ${accessToken}` } }), 'Failed to load conversation history')
}

export async function getKnowledgeBaseConversations(accessToken, knowledgeBaseId) {
  return readJson(await fetch(`${API_PREFIX}/ai/knowledge-bases/${knowledgeBaseId}/conversations`, { headers: { Authorization: `Bearer ${accessToken}` } }), 'Failed to load conversation history')
}

export async function deleteConversation(accessToken, conversationId) {
  const response = await fetch(`${API_PREFIX}/ai/conversations/${conversationId}`, { method: 'DELETE', headers: { Authorization: `Bearer ${accessToken}` } })
  if (response.status !== 204) await readJson(response, 'Failed to delete conversation')
}

export async function getKnowledgeBases(accessToken) {
  return readJson(await fetch(`${API_PREFIX}/knowledge-bases`, { headers: { Authorization: `Bearer ${accessToken}` } }), 'Failed to load knowledge bases')
}

export async function createKnowledgeBase(accessToken, name, description) {
  return readJson(await fetch(`${API_PREFIX}/knowledge-bases`, { method: 'POST', headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ name, description: description || null }) }), 'Failed to create knowledge base')
}

export async function deleteKnowledgeBase(accessToken, knowledgeBaseId) {
  const response = await fetch(`${API_PREFIX}/knowledge-bases/${knowledgeBaseId}`, { method: 'DELETE', headers: { Authorization: `Bearer ${accessToken}` } })
  if (response.status !== 204) await readJson(response, 'Failed to delete knowledge base')
}

export async function updateKnowledgeBase(accessToken, knowledgeBaseId, name, description) {
  return readJson(await fetch(`${API_PREFIX}/knowledge-bases/${knowledgeBaseId}`, { method: 'PATCH', headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ name, description: description || null }) }), 'Failed to update knowledge base')
}

export async function getKnowledgeBaseMembers(accessToken, knowledgeBaseId) {
  return readJson(await fetch(`${API_PREFIX}/knowledge-bases/${knowledgeBaseId}/members`, { headers: { Authorization: `Bearer ${accessToken}` } }), 'Failed to load knowledge base members')
}

export async function addKnowledgeBaseMember(accessToken, knowledgeBaseId, username, role) {
  return readJson(await fetch(`${API_PREFIX}/knowledge-bases/${knowledgeBaseId}/members`, { method: 'PUT', headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ username, role }) }), 'Failed to share knowledge base')
}

export async function removeKnowledgeBaseMember(accessToken, knowledgeBaseId, userId) {
  const response = await fetch(`${API_PREFIX}/knowledge-bases/${knowledgeBaseId}/members/${userId}`, { method: 'DELETE', headers: { Authorization: `Bearer ${accessToken}` } })
  if (response.status !== 204) await readJson(response, 'Failed to remove knowledge base member')
}

export async function getKnowledgeBaseAuditLogs(accessToken, knowledgeBaseId) {
  return readJson(await fetch(`${API_PREFIX}/knowledge-bases/${knowledgeBaseId}/audit-logs`, { headers: { Authorization: `Bearer ${accessToken}` } }), 'Failed to load audit logs')
}

export async function getKnowledgeBaseFeedbackSummary(accessToken, knowledgeBaseId) {
  return readJson(await fetch(`${API_PREFIX}/knowledge-bases/${knowledgeBaseId}/feedback-summary`, { headers: { Authorization: `Bearer ${accessToken}` } }), 'Failed to load feedback quality')
}

export async function submitAnswerFeedback(accessToken, messageId, feedback, comment) {
  return readJson(await fetch(`${API_PREFIX}/ai/answer-messages/${messageId}/feedback`, { method: 'PUT', headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ feedback, comment: comment || null }) }), 'Failed to save answer feedback')
}

export async function uploadDocument(accessToken, file, knowledgeBaseId, tags) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('knowledge_base_id', knowledgeBaseId)
  if (tags?.length) formData.append('tags', tags.join(','))
  return readJson(await fetch(`${API_PREFIX}/documents`, { method: 'POST', headers: { Authorization: `Bearer ${accessToken}` }, body: formData }), 'Failed to upload document')
}

export async function getMyDocuments(accessToken, knowledgeBaseId) {
  return readJson(await fetch(`${API_PREFIX}/documents?knowledge_base_id=${knowledgeBaseId}`, { headers: { Authorization: `Bearer ${accessToken}` } }), 'Failed to load documents')
}

export async function searchDocuments(accessToken, knowledgeBaseId, question, tags) {
  const params = new URLSearchParams({ knowledge_base_id: knowledgeBaseId })
  return readJson(await fetch(`${API_PREFIX}/documents/search?${params}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, tags }),
  }), 'Failed to search documents')
}

export async function deleteDocument(accessToken, documentId) {
  const response = await fetch(`${API_PREFIX}/documents/${documentId}`, { method: 'DELETE', headers: { Authorization: `Bearer ${accessToken}` } })
  if (response.status !== 204) await readJson(response, 'Failed to delete document')
}

export async function retryDocument(accessToken, documentId) {
  return readJson(await fetch(`${API_PREFIX}/documents/${documentId}/retry`, { method: 'POST', headers: { Authorization: `Bearer ${accessToken}` } }), 'Failed to retry document')
}

export async function reindexDocument(accessToken, documentId) {
  return readJson(await fetch(`${API_PREFIX}/documents/${documentId}/reindex`, { method: 'POST', headers: { Authorization: `Bearer ${accessToken}` } }), 'Failed to reindex document')
}

export async function updateDocumentTags(accessToken, documentId, tags) {
  return readJson(await fetch(`${API_PREFIX}/documents/${documentId}/tags`, { method: 'PATCH', headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ tags }) }), 'Failed to update document tags')
}

export async function downloadDocument(accessToken, selectedDocument) {
  const response = await fetch(`${API_PREFIX}/documents/${selectedDocument.id}/download`, { headers: { Authorization: `Bearer ${accessToken}` } })
  if (!response.ok) await readJson(response, 'Failed to download document')
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = selectedDocument.filename
  link.click()
  URL.revokeObjectURL(url)
}
