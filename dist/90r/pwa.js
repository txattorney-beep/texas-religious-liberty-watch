'use strict';
(() => {
 let installPrompt=null,registration=null,reloadForUpdate=false,cachedFallback=false;
 const installed=()=>matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;
 const buttons=()=>[...document.querySelectorAll('[data-install-button]')];
 const status=document.querySelector('#install-status');
 function installState(){
  buttons().forEach(button=>button.hidden=!installPrompt||installed());
  if(installed()){
   document.querySelectorAll('a[href="/90r/install/"]').forEach(link=>link.hidden=true);
   if(status)status.textContent='You are using the installed 90R tracker.';
  }
 }
 window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();installPrompt=event;installState();});
 window.addEventListener('appinstalled',()=>{installPrompt=null;buttons().forEach(b=>b.hidden=true);if(status)status.textContent='The 90R app was installed. Look for 90R Watch on your home or apps screen.';});
 buttons().forEach(button=>button.addEventListener('click',async()=>{
  if(!installPrompt)return;
  const prompt=installPrompt;installPrompt=null;buttons().forEach(b=>b.hidden=true);
  try{await prompt.prompt();const choice=await prompt.userChoice;if(status)status.textContent=choice.outcome==='accepted'?'Installation requested. Follow your browser’s confirmation and look for 90R Watch.':'You can install later through your browser menu, or keep using the tracker here.';}
  catch{if(status)status.textContent='Use the iPhone or Samsung instructions below to install from your browser menu.';}
 }));
 const connection=document.querySelector('#app-connection');
 cachedFallback=connection?.dataset.cached==='true';
 function connectionState(){
  if(!connection)return;
  connection.hidden=navigator.onLine&&!cachedFallback;
  connection.querySelector('span').textContent=navigator.onLine?'Showing saved content after a connection problem. Refresh while online for the latest published snapshot.':'You are offline. Showing saved content, which may be out of date. Official source links need an internet connection.';
 }
 window.addEventListener('offline',connectionState);
 window.addEventListener('online',()=>{cachedFallback=true;connectionState();});
 document.querySelectorAll('[data-app-refresh]').forEach(b=>b.addEventListener('click',()=>location.reload()));
 installState();connectionState();
 if(!('serviceWorker' in navigator)||!window.isSecureContext)return;
 navigator.serviceWorker.addEventListener('message',event=>{if(event.data?.type==='CACHE_FALLBACK'){cachedFallback=true;connectionState();}});
 navigator.serviceWorker.addEventListener('controllerchange',()=>{if(reloadForUpdate)location.reload();});
 const showUpdate=()=>{const notice=document.querySelector('#app-update');if(notice&&registration?.waiting)notice.hidden=false;};
 document.querySelector('#app-update-button')?.addEventListener('click',()=>{if(registration?.waiting){reloadForUpdate=true;registration.waiting.postMessage({type:'SKIP_WAITING'});}});
 window.addEventListener('load',async()=>{
  try{
   registration=await navigator.serviceWorker.register('/90r/sw.js',{scope:'/90r/',updateViaCache:'none'});
   showUpdate();
   registration.addEventListener('updatefound',()=>{const worker=registration.installing;worker?.addEventListener('statechange',()=>{if(worker.state==='installed'&&navigator.serviceWorker.controller)showUpdate();});});
  }catch{if(status)status.textContent='The tracker works online. Offline setup was unavailable; use your browser’s home-screen option and try an online visit again.';}
 });
})();
