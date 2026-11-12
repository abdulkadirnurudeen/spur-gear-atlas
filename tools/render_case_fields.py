"""Recover and plot preserved P1 fields without a new elasticity solve.

Requires raw mesh and the retained tooth-position NPZ for each selected case.
Each byte identity and displacement array is checked before recovery. Regional
VM maxima must reproduce the stored FE assessment to 2e-9 relative error.
"""
from pathlib import Path
import argparse,ast,hashlib,itertools,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri

a=argparse.ArgumentParser();a.add_argument('--raw',type=Path,required=True);a.add_argument('--numerical',type=Path,required=True);args=a.parse_args()
P=Path(__file__).resolve().parents[1];D=P/'dist/data';E=json.load((D/'engineering.json').open());root=args.raw.resolve();N=args.numerical.resolve()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=[N/'Code_S2/implementation/review_work/native/extracted/archived_source/original_drivers/recover_fatigue_history.py',N/'Code_S2/implementation/review_work/native/extracted/archived_source/gear_steel_design/recover_objective_regions.py']
ns={'np':np,'E':210000.,'NU':.3,'combinations':itertools.combinations}
for p,name in zip(sources,['tensors','radial_range']):
 tree=ast.parse(p.read_text());node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name)
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(p),'exec'),ns)
out=P/'dist/assets/case-fields';out.mkdir(exist_ok=True);receipts={}
for id,e in E['cases'].items():
 tooth=max(e['regionalStressByTooth'],key=lambda r:r['main']['tooth_root'])['tooth']
 selected=[v for v in e['rawFiles'] if v['path'].split('/')[-1] in ['mesh.npz',f'tooth{tooth:02}.npz']]
 for f in selected:assert sha(root/f['path'])==f['sha256'],(id,f['path'])
 meshpath=next(root/f['path'] for f in selected if f['path'].endswith('mesh.npz'));upath=next(root/f['path'] for f in selected if f['path'].endswith(f'tooth{tooth:02}.npz'))
 with np.load(meshpath,allow_pickle=False) as z:xyz=z['mesh_p_0'].T.copy();nodes=z['mesh_t_0'].T.copy()
 with np.load(upath,allow_pickle=False) as z:receipt=json.loads(str(z['record']));u=z['U'][:2].copy()
 assert receipt['tooth']==tooth and receipt['binding']['mesh_sha256']==e['geometry']['mesh_sha256']
 for i,k in enumerate(['main','secondary']):assert hashlib.sha256(np.ascontiguousarray(u[i]).view(np.uint8)).hexdigest()==receipt['direct'][k]['U_sha256']
 u=u.reshape((2,len(xyz),3));vm=np.empty((2,len(nodes)));peaks={k:{r:0. for r in ['web','rim','tooth_root','tooth_flank']} for k in ['main','secondary']}
 g=e['geometry'];bands={'web':(22.5,g['root_radius_mm']-10),'rim':(g['root_radius_mm']-10,g['root_radius_mm']-1),'tooth_root':(g['root_radius_mm']-1,g['pitch_radius_mm']-1),'tooth_flank':(g['pitch_radius_mm']-2.5,np.inf)}
 for start in range(0,len(nodes),10000):
  cells=nodes[start:start+10000];pts=xyz[cells];inverse=np.linalg.inv(pts[:,1:]-pts[:,:1]);s=ns['tensors'](u,cells,inverse)
  s[...,np.arange(3),np.arange(3)]-=np.trace(s,axis1=-2,axis2=-1)[...,None]/3
  v=np.sqrt(1.5*np.sum(s*s,axis=(-1,-2)));vm[:,start:start+len(cells)]=v
  lo,hi=ns['radial_range'](pts[:,:,:2])
  for region,(lower,upper) in bands.items():
   chosen=(hi>=lower)&(lo<=upper)
   if chosen.any():
    for i,k in enumerate(['main','secondary']):peaks[k][region]=max(peaks[k][region],float(v[i,chosen].max()))
 discrepancy=max(abs(peaks[k][r]/receipt['peaks'][k]['geometry_aware'][r]['peak_VM_MPa']-1) for k in peaks for r in peaks[k])
 assert discrepancy<2e-9,(id,discrepancy)
 faces=[];parents=[];zmax=xyz[:,2].max()
 for face in itertools.combinations(range(4),3):
  test=nodes[:,face];mask=np.all(np.abs(xyz[test,2]-zmax)<1e-8,axis=1)
  faces.append(test[mask]);parents.append(np.flatnonzero(mask))
 faces=np.concatenate(faces);parents=np.concatenate(parents);used=np.unique(faces);mapping=np.full(len(xyz),-1);mapping[used]=np.arange(len(used));tri=mtri.Triangulation(xyz[used,0],xyz[used,1],mapping[faces])
 displacement=np.linalg.norm(u[:,used],axis=-1)*1000
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titlesize':11,'figure.facecolor':'white'})
 fig,axes=plt.subplots(2,2,figsize=(11.5,10),layout='constrained');sv=float(vm[:,parents].max());uv=float(displacement.max())
 for i,k in enumerate(['main','secondary']):
  m=axes[0,i].tripcolor(tri,facecolors=vm[i,parents],shading='flat',cmap='viridis',vmin=0,vmax=sv,rasterized=True)
  fig.colorbar(m,ax=axes[0,i],label='von Mises stress (MPa)',shrink=.86)
  d=axes[1,i].tripcolor(tri,displacement[i],shading='gouraud',cmap='viridis',vmin=0,vmax=uv,rasterized=True)
  fig.colorbar(d,ax=axes[1,i],label='Displacement magnitude (µm)',shrink=.86)
  l=receipt['direct'][k]['load'];rpm=receipt['direct'][k]['rpm'];label='T' if i==0 else 'P'
  axes[0,i].set_title(f'{label}: {l["requested_torque_Nmm"]/1000:.3f} Nm · {rpm:.2f} rpm\nUnsmoothed P1 element stress, axial top surface')
  axes[1,i].set_title(f'{label}: nodal displacement magnitude\nUndeformed geometry; no displacement amplification')
 for ax in axes.flat:ax.set_aspect('equal');ax.set_xlabel('x (mm)');ax.set_ylabel('y (mm)');ax.set_xlim(-110,110);ax.set_ylim(-110,110)
 fig.suptitle(f'SpurAtlas {id} · {e["sourceCase"]}\nRetained reference steel: E = 210 GPa, ν = 0.3 · tooth position {tooth} (T tooth-root-governing position)',fontsize=13)
 filename=f'{id}_Troot_tooth{tooth:02}_reference.png';fig.savefig(out/filename,dpi=170);plt.close(fig)
 field={'image':'assets/case-fields/'+filename,'tooth':tooth,'loadReferences':['T','P'],'materialReference':'E 210 GPa, nu 0.3; stored research steel','view':'Axial top surface, undeformed coordinates. P1 stress is unsmoothed per element; displacement is nodal P1 magnitude. The selected tooth position governs retained T tooth-root regional stress, not necessarily every region or P.','regionalRecoveryMaximumRelativeDiscrepancy':discrepancy,'topSurfaceStressMaxMPa':[float(vm[i,parents].max()) for i in range(2)],'wholeMeshStressMaxMPa':[float(vm[i].max()) for i in range(2)],'topSurfaceDisplacementMaxMicrometre':[float(displacement[i].max()) for i in range(2)],'rawSourceFiles':{str(p.relative_to(root)):sha(p) for p in [meshpath,upath]},'recoverySourceHashes':{str(p.relative_to(N)):sha(p) for p in sources},'imageSha256':sha(out/filename),'newElasticitySolve':False}
 e['fieldPlot']=field;e['displayScope']='Case-linked stress summaries and byte-authenticated raw T/P field recovery at the retained T tooth-root-governing position. Screening mesh; no new elasticity solution or physical qualification.'
 entry=D/f'cases/{id}-evidence.json';entry.write_text(json.dumps(e,separators=(',',':'))+'\n');receipts[id]=field
 print(id,'PASS','regional relative discrepancy',f'{discrepancy:.3e}',flush=True)
(D/'engineering.json').write_text(json.dumps(E,separators=(',',':'))+'\n');(D/'field-recovery.json').write_text(json.dumps(receipts,indent=2)+'\n')
prov=json.load((D/'provenance.json').open());prov['caseFieldRecovery']={'cases':10,'scope':'Byte-authenticated raw displacement-field recovery and top-surface plots only; no new elasticity solution','receiptSha256':sha(D/'field-recovery.json')};(D/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
