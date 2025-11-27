import React, { useState } from 'react';
import { completePrompt, exportProject } from '../api';
import { buildPrompt, detectTask } from '../utils/prompt';

const roles = [
  { label: 'Default', value: '' },
  { label: 'Rust expert', value: 'You are a Rust expert.' },
  { label: 'Python guru', value: 'You are a Python guru.' },
  { label: 'Frontend specialist', value: 'You are a Front-end specialist.' },
];

const tools = [
  { key: 'explain', label: 'Explain this file' },
  { key: 'improve', label: 'Improve performance' },
  { key: 'docs', label: 'Add docs' },
  { key: 'tests', label: 'Write unit tests' },
];

interface Props {
  getCode(): string;
  role: string;
  setRole(role: string): void;
  history: any[];
  setHistory(h: any[]): void;
  onSave(): void;
  onLoad(): void;
}

export default function PromptPanel({ getCode, role, setRole, history, setHistory, onSave, onLoad }: Props) {
  const [input, setInput] = useState('');

  const append = (entry: any) => setHistory((h) => [...h, entry]);

  const send = async (prompt: string) => {
    const code = getCode();
    const task = detectTask(code);
    const res = await completePrompt(task, prompt, [
      ...(role ? [{ role: 'system', content: role }] : []),
      ...history,
    ]);
    append({ role: 'user', content: prompt });
    append({ role: 'assistant', content: res.result.content, model: res.result.model, tokens: res.result.tokens });
    setInput('');
  };

  const runTool = async (key: string) => {
    const code = getCode();
    const { prompt } = buildPrompt(key, code);
    await send(prompt);
  };

  const handleSave = async () => {
    onSave();
  };

  const handleLoad = async () => {
    onLoad();
  };

  const handleExport = async () => {
    const blob = await exportProject();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'project.zip';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-2 border-t border-gray-700 text-sm space-y-2">
      <div className="flex items-center space-x-2">
        <select className="bg-gray-800 text-white p-1" value={role} onChange={(e) => setRole(e.target.value)}>
          {roles.map((r) => (
            <option key={r.label} value={r.value}>{r.label}</option>
          ))}
        </select>
        {tools.map((t) => (
          <button
            key={t.key}
            onClick={() => runTool(t.key)}
            className="px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            {t.label}
          </button>
        ))}
        <button className="px-2 py-1 bg-gray-600 text-white rounded" onClick={handleSave}>Save</button>
        <button className="px-2 py-1 bg-gray-600 text-white rounded" onClick={handleLoad}>Load</button>
        <button className="px-2 py-1 bg-gray-600 text-white rounded" onClick={handleExport}>Export</button>
      </div>
      <div className="h-40 overflow-auto bg-gray-900 text-gray-100 p-2 space-y-1">
        {history.map((m, i) => (
          <div key={i} className="whitespace-pre-wrap">
            <strong>{m.role}:</strong> {m.content}
            {m.model && (
              <span className="ml-2 text-xs text-gray-400">[{m.model} | {m.tokens} tokens]</span>
            )}
          </div>
        ))}
      </div>
      <div className="flex">
        <input
          className="flex-1 bg-gray-800 text-white p-2 mr-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send(input)}
          placeholder="Ask the assistant..."
        />
        <button className="px-3 py-1 bg-green-600 text-white rounded" onClick={() => send(input)}>
          Send
        </button>
      </div>
    </div>
  );
}
