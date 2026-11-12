"""Add authenticated research rows and source-checked material conditions.
Run after prepare_data.py. Requires the complete numerical release and the
document evidence directory; no solver, interpolation or model fitting runs.
"""
from pathlib import Path
import argparse,csv,hashlib,json,math

P=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--research',type=Path,required=True);ap.add_argument('--numerical',type=Path,required=True);ap.add_argument('--reports',type=Path,required=True);a=ap.parse_args()
R=a.research;N=a.numerical;I=N/'Code_S2/implementation';D=P/'dist/data'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((N/'Code_S2/implementation_manifest.json').read_text())
for item in manifest['files']:
 f=I/item['path'];assert f.stat().st_size==item['bytes'] and sha(f)==item['sha256'],str(f)
fit=I/'review_program/fitting'
bindings=json.loads((fit/'source_bindings.json').read_text())
for b in bindings:assert sha(fit/'source_data'/b['package_source'])==b['sha256']

records=[];sources={}
def ingest(path,role,kind):
 source=str(path.relative_to(N)) if path.is_relative_to(N) else str(path.relative_to(R/'release'))
 digest=sha(path);sources[source]=digest
 for line,row in enumerate(csv.DictReader(path.open()),2):
  if kind=='development':
   teeth=int(row['teeth']);layout=row['layout'];lam=float(row['load_mix_lambda']);x=float(row['retention_reference']);aa=float(row['a']);bb=float(row['b']);response=row['response'];construction=row['construction'];original=row['source']
  elif kind=='benchmark':
   teeth=42;layout=f"benchmark42_{row['family']}_{row['scale']}";lam=float(row['lambda_main']);x=float(row['reference_retention']);aa=lam;bb=1-lam;response=row['response'];construction='Published displacement-field recovery, matching solid denominator';original=source
   assert abs(float(row['perforated_FoS'])/float(row['solid_FoS'])-x)<2e-12
  else:
   teeth=int(row['teeth']);layout=row['case'];lam=float(row['lambda_main']);x=float(row['reference_retention']);aa=lam;bb=1-lam;response=row['response'];construction='Pre-specified test response on screening mesh';original=source
   assert abs(float(row['perforated_FoS'])/float(row['solid_FoS'])-x)<2e-12
  assert math.isfinite(x) and x>0 and aa>=0 and bb>=0 and abs(lam-aa/(aa+bb))<1e-12
  records.append(dict(teeth=teeth,layout=layout,family=row['family'],response=response,a=aa,b=bb,retention=x,role=role,construction=construction,sourceFile=source,sourceRow=line,sourceSha256=digest,originalSource=original))
for kind in ['static','fatigue']:ingest(fit/(kind+'_development_reconstructed.csv'),'Reconstructed development record','development')
ingest(N/'Data_S1/test_responses_with_geometry.csv','Published benchmark (previously exposed)','benchmark')
ingest(I/'review_program/prospective/all_100_response_rows.csv','Pre-specified geometry test','prospective')
assert len(records)==631 and sorted({r['teeth'] for r in records})==[32,34,36,38,40,42,44,46,48]

# Five published cards match the original reports. The three SAE 8620 cards
# below are corrected to the reports, rather than retaining conflicting fits.
published={
 '20MnCr5_core129_research':(194300.,852.,1356.,-.0703,19),
 '20MnCr5_core130_research':(194200.,1071.,1994.,-.082,19),
 'SAE8620_core119_research':(211800.,693.5,1638.8,-.1007,22),
 'SAE8620_core120_research':(210300.,795.8,1910.2,-.1028,22),
 'SAE8620_core121_research':(213500.,989.5,2209.9,-.0987,23),
 'SAE4320_core122_research':(194200.,620.5,1269.,-.081,19),
 'SAE4320_core123_research':(194300.,745.,1215.,-.066,18),
 'SAE4320_core124_research':(193600.,867.,1547.,-.057,19)}
