const {chromium}=require('playwright');
const fs=require('fs'),assert=require('node:assert/strict');
const root=process.cwd();
const fixture={country:'FRA',generated_at_utc:new Date().toISOString(),tournaments:[{to_id:'99999',name:'Concours salle test',date_text:'4 Oct 2026',end_date:'2026-10-04',details_url:'https://www.ianseo.net/Details.php?toId=99999',ena_url:'https://www.ianseo.net/TourData/2026/99999/ENA.php',ic_url:'https://www.ianseo.net/TourData/2026/99999/IC.php',entries:[{name:'MARTIN Élodie',club:'0335067 - RENNES',category:'U21',target:'2B',depart:'Départ 1 - 09:00'},{name:'DUPONT Paul',club:'0174246 - SEYNOD',category:'U18',target:'1A'}]}]};
const live='<html><div class="results-header-center"><div>Tir en salle</div><div>Annecy</div></div><table><thead><tr><th colspan="12">Arc Classique [Après 60 flèches]</th></tr></thead><tbody><tr><td>1</td><td>MARTIN Élodie</td><td>0335067 - RENNES</td><td>250/1</td><td>260/1</td><td>510</td><td>12</td><td>3</td></tr></tbody></table></html>';
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const context=await browser.newContext();const errors=[];
 await context.route('**/*',async route=>{
  const url=new URL(route.request().url());
  if(url.hostname==='proxy.test'){
   const source=url.searchParams.get('url')||'';
   const body=source.includes('Details.php')?'<html><title>Concours salle test</title><a href="/TourData/2026/99999/IC.php">Live</a></html>':source.includes('ENA.php')?'<table><tr><th>Athlete</th><th>Target</th><th>Country</th><th>Class</th><th>Session</th></tr><tr><td>MARTIN Élodie</td><td>2B</td><td>0335067 - RENNES</td><td>U21</td><td>Départ 1 - 09:00</td></tr></table>':live;
   return route.fulfill({body,headers:{'content-type':'text/html','x-arclive-fetched-at':new Date().toISOString()}});
  }
  if(url.pathname.endsWith('competition_catalog.json'))return route.fulfill({json:fixture});
  if(url.pathname.endsWith('admin_config.json'))return route.fulfill({json:{ianseoProxyUrl:'https://proxy.test',adminBridgeUrl:''}});
  if(url.pathname.endsWith('admin_state.json'))return route.fulfill({json:JSON.parse(fs.readFileSync(root+'/data/admin_state.json'))});
  if(url.pathname.endsWith('live.json'))return route.fulfill({json:JSON.parse(fs.readFileSync(root+'/data/live.json'))});
  return route.fulfill({contentType:'text/html',body:fs.readFileSync(root+'/index.html','utf8')});
 });
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://localhost:8765/?admin=1');
 await page.waitForSelector('#adminPanel:not(.hidden)');
 await page.waitForFunction(()=>document.querySelector('#statusText').textContent!=='Chargement...');
 await page.fill('#clubInput','Seynod, 0335067 - RENNES');await page.click('#applyClubBtn');
 assert.equal(await page.inputValue('#clubInput'),'0174246, 0335067');
 await page.fill('#archerSearchInput','elodie martin');await page.click('#searchArcherBtn');
 await page.waitForSelector('[data-select-archer]');await page.click('[data-select-archer="0"]');
 await page.waitForFunction(()=>document.querySelector('#statFinished').textContent==='1');
 assert.equal(await page.inputValue('#selectionMode'),'archers');
 assert.equal(await page.textContent('#statArchers'),'1');
 assert.match(await page.textContent('#finishedRows'),/MARTIN Élodie/);
 assert.match(await page.textContent('#finishedRows'),/510/);
 assert.match(await page.textContent('#freshnessInfo'),/HTML IANSEO/);
 // Direct parser checks use actual DOMParser in Chromium.
 assert.equal(await page.evaluate(html=>parseHtmlEntries(html)[0].club,'<table><tr><td colspan="4">0174246 - SEYNOD</td></tr><tr><td>DUPONT Paul</td><td>1A</td><td>U18</td><td>Départ 2 - 14h00</td></tr></table>'),'0174246 - SEYNOD');
 if(process.env.ARCLIVE_SCREENSHOT) await page.screenshot({path:process.env.ARCLIVE_SCREENSHOT,fullPage:true});
 const spectator=await context.newPage();spectator.on('pageerror',e=>errors.push(e.message));
 await spectator.goto('https://viewer.example/?admin=seynod-admin');
 await spectator.waitForFunction(()=>document.querySelector('#statusText').textContent!=='Chargement...');
 assert.equal(await spectator.locator('#adminPanel').isVisible(),false);
 assert.equal(await spectator.locator('#archerSearchInput').isVisible(),false);
 assert.deepEqual(errors,[]);
 console.log('Browser smoke passed: multi-club, accent/order search, exact archer, native HTML, freshness, spectator isolation');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
