import React from 'react';
import { performInlineAction } from '../api';

interface Props {
  getCode(): string;
  onResult(res: string): void;
}

const actions = [
  { key: 'fix', label: 'Fix code' },
  { key: 'explain', label: 'Explain' },
  { key: 'refactor', label: 'Refactor' },
  { key: 'tests', label: 'Generate tests' },
];

export default function InlineActions({ getCode, onResult }: Props) {
  const handle = async (key: string) => {
    const code = getCode();
    if (!code) return;
    try {
      const { result } = await performInlineAction(key, code);
      onResult(result.content);
    } catch (err) {
      onResult(String(err));
    }
  };

  return (
    <div className="absolute top-2 right-2 space-x-2 z-10">
      {actions.map((a) => (
        <button
          key={a.key}
          onClick={() => handle(a.key)}
          className="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
        >
          {a.label}
        </button>
      ))}
    </div>
  );
}
