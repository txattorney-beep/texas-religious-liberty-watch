'use strict';
const rulingCards=[...document.querySelectorAll('[data-ruling]')];
const rulingControls=Object.fromEntries(['search','group','state','topic','kind','period'].map(id=>[id,document.querySelector('#ruling-'+id)]));
let rulingView='checked';
function filterRulings(){
 const q=rulingControls.search.value.trim().toLowerCase();let shown=0;
 const windowEnd=document.querySelector('.ruling-filters').dataset.windowEnd;
 const cutoff=rulingControls.period.value?new Date(Date.parse(windowEnd+'T12:00:00Z')-Number(rulingControls.period.value)*86400000).toISOString().slice(0,10):'';
 for(const card of rulingCards){
  const d=card.dataset;
  const match=d.review===rulingView&&(!cutoff||d.date>=cutoff)&&(!q||d.search.toLowerCase().includes(q))&&(!rulingControls.group.value||d.group===rulingControls.group.value)&&(!rulingControls.state.value||d.state===rulingControls.state.value)&&(rulingView==='match'||(!rulingControls.topic.value||d.topics.split('|').includes(rulingControls.topic.value))&&(!rulingControls.kind.value||d.kind===rulingControls.kind.value));
  card.hidden=!match;if(match)shown++;
 }
 document.querySelector('#ruling-count').textContent=`${shown} ${rulingView==='checked'?'source-checked entries':'opinion matches awaiting review'}`;
 document.querySelector('#ruling-empty').hidden=shown!==0;
}
function setRulingView(view){
 rulingView=view;
 for(const [id,mode] of [['checked','checked'],['matches','match']]){const b=document.querySelector('#ruling-'+id);b.classList.toggle('selected',view===mode);b.setAttribute('aria-pressed',String(view===mode));}
 for(const id of ['topic','kind'])rulingControls[id].disabled=view==='match';
 document.querySelector('#ruling-view-note').textContent=view==='checked'?'Case blurbs are checked against the linked decisions. Procedural orders and related civil-remedies decisions are identified separately.':'Automatically discovered opinions with search excerpts. Relevance and holdings have not yet been reviewed. Incidental keyword matches may appear.';
 filterRulings();
}
for(const control of Object.values(rulingControls))control.addEventListener(control.type==='search'?'input':'change',filterRulings);
document.querySelector('#ruling-checked').addEventListener('click',()=>setRulingView('checked'));
document.querySelector('#ruling-matches').addEventListener('click',()=>setRulingView('match'));
document.querySelector('#ruling-reset').addEventListener('click',()=>{Object.values(rulingControls).forEach(c=>c.value='');filterRulings();});
document.querySelector('#ruling-export').addEventListener('click',()=>{
 const cell=v=>'"'+String(v??'').replace(/^[=+@\-\t\r]/,"'$&").replace(/"/g,'""')+'"';
 const rows=[['Case','Court / docket','Date','Review status','Type','Summary or search context','Procedural context','Opinion URL']];
 for(const card of rulingCards.filter(c=>!c.hidden))rows.push([card.querySelector('h2').textContent,card.querySelector('.ruling-court').textContent,card.dataset.date,card.dataset.review==='checked'?'Source checked':'Unreviewed opinion match',card.dataset.kind,card.querySelector('.ruling-summary').textContent+(card.querySelector('blockquote')?' Search excerpt: '+card.querySelector('blockquote').textContent:''),card.querySelector('.ruling-status')?.textContent||'',card.querySelector('h2 a').href]);
 const url=URL.createObjectURL(new Blob(['\uFEFF'+rows.map(row=>row.map(cell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='religious-liberty-court-rulings.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
const stale=document.querySelector('#ruling-stale');stale.hidden=Date.now()-Date.parse(stale.dataset.updated)<=36*3600000;
if(location.hash){const card=document.getElementById(location.hash.slice(1));if(card?.dataset.review==='match')setRulingView('match');}
filterRulings();
