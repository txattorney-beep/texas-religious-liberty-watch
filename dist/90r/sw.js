'use strict';
// This worker controls /90r/ only. It never caches the wider news or court site.
const CACHE_NAME='texas-90r-app-v4';
const CORE=[
 '/90r/','/90r/install/','/90r/offline.html',
 '/styles.css?v=simple-search-20261112','/news.css?v=maroon-courts','/mobile.css?v=90r-app',
 '/app.js?v=simple-search-20261112','/90r/pwa.js','/90r/manifest.webmanifest','/favicon.svg','/data/bills.json',
 '/90r/icons/icon-192.png','/90r/icons/icon-512.png','/90r/icons/maskable-512.png','/90r/icons/apple-touch-icon.png'
];
const CACHEABLE=new Set(CORE.map(path=>new URL(path,self.location.origin).pathname));
function cacheKey(url){let path=url.pathname;if(path.endsWith('/index.html'))path=path.slice(0,-10);return new URL(path,self.location.origin).href;}
self.addEventListener('install',event=>{
 event.waitUntil((async()=>{
  const cache=await caches.open(CACHE_NAME);
  await Promise.all(CORE.map(async path=>{
   const response=await fetch(new Request(path,{cache:'reload'}));
   if(!response.ok)throw new Error('App resource unavailable: '+path);
   await cache.put(cacheKey(new URL(path,self.location.origin)),response);
  }));
 })());
});
self.addEventListener('activate',event=>{
 event.waitUntil((async()=>{for(const name of await caches.keys())if(name.startsWith('texas-90r-app-')&&name!==CACHE_NAME)await caches.delete(name);await self.clients.claim();})());
});
self.addEventListener('message',event=>{if(event.data?.type==='SKIP_WAITING')self.skipWaiting();});
async function fallback(event,key){
 const cache=await caches.open(CACHE_NAME);
 let response=await cache.match(key);
 if(!response&&event.request.mode==='navigate')response=await cache.match(new URL('/90r/offline.html',self.location.origin).href);
 if(!response)return new Response('Offline. Open the 90R tracker online first.',{status:503,headers:{'Content-Type':'text/plain'}});
 const client=await self.clients.get(event.clientId||event.resultingClientId);
 client?.postMessage({type:'CACHE_FALLBACK'});
 if(event.request.mode==='navigate'){
  const text=(await response.text()).replace('id="app-connection" class="app-status" role="status" hidden','id="app-connection" class="app-status" role="status" data-cached="true"');
  return new Response(text,{status:200,headers:{'Content-Type':'text/html; charset=utf-8','X-Liberty-Watch-Cache':'saved'}});
 }
 return response;
}
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 if(event.request.method!=='GET'||url.origin!==self.location.origin)return;
 const key=cacheKey(url),path=new URL(key).pathname;
 const navigation=event.request.mode==='navigate'&&path.startsWith('/90r/');
 if(!navigation&&!CACHEABLE.has(path))return;
 event.respondWith((async()=>{
  try{
   const response=await fetch(event.request,{cache:'no-store'});
   if(response.status>=500)return fallback(event,key);
   if(response.ok&&CACHEABLE.has(path)){
    const copy=response.clone();
    event.waitUntil(caches.open(CACHE_NAME).then(cache=>cache.put(key,copy)).catch(()=>{}));
   }
   return response;
  }catch{return fallback(event,key);}
 })());
});
