import { useState } from 'react'

function LoginForm({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setIsSubmitting(true)
    setMessage('正在登录...')

    try {
      await onLogin(username, password)
    } catch (error) {
      setMessage(error.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="login-section" aria-labelledby="login-title">
      <h2 id="login-title">登录</h2>
      <form className="login-form" onSubmit={handleSubmit}>
        <label htmlFor="username">用户名</label>
        <input
          id="username"
          value={username}
          autoComplete="username"
          onChange={(event) => setUsername(event.target.value)}
          required
        />
        <label htmlFor="password">密码</label>
        <input
          id="password"
          type="password"
          value={password}
          autoComplete="current-password"
          onChange={(event) => setPassword(event.target.value)}
          required
        />
        <button type="submit" disabled={isSubmitting}>
          登录
        </button>
      </form>
      <p className="login-message" role="alert">{message}</p>
    </section>
  )
}

export default LoginForm
