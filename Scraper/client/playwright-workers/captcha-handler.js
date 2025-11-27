class CaptchaHandler {
});
}
// Check for Cloudflare challenges
if (node.innerHTML?.includes('Checking your browser')) {
window.onCaptchaDetected({
type: 'cloudflare',
element: 'div',
content: 'browser_check'
});
}
}
}
}
}
});
observer.observe(document.body, {
childList: true,
subtree: true
});
});
}
async waitForHumanSolution(timeout = 300000) { // 5 minutes
const startTime = Date.now();
while (Date.now() - startTime < timeout) {
// Check if CAPTCHA is still present
const recaptchaPresent = await this.page.$('iframe[src*="recaptcha"]');
const hcaptchaPresent = await this.page.$('.hcaptcha');
if (!recaptchaPresent && !hcaptchaPresent) {
// CAPTCHA solved
this.captchaDetected = false;
return true;
}
// Wait before checking again
await this.page.waitForTimeout(5000);
}
throw new Error('CAPTCHA not solved within timeout');
}
async handleCaptcha(jobId) {
// Pause automation and wait for human intervention
console.log(`CAPTCHA detected for job ${jobId}. Waiting for human solution...`);
// In a real implementation, this would:
// 1. Notify the backend API
// 2. Pause the job
// 3. Provide a way for user to solve CAPTCHA
// 4. Resume when solved
try {
await this.waitForHumanSolution();
console.log('CAPTCHA solved, resuming automation');
return true;
} catch (error) {
console.error('CAPTCHA timeout:', error.message);
throw error;
}
}
}

module.exports = CaptchaHandler;
