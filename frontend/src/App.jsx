import { useEffect, useRef, useState } from 'react'
import './App.css'
import swireLogo from './assets/swire-logo.svg'

const quickActions = ['Check another PO', 'Show related documents', 'Vendor details']

const defaultConversationTemplates = [
  {
    id: 'conversation-po-12321',
    title: 'PO 12321 Enquiry',
    messages: [
      { role: 'assistant', text: 'PO 12321 is approved and waiting for supplier confirmation.' },
      { role: 'user', text: 'Can you check the estimated delivery date?' },
      { role: 'assistant', text: 'Latest ETA is 12 Jun 2026.' },
    ],
  },
  {
    id: 'conversation-general-procurement',
    title: 'General Procurement',
    messages: [
      { role: 'assistant', text: 'I can help with purchase requests, approvals, and sourcing steps.' },
      { role: 'user', text: 'What is the approval threshold for direct purchase?' },
      { role: 'assistant', text: 'Direct purchases above HKD 100,000 require manager approval.' },
    ],
  },
  {
    id: 'conversation-vendor-enquiry',
    title: 'Vendor Enquiry',
    messages: [
      { role: 'assistant', text: 'Vendor ACME Supplies is active and compliant.' },
      { role: 'user', text: 'Do we have their latest banking confirmation?' },
      { role: 'assistant', text: 'Yes, the latest bank confirmation was updated on 28 May 2026.' },
    ],
  },
]

const conversationsStoragePrefix = 'chatbot_conversations_'
const activeConversationStoragePrefix = 'chatbot_active_conversation_'

function getConversationsStorageKey(username) {
  return `${conversationsStoragePrefix}${username}`
}

function getActiveConversationStorageKey(username) {
  return `${activeConversationStoragePrefix}${username}`
}

function readStoredConversations(username) {
  if (!username) return []

  const raw = localStorage.getItem(getConversationsStorageKey(username))
  if (!raw) return []

  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []

    return parsed
      .map((conversation, conversationIndex) => {
        const conversationId = String(conversation?.id || '').trim()
        if (!conversationId) return null

        const messages = Array.isArray(conversation?.messages) ? conversation.messages : []
        return {
          id: conversationId,
          title: String(conversation?.title || `Conversation ${conversationIndex + 1}`),
          messages: messages
            .map((message, messageIndex) => {
              const role = message?.role === 'assistant' ? 'assistant' : 'user'
              const text = String(message?.text || '').trim()
              if (!text) return null

              return {
                id: String(message?.id || `${conversationId}-message-${messageIndex}`),
                role,
                text,
                createdAt: String(message?.createdAt || new Date().toISOString()),
              }
            })
            .filter(Boolean),
        }
      })
      .filter(Boolean)
  } catch {
    return []
  }
}

function buildDefaultConversations() {
  const now = Date.now()
  return defaultConversationTemplates.map((conversation, conversationIndex) => ({
    ...conversation,
    messages: conversation.messages.map((message, messageIndex) => ({
      id: `${conversation.id}-seed-${messageIndex}`,
      ...message,
      createdAt: new Date(now - (conversationIndex * 3 + messageIndex + 1) * 60000).toISOString(),
    })),
  }))
}

function formatTime(value) {
  if (!value) return ''

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''

  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

async function apiRequest(path, { method = 'GET', body, token } = {}) {
  const response = await fetch(path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: 'Bearer ' + token } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(data.error || 'Request failed')
  }

  return data
}

function LoginScreen({ onLogin, loading, error }) {
  const [username, setUsername] = useState('john')
  const [password, setPassword] = useState('password123')

  const handleSubmit = (event) => {
    event.preventDefault()
    onLogin({ username, password })
  }

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="brand login-brand">
          <div className="brand-mark" aria-hidden="true">
            <img src={swireLogo} alt="" />
          </div>
          <span className="brand-name">SWIRE</span>
        </div>

        <h1>Swire Procurement Assistant</h1>
        <p>Sign in to continue</p>

        <form onSubmit={handleSubmit} className="login-form">
          <label htmlFor="username">Username</label>
          <input
            id="username"
            name="username"
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
          />

          {error && <p className="login-error">{error}</p>}

          <button type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}

