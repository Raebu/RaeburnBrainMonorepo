import React, { useState, useEffect } from 'react';
import CodeEditor from './components/Editor';
import PromptPanel from './components/PromptPanel';
import QuotaBar from './components/QuotaBar';
import FileTree from './components/FileTree';
import GitCommitModal from './components/GitCommitModal';
import { readFile, saveFile, saveFullSession, loadFullSession } from './api';
import Login from "./components/Login"; 

function detectLanguage(path: string) {
  if (path.endsWith('.ts') || path.endsWith('.tsx')) return 'typescript';
  if (path.endsWith('.js') || path.endsWith('.jsx')) return 'javascript';
  if (path.endsWith('.py')) return 'python';
  if (path.endsWith('.json')) return 'json';
  if (path.endsWith('.md')) return 'markdown';
  return 'plaintext';
}

interface Tab {
  path: string;
  code: string;
  saved: string;
  language: string;
  scroll: number;
}

export default function App() {
  const [tabs, setTabs] = useState<Tab[]>([]);
  const [active, setActive] = useState('');
  const [history, setHistory] = useState<any[]>([]);
  const [role, setRole] = useState('');
  const [commitOpen, setCommitOpen] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // check for token
  const token = sessionStorage.getItem("token");

  if (!token) {
    return <Login />;
  }

  const openFile = async (p: string) => {
    const existing = tabs.find((t) => t.path === p);
    if (existing) {
      setActive(p);
      return;
    }
    try {
      const res = await readFile(p);
      const lang = detectLanguage(p);
      setTabs((t) => [...t, { path: p, code: res.content, saved: res.content, language: lang, scroll: 0 }]);
      setActive(p);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    openFile('README.md');
  }, []);

  const updateCode = (p: string, val: string) => {
    setTabs((t) => t.map((tab) => (tab.path === p ? { ...tab, code: val } : tab)));
  };

  const updateScroll = (p: string, pos: number) => {
    setTabs((t) => t.map((tab) => (tab.path === p ? { ...tab, scroll: pos } : tab)));
  };

  const closeTab = (p: string) => {
    const tab = tabs.find((t) => t.path === p);
    if (!tab) return;
    if (tab.code !== tab.saved && !window.confirm('Discard changes?')) return;
    setTabs((t) => t.filter((tb) => tb.path !== p));
    if (active === p) {
      const idx = tabs.findIndex((tb) => tb.path === p);
      const next = tabs[idx - 1] || tabs[idx + 1];
      setActive(next?.path || '');
    }
  };

  const activeTab = tabs.find((t) => t.path === active);

  useEffect(() => {
    if (!activeTab) return;
    const id = setTimeout(() => {
      if (activeTab.code !== activeTab.saved) {
        saveFile(activeTab.path, activeTab.code);
        setTabs((t) =>
          t.map((tb) => (tb.path === activeTab.path ? { ...tb, saved: activeTab.code } : tb)),
        );
      }
    }, 3000);
    return () => clearTimeout(id);
  }, [activeTab?.code, activeTab?.path]);

  const handleSaveSession = async () => {
    const name = window.prompt('Session name');
    if (!name) return;
    const tabsData = tabs.map((t) => ({ path: t.path, code: t.code, scroll: t.scroll }));
    await saveFullSession(name, { history, role, tabs: tabsData, active });
  };

  const handleLoadSession = async () => {
    const name = window.prompt('Session name to load');
    if (!name) return;
    const res = await loadFullSession(name);
    const loadedTabs: Tab[] = (res.data.tabs || []).map((t: any) => ({
      path: t.path,
      code: t.code,
      saved: t.code,
      language: detectLanguage(t.path),
      scroll: t.scroll || 0,
    }));
    setTabs(loadedTabs);
    setActive(res.data.active || '');
    setHistory(res.data.history || []);
    setRole(res.data.role || '');
  };

  return (
    <div className="h-full flex flex-col">
      <header className="p-2 bg-gray-800 text-white space-y-1">
        <div>Code Assistant</div>
        <QuotaBar />
      </header>
      <div className="flex flex-1">
        <div className="w-60 border-r border-gray-700 bg-gray-800 text-white flex flex-col">
          <button className="m-2 px-2 py-1 bg-gray-700 rounded" onClick={() => setCommitOpen(true)}>
            Commit
          </button>
          <div className="flex-1 overflow-auto">
            <FileTree onOpen={openFile} />
          </div>
        </div>
        <div className="flex-1 flex flex-col">
          <div className="flex bg-gray-900 text-white border-b border-gray-700 overflow-x-auto">
            {tabs.map((t) => (
              <div
                key={t.path}
                className={`px-2 py-1 cursor-pointer flex items-center space-x-1 ${active === t.path ? 'bg-gray-800' : ''}`}
                onClick={() => setActive(t.path)}
              >
                <span>{t.path}</span>
                {t.code !== t.saved && <span className="text-yellow-400">*</span>}
                <button className="ml-1" onClick={(e) => { e.stopPropagation(); closeTab(t.path); }}>x</button>
              </div>
            ))}
          </div>
          {activeTab && (
            <CodeEditor
              language={activeTab.language}
              value={activeTab.code}
              onChange={(val) => updateCode(activeTab.path, val)}
              path={activeTab.path}
              scroll={activeTab.scroll}
              onScroll={(pos) => updateScroll(activeTab.path, pos)}
            />
          )}
        </div>
      </div>
      <PromptPanel
        getCode={() => activeTab?.code || ''}
        role={role}
        setRole={setRole}
        history={history}
        setHistory={setHistory}
        onSave={handleSaveSession}
        onLoad={handleLoadSession}
      />
      <GitCommitModal open={commitOpen} onClose={() => setCommitOpen(false)} />
    </div>
  );
}
