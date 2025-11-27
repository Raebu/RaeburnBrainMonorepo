const { PrismaClient } = require('@prisma/client');
const WebSocket = require('ws');

class CaptchaNotifier {
constructor() {
this.prisma = new PrismaClient();
this.clients = new Map(); // userId -> WebSocket connections
}
async notifyUser(userId, jobId, captchaInfo) {
// Update job status
await this.prisma.scrapeJob.update({
where: { id: jobId },
data: {
status: 'waiting_for_captcha',
metadata: JSON.stringify({ captcha: captchaInfo })
}
});
// Send notification to user (WebSocket, email, etc.)
const userConnections = this.clients.get(userId);
if (userConnections) {
userConnections.forEach(ws => {
if (ws.readyState === WebSocket.OPEN) {
ws.send(JSON.stringify({
type: 'captcha_required',
jobId,
captchaInfo
}));
}
});
}
// Send email notification
// await this.sendEmailNotification(userId, jobId);
}
registerWebSocket(userId, ws) {
if (!this.clients.has(userId)) {
this.clients.set(userId, new Set());
}
this.clients.get(userId).add(ws);
ws.on('close', () => {
const userConnections = this.clients.get(userId);
if (userConnections) {
userConnections.delete(ws);
if (userConnections.size === 0) {
this.clients.delete(userId);
}
}
});
}
}

module.exports = new CaptchaNotifier();