function App() {
  const [authToken, setAuthToken] = useState(() => localStorage.getItem('chatbot_token') || '')
  const [user, setUser] = useState(null)
  const [isCheckingSession, setIsCheckingSession] = useState(true)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [authError, setAuthError] = useState('')

  const [conversations, setConversations] = useState(() => buildDefaultConversations())
  const [activeConversationId, setActiveConversationId] = useState('conversation-po-12321')
  const [inputValue, setInputValue] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [profileMenuOpen, setProfileMenuOpen] = useState(false)

  const menuRef = useRef(null)

  useEffect(() => {
    const closeMenuOnOutsideClick = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setProfileMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', closeMenuOnOutsideClick)
    return () => document.removeEventListener('mousedown', closeMenuOnOutsideClick)
  }, [])

  useEffect(() => {
    const loadSession = async () => {
      if (!authToken) {
        setUser(null)
        const defaults = buildDefaultConversations()
        setConversations(defaults)
        setActiveConversationId(defaults[0]?.id || '')
        setIsCheckingSession(false)
        return
      }

      try {
        const me = await apiRequest('/api/me', { token: authToken })
        setUser(me.user)

        const storedConversations = readStoredConversations(me.user.username)
        const storedActiveConversationId = localStorage.getItem(
          getActiveConversationStorageKey(me.user.username),
        )

        if (storedConversations.length > 0) {
          const fallbackConversationId = storedConversations[0]?.id || ''
          const nextActiveConversationId = storedConversations.some(
            (conversation) => conversation.id === storedActiveConversationId,
          )
            ? storedActiveConversationId
            : fallbackConversationId

          setConversations(storedConversations)
          setActiveConversationId(nextActiveConversationId)
        } else {
          const defaults = buildDefaultConversations()
          const history = await apiRequest('/api/chat/history', { token: authToken })
          if (history.messages.length > 0 && defaults[0]) {
            defaults[0] = {
              ...defaults[0],
              messages: [...defaults[0].messages, ...history.messages],
            }
          }
          setConversations(defaults)
          setActiveConversationId(defaults[0]?.id || '')
        }
      } catch {
        localStorage.removeItem('chatbot_token')
        setAuthToken('')
        setUser(null)
        const defaults = buildDefaultConversations()
        setConversations(defaults)
        setActiveConversationId(defaults[0]?.id || '')
      } finally {
        setIsCheckingSession(false)
      }
    }

    void loadSession()
  }, [authToken])

  useEffect(() => {
    if (!user?.username || conversations.length === 0) return

    localStorage.setItem(getConversationsStorageKey(user.username), JSON.stringify(conversations))
  }, [conversations, user?.username])

  useEffect(() => {
    if (!user?.username || !activeConversationId) return

    localStorage.setItem(getActiveConversationStorageKey(user.username), activeConversationId)
  }, [activeConversationId, user?.username])

  const handleLogin = async ({ username, password }) => {
    setIsLoggingIn(true)
    setAuthError('')

    try {
      const result = await apiRequest('/api/login', {
        method: 'POST',
        body: { username, password },
      })

      localStorage.setItem('chatbot_token', result.token)
      setAuthToken(result.token)
      setUser(result.user)
      setProfileMenuOpen(false)
    } catch (error) {
      setAuthError(error.message)
    } finally {
      setIsLoggingIn(false)
    }
  }

  const handleLogout = async () => {
    try {
      if (authToken) {
        await apiRequest('/api/logout', {
          method: 'POST',
          token: authToken,
        })
      }
    } finally {
      localStorage.removeItem('chatbot_token')
      setAuthToken('')
      setUser(null)
      const defaults = buildDefaultConversations()
      setConversations(defaults)
      setActiveConversationId(defaults[0]?.id || '')
      setInputValue('')
      setProfileMenuOpen(false)
    }
  }

  const activeConversation =
    conversations.find((conversation) => conversation.id === activeConversationId) || conversations[0]
  const activeMessages = activeConversation?.messages || []

  const updateActiveConversationMessages = (updater) => {
    setConversations((previousConversations) =>
      previousConversations.map((conversation) =>
        conversation.id === activeConversation?.id
          ? { ...conversation, messages: updater(conversation.messages) }
          : conversation,
      ),
    )
  }

  const handleCreateConversation = () => {
    const now = new Date().toISOString()
    const id = `conversation-${Date.now()}`
    const newConversation = {
      id,
      title: 'New chat',
      messages: [
        {
          id: `${id}-welcome`,
          role: 'assistant',
          text: 'What can I help you today?',
          createdAt: now,
        },
      ],
    }

    setConversations((previousConversations) => [newConversation, ...previousConversations])
    setActiveConversationId(id)
    setInputValue('')
  }

  const handleSendMessage = async () => {
    const trimmedMessage = inputValue.trim()
    if (!trimmedMessage || !authToken || isSending || !activeConversation) return

    const tempUserMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      text: trimmedMessage,
      createdAt: new Date().toISOString(),
    }

    updateActiveConversationMessages((previousMessages) => [...previousMessages, tempUserMessage])
    setInputValue('')
    setIsSending(true)

    try {
      const result = await apiRequest('/api/chat', {
        method: 'POST',
        token: authToken,
        body: { message: trimmedMessage },
      })

      updateActiveConversationMessages((previousMessages) => [
        ...previousMessages.filter((message) => message.id !== tempUserMessage.id),
        result.userMessage,
        result.assistantMessage,
      ])
    } catch (error) {
      updateActiveConversationMessages((previousMessages) => [
        ...previousMessages,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          text: `Unable to send message: ${error.message}`,
          createdAt: new Date().toISOString(),
        },
      ])
    } finally {
      setIsSending(false)
    }
  }

  if (isCheckingSession) {
    return (
      <div className="login-shell">
        <p className="loading-text">Loading...</p>
      </div>
    )
  }

  if (!user) {
    return <LoginScreen onLogin={handleLogin} loading={isLoggingIn} error={authError} />
  }

  return (
    <div className="chatbot-shell">
      <header className="top-bar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <img src={swireLogo} alt="" />
          </div>
          <span className="brand-name">SWIRE</span>
        </div>
        <div className="assistant-header">
          <h1>Swire Procurement Assistant</h1>
          <p>
            <span className="online-dot" />
            Online
          </p>
        </div>
      </header>

      <div className="chat-layout">
        <aside className="sidebar">
          <button className="new-chat" type="button" onClick={handleCreateConversation}>
            + New chat
          </button>

          <h2>Conversation</h2>
          <ul className="history-list">
            {conversations.map((conversation) => {
              const latestMessage = conversation.messages[conversation.messages.length - 1]
              return (
                <li
                  key={conversation.id}
                  className={conversation.id === activeConversation?.id ? 'active' : ''}
                >
                  <button
                    className="history-item"
                    type="button"
                    onClick={() => setActiveConversationId(conversation.id)}
                  >
                    <p>{conversation.title}</p>
                    <span>{formatTime(latestMessage?.createdAt)}</span>
                  </button>
                </li>
              )
            })}
          </ul>

          <div className="profile-wrapper" ref={menuRef}>
            <button
              className="profile-card"
              type="button"
              onClick={() => setProfileMenuOpen((open) => !open)}
            >
              <div className="avatar">{user.displayName.slice(0, 2).toUpperCase()}</div>
              <div>
                <strong>{user.displayName}</strong>
                <p>{user.department}</p>
              </div>
              <span>⌄</span>
            </button>

            {profileMenuOpen && (
              <div className="profile-menu">
                <button type="button" onClick={handleLogout}>
                  Logout
                </button>
              </div>
            )}
          </div>
        </aside>

        <main className="chat-panel">
          <div className="chat-scroll">
            <div className="date-pill">Today</div>

            {activeMessages.length === 0 && (
              <div className="message-row received">
                <div className="bot-icon">🤖</div>
                <div>
                  <div className="message bubble received-bubble">
                    Welcome! Ask anything about procurement workflows.
                  </div>
                </div>
              </div>
            )}

            {activeMessages.map((message) => (
              <div key={message.id}>
                <div className={`message-row ${message.role === 'user' ? 'sent' : 'received'}`}>
                  {message.role === 'assistant' && <div className="bot-icon">🤖</div>}
                  <div className={`message bubble ${message.role === 'user' ? 'sent-bubble' : 'received-bubble'}`}>
                    {message.text}
                  </div>
                </div>
                <div className={`timestamp ${message.role === 'user' ? 'sent-time' : ''}`}>
                  {formatTime(message.createdAt)}
                </div>
              </div>
            ))}
          </div>

          <div className="chat-footer">
            <div className="quick-actions">
              {quickActions.map((label) => (
                <button key={label} type="button" onClick={() => setInputValue(label)}>
                  {label}
                </button>
              ))}
            </div>

            <div className="input-area">
              <input
                type="text"
                placeholder="Ask anything about procurement..."
                value={inputValue}
                onChange={(event) => setInputValue(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault()
                    void handleSendMessage()
                  }
                }}
              />
              <button type="button" aria-label="Send message" onClick={handleSendMessage}>
                {isSending ? '...' : '➤'}
              </button>
            </div>
            <p className="footnote">AI-generated responses. Please review before action.</p>
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
