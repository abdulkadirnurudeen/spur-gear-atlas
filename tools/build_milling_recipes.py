"""Generate geometry-specific recipes with the unchanged retained LCA planner.

No FE solve or source inventory is modified. The source archive is authenticated
before using its cutter, reach, swept-area and finishing-travel rules.
"""
from pathlib import Path
import argparse,csv,hashlib,importlib.util,json,math,sqlite3,sys,tempfile
import numpy as np

P=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--lca-dir',type=Path,required=True);ap.add_argument('--lca-archive',type=Path,required=True);ap.add_argument('--route-source',type=Path,required=True)
args=ap.parse_args();R=args.lca_dir.resolve();route=args.route_source.resolve()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(args.lca_archive)=='dc3adbcb91dc33a758659dbaeea761a924e84ca6096f6c89c8ebd0862c435c04'
sys.path[:0]=[str(R),str(route)]
from build_full_atlas_lca import load_phase7
from process_inventory import opening_shapes
from sector_rest_milling import plan_geometry,sample_opening
from validate_break_even import milling_legs
from break_even_law import manufacturing,road_projection
config=json.loads((R/'phase8_inputs.json').read_text());data=json.loads((P/'dist/data/atlas.json').read_text());eng=json.loads((P/'dist/data/engineering.json').read_text())

class OneShape:
 def __init__(self,ident,curves):self.ident=ident;self.curves=curves
 def execute(self,_):return [(self.ident,json.dumps({'openings':self.curves}))]

def prepare(c,curves,phase1,inputs1):
 profile=opening_shapes(OneShape(c['id'],curves))[c['id']]
 gear={'teeth':c['teeth'],'module_mm':c['pitchDiameter']/c['teeth'],'face_mm':c['faceWidth'],'opening_count':len(curves),'total_opening_area_mm2':c['openingAreaMm2'],'total_opening_perimeter_mm':c['openingPerimeterMm']}
 sector=None
 if c['family']=='sector':
  rasters=[sample_opening(np.asarray(curves[0]).T,h) for h in config['sector_rest_milling']['grid_reference_steps_mm']]
  entry={'saved_atlas_geometry':{'scale':1.,'face_mm':c['faceWidth'],'id':c['id']},'geometry_basis':{'volume_removed_mm3':c['openingAreaMm2']*c['faceWidth']}}
  sector=plan_geometry(entry,profile,rasters,config,inputs1,phase1)
 legs,setups=milling_legs(c['family'],gear,profile,config,sector)
 assert len(legs)==2
 if sector:
  tools=[sector['roughing_tool'],sector['finishing_tool']];faces=2
 else:
  tools=[next(t for t in config['milling']['tools'] if t['diameter_mm']==legs[0]['diameter_mm'])]*2;faces=setups
 for i,leg in enumerate(legs):
  leg.update(operation='Bulk roughing' if i==0 else 'Wall and corner finishing',catalogueEDP=tools[i]['edp'],fluteLengthMm=tools[i]['flute_length_mm'],neckReachMm=tools[i].get('neck_reach_mm'),axialLevelsPerFace=round(c['faceWidth']/faces/leg['axial_depth_mm']),maximumAxialDepthMm=tools[i]['catalogue_axial_limit_mm'] if sector and i==1 else .75*tools[i]['diameter_mm'])
 return {'id':c['id'],'family':c['family'],'gear':gear,'legs':legs,'setupCount':setups,'machiningFaces':faces,'distinctTools':len({l['catalogueEDP'] for l in legs}),'access':None if not sector else {k:sector[k] for k in ['rough_swept_area_fraction','coarse_grid_rough_swept_area_fraction','finish_sampled_sweep_fraction','minimum_required_reach_mm','reference_grid_steps_mm']},'profile':profile,'source':'Retained LCA08 milling and sector-rest-milling rules; applied to this exact sampled opening geometry.','catalogueUrl':config['sources']['OSG_WXL']}

