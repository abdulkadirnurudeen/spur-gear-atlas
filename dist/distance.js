export const KM_PER_MILE=1.609344;
export const DEFAULT_CYCLES_PER_KM=166.75013363026054;
export const DEFAULT_DISTANCE_KM=29984.983466859652;
export const DEFAULT_DISTANCE_MILES=DEFAULT_DISTANCE_KM/KM_PER_MILE;
export const toMiles=km=>km/KM_PER_MILE;
export const toKm=miles=>miles*KM_PER_MILE;
export function carbonDisplayValue(key,value){return key==='distanceKm'?toMiles(value):['cyclesPerKm','frv'].includes(key)?value*KM_PER_MILE:value;}
export function carbonStoredValue(key,value){return key==='distanceKm'?toKm(value):['cyclesPerKm','frv'].includes(key)?value/KM_PER_MILE:value;}
export function mileageDecision(paybackMiles,limitMiles){
 if(!Number.isFinite(limitMiles)||limitMiles<0)throw new Error('Enter a finite, nonnegative service mileage.');
 if(paybackMiles!==null&&(!Number.isFinite(paybackMiles)||paybackMiles<0))throw new Error('Calculated payback must be finite and nonnegative.');
 return {limitMiles,paybackMiles,exceedsDesignerMileage:paybackMiles===null||paybackMiles>limitMiles,status:paybackMiles===null?'No finite payback':paybackMiles>limitMiles?'Beyond chosen mileage':'Within chosen mileage'};
}
