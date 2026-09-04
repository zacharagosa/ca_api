const puppeteer = require('puppeteer-core');

(async () => {
  console.log('Testing Multi-Turn Iterative Dashboard Editing in Chrome...');
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  page.on('console', msg => console.log(`[BROWSER CONSOLE ${msg.type()}]:`, msg.text()));

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

  // Turn 1: Build initial dashboard
  const prompt1 = "Build a LiveOps War Room dashboard for Lookerwood Farm with 2 tiles: Daily Active Users and Total Revenue.";
  console.log('\n--- Turn 1 Prompt ---:', prompt1);
  let input = await page.$('input');
  if (input) {
    await input.click();
    await input.type(prompt1);
    await input.press('Enter');
  }

  console.log('Waiting for Turn 1 dashboard creation (25s)...');
  await new Promise(r => setTimeout(r, 25000));
  await page.screenshot({ path: '/tmp/iterative_turn1.png' });

  // Turn 2: Edit dashboard incrementally
  const prompt2 = "Add a new tile for ARPU Trend to this dashboard, and add a Date Range filter for the last 30 days.";
  console.log('\n--- Turn 2 Prompt ---:', prompt2);
  input = await page.$('input');
  if (input) {
    await input.click();
    await input.type(prompt2);
    await input.press('Enter');
  }

  console.log('Waiting for Turn 2 iterative dashboard editing (25s)...');
  await new Promise(r => setTimeout(r, 25000));
  await page.screenshot({ path: '/tmp/iterative_turn2.png' });

  console.log('Test complete. Screenshots saved.');
  await browser.close();
})();
