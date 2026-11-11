const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const origin='https://texasreligiouslibertywatch.org';
const source=fs.readFileSync(path.join(__dirname,'../dist/90r/sw.js'),'utf8');

function worker(network){
 const handlers={},stored=new Map(),messages=[],requests=[];
 const cache={match:async key=>stored.get(String(key))?.clone(),put:async(key,response)=>{stored.set(String(key),response.clone());}};
 const self={location:{origin},clients:{get:async()=>({postMessage:m=>messages.push(m)}),claim:async()=>{}},addEventListener:(name,handler)=>handlers[name]=handler,skipWaiting:()=>{}};
 class LocalRequest extends Request{constructor(url,options){super(new URL(url,origin),options);}}
 vm.runInNewContext(source,{self,URL,Set,Request:LocalRequest,Response,caches:{open:async()=>cache,keys:async()=>['texas-90r-app-v1'],delete:async()=>true},fetch:async(request,options)=>{requests.push({request,options});return network(request,options);}});
 async function request(url,mode='cors',method='GET'){
  const pending=[];let response;
  handlers.fetch({request:{url:new URL(url,origin).href,mode,method},clientId:'test-client',waitUntil:p=>pending.push(p),respondWith:p=>response=p});
  const result=await response;await Promise.all(pending);return result;
 }
 return {handlers,stored,messages,requests,request};
}

test('fresh bill data always comes from network, overriding older saved data',async()=>{
 const w=worker(async()=>new Response('{"updatedAt":"new"}',{headers:{'Content-Type':'application/json'}}));
 w.stored.set(origin+'/data/bills.json',new Response('{"updatedAt":"old"}'));
 const response=await w.request('/data/bills.json');
 assert.equal(await response.text(),'{"updatedAt":"new"}');
 assert.equal(w.requests[0].options.cache,'no-store');
 assert.equal(await w.stored.get(origin+'/data/bills.json').text(),'{"updatedAt":"new"}');
});

test('offline bill data retains its timestamp and reports saved-content mode',async()=>{
 const w=worker(async()=>{throw Error('offline');});
 w.stored.set(origin+'/data/bills.json',new Response('{"updatedAt":"old"}'));
 assert.equal(await (await w.request('/data/bills.json')).text(),'{"updatedAt":"old"}');
 assert.equal(w.messages[0].type,'CACHE_FALLBACK');
});

test('offline navigation visibly identifies the cached page',async()=>{
 const w=worker(async()=>{throw Error('offline');});
 w.stored.set(origin+'/90r/',new Response('<div id="app-connection" class="app-status" role="status" hidden>Saved content</div>'));
 const response=await w.request('/90r/?bill=HB236','navigate');
 assert.match(await response.text(),/data-cached="true"/);
 assert.equal(response.headers.get('X-Liberty-Watch-Cache'),'saved');
});

test('network errors use offline page for an unsaved app route',async()=>{
 const w=worker(async()=>{throw Error('offline');});
 w.stored.set(origin+'/90r/offline.html',new Response('This page is not saved yet.'));
 assert.equal(await (await w.request('/90r/missing/','navigate')).text(),'This page is not saved yet.');
});

test('scope ignores news, courts, external requests and writes',async()=>{
 const w=worker(async()=>{throw Error('must not fetch');});
 for(const [url,mode,method] of [['/news/','navigate','GET'],['/rulings/','navigate','GET'],['/data/news.json','cors','GET'],['/data/rulings.json','cors','GET'],['https://capitol.texas.gov/','navigate','GET'],['/data/bills.json','cors','POST']]){
  assert.equal(await w.request(url,mode,method),undefined);
 }
 assert.equal(w.requests.length,0);
});

test('server failures retain saved data but genuine 404 responses stay 404',async()=>{
 const w=worker(async()=>new Response('Error',{status:503}));w.stored.set(origin+'/data/bills.json',new Response('Saved snapshot'));
 assert.equal(await (await w.request('/data/bills.json')).text(),'Saved snapshot');
 const missing=worker(async()=>new Response('Not found',{status:404}));missing.stored.set(origin+'/data/bills.json',new Response('Old'));
 assert.equal((await missing.request('/data/bills.json')).status,404);
 assert.equal(missing.messages.length,0);
});

test('every precached resource exists and app data excludes news and rulings',async()=>{
 const w=worker(async request=>{
  const pathname=new URL(request.url).pathname;
  const filename=path.join(__dirname,'../dist',pathname,pathname.endsWith('/')?'index.html':'');
  assert.ok(fs.existsSync(filename),filename+' must exist');
  assert.ok(!/\/data\/(news|rulings|hearings)\.json/.test(pathname));
  return new Response('asset');
 });
 let pending;w.handlers.install({waitUntil:p=>pending=p});await pending;
 assert.ok(w.stored.has(origin+'/data/bills.json'));
 assert.ok(w.stored.has(origin+'/90r/'));
});
