import {readFileSync} from 'node:fs';
import {before,after,beforeEach,test} from 'node:test';
import assert from 'node:assert/strict';
import {initializeTestEnvironment,assertFails,assertSucceeds} from '@firebase/rules-unit-testing';
import {doc,collection,setDoc,getDoc,getDocs,updateDoc,deleteDoc,serverTimestamp} from 'firebase/firestore';
import {blankRatings,toDocument} from '../src/domain.js';

const BOARD='test_board_123456789012345678901234567890';
let env,db;
const member=()=>({...toDocument({name:'メンバー',notes:'',ratings:blankRatings()}),order:1,createdAt:serverTimestamp(),updatedAt:serverTimestamp()});
const ref=(database,id='one',board=BOARD)=>doc(database,'boards',board,'members',id);
before(async()=>{
  env=await initializeTestEnvironment({projectId:'demo-gymbattle',firestore:{host:'127.0.0.1',port:8085,rules:readFileSync(new URL('../firestore.rules',import.meta.url),'utf8')}});
});
after(async()=>env?.cleanup());
test('inventory stays separate per member and rejects invalid or orphan entries',async()=>{
  await setDoc(ref(db),member());await setDoc(ref(db,'two'),member());
  const entry=(database,person='one',character='pair-001')=>doc(database,'boards',BOARD,'members',person,'inventory',character);
  const value={owned:true,level:200,moveLevel:2,exRole:true,updatedAt:serverTimestamp()};
  await assertSucceeds(setDoc(entry(db),value));
  await assertSucceeds(setDoc(entry(db,'two'),{...value,owned:false}));
  assert.equal((await getDoc(entry(db))).data().owned,true);
  assert.equal((await getDoc(entry(db,'two'))).data().owned,false);
  await assertFails(setDoc(entry(db,'missing'),value));
  await assertFails(setDoc(entry(db,'one','unknown'),value));
  await assertFails(updateDoc(entry(db),{level:201,updatedAt:serverTimestamp()}));
  await assertFails(updateDoc(entry(db),{owned:'true',updatedAt:serverTimestamp()}));
  await assertFails(updateDoc(entry(db),{moveLevel:6,updatedAt:serverTimestamp()}));
  await assertFails(updateDoc(entry(db),{extra:'invalid',updatedAt:serverTimestamp()}));
  await assertFails(getDoc(entry(env.unauthenticatedContext().firestore())));
  const visitor=env.authenticatedContext('visitor').firestore();
  await assertSucceeds(updateDoc(entry(visitor),{moveLevel:3,updatedAt:serverTimestamp()}));
});
test('candy counts have a fixed bounded numeric schema',async()=>{
  await setDoc(ref(db),member());
  const candy=doc(db,'boards',BOARD,'members','one','supplies','candies');
  const value={yellow:2,green:4,red:1,orange:0,blue:1,purple:1,awakening:3,updatedAt:serverTimestamp()};
  await assertSucceeds(setDoc(candy,value));
  await assertFails(updateDoc(candy,{yellow:-1,updatedAt:serverTimestamp()}));
  await assertFails(updateDoc(candy,{green:1.5,updatedAt:serverTimestamp()}));
  await assertFails(updateDoc(candy,{red:10000,updatedAt:serverTimestamp()}));
  await assertFails(setDoc(doc(db,'boards',BOARD,'members','one','supplies','other'),value));
  await assertFails(getDoc(doc(env.unauthenticatedContext().firestore(),'boards',BOARD,'members','one','supplies','candies')));
});
beforeEach(async()=>{
  await env.clearFirestore();
  await env.withSecurityRulesDisabled(async context=>setDoc(doc(context.firestore(),'boards',BOARD),{enabled:true,schemaVersion:1}));
  db=env.authenticatedContext('anonymous-editor',{firebase:{sign_in_provider:'anonymous'}}).firestore();
});
test('URL holder can read the board, add and edit all five symbols',async()=>{
  await assertSucceeds(getDoc(doc(db,'boards',BOARD)));
  await assertSucceeds(setDoc(ref(db),member()));
  for(const status of ['excellent','yes','conditional','no','unset']) {
    await assertSucceeds(updateDoc(ref(db),{'ratings.fire_physical':status,updatedAt:serverTimestamp()}));
  }
  assert.equal((await getDoc(ref(db))).data().ratings.fire_special,'no');
  await assertSucceeds(getDocs(collection(db,'boards',BOARD,'members')));
  await assertSucceeds(deleteDoc(ref(db)));
});
test('another visitor can edit and observe the same shared member',async()=>{
  await setDoc(ref(db),member());
  const other=env.authenticatedContext('another-visitor').firestore();
  await assertSucceeds(updateDoc(ref(other),{name:'共有編集',updatedAt:serverTimestamp()}));
  assert.equal((await getDoc(ref(db))).data().name,'共有編集');
});
test('unauthenticated API calls cannot read or write',async()=>{
  const guest=env.unauthenticatedContext().firestore();
  await assertFails(getDoc(doc(guest,'boards',BOARD)));
  await assertFails(getDocs(collection(guest,'boards',BOARD,'members')));
  await assertFails(setDoc(ref(guest),member()));
});
test('board enumeration and public board creation or configuration are forbidden',async()=>{
  await assertFails(getDocs(collection(db,'boards')));
  await assertFails(setDoc(doc(db,'boards','b'.repeat(48)),{enabled:true}));
  await assertFails(updateDoc(doc(db,'boards',BOARD),{enabled:false}));
  await assertFails(deleteDoc(doc(db,'boards',BOARD)));
});
test('wrong board or disabled board denies all data access',async()=>{
  await assertFails(setDoc(ref(db,'one','x'.repeat(48)),member()));
  await assertFails(getDocs(collection(db,'boards','x'.repeat(48),'members')));
  await env.withSecurityRulesDisabled(async context=>updateDoc(doc(context.firestore(),'boards',BOARD),{enabled:false}));
  await assertFails(getDoc(doc(db,'boards',BOARD)));
  await assertFails(setDoc(ref(db),member()));
});
test('invalid symbols, missing cells, extra fields, and oversized values are denied',async()=>{
  for(const mutate of [
    data=>{data.ratings.fire_physical='bad';},
    data=>{delete data.ratings.fire_special;},
    data=>{data.ratings.secret={status:'no',condition:''};},
    data=>{data.admin=true;},
    data=>{data.name='';},
    data=>{data.name='a'.repeat(61);},
    data=>{data.notes='a'.repeat(1001);},
    data=>{data.conditions.fire_physical='a'.repeat(201);},
  ]) {const data=member();mutate(data);await assertFails(setDoc(ref(db),data));}
});
test('an update cannot inject fields or overwrite creation metadata',async()=>{
  await setDoc(ref(db),member());
  await assertFails(updateDoc(ref(db),{order:2,updatedAt:serverTimestamp()}));
  await assertFails(updateDoc(ref(db),{createdAt:new Date(0),updatedAt:serverTimestamp()}));
  await assertFails(updateDoc(ref(db),{'ratings.fire_physical.image':'https://example.com',updatedAt:serverTimestamp()}));
});
