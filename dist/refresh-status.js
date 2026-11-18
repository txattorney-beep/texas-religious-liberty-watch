(() => {
 const names={bills:'Bills',news:'News',hearings:'Hearings',rulings:'Court opinions'};
 const format=new Intl.DateTimeFormat('en-US',{timeZone:'America/Chicago',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'});
 const localParts=d=>Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'America/Chicago',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(d).map(p=>[p.type,p.value]));
 function windowKey(d){const p=localParts(d),minutes=+p.hour*60+(+p.minute);if(minutes<450){const yesterday=new Date(Date.UTC(+p.year,+p.month-1,+p.day-1));return yesterday.toISOString().slice(0,10)+' 16:30';}const date=`${p.year}-${p.month}-${p.day}`;return `${date} ${minutes>=990?'16:30':minutes>=450?'07:30':'00:00'}`;}
 async function update(){
  const box=document.createElement('aside');box.id='refresh-health';box.setAttribute('role','status');box.style.cssText='margin:12px auto;padding:10px 16px;max-width:1180px;border:1px solid #ccc;font-size:14px;line-height:1.5';
  const target=document.querySelector('main');if(!target)return;target.prepend(box);
  try{
   const response=await fetch('/data/refresh-health.json',{cache:'no-store'});if(!response.ok)throw Error();const data=await response.json();
   const lines=Object.entries(names).map(([key,label])=>{const s=data.feeds[key];if(!s)return `${label}: status unavailable`;const last=s.lastSuccessAt?new Date(s.lastSuccessAt):null;const overdue=last&&windowKey(last)<windowKey(new Date());return `${label}: ${s.status==='archived'?'archived':s.status!=='ok'?'partial or failed check; previous records retained':overdue?'scheduled refresh overdue':'checked successfully'}${last?' · last successful check '+format.format(last):''}`;});
   box.textContent='Scheduled checks: 7:30 a.m. and 4:30 p.m. Central. '+lines.join(' | ');
  }catch{box.textContent='Refresh status unavailable. Displayed records may be from a previous snapshot.';}
 }
 update();
})();
