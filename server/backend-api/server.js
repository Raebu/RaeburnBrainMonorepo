const fastify = require('fastify')({ logger: true });
const cors = require('@fastify/cors');
const jwt = require('@fastify/jwt');
const rateLimit = require('@fastify/rate-limit');
const Redis = require('ioredis');
const { PrismaClient } = require('@prisma/client');

// Initialize services
const redis = new Redis(process.env.REDIS_URL);
const prisma = new PrismaClient();

// Register plugins
fastify.register(cors, { origin: process.env.FRONTEND_URL });
fastify.register(jwt, { secret: process.env.JWT_SECRET });
fastify.register(rateLimit, { redis });

// Authentication middleware
fastify.decorate("authenticate", async (request, reply) => {
try {
await request.jwtVerify();
} catch (err) {
reply.send(err);
}
});

// Routes
fastify.register(require('./routes/auth'), { prefix: '/api/auth' });
fastify.register(require('./routes/scraping'), { prefix: '/api/scraping' });
fastify.register(require('./routes/users'), { prefix: '/api/users' });

// Start server
const start = async () => {
try {
await fastify.listen({ port: 3001, host: '0.0.0.0' });
} catch (err) {
fastify.log.error(err);
process.exit(1);
}
};

start();
