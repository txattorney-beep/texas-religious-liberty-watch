'use strict';
(()=>{
 const front=document.querySelector('#wire-front'),desk=document.querySelector('#legislative-desk');
 if(!front||!desk)return;
 function view(){const showingDesk=Boolean(location.hash)&&location.hash!=='#main';front.hidden=showingDesk;desk.hidden=!showingDesk;document.querySelectorAll('.nav-item[data-view]').forEach(el=>{if(!showingDesk){el.classList.remove('active');el.removeAttribute('aria-current');}});}
 document.addEventListener('liberty-view-change',view);window.addEventListener('hashchange',view);view();
})();
