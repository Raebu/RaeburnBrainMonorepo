import fetch from 'node-fetch';
import dotenv from 'dotenv';

dotenv.config();

let tokensUsed = 0;

/**
 * Determine which model to use based on task type.
 */
const MODEL_MAP = {
  'front-end': { provider: 'openrouter', model: 'codegemma:7b' },
  'back-end': { provider: 'huggingface', model: 'bigcode/starcoder2-15b' },
  'full-stack': { provider: 'openrouter', model: 'deepseek-coder:33b' },
  'mobile': { provider: 'openrouter', model: 'deepseek-coder:33b' },
  'python': { provider: 'huggingface', model: 'WizardLM/WizardCoder-Python-34B-V1.0' },
  'blockchain': { provider: 'huggingface', model: 'bigcode/starcoder2-15b' },
  'testing': { provider: 'huggingface', model: 'WizardLM/WizardCoder-Python-34B-V1.0' },
};

const DEFAULT_MODEL = { provider: 'openrouter', model: 'codellama' };

/**
 * Estimate tokens using simple word count approximation.
 * @param {string} text
 */
function estimateTokens(text) {
  return Math.ceil(text.split(/\s+/).length * 1.5);
}

export function getQuota() {
  const limit = Number(process.env.QUOTA_LIMIT) || Infinity;
  return { used: tokensUsed, limit };
}

export function resetQuota() {
  tokensUsed = 0;
}

/**
 * Perform an HTTP request with retries on 429 and network errors.
 * @param {string} url
 * @param {object} options
 */
async function fetchWithRetry(url, options, retries = 3) {
  for (let i = 0; i <= retries; i += 1) {
    try {
      const res = await fetch(url, options);
      if (res.status !== 429 && res.status < 500) {
        return res;
      }
      if (i === retries) throw new Error(`Request failed with status ${res.status}`);
    } catch (err) {
      if (i === retries) throw err;
    }
    await new Promise((r) => setTimeout(r, (i + 1) * 1000));
  }
}

/**
 * Call OpenRouter chat completion API.
 */
async function callOpenRouter(model, messages) {
  const url = 'https://openrouter.ai/api/v1/chat/completions';
  const apiKey = process.env.OPENROUTER_API_KEY;
  const body = {
    model,
    messages,
  };
  const res = await fetchWithRetry(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  const tokens = data.usage.total_tokens;
  tokensUsed += tokens;
  return { content: data.choices[0].message.content, tokens };
}

/**
 * Call HuggingFace inference API.
 */
async function callHuggingFace(model, prompt) {
  const url = `https://api-inference.huggingface.co/models/${model}`;
  const apiKey = process.env.HUGGINGFACE_API_KEY;
  const res = await fetchWithRetry(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({ inputs: prompt }),
  });
  const data = await res.json();
  const text = Array.isArray(data) ? data[0].generated_text : data.generated_text;
  const tokens = estimateTokens(text);
  tokensUsed += tokens;
  return { content: text, tokens };
}

/**
 * Main entry for routing a prompt to the appropriate model.
 * @param {string} task
 * @param {string} prompt
 * @param {Array} [messages]
 */
export async function routePrompt(task, prompt, messages = []) {
  const mapping = MODEL_MAP[task] || DEFAULT_MODEL;
  if (mapping.provider === 'openrouter') {
    const fullMessages = [
      { role: 'system', content: 'You are a senior developer assistant.' },
      ...messages,
      { role: 'user', content: prompt },
    ];
    const res = await callOpenRouter(mapping.model, fullMessages);
    return { ...res, model: mapping.model };
  }
  if (mapping.provider === 'huggingface') {
    const res = await callHuggingFace(mapping.model, prompt);
    return { ...res, model: mapping.model };
  }
  throw new Error('Unsupported provider');
}

export default { routePrompt, getQuota, resetQuota };
