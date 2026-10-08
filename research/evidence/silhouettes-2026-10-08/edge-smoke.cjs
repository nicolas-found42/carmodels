const {chromium}=require('/Users/Nicolas/Documents/github/hermes/tontoko-jeev-browser/node_modules/playwright-core');
const assert=require('node:assert/strict');const fs=require('node:fs');
(async()=>{const b=await chromium.launch({headless:true});try{
 const root='http://127.0.0.1:8098/';
 const missing=await b.newPage();await missing.route('**/vendor/three.module.js',r=>r.fulfill({status:404,body:'missing'}));await missing.goto(root);await missing.getByRole('button',{name:'Reload viewer'}).waitFor({timeout:8000});assert.match(await missing.locator('#loading').textContent(),/could not start|longer than expected/);console.log('Missing vendor: visible startup guidance + Reload viewer');await missing.close();
 const disk=await b.newPage();await disk.goto('file://'+process.cwd()+'/viewer/index.html');assert.match(await disk.locator('#loading').textContent(),/served, not opened from disk/);console.log('file://: correct local-server guidance');await disk.close();
 const p=await b.newPage();await p.goto(root);await p.waitForFunction(()=>window.__viewerBoot.loaded);
 const corpus=JSON.parse(fs.readFileSync('viewer/public/cars.json'));
 for(const label of ['CLASSIC','MODERN'])await p.locator('.chip').filter({hasText:new RegExp('^'+label+'$')}).click();
 await p.locator('.chip').filter({hasText:/^COUPE$/}).click();
 const expected=corpus.filter(c=>['CLASSIC','MODERN'].includes(c.group)&&c.bodyStyle==='coupe').length;
 assert.equal(await p.locator('.car-row:visible').count(),expected);
 await p.locator('#search').fill('2002');assert.equal(await p.locator('.car-row:visible').count(),corpus.filter(c=>['CLASSIC','MODERN'].includes(c.group)&&c.bodyStyle==='coupe'&&(c.name+' '+c.code+' '+c.year).includes('2002')).length);
 console.log('Group OR, style AND, year search: expected counts match corpus');await p.close();
 console.log('PASS silhouette startup and filter smoke');
}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
