import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {productionCapacityRequirement,defaults,operatingPoint,shortlist,makeReport,carbonDefaults} from '../dist/design-model.js';
import {productionCapacityMarkup,printable} from '../dist/design-ui.js';
const data=JSON.parse(readFileSync(new URL('../dist/data/atlas.json',import.meta.url))),eng=JSON.parse(readFileSync(new URL('../dist/data/engineering.json',import.meta.url)));
const close=(a,b)=>assert.ok(Math.abs(a-b)<Math.max(1e-12,Math.abs(b)*1e-12),`${a} != ${b}`);

test('minimum production capacity reproduces the manuscript examples without clipping requirements above unity',()=>{
 const request={fatigueTarget:1.5,epsilon:.1};
 let r=productionCapacityRequirement({referenceFatigue:5.890,lowerFatigue:5},request);close(r.minimumRetainedFraction,1.5/5.89);close(r.minimumRetainedFractionWithAssumedError,.3);
 r=productionCapacityRequirement({referenceFatigue:1.500046,lowerFatigue:1.4},request);close(r.minimumRetainedFraction,.9999693342737488);assert.ok(r.minimumRetainedFractionWithAssumedError>1);
 assert.equal(r.measuredMillingCapacityFraction,null);assert.equal(r.measuredWireEdmCapacityFraction,null);
 assert.equal(productionCapacityRequirement(null,request),null);
 for(const x of [0,NaN,Infinity,-1])assert.throws(()=>productionCapacityRequirement({referenceFatigue:x,lowerFatigue:1},request));
});

test('capacity follows the selected material, target and full load-mixture requirement at the fixed reference exposure',()=>{
 for(const allMixtures of [false,true])for(const material of ['reference','SAE8620_core121_research']){
  const request={...defaults,...operatingPoint(data,.5),teeth:46,allMixtures,material},result=shortlist(data,request),selected=result.rows.find(r=>r.id==='G07');
  const report=makeReport(data,eng,request,result,'G07',carbonDefaults);const p=report.productionCapacity;
  close(p.minimumRetainedFraction,request.fatigueTarget/selected.referenceFatigue);close(p.minimumRetainedFractionWithAssumedError,request.fatigueTarget/selected.lowerFatigue);
  const rows=selected.chosen;close(p.minimumRetainedFraction,Math.max(...rows.map(r=>request.fatigueTarget/r.fatigueReference)));
  assert.equal(p.referenceCycles,5000000);
  const distant=makeReport(data,eng,request,result,'G07',{...carbonDefaults,distanceKm:1e6});assert.deepEqual(distant.productionCapacity,p);
  assert.ok(distant.matchedCarbon.every(r=>!r.exceedsDesignerMileage));
 }
});

test('browser and printable report expose the same production requirement and preserve unmeasured route capacities',()=>{
 const request={...defaults,...operatingPoint(data,.5),teeth:46},result=shortlist(data,request),report=makeReport(data,eng,request,result,'G07',carbonDefaults),html=productionCapacityMarkup(report.productionCapacity);
 close(report.productionCapacity.minimumRetainedFraction,.529598370328203);assert.match(html,/52.96%/);assert.match(html,/production testing must establish/);
 assert.match(html,/does not establish the value/);assert.ok(printable(report,data,eng).includes(html));
 assert.match(printable(report,data,eng),/primary static model/);
});
