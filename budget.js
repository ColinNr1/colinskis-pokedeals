/* Colinskis PokeDeals — Budget Allocator V2 */
(()=>{
const money=n=>`€${Number(n||0).toFixed(2)}`;
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
function bestPrice(p){return Math.min(...(p.listings||[]).map(x=>+x.price).filter(x=>x>0),Infinity)}
function setMap(raw){return raw?.sets||raw||{}}
function pullScore(p,raw){const pulls=setMap(raw),s=pulls?.[p.set];if(!s)return 0; const arr=s.top_pulls||[]; if(!arr.length)return 0; const vals=arr.map(x=>+x.price||+x.avg7||0).filter(Boolean); if(!vals.length)return 0; const top=Math.max(...vals), depth=vals.slice(0,5).reduce((a,b)=>a+b,0)/Math.min(5,vals.length); return Math.min(100,Math.round(22*Math.log10(1+top)+12*Math.log10(1+depth)));}
function score(p,mode,pulls){const price=bestPrice(p), pc=packs(p); if(!isFinite(price)||!pc)return -1; const cm=+p.cm||price, deal=Math.max(0,Math.min(100,50+(cm-price)/Math.max(cm,.01)*250)), pp=pullScore(p,pulls), sealed=+p.potential||50, efficiency=Math.max(0,Math.min(100,100-(price/pc-4.5)*14)); if(mode==='boosters')return pc/price*100; if(mode==='value')return deal*.7+efficiency*.3; if(mode==='pull')return pp*.7+efficiency*.3; if(mode==='sealed')return sealed*.75+deal*.25; return deal*.3+pp*.25+sealed*.25+efficiency*.2;}
function allocate(products,budget,mode,dupes,pulls){let left=budget,out=[]; const candidates=products.map(p=>({p,price:bestPrice(p),pc:packs(p),s:score(p,mode,pulls)})).filter(x=>x.s>=0&&x.price<=budget).sort((a,b)=>b.s-a.s); let guard=0; while(guard++<200){const fit=candidates.filter(x=>x.price<=left&&(dupes||!out.some(o=>o.p.id===x.p.id))); if(!fit.length)break; let x=fit[0]; if(mode==='boosters')x=fit.slice().sort((a,b)=>(b.pc/b.price)-(a.pc/a.price))[0]; out.push(x);left-=x.price;} return {out,left};}
function applyPackBadges(products){document.querySelectorAll('.card').forEach(card=>{const h=card.querySelector('h3');if(!h)return;const p=products.find(x=>x.name===h.textContent.trim());if(!p)return;const pc=packs(p),bp=bestPrice(p);if(!pc||!isFinite(bp)||card.querySelector('.packintel'))return;const d=document.createElement('div');d.className='packintel';d.innerHTML=`<b>${pc} booster${pc===1?'':'s'}</b><span>${money(bp/pc)} / booster</span>`; const body=card.querySelector('.body')||card;body.insertBefore(d,body.querySelector('.prices')||null);});}
async function init(){let cat,pulls={}; try{cat=await fetch('data/catalog.json?b='+Date.now(),{cache:'no-store'}).then(r=>r.json()); pulls=await fetch('data/pulls.json?b='+Date.now(),{cache:'no-store'}).then(r=>r.json());}catch(e){return}
 const products=(cat.products||[]).filter(p=>(p.listings||[]).some(x=>+x.price>0));
 applyPackBadges(products);let badgeTimer=setInterval(()=>applyPackBadges(products),700);setTimeout(()=>clearInterval(badgeTimer),7000);
 const observer=new MutationObserver(()=>applyPackBadges(products));const grid=document.querySelector('#grid');if(grid)observer.observe(grid,{childList:true,subtree:true});
 if(document.querySelector('.budget-fab'))return;
 const btn=document.createElement('button');btn.className='budget-fab';btn.textContent='Budget Allocator';document.body.appendChild(btn);
 const modal=document.createElement('div');modal.className='budget-modal';modal.innerHTML=`<div class="budget-panel"><button class="budget-x">×</button><div class="budget-kicker">POKEDEALS BUY ENGINE</div><h2>Budget Allocator</h2><p>Choose what you want to optimize. Unverified pack counts are excluded instead of guessed.</p><div class="budget-controls"><label>Budget €<input id="baBudget" type="number" min="5" step="5" value="100"></label><label>Goal<select id="baMode"><option value="balanced">Balanced</option><option value="boosters">Most Boosters</option><option value="value">Best Value</option><option value="pull">Best Pull Potential</option><option value="sealed">Best Sealed Potential</option></select></label><label class="ba-check"><input id="baDupes" type="checkbox"> Duplicates allowed</label><button id="baRun">Build my buy</button></div><div id="baResult"></div></div>`;document.body.appendChild(modal);
 function run(){const b=Math.max(0,+document.querySelector('#baBudget').value||0),mode=document.querySelector('#baMode').value,dupes=document.querySelector('#baDupes').checked,{out,left}=allocate(products,b,mode,dupes,pulls);const spent=b-left,total=out.reduce((a,x)=>a+x.pc,0);document.querySelector('#baResult').innerHTML=out.length?`<div class="ba-summary"><div><b>${money(spent)}</b><span>spent</span></div><div><b>${total}</b><span>boosters</span></div><div><b>${total?money(spent/total):'—'}</b><span>avg / booster</span></div><div><b>${money(left)}</b><span>left</span></div></div><div class="ba-list">${out.map((x,i)=>`<div class="ba-row"><strong>${i+1}. ${x.p.name}</strong><span>${x.pc} boosters · ${money(x.price)} · ${money(x.price/x.pc)}/booster</span><small>${x.p.set||''}${mode==='pull'?` · Pull score ${pullScore(x.p,pulls)}/100`:''}</small></div>`).join('')}</div>`:`<div class="ba-empty">No verified in-stock product with a known pack count fits this budget.</div>`;}
 btn.onclick=()=>{modal.classList.add('open');run()};modal.querySelector('.budget-x').onclick=()=>modal.classList.remove('open');modal.onclick=e=>{if(e.target===modal)modal.classList.remove('open')};modal.querySelector('#baRun').onclick=run;modal.querySelector('#baMode').onchange=run;modal.querySelector('#baDupes').onchange=run;modal.querySelector('#baBudget').oninput=()=>{clearTimeout(window.__baT);window.__baT=setTimeout(run,180)};
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(init,350));else setTimeout(init,350);
})();
