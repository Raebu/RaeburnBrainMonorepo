const OpenRouter = require('openrouter');
Object.keys(config.selectors.fields).length > 0;
}

async repairSelectors(html, currentSelectors, error) {
try {
const response = await this.openRouter.chat.completions.create({
model: 'qwen/qwen-3-coder-7b-instruct',
messages: [
{
role: 'system',
content: `You are a DOM analysis expert. Fix CSS selectors that are not working.
Given HTML structure and failed selectors, provide corrected selectors.
Return ONLY valid JSON: {"container": "...", "fields": {...}}`
},
{
role: 'user',
content: `HTML: ${html.substring(0, 2000)}...
Failed selectors: ${JSON.stringify(currentSelectors)}
Error: ${error}`
}
],
temperature: 0.2,
max_tokens: 300
});

return JSON.parse(response.choices[0].message.content);
} catch (error) {
console.error('Selector repair failed:', error.message);
return null;
}
}
}

module.exports = new LLMService();
