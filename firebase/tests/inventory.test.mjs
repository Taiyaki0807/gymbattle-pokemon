import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {filterCharacters,validateEntry,EMPTY_ENTRY} from '../src/inventory-domain.js';
const characters=JSON.parse(readFileSync(new URL('../src/characters.json',import.meta.url),'utf8'));
test('catalog contains 89 distinct named characters from the provided list',()=>{
  assert.equal(characters.length,89);assert.equal(new Set(characters.map(c=>c.id)).size,89);assert.equal(new Set(characters.map(c=>c.name)).size,89);
  assert.deepEqual(characters.slice(0,2).map(c=>c.name),['Cコトネ','Mレッド']);
});
test('ownership filters combine with character name, type and role',()=>{
  const entries={'pair-001':{...EMPTY_ENTRY,owned:true}};
  assert.equal(filterCharacters(characters,entries,{owned:'yes',type:'ほのお',role:'アタッカー'}).length,1);
  assert.equal(filterCharacters(characters,entries,{query:'Mレッド',owned:'no'})[0].id,'pair-002');
  assert.equal(filterCharacters(characters,entries,{query:'Mレッド',owned:'yes'}).length,0);
});
test('entry accepts blanks and rejects out-of-range, fractional and extra fields',()=>{
  assert.deepEqual(validateEntry(EMPTY_ENTRY),EMPTY_ENTRY);
  assert.equal(validateEntry({...EMPTY_ENTRY,level:200,moveLevel:5}).level,200);
  for(const changes of [{level:201},{moveLevel:0},{level:1.5},{owned:'false'},{extra:1}])assert.throws(()=>validateEntry({...EMPTY_ENTRY,...changes}));
});
