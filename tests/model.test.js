import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {DEFAULT,MIXTURES,TARGETS,stateFromUrl,selectedCase,selectedRow,estimate,decision,carbonSummary,csvText,materialRow} from '../dist/model.js';
const data=JSON.parse(fs.readFileSync(new URL('../dist/data/atlas.json',import.meta.url)));

test('every documented response retains its source factor ratio',()=>{
  assert.equal(data.cases.length,10);
  for(const c of data.cases){
    assert.equal(c.rows.length,5);
    assert(c.materialRemovalFraction>0&&c.materialRemovalFraction<1);
    for(const row of c.rows)for(const response of ['static','fatigue']){
      assert(Math.abs(row[response].referenceFactor/row[response].solidFactor-row[response].reference)<1e-12);
      for(const model of ['E','H'])assert(estimate(row,response,model)>0);
    }
  }
});
test('all target decisions preserve unrounded reference and prediction comparisons',()=>{
  let count=0,staticFalsePass=0,fatigueFalsePass=0;
  for(const c of data.cases)for(const row of c.rows)for(const target of TARGETS){
    const result=decision(row,target,'H');
    assert.equal(result.reference,Math.min(row.static.referenceFactor,row.fatigue.referenceFactor)>=target);
    if(row.static.estimateH*row.static.solidFactor>=target&&row.static.referenceFactor<target)staticFalsePass++;
    if(row.fatigue.estimate*row.fatigue.solidFactor>=target&&row.fatigue.referenceFactor<target)fatigueFalsePass++;
    count++;
  }
  assert.equal(count,500);assert.equal(staticFalsePass,3);assert.equal(fatigueFalsePass,3);
});
test('both carbon examples match all retained paybacks and reference-exposure differences',()=>{
  assert.equal(data.carbon.length,48);
  for(const layout of ['circle','sector'])for(const frv of [.15,.26])for(const route of ['milling','wire']){
    const summary=carbonSummary(data,layout,frv,route);
    assert.equal(summary.rows.length,route==='milling'?9:3);
    assert(summary.minPayback<=summary.nominal.paybackMillionCycles&&summary.nominal.paybackMillionCycles<=summary.maxPayback);
    for(const row of summary.rows){
      assert(Math.abs(row.initialKg/row.savingKgPerCycle/1e6-row.paybackMillionCycles)<1e-10);
      assert(Math.abs(row.initialKg-row.savingKgPerCycle*5e6-row.deltaAt5MillionKg)<1e-10);
      assert.equal(row.paybackMillionCycles<=5,row.deltaAt5MillionKg<=0);
    }
  }
});
test('selection URLs reject unsupported inputs and restore legitimate selections',()=>{
  const s=stateFromUrl('?layout=G10&lambda=1&target=6&model=E&response=fatigue&carbon=sector&frv=0.26',data);
  assert.equal(selectedCase(data,s).family,'superellipse');assert.equal(selectedRow(selectedCase(data,s),s.lambda).lambda,1);
  assert.equal(s.target,6);assert.equal(s.model,'E');assert.equal(s.carbon,'sector');assert.equal(s.frv,.26);
  assert.deepEqual(stateFromUrl('?layout=bad&lambda=.33&target=0&model=bad&frv=NaN',data),DEFAULT);
  for(const lambda of MIXTURES)assert.equal(stateFromUrl('?lambda='+lambda,data).lambda,lambda);
});
test('CSV exports preserve quotation, newlines and source identifiers',()=>{
  const csv=csvText([['Citation','Nurudeen, A. O.'],['Note','A "quoted" value'],['DOI',data.dataDoi]]);
  assert(csv.includes('"A ""quoted"" value"'));assert(csv.includes(data.dataDoi));assert(csv.endsWith('\r\n'));
});
test('material calculations preserve stress-reference ratios and use source-corrected properties',()=>{
  assert.equal(data.materials.length,9);
  const published={SAE8620_core119_research:[211.8,693.5,1638.8,-.1007],SAE8620_core120_research:[210.3,795.8,1910.2,-.1028],SAE8620_core121_research:[213.5,989.5,2209.9,-.0987]};
  for(const m of data.materials){
    if(!m.reference)assert(Math.abs(m.fatigueMPa-.8*m.basquinMPa*(1e7)**m.basquinExponent)<1e-10);
    if(published[m.id])assert.deepEqual([m.E_GPa,m.yieldMPa,m.basquinMPa,m.basquinExponent],published[m.id]);
    for(const c of data.cases)for(const raw of c.rows){
      const r=materialRow(raw,m);
      assert(Math.abs(r.static.referenceFactor/raw.static.referenceFactor-m.yieldMPa/695)<1e-12);
      assert(Math.abs(r.fatigue.referenceFactor/raw.fatigue.referenceFactor-m.fatigueMPa/277.7262951561842)<1e-12);
      for(const kind of ['static','fatigue'])assert(Math.abs(r[kind].referenceFactor/r[kind].solidFactor-raw[kind].reference)<1e-12);
      for(const target of TARGETS)assert.equal(decision(r,target,'H').reference,Math.min(r.static.referenceFactor,r.fatigue.referenceFactor)>=target);
    }
  }
});
test('research index retains missing-response boundaries and all source records',()=>{
  const index=JSON.parse(fs.readFileSync(new URL('../dist/data/coverage.json',import.meta.url)));
  assert.equal(index.records.length,631);
  assert.deepEqual(index.toothCounts.map(x=>x.teeth),[32,34,36,38,40,42,44,46,48]);
  assert.equal(index.toothCounts.find(x=>x.teeth===32).static,0);
  assert.equal(index.toothCounts.find(x=>x.teeth===44).fatigue,0);
  for(const r of index.records){assert.match(r.sourceSha256,/^[0-9a-f]{64}$/);assert(r.sourceRow>=2);assert(r.retention>0);assert(r.construction.length>10);}
});
