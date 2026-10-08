// Executed diagnostic harness. Reuses the existing browser package, adds no project dependency.
const {chromium}=require('/Users/Nicolas/Documents/github/hermes/tontoko-jeev-browser/node_modules/playwright-core');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const root='research/evidence/silhouettes-2026-10-08', base='http://127.0.0.1:8098/';
const corpus=JSON.parse(fs.readFileSync('viewer/public/cars.json'));
const probe=`window.probe=()=>({memory:{...renderer.info.memory},code:current?.code,
 camera:camera.position.toArray(),target:controls.target.toArray(),auto:controls.autoRotate,
 wheels:carMesh?.userData.wheels.map(w=>w.quaternion.toArray()),
 projected:carMesh?(()=>{const b=new THREE.Box3().setFromObject(carMesh);return [b.min.x,b.max.x].flatMap(x=>[b.min.y,b.max.y].flatMap(y=>[b.min.z,b.max.z].map(z=>new THREE.Vector3(x,y,z).project(camera).toArray())));})():[]});`;
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
  console.log('Browser',browser.version());
  const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
  const external=[];
  await context.route('**/*',async route=>{
   if(!route.request().url().startsWith(base)){external.push(route.request().url());return route.abort();}
   if(route.request().url()===base){const response=await route.fetch();return route.fulfill({response,body:(await response.text()).replace('loadCorpus();\n</script>',probe+'\nloadCorpus();\n</script>')});}
   return route.continue();
  });
  const page=await context.newPage(), errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);await page.waitForFunction(()=>window.__viewerBoot.loaded);
  await page.waitForTimeout(300);
  assert.equal(await page.locator('.car-row').count(),35);
  assert.equal((await page.evaluate(()=>probe())).auto,false);
  const stationary=await page.evaluate(()=>probe());await page.waitForTimeout(300);
  assert.deepEqual((await page.evaluate(()=>probe())).camera,stationary.camera);
  assert.deepEqual((await page.evaluate(()=>probe())).wheels,stationary.wheels);
  await page.screenshot({path:root+'/after-desktop.png'});
  let maxGeometry=0;
  for(let i=0;i<105;i++) {
   await page.locator('.car-row').nth(i%35).click();
   await page.waitForTimeout(30);
   const data=await page.evaluate(()=>probe());
   maxGeometry=Math.max(maxGeometry,data.memory.geometries);
   assert(data.projected.every(p=>Math.abs(p[0])<=1&&Math.abs(p[1])<=1),data.code+' clipped');
  }
  assert(maxGeometry<30,'GPU geometry grows across switches');
  console.log('105 corpus selections: max GPU geometries',maxGeometry,'final',await page.evaluate(()=>probe().memory),'all projected bounds fit');
  await page.locator('.car-row').filter({hasText:'F-150 FLARESIDE'}).click();
  await page.getByRole('button',{name:'Side',exact:true}).focus();await page.keyboard.press('Enter');
  await page.screenshot({path:root+'/after-pickup-side.png'});
  for(const name of ['Front','Top','Reset view']){await page.getByRole('button',{name,exact:true}).click();assert((await page.evaluate(()=>probe())).projected.every(p=>Math.abs(p[0])<=1&&Math.abs(p[1])<=1));}
  await page.locator('#auto-rotate').check();
  const moving=await page.evaluate(()=>probe().camera);await page.waitForTimeout(300);
  assert.notDeepEqual(await page.evaluate(()=>probe().camera),moving);
  await page.locator('#auto-rotate').uncheck();
  await page.waitForTimeout(300);const stopped=await page.evaluate(()=>probe().camera);await page.waitForTimeout(300);
  assert.deepEqual(await page.evaluate(()=>probe().camera),stopped);
  console.log('Reduced motion, explicit rotation pause/resume, keyboard side view and reset/front/top: PASS');
  await page.locator('#search').fill('no-car-has-this-name');
  assert.equal(await page.locator('.car-row:visible').count(),0);
  assert(await page.locator('#empty').isVisible());
  assert.match(await page.locator('#results').textContent(),/^0 of 35/);
  await page.getByRole('button',{name:'Clear search and filters'}).click();
  assert.equal(await page.locator('.car-row:visible').count(),35);
  await page.locator('.chip').filter({hasText:'PICKUP'}).focus();await page.keyboard.press('Space');
  assert.equal(await page.locator('.car-row:visible').count(),6);
  await page.getByRole('button',{name:'Clear search and filters'}).click();
  for(const width of [320,390,768,1280]){
   await page.setViewportSize({width,height:844});await page.waitForTimeout(150);
   const layout=await page.evaluate(()=>{const a=document.querySelector('#stage').getBoundingClientRect(),b=document.querySelector('#panel').getBoundingClientRect();return{overflow:document.documentElement.scrollWidth-innerWidth,overlap:Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top))};});
   assert.equal(layout.overflow,0);assert.equal(layout.overlap,0);console.log('layout',width,layout);
   if(width===390){await page.screenshot({path:root+'/after-mobile-full.png',fullPage:true});await page.locator('#stage').scrollIntoViewIfNeeded();await page.screenshot({path:root+'/after-mobile.png'});}
  }
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  console.log('Success-path page errors and external requests: zero');
  await context.close();
  for(const [name,data,status] of [['empty',[],200],['duplicate',[corpus[0],corpus[0]],200],['invalid-rating',[{...corpus[0],speed:2}],200],['http-error',corpus,404],['malformed',{},200]]){
   const p=await browser.newPage();let failures=1;
   await p.route('**/public/cars.json',r=>r.fulfill({status:failures-- > 0?status:200,contentType:'application/json',body:JSON.stringify(failures>=0?data:corpus)}));
   await p.goto(base);await p.getByRole('button',{name:'Retry loading cars'}).waitFor();
   assert.equal(await p.locator('.car-row').count(),0);
   console.log(name,await p.locator('#loading').textContent());
   await p.getByRole('button',{name:'Retry loading cars'}).click();await p.waitForFunction(()=>window.__viewerBoot.loaded);
   assert.equal(await p.locator('.car-row').count(),35);console.log(name,'same-page retry PASS');await p.close();
  }
  const slow=await browser.newPage();await slow.route('**/public/cars.json',async r=>{await new Promise(res=>setTimeout(res,5600));await r.fulfill({contentType:'application/json',body:JSON.stringify(corpus)});});
  await slow.goto(base);await slow.waitForTimeout(5100);assert.equal(await slow.locator('#loading').textContent(),'Loading corpus…');
  await slow.waitForFunction(()=>window.__viewerBoot.loaded);assert.equal(await slow.locator('.car-row').count(),35);console.log('5.6s valid load: no premature error, success');await slow.close();
  const stall=await browser.newPage();await stall.route('**/public/cars.json',()=>{});await stall.goto(base);const started=Date.now();await stall.getByRole('button',{name:'Retry loading cars'}).waitFor({timeout:20000});assert.match(await stall.locator('#loading').textContent(),/timed out/);console.log('stalled request fails with retry at',Date.now()-started,'ms');await stall.close();
  const injected=await browser.newPage();await injected.route('**/public/cars.json',r=>r.fulfill({contentType:'application/json',body:JSON.stringify([{...corpus[0],name:'<img src=x onerror="window.injected=true">'}])}));
  await injected.goto(base);await injected.waitForFunction(()=>window.__viewerBoot.loaded);assert.equal(await injected.locator('#list img').count(),0);assert.equal(await injected.evaluate(()=>!!window.injected),false);assert.match(await injected.locator('.nm').textContent(),/<img/);console.log('HTML name remains literal, zero img nodes/execution');await injected.close();
  console.log('PASS silhouettes browser re-attack');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
