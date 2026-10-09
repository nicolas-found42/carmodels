const {chromium}=require('/Users/Nicolas/Documents/github/hermes/tontoko-jeev-browser/node_modules/playwright-core');
const assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({headless:true});try{
const context=await browser.newContext();const page=await context.newPage();let remote=0;const errors=[];
await page.route('**/*',route=>{if(!route.request().url().startsWith('http://127.0.0.1:8088/')){remote++;return route.abort();}return route.continue();});page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:8088/recovered.html');await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('GRAN TORINO ·'),undefined,{timeout:10000});assert.equal(await page.locator('#error').innerText(),'');assert.equal(await page.locator('canvas').count(),1);assert.equal(remote,0);assert.deepEqual(errors,[]);console.log('PASS clean-browser: isolated copied viewer, fresh browser context, empty environment, external requests blocked, model loaded, no page errors');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
