/* Shared, dependency-free search model; also exercised by Node tests. */
(function(root){
 const normalize=s=>String(s||'').toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/\b(hb|sb|hjr|sjr)\s+(\d+)/g,'$1$2').replace(/[^a-z0-9]+/g,' ').trim();
 const labels={bills:'Bills',rulings:'Court rulings',hearings:'Hearings',news:'News',pages:'Site pages'};
 function records(data){
  const out=[],add=(type,title,description,url,meta,extra='')=>{out.push({type,title,description:description||'',url,meta:meta||'',search:normalize([title,description,meta,extra].join(' '))});};
  for(const b of data.bills?.bills||[])add('bills',`${b.number}: ${b.title||b.summary?.title||b.caption}`,typeof b.summary==='string'?b.summary:[b.summary?.plainEnglish,b.relevance,b.caption].filter(Boolean).join(' '),`/#bill/${encodeURIComponent(b.id)}`,[b.author,b.reviewState,b.actionDate].filter(Boolean).join(' · '),(b.topics||[]).join(' '));
  for(const b of [...data.rulings?.rulings||[],...data.rulings?.matches||[]])add('rulings',b.name,b.summary||b.excerpt,b.sourceUrl,[b.court,b.date,b.reviewState].filter(Boolean).join(' '),[b.docket,...b.topics||[]].join(' '));
  for(const b of data.hearings?.events||[])add('hearings',b.committee,[b.timeAndDate,b.location,(b.relatedBills||[]).join(' '),b.status].filter(Boolean).join(' · '),`/hearings/#${encodeURIComponent(b.id)}`,[b.chamber,b.date].join(' '),(b.relatedBills||[]).map(id=>{const bill=(data.bills?.bills||[]).find(row=>row.id===id);return bill?[bill.number,bill.caption,bill.summary,...bill.topics||[]].join(' '):'';}).join(' '));
  for(const b of data.news?.items||[])add('news',b.title,b.publisher,b.url,[b.publisher,(b.publishedAt||'').slice(0,10),...(b.scopes||[])].join(' · '));
  for(const page of data.pages?.pages||[])add('pages',page.title,page.text,page.url,'Site information');
  if(!data.pages?.pages?.length){
  add('pages','About Eric A. Hudson','Commercial litigation, constitutional disputes, religious liberty, injunctions, appeals, Arambula Terrazas PLLC. Contact and selected media coverage.','/about/','Biography');
  add('pages','Religious liberty: the issues and sources','Religious freedom, First Amendment, free exercise, RFRA, RLUIPA, Texas Constitution, legislation and court decisions.','/religious-liberty/','Sources');
  add('pages','Install the 90R tracker','Install Liberty Watch on your phone. Save bills, private notes and watchlists.','/90r/install/','Phone app');
  }
  return out;
 }
 function search(rows,query,priority){
  const terms=[...new Set(normalize(query).split(' ').filter(Boolean))];if(!terms.length)return [];
  const neutral=new Set(['bill','bills','news','court','courts','ruling','rulings','hearing','hearings','the','and','of','in','a','on']);
  const meaningful=terms.filter(t=>!neutral.has(t));const required=meaningful.length?meaningful:terms;
  const has=(text,t)=>text.includes(t)||t.length>4&&t.endsWith('s')&&text.includes(t.slice(0,-1));
  return rows.map(row=>{const text=row.search+' '+normalize(labels[row.type]);if(!required.every(t=>has(text,t)))return null;const title=normalize(row.title);return {...row,score:terms.reduce((n,t)=>n+(has(title,t)?8:has(text,t)?2:0),0)};}).filter(Boolean).sort((a,b)=>(b.type===priority)-(a.type===priority)||b.score-a.score||a.title.localeCompare(b.title));
 }
 const api={normalize,records,search,labels};if(typeof module!=='undefined')module.exports=api;else root.LibertySearch=api;
})(typeof window==='undefined'?globalThis:window);
