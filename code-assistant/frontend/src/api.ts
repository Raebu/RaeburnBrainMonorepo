import axios from 'axios';
import { buildPrompt } from './utils/prompt';

export const api = axios.create();

export async function login(username: string, password: string) {
  const res = await api.post('/api/login', { username, password });
  return res.data;
}

export async function performInlineAction(action: string, code: string) {
  const { task, prompt } = buildPrompt(action, code);
  const res = await axios.post('/api/complete', { task, prompt });
  return res.data;
}

export async function completePrompt(task: string, prompt: string, messages: any[] = []) {
  const res = await axios.post('/api/complete', { task, prompt, messages });
  return res.data;
}

export async function saveSession(name: string, history: any[]) {
  const res = await axios.post('/api/session/save', { name, history });
  return res.data;
}

export async function loadSession(name: string) {
  const res = await axios.get('/api/session/load', { params: { name } });
  return res.data;
}

export async function saveFullSession(name: string, data: any) {
  const res = await axios.post('/api/session/fullsave', { name, data });
  return res.data;
}

export async function loadFullSession(name: string) {
  const res = await axios.get('/api/session/fullload', { params: { name } });
  return res.data;
}

export async function listSessions() {
  const res = await axios.get('/api/session/list');
  return res.data;
}

export async function exportProject() {
  const res = await axios.get('/api/export', { responseType: 'blob' });
  return res.data as Blob;
}

export async function getQuota() {
  const res = await axios.get('/api/quota');
  return res.data;
}

export async function listFiles(path = '.') {
  const res = await axios.get('/api/files', { params: { path } });
  return res.data;
}

export async function readFile(path: string) {
  const res = await axios.get('/api/file', { params: { path } });
  return res.data;
}

export async function saveFile(path: string, content: string) {
  const res = await axios.post('/api/file', { path, content });
  return res.data;
}

export async function getGitStatus() {
  const res = await axios.get('/api/git-status');
  return res.data;
}

export async function gitAdd(files: string[]) {
  const res = await axios.post('/api/git-add', { files });
  return res.data;
}

export async function gitCommit(message: string) {
  const res = await axios.post('/api/git-commit', { message });
  return res.data;
}

export async function gitPush() {
  const res = await axios.post('/api/git-push');
  return res.data;
}
