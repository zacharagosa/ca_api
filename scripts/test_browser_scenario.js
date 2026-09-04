const puppeteer = require('puppeteer-core');

(async () => {
  console.log('Testing User Lookerwood Farm prompt in headless Chrome...');
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  page.on('console', msg => console.log(`[BROWSER CONSOLE ${msg.type()}]:`, msg.text()));

  page.on('response', res => {
    const url = res.url();
    if (url.includes('/chat') || url.includes('/api/embed')) {
      console.log(`[HTTP ${res.status()}]: ${url}`);
    }
  });

  console.log('Navigating to http://localhost:5173 ...');
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle2', timeout: 30000 });

  console.log('Switching to Deep Mode...');
  const buttons = await page.$$('button');
  for (const b of buttons) {
    const text = await page.evaluate(el => el.textContent, b);
    if (text && text.includes('Deep')) {
      await b.click();
      console.log('Clicked Deep mode button!');
      break;
    }
  }

  await new Promise(r => setTimeout(r, 1000));

  const prompt = "Build a comprehensive performance dashboard for Lookerwood Farm tracking revenue, DAU, and engagement for the last 30 days.";
  console.log('Typing scenario prompt:', prompt);
  const input = await page.$('input');
  if (input) {
    await input.click();
    await input.type(prompt);
    console.log('Pressing Enter...');
    await input.press('Enter');
  }

  console.log('Waiting for Deep Analysis response stream and dashboard creation...');
  for (let i = 1; i <= 7; i++) {
    await new Promise(r => setTimeout(r, 5000));
    await page.screenshot({ path: `/tmp/lookerwood_step_${i}.png` });
    console.log(`Captured step ${i} (${i * 5}s)`);
  }

  const iframeSrc = await page.evaluate(() => {
    const iframe = document.querySelector('iframe');
    return iframe ? iframe.src : 'No iframe found';
  });
  console.log('Current embedded iframe src:', iframeSrc);

  console.log('Waiting for Looker tiles to execute queries in iframe...');
  await new Promise(r => setTimeout(r, 15000));

  await page.screenshot({ path: '/tmp/lookerwood_final.png' });
  console.log('Test complete. Screenshots saved.');

  await browser.close();
})();
