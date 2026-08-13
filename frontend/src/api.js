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

export async function getDocumentConversations(accessToken, documentId) {
  return readJson(await fetch(`${API_PREFIX}/ai/documents/${documentId}/conversations`, { headers: { Authorization: `Bearer ${accessToken}` } }), 'Failed to load conversation history')
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

export async function uploadDocument(accessToken, file, knowledgeBaseId) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('knowledge_base_id', knowledgeBaseId)
  return readJson(await fetch(`${API_PREFIX}/documents`, { method: 'POST', headers: { Authorization: `Bearer ${accessToken}` }, body: formData }), 'Failed to upload document')
}

export async function getMyDocuments(accessToken, knowledgeBaseId) {
  return readJson(await fetch(`${API_PREFIX}/documents?knowledge_base_id=${knowledgeBaseId}`, { headers: { Authorization: `Bearer ${accessToken}` } }), 'Failed to load documents')
}

export async function deleteDocument(accessToken, documentId) {
  const response = await fetch(`${API_PREFIX}/documents/${documentId}`, { method: 'DELETE', headers: { Authorization: `Bearer ${accessToken}` } })
  if (response.status !== 204) await readJson(response, 'Failed to delete document')
}

export async function retryDocument(accessToken, documentId) {
  return readJson(await fetch(`${API_PREFIX}/documents/${documentId}/retry`, { method: 'POST', headers: { Authorization: `Bearer ${accessToken}` } }), 'Failed to retry document')
}
