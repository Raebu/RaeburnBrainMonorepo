const { Worker } = require('bullmq');
const { PrismaClient } = require('@prisma/client');
const Redis = require('ioredis');

class RegionAwareWorker {
constructor(region) {
this.region = region;
this.redis = new Redis(process.env.REDIS_URL);
this.prisma = new PrismaClient();
this.worker = new Worker('scraping', this.processJob.bind(this), {
connection: this.redis,
concurrency: 5
});
// Only process jobs that should run in this region
this.worker.on('active', async (job) => {
if (job.data.preferredRegion && job.data.preferredRegion !== this.region) {
// Re-queue for the correct region
await job.moveToDelayed(Date.now() + 5000);
return false;
}
return true;
});
}
async processJob(job) {
const { url, selectors, config, userId } = job.data;
// Add region metadata to job
await this.prisma.scrapeJob.update({
where: { id: job.id },
data: {
metadata: JSON.stringify({
region: this.region,
workerId: process.env.HOSTNAME
})
}
});
// Process job normally (existing logic)
// ... [existing scraping logic]
}
}

// Start worker for this region
const region = process.env.REGION || 'us-east-1';
new RegionAwareWorker(region);
