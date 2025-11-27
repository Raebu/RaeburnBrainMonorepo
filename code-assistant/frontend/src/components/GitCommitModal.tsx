import React, { useEffect, useState } from 'react';
import { getGitStatus, gitAdd, gitCommit, gitPush } from '../api';

interface Props {
  open: boolean;
  onClose(): void;
}

export default function GitCommitModal({ open, onClose }: Props) {
  const [files, setFiles] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    if (!open) return;
    (async () => {
      try {
        const res = await getGitStatus();
        const fls = res.status.map((s: any) => s.file);
        setFiles(fls);
        setSelected(fls);
      } catch {
        // ignore
      }
    })();
  }, [open]);

  const toggle = (f: string) => {
    setSelected((s) => (s.includes(f) ? s.filter((x) => x !== f) : [...s, f]));
  };

  const commit = async () => {
    if (!msg) return;
    try {
      await gitAdd(selected);
      await gitCommit(msg);
      await gitPush();
      onClose();
    } catch {
      // ignore
    }
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-gray-800 p-4 text-white space-y-2 w-80">
        <h3 className="text-lg">Commit Changes</h3>
        <div className="max-h-40 overflow-auto text-sm">
          {files.map((f) => (
            <label key={f} className="block">
              <input type="checkbox" checked={selected.includes(f)} onChange={() => toggle(f)} /> {f}
            </label>
          ))}
        </div>
        <input className="w-full p-1 text-black" placeholder="Commit message" value={msg} onChange={(e) => setMsg(e.target.value)} />
        <div className="flex justify-end space-x-2">
          <button className="px-2 py-1 bg-gray-600" onClick={onClose}>Cancel</button>
          <button className="px-2 py-1 bg-blue-600" onClick={commit}>Commit</button>
        </div>
      </div>
    </div>
  );
}
