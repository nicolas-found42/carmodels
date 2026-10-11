// Usage: node capture.mjs <port> <car codes comma> <model:light pairs comma>
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW);
const [port, cars, combos] = process.argv.slice(2);
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 }, deviceScaleFactor: 1 });
const out = {};
page.on('pageerror', e => console.error('pageerror', e.message));
for (const car of cars.split(',')) for (const combo of combos.split(',')) {
  const [model, light] = combo.split(':');
  await page.goto(`http://127.0.0.1:${port}/${model}/${light}/dealership.html?car=${car}`);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
  await page.waitForTimeout(1500);
  const r = await page.evaluate(async (name) => { const r = window.__capture(); await fetch('/save/' + name, { method: 'POST', body: JSON.stringify(r) }); return r.stats; }, `${car}__${model}__${light}.png`);
  out[`${car} ${model} ${light}`] = r; console.log(car, model, light, JSON.stringify(r));
}
await browser.close();
