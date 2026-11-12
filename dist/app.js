import {KM_PER_MILE,DEFAULT_CYCLES_PER_KM,mileageDecision} from './distance.js';
import {millingRecipes} from './milling-recipes.js';
import {recipeMarkup} from './recipe-ui.js';
import {initializeEvidence,showMaterial} from './evidence.js';
import {initializeDesign} from './design-ui.js';
import {readSaved,writeSaved,referenceSearch,legacyDestination} from './page-state.js';
import {DEFAULT, stateFromUrl, selectedCase, selectedRow, estimate, decision, carbonSummary, csvText, selectedMaterial, materialRow} from './model.js';

const $=id=>document.getElementById(id);
const names={circle:'Circular',sector:'Rounded sector',superellipse:'Superellipse'};
const pct=(n,d=1)=>(n*100).toFixed(d)+'%';
const f=(n,d=3)=>Number(n).toFixed(d);
let data, state, toastTimer;

function toast(message) { $('toast').textContent=message; $('toast').hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('toast').hidden=true,3500); }
async function copy(text, success) {
  try {
    if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
    else {
      const el=document.createElement('textarea');el.value=text;el.style.position='fixed';el.style.opacity='0';document.body.append(el);el.select();
      const ok=document.execCommand('copy');el.remove();if(!ok)throw new Error('Clipboard unavailable');
    }
    toast(success);
  } catch { toast('Clipboard access is unavailable. You can select and copy the text directly.'); }
}
function syncUrl() {
  if(!$('explorer')&&!$('carbon-chart'))return;
  writeSaved('reference',state);
  const url=new URL(location.href);
  for (const [key,value] of Object.entries(state)) url.searchParams.set(key,String(value));
  history.replaceState(null,'',url);
}
function citation() {
  return `Nurudeen, A. O. (2026). SpurAtlas: Geometry, Strength and Carbon Payback (Version ${data.release}). Zenodo. https://doi.org/10.5281/zenodo.24165269. Supporting numerical data: Supporting Finite-Element Fields and Regeneration Code for Perforated-Spur-Gear Strength Retention (Version 2.0.0). https://doi.org/${data.dataDoi}.`;
}
function gearSvg(c, hero=false) {
  const color=hero?'#d5dfc7':'#dce6d4';
  return `<svg viewBox="-128 -128 256 256" role="img" aria-label="Actual saved plan-view geometry for ${c.id}: ${c.teeth}-tooth ${names[c.family].toLowerCase()} layout with five openings and a 30 mm bore"><g stroke="#aab9a4" stroke-width=".35" stroke-dasharray="2 2"><path d="M-119 0H119M0-119V119"/><circle r="100" fill="none"/></g><path d="${c.geometryPath}" fill="${color}" fill-rule="evenodd" stroke="#35523d" stroke-width=".45"/><g fill="none" stroke="#82967c" stroke-width=".35"><circle r="100" stroke-dasharray="2 2"/><path d="M-100 109V120M100 109V120M-100 116H100"/><path d="M-100 116l4-1.6v3.2zM100 116l-4-1.6v3.2z" fill="#82967c"/></g><rect x="-20" y="112" width="40" height="9" fill="${hero?'#e9ede4':'#e9eee5'}"/><text x="0" y="118" text-anchor="middle" font-family="Arial,sans-serif" font-size="6" fill="#526a4e">Ø 200 mm</text></svg>`;
}
function retentionChart(c) {
  const compact=matchMedia('(max-width:620px)').matches;
  const response=state.response,rows=c.rows,W=compact?340:540,H=compact?250:285,L=compact?35:48,R=compact?10:18,T=20,B=47;
  const x=l=>L+l*(W-L-R),y=v=>T+(1.10-v)/1.10*(H-T-B);
  const reference=rows.map(r=>`${x(r.lambda)},${y(r[response].reference)}`).join(' ');
  const predicted=rows.map(r=>`${x(r.lambda)},${y(estimate(r,response,state.model))}`).join(' ');
  let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${response==='static'?'Static':'Fatigue'} safety-factor retention in percent across the five saved load mixtures. Exact selected values are given in the result table."><rect x="${x(state.lambda)-14}" y="${T}" width="28" height="${H-T-B}" fill="#edf2e8"/>`;
  for(const value of [0,.25,.5,.75,1]) svg+=`<line x1="${L}" x2="${W-R}" y1="${y(value)}" y2="${y(value)}" stroke="#e1e6dc" stroke-width="1"/><text x="${L-9}" y="${y(value)+4}" text-anchor="end" fill="#6b7769" font-family="Arial" font-size="12">${value*100}</text>`;
  for(const r of rows) svg+=`<text x="${x(r.lambda)}" y="${H-B+22}" text-anchor="middle" fill="#63745e" font-family="Arial" font-size="12">${r.lambda*100}%</text>`;
  svg+=`<text x="${L}" y="11" font-family="Arial" font-size="11" fill="#657660">Retention (%)</text><text x="${(L+W-R)/2}" y="${H-5}" text-anchor="middle" font-family="Arial" font-size="11" fill="#657660">Peak-torque reference share · λ</text><polyline points="${reference}" fill="none" stroke="#173e35" stroke-width="2"/><polyline points="${predicted}" fill="none" stroke="#bd522e" stroke-width="2" stroke-dasharray="6 4"/>`;
  for(const r of rows){const selected=r.lambda===state.lambda;svg+=`<circle cx="${x(r.lambda)}" cy="${y(r[response].reference)}" r="${selected?5:3}" fill="#173e35" stroke="white" stroke-width="1.2"><title>FE reference at ${r.lambda*100}% T: ${pct(r[response].reference,3)}</title></circle><rect x="${x(r.lambda)-3}" y="${y(estimate(r,response,state.model))-3}" width="6" height="6" fill="#bd522e" stroke="white" stroke-width="1"><title>Model estimate at ${r.lambda*100}% T: ${pct(estimate(r,response,state.model),3)}</title></rect>`;}
  return svg+'</svg>';
}
function renderAtlas() {
  if(!$('explorer'))return;
  const c=selectedCase(data,state),m=selectedMaterial(data,state),r=materialRow(selectedRow(c,state.lambda),m);
  document.querySelectorAll('[data-family]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.family===c.family)));
  const toothCounts=[...new Set(data.cases.filter(k=>k.family===c.family).map(k=>k.teeth))];
  $('teeth').innerHTML=toothCounts.map(t=>`<option value="${t}" ${t===c.teeth?'selected':''}>${t} teeth</option>`).join('');
  const options=data.cases.filter(k=>k.family===c.family&&k.teeth===c.teeth);
  $('layout').innerHTML=options.map(k=>`<option value="${k.id}" ${k.id===c.id?'selected':''}>${k.id} · ${pct(k.phi,1)}${k.teeth===42?' · r'+f(k.radialPosition,0):''}</option>`).join('');
  $('layout-help').textContent=c.teeth===42?'r is opening-centre radius in mm. Area fraction uses the study’s reference annulus.':'Saved contour sizes at 46 teeth. Area fraction uses the study’s reference annulus.';
  $('target').value=f(state.target,1);$('model').value=state.model;$('material').value=m.id;showMaterial(m);
  $('evidence-tag').textContent=m.reference?'Saved FE reference':'Material-scaled calculation';
  $('reference-heading').textContent=m.reference?'FE reference':'Scaled reference';
  $('scope-text').textContent=m.reference?'Original research reference':'Homogeneous material calculation';
  document.querySelectorAll('[data-lambda]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.lambda)===state.lambda)));
  document.querySelectorAll('[data-response]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.response===state.response)));
  $('case-id').textContent=`LAYOUT ${c.id} / ${c.teeth} TEETH`;
  $('case-title').textContent=names[c.family]+' opening';
  $('removed').textContent=pct(c.materialRemovalFraction);
  $('static-retention').textContent=pct(r.static.reference);
  $('fatigue-retention').textContent=pct(r.fatigue.reference);
  $('case-geometry').innerHTML=gearSvg(c);
  $('geometry-label').textContent=`${c.id} / FIVE OPENINGS`;
  $('geometry-caption').textContent=`Ø ${c.boreDiameter} bore · ${c.faceWidth} face width`;
  $('retention-chart').innerHTML=retentionChart(c);
  $('model-legend').textContent=state.response==='static'?`Model ${state.model} estimate`:'Fatigue model estimate';
  $('phi-value').textContent=pct(c.phi,2);
  $('ligament-value').textContent=f(c.ligamentMm,2)+' mm';
  $('mass-value').textContent=f(c.massRemovedKg,3)+' kg';
  $('factor-rows').innerHTML=['static','fatigue'].map(kind=>{
    const ref=r[kind],pred=estimate(r,kind,state.model),error=100*(pred/ref.reference-1);
    return `<tr><td>${kind==='static'?'Static · Model '+state.model:'Fatigue'}</td><td>${f(ref.referenceFactor)}</td><td>${f(pred*ref.solidFactor)}</td><td>${error>=0?'+':''}${f(error,2)}%</td></tr>`;
  }).join('');
  const d=decision(r,state.target,state.model),target=f(state.target,1);
  $('decision').classList.toggle('caution',!d.reference||!d.agreement);
  $('decision').querySelector('.decision-icon').textContent=d.reference&&d.agreement?'✓':'!';
  $('decision-title').textContent=d.reference?`Both ${m.reference?'saved FE':'material-scaled'} factors meet the ${target} target.`:`At least one ${m.reference?'saved FE':'material-scaled'} factor is below the ${target} target.`;
  $('decision-detail').textContent=`${d.agreement?'The model estimates give the same target decision.':'The model estimates give a different target decision; inspect both values above.'} ${m.reference?'Numerical comparison on the study mesh':'Calculated using published material properties and the homogeneous study assumptions'}; production fatigue capacity and further validation remain separate.`;
  $('sector-note').hidden=!(c.family==='sector'&&c.phi>=.55);
  $('compare-rows').innerHTML=data.cases.map(k=>{
    const row=materialRow(selectedRow(k,state.lambda),m),met=decision(row,state.target,state.model).reference;
    return `<tr class="${k.id===c.id?'active':''}"><td><button data-layout="${k.id}" aria-label="Inspect layout ${k.id}">${k.id} <svg class="icon" aria-hidden="true" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M4 16L16 4M4 4H16V16"/></svg></button></td><td>${names[k.family]}</td><td>${k.teeth}</td><td>${pct(k.materialRemovalFraction,2)}</td><td>${f(row.static.referenceFactor)}</td><td>${f(row.fatigue.referenceFactor)}</td><td><span class="target-tag ${met?'':'below'}">${met?'Both meet '+target:'Below '+target}</span></td></tr>`;
  }).join('');
  syncUrl();
}
function carbonChart(summaries) {
  const compact=matchMedia('(max-width:620px)').matches;
  const W=compact?360:690,H=compact?310:365,L=compact?43:58,R=compact?13:19,T=25,B=53;
  const miles=state.miles,cyclesPerMile=DEFAULT_CYCLES_PER_KM*KM_PER_MILE;
  if(!Number.isFinite(miles)||miles<0)throw new Error('Enter a finite, nonnegative service mileage.');
  const all=summaries.flatMap(s=>s.rows),tail=all.map(r=>r.initialKg-r.savingKgPerCycle*miles*cyclesPerMile);
  if(tail.some(v=>!Number.isFinite(v)))throw new Error('This mileage exceeds the finite calculation range. Enter a smaller value.');
  const lo=Math.min(-5,...tail),hi=Math.max(10,...all.map(r=>r.initialKg)),span=hi-lo;
  if(!Number.isFinite(span))throw new Error('This mileage exceeds the finite chart range. Enter a smaller value.');
  const x=n=>L+(miles?n/miles:0)*(W-L-R),y=n=>T+(hi-n)/span*(H-T-B);
  const number=n=>Math.abs(n)>=1e8?n.toExponential(1):n.toLocaleString('en-GB',{maximumFractionDigits:0});
  let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Calculated net climate emissions from zero to the designer's chosen ${number(miles)} miles. Solid lines show nominal manufacturing scenarios; shading covers the retained process scenarios.">`;
  for(let i=0;i<=5;i++){const n=lo+i/5*span;svg+=`<line x1="${L}" x2="${W-R}" y1="${y(n)}" y2="${y(n)}" stroke="#e2e6de"/><text x="${L-8}" y="${y(n)+4}" text-anchor="end" font-family="Arial" font-size="11" fill="#64715f">${number(n)}</text>`;}
  if(lo<0&&hi>0)svg+=`<line x1="${L}" x2="${W-R}" y1="${y(0)}" y2="${y(0)}" stroke="#62785a" stroke-width="1.3"/>`;
  for(let i=0;i<=(miles?5:0);i++){const n=miles*(i/5);svg+=`<line x1="${x(n)}" x2="${x(n)}" y1="${T}" y2="${H-B}" stroke="#e7e9e1"/><text x="${x(n)}" y="${H-B+23}" text-anchor="middle" font-family="Arial" font-size="11" fill="#64715f">${number(n)}</text>`;}
  const colors=['#5e7c3f','#bc683d'];
  summaries.forEach((summary,index)=>{
    const upper=[],lower=[];
    for(let i=0;i<=25;i++){const distance=miles*(i/25),values=summary.rows.map(r=>r.initialKg-r.savingKgPerCycle*distance*cyclesPerMile);upper.push(`${x(distance)},${y(Math.max(...values))}`);lower.push(`${x(distance)},${y(Math.min(...values))}`);}
    svg+=`<polygon points="${upper.concat(lower.reverse()).join(' ')}" fill="${colors[index]}" fill-opacity=".15"/><path d="M${x(0)},${y(summary.nominal.initialKg)}L${x(miles)},${y(summary.nominal.initialKg-summary.nominal.savingKgPerCycle*miles*cyclesPerMile)}" fill="none" stroke="${colors[index]}" stroke-width="2.3"/><circle cx="${x(miles)}" cy="${y(summary.nominal.initialKg-summary.nominal.savingKgPerCycle*miles*cyclesPerMile)}" r="3" fill="${colors[index]}"/>`;
  });
  return svg+`<line x1="${x(miles)}" x2="${x(miles)}" y1="${T}" y2="${H-B}" stroke="#6e7e65" stroke-dasharray="4 4"/><text x="${miles?x(miles)-8:x(0)+8}" y="${T+12}" text-anchor="${miles?'end':'start'}" font-family="Arial" font-size="11" fill="#607456">Chosen service mileage</text><text x="${(L+W-R)/2}" y="${H-7}" text-anchor="middle" font-family="Arial" font-size="12" fill="#64715f">Service mileage (miles)</text><text transform="translate(15,${(T+H-B)/2}) rotate(-90)" text-anchor="middle" font-family="Arial" font-size="12" fill="#64715f">Net emissions (kg CO₂e)</text></svg>`;
}
function renderCarbon(syncInput=true) {
  if(!$('carbon-chart'))return;
  $('carbon-layout').value=state.carbon;$('frv').value=String(state.frv);
  const summaries=['milling','wire'].map(route=>carbonSummary(data,state.carbon,state.frv,route));
  try{
    const cpm=DEFAULT_CYCLES_PER_KM*KM_PER_MILE,chart=carbonChart(summaries);
    if(syncInput)$('carbon-mileage').value=state.miles;
    summaries.forEach((summary,i)=>$(i?'wire-payback':'milling-payback').textContent=[summary.minPayback,summary.maxPayback].map(v=>(v*1e6/cpm).toLocaleString('en-GB',{maximumFractionDigits:0})).join('–'));
    $('carbon-chart').hidden=false;$('carbon-chart').innerHTML=chart;
    const flags=summaries.map((summary,i)=>{const d=mileageDecision(summary.nominal.paybackMillionCycles*1e6/cpm,state.miles);return `${i?'Wire EDM':'Milling'} nominal payback: ${d.paybackMiles.toLocaleString('en-GB',{maximumFractionDigits:0})} miles — ${d.status.toLowerCase()}.`;});
    $('carbon-mileage-status').textContent=flags.join(' ');
    $('carbon-description').textContent=`Lines show nominal processes; shading covers ${summaries[0].rows.length} milling and ${summaries[1].rows.length} wire-EDM scenarios at the selected fuel-saving value. Negative values favour perforation within the stated boundary. The chart ends at your chosen service mileage. The original exposure mapping is retained at ${(cpm).toFixed(3)} counted cycles per mile.`;
    $('original-milling-recipe').innerHTML=recipeMarkup(millingRecipes.originalCases[state.carbon].nominalMilling,{original:true});
    writeSaved('mileage',{miles:state.miles});syncUrl();
  }catch(error){$('carbon-mileage-status').textContent=error.message;$('carbon-chart').hidden=true;$('milling-payback').textContent='—';$('wire-payback').textContent='—';}
}
function downloadResult() {
  const c=selectedCase(data,state),m=selectedMaterial(data,state),r=materialRow(selectedRow(c,state.lambda),m),d=decision(r,state.target,state.model);
  const rows=[['Quantity','Value','Unit / context'],['Atlas','SpurAtlas','Research preview '+data.release],['Author',data.author,'ORCID '+data.orcid],['Layout',c.id,c.sourceCase],['Family',names[c.family],'Five openings'],['Tooth count',c.teeth,''],['Pitch diameter',c.pitchDiameter,'mm'],['Face width',c.faceWidth,'mm'],['Bore diameter',c.boreDiameter,'mm'],['Material condition',m.label,m.id],['Yield strength',m.yieldMPa,'MPa'],['Effective fatigue amplitude',m.fatigueMPa,'MPa'],['Material source',m.sourceUrl,m.reference?'Inherited study reference':'Original report'],['Material calculation basis',m.basis,'Uniform linear elasticity with fixed geometry, loads, nu and density'],['Opening fraction',c.phi,'opening area / reference annulus'],['Root-side ligament ratio',c.ligamentRatio,'ligament / whole tooth height'],['Minimum root-side ligament',c.ligamentMm,'mm'],['Material removed',c.materialRemovalFraction,'fraction of matching solid'],['Removed mass',c.massRemovedKg,'kg at density 7800 kg/m3'],['T reference load multiplier a',state.lambda,'a+b=1'],['P reference load multiplier b',1-state.lambda,'a+b=1'],['Required safety factor',state.target,''],['Static prediction model',state.model,state.model==='H'?'Secondary static model H with harmonic load combination':'Primary static model E with exponential load mixing']];
  for(const kind of ['static','fatigue']){
    const response=r[kind],pred=estimate(r,kind,state.model);
    rows.push([kind+' reference retention',response.reference,'fraction of solid'],[kind+' model retention',pred,'fraction of solid'],[kind+' reference safety factor',response.referenceFactor,m.reference?'saved FE-derived reference':'material-scaled calculation from reference FE'],[kind+' estimated safety factor',pred*response.solidFactor,'model estimate on matching solid reference'],[kind+' signed model error',100*(pred/response.reference-1),'percent']);
  }
  rows.push(['FE target comparison',d.reference?'Both factors meet target':'At least one factor below target','Numerical comparison, not production qualification'],['Model target comparison',d.predicted?'Both factors meet target':'At least one factor below target',''],['Fatigue reference exposure',data.fatigueReferenceCycles,'counted stress cycles; not measured component life'],['Supporting data','https://doi.org/'+data.dataDoi,'release '+data.dataRelease],['Source data SHA-256',data.sourceSha256['Code_S2/implementation/review_program/prospective/all_100_response_rows.csv'],'test response source'],['Selection URL',location.href,''],['Citation',citation(),'']);
  const blob=new Blob([csvText(rows)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`SpurAtlas_${c.id}_T${state.lambda*100}_FoS${state.target}.csv`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),5000);toast('Result download prepared with source, study scope and citation.');
}
const on=(id,event,handler)=>$(id)?.addEventListener(event,handler);
function bindShell(){
  on('open-fields','click',()=>$('fields-dialog').showModal());
  on('close-fields','click',()=>$('fields-dialog').close());
  on('fields-dialog','click',e=>{if(e.target===$('fields-dialog')){const rect=e.target.getBoundingClientRect();if(e.clientX<rect.left||e.clientX>rect.right||e.clientY<rect.top||e.clientY>rect.bottom)e.target.close();}});
  on('menu-toggle','click',()=>{const open=$('menu-toggle').getAttribute('aria-expanded')==='false';$('menu-toggle').setAttribute('aria-expanded',String(open));$('main-nav').classList.toggle('open',open);});
  on('main-nav','click',()=>{$('main-nav').classList.remove('open');$('menu-toggle').setAttribute('aria-expanded','false');});
}
function bind() {
  on('family-options','click',e=>{
    const button=e.target.closest('[data-family]');if(!button)return;
    const current=selectedCase(data,state),matching=data.cases.filter(c=>c.family===button.dataset.family);
    state.layout=(matching.find(c=>c.teeth===current.teeth)||matching[0]).id;renderAtlas();
  });
  on('teeth','change',e=>{const c=selectedCase(data,state);state.layout=data.cases.find(k=>k.family===c.family&&k.teeth===Number(e.target.value)).id;renderAtlas();});
  on('layout','change',e=>{state.layout=e.target.value;renderAtlas();});
  on('mixture','click',e=>{const b=e.target.closest('[data-lambda]');if(b){state.lambda=Number(b.dataset.lambda);renderAtlas();}});
  on('target','change',e=>{state.target=Number(e.target.value);renderAtlas();});
  on('model','change',e=>{state.model=e.target.value;renderAtlas();});
  on('material','change',e=>{state.material=e.target.value;renderAtlas();});
  on('response-tabs','click',e=>{const b=e.target.closest('[data-response]');if(b){state.response=b.dataset.response;renderAtlas();}});
  on('reset','click',()=>{state={...DEFAULT};renderAtlas();renderCarbon();toast('Atlas selection reset.');});
  on('compare-rows','click',e=>{const b=e.target.closest('[data-layout]');if(b){state.layout=b.dataset.layout;renderAtlas();$('explorer').scrollIntoView({behavior:'smooth',block:'start'});}});
  on('carbon-layout','change',e=>{state.carbon=e.target.value;renderCarbon();});
  on('frv','change',e=>{state.frv=Number(e.target.value);renderCarbon();});
  on('carbon-mileage','input',e=>{state.miles=e.target.value.trim()===''?NaN:Number(e.target.value);renderCarbon(false);});
  on('export-result','click',downloadResult);
  on('copy-link','click',()=>copy(location.href,'Selection link copied.'));
  on('copy-citation','click',()=>copy(citation(),'Citation copied.'));
}
function renderPageContext(){
  if(!$('current-design-link'))return;
  const saved=readSaved('design'),c=data?.cases.find(c=>c.id===saved?.selectedId);
  $('current-design-link').textContent=c?`Return to design · ${c.teeth} teeth · ${c.id}`:'Start a design comparison';
}
async function init() {
  const legacy=legacyDestination(location.pathname,location.search,location.hash);
  if(legacy){location.replace(legacy);return;}
  bindShell();
  try {
    const response=await fetch('data/atlas.json');if(!response.ok)throw new Error('Data response '+response.status);
    data=await response.json();state=stateFromUrl(referenceSearch(location.search,readSaved('reference')),data);
    const mileage=readSaved('mileage');if(!new URLSearchParams(location.search).has('miles')&&Number.isFinite(mileage?.miles))state.miles=mileage.miles;
    if($('material'))$('material').innerHTML=data.materials.map(m=>`<option value="${m.id}">${m.label}</option>`).join('');
    if($('archive-teeth'))await initializeEvidence();
    if($('hero-geometry'))$('hero-geometry').innerHTML=gearSvg(data.cases[0],true);
    if($('citation-text'))$('citation-text').textContent=citation();
    renderAtlas();renderCarbon();renderPageContext();bind();
    if($('explorer'))$('explorer').setAttribute('aria-busy','false');
    if($('design-form'))initializeDesign(data,()=>({...state}),{saved:readSaved('design'),save:value=>{writeSaved('design',value);renderPageContext();}}).catch(error=>{console.error('Engineering workflow loading failed',error);$('design-loading').textContent='The engineering evidence could not be loaded. Reload to try again.';});
  } catch (error) {
    console.error('Atlas loading failed',error);
    if($('page-error'))$('page-error').hidden=false;
    if($('load-error'))$('load-error').hidden=false;
    if($('explorer'))$('explorer').hidden=true;
  }
}
window.addEventListener('resize',()=>{if(data&&state){if($('retention-chart'))$('retention-chart').innerHTML=retentionChart(selectedCase(data,state));if($('carbon-chart')&&!$('carbon-chart').hidden)$('carbon-chart').innerHTML=carbonChart(['milling','wire'].map(route=>carbonSummary(data,state.carbon,state.frv,route)));}});
on('retry','click',()=>location.reload());
on('page-retry','click',()=>location.reload());
init();
