import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readSaved,writeSaved,referenceSearch,legacyDestination} from '../dist/page-state.js';

test('page navigation restores local comparisons and tolerates unavailable or corrupted storage',()=>{
 const entries=new Map(),storage={getItem:key=>entries.get(key),setItem:(key,value)=>entries.set(key,value)};
 const comparison={requirements:{teeth:46,material:'SAE8620_core121_research',staticTarget:4},selectedId:'G08',settings:{frv:.26},project:'Local label'};
 assert.equal(writeSaved('design',comparison,storage),true);assert.deepEqual(readSaved('design',storage),comparison);
 assert.equal(readSaved('reference',storage),null);
 const unavailable={getItem(){throw Error('Denied');},setItem(){throw Error('Denied');}};
 assert.equal(readSaved('design',unavailable),null);assert.equal(writeSaved('design',comparison,unavailable),false);
 for(const value of ['invalid','null','[]','"text"']){storage.setItem('spuratlas-navigation-v1:design',value);assert.equal(readSaved('design',storage),null);}
});
test('shared reference links take precedence over the previous page selection',()=>{
 const saved={layout:'G10',target:4,model:'H',lambda:.75,carbon:'m1',frv:.26,project:'Must not enter URL'};
 for(const explicit of ['?layout=G01&target=2','?frv=0&carbon=m2','?material=reference'])assert.equal(referenceSearch(explicit,saved),explicit);
 const restored=new URLSearchParams(referenceSearch('',saved));
 for(const key of ['layout','target','model','lambda','carbon','frv'])assert.equal(restored.get(key),String(saved[key]));
 assert.equal(restored.has('project'),false);assert.equal(referenceSearch('',null),'');
});
test('original root links reach the corresponding new page with their selection intact',()=>{
 const design='?d_teeth=46&d_selected=G08&c_frv=.26';
 assert.equal(legacyDestination('/',design,'#design'),'design.html'+design+'#design');
 assert.equal(legacyDestination('/index.html',design,''),'design.html'+design);
 assert.equal(legacyDestination('/','?layout=G10&target=4','#explore'),'explore.html?layout=G10&target=4#explore');
 assert.equal(legacyDestination('/','','#research-index'),'explore.html#research-index');
 for(const page of ['carbon','evidence','about'])assert.equal(legacyDestination('/','','#'+page),page+'.html#'+page);
 assert.equal(legacyDestination('/','?carbon=m1&frv=.26',''),'carbon.html?carbon=m1&frv=.26');
 assert.equal(legacyDestination('/design.html',design,'#design'),null);assert.equal(legacyDestination('/','',''),null);
});
