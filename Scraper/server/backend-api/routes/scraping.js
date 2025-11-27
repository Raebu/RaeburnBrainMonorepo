const { Queue } = require('bullmq');
userId,
config: JSON.stringify(config)
}
});
reply.send({ jobId: job.id, status: 'queued' });
});
// Get job status
fastify.get('/jobs/:jobId', async (request, reply) => {
const { jobId } = request.params;
const userId = request.user.id;
const job = await prisma.scrapeJob.findUnique({
where: { id: jobId, userId }
});
if (!job) {
return reply.status(404).send({ error: 'Job not found' });
}
reply.send(job);
});
// Get user jobs
fastify.get('/jobs', async (request, reply) => {
const userId = request.user.id;
const { page = 1, limit = 20 } = request.query;
const jobs = await prisma.scrapeJob.findMany({
where: { userId },
orderBy: { createdAt: 'desc' },
skip: (page - 1) * limit,
take: limit
});
reply.send(jobs);
});
// Get results
fastify.get('/results/:jobId', async (request, reply) => {
const { jobId } = request.params;
const userId = request.user.id;
const job = await prisma.scrapeJob.findUnique({
where: { id: jobId, userId }
});
if (!job || !job.resultUrl) {
return reply.status(404).send({ error: 'Results not available' });
}
// Redirect to result file
reply.redirect(job.resultUrl);
});
};
