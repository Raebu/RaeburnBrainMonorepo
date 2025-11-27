const { Worker, QueueEvents } = require('bullmq');
data: {
status: 'completed',
completedAt: new Date(),
resultUrl: uploadResult.Location
}
});
// Cleanup container
exec(`docker rm ${containerId}`, () => {});
return result;
} catch (error) {
// Update job with error
await prisma.scrapeJob.update({
where: { id: job.id },
data: {
status: 'failed',
error: error.message,
completedAt: new Date()
}
});
throw error;
}
}, { connection: redis });

// Handle worker events
worker.on('completed', job => {
console.log(`Job ${job.id} completed`);
});

worker.on('failed', (job, err) => {
console.log(`Job ${job.id} failed:`, err.message);
});

console.log('Scraping worker started');
