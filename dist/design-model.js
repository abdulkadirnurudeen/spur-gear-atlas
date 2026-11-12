import {materialRow,estimate,MIXTURES} from './model.js';
import {millingRecipes} from './milling-recipes.js';
import {KM_PER_MILE,DEFAULT_DISTANCE_KM,toMiles,mileageDecision} from './distance.js';

export const defaults={teeth:42,pitchDiameter:200,faceWidth:30,boreDiameter:30,pressureAngle:20,lambda:.5,cycles:5000000,staticTarget:3,fatigueTarget:3,material:'reference',model:'E',epsilon:.10,allMixtures:false,objective:'mass',family:'all'};
export function operatingPoint(data,lambda) {
  return {torqueNm:lambda*data.loads.T.torqueNm+(1-lambda)*data.loads.P.torqueNm,speedRpm:Math.sqrt(lambda*data.loads.T.speedRpm**2+(1-lambda)*data.loads.P.speedRpm**2)};
}
const near=(a,b,tolerance)=>Number.isFinite(a)&&Math.abs(a-b)<=tolerance;
export function assessRequirements(data,request) {
  const reasons=[];
  for(const k of ['teeth','pitchDiameter','faceWidth','boreDiameter','pressureAngle','torqueNm','speedRpm','cycles','staticTarget','fatigueTarget'])if(!Number.isFinite(request[k])||request[k]<=0)reasons.push(`${k}: enter a positive finite value.`);
  if(!Number.isInteger(request.teeth))reasons.push('Tooth count must be a whole number.');
  if(!Number.isFinite(request.epsilon)||request.epsilon<0||request.epsilon>=1)reasons.push('The assumed relative-error bound must be between 0 and 100%, excluding 100%.');
  if(!MIXTURES.includes(request.lambda))reasons.push('Select one of the five retained load mixtures.');
  if(!['E','H'].includes(request.model))reasons.push('Select the registered E or H static model.');
  if(!['mass','margin'].includes(request.objective))reasons.push('Select a supported ranking objective.');
  if(!['all','circle','sector','superellipse'].includes(request.family))reasons.push('Select a supported opening family.');
  if(!data.materials.some(m=>m.id===request.material))reasons.push('The material condition is not in the verified index.');
  const matched=data.cases.filter(c=>c.teeth===request.teeth);
  if(!matched.length)reasons.push(`No complete case-linked design comparison is retained for ${request.teeth} teeth. The wider research index can still be inspected.`);
  const c=matched[0];
  if(c)for(const [key,label] of [['pitchDiameter','Pitch diameter'],['faceWidth','Face width'],['boreDiameter','Bore diameter'],['pressureAngle','Pressure angle']])if(!near(request[key],c[key],.001))reasons.push(`${label} is outside the retained ${c[key]} ${key==='pressureAngle'?'degree':'mm'} case.`);
  if(request.cycles!==data.fatigueReferenceCycles)reasons.push('The retained fatigue calculation is defined at 5,000,000 counted stress cycles. No different-life prediction is supplied.');
  const op=operatingPoint(data,request.lambda);
  if(!near(request.torqueNm,op.torqueNm,.001)||!near(request.speedRpm,op.speedRpm,.001))reasons.push('Torque and speed must match the selected retained load mixture. Arbitrary load scaling is not validated.');
  if(request.boreDiameter>=request.pitchDiameter)reasons.push('Bore diameter must be smaller than pitch diameter.');
  return {supported:reasons.length===0,reasons,moduleMm:request.pitchDiameter/request.teeth,operatingPoint:op,matchingCases:matched.length,inputMatchingTolerance:'0.001 mm, degree, Nm or rpm for numerical entry only; this is not a manufacturing tolerance.'};
}
export function interval(factor,epsilon) {return {lower:factor/(1+epsilon),upper:factor/(1-epsilon)};}
export function shortlist(data,request) {
  const coverage=assessRequirements(data,request);if(!coverage.supported)return {coverage,rows:[],recommended:null};
  const material=data.materials.find(m=>m.id===request.material);
  const rows=data.cases.filter(c=>c.teeth===request.teeth&&(request.family==='all'||request.family===c.family)).map(c=>{
    const chosen=c.rows.filter(r=>request.allMixtures||r.lambda===request.lambda).map(r=>{
      const v=materialRow(r,material);const st=estimate(v,'static',request.model)*v.static.solidFactor,ft=estimate(v,'fatigue',request.model)*v.fatigue.solidFactor;
      return {lambda:r.lambda,staticReference:v.static.referenceFactor,fatigueReference:v.fatigue.referenceFactor,staticEstimate:st,fatigueEstimate:ft,staticInterval:interval(st,request.epsilon),fatigueInterval:interval(ft,request.epsilon)};
    });
    const minimum=key=>Math.min(...chosen.map(r=>r[key]));
    const referenceStatic=minimum('staticReference'),referenceFatigue=minimum('fatigueReference');
    const lowerStatic=Math.min(...chosen.map(r=>r.staticInterval.lower)),lowerFatigue=Math.min(...chosen.map(r=>r.fatigueInterval.lower));
    const upperStatic=Math.min(...chosen.map(r=>r.staticInterval.upper)),upperFatigue=Math.min(...chosen.map(r=>r.fatigueInterval.upper));
    const meetsReference=referenceStatic>=request.staticTarget&&referenceFatigue>=request.fatigueTarget;
    const meetsConditional=lowerStatic>=request.staticTarget&&lowerFatigue>=request.fatigueTarget;
    const belowConditional=upperStatic<request.staticTarget||upperFatigue<request.fatigueTarget;
    const referral=c.family==='sector'&&c.phi>=.55;
    const status=!meetsReference?'Below recorded-factor target':referral?'Direct FE assessment required':meetsConditional?'Meets conditional screen':belowConditional?'Below model interval target':'Sensitive to assumed error';
    return {id:c.id,family:c.family,teeth:c.teeth,materialRemovalFraction:c.materialRemovalFraction,massRemovedKg:c.massRemovedKg,referenceStatic,referenceFatigue,lowerStatic,lowerFatigue,upperStatic,upperFatigue,meetsReference,meetsConditional,referral,eligible:meetsReference&&meetsConditional&&!referral,status,governingMargin:Math.min(lowerStatic/request.staticTarget,lowerFatigue/request.fatigueTarget)-1,chosen,dominated:false};
  });
  for(const r of rows)r.dominated=rows.some(o=>o.id!==r.id&&o.materialRemovalFraction>=r.materialRemovalFraction&&o.referenceStatic>=r.referenceStatic&&o.referenceFatigue>=r.referenceFatigue&&(o.materialRemovalFraction>r.materialRemovalFraction||o.referenceStatic>r.referenceStatic||o.referenceFatigue>r.referenceFatigue));
  rows.sort((a,b)=>Number(b.eligible)-Number(a.eligible)||(request.objective==='margin'?b.governingMargin-a.governingMargin:b.materialRemovalFraction-a.materialRemovalFraction)||a.id.localeCompare(b.id));
  return {coverage,rows,recommended:rows.find(r=>r.eligible)?.id||null};
}

