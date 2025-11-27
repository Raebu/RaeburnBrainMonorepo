import React, { useEffect, useState } from 'react';
import { listFiles } from '../api';

interface Entry {
  name: string;
  path: string;
  type: 'file' | 'dir';
}

interface Props {
  onOpen(path: string): void;
}

export default function FileTree({ onOpen }: Props) {
  const [nodes, setNodes] = useState<Record<string, Entry[]>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    loadDir('.');
  }, []);

  async function loadDir(dir: string) {
    if (nodes[dir]) return;
    const res = await listFiles(dir);
    setNodes((n) => ({ ...n, [dir]: res.files }));
  }

  async function toggle(dir: string) {
    const open = !expanded[dir];
    setExpanded((e) => ({ ...e, [dir]: open }));
    if (open) await loadDir(dir);
  }

  function renderDir(dir: string, level: number): JSX.Element[] {
    const entries = nodes[dir] || [];
    return entries.map((e) => (
      <div key={e.path} style={{ paddingLeft: level * 12 }}>
        {e.type === 'dir' ? (
          <div
            className="cursor-pointer select-none"
            onClick={() => toggle(e.path)}
          >
            {expanded[e.path] ? '📂' : '📁'} {e.name}
          </div>
        ) : (
          <div
            className="cursor-pointer hover:bg-gray-700"
            onDoubleClick={() => onOpen(e.path)}
          >
            📄 {e.name}
          </div>
        )}
        {e.type === 'dir' && expanded[e.path] && renderDir(e.path, level + 1)}
      </div>
    ));
  }

  return <div className="overflow-auto text-sm p-2">{renderDir('.', 0)}</div>;
}
