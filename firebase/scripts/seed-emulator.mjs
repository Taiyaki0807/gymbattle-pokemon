import {initializeTestEnvironment} from '@firebase/rules-unit-testing';
import {doc,setDoc,serverTimestamp} from 'firebase/firestore';
import {blankRatings,toDocument} from '../src/domain.js';
const projectId='demo-gymbattle',board='demo_board_123456789012345678901234567890';
const env=await initializeTestEnvironment({projectId,firestore:{host:'127.0.0.1',port:8085}});
await env.withSecurityRulesDisabled(async context=>{
  const db=context.firestore();
  await setDoc(doc(db,'boards',board),{enabled:true,schemaVersion:1});
  const ratings=blankRatings();ratings.fire_physical.status='excellent';ratings.water_special.status='yes';
  await setDoc(doc(db,'boards',board,'members','sample'),{...toDocument({name:'サンプルメンバー',notes:'テスト用データ',ratings}),order:1,createdAt:serverTimestamp(),updatedAt:serverTimestamp()});
});
await env.cleanup();
console.log(`http://127.0.0.1:5173/#b=${board}`);
