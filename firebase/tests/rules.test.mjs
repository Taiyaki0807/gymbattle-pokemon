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
