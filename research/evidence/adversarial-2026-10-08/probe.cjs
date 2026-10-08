const {chromium}=require('/Users/Nicolas/Documents/github/hermes/tontoko-jeev-browser/node_modules/playwright-core');
const fs=require('fs');
(async()=>{
const browser=await chromium.launch({headless:true}); const page=await browser.newPage({viewport:{width:1280,height:900}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.route('**/recovered.html',async route=>{const r=await route.fetch();let html=await r.text();html=html.replace('await loadCar();window.__recBoot.ok();','await loadCar();window.__recBoot.ok();window.probe=()=>({selected:selected?.code,meshes:loaded.meshes.map(m=>({base:m.userData.baseMaterial,map:loaded.textures.indexOf(m.material.map),color:m.material.color.toArray(),factor:loaded.doc.materials[m.userData.baseMaterial].pbrMetallicRoughness})),doc:loaded.doc});');await route.fulfill({response:r,body:html});});
await page.goto('http://127.0.0.1:8087/recovered.html');await page.waitForFunction(()=>window.probe);
const base=await page.evaluate(()=>{const p=probe();return {selected:p.selected,materials:p.doc.materials.length,textures:p.doc.textures.length,wrongMaps:p.meshes.filter(m=>m.map!==(m.factor.baseColorTexture?.index??-1)).length,examples:p.meshes.slice(0,3)}});console.log('E01 material baseline',JSON.stringify(base));
await page.route('**/COBRA.glb',route=>route.fulfill({status:404,body:'missing'}));await page.selectOption('#car','COBRA');await page.waitForFunction(()=>document.querySelector('#error').textContent.includes('did not load'));
console.log('E02 failed switch',JSON.stringify(await page.evaluate(()=>({car:document.querySelector('#car').value,shown:probe().selected,download:document.querySelector('#download').getAttribute('href'),recordEnabled:!document.querySelector('#record').disabled,status:document.querySelector('#status').textContent,error:document.querySelector('#error').textContent}))));
await page.selectOption('#record','scene2');console.log('E02 geometry after failure',await page.locator('#status').innerText());
await page.screenshot({path:'.scratch/adversarial-2026-10-08/baseline-failed.png'});
await page.unroute('**/COBRA.glb');await page.selectOption('#car','FOCUS_WRC');await page.waitForFunction(()=>probe().selected==='FOCUS_WRC');console.log('E03 recovery',await page.locator('#status').innerText());
await page.goto('http://127.0.0.1:8087/');await page.waitForSelector('.car-row');console.log('E04 gallery',await page.locator('.car-row').count(),'rows, keyboard focusable',await page.locator('.car-row').evaluateAll(xs=>xs.filter(x=>x.tabIndex>=0).length));console.log('pageErrors',errors);
await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1;});
