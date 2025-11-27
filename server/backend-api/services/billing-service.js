const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const { PrismaClient } = require('@prisma/client');

class BillingService {
constructor() {
this.prisma = new PrismaClient();
}
async createCustomer(user) {
const customer = await stripe.customers.create({
email: user.email,
name: user.name,
metadata: { userId: user.id }
});
await this.prisma.user.update({
where: { id: user.id },
data: { stripeCustomerId: customer.id }
});
return customer;
}
async createSubscription(user, planId) {
const customer = await this.getOrCreateCustomer(user);
const subscription = await stripe.subscriptions.create({
customer: customer.id,
items: [{ price: planId }],
payment_behavior: 'default_incomplete',
payment_settings: {
save_default_payment_method: 'on_subscription'
},
expand: ['latest_invoice.payment_intent']
});
return subscription;
}
async getOrCreateCustomer(user) {
if (user.stripeCustomerId) {
return await stripe.customers.retrieve(user.stripeCustomerId);
}
return await this.createCustomer(user);
}
async recordUsage(userId, usageType, quantity) {
// Record usage for metered billing
const user = await this.prisma.user.findUnique({ where: { id: userId } });
if (!user.stripeCustomerId) return;
// Get active subscription
const subscriptions = await stripe.subscriptions.list({
customer: user.stripeCustomerId,
status: 'active'
});
if (subscriptions.data.length === 0) return;
const subscription = subscriptions.data[0];
const subscriptionItem = subscription.items.data.find(
item => item.price.lookup_key === `${usageType}_metered`
);
if (subscriptionItem) {
await stripe.subscriptionItems.createUsageRecord(
subscriptionItem.id,
{
quantity: quantity,
timestamp: 'now',
action: 'increment'
}
);
}
}
async setupWebhooks() {
// Handle Stripe webhooks for subscription events
// Implementation would go here
}
}

module.exports = new BillingService();
