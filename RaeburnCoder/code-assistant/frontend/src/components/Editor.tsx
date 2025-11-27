import React, { useRef, useState } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import InlineActions from './InlineActions';

interface Props {
  language: string;
  path: string;
  value: string;
  onChange?(val: string): void;
  scroll?: number;
  onScroll?(pos: number): void;
}

export default function CodeEditor({ language, value, onChange, path, scroll = 0, onScroll }: Props) {
  const editorRef = useRef<import('monaco-editor').editor.IStandaloneCodeEditor | null>(null);
  const [result, setResult] = useState('');

  const handleMount: OnMount = (editor) => {
    editorRef.current = editor;
    editor.setScrollTop(scroll);
    editor.onDidScrollChange(() => {
      onScroll && onScroll(editor.getScrollTop());
    });
  };

  const getSelection = () => {
    const editor = editorRef.current;
    if (!editor) return '';
    const sel = editor.getSelection();
    if (!sel) return '';
    return editor.getModel()?.getValueInRange(sel) || '';
  };

  return (
    <div className="h-full relative">
      <Editor
        key={path}
        height="100%"
        language={language}
        value={value}
        theme="vs-dark"
        onMount={handleMount}
        onChange={(v) => onChange && onChange(v || '')}
        options={{ minimap: { enabled: false }, fontSize: 14 }}
      />
      <InlineActions getCode={getSelection} onResult={setResult} />
      {result && (
        <pre className="absolute bottom-0 left-0 right-0 max-h-40 overflow-auto bg-gray-900 text-green-300 p-2 text-sm">
          {result}
        </pre>
      )}
    </div>
  );
}
