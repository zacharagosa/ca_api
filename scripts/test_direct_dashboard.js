const puppeteer = require('puppeteer-core');

(async () => {
  console.log('Testing direct embed of Dashboard 117 (with vis_config and domcontentloaded)...');
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  page.on('console', msg => console.log(`[BROWSER CONSOLE ${msg.type()}]:`, msg.text()));

  // Fetch signed SSO URL for dashboard 117
  const res = await fetch('http://localhost:8080/api/embed', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_url: '/embed/dashboards/117', user_id: 'embed_guest_user' })
  });
  const data = await res.json();
  console.log('Signed SSO URL for Dashboard 117:', data.url);

  console.log('Navigating to signed SSO URL in Chrome...');
  await page.goto(data.url, { waitUntil: 'domcontentloaded', timeout: 30000 });

  console.log('Waiting 15 seconds for Looker charts to render...');
  await new Promise(r => setTimeout(r, 15000));

  await page.screenshot({ path: '/tmp/dashboard_117_rendered.png' });
  console.log('Screenshot saved to /tmp/dashboard_117_rendered.png');

  await browser.close();
  console.log('Test complete.');
})();