cards=json.loads((R/'evidence/material_cards.json').read_text());materials=[];audits=[]
for c in cards:
 reference=c['id']=='20MnCr5_core128_research'
 if reference:
  m=dict(id='reference',label='20MnCr5 · original research reference',grade='20MnCr5',condition='128 research reference',E_GPa=210.,yieldMPa=695.,fatigueMPa=c['conditional_capacity_MPa'],sourceUrl='https://doi.org/10.5281/zenodo.24144925',basis='Inherited research reference. The fatigue amplitude is a declared study input, not a newly verified published Basquin fit.',reference=True)
 else:
  E,sy,sf,b,page=published[c['id']];capacity=.8*sf*(2*5000000)**b
  correction=any(abs(c[key]-v)>1e-9 for key,v in [('E_MPa',E),('yield_MPa',sy),('published_Basquin_coefficient_MPa',sf),('published_Basquin_exponent',b)])
  pdf=a.reports/(c['id']+'.pdf');assert pdf.exists()
  report=c['source']['published_report_url']
  m=dict(id=c['id'],label=c['standard_grade_name']+' · core '+c['id'].split('core')[1].split('_')[0],grade=c['standard_grade_name'],condition=c['state'],E_GPa=E/1000,yieldMPa=sy,fatigueMPa=capacity,basquinMPa=sf,basquinExponent=b,sourceUrl=report,sourcePage=page,sourceTable='Table 2',reference=False,corrected=correction,basis='Published homogeneous simulated-core specimen condition; comparative calculation with study assumptions, not a production allowable.')
  audits.append(dict(id=c['id'],status='CORRECTED_TO_PRIMARY_REPORT' if correction else 'MATCHES_PRIMARY_REPORT',reportUrl=report,pdfPage=page,table='Table 2',reportSha256=sha(pdf),published=dict(E_MPa=E,yield_MPa=sy,sigma_f_MPa=sf,basquin_b=b),previousCard=dict(E_MPa=c['E_MPa'],yield_MPa=c['yield_MPa'],sigma_f_MPa=c['published_Basquin_coefficient_MPa'],basquin_b=c['published_Basquin_exponent']),effectiveAmplitudeMPa=capacity,verification='Original report property table checked; SAE8620 scanned tables visually inspected.'))
 m.update(poissonRatio=.3,densityKgM3=7800,referenceCycles=5000000,amplitudeFactor=.8,findleyK=[.2,.3]);materials.append(m)
assert len(materials)==9 and sum(x.get('corrected',False) for x in materials)==3
summary=[]
for t in sorted({r['teeth'] for r in records}):
 rr=[r for r in records if r['teeth']==t]
 summary.append(dict(teeth=t,static=sum(r['response']=='static' for r in rr),fatigue=sum(r['response']=='fatigue' for r in rr),layouts=len({r['layout'] for r in rr}),roles=sorted({r['role'] for r in rr})))
coverage=dict(release='0.2.0',records=records,toothCounts=summary,sourceSha256=sources,sourceBindings=bindings,verification=dict(sourceManifestFilesChecked=len(manifest['files']),sourceBindingsChecked=len(bindings),recordCount=len(records),scope='SHA-256 source authentication and reproduced retained-summary arithmetic. Not new raw-field solves or experimental verification. Reconstructed records retain explicit centring and source-control provenance.'))
(D/'coverage.json').write_text(json.dumps(coverage,separators=(',',':'))+'\n')
with (D/'research-index.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
audit=dict(date='2026-11-12',status='PASS_WITH_THREE_SOURCE_CORRECTIONS',originalCardsSha256=sha(R/'evidence/material_cards.json'),referencePolicy=materials[0]['basis'],cards=audits,scaling='Static factors multiply by Sy/695; fatigue factors multiply by effective_amplitude/277.7262951561842. Uniform linear elasticity, fixed geometry/load/nu/density; material changes do not establish new FE or component validation.',sourceRestriction='Waterloo supplies research-example data, not production design allowables.')
(D/'material-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
(D/'materials.json').write_text(json.dumps(materials,indent=2)+'\n')
atlas=json.loads((D/'atlas.json').read_text());atlas.update(materials=materials,release='0.2.0');(D/'atlas.json').write_text(json.dumps(atlas,separators=(',',':'))+'\n')
prov=json.loads((D/'provenance.json').read_text());prov.update(expandedCoverage=coverage['verification'],materialAudit='material-audit.json',atlasJsonSha256=sha(D/'atlas.json'));(D/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
print(json.dumps(dict(status='PASS',records=len(records),counts=summary,materialOptions=len(materials),publishedConditions=8,sourceCorrections=3),indent=2))
