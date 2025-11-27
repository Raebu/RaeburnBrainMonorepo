import { describe, it, expect } from 'vitest';
import { buildPrompt } from '../prompt';

describe('buildPrompt', () => {
  it('creates fix prompt', () => {
    const { task, prompt } = buildPrompt('fix', 'function x() {}');
    expect(task).toBe('front-end');
    expect(prompt).toContain('Fix the following code');
  });

  it('creates docs prompt', () => {
    const { task, prompt } = buildPrompt('docs', 'def x(): pass');
    expect(task).toBe('python');
    expect(prompt).toContain('Add documentation');
  });
});
