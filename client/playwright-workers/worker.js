const { chromium } = require('playwright');
const fs = require('fs').promises;

async function runScrape() {
const url = process.env.TARGET_URL;
const selectors = JSON.parse(process.env.SELECTORS);
const cookies = JSON.parse(process.env.COOKIES);
const userAgent = process.env.USER_AGENT;
const browser = await chromium.launch({
headless: true,
args: [
'--no-sandbox',
'--disable-setuid-sandbox',
'--disable-blink-features=AutomationControlled'
]
});
const context = await browser.newContext({
userAgent,
viewport: { width: 1280, height: 800 }
});
// Set cookies
await context.addCookies(cookies);
// Apply stealth evasions
const stealthBundle = await fs.readFile('./stealth/stealth.bundle.js', 'utf8');
await context.addInitScript(stealthBundle);
const page = await context.newPage();
try {
await page.goto(url, { waitUntil: 'networkidle' });
// Wait for content
await page.waitForTimeout(3000);
// Extract data based on selectors
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
process.exit(1);
} finally {
await browser.close();
}
}

runScrape().catch(console.error);
