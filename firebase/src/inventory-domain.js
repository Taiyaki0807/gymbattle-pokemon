export const CANDIES=[['yellow','黄'],['green','緑'],['red','赤'],['orange','橙'],['blue','青'],['purple','紫'],['awakening','超覚醒']];
export const EMPTY_ENTRY={owned:false,level:null,moveLevel:null,exRole:false};
export const LEVEL_OPTIONS=[140,150,180,200];
export const MOVE_LEVEL_OPTIONS=Array.from({length:10},(_,i)=>i+1);
export function validateEntry(value){
  if(!value||Object.keys(value).sort().join(',')!=='exRole,level,moveLevel,owned'||typeof value.owned!=='boolean'||typeof value.exRole!=='boolean'||!(value.level===null||Number.isInteger(value.level)&&value.level>=1&&value.level<=200)||!(value.moveLevel===null||Number.isInteger(value.moveLevel)&&value.moveLevel>=1&&value.moveLevel<=10))throw Error('手持ち情報の値が正しくありません。');
  return {...value};
}
export function filterCharacters(characters,entries,{query='',type='',role='',owned=''}={}){
  return characters.filter(c=>c.name.toLowerCase().includes(query.trim().toLowerCase())&&(!type||c.type===type)&&(!role||c.role===role)&&(!owned||(entries[c.id]?.owned===true)===(owned==='yes')));
}
