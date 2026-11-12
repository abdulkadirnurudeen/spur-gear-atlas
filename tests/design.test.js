import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {defaults,operatingPoint,assessRequirements,shortlist,interval,carbonDefaults,manufacturingScenario,matchedCarbon,makeReport} from '../dist/design-model.js';
import {printable} from '../dist/design-ui.js';
const read=p=>JSON.parse(readFileSync(new URL(p,import.meta.url)));
const data=read('../dist/data/atlas.json'),engineering=read('../dist/data/engineering.json');
const req={...defaults,...operatingPoint(data,.5)};
const close=(a,b)=>assert.ok(Math.abs(a-b)<=Math.max(1e-10,Math.abs(b)*2e-12),`${a} != ${b}`);

test('gear matching rejects unsupported dimensions, loads, life and malformed inputs',()=>{
 assert.equal(assessRequirements(data,req).supported,true);
 for(const variant of [{teeth:32},{teeth:42.5},{pitchDiameter:201},{faceWidth:31},{boreDiameter:31},{pressureAngle:21},{torqueNm:250},{speedRpm:2000},{cycles:1e6},{material:'unknown'},{epsilon:1},{epsilon:-.01},{torqueNm:NaN},{lambda:.37},{model:'other'},{family:'unknown'}]){
  const result=shortlist(data,{...req,...variant});assert.equal(result.coverage.supported,false,JSON.stringify(variant));assert.equal(result.rows.length,0);assert.equal(result.recommended,null);
 }
});
test('shortlists preserve fixed gear compatibility, target outcomes and all mixtures',()=>{
 const a=shortlist(data,req);assert.equal(a.rows.length,4);assert.equal(a.recommended,'G03');assert.ok(a.rows.every(r=>r.teeth===42));
 const high=shortlist(data,{...req,fatigueTarget:6});assert.equal(high.recommended,null);assert.ok(high.rows.some(r=>r.meetsReference&&!r.meetsConditional));
 const b=shortlist(data,{...req,teeth:46,allMixtures:true});assert.equal(b.rows.length,6);assert.ok(b.rows.every(r=>r.chosen.length===5));assert.equal(b.rows.find(r=>r.id==='G08').referral,true);assert.notEqual(b.recommended,'G08');
 const family=shortlist(data,{...req,teeth:46,family:'superellipse'});assert.equal(family.rows.length,2);assert.ok(family.rows.every(r=>r.family==='superellipse'));
});
test('conditional interval reproduces the retained H decision audit without treating it as a guarantee',()=>{
 for(const summary of engineering.sensitivityAudit.results){
  const count={eligible:0,ineligible:0,requires_FE:0,overstated_eligibility:0,missed_eligibility:0};
  for(const c of data.cases)for(const row of c.rows)for(const kind of ['static','fatigue']){
   const factor=(kind==='static'?row.static.estimateH:row.fatigue.estimate)*row[kind].solidFactor,ref=row[kind].referenceFactor;
   const band=interval(factor,summary.tolerance);
   for(let i=0;i<10;i++){const target=1.5+.5*i,status=band.lower>=target?'eligible':band.upper<target?'ineligible':'requires_FE';count[status]++;count.overstated_eligibility+=Number(status==='eligible'&&ref<target);count.missed_eligibility+=Number(status==='ineligible'&&ref>=target);}
  }
  for(const k of Object.keys(count))assert.equal(count[k],summary[k],`${summary.tolerance} ${k}`);
 }
});
test('new JavaScript carbon calculation matches 60 independently computed archived-Python fixtures',()=>{
 for(const fixture of read('./multitool-reference-fixtures.json')){
  const c=data.cases.find(c=>c.id===fixture.layout),s={...carbonDefaults,grid:fixture.grid};
  const r=manufacturingScenario(c,s,engineering.carbonCoefficients,fixture.method),ref=fixture.manufacturing;
  for(const[a,b]of [['massRemovedKg','mass_removed_kg'],['activeMinutes','active_minutes'],['siteElectricityKWh','site_electricity_delta_kWh'],['upfrontKgCO2e','initial_climate_delta_kg_CO2e']])close(r[a],ref[b]);
  const carbon=matchedCarbon(c,s,engineering).find(r=>r.method===fixture.method);close(carbon.breakEvenKm,fixture.road.break_even_km);close(carbon.netKgCO2e,fixture.road.climate_delta_kg_CO2e_during_test);
 }
});
test('carbon records handle zero savings, omitted burdens, exposure and unsuitable tools',()=>{
 const c=data.cases.find(c=>c.id==='G03');
 assert.ok(matchedCarbon(c,{...carbonDefaults,frv:0},engineering).every(r=>r.breakEvenKm===null));
 const a=matchedCarbon(c,carbonDefaults,engineering),b=matchedCarbon(c,{...carbonDefaults,extraBurden:4},engineering);close(b[0].netKgCO2e-a[0].netKgCO2e,4);
 assert.equal(matchedCarbon(c,{...carbonDefaults,distanceKm:1e6},engineering)[0].withinReferenceExposure,false);
 assert.throws(()=>matchedCarbon(c,{...carbonDefaults,cutterMm:12},engineering),/geometry-checked/);
 for(const s of [{frv:-1},{savingFraction:1.1},{grid:NaN},{efficiency:0},{radialEngagementMm:11}])assert.throws(()=>matchedCarbon(c,{...carbonDefaults,...s},engineering));
});
test('all case evidence is bound to the right mesh, source hashes and geometry exports',()=>{
 assert.equal(Object.keys(engineering.cases).length,10);
 for(const c of data.cases){const e=engineering.cases[c.id];assert.equal(e.sourceCase,c.sourceCase);assert.equal(e.geometry.mesh_sha256,e.meshAudit.mesh_sha256);assert.equal(e.regionalStressByTooth.length,c.teeth);assert.equal(e.meshAudit.status,'PASS');assert.ok(e.minimumSampledOpeningCurvatureRadiusMm>0);assert.equal(e.meshAudit.unexpected_internal_exposed_faces,0);
  for(const suffix of ['.svg','.dxf','-coordinates.csv','-evidence.json'])assert.ok(existsSync(new URL('../dist/data/cases/'+c.id+suffix,import.meta.url)));
  assert.ok(e.fieldPlot.regionalRecoveryMaximumRelativeDiscrepancy<2e-9);assert.equal(e.fieldPlot.newElasticitySolve,false);
  assert.equal(e.fieldPlot.imageSha256,createHash('sha256').update(readFileSync(new URL('../dist/'+e.fieldPlot.image,import.meta.url))).digest('hex'));
 }
 const provenance=read('../dist/data/provenance.json');assert.equal(provenance.atlasJsonSha256,createHash('sha256').update(readFileSync(new URL('../dist/data/atlas.json',import.meta.url))).digest('hex'));
});
test('reproducible reports retain unsupported outcomes and never manufacture missing evidence',()=>{
 const result=shortlist(data,req),report=makeReport(data,engineering,req,result,result.recommended,carbonDefaults,'Sample');
 assert.equal(report.tool,'SpurAtlas');assert.equal(report.geometry.teeth,42);assert.equal(report.evidence.sourceCase,report.geometry.sourceCase);assert.equal(report.allCompatibleResults.length,4);assert.equal(report.matchedCarbon.length,2);assert.match(report.assessmentStatus.toothRootRating,/not calculated/);assert.match(report.assessmentStatus.uncertainty,/No calibrated/);
 const outside={...req,teeth:32},r=shortlist(data,outside),missing=makeReport(data,engineering,outside,r,null,carbonDefaults);
 assert.equal(missing.geometry,null);assert.equal(missing.evidence,null);assert.equal(missing.matchedCarbon,null);assert.equal(missing.coverage.supported,false);
});
test('printable reports escape project text and retain self-contained field evidence',()=>{
 const r=shortlist(data,req),report=makeReport(data,engineering,req,r,r.recommended,carbonDefaults,'<script>unsafe()</script>');
 const html=printable(report,data,engineering,'data:image/png;base64,QA');
 assert.ok(html.includes('&lt;script&gt;unsafe()&lt;/script&gt;'));assert.ok(!html.includes('<script>unsafe()'));
 assert.ok(html.includes('data:image/png;base64,QA'));assert.ok(html.includes('ISO 6336 tooth-root bending rating not calculated'));assert.ok(html.includes(report.evidence.geometry.mesh_sha256));
});
