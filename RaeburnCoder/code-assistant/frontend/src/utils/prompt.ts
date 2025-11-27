export function buildPrompt(action: string, code: string): { task: string; prompt: string } {
  const task = detectTask(code);
  const instructions: Record<string, string> = {
    fix: 'Fix the following code',
    explain: 'Explain the following code',
    refactor: 'Refactor the following code',
    tests: 'Write unit tests for the following code',
    improve: 'Improve the performance of the following code',
    docs: 'Add documentation to the following code',
  };
  const prefix = instructions[action] || 'Process the following code';
  return { task, prompt: `${prefix}:\n${code}` };
}

export function detectTask(code: string): string {
  if (/pragma solidity/.test(code)) return 'blockchain';
  if (/^\s*import .* from 'react'/.test(code)) return 'front-end';
  if (/\bdef\b/.test(code)) return 'python';
  return 'full-stack';
}
