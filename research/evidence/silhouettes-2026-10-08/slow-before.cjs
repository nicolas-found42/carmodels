const {chromium}=require('/Users/Nicolas/Documents/github/hermes/tontoko-jeev-browser/node_modules/playwright-core');
const fs=require('node:fs');
(async()=>{const browser=await chromium.launch({headless:true});try{
 const page=await browser.newPage();const base='http://127.0.0.1:8098/';
 await page.route(base,r=>r.fulfill({contentType:'text/html',body:fs.readFileSync('.scratch/silhouettes-2026-10-08/index.before.html','utf8')}));
 await page.route('**/public/cars.json',async r=>{await new Promise(res=>setTimeout(res,5600));await r.fulfill({contentType:'application/json',body:fs.readFileSync('viewer/public/cars.json','utf8')});});
 await page.goto(base);await page.waitForTimeout(5100);
 console.log('At 5.1s',await page.evaluate(()=>({boot:window.__viewerBoot,text:document.querySelector('#loading')?.textContent})));
 await page.waitForFunction(()=>window.__viewerBoot.loaded);
 console.log('After response',await page.evaluate(()=>({boot:window.__viewerBoot,rows:document.querySelectorAll('.car-row').length})));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
