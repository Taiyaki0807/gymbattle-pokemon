import test from 'node:test';
import assert from 'node:assert/strict';
import {TYPES,STATUSES,blankRatings,validBoardId,normalizeMember,filterMembers,visibleTypes,parseBackup,toDocument,fromDocument,storageField} from '../src/domain.js';

test('18 types end with normal and contain five symbols',()=>{
  assert.equal(TYPES.length,18);assert.equal(TYPES.at(-1)[0],'normal');assert.deepEqual(STATUSES.map(x=>x[1]),['◎','〇','△','×','-']);
});
test('36 cells are independent, all start at x',()=>{
  const ratings=blankRatings();assert.equal(Object.keys(ratings).length,36);
  ratings.fire_physical.status='excellent';assert.equal(ratings.fire_special.status,'no');assert.equal(blankRatings().fire_physical.status,'no');
});
test('multiple types keep canonical order and never expose other columns',()=>{
  assert.deepEqual(visibleTypes(new Set(['normal','fire'])).map(x=>x[0]),['fire','normal']);assert.equal(visibleTypes(new Set()).length,18);
});
test('filters match the same cell and any selected type',()=>{
  const first={name:'あおい',notes:'',ratings:blankRatings()},second={name:'みどり',notes:'',ratings:blankRatings()};
  first.ratings.fire_physical.status='yes';second.ratings.water_special.status='yes';
  assert.deepEqual(filterMembers([first,second],{types:new Set(['fire','water']),category:'physical',status:'yes'}),[first]);
  assert.deepEqual(filterMembers([first,second],{query:'みど',types:new Set(['water']),category:'special',status:'yes'}),[second]);
});
test('backup excludes metadata and validates all cells before import',()=>{
  const member={id:'private-id',name:' 名前 ',notes:'メモ',ratings:blankRatings(),createdAt:'ignored'};
  const imported=parseBackup(JSON.stringify({version:1,members:[member]}));
  assert.deepEqual(Object.keys(imported[0]),['name','notes','ratings']);assert.equal(imported[0].name,'名前');
  member.ratings.fire_physical.status='invalid';assert.throws(()=>normalizeMember(member));
  assert.throws(()=>parseBackup('{bad'));assert.throws(()=>parseBackup(JSON.stringify({version:2,members:[]})));
});
test('bad name and oversized notes are rejected',()=>{
  for(const name of ['', '  ', 'a'.repeat(61)]) assert.throws(()=>normalizeMember({name,notes:'',ratings:blankRatings()}));
  assert.throws(()=>normalizeMember({name:'a',notes:'a'.repeat(1001),ratings:blankRatings()}));
});
test('board IDs must be long URL-safe values',()=>{
  assert.equal(validBoardId('a'.repeat(48)),true);
  for(const id of ['', 'short', '../'+'a'.repeat(40),'a'.repeat(81)]) assert.equal(validBoardId(id),false);
});
test('storage conversion round-trips and targets separate cell fields',()=>{
  const member={name:'共有',notes:'メモ',ratings:blankRatings()};
  member.ratings.fire_special={status:'unset',condition:'条件'};
  const document=toDocument(member);
  assert.equal(document.ratings.fire_special,'unset');assert.equal(document.conditions.fire_special,'条件');
  const restored=fromDocument(document);assert.deepEqual(normalizeMember(restored),member);
  assert.equal(storageField('ratings.fire_special.status'),'ratings.fire_special');
  assert.equal(storageField('ratings.fire_special.condition'),'conditions.fire_special');
  assert.throws(()=>storageField('ratings.invalid.status'));
});
