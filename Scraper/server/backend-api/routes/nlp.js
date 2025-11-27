const LLMService = require('../services/llm-service');
const { Queue } = require('bullmq');

module.exports = async (fastify, opts) => {
fastify.addHook('preHandler', fastify.authenticate);
// Natural language scraping request
fastify.post('/nlp/scrape', async (request, reply) => {
const { prompt, domain } = request.body;
const userId = request.user.id;
// Generate configuration using LLM
const config = await LLMService.generateScrapeConfig(prompt, domain);
if (!config) {
return reply.status(400).send({ error: 'Could not generate scraping configuration' });
}
// Add job to queue
const scrapingQueue = new Queue('scraping', {
connection: { host: process.env.REDIS_HOST, port: process.env.REDIS_PORT }
});
const job = await scrapingQueue.add('scrape', {
url: config.url,
selectors: config.selectors,
config: config.config,
userId,
isNLRequest: true,
originalPrompt: prompt
}, {
jobId: `nlp-${Date.now()}-${userId}`,
attempts: 2
});
reply.send({
jobId: job.id,
status: 'queued',
generatedConfig: config
});
});
// Improve selectors based on failed attempts
fastify.post('/nlp/improve', async (request, reply) => {
const { html, selectors, error } = request.body;
const improved = await LLMService.repairSelectors(html, selectors, error);
if (improved) {
reply.send({ improvedSelectors: improved });
} else {
reply.status(400).send({ error: 'Could not improve selectors' });
}
});
};
