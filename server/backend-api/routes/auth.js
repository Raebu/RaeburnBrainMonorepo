const { PrismaClient } = require('@prisma/client');
const bcrypt = require('bcrypt');
const { v4: uuidv4 } = require('uuid');

const prisma = new PrismaClient();

module.exports = async (fastify, opts) => {
// Email signup
fastify.post('/signup', async (request, reply) => {
const { email, password, name } = request.body;
// Check if user exists
const existingUser = await prisma.user.findUnique({ where: { email } });
if (existingUser) {
return reply.status(400).send({ error: 'User already exists' });
}
// Hash password
const hashedPassword = await bcrypt.hash(password, 10);
// Create user
const user = await prisma.user.create({
data: {
id: uuidv4(),
email,
password: hashedPassword,
name,
quota: { create: { dailyLimit: 10, usedToday: 0 } }
}
});
// Generate JWT
const token = fastify.jwt.sign({ id: user.id });
reply.send({ token, user: { id: user.id, email: user.email, name: user.name } });
});
// Login
fastify.post('/login', async (request, reply) => {
const { email, password } = request.body;
const user = await prisma.user.findUnique({
where: { email },
include: { quota: true }
});
if (!user || !await bcrypt.compare(password, user.password)) {
return reply.status(401).send({ error: 'Invalid credentials' });
}
const token = fastify.jwt.sign({ id: user.id });
reply.send({ token, user: {
id: user.id,
email: user.email,
name: user.name,
quota: user.quota
}});
});
// Google OAuth (simplified)
fastify.get('/google/callback', async (request, reply) => {
// Implementation for Google OAuth flow
// Would use passport-google-oauth20 or similar
});
};
