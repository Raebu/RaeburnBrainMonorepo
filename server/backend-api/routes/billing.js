const BillingService = require('../services/billing-service');

module.exports = async (fastify, opts) => {
fastify.addHook('preHandler', fastify.authenticate);
// Get billing portal session
fastify.get('/portal', async (request, reply) => {
const user = await fastify.prisma.user.findUnique({
where: { id: request.user.id }
});
if (!user.stripeCustomerId) {
return reply.status(400).send({ error: 'No customer found' });
}
const session = await stripe.billingPortal.sessions.create({
customer: user.stripeCustomerId,
return_url: `${process.env.FRONTEND_URL}/dashboard`
});
reply.send({ url: session.url });
});
// Create checkout session
fastify.post('/checkout', async (request, reply) => {
const { planId } = request.body;
const user = request.user;
const session = await stripe.checkout.sessions.create({
mode: 'subscription',
payment_method_types: ['card'],
line_items: [{
price: planId,
quantity: 1
}],
customer_email: user.email,
success_url: `${process.env.FRONTEND_URL}/success?session_id={CHECKOUT_SESSION_ID}`,
cancel_url: `${process.env.FRONTEND_URL}/pricing`,
client_reference_id: user.id
});
reply.send({ sessionId: session.id });
});
};
