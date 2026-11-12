"""Build case-linked design evidence from the authenticated retained package.

Only geometry and arithmetic are executed. No new FE solution or physical
validation is claimed. Original research inputs remain read-only.
"""
from pathlib import Path
import argparse, ast, csv, hashlib, json, math, shutil, sys, types, zipfile
import numpy as np
from scipy.optimize import brentq
from scipy.special import gamma

ap=argparse.ArgumentParser();ap.add_argument('--numerical',type=Path,required=True);ap.add_argument('--research',type=Path,required=True)
args=ap.parse_args();N=args.numerical.resolve();R=args.research.resolve()/'release'
W=N/'Code_S2/implementation/review_program'
A=W.parent/'review_work/native/extracted/archived_source/gear_steel_design'
P=Path(__file__).resolve().parents[1];D=P/'dist/data';O=D/'cases';O.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources={}
def read(p):
    sources[str(p.relative_to(N) if p.is_relative_to(N) else p.relative_to(R))]=sha(p)
    return json.loads(p.read_text())
def selected(p,names,ns):
    sources[str(p.relative_to(N))]=sha(p)
    body=[x for x in ast.parse(p.read_text()).body if isinstance(x,(ast.FunctionDef,ast.ClassDef)) and x.name in names]
    assert {x.name for x in body}==set(names)
    exec(compile(ast.Module(body=body,type_ignores=[]),str(p),'exec'),ns)