recipes={};fixtures=[]
with tempfile.TemporaryDirectory(prefix='atlas-milling-planner-') as tmp:
 _,_,_,phases=load_phase7(config['phase7'],Path(tmp));inputs1=phases[1][0];phase1=phases[1][2]
 for c in data['cases']:
  boundaries={}
  for row in csv.DictReader((P/'dist/data/cases'/f'{c["id"]}-coordinates.csv').open()):boundaries.setdefault(int(row['boundary']),[]).append([float(row['x_mm']),float(row['y_mm'])])
  curves=[np.asarray(v).T.tolist() for k,v in sorted(boundaries.items()) if k>=2]
  recipes[c['id']]=prepare(c,curves,phase1,inputs1)
 # Recover the two original page recipes directly from the immutable inventory.
 db=sqlite3.connect((R/'Atlas007_LCA.sqlite').as_uri()+'?mode=ro&immutable=1',uri=True);original={}
 for layout,gid in [('circle','sizecmp_circle_n5_s0800_20261024_m3_S2'),('sector','sizecmp_sector_n5_s0950_20261024_m3_S2')]:
  row=db.execute('SELECT inventory_json FROM process_cases WHERE geometry_id=? AND nominal=1 AND route<>? ',(gid,'wire_edm_P20_kerf_volume_benchmark')).fetchall()
  assert len(row)==1,(layout,len(row));inv=json.loads(row[0][0]);g=json.loads(db.execute('SELECT inventory_json FROM geometries WHERE geometry_id=?',(gid,)).fetchone()[0])
  geom=g['saved_atlas_geometry'];basis=g['polygon_geometry_basis'];V=basis['volume_removed_mm3'];faces=inv['machining_faces'] if layout=='circle' else 2
  if layout=='circle':
   tool=inv['cutter'];legs=[{'diameter_mm':tool['diameter_mm'],'feed_mm_min':tool['feed_mm_min'],'rpm':tool['rpm'],'flutes':4,'volume_fraction':inv[key]/V,'axial_depth_mm':inv['axial_depth_mm'],'radial_engagement_mm':inv['rough_radial_engagement_mm'] if i==0 else inv['finish_allowance_mm'],'contour_floor_min':0.,'catalogueEDP':tool['edp'],'operation':'Bulk roughing' if i==0 else 'Wall and corner finishing','fluteLengthMm':tool['flute_length_mm']} for i,key in enumerate(['rough_volume_mm3','finish_volume_mm3'])]
  else:
   plan=inv['sector_milling_plan'];temp={'id':'original-sector','family':'sector','faceWidth':geom['face_mm'],'teeth':40,'pitchDiameter':200,'openingAreaMm2':V/geom['face_mm'],'openingPerimeterMm':g['opening_profile_reference_dimensions']['perimeter_mm']}
   legs,_=milling_legs('sector',{'total_opening_area_mm2':temp['openingAreaMm2'],'total_opening_perimeter_mm':temp['openingPerimeterMm'],'face_mm':geom['face_mm'],'opening_count':5},{},config,plan)
   for i,leg in enumerate(legs):
    tool=plan['roughing_tool' if i==0 else 'finishing_tool'];leg.update(catalogueEDP=tool['edp'],operation='Bulk roughing' if i==0 else 'Wall and corner finishing',fluteLengthMm=tool['flute_length_mm'],neckReachMm=tool.get('neck_reach_mm'))
  operations=[]
  for leg in legs:
   d=leg['diameter_mm'];ae=leg['radial_engagement_mm'];ap=leg['axial_depth_mm'];feed=leg['feed_mm_min'];chip=2*ae/d/math.acos(1-2*ae/d)*feed/(4*leg['rpm']);v=V*leg['volume_fraction'];work=v*2140*chip**(-.25)/3.6e9;minutes=max(v/(ap*ae*feed),leg['contour_floor_min'])
   operations.append({'operation':leg['operation'],'catalogueEDP':leg['catalogueEDP'],'diameterMm':d,'flutes':4,'rpm':leg['rpm'],'feedMmMin':feed,'axialDepthMm':ap,'radialEngagementMm':ae,'volumeFraction':leg['volume_fraction'],'volumeMm3':v,'activeMinutes':minutes,'contourFloorMinutes':leg['contour_floor_min'],'mechanicalCuttingKWh':work,'driveElectricityKWh':work/.8,'baseElectricityKWh':2*minutes/60})
  recipe={'id':gid,'legs':legs,'setupCount':round(inv['allocated_noncut_minutes']/4),'machiningFaces':faces,'distinctTools':len({l['catalogueEDP'] for l in legs}),'catalogueUrl':config['sources']['OSG_WXL']}
  result={'recipe':recipe,'operations':operations,'noncutElectricityKWh':2*inv['allocated_noncut_minutes']/60,'chipPressElectricityKWh':inv['press_electricity_kWh']['delta_perforated_minus_solid'],'siteElectricityKWh':inv['site_electricity_for_hole_operation_and_chip_press_kWh']['delta_perforated_minus_solid']}
  assert math.isclose(sum(o['driveElectricityKWh']+o['baseElectricityKWh'] for o in operations)+result['noncutElectricityKWh']+result['chipPressElectricityKWh'],result['siteElectricityKWh'],rel_tol=2e-12)
  original[layout]={'geometryId':gid,'nominalMilling':result}
 db.close()
 machine=next(m for m in inputs1['perforation_milling']['machine_cases'] if m['id']=='nominal_assumption')
 for c in data['cases']:
  recipe=recipes[c['id']]
  for grid in [.18437,0.,.4]:
   coeff={**eng['carbonCoefficients'],'grid_kg_CO2e_kWh':grid}
   for method in ['milling','wire_edm']:
    process={'method':method,'press_dry_feed_kg_h':55,'machine':{**machine,'allocated_setup_count':recipe['setupCount']},'legs':recipe['legs']} if method=='milling' else {'method':method,'press_dry_feed_kg_h':55,'kerf_mm':.28}
    made=manufacturing(recipe['gear'],process,coeff);road=road_projection(made,eng['roadReference']);fixtures.append({'layout':c['id'],'grid':grid,'method':method,'manufacturing':made,'road':road})

