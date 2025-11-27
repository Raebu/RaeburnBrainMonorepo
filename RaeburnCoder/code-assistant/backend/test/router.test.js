import nock from 'nock';
import { routePrompt, getQuota, resetQuota } from '../router.js';

describe('routePrompt', () => {
  afterEach(() => {
    nock.cleanAll();
  });

  test('uses OpenRouter for front-end tasks', async () => {
    const scope = nock('https://openrouter.ai')
      .post('/api/v1/chat/completions')
      .reply(200, {
        choices: [{ message: { content: 'ok' } }],
        usage: { total_tokens: 10 },
      });

    const result = await routePrompt('front-end', 'hello');
    expect(result.content).toBe('ok');
    expect(result.tokens).toBe(10);
    expect(result.model).toBe('codegemma:7b');
    scope.done();
  });

  test('uses HuggingFace for python tasks', async () => {
    const scope = nock('https://api-inference.huggingface.co')
      .post(/\/models\/WizardLM\/WizardCoder-Python-34B-V1.0/) // regex to match path
      .reply(200, { generated_text: 'print(1)' });

    const result = await routePrompt('python', 'hi');
    expect(result.content).toBe('print(1)');
    expect(result.tokens).toBeGreaterThan(0);
    expect(result.model).toMatch(/WizardCoder-Python-34B/);
    scope.done();
  });

  test('tracks token usage in quota', async () => {
    resetQuota();
    const scope = nock('https://openrouter.ai')
      .post('/api/v1/chat/completions')
      .reply(200, {
        choices: [{ message: { content: 'ok' } }],
        usage: { total_tokens: 5 },
      });

    await routePrompt('front-end', 'hello');
    const quota = getQuota();
    expect(quota.used).toBe(5);
    scope.done();
  });
});
