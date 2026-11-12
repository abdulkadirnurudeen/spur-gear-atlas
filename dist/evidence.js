import {readSaved,writeSaved} from './page-state.js';
const $=id=>document.getElementById(id);
const family={circle:'Circular',sector:'Rounded sector',superellipse:'Superellipse'};
export function showMaterial(m) {
  $('material-title').textContent=m.label;
  $('material-properties').textContent=`E ${m.E_GPa.toFixed(1)} GPa · Yield ${m.yieldMPa.toFixed(1)} MPa · Effective fatigue amplitude ${m.fatigueMPa.toFixed(3)} MPa at five million counted cycles.`;
  $('material-basis').textContent=m.reference?m.basis:`${m.corrected?'Source-corrected values. ':''}${m.basis} Property table checked in the original report: ${m.sourceTable}, PDF page ${m.sourcePage}.`;
  $('material-source').href=m.sourceUrl;
  $('material-source').textContent=m.reference?'Read the supporting research record':'Read the original material report';
}
export async function initializeEvidence() {
  const response=await fetch('data/coverage.json');if(!response.ok)throw new Error('Research index unavailable');
  const data=await response.json();
  const saved=readSaved('research');
  const initialTooth=data.toothCounts.some(c=>c.teeth===saved?.teeth)?saved.teeth:40;
  $('archive-teeth').innerHTML=data.toothCounts.map(c=>`<option value="${c.teeth}" ${c.teeth===initialTooth?'selected':''}>${c.teeth} teeth</option>`).join('');
  $('coverage-rows').innerHTML=data.toothCounts.map(c=>`<tr><th scope="row">${c.teeth}</th><td>${c.static||'Not retained'}</td><td>${c.fatigue||'Not retained'}</td><td>${c.roles.join('; ')}</td></tr>`).join('');
  function populateLayouts(preferred) {
    const rows=data.records.filter(r=>r.teeth===Number($('archive-teeth').value));
    $('archive-layout').innerHTML=[...new Set(rows.map(r=>r.layout))].map(layout=>`<option value="${layout}">${layout}</option>`).join('');
    if(rows.some(r=>r.layout===preferred))$('archive-layout').value=preferred;
    render();
  }
  function render() {
    const t=Number($('archive-teeth').value),layout=$('archive-layout').value;
    const rows=data.records.filter(r=>r.teeth===t&&r.layout===layout),summary=data.toothCounts.find(c=>c.teeth===t);
    writeSaved('research',{teeth:t,layout});
    $('archive-caption').textContent=`${t} teeth · ${family[rows[0]?.family]||''} · ${rows.length} saved response rows`;
    $('archive-role').textContent=[...new Set(rows.map(r=>r.role))].join('; ');
    $('archive-missing').textContent=!summary.static?'Only fatigue records are retained for this tooth count; no static result is inferred.':!summary.fatigue?'Only static records are retained for this tooth count; no fatigue result is inferred.':'Both response types exist in this tooth-count record. Some individual layouts have only one response type.';
    $('archive-rows').innerHTML=rows.map(r=>`<tr><td>${r.response==='static'?'Static':'Fatigue'}</td><td>${r.a.toPrecision(3)}</td><td>${r.b.toPrecision(3)}</td><td>${(r.retention*100).toFixed(3)}%</td><td><details><summary>Row ${r.sourceRow} · ${r.sourceSha256.slice(0,8)}…</summary><p>${r.sourceFile}</p><p>${r.construction}</p><p>Original source: ${r.originalSource}</p><p>SHA-256: ${r.sourceSha256}</p></details></td></tr>`).join('');
  }
  $('archive-teeth').addEventListener('change',populateLayouts);
  $('archive-layout').addEventListener('change',render);
  populateLayouts(saved?.layout);
}
