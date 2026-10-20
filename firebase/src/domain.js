export const TYPES = [
  ['fire','ほのお'],['water','みず'],['electric','でんき'],['grass','くさ'],['ice','こおり'],['fighting','かくとう'],
  ['poison','どく'],['ground','じめん'],['flying','ひこう'],['psychic','エスパー'],['bug','むし'],['rock','いわ'],
  ['ghost','ゴースト'],['dragon','ドラゴン'],['dark','あく'],['steel','はがね'],['fairy','フェアリー'],['normal','ノーマル'],
];
export const CATEGORIES = [['physical','物理'],['special','特殊']];
export const STATUSES = [['excellent','◎'],['yes','〇'],['conditional','△'],['no','×'],['unset','-']];
export const CELL_KEYS = TYPES.flatMap(([type]) => CATEGORIES.map(([category]) => `${type}_${category}`));
export function blankRatings() { return Object.fromEntries(CELL_KEYS.map(key => [key,{status:'no',condition:''}])); }
export function validBoardId(value) { return /^[a-zA-Z0-9_-]{32,80}$/.test(value || ''); }
export function normalizeMember(value) {
  if (!value || typeof value.name !== 'string' || !value.name.trim() || value.name.trim().length > 60) throw new Error('名前は1～60文字で入力してください。');
  if (typeof value.notes !== 'string' || value.notes.length > 1000) throw new Error('メモは1000文字以内で入力してください。');
  const ratings = value.ratings;
  if (!ratings || Object.keys(ratings).length !== 36 || !CELL_KEYS.every(key => Object.hasOwn(ratings,key))) throw new Error('36セルの記号が必要です。');
  for (const key of CELL_KEYS) {
    const cell = ratings[key];
    if (!cell || Object.keys(cell).sort().join(',') !== 'condition,status' || !STATUSES.some(([status])=>status===cell.status) || typeof cell.condition !== 'string' || cell.condition.length > 200) throw new Error('記号または条件メモが正しくありません。');
  }
  return {name:value.name.trim(),notes:value.notes,ratings:structuredClone(ratings)};
}
export function visibleTypes(selected) { return TYPES.filter(([type]) => !selected.size || selected.has(type)); }
export function filterMembers(members,{query='',types=new Set(),category='',status=''}) {
  const keys = visibleTypes(types).flatMap(([type])=>CATEGORIES.filter(([key])=>!category||key===category).map(([key])=>`${type}_${key}`));
  return members.filter(member=>member.name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()) && (!status || keys.some(key=>member.ratings[key]?.status===status)));
}
export function parseBackup(text) {
  const data = JSON.parse(text);
  if (data.version !== 1 || !Array.isArray(data.members) || data.members.length > 100) throw new Error('対応する形式のバックアップではありません（最大100人）。');
  return data.members.map(normalizeMember);
}
export function toDocument(member) {
  const clean=normalizeMember(member);
  return {name:clean.name,notes:clean.notes,
    ratings:Object.fromEntries(CELL_KEYS.map(key=>[key,clean.ratings[key].status])),
    conditions:Object.fromEntries(CELL_KEYS.map(key=>[key,clean.ratings[key].condition]))};
}
export function fromDocument(data) {
  return {...data,ratings:Object.fromEntries(CELL_KEYS.map(key=>[key,{status:data.ratings[key],condition:data.conditions[key]}]))};
}
export function storageField(field) {
  if(!field.startsWith('ratings.')) return field;
  const [,key,property]=field.split('.');
  if(!CELL_KEYS.includes(key)||!['status','condition'].includes(property)) throw new Error('Invalid cell');
  return `${property==='status'?'ratings':'conditions'}.${key}`;
}
