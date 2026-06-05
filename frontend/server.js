import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import Database from 'better-sqlite3'
import express from 'express'
import rateLimit from 'express-rate-limit'

const PORT = Number(process.env.PORT || 3001)
const AGENT_API_URL = process.env.AGENT_API_URL || 'http://127.0.0.1:8000'
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const dataDirectory = path.join(__dirname, 'data')

if (!fs.existsSync(dataDirectory)) {
  fs.mkdirSync(dataDirectory, { recursive: true })
}

const database = new Database(path.join(dataDirectory, 'chatbot.sqlite'))
database.pragma('journal_mode = WAL')

database.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    display_name TEXT NOT NULL,
    department TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
  );

  CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
  );
`)

// Add demo_user_key column if it doesn't exist
try {
  database.exec('ALTER TABLE users ADD COLUMN demo_user_key TEXT')
} catch {
  // Column already exists
}

const upsertUser = database.prepare(`
  INSERT INTO users (username, password, display_name, department, demo_user_key)
  VALUES (@username, @password, @display_name, @department, @demo_user_key)
  ON CONFLICT(username) DO UPDATE SET
    password = excluded.password,
    display_name = excluded.display_name,
    department = excluded.department,
    demo_user_key = excluded.demo_user_key
`)

const demoUsers = [
  { username: 'coco', password: 'password123', display_name: 'Alice Tan', department: 'CPAC - Cityplaza Management Office', demo_user_key: 'coco' },
  { username: 'nam', password: 'password123', display_name: 'Bob Chen', department: 'CPAC - Cityplaza Management Office', demo_user_key: 'nam' },
  { username: 'finance', password: 'password123', display_name: 'Carol Wong', department: 'HFIN - Head Office FIN', demo_user_key: 'finance' },
  { username: 'admin', password: 'password123', display_name: 'Admin Demo', department: 'Digital / IT', demo_user_key: 'admin' },
  { username: 'maggie', password: 'password123', display_name: 'Diana Lau', department: 'PPAC - Pacific Place Management Office', demo_user_key: 'maggie' },
]

for (const user of demoUsers) {
  upsertUser.run(user)
}

const app = express()
app.use(express.json())
app.use(
  '/api',
  rateLimit({
    windowMs: 60 * 1000,
    limit: 60,
    standardHeaders: 'draft-8',
    legacyHeaders: false,
    message: { error: 'Too many requests. Please try again shortly.' },
  }),
)

function readToken(req) {
  const header = req.get('authorization') || ''
  if (!header.startsWith('Bearer ')) return ''
  return header.slice('Bearer '.length).trim()
}

function authenticate(req, res, next) {
  const token = readToken(req)
  if (!token) {
    res.status(401).json({ error: 'Unauthorized' })
    return
  }

  const session = database
    .prepare(
      `
        SELECT
          s.token,
          u.id AS userId,
          u.username,
          u.display_name AS displayName,
          u.department,
          u.demo_user_key AS demoUserKey
        FROM sessions s
        INNER JOIN users u ON u.id = s.user_id
        WHERE s.token = ?
      `,
    )
    .get(token)

  if (!session) {
    res.status(401).json({ error: 'Session expired' })
    return
  }

  req.user = session
  req.sessionToken = token
  next()
}

app.post('/api/login', (req, res) => {
  const username = String(req.body?.username || '').trim()
  const password = String(req.body?.password || '').trim()

  if (!username || !password) {
    res.status(400).json({ error: 'Username and password are required' })
    return
  }

  const user = database
    .prepare(
      `
        SELECT id AS userId, username, display_name AS displayName, department, demo_user_key AS demoUserKey
        FROM users
        WHERE username = ? AND password = ?
      `,
    )
    .get(username, password)

  if (!user) {
    res.status(401).json({ error: 'Invalid username or password' })
    return
  }

  database.prepare('DELETE FROM sessions WHERE user_id = ?').run(user.userId)

  const token = crypto.randomUUID()
  database
    .prepare(
      `
        INSERT INTO sessions (token, user_id, created_at)
        VALUES (?, ?, ?)
      `,
    )
    .run(token, user.userId, new Date().toISOString())

  res.json({
    token,
    user: {
      username: user.username,
      displayName: user.displayName,
      department: user.department,
    },
  })
})

app.get('/api/me', authenticate, (req, res) => {
  res.json({
    user: {
      username: req.user.username,
      displayName: req.user.displayName,
      department: req.user.department,
    },
  })
})

app.post('/api/logout', authenticate, (req, res) => {
  database.prepare('DELETE FROM sessions WHERE token = ?').run(req.sessionToken)
  res.json({ success: true })
})

app.get('/api/chat/history', authenticate, (req, res) => {
  const messages = database
    .prepare(
      `
        SELECT id, role, text, created_at AS createdAt
        FROM messages
        WHERE user_id = ?
        ORDER BY id ASC
      `,
    )
    .all(req.user.userId)

  res.json({ messages })
})

app.post('/api/chat', authenticate, async (req, res) => {
  const text = String(req.body?.message || '').trim()
  if (!text) {
    res.status(400).json({ error: 'Message is required' })
    return
  }

  const now = new Date().toISOString()
  const userInsert = database
    .prepare(
      `
        INSERT INTO messages (user_id, role, text, created_at)
        VALUES (?, 'user', ?, ?)
      `,
    )
    .run(req.user.userId, text, now)

  let replyText = 'Sorry, the AI agent is unavailable right now.'
  try {
    const demoUserKey = req.user.demoUserKey || req.user.username
    const agentResponse = await fetch(`${AGENT_API_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Demo-User': demoUserKey,
      },
      body: JSON.stringify({ message: text }),
    })
    if (agentResponse.ok) {
      const agentData = await agentResponse.json()
      replyText = agentData.answer || replyText
    }
  } catch {
    // Agent API unreachable — fall back to error message
  }

  const replyTime = new Date().toISOString()
  const assistantInsert = database
    .prepare(
      `
        INSERT INTO messages (user_id, role, text, created_at)
        VALUES (?, 'assistant', ?, ?)
      `,
    )
    .run(req.user.userId, replyText, replyTime)

  res.json({
    userMessage: {
      id: userInsert.lastInsertRowid,
      role: 'user',
      text,
      createdAt: now,
    },
    assistantMessage: {
      id: assistantInsert.lastInsertRowid,
      role: 'assistant',
      text: replyText,
      createdAt: replyTime,
    },
  })
})

app.listen(PORT, () => {
  console.log(`Backend listening on http://localhost:${PORT}`)
})
