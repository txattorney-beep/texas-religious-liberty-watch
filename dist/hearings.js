'use strict';
const hearingCards=[...document.querySelectorAll('[data-hearing]')];
const hearingSearch=document.querySelector('#hearing-search');
const hearingChamber=document.querySelector('#hearing-chamber');
const hearingPeriod=document.querySelector('#hearing-period');
const hearingWatch=document.querySelector('#hearing-watch');
const hearingToday=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Chicago',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
let hearingSaved=[];
try { const local=JSON.parse(localStorage.getItem('texas-liberty-watch-90r-v1')); if(Array.isArray(local?.saved))hearingSaved=local.saved; } catch {}
const requestedBill=new URLSearchParams(location.search).get('bill');
if(requestedBill && /^(HB|SB|HJR|SJR|HCR|SCR|HR|SR)\d+$/.test(requestedBill)){hearingSearch.value=requestedBill;hearingPeriod.value='all';}
function filterHearings(){
 const query=hearingSearch.value.trim().toLowerCase();const compact=query.replace(/\s/g,'');
 const terms=query.split(/\s+/).filter(Boolean);
 let shown=0;
 for(const card of hearingCards){
  const bills=card.dataset.bills.split(' ');const period=hearingPeriod.value;
  const date=card.dataset.date,status=card.dataset.status;
  const matches=(terms.every(term=>card.dataset.search.toLowerCase().includes(term))||bills.some(b=>b.toLowerCase()===compact))&&(!hearingChamber.value||card.dataset.chamber===hearingChamber.value)&&(!hearingWatch.checked||bills.some(b=>hearingSaved.includes(b)))&&(period==='all'||period==='upcoming'&&date>=hearingToday&&status!=='Canceled'||period==='past'&&date<hearingToday||period==='canceled'&&status==='Canceled');
  card.hidden=!matches;if(matches)shown++;
 }
 document.querySelector('#hearing-count').textContent=`${shown} notice${shown===1?'':'s'} matching this view`;
 document.querySelector('#hearing-filter-empty').hidden=shown!==0||hearingCards.length===0&&!hearingWatch.checked;
 document.querySelector('#hearing-empty-detail').textContent=hearingWatch.checked&&!hearingSaved.length?'Your watchlist is empty in this browser. Star bills in the tracker, then return here.':'Try all notices, another bill, or a different chamber.';
}
hearingSearch.addEventListener('input',filterHearings);
document.querySelector('#hearing-search-form').addEventListener('submit',event=>{
 event.preventDefault();
 filterHearings();
});
for(const control of [hearingChamber,hearingPeriod,hearingWatch])control.addEventListener('change',filterHearings);
document.querySelector('#hearing-reset').addEventListener('click',()=>{hearingSearch.value='';hearingChamber.value='';hearingPeriod.value='all';hearingWatch.checked=false;filterHearings();});
document.querySelector('#hearing-export').addEventListener('click',()=>{
 const cell=value=>'"'+String(value??'').replace(/^[=+@\-\t\r]/,"'$&").replace(/"/g,'""')+'"';
 const rows=[['Bills','Committee','Chamber','Date','Official time/date','Location','Status','Notice URL']];
 for(const card of hearingCards.filter(c=>!c.hidden)){const facts=[...card.querySelectorAll('dd')].map(el=>el.textContent);rows.push([card.dataset.bills,card.querySelector('h2').textContent,card.dataset.chamber,...facts,card.dataset.status,card.querySelector('.hearing-links a').href]);}
 const url=URL.createObjectURL(new Blob(['\uFEFF'+rows.map(row=>row.map(cell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='texas-90r-hearings.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
const stale=document.querySelector('#hearing-stale');stale.hidden=Date.now()-Date.parse(stale.dataset.updated)<=36*3600000;
filterHearings();
