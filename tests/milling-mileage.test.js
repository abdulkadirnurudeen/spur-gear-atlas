import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

import {carbonDefaults,effectiveCarbonSettings,manufacturingScenario,matchedCarbon,makeReport,defaults,operatingPoint,shortlist} from '../dist/design-model.js';
import {millingRecipes} from '../dist/milling-recipes.js';
import {KM_PER_MILE,DEFAULT_DISTANCE_MILES,toMiles,toKm,carbonDisplayValue,carbonStoredValue,mileageDecision} from '../dist/distance.js';
import {printable} from '../dist/design-ui.js';
const read=p=>JSON.parse(readFileSync(new URL(p,import.meta.url)));
const data=read('../dist/data/atlas.json'),engineering=read('../dist/data/engineering.json');
const close=(a,b)=>assert.ok(Math.abs(a-b)<=Math.max(1e-10,Math.abs(b)*2e-12),`${a} != ${b}`);

test('all ten geometry recipes conserve removed volume and account for each electricity subtotal',()=>{
 for(const c of data.cases){
  const r=manufacturingScenario(c,carbonDefaults,engineering.carbonCoefficients,'milling'),p=r.recipe;
  assert.equal(p.legs.length,2);close(p.legs.reduce((s,l)=>s+l.volume_fraction,0),1);
  close(r.operations.reduce((s,o)=>s+o.volumeMm3,0),c.openingAreaMm2*c.faceWidth);
  close(r.operations.reduce((s,o)=>s+o.driveElectricityKWh+o.baseElectricityKWh,0)+r.noncutElectricityKWh+r.chipPressElectricityKWh,r.siteElectricityKWh);
  assert.deepEqual(p.legs.map(l=>l.diameter_mm),['G07','G08'].includes(c.id)?[12,3]:[20,20]);
  assert.ok(p.legs.every(l=>l.catalogueEDP&&l.flutes===4&&l.fluteLengthMm>0));
 }
 for(const p of Object.values(millingRecipes.originalCases)){
  const r=p.nominalMilling;
  close(r.operations.reduce((s,o)=>s+o.driveElectricityKWh+o.baseElectricityKWh,0)+r.noncutElectricityKWh+r.chipPressElectricityKWh,r.siteElectricityKWh);
 }
 assert.deepEqual(read('../dist/data/milling-recipes.json'),millingRecipes);
});

test('invalid shared and edited inputs cannot produce an exportable nonfinite or fractional-flute calculation',()=>{
 const c=data.cases.find(c=>c.id==='G03');
 for(const invalid of [{flutes:1.5},{bulkFlutes:1.5},{flutes:0},{flutes:Infinity},{flutes:2**54},{feedMmMin:0},{bulkFeedMmMin:1e-300},{grid:NaN},{distanceKm:Infinity},{distanceKm:1e308},{frv:1e308},{grid:1e308},{rpm:1e308},{radialEngagementMm:11},{axialDepthMm:100},{cutterMm:3}]){
  assert.throws(()=>matchedCarbon(c,{...carbonDefaults,...invalid},engineering),JSON.stringify(invalid));
 }
 const sector=data.cases.find(c=>c.id==='G07');
 assert.throws(()=>effectiveCarbonSettings(sector,{...carbonDefaults,flutes:1.5}),/whole numbers/);
});

test('miles round trip without changing the source default or fuel-saving calculation',()=>{
 close(DEFAULT_DISTANCE_MILES,18631.80492601933);
 for(const key of ['distanceKm','cyclesPerKm','frv'])close(carbonStoredValue(key,carbonDisplayValue(key,carbonDefaults[key])),carbonDefaults[key]);
 close(toKm(toMiles(29984.983466859652)),29984.983466859652);
 const c=data.cases.find(c=>c.id==='G03'),r=matchedCarbon(c,carbonDefaults,engineering)[0];
 close(r.breakEvenMiles*KM_PER_MILE,r.breakEvenKm);
 close(r.savingKgCO2ePerMile*DEFAULT_DISTANCE_MILES,r.savingKgCO2ePerKm*carbonDefaults.distanceKm);
 close(carbonDisplayValue('frv',.15),.2414016);
});

test('payback flags compare only with the designer mileage, including zero and no finite crossing',()=>{
 assert.equal(mileageDecision(100,100).exceedsDesignerMileage,false);
 assert.equal(mileageDecision(101,100).exceedsDesignerMileage,true);
 assert.equal(mileageDecision(99,100).exceedsDesignerMileage,false);
 assert.equal(mileageDecision(null,1e6).status,'No finite payback');
 const c=data.cases.find(c=>c.id==='G07');
 const a=matchedCarbon(c,{...carbonDefaults,distanceKm:toKm(1e6)},engineering);
 assert.ok(a.every(r=>!r.withinReferenceExposure&&!r.exceedsDesignerMileage));
 assert.ok(matchedCarbon(c,{...carbonDefaults,distanceKm:0},engineering).every(r=>r.exceedsDesignerMileage));
 assert.ok(matchedCarbon(c,{...carbonDefaults,frv:0},engineering).every(r=>r.breakEvenMiles===null&&r.exceedsDesignerMileage));
});

test('reports normalize the selected geometry recipe and expose the actual operations and mileage',()=>{
 const request={...defaults,teeth:46,...operatingPoint(data,.5)},result=shortlist(data,request);
 const report=makeReport(data,engineering,request,result,'G07',carbonDefaults);
 assert.equal(report.carbonSettings.recipeCaseId,'G07');assert.equal(report.carbonSettings.bulkCutterMm,12);assert.equal(report.carbonSettings.cutterMm,3);
 close(report.mileageInputs.serviceMileageMiles,DEFAULT_DISTANCE_MILES);
 const html=printable(report,data,engineering);
 const edited=makeReport(data,engineering,request,result,'G07',{...report.carbonSettings,setupCount:2,baseKW:3});
 assert.ok(printable(edited,data,engineering).includes('2 allocated setups'));
 assert.ok(printable(edited,data,engineering).includes('Applied base power: 3.00 kW'));
 for(const term of ['Recommended milling recipe','3130620','3174016','Payback (miles)','cycles per mile','Step electricity (kWh)'])assert.ok(html.includes(term),term);
 assert.ok(!html.includes('cycles per km'));
});
