const {chromium} = require('/Users/Nicolas/Documents/github/hermes/tontoko-jeev-browser/node_modules/playwright-core');
const fs = require('node:fs');
const root = 'research/evidence/silhouettes-2026-10-08';
const base = 'http://127.0.0.1:8098/';
(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1280,height:900}});
    await page.route(base, async route => {
      const response = await route.fetch();
      let html = await response.text();
      html = html.replace('tick();\n</script>', `tick();
window.probe = () => ({memory:{...renderer.info.memory}, code:current?.code,
  bounds:carMesh ? new THREE.Box3().setFromObject(carMesh).getSize(new THREE.Vector3()).toArray():null,
  wheelAxes:carMesh?.userData.wheels?.map(w=>new THREE.Vector3(0,1,0).applyQuaternion(w.quaternion).toArray())});
</script>`);
      await route.fulfill({response,body:html});
    });
    await page.goto(base);
    await page.waitForFunction(()=>window.__viewerBoot.loaded);
    await page.waitForTimeout(500);
    console.log('initial',await page.evaluate(()=>probe()));
    await page.screenshot({path:root+'/before-desktop.png'});
    for (const code of ['F150','FOCUS_WRC','EXPLORER']) {
      await page.evaluate(code=>[...document.querySelectorAll('.car-row')].find(x=>x._code===code).click(),code);
      await page.waitForTimeout(100);
      await page.screenshot({path:root+'/before-'+code+'.png'});
    }
    for (let i=0;i<105;i++) {
      await page.evaluate(i=>document.querySelectorAll('.car-row')[i%35].click(),i);
      await page.waitForTimeout(20);
    }
    console.log('after105',await page.evaluate(()=>probe()));
    await page.locator('#search').fill('no-car-has-this-name');
    console.log('empty-search',await page.evaluate(()=>({visible:[...document.querySelectorAll('.car-row')].filter(x=>getComputedStyle(x).display!=='none').length,body:document.querySelector('#list').innerText,hud:document.querySelector('#hud-name').textContent})));
    await page.locator('#search').fill('');
    await page.setViewportSize({width:390,height:844});
    console.log('mobile',await page.evaluate(()=>{const rect=id=>{const r=document.getElementById(id).getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height}};return{stage:rect('stage'),panel:rect('panel'),hud:rect('hud'),overflow:document.documentElement.scrollWidth-innerWidth};}));
    await page.screenshot({path:root+'/before-mobile.png'});
    await page.close();
    for (const [name,body,delay,status] of [
      ['empty','[]',0,200],['http-error','[]',0,404],['malformed','{}',0,200],
      ['slow',fs.readFileSync('viewer/public/cars.json','utf8'),5600,200],
      ['injected',JSON.stringify([{...JSON.parse(fs.readFileSync('viewer/public/cars.json'))[0],name:'<img src=x onerror="window.injected=true">'}]),0,200],
    ]) {
      const p = await browser.newPage();
      await p.route('**/public/cars.json',async route=>{await new Promise(r=>setTimeout(r,delay));await route.fulfill({status,contentType:'application/json',body});});
      await p.goto(base);
      await p.waitForTimeout(delay+900);
      console.log(name,await p.evaluate(()=>({boot:window.__viewerBoot,loading:document.getElementById('loading')?.textContent,rows:document.querySelectorAll('.car-row').length,injected:!!window.injected,imgs:document.querySelectorAll('#list img').length})));
      await p.close();
    }
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
