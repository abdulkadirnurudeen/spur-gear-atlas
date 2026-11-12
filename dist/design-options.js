import {MIXTURES,TARGETS} from './model.js';
import {defaults,operatingPoint} from './design-model.js';

export const GEOMETRY_KEYS=['teeth','pitchDiameter','faceWidth','boreDiameter','pressureAngle'];
export const SENSITIVITY_OPTIONS=[.05,.10,.15];
export function geometryOptions(data,selection={}) {
  let cases=data.cases.slice();const values={},options={};
  for(const key of GEOMETRY_KEYS){
    options[key]=[...new Set(cases.map(c=>c[key]))].sort((a,b)=>a-b);
    const requested=Number(selection[key]);
    values[key]=options[key].includes(requested)?requested:options[key][0];
    cases=cases.filter(c=>c[key]===values[key]);
  }
  return {values,options,cases,families:[...new Set(cases.map(c=>c.family))]};
}
export function operatingOptions(data) {return MIXTURES.map(lambda=>({lambda,...operatingPoint(data,lambda)}));}
export function comparisonSelection(data,selection={},changedKey='lambda') {
  const geometry=geometryOptions(data,selection),loads=operatingOptions(data);
  let load;
  if(['torqueNm','speedRpm'].includes(changedKey))load=loads.find(p=>p[changedKey]===Number(selection[changedKey]));
  load=load||loads.find(p=>p.lambda===Number(selection.lambda))||loads.find(p=>p.lambda===defaults.lambda)||loads[0];
  const member=(key,options,fallback)=>options.includes(selection[key])?selection[key]:fallback;
  const values={...defaults,...geometry.values,...load,
    cycles:data.fatigueReferenceCycles,
    staticTarget:TARGETS.includes(Number(selection.staticTarget))?Number(selection.staticTarget):defaults.staticTarget,
    fatigueTarget:TARGETS.includes(Number(selection.fatigueTarget))?Number(selection.fatigueTarget):defaults.fatigueTarget,
    epsilon:SENSITIVITY_OPTIONS.includes(Number(selection.epsilon))?Number(selection.epsilon):defaults.epsilon,
    allMixtures:selection.allMixtures===true||selection.allMixtures==='true',
    material:member('material',data.materials.map(m=>m.id),data.materials.find(m=>m.id===defaults.material)?.id||data.materials[0].id),
    family:member('family',['all',...geometry.families],'all'),
    model:member('model',['E','H'],defaults.model),objective:member('objective',['mass','margin'],defaults.objective)};
  const adjustedKeys=Object.keys(values).filter(k=>selection[k]!==undefined&&selection[k]!==values[k]);
  return {values,geometry,loads,targets:TARGETS,sensitivity:SENSITIVITY_OPTIONS,adjustedKeys};
}
