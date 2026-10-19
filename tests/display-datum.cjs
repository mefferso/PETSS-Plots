const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function page(file) {
  const html = fs.readFileSync(file, 'utf8');
  const elements = {};
  const el = id => elements[id] ||= {value:'', checked:false, innerHTML:'', addEventListener(e, fn){this[e]=fn}, appendChild(){}, getContext(){return {}}};
  for (const match of html.matchAll(/<select id="([^"]+)"[^>]*>([\s\S]*?)<\/select>/g)) {
    const options = [...match[2].matchAll(/<option value="([^"]+)"([^>]*)>/g)];
    if (!options.length) continue;
    el(match[1]).value = (options.find(o => o[2].includes('selected')) || options[0])[1];
  }
  const context = vm.createContext({console, Date, setInterval(){}, clearInterval(){},
    document:{getElementById:el, createElement:()=>({})}, window:{addEventListener(){}},
    Papa:{parse(url, options){const rows=fs.readFileSync(url.split('?')[0],'utf8').trim().split(/\r?\n/).map(r=>r.split(',')); options.complete({data:rows})}},
    Plotly:{purge(){},react(id,traces,layout){context.plot={traces,layout}},downloadImage(){}},
    Chart: Object.assign(function(ctx, config){context.chartConfig=config;this.destroy=()=>{}}, {register(){}}),
    fetch:async url=>({ok:true,json:async()=>JSON.parse(fs.readFileSync(url.split('?')[0],'utf8'))})});
  vm.runInContext([...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n'), context);
  return {context, el, run:code=>vm.runInContext(code,context)};
}
test('default, all stations, datum round trips and aligned flood/forecast/observations',()=>{
  const p=page('index.html');
  assert.equal(p.el('datumSelect').value,'MHHW');
  for(const id of p.run('Object.keys(STATIONS)')) {
    p.run(`loadStation('${id}')`);
    const mhhw=JSON.parse(JSON.stringify(p.context.plot));
    assert.match(mhhw.layout.yaxis.title.text,/MHHW/);
    p.el('datumSelect').value='MLLW'; p.el('datumSelect').change();
    const mllw=JSON.parse(JSON.stringify(p.context.plot));
    const offset=p.run(`STATIONS['${id}'].datumOffsetMHHW`);
    for(let t=0;t<mllw.traces.length;t++) for(let i=0;i<mllw.traces[t].y.length;i++) {
      const value=mllw.traces[t].y[i];
      if(value!=null) assert.ok(Math.abs(value-mhhw.traces[t].y[i]-offset)<1e-9);
    }
    if(id==='8760922') {assert.equal(mllw.traces[0].y[0],3.5);assert.ok(Math.abs(mhhw.traces[0].y[0]-2.33)<1e-9);}
    p.el('datumSelect').value='MHHW';p.el('datumSelect').change();
    assert.deepEqual(JSON.parse(JSON.stringify(p.context.plot)),mhhw);
  }
});
test('surge dashboard defaults to MHHW, converts heights only and preserves raw data',async()=>{
  const p=page('surge.html');
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(p.run('selectedDatum'),'MHHW');
  const raw=JSON.parse(fs.readFileSync('data/surge_dashboard/chart_data.json','utf8'));
  p.run('selectedDatum="MLLW"');
  const mllw=p.run(`dashboardForDisplay(${JSON.stringify(raw)})`);
  p.run('selectedDatum="MHHW"');
  const mhhw=p.run(`dashboardForDisplay(${JSON.stringify(raw)})`);
  for(let i=0;i<raw.series.length;i++) {
    for(const key of ['twl_ft','twl10_ft','twl90_ft','tide_ft','obs_ft']) if(raw.series[i][key]!=null) assert.ok(Math.abs(mllw.series[i][key]-mhhw.series[i][key]-0.41)<1e-9);
    assert.equal(mhhw.series[i].surge_ft,raw.series[i].surge_ft);
  }
  assert.equal(JSON.stringify(mllw),JSON.stringify(raw));
});
test('surge dashboard recovers after an error removes toggle controls',async()=>{
  const p=page('surge.html');
  await new Promise(resolve=>setImmediate(resolve));
  const lookup=p.context.document.getElementById;
  let missing = 4;
  p.context.document.getElementById=id=>id.startsWith('toggle') && missing-- > 0 ? null : lookup(id);
  assert.doesNotThrow(()=>p.run('renderDashboard()'));
});
test('Pilots offset matches preserved station-specific NOAA metadata',()=>{
  const reference=JSON.parse(fs.readFileSync('docs/pilots-station-noaa-datums.json','utf8'));
  assert.equal(reference.units,'feet');
  const elevations=Object.fromEntries(reference.datums.map(d=>[d.name,d.value]));
  const p=page('index.html');
  assert.ok(Math.abs(p.run('STATIONS["8760922"].datumOffsetMHHW')-(elevations.MHHW-elevations.MLLW))<1e-9);
});
test('a late station response cannot replace the newly selected station',()=>{
  const p=page('index.html');const pending=[];
  const parse=p.context.Papa.parse;
  p.context.Papa.parse=(url,options)=>pending.push(()=>parse(url,options));
  p.run('loadStation("8760922")');p.run('loadStation("8747437")');
  pending[1]();const latest=JSON.stringify(p.context.plot);
  pending[0]();assert.equal(JSON.stringify(p.context.plot),latest);
});
