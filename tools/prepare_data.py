"""Prepare the atlas from the checked research release; never run an FE solver.

Usage: python tools/prepare_data.py --source /path/to/extracted/document/source
The deployed site reads only dist/data/atlas.json. Original research inputs
remain unchanged. Geometry functions are extracted verbatim with ast to avoid
importing or executing the archived solver or creating research output folders.
"""
from pathlib import Path
import argparse, ast, csv, hashlib, json, math, shutil, sys, types
import numpy as np
from scipy.optimize import brentq
from scipy.special import gamma

P = Path(__file__).resolve().parents[1]
args = argparse.ArgumentParser()
args.add_argument('--source', type=Path, required=True)
S = args.parse_args().source.resolve()
R = S / 'release'
if not R.exists():
    R = S
W = R / 'Code_S2/implementation/review_program'
A = R / 'Code_S2/implementation/review_work/native/extracted/archived_source/gear_steel_design'
D = P / 'dist/data'
D.mkdir(parents=True, exist_ok=True)
(P / 'dist/assets').mkdir(exist_ok=True)

inputs = [R/'Data_S1/frozen_law_coefficients.json', W/'prospective/protocol.json',
          W/'prospective/all_100_response_rows.csv', W/'anchor_model/prospective_evaluation_rows.csv',
          W/'anchor_model/frozen_protocol.json', R/'Data_S1/figure4_scenario_sources.csv',
          W/'carbon/route_model/break_even_coefficients.json',
          A/'expanded_geometry.py', A/'sector_geometry.py',
          A/'source_model/coupled_gear.py', A/'source_model/geometry_shapes.py']
digests = {str(f.relative_to(R)): hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}

def selected(path, names, namespace):
    tree = ast.parse(path.read_text())
    body = [x for x in tree.body if isinstance(x, (ast.FunctionDef, ast.ClassDef)) and x.name in names]
    assert {x.name for x in body} == set(names)
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), 'exec'), namespace)

ns = {'np': np, 'brentq': brentq, 'gamma': gamma}
selected(A/'source_model/coupled_gear.py', ['polyarc', 'Profile'], ns)
selected(A/'source_model/geometry_shapes.py', ['outline'], ns)
ns.update(N_CURVE=512, REFERENCE_REMOVED_AREA=5*np.pi*55**2/4*np.sin(2*np.pi/512)/(2*np.pi/512))
selected(A/'expanded_geometry.py', ['polygon_area', 'hole_curves'], ns)
expanded = types.ModuleType('expanded_geometry')
expanded.__dict__.update(ns)
sys.modules['expanded_geometry'] = expanded
sector = types.ModuleType('sector_geometry')
sector.__dict__.update(ns)
selected(A/'sector_geometry.py', ['rounded_sector', 'sector_curves'], sector.__dict__)
sys.modules['sector_geometry'] = sector

def rows(path):
    return list(csv.DictReader(path.open()))

protocol = json.loads((W/'prospective/protocol.json').read_text())
responses = rows(W/'prospective/all_100_response_rows.csv')
harmonic = rows(W/'anchor_model/prospective_evaluation_rows.csv')
coeff = json.loads((R/'Data_S1/frozen_law_coefficients.json').read_text())['coefficient_theta']
hprotocol = json.loads((W/'anchor_model/frozen_protocol.json').read_text())
htheta = hprotocol['theta']
density = json.loads((W/'carbon/route_model/break_even_coefficients.json').read_text())['density_kg_mm3']
assert len(responses) == 100 and len(harmonic) == 50

def path(curve):
    return 'M' + 'L'.join(f'{x:.3f},{-y:.3f}' for x, y in curve.T) + 'Z'

