const { chromium } = require('playwright');
resolve();
}
}, 5000);
});
}
// Continue with scraping
await page.waitForTimeout(3000);
const results = [];
const elements = await page.$$(selectors.container);
for (const element of elements) {
const item = {};
for (const [key, selector] of Object.entries(selectors.fields)) {
try {
item[key] = await element.$eval(selector, el => el.textContent.trim());
} catch (e) {
item[key] = null;
}
}
results.push(item);
}
console.log(JSON.stringify(results));
} catch (error) {
console.error('Scraping failed:', error.message);
// Handle CAPTCHA-specific errors
if (error.message.includes('CAPTCHA')) {
if (process.send) {
process.send({
type: 'captcha_error',
jobId,
error: error.message
});
}
}
process.exit(1);
} finally {
await browser.close();
}
}

// Handle messages from parent process
process.on('message', async (message) => {
if (message.type === 'captcha_solved') {
// Resume scraping after CAPTCHA is solved
console.log('Received CAPTCHA solved notification');
}
});

runEnhancedScrape().catch(console.error);
