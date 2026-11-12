"""Package the exact browser arithmetic, evidence and a dependency-free Node replay."""
from pathlib import Path
import hashlib,json,zipfile
P=Path(__file__).resolve().parents[1];D=P/'dist/data'
atlas=json.loads((D/'atlas.json').read_text())
t=atlas['loads']['T'];p=atlas['loads']['P']
example={'project':'SpurAtlas reproducible example','requirements':{'teeth':42,'pitchDiameter':200,'faceWidth':30,'boreDiameter':30,'pressureAngle':20,'lambda':.5,'torqueNm':.5*(t['torqueNm']+p['torqueNm']),'speedRpm':(.5*(t['speedRpm']**2+p['speedRpm']**2))**.5,'cycles':5000000,'staticTarget':3,'fatigueTarget':3,'material':'reference','model':'E','epsilon':.1,'allMixtures':False,'objective':'mass','family':'all'}}
cli='''import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const root=new URL('./',import.meta.url);
const read=p=>JSON.parse(readFileSync(new URL(p,root),'utf8'));
const manifest=read('manifest.json');
for(const [path,hash]of Object.entries(manifest.files)){const actual=createHash('sha256').update(readFileSync(new URL(path,root))).digest('hex');if(actual!==hash)throw new Error('Integrity mismatch: '+path);}
const {shortlist,makeReport,carbonDefaults}=await import('./dist/design-model.js');
const {printable}=await import('./dist/design-ui.js');
const data=read('dist/data/atlas.json'),engineering=read('dist/data/engineering.json');
const input=JSON.parse(readFileSync(process.argv[2]||new URL('example-request.json',root),'utf8'));
const request=input.requirements||input;const result=shortlist(data,request);
const selected=input.selection?.id||input.selectedId||result.recommended||result.rows[0]?.id;
const report=makeReport(data,engineering,request,result,selected,input.carbonSettings||carbonDefaults,input.project||'');
const text=JSON.stringify(report,null,2)+'\\n';if(process.argv[3])writeFileSync(process.argv[3],text);else process.stdout.write(text);
const html=process.argv.indexOf('--html');if(html>=0&&process.argv[html+1]){const field=engineering.cases[selected]?.fieldPlot;const imageData=field?'data:image/png;base64,'+readFileSync(new URL('dist/'+field.image,root)).toString('base64'):'';writeFileSync(process.argv[html+1],printable(report,data,engineering,imageData));}
'''
readme='''# SpurAtlas VERSION — reproducible design calculation

Unzip this package into a new folder. Node.js 20 or newer is required; there
are no external JavaScript dependencies. The browser and this replay use the
same retained data and pure calculation module.

Run the example:

    node reproduce.mjs example-request.json recalculated.json --html report.html

Replay a JSON calculation exported from the website:

    node reproduce.mjs exported_calculation.json recalculated.json --html report.html

Open report.html in a browser and print it or save it as a PDF. Its selected
field figure is embedded in the file. JSON numerical results reproduce;
generatedUtc records the new replay time. The original exported project label
is retained locally. Verify that requirements, selected case and carbon inputs
match before comparing outputs.

Run all software checks:

    node --test tests/*.test.js

The SHA-256 manifest detects changed package bytes; it is not a digital
signature or independent engineering certification. The script verifies the
manifest before executing the calculation modules.

The ten case figures are recovered from SHA-256-authenticated mesh and nodal
displacement arrays. tools/render_case_fields.py records how to recover them
from the separately archived raw files. Their regional stress maxima reproduce
the retained assessment to the tolerance recorded in data/field-recovery.json.
The large raw arrays are not duplicated in this small replay package. No new
FE solve occurs. tools/build_engineering.py rebuilds metadata and drawings from
the complete retained numerical/document source package.

Scope: compatible retained 42/46-tooth cases, 200 mm pitch diameter, 30 mm face
and bore, 20-degree pressure angle, five saved force/body-load mixtures and
five million counted fatigue cycles. Wider tooth counts are research-index
records and do not acquire missing absolute factors through this tool.
Homogeneous material comparisons preserve the declared density and Poisson
ratio. Published specimen fits are not production allowables. Conditional
error bands are sensitivity assumptions, not calibrated physical uncertainty.

Matched climate results are new same-geometry route-planning scenarios from
the archived route equation. Default milling uses the retained geometry-specific roughing and finishing
recipe, with its cutter references, operation fractions and electricity inventory.
Miles are displayed; canonical source units are retained for exact replay. Real
tool reach, machine stability, material state, fatigue performance, measured
inventory, ISO 6336 gear ratings and full LCA conformity remain separate
assessments. Each report records their status explicitly.

Author: Abdulkadir Oshioze Nurudeen; ORCID 0000-0002-2646-5784.
Supporting numerical data: https://doi.org/10.5281/zenodo.24144925 (2.0.0).
Original benchmark: https://doi.org/10.5281/zenodo.24055230.
Software: MIT. Research data: CC BY 4.0; third-party rights remain with owners.
'''
files={}
for f in (P/'dist/data').rglob('*'):
 if f.is_file() and f.suffix!='.zip':files[str(f.relative_to(P))]=f.read_bytes()
for f in (P/'dist/assets/case-fields').glob('*.png'):files[str(f.relative_to(P))]=f.read_bytes()
for f in (P/'tests').iterdir():
 if f.is_file():files[str(f.relative_to(P))]=f.read_bytes()
for name in ['dist/model.js','dist/distance.js','dist/milling-recipes.js','dist/recipe-ui.js','tools/build_milling_recipes.py','dist/design-model.js','dist/design-options.js','dist/design-ui.js','dist/page-state.js','tools/build_engineering.py','tools/render_case_fields.py','tools/package_reproduction.py','LICENSE','CITATION.cff']:
 files[name]=(P/name).read_bytes()
files['README.md']=readme.replace('VERSION',atlas['release']).encode();files['reproduce.mjs']=cli.encode();files['example-request.json']=(json.dumps(example,indent=2)+'\n').encode();files['package.json']=b'{"type":"module","private":true}\n'
manifest={'tool':'SpurAtlas','release':atlas['release'],'scope':'Calculation reproduction and retained evidence; no new FE solve','files':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()}}
files['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
target=D/'reproduction-bundle.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name,b in files.items():z.writestr(name,b)
print(json.dumps({'files':len(files),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))