provenance={'lcaArchiveSha256':sha(args.lca_archive),'sourceFiles':{n:sha(R/n) for n in ['phase8_inputs.json','process_inventory.py','sector_rest_milling.py']},'routeRecipeBuilderSha256':sha(route/'validate_break_even.py'),'scope':'Regenerated retained milling planning rules and exact-geometry scenario arithmetic only. Material process proxies, machine assumptions and physical-validation scope are unchanged.'}
payload={'schema':'spuratlas-milling-recipes-v1','provenance':provenance,'cases':recipes,'originalCases':original}
(P/'dist/data/milling-recipes.json').write_text(json.dumps(payload,separators=(',',':'))+'\n')
(P/'dist/milling-recipes.js').write_text('// Generated by tools/build_milling_recipes.py from authenticated retained sources.\nexport const millingRecipes='+json.dumps(payload,separators=(',',':'))+';\n')
(P/'tests/multitool-reference-fixtures.json').write_text(json.dumps(fixtures,separators=(',',':'))+'\n')
source=P/'dist/data/milling-source';source.mkdir(exist_ok=True)
for n in ['phase8_inputs.json','process_inventory.py','sector_rest_milling.py']:(source/n).write_bytes((R/n).read_bytes())
print(json.dumps({'recipes':len(recipes),'freshPythonFixtures':len(fixtures),'tools':{k:[x['diameter_mm'] for x in v['legs']] for k,v in recipes.items()}},indent=2))