const stageKeys={cutterMm:'diameter_mm',feedMmMin:'feed_mm_min',rpm:'rpm',flutes:'flutes',axialDepthMm:'axial_depth_mm',radialEngagementMm:'radial_engagement_mm'};
function recipeDefaults(c){
 const recipe=millingRecipes.cases[c.id];if(!recipe)throw new Error('No geometry-checked milling recipe is retained for this case.');
 const values={recipeCaseId:c.id,setupCount:recipe.setupCount};
 for(const [key,source]of Object.entries(stageKeys)){values[key]=recipe.legs[1][source];values['bulk'+key[0].toUpperCase()+key.slice(1)]=recipe.legs[0][source];}
 return values;
}
export const carbonDefaults={grid:.18437,frv:.15,distanceKm:DEFAULT_DISTANCE_KM,cyclesPerKm:166.75013363026054,extraBurden:0,savingFraction:1,baseKW:2,efficiency:.8,noncutMinutes:4,pressKgH:55,kerfMm:.28,...recipeDefaults({id:'G03'})};
export function validateCarbonSettings(s){
 const nonnegative=['grid','baseKW','noncutMinutes','setupCount','distanceKm','cyclesPerKm','extraBurden','frv','savingFraction'];
 const positive=['pressKgH','efficiency','cutterMm','feedMmMin','rpm','axialDepthMm','radialEngagementMm','kerfMm','bulkCutterMm','bulkFeedMmMin','bulkRpm','bulkAxialDepthMm','bulkRadialEngagementMm'];
 for(const key of nonnegative)if(s[key]!==undefined&&(!Number.isFinite(s[key])||s[key]<0))throw new Error(`${key}: enter a finite, nonnegative value.`);
 for(const key of positive)if(s[key]!==undefined&&(!Number.isFinite(s[key])||s[key]<.001))throw new Error(`${key}: enter a finite value of at least 0.001.`);
 for(const key of ['flutes','bulkFlutes'])if(s[key]!==undefined&&(!Number.isSafeInteger(s[key])||s[key]<1))throw new Error('Cutter flute counts must be positive whole numbers.');
 if(s.efficiency>1||s.savingFraction>1)throw new Error('Drive efficiency and retained service-saving fraction must not exceed one.');
}
export function effectiveCarbonSettings(c,input=carbonDefaults,restore=false){
 validateCarbonSettings(input);
 const s={...carbonDefaults,...input};
 if(restore||s.recipeCaseId!==c.id)Object.assign(s,recipeDefaults(c));
 validateCarbonSettings(s);return s;
}
function finiteResult(value){
 for(const v of Object.values(value))if(typeof v==='number'&&!Number.isFinite(v))throw new Error('These inputs exceed the finite calculation range. Revise the inputs before exporting.');
 return value;
}
export function manufacturingScenario(c,settings,coeff,method) {
  const s=effectiveCarbonSettings(c,settings),recipe=millingRecipes.cases[c.id];
  const volume=c.openingAreaMm2*c.faceWidth,mass=volume*coeff.density_kg_mm3,capture=coeff.added_steel_capture_fraction;
  let electricity,time,pressed,transported,water=null,wire=null,curvaturePass=true,operations=[];
  if(method==='milling') {
    let work=0;time=0;
    for(const [i,leg]of recipe.legs.entries()){
      const key=name=>i===0?'bulk'+name[0].toUpperCase()+name.slice(1):name;
      const d=s[key('cutterMm')],ae=s[key('radialEngagementMm')],ap=s[key('axialDepthMm')],feed=s[key('feedMmMin')],rpm=s[key('rpm')],flutes=s[key('flutes')];
      if(d!==leg.diameter_mm)throw new Error('Cutter diameter must match this geometry-checked recipe. Restore the recommended recipe.');
      if(ae>d/2)throw new Error('Radial engagement must not exceed half the cutter diameter.');
      if(ap>leg.maximumAxialDepthMm+1e-12)throw new Error('Axial depth exceeds the retained cutter limit. Restore the recommended recipe or reduce the depth.');
      const arc=Math.acos(1-2*ae/d),chip=2*ae/d/arc*feed/(flutes*rpm),v=volume*leg.volume_fraction;
      const cuttingWork=v*coeff.kc_1_1_N_per_mm2*chip**(coeff.cutting_exponent_1_minus_m-1)/3.6e9;
      const floor=leg.contour_floor_min?recipe.machiningFaces*Math.ceil(c.faceWidth/recipe.machiningFaces/ap)*c.openingPerimeterMm/feed:0;
      const minutes=Math.max(v/(ap*ae*feed),floor);
      operations.push(finiteResult({operation:leg.operation,catalogueEDP:leg.catalogueEDP,diameterMm:d,flutes,rpm,feedMmMin:feed,axialDepthMm:ap,radialEngagementMm:ae,volumeFraction:leg.volume_fraction,volumeMm3:v,activeMinutes:minutes,contourFloorMinutes:floor,mechanicalCuttingKWh:cuttingWork,driveElectricityKWh:cuttingWork/s.efficiency,baseElectricityKWh:s.baseKW*minutes/60}));
      work+=cuttingWork;time+=minutes;
    }
    electricity=work/s.efficiency+s.baseKW*(time+s.noncutMinutes*s.setupCount)/60;
    pressed=capture*mass;transported=pressed;curvaturePass=recipe.legs[1].diameter_mm/2<=c.minimumCurvatureRadiusMm;
  } else if(method==='wire_edm') {
    const e=coeff.edm,lead=c.openingCount*e.lead_mm_per_opening_at_200*c.pitchDiameter/200;
    const kerf=s.kerfMm*c.faceWidth*(c.openingPerimeterMm+lead),drill=c.openingCount*Math.PI*(e.start_hole_diameter_mm/2)**2*c.faceWidth;
    if(kerf+drill>=volume)throw new Error('Kerf and start holes exceed the opening volume.');
    electricity=e.electricity_kJ_per_mm3_kerf*kerf/3600;time=kerf/e.material_removal_mm3_min;
    pressed=capture*coeff.density_kg_mm3*drill;transported=capture*(mass-coeff.density_kg_mm3*kerf);
    water=e.allocated_deionised_water_input_L_h*time/60;wire=e.wire_feed_m_min*time;
  } else throw new Error('Unknown manufacturing route.');
  const siteElectricity=electricity+coeff.press_power_kW*pressed/s.pressKgH;
  const upfront=s.grid*siteElectricity+coeff.scrap_transport_kg_CO2e_kg*transported;
  return finiteResult({method,massRemovedKg:mass,openingVolumeMm3:volume,activeMinutes:time,holeElectricityKWh:electricity,siteElectricityKWh:siteElectricity,upfrontKgCO2e:upfront,waterInputL:water,wireUseM:wire,curvaturePass,operations,recipe:method==='milling'?recipe:null,noncutElectricityKWh:method==='milling'?s.baseKW*s.noncutMinutes*s.setupCount/60:0,chipPressElectricityKWh:coeff.press_power_kW*pressed/s.pressKgH,allocatedSetupCount:method==='milling'?s.setupCount:0,basePowerKW:s.baseKW,driveEfficiency:s.efficiency,noncutMinutesPerSetup:s.noncutMinutes,chipPressFeedKgH:s.pressKgH,productionProcessValidated:false});
}
export function matchedCarbon(c,settings,engineering) {
  const s=effectiveCarbonSettings(c,settings);
  const fuelFactor=engineering.roadReference.combustion_kg_CO2e_L+engineering.roadReference.supply_kg_CO2e_L;
  return ['milling','wire_edm'].map(method=>{
    const m=manufacturingScenario(c,s,engineering.carbonCoefficients,method);
    const savingKm=m.massRemovedKg*s.frv/10000*fuelFactor*s.savingFraction,upfront=m.upfrontKgCO2e+s.extraBurden;
    const breakEvenKm=savingKm>0?upfront/savingKm:upfront===0?0:null;
    const mileage=mileageDecision(breakEvenKm===null?null:toMiles(breakEvenKm),toMiles(s.distanceKm));
    return finiteResult({...m,extraBurdenKgCO2e:s.extraBurden,savingKgCO2ePerKm:savingKm,savingKgCO2ePerMile:savingKm*KM_PER_MILE,breakEvenKm,breakEvenMiles:mileage.paybackMiles,designerMileageMiles:mileage.limitMiles,exceedsDesignerMileage:mileage.exceedsDesignerMileage,paybackMileageStatus:mileage.status,netKgCO2e:upfront-savingKm*s.distanceKm,countedExposure:s.distanceKm*s.cyclesPerKm,withinReferenceExposure:s.distanceKm*s.cyclesPerKm<=5000000+1e-6,remainingUncountedBurdenBudgetKgCO2e:savingKm*s.distanceKm-upfront,scope:'New same-geometry planning calculation using the archived route equation and declared inputs; not a measured inventory or certified LCA. Mileage-to-cycle mapping is a user scenario, not a measured duty history.'});
  });
}
export function productionCapacityRequirement(selection,request,referenceCycles=5000000){
 if(!selection)return null;
 if(!Number.isFinite(request.epsilon)||request.epsilon<0||request.epsilon>=1)throw new Error('The assumed model-error bound must be finite and between zero and one, excluding one.');
 const target=request.fatigueTarget,recorded=selection.referenceFatigue,lower=selection.lowerFatigue;
 for(const value of [target,recorded,lower,referenceCycles])if(!Number.isFinite(value)||value<=0)throw new Error('Fatigue capacity requirements need positive finite safety factors and reference exposure.');
 return finiteResult({requiredFatigueFactor:target,recordedFatigueFactor:recorded,minimumRetainedFraction:target/recorded,conditionalLowerFatigueFactor:lower,minimumRetainedFractionWithAssumedError:target/lower,assumedRelativeModelError:request.epsilon,referenceCycles,measuredMillingCapacityFraction:null,measuredWireEdmCapacityFraction:null,scope:'Minimum capacity requirements at the stated fatigue-assessment exposure. Each manufacturing route must establish its own retained fatigue capacity by production testing. The conditional value also assumes the declared pointwise model-error bound.'});
}
export function makeReport(data,engineering,request,result,selectedId,carbonSettings,project='') {
  const c=data.cases.find(c=>c.id===selectedId),r=result.rows.find(r=>r.id===selectedId);
  const material=data.materials.find(m=>m.id===request.material);
  if(c)carbonSettings=effectiveCarbonSettings(c,carbonSettings);
  return {tool:'SpurAtlas',release:data.release,project,generatedUtc:new Date().toISOString(),requirements:request,coverage:result.coverage,selection:r||null,recommended:result.recommended,rankingRule:request.objective==='mass'?'Largest material removal among compatible cases meeting recorded factors and conditional interval screen; direct-FE referrals excluded.':'Largest minimum conditional margin among compatible cases; direct-FE referrals excluded.',allCompatibleResults:result.rows,productionCapacity:productionCapacityRequirement(r,request,data.fatigueReferenceCycles),geometry:c?{...c,rows:undefined,geometryPath:undefined}:null,material,carbonSettings,mileageInputs:{serviceMileageMiles:toMiles(carbonSettings.distanceKm),countedCyclesPerMile:carbonSettings.cyclesPerKm*KM_PER_MILE,fuelSavingLitresPer100MilesPer100Kg:carbonSettings.frv*KM_PER_MILE},matchedCarbon:c?matchedCarbon(c,carbonSettings,engineering):null,evidence:c?engineering.cases[c.id]:null,modelCoefficients:engineering.coefficients,harmonicModel:engineering.harmonicModel,empiricalErrors:engineering.empiricalErrors,assessmentStatus:{geometricCompatibility:result.coverage.supported?'Matched to retained cases':'Outside retained case scope',numericalEvidence:'Retained screening-mesh FE summaries; separate local refinement is not a convergence certificate for this selected geometry',uncertainty:'Conditional error sensitivity only. No calibrated probabilistic capacity bound established.',toothRootRating:'ISO 6336 tooth-root bending rating not calculated',contactRating:'Mating-gear contact/pitting rating not calculated',productionFatigue:'Matched steel component fatigue testing not completed',manufacturing:'Declared route planning; tool reach, process stability, tolerances and actual machine inputs require verification',climate:'Same-geometry conditional climate comparison; full ISO 14040/14044 LCA compliance not established'},softwareArchive:{doi:'10.5281/zenodo.24165269',version:data.release},sourceData:{doi:data.dataDoi,release:data.dataRelease,atlasSources:data.sourceSha256,engineeringSources:engineering.sources,millingRecipeSources:millingRecipes.provenance},equations:{retention:'R = F_perforated / F_matching_solid',primary:'Rhat = 1 / (1 + exp(theta_family) * phi^n * b_R^(-m) * exp(c*(lambda-0.5)))',interval:'[Fhat/(1+epsilon), Fhat/(1-epsilon)] conditional on a pointwise relative-error bound epsilon',materialStatic:'F = F_reference * yield / 695 MPa',materialFatigue:'F = F_reference * effective_amplitude / 277.7262951561842 MPa',productionCapacity:'kappa_min = required_fatigue_factor / fatigue_factor_before_manufacturing',climate:'Delta_C = C_manufacturing + C_extra - mass_removed * FRV_L_per_100_miles_per_100kg/10000 * fuel_factor * saving_fraction * service_miles'},limitations:engineering.scope};
}
