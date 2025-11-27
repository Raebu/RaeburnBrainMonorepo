import express from 'express';
import bodyParser from 'body-parser';
import cors from 'cors';
import jwt from 'jsonwebtoken';
import dotenv from 'dotenv';
import path from 'path';
import fs from 'fs-extra';
import archiver from 'archiver';
import { routePrompt, getQuota } from './router.js';
import authMiddleware from './auth.js';
import {
  listDir,
  readFile,
  writeFile,
  createDir,
  renamePath,
  deletePath,
  gitStatus,
  gitAdd,
  gitCommit,
  gitPush,
} from './fsController.js';
import router from './router.js';

dotenv.config();

const app = express();
const port = process.env.PORT || 3001;
app.use(express.json());

const SESSION_DIR = path.join(process.cwd(), 'sessions');
fs.ensureDirSync(SESSION_DIR);

// ✅ SINGLE secure login route
app.post('/api/login', (req, res) => {
  const { username, password } = req.body;
  if (
    username === process.env.AUTH_USER &&
    password === process.env.AUTH_PASS
  ) {
    const token = jwt.sign(
      { user: username },
      process.env.AUTH_SECRET,
      { expiresIn: '15m' }
    );
    return res.json({ token });
  } else {
    return res.status(401).json({ message: 'Invalid credentials' });
  }
});

app.use(bodyParser.json());
app.use(cors());


// secure routes after login
app.use(authMiddleware);


// main router
app.use('/api', router);
app.use('/api/fs', fsController);
// routes are defined directly without extra routers

// default
app.get('/', (req, res) => {
  res.send('AI Code Assistant Backend Running');
});

app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});

app.post('/api/complete', async (req, res) => {
  const { task, prompt, messages = [] } = req.body;
  if (!task || !prompt) {
    res.status(400).json({ error: 'task and prompt are required' });
    return;
  }
  try {
    const result = await routePrompt(task, prompt, messages);
    res.json({ result });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/files', async (req, res) => {
  try {
    const result = await listDir(req.query.path || '.');
    res.json({ files: result });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/file', async (req, res) => {