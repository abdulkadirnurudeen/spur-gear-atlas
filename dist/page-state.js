const prefix='spuratlas-navigation-v1:';
function browserStorage(){try{return typeof sessionStorage==='undefined'?null:sessionStorage;}catch{return null;}}
export function readSaved(section,storage=browserStorage()){
  try{const value=JSON.parse(storage?.getItem(prefix+section)||'null');return value&&typeof value==='object'&&!Array.isArray(value)?value:null;}catch{return null;}
}
export function writeSaved(section,value,storage=browserStorage()){
  try{if(!storage)return false;storage.setItem(prefix+section,JSON.stringify(value));return true;}catch{return false;}
}
export function referenceSearch(search,saved){
  const params=new URLSearchParams(search),keys=['layout','lambda','target','model','response','carbon','frv','material','miles'];
  if(keys.some(k=>params.has(k))||!saved)return search;
  const restored=new URLSearchParams();for(const key of keys)if(saved[key]!==undefined)restored.set(key,String(saved[key]));
  return '?'+restored.toString();
}
export function legacyDestination(pathname,search,hash){
  const page=pathname.split('/').pop();if(page&&page!=='index.html')return null;
  const targets={design:'design.html',explore:'explore.html','research-index':'explore.html',carbon:'carbon.html',evidence:'evidence.html',about:'about.html'};
  const anchor=hash.replace(/^#/,'');let target=targets[anchor];
  const params=new URLSearchParams(search);
  if(!target&&[...params.keys()].some(k=>k.startsWith('d_')||k.startsWith('c_')))target='design.html';
  if(!target&&params.has('layout'))target='explore.html';
  if(!target&&(params.has('carbon')||params.has('frv')||params.has('miles')))target='carbon.html';
  return target?target+search+(targets[anchor]?hash:''):null;
}
