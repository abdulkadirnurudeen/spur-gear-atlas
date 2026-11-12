import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {comparisonSelection,operatingOptions,SENSITIVITY_OPTIONS} from '../dist/design-options.js';
import {assessRequirements,shortlist} from '../dist/design-model.js';
const data=JSON.parse(readFileSync(new URL('../dist/data/atlas.json',import.meta.url)));

test('all offered geometry, load, factor and sensitivity selections remain within the retained case scope',()=>{
 for(const teeth of [42,46]){
  const menu=comparisonSelection(data,{teeth});
  for(const load of menu.loads)for(const st of menu.targets)for(const ft of menu.targets)for(const epsilon of SENSITIVITY_OPTIONS){
   const request={...menu.values,...load,staticTarget:st,fatigueTarget:ft,epsilon};
   assert.equal(assessRequirements(data,request).supported,true,JSON.stringify(request));
  }
  for(const family of ['all',...menu.geometry.families])for(const material of data.materials){
   const result=shortlist(data,{...menu.values,family,material:material.id});
   assert.equal(result.coverage.supported,true);assert.ok(result.rows.length>0);assert.ok(result.rows.every(r=>r.teeth===teeth));
  }
 }
});
test('choosing torque or speed synchronizes the exact coupled operating point and gear changes refresh families',()=>{
 const initial=comparisonSelection(data,{teeth:46,family:'sector'}).values;
 for(const load of operatingOptions(data))for(const key of ['lambda','torqueNm','speedRpm']){
  const result=comparisonSelection(data,{...initial,[key]:load[key]},key).values;
  assert.equal(result.lambda,load.lambda);assert.equal(result.torqueNm,load.torqueNm);assert.equal(result.speedRpm,load.speedRpm);
  assert.equal(assessRequirements(data,result).supported,true);
 }
 const changed=comparisonSelection(data,{...initial,teeth:42});
 assert.deepEqual(changed.geometry.families,['circle']);assert.equal(changed.values.family,'all');assert.ok(shortlist(data,changed.values).rows.length>0);
});
test('unsupported legacy links are explicitly adjusted to available menu choices while valid links restore exactly',()=>{
 const normalized=comparisonSelection(data,{teeth:32,pitchDiameter:250,torqueNm:250,speedRpm:2000,cycles:1e6,staticTarget:3.2,family:'sector',epsilon:.99,material:'missing'});
 for(const key of ['teeth','pitchDiameter','torqueNm','speedRpm','cycles','staticTarget','family','epsilon','material'])assert.ok(normalized.adjustedKeys.includes(key),key);
 assert.equal(assessRequirements(data,normalized.values).supported,true);
 const request=comparisonSelection(data,{teeth:46,lambda:.75,material:'SAE8620_core121_research',allMixtures:true,model:'H',epsilon:.15,staticTarget:5.5,fatigueTarget:6,family:'superellipse'}).values;
 const restored=comparisonSelection(data,request);assert.deepEqual(restored.values,request);assert.deepEqual(restored.adjustedKeys,[]);
});