ns={'np':np,'brentq':brentq,'gamma':gamma}
selected(A/'source_model/coupled_gear.py',['polyarc','Profile'],ns)
selected(A/'source_model/geometry_shapes.py',['outline'],ns)
ns.update(N_CURVE=512,REFERENCE_REMOVED_AREA=5*np.pi*55**2/4*np.sin(2*np.pi/512)/(2*np.pi/512))
selected(A/'expanded_geometry.py',['polygon_area','hole_curves'],ns)
mod=types.ModuleType('expanded_geometry');mod.__dict__.update(ns);sys.modules['expanded_geometry']=mod
mod2=types.ModuleType('sector_geometry');mod2.__dict__.update(ns)
selected(A/'sector_geometry.py',['rounded_sector','sector_curves'],mod2.__dict__);sys.modules['sector_geometry']=mod2
protocol=read(W/'prospective/protocol.json');coeff=read(R/'Data_S1/frozen_law_coefficients.json');h=read(W/'anchor_model/frozen_protocol.json')
carbon=read(W/'carbon/route_model/break_even_coefficients.json');example=read(W/'carbon/route_model/example_64_tooth_sector.json')
sensitivity=read(W/'prospective/decision_interval_report.json')
atlas=json.loads((D/'atlas.json').read_text());atlas['release']='0.3.0';atlas['name']='SpurAtlas'
cases={};regions=['web','rim','tooth_root','tooth_flank']
for c in atlas['cases']:
    name=c['sourceCase'];folder=W/'prospective/output/cases'/name
    assessment=read(folder/'assessment.json');g=read(folder/'geometry.json');audit=read(folder/'complete_mesh_audit.json')
    boundary=read(folder/'boundary_topology_audit.json');fatigue=read(W/f'prospective/output/{name}_fatigue_recovery.json')
    archive=read(W/f'field_archives/prospective_{name}_manifest.json')
    for source_name in ['geometry.json','assessment.json']:
        archived=next(v for v in archive['files'] if v['path'].endswith('/'+source_name))
        assert sha(folder/source_name)==archived['sha256'],(name,source_name,'archive binding mismatch')
    assert audit['status']=='PASS' and assessment['binding']['mesh_sha256']==g['mesh_sha256']==audit['mesh_sha256']
    assert abs(g['aperture_area_mm2']-c['openingAreaMm2'])<1e-8
    nominal=g['case']['nominal_opening_geometry'];profile=ns['Profile'](module=c['module'],teeth=c['teeth'],alpha=20.)
    outer=profile.polygon(3.);theta=np.arange(512)*2*np.pi/512;bore=c['boreDiameter']/2*np.array([np.cos(theta),np.sin(theta)])
    holes,_=ns['hole_curves'](**nominal);curves=[outer,bore,*holes]
    def pth(a):return 'M'+'L'.join(f'{x:.9f},{-y:.9f}' for x,y in a.T)+'Z'
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="256mm" height="256mm" viewBox="-128 -128 256 256"><title>SpurAtlas {c["id"]}: sampled nominal research profile, millimetres</title><desc>200 mm pitch diameter. Sampled boundaries; no manufacturing tolerances or production qualification.</desc><path d="'+''.join(pth(a) for a in curves)+'" fill="#e5ede6" fill-rule="evenodd" stroke="#173e35" stroke-width="0.15"/></svg>'
    (O/f'{c["id"]}.svg').write_text(svg)
    dxf=['0','SECTION','2','HEADER','9','$INSUNITS','70','4','0','ENDSEC','0','SECTION','2','ENTITIES']
    for i,a in enumerate(curves):
        for j in range(a.shape[1]):
            k=(j+1)%a.shape[1]
            dxf+=['0','LINE','8','OUTLINE' if i==0 else 'BORE' if i==1 else 'OPENINGS','10',str(a[0,j]),'20',str(a[1,j]),'30','0','11',str(a[0,k]),'21',str(a[1,k]),'31','0']
    (O/f'{c["id"]}.dxf').write_text('\n'.join(dxf+['0','ENDSEC','0','EOF'])+'\n')
    with (O/f'{c["id"]}-coordinates.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['boundary','point','x_mm','y_mm'])
        for i,a in enumerate(curves):
            writer.writerows((i,j,float(x),float(y)) for j,(x,y) in enumerate(a.T))
    # Retain actual per-tooth regional maxima, not an invented stress contour.
    stresses=[];metrics={k:0. for k in ['free_relative_residual','force_relative_balance','moment_relative_balance','virtual_work']}
    loads=[]
    for record in assessment['records']:
        item={'tooth':record['tooth']}
        for load in ['main','secondary']:
            item[load]={reg:record['peaks'][load]['geometry_aware'][reg]['peak_VM_MPa'] for reg in regions}
            direct=record['direct'][load]
            for k in metrics:metrics[k]=max(metrics[k],abs(direct[k]))
        stresses.append(item)
    for load in ['main','secondary']:
        d=assessment['records'][0]['direct'][load]
        loads.append({'anchor':load,'rpm':d['rpm'],'load':d['load']})
    # Curvature screen only. It does not establish reach, chatter or machine capacity.
    radii=[]
    for a in holes:
        p0=np.roll(a,1,axis=1);p1=a;p2=np.roll(a,-1,axis=1)
        ab=np.linalg.norm(p1-p0,axis=0);bc=np.linalg.norm(p2-p1,axis=0);ac=np.linalg.norm(p2-p0,axis=0)
        cross=np.abs((p1-p0)[0]*(p2-p1)[1]-(p1-p0)[1]*(p2-p1)[0])
        valid=(cross>1e-10)&(ab>1e-8)&(bc>1e-8)
        radii.extend((ab[valid]*bc[valid]*ac[valid]/(2*cross[valid])).tolist())
    files=[folder/'assessment.json',folder/'geometry.json',folder/'complete_mesh_audit.json',folder/'boundary_topology_audit.json',W/f'prospective/output/{name}_fatigue_recovery.json']
    entry={'id':c['id'],'sourceCase':name,'geometry':g,'meshAudit':audit,'boundaryAudit':boundary,'solverMetricMaxima':metrics,'loadsAtTooth0':loads,'regionalStressByTooth':stresses,'fatigueDemand':fatigue['regions']['geometry_aware'],'fatigueBoundDefinition':fatigue['bound_definition'],'rawFieldArchives':archive['archives'],'rawFiles':archive['files'],'minimumSampledOpeningCurvatureRadiusMm':min(radii),'sourceFiles':{str(p.relative_to(N)):sha(p) for p in files},'displayScope':'Regional stress maxima from retained case-specific FE summaries. No full-field displacement/stress contours reconstructed from missing local arrays. All regions, bore fixation and load patches follow the archived research model.'}
    (O/f'{c["id"]}-evidence.json').write_text(json.dumps(entry,separators=(',',':'))+'\n')
    cases[c['id']]=entry
    c.update(pressureAngle=20.,openingPerimeterMm=g['total_opening_perimeter_mm'],minimumCurvatureRadiusMm=min(radii),nominalOpening=nominal)

def errors(model,kind):
    values=[]
    for c in atlas['cases']:
        for r in c['rows']:
            p=r[kind]['estimate'+model] if kind=='static' else r[kind]['estimate']
            values.append(100*(p/r[kind]['reference']-1))
    return {'observations':len(values),'minimumSignedPercent':min(values),'maximumSignedPercent':max(values),'maximumAbsolutePercent':max(map(abs,values)),'p95AbsolutePercent':float(np.quantile(np.abs(values),.95))}
engineering={'release':'0.3.0','schema':'spuratlas-engineering-v1','cases':cases,'coefficients':coeff,'harmonicModel':h,'carbonCoefficients':carbon,'roadReference':example['road'],'sensitivityAudit':sensitivity,'empiricalErrors':{'E':errors('E','static'),'H':errors('H','static'),'fatigue':errors('','fatigue')},'sources':sources,'scope':'Case-linked retained evidence and newly computed scenario arithmetic. No refitting, new FE solve, case-specific convergence certification, measured production inventory or steel experiment. Conditional sensitivity intervals are not calibrated uncertainty bounds.'}
(D/'engineering.json').write_text(json.dumps(engineering,separators=(',',':'))+'\n')
(D/'atlas.json').write_text(json.dumps(atlas,separators=(',',':'))+'\n')
shutil.copy2(W/'carbon/route_model/break_even_law.py',D/'reference_carbon_model.py')
(D/'frozen-models.json').write_text(json.dumps({'powerLawBased':coeff,'secondaryHarmonic':h},indent=2)+'\n')
with (D/'case-stress-summaries.csv').open('w',newline='') as f:
    writer=csv.writer(f);writer.writerow(['layout','source_case','tooth','load_reference','region','peak_VM_MPa','mesh_sha256'])
    for id,e in cases.items():
        for row in e['regionalStressByTooth']:
            for load in ['main','secondary']:
                for reg in regions:writer.writerow([id,e['sourceCase'],row['tooth'],load,reg,row[load][reg],e['geometry']['mesh_sha256']])
prov=json.loads((D/'provenance.json').read_text());prov['engineeringExtension']={'release':'0.3.0','cases':len(cases),'sourceHashes':sources,'scope':engineering['scope']};prov['atlasJsonSha256']=sha(D/'atlas.json')
(D/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
print(json.dumps({'caseEvidencePackages':len(cases),'stressSummaryRows':sum(len(e['regionalStressByTooth'])*8 for e in cases.values()),'sourceBindings':len(sources),'sampledMinimumCurvatureMm':{id:e['minimumSampledOpeningCurvatureRadiusMm'] for id,e in cases.items()}},indent=2))
