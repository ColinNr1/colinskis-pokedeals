/* Colinskis PokeDeals — Budget Allocator V3.1 (single-store aware + live denylist) */
(()=>{
const money=n=>`€${Number(n||0).toFixed(2)}`;
const BAD_LISTINGS=[
  {product:'first-partner-s3',store:'Gamebreaker'},
];
function isBadListing(p,x){return BAD_LISTINGS.some(b=>p?.id===b.product&&x?.store===b.store)}
function packs(p){
  const verified=Number(p.pack_count||0); if(verified>0)return verified;
  const n=(p.name||'').toLowerCase(), t=(p.type||'').toLowerCase();
  let m=n.match(/\((\d+)\s*(?:packs?|boosters?)\)/i)||n.match(/(\d+)\s*(?:packs?|boosters?)/i); if(m)return +m[1];
  if(/half booster box/.test(n)||/half booster box/.test(t))return 18;
  if(/booster box/.test(n)||/booster box/.test(t))return 36;
  if(/booster bundle/.test(n)||/booster bundle/.test(t))return 6;
  if(/3[- ]pack|three[- ]pack/.test(n)||/3[- ]pack/.test(t))return 3;
  if(/booster pack|sleeved booster/.test(n)||/booster pack|sleeved booster/.test(t))return 1;
  return 0;
}
function verifiedListings(p){
  return (p.listings||[]).filter(x=>!isBadListing(p,x) && +x.price>0 && x.live_verified===true && x.price_verified===true && x.stock_verified===true);
}
function listingForStore(p,store){
  const ls=verifiedListings(p);
  if(store && store!=='__all__') return ls.filter(x=>x.store===store).sort((a,b)=>+a.price-+b.price)[0]||null;
  return ls.slice().sort((a,b)=>+a.price-+b.price)[0]||null;
}
function setMap(raw){return raw?.sets||raw||{}}
function pullScore(p,raw){const pulls=setMap(raw),s=pulls?.[p.set];if(!s)return 0; const arr=s.top_pulls||[]; if(!arr.length)return 0; const vals=arr.map(x=>+x.price||+x.avg7||0).filter(Boolean); if(!vals.length)return 0; const top=Math.max(...vals), depth=vals.slice(0,5).reduce((a,b)=>a+b,0)/Math.min(5,vals.length); return Math.min(100,Math.round(22*Math.log10(1+top)+12*Math.log10(1+depth)));}
function score(p,price,mode,pulls){const pc=packs(p); if(!isFinite(price)||!pc)return -1; const cm=+p.cm||price, deal=Math.max(0,Math.min(100,50+(cm-price)/Math.max(cm,.01)*250)), pp=pullScore(p,pulls), sealed=+p.potential||50, efficiency=Math.max(0,Math.min(100,100-(price/pc-4.5)*14)); if(mode==='boosters')return pc/price*100; if(mode==='value')return deal*.7+efficiency*.3; if(mode==='pull')return pp*.7+efficiency*.3; if(mode==='sealed')return sealed*.75+deal*.25; return deal*.3+pp*.25+sealed*.25+efficiency*.2;}
function allocate(products,budget,mode,dupes,pulls,store){
  let left=budget,out=[];
  const candidates=products.map(p=>{const listing=listingForStore(p,store); const price=listing?+listing.price:Infinity; return {p,listing,price,pc:packs(p),s:score(p,price,mode,pulls)}}).filter(x=>x.listing&&x.s>=0&&x.price<=budget).sort((a,b)=>b.s-a.s);
  let guard=0; while(guard++<200){const fit=candidates.filter(x=>x.price<=left&&(dupes||!out.some(o=>o.p.id===x.p.id))); if(!fit.length)break; let x=fit[0]; if(mode==='boosters')x=fit.slice().sort((a,b)=>(b.pc/b.price)-(a.pc/a.price))[0]; out.push(x);left-=x.price;} return {out,left};
}
function bestSingleStore(products,budget,mode,dupes,pulls,stores){
  let best={out:[],left:budget,store:null,utility:-Infinity};
  for(const store of stores){const r=allocate(products,budget,mode,dupes,pulls,store);const spent=budget-r.left,total=r.out.reduce((a,x)=>a+x.pc,0),avgScore=r.out.length?r.out.reduce((a,x)=>a+x.s,0)/r.out.length:0;const utility=(mode==='boosters'?total*20:avgScore*2)+spent/Math.max(1,budget)*20+total*.4;if(r.out.length&&utility>best.utility)best={...r,store,utility};}
  return best;
}
function removeDeniedCards(){
  document.querySelectorAll('.card').forEach(card=>{
    const h=card.querySelector('h3'); if(!h)return;
    const title=h.textContent.trim();
    if(title==='First Partner Illustration Collection – Series 3' || title==='First Partner Illustration Collection - Series 3') card.remove();
  });
}
function applyPackBadges(products){removeDeniedCards();document.querySelectorAll('.card').forEach(card=>{const h=card.querySelector('h3');if(!h)return;const p=products.find(x=>x.name===h.textContent.trim());if(!p)return;const pc=packs(p),ls=verifiedListings(p),bp=ls.length?Math.min(...ls.map(x=>+x.price)):Infinity;if(!pc||!isFinite(bp)||card.querySelector('.packintel'))return;const d=document.createElement('div');d.className='packintel';d.innerHTML=`<b>${pc} booster${pc===1?'':'s'}</b><span>from ${money(bp/pc)} / booster</span>`; const body=card.querySelector('.body')||card;body.insertBefore(d,body.querySelector('.prices')||null);});}
async function init(){let cat,pulls={}; try{cat=await fetch('data/catalog.json?b='+Date.now(),{cache:'no-store'}).then(r=>r.json()); pulls=await fetch('data/pulls.json?b='+Date.now(),{cache:'no-store'}).then(r=>r.json());}catch(e){return}
 const products=(cat.products||[]).filter(p=>verifiedListings(p).length);
 const stores=[...new Set(products.flatMap(p=>verifiedListings(p).map(x=>x.store)).filter(Boolean))].sort();
 removeDeniedCards();applyPackBadges(products);let badgeTimer=setInterval(()=>applyPackBadges(products),500);setTimeout(()=>clearInterval(badgeTimer),12000);
 const observer=new MutationObserver(()=>{removeDeniedCards();applyPackBadges(products)});const grid=document.querySelector('#grid');if(grid)observer.observe(grid,{childList:true,subtree:true});
 if(document.querySelector('.budget-fab'))return;
 const btn=document.createElement('button');btn.className='budget-fab';btn.textContent='Budget Allocator';document.body.appendChild(btn);
 const modal=document.createElement('div');modal.className='budget-modal';modal.innerHTML=`<div class="budget-panel"><button class="budget-x">×</button><div class="budget-kicker">POKEDEALS BUY ENGINE</div><h2>Budget Allocator</h2><p>Build a buy from one Malta store so you do not have to drive across the island. Only currently verified listings are used.</p><div class="budget-controls"><label>Budget €<input id="baBudget" type="number" min="5" step="5" value="100"></label><label>Goal<select id="baMode"><option value="balanced">Balanced</option><option value="boosters">Most Boosters</option><option value="value">Best Value</option><option value="pull">Best Pull Potential</option><option value="sealed">Best Sealed Potential</option></select></label><label>Store<select id="baStore"><option value="__best_single__">Best single store</option>${stores.map(s=>`<option value="${s.replace(/"/g,'&quot;')}">${s}</option>`).join('')}<option value="__all__">Across all Malta</option></select></label><label class="ba-check"><input id="baDupes" type="checkbox"> Duplicates allowed</label><button id="baRun">Build my buy</button></div><div id="baResult"></div></div>`;document.body.appendChild(modal);
 function run(){const b=Math.max(0,+document.querySelector('#baBudget').value||0),mode=document.querySelector('#baMode').value,dupes=document.querySelector('#baDupes').checked,storeChoice=document.querySelector('#baStore').value;let result=storeChoice==='__best_single__'?bestSingleStore(products,b,mode,dupes,pulls,stores):allocate(products,b,mode,dupes,pulls,storeChoice);const {out,left}=result,spent=b-left,total=out.reduce((a,x)=>a+x.pc,0),usedStores=[...new Set(out.map(x=>x.listing.store))];const storeLabel=result.store|| (storeChoice==='__all__'?'Across Malta':storeChoice);document.querySelector('#baResult').innerHTML=out.length?`<div class="ba-summary"><div><b>${money(spent)}</b><span>spent</span></div><div><b>${total}</b><span>boosters</span></div><div><b>${total?money(spent/total):'—'}</b><span>avg / booster</span></div><div><b>${money(left)}</b><span>left</span></div></div><div class="ba-storeline"><b>${storeLabel}</b><span>${usedStores.length} store${usedStores.length===1?'':'s'} used</span></div><div class="ba-list">${out.map((x,i)=>`<div class="ba-row"><strong>${i+1}. ${x.p.name}</strong><span>${x.pc} boosters · ${money(x.price)} · ${money(x.price/x.pc)}/booster</span><small>${x.listing.store}${x.p.set?` · ${x.p.set}`:''}${mode==='pull'?` · Pull score ${pullScore(x.p,pulls)}/100`:''}</small></div>`).join('')}</div>`:`<div class="ba-empty">No currently verified product with a known pack count fits this budget/store.</div>`;}
 btn.onclick=()=>{modal.classList.add('open');run()};modal.querySelector('.budget-x').onclick=()=>modal.classList.remove('open');modal.onclick=e=>{if(e.target===modal)modal.classList.remove('open')};modal.querySelector('#baRun').onclick=run;modal.querySelector('#baMode').onchange=run;modal.querySelector('#baStore').onchange=run;modal.querySelector('#baDupes').onchange=run;modal.querySelector('#baBudget').oninput=()=>{clearTimeout(window.__baT);window.__baT=setTimeout(run,180)};
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(init,350));else setTimeout(init,350);
})();
