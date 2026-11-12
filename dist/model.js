import {DEFAULT_DISTANCE_MILES} from './distance.js';
export const MIXTURES = [0, 0.25, 0.5, 0.75, 1];
export const TARGETS = [1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6];
export const DEFAULT = {layout:'G01',lambda:0.5,target:3,model:'E',response:'static',carbon:'circle',frv:0.15,material:'reference',miles:DEFAULT_DISTANCE_MILES};
export function stateFromUrl(search, data) {
  const p = new URLSearchParams(search), s = {...DEFAULT};
  if (data.cases.some(c => c.id === p.get('layout'))) s.layout = p.get('layout');
  for (const [key, values] of [['lambda',MIXTURES],['target',TARGETS],['frv',[0.15,0.26]]]) {
    if (p.has(key) && values.includes(Number(p.get(key)))) s[key] = Number(p.get(key));
  }
  if(p.has('miles')&&Number.isFinite(Number(p.get('miles')))&&Number(p.get('miles'))>=0)s.miles=Number(p.get('miles'));
  if (['E','H'].includes(p.get('model'))) s.model = p.get('model');
  if (['static','fatigue'].includes(p.get('response'))) s.response = p.get('response');
  if (['circle','sector'].includes(p.get('carbon'))) s.carbon = p.get('carbon');
  if ((data.materials||[]).some(m=>m.id===p.get('material'))) s.material=p.get('material');
  return s;
}
export function selectedCase(data, state) { return data.cases.find(c=>c.id===state.layout); }
export function selectedRow(c, lambda) { return c.rows.find(r=>r.lambda===lambda); }
export function selectedMaterial(data,state) { return (data.materials||[]).find(m=>m.id===state.material)||(data.materials||[])[0]; }
export function materialRow(row, material) {
  if (!material||material.reference) return row;
  const out={...row};
  for (const kind of ['static','fatigue']) {
    const scale=kind==='static'?material.yieldMPa/695:material.fatigueMPa/277.7262951561842;
    out[kind]={...row[kind],solidFactor:row[kind].solidFactor*scale,referenceFactor:row[kind].referenceFactor*scale};
  }
  return out;
}
export function estimate(row, response, model) {
  return response==='static' ? row.static['estimate'+model] : row.fatigue.estimate;
}
export function decision(row, target, model) {
  const reference = row.static.referenceFactor>=target && row.fatigue.referenceFactor>=target;
  const predicted = estimate(row,'static',model)*row.static.solidFactor>=target && row.fatigue.estimate*row.fatigue.solidFactor>=target;
  return {reference,predicted,agreement:reference===predicted};
}
export function carbonSummary(data, layout, frv, route) {
  const rows=data.carbon.filter(r=>r.layout===layout&&r.frv===frv&&r.route===route);
  const nominal=rows.find(r=>r.nominal);
  if (!rows.length||!nominal) throw new Error('Missing documented carbon scenario');
  return {rows,nominal,minPayback:Math.min(...rows.map(r=>r.paybackMillionCycles)),maxPayback:Math.max(...rows.map(r=>r.paybackMillionCycles))};
}
export function csvText(rows) {
  return '\ufeff'+rows.map(row=>row.map(value=>'"'+String(value??'').replaceAll('"','""')+'"').join(',')).join('\r\n')+'\r\n';
}