cases = []
for i, item in enumerate((c for c in protocol['cases'] if c['case']['opening_count']), 1):
    case = item['case']
    g = item['geometry_features']
    profile = ns['Profile'](module=case['module_mm'], teeth=case['teeth'], alpha=case['pressure_angle_deg'])
    outer = profile.polygon(3.)
    theta = np.arange(512)*2*np.pi/512
    bore = case['bore_diameter_mm']/2*np.array([np.cos(theta), np.sin(theta)])
    holes, _ = ns['hole_curves'](**case['nominal_opening_geometry'])
    solid_area = ns['polygon_area'](outer) - ns['polygon_area'](bore)
    opening_area = sum(ns['polygon_area'](h) for h in holes)
    phi = opening_area/(np.pi*(90.75**2-22.5**2))
    b_r = (profile.rf-max(np.linalg.norm(h, axis=0).max() for h in holes))/(2.25*case['module_mm'])
    assert abs(phi-g['phi']) < 1e-10
    assert abs(b_r-g['b_R']) < 1e-10
    data = []
    for lam in [0, .25, .5, .75, 1]:
        st = next(r for r in responses if r['case']==item['name'] and r['response']=='static' and float(r['lambda_main'])==lam)
        ft = next(r for r in responses if r['case']==item['name'] and r['response']=='fatigue' and float(r['lambda_main'])==lam)
        h = next(r for r in harmonic if r['case']==item['name'] and float(r['lambda_main'])==lam)
        # Independently verify the power-law formula against all saved E/fatigue
        # predictions. Website interactions use these saved rows, not refitting.
        family_index = ['circle','sector','superellipse'].index(case['family'])
        for kind, row in [('static',st),('fatigue',ft)]:
            t = coeff[kind]
            prediction = 1/(1+math.exp(t[family_index])*phi**t[3]*b_r**(-t[4])*math.exp(t[5]*(lam-.5)))
            assert abs(prediction-float(row['predicted_retention'])) < 2e-12
        data.append({'lambda':lam,
          'static':{'reference':float(st['reference_retention']), 'estimateE':float(st['predicted_retention']), 'estimateH':float(h['anchor8_prediction']), 'solidFactor':float(st['solid_FoS']), 'referenceFactor':float(st['perforated_FoS'])},
          'fatigue':{'reference':float(ft['reference_retention']), 'estimate':float(ft['predicted_retention']), 'solidFactor':float(ft['solid_FoS']), 'referenceFactor':float(ft['perforated_FoS'])}})
    cases.append({'id':f'G{i:02}', 'sourceCase':item['name'], 'family':case['family'], 'teeth':case['teeth'],
      'pitchDiameter':case['pitch_diameter_mm'], 'faceWidth':case['face_width_mm'], 'boreDiameter':case['bore_diameter_mm'],
      'module':case['module_mm'], 'openingCount':case['opening_count'], 'phi':g['phi'], 'ligamentRatio':g['b_R'],
      'radialPosition':case['nominal_opening_geometry']['r'], 'ligamentMm':g['b_R']*2.25*case['module_mm'],
      'openingAreaMm2':opening_area, 'solidAreaMm2':solid_area, 'materialRemovalFraction':opening_area/solid_area,
      'massRemovedKg':opening_area*case['face_width_mm']*density,
      'solidMassKg':solid_area*case['face_width_mm']*density,
      'referenceAnnulusAreaMm2':np.pi*(90.75**2-22.5**2),
      'geometryPath':''.join(path(x) for x in [outer,bore,*holes]), 'rows':data})

carbon=[]
for r in rows(R/'Data_S1/figure4_scenario_sources.csv'):
    a=float(r['initial_climate_kg_CO2e']);s=float(r['slope_kg_per_cycle'])
    pay=float(r['payback_million_cycles'])
    assert abs(a/s/1e6-pay)<1e-10
    assert abs(a-s*5e6-float(r['climate_delta_kg_CO2e_during_test']))<1e-10
    carbon.append({'layout':'circle' if r['layout']=='Circle 0800' else 'sector',
      'route':'milling' if r['route']=='milling' else 'wire', 'process':r['process_id'],
      'nominal':r['nominal']=='1', 'frv':float(r['FRV_L_per_100km_per_100kg']),
      'initialKg':a,'savingKgPerCycle':s,'paybackMillionCycles':pay,
      'deltaAt5MillionKg':float(r['climate_delta_kg_CO2e_during_test'])})
assert len(carbon)==48

payload={'release':'0.1.0','date':'2026-11-12','author':'Abdulkadir Oshioze Nurudeen',
  'orcid':'0000-0002-2646-5784','dataDoi':'10.5281/zenodo.24144925','benchmarkDoi':'10.5281/zenodo.24055230',
  'dataRelease':'2.0.0','licence':'CC BY 4.0','scope':'Ten pre-specified test layouts; five related load mixtures per layout; reference steel on screening meshes. Carbon scenarios are separate 40-tooth cases.',
  'referenceSteel':{'E_GPa':210,'poissonRatio':.3,'yieldStrengthMPa':695,'densityKgMm3':density},
  'loads':{'T':{'torqueNm':177.909,'speedRpm':1881.8609513852587},'P':{'torqueNm':152.23170306739792,'speedRpm':3136.434918975431}},
  'fatigueReferenceCycles':5000000,'cases':cases,'carbon':carbon,'sourceSha256':digests}
(D/'atlas.json').write_text(json.dumps(payload,separators=(',',':'))+'\n')

for src, name in [(W/'prospective/all_100_response_rows.csv','test-responses.csv'),
                  (W/'anchor_model/prospective_evaluation_rows.csv','static-model-comparison.csv'),
                  (R/'Data_S1/figure4_scenario_sources.csv','carbon-scenarios.csv'),
                  (R/'LICENSE_DATA.txt','DATA-LICENCE.txt')]:
    shutil.copy2(src,D/name)
for name in ['figS1_native_fields.png','figS2_mesh_load.png','fig3_prospective_errors.png']:
    shutil.copy2(S/'assets'/name,P/'dist/assets'/name)

manifest={'status':'PASS','scope':'Data extraction and geometry reproduction only; no new finite-element solutions.',
  'testLayouts':len(cases),'savedResponseComparisons':len(responses),'staticHComparisons':len(harmonic),
  'carbonScenarios':len(carbon),'checked':'All geometry area/ligament features and primary/fatigue model predictions match the frozen source records; all carbon paybacks and five-million-cycle values match.',
  'derivedGeometry':'Actual archived profile and opening functions; only geometry definitions executed. SVG coordinates rounded to 0.001 mm for display; numerical values use full precision.',
  'sourceSha256':digests,'atlasJsonSha256':hashlib.sha256((D/'atlas.json').read_bytes()).hexdigest()}
(D/'provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
shutil.copy2(R/'LICENSE_CODE.txt',P/'LICENSE')
print(json.dumps({k:v for k,v in manifest.items() if k!='sourceSha256'},indent=2))
