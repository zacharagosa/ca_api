const puppeteer = require('puppeteer-core');

(async () => {
  console.log('Inspecting Looker dashboard rendering with extended wait...');
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  page.on('console', msg => console.log(`[BROWSER CONSOLE]:`, msg.text()));

  // Fetch signed SSO URL for dashboard 116
  const res = await fetch('http://localhost:8080/api/embed', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_url: '/embed/dashboards/116', user_id: 'embed_guest_user' })
  });
  const data = await res.json();
  console.log('Signed URL fetched. Loading in browser...');

  await page.goto(data.url, { waitUntil: 'networkidle2', timeout: 30000 });
  
  console.log('Waiting 20 seconds for complete rendering...');
  await new Promise(r => setTimeout(r, 20000));

  await page.screenshot({ path: '/tmp/dash116_rendered_20s.png' });
  console.log('Saved /tmp/dash116_rendered_20s.png');

  await browser.close();
})();
