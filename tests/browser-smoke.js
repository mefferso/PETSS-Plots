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
for(const id of await page.locator('#stationSelect option').evaluateAll(options=>options.map(o=>o.value))){
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
await page.goto(base+'/surge.html');await page.waitForSelector('#datumSelect');assert.equal(await page.locator('#datumSelect').inputValue(),'MHHW');
const before=await page.evaluate(()=>chart.data.datasets.map(d=>d.data));
await page.selectOption('#datumSelect','MLLW');const after=await page.evaluate(()=>chart.data.datasets.map(d=>d.data));
assert.deepEqual(before[4],after[4]);assert.ok(Math.abs(after[5][0]-before[5][0]-0.41)<1e-9);
await page.click('#refreshBtn');await page.waitForFunction(()=>!document.querySelector('#refreshBtn').disabled);assert.equal(await page.locator('#datumSelect').inputValue(),'MLLW');
assert.deepEqual(errors,[]);console.log('PASS: real Chromium + Plotly/Chart.js; six stations, datum switching, Pilots thresholds, surge invariance, refresh, zero page errors');
await browser.close();server.close();
})().catch(e=>{console.error(e);process.exit(1)});
