const {chromium}=require('playwright');
const fs=require('fs');const assert=require('assert/strict');const http=require('http');const path=require('path');
(async()=>{
const server=http.createServer((req,res)=>{try{const name=decodeURIComponent(req.url.split('?')[0]);res.setHeader('Content-Type',name.endsWith('.html')?'text/html':name.endsWith('.json')?'application/json':'text/plain');res.end(fs.readFileSync(path.join(process.cwd(),name)))}catch(e){res.statusCode=404;res.end()}}).listen(0);
fs.mkdirSync('/tmp/petss-vendor',{recursive:true});
for (const [name,url] of Object.entries({
 'plotly.js':'https://cdn.plot.ly/plotly-2.35.2.min.js',
 'papa.js':'https://cdn.jsdelivr.net/npm/papaparse@5.4.1/papaparse.min.js',
 'chart.js':'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'})) {
 const response=await fetch(url);if(!response.ok)throw new Error(`Library download failed: ${url}`);
 fs.writeFileSync('/tmp/petss-vendor/'+name,Buffer.from(await response.arrayBuffer()));
}
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.route('https://cdn.plot.ly/**',r=>r.fulfill({path:'/tmp/petss-vendor/plotly.js',contentType:'text/javascript'}));
await page.route('https://cdn.jsdelivr.net/**',r=>r.fulfill({path:r.request().url().includes('papaparse')?'/tmp/petss-vendor/papa.js':'/tmp/petss-vendor/chart.js',contentType:'text/javascript'}));
const base=`http://localhost:${server.address().port}`;
await page.goto(base+'/index.html');await page.waitForFunction(()=>document.querySelector('#chart').data?.length);
assert.equal(await page.locator('#datumSelect').inputValue(),'MHHW');
for(const id of await page.locator('#stationSelect option').evaluateAll(options=>options.map(o=>o.value).filter(id=>!STATIONS[id].observationOnly))){
 await page.selectOption('#stationSelect',id);await page.waitForFunction(id=>document.querySelector('#chart').layout?.title?.text?.includes(STATIONS[id].name),id);
 const before=await page.evaluate(()=>document.querySelector('#chart').data.map(t=>t.y));
 await page.selectOption('#datumSelect','MLLW');
 const after=await page.evaluate(()=>document.querySelector('#chart').data.map(t=>t.y));
 const offset=await page.evaluate(id=>STATIONS[id].datumOffsetMHHW,id);
 before.forEach((ys,t)=>ys.forEach((v,i)=>{if(v!=null)assert.ok(Math.abs(after[t][i]-v-offset)<1e-9)}));
 if(id==='8760922')assert.equal(after[0][0],3.5);
 await page.selectOption('#datumSelect','MHHW');
 if(id==='8760922')assert.match(await page.locator('#thresholdPill').textContent(),/2.33 ft MHHW/);
}
for (const [id, datum, threshold] of [['BSGL1','NAVD88',2.5],['BYGL1','MSL',1.2],['MAUL1','NAVD88',4]]) {
 await page.selectOption('#stationSelect',id);
 await page.waitForFunction(id=>document.querySelector('#chart').layout?.title?.text===STATIONS[id].name,id);
 assert.equal(await page.locator('#datumSelect').inputValue(),datum);
 assert.equal(await page.locator('#datumSelect option[value="MHHW"]').isDisabled(),true);
 assert.equal(await page.locator('#astroToggle').isVisible(),false);
 assert.equal(await page.locator('#rangeToggle').isVisible(),false);
 assert.match(await page.locator('#latestPill').textContent(),/ft.*2026-/);
 const plot=await page.evaluate(()=>({data:document.querySelector('#chart').data,layout:document.querySelector('#chart').layout}));
 assert.equal(plot.data.length,2);assert.equal(plot.data[0].y[0],threshold);
 assert.equal(plot.data[1].connectgaps,false);
 assert.match(plot.layout.yaxis.title.text,new RegExp(datum));
 if(id==='BYGL1'){
  const before=plot.data[1].y;
  await page.selectOption('#datumSelect','NAVD88');
  const after=await page.evaluate(()=>document.querySelector('#chart').data);
  assert.ok(Math.abs(after[0].y[0]-1.68)<1e-9);
  before.forEach((v,i)=>{if(v!==null)assert.ok(Math.abs(after[1].y[i]-v-.48)<1e-9)});
 }
}
await page.selectOption('#stationSelect','8761927');
await page.waitForFunction(()=>document.querySelector('#chart').layout?.title?.text?.includes('New Canal'));
assert.equal(await page.locator('#datumSelect').inputValue(),'MHHW');
assert.equal(await page.locator('#astroToggle').isVisible(),true);
await page.setViewportSize({width:390,height:844});
await page.selectOption('#stationSelect','BSGL1');
await page.waitForFunction(()=>document.querySelector('#chart').layout?.title?.text===STATIONS.BSGL1.name);
await page.screenshot({path:'/tmp/petss-observation-mobile.png',fullPage:true});
await page.setViewportSize({width:1400,height:1000});
await page.screenshot({path:'/tmp/petss-observation-desktop.png',fullPage:true});
await page.goto(base+'/surge.html');await page.waitForSelector('#datumSelect');assert.equal(await page.locator('#datumSelect').inputValue(),'MHHW');
const before=await page.evaluate(()=>chart.data.datasets.map(d=>d.data));
await page.selectOption('#datumSelect','MLLW');const after=await page.evaluate(()=>chart.data.datasets.map(d=>d.data));
assert.deepEqual(before[4],after[4]);assert.ok(Math.abs(after[5][0]-before[5][0]-0.41)<1e-9);
await page.click('#refreshBtn');await page.waitForFunction(()=>!document.querySelector('#refreshBtn').disabled);assert.equal(await page.locator('#datumSelect').inputValue(),'MLLW');
assert.deepEqual(errors,[]);console.log('PASS: real Chromium + Plotly/Chart.js; nine stations, observation-only traces, datum switching, Pilots thresholds, surge invariance, refresh, zero page errors');
await browser.close();server.close();
})().catch(e=>{console.error(e);process.exit(1)});
