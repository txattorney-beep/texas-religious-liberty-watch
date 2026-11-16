/* First-party sharing controls. No third-party SDKs, pixels, or automatic posts. */
(()=>{'use strict';
 const site={"name": "Texas Religious Liberty Watch", "url": "https://texasreligiouslibertywatch.org/", "description": "Follow religious liberty news, Texas legislation, and court developments.", "theme": "liberty"};
 const enc=encodeURIComponent;
 function mount(){
  if(document.getElementById('site-sharing'))return;
  const block=document.createElement('section');block.id='site-sharing';block.className='site-sharing '+site.theme;block.setAttribute('aria-labelledby','site-sharing-title');
  const text=site.name+': '+site.description;
  const body=text+'\n'+site.url;
  const links=[['Facebook','https://www.facebook.com/sharer/sharer.php?u='+enc(site.url)],['LinkedIn','https://www.linkedin.com/sharing/share-offsite/?url='+enc(site.url)],['X','https://x.com/intent/tweet?text='+enc(text)+'&url='+enc(site.url)],['WhatsApp','https://wa.me/?text='+enc(body)],['Text message','sms:' + (/iPad|iPhone|iPod/.test(navigator.userAgent)?'&':'?')+'body='+enc(body)],['Email','mailto:?subject='+enc(site.name)+'&body='+enc(body)]];
  block.innerHTML='<div class="sharing-heading"><p>PASS IT ALONG</p><h2 id="site-sharing-title">Share '+site.name+'</h2></div><div class="sharing-buttons"></div><p class="sharing-status" role="status" aria-live="polite"></p>';
  const buttons=block.querySelector('.sharing-buttons'),status=block.querySelector('.sharing-status');
  for(const [name,url] of links){const a=document.createElement('a');a.textContent=name;a.href=url;if(url.startsWith('https:')){a.target='_blank';a.rel='noopener noreferrer'}a.setAttribute('aria-label','Share '+site.name+' via '+name);buttons.append(a)}
  function button(label,action){const b=document.createElement('button');b.type='button';b.textContent=label;b.addEventListener('click',action);buttons.append(b);return b}
  const dialog=document.createElement('dialog');dialog.className='sharing-dialog '+site.theme;dialog.setAttribute('aria-labelledby','sharing-dialog-title');
  dialog.innerHTML='<h2 id="sharing-dialog-title">Share on Instagram</h2><p>Copy the link and paste it into an Instagram message, or use the link sticker in a story. Instagram may also appear in your device’s share menu.</p><label for="sharing-link">Website link</label><input id="sharing-link" readonly><div class="sharing-dialog-actions"><button type="button" data-sharing-copy>Copy link</button><a href="https://www.instagram.com/" target="_blank" rel="noopener noreferrer">Open Instagram ↗</a><button type="button" data-sharing-close>Done</button></div><p role="status" aria-live="polite" class="sharing-dialog-status"></p>';
  dialog.querySelector('input').value=site.url;
  async function copy(target=status){try{if(!navigator.clipboard?.writeText)throw new Error('Clipboard unavailable');await navigator.clipboard.writeText(site.url);target.textContent='Link copied.'}catch{if(!dialog.open)dialog.showModal();const input=dialog.querySelector('input');input.focus();input.select();dialog.querySelector('.sharing-dialog-status').textContent='Select and copy this link using your device’s copy command.'}}
  button('Instagram',()=>{dialog.showModal();dialog.querySelector('.sharing-dialog-status').textContent=''});
  button('Copy link',()=>copy());
  if(typeof navigator.share==='function')button('More ways to share',async()=>{try{await navigator.share({title:site.name,text:site.description,url:site.url})}catch(error){if(error.name!=='AbortError')status.textContent='Sharing is unavailable here. Use a button above or copy the link.'}});
  dialog.querySelector('[data-sharing-copy]').addEventListener('click',()=>copy(dialog.querySelector('.sharing-dialog-status')));
  dialog.querySelector('[data-sharing-close]').addEventListener('click',()=>dialog.close());
  document.body.append(block,dialog);
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
})();
