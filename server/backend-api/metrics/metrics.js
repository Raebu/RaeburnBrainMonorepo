const client = require('prom-client');
const collectDefaultMetrics = client.collectDefaultMetrics;

// Collect default metrics
collectDefaultMetrics({ timeout: 5000 });

// Custom metrics
const jobDuration = new client.Histogram({
name: 'scrapebot_job_duration_seconds',
help: 'Duration of scraping jobs in seconds',
labelNames: ['status', 'region']
});

const activeWorkers = new client.Gauge({
name: 'scrapebot_active_workers',
help: 'Number of currently active workers',
labelNames: ['region']
});

const jobsProcessed = new client.Counter({
name: 'scrapebot_jobs_processed_total',
help: 'Total number of jobs processed',
labelNames: ['status', 'region']
});

const dataRowsExtracted = new client.Counter({
name: 'scrapebot_data_rows_extracted_total',
help: 'Total number of data rows extracted',
labelNames: ['domain']
});

module.exports = {
jobDuration,
activeWorkers,
jobsProcessed,
dataRowsExtracted,
register: client.register
};
