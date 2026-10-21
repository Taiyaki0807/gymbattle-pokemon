import './style.css';
import {createInventory} from './inventory.js';
import {initializeApp} from 'firebase/app';
import {getAuth,signInAnonymously,connectAuthEmulator} from 'firebase/auth';
import {getFirestore,collection,doc,getDoc,onSnapshot,updateDoc,setDoc,deleteDoc,serverTimestamp,writeBatch,connectFirestoreEmulator} from 'firebase/firestore';
import {TYPES,CATEGORIES,STATUSES,blankRatings,validBoardId,normalizeMember,visibleTypes,filterMembers,parseBackup,toDocument,fromDocument,storageField} from './domain.js';

const $ = id => document.getElementById(id);
const table = $('table-body').closest('table');
function element(tag,text,attrs={}) {
  const node=document.createElement(tag);
  if(text!==null) node.textContent=text;
  for(const [key,value] of Object.entries(attrs)) node.setAttribute(key,value);
  return node;
}
const state={members:[],filters:{query:'',types:new Set(),category:'',status:''},ready:false};
let db, board, memberCollection, unsubscribe;
let inventory;
const writes=new Map();
let saving=false, failed=false, deferred=false, busy=false, operationError='';
function notice(text,error=false) { $('save-status').textContent=text; $('save-status').classList.toggle('error',error); }
function syncStatus() {
  $('retry').hidden=!failed;
  $('add').disabled=!state.ready||busy||writes.size>0;
  $('backup').disabled=!state.ready;
  $('restore').disabled=!state.ready||busy||writes.size>0;
  if(failed) notice('保存できない変更があります。入力を残しています。「保存を再試行」を押してください。',true);
  else if(operationError) notice(operationError,true);
  else if(writes.size) notice(`保存中…（${writes.size}件）`);
  else if(state.ready) notice('保存済み・チームの表と同期しています。');
}
function memberRef(id) { return doc(memberCollection,id); }
async function flush() {
  if(saving||failed) return;
  saving=true;
  while(writes.size) {
    const [key,job]=writes.entries().next().value;
    syncStatus();
    try {
      await updateDoc(memberRef(job.id),{[storageField(job.field)]:job.value,updatedAt:serverTimestamp()});
      if(writes.get(key)===job) writes.delete(key);
    } catch(error) {
      failed=true;
      console.error('Save failed',error.code);
      break;
    }
  }
  saving=false;
  syncStatus();
  render();
}
function queue(id,field,value) {
  writes.set(`${id}/${field}`,{id,field,value});
  syncStatus();
  flush();
}
function effectiveMembers() {
  const members=structuredClone(state.members);
  for(const job of writes.values()) {
    const member=members.find(item=>item.id===job.id);
    if(!member) continue;
    if(job.field.startsWith('ratings.')) {
      const [,key,property]=job.field.split('.');
      member.ratings[key][property]=job.value;
    } else member[job.field]=job.value;
  }
  return members;
}
function editable(tag,value,id,field,label,maximum) {
  const node=element(tag,null,{'aria-label':label,'data-member':id,'data-field':field});
  node.value=value;
  if(tag==='input'||tag==='textarea') node.defaultValue=value;
  if(maximum) node.maxLength=maximum;
  return node;
}
function memo(value,id,field,label,max) {
  const details=element('details',null);
  details.append(element('summary',value?'メモあり':'メモ'));
  details.append(editable('textarea',value,id,field,label,max));
  return details;
}
function render(force=false) {
  if(!force && table.contains(document.activeElement)) { deferred=true; return; }
  deferred=false;
  const types=visibleTypes(state.filters.types);
  const all=effectiveMembers();
  const members=filterMembers(all,state.filters).sort((a,b)=>(a.order||0)-(b.order||0)||a.id.localeCompare(b.id));
  const head=element('tr',null);
  head.append(element('th','タイプ・分類',{scope:'col',class:'type-label'}));
  for(const member of members) {
    const name=element('th',null,{scope:'col',class:'member-heading',id:`member-${member.id}`});
    const input=editable('input',member.name,member.id,'name',`${member.name}の名前`,60);
    input.required=true;
    name.append(input,memo(member.notes,member.id,'notes','メンバーのメモ',1000));
    name.append(element('button','削除',{'data-delete':member.id,class:'delete-link','aria-label':`${member.name}を削除`}));
    head.append(name);
  }
  $('table-head').replaceChildren(head);
  const fragment=document.createDocumentFragment();
  for(const [type,label] of types) for(const [category,categoryLabel] of CATEGORIES.filter(([key])=>!state.filters.category||key===state.filters.category)) {
    if(!members.length) break;
    const row=element('tr',null,{class:`rating-row ${category}`});
    const heading=element('th',null,{scope:'row',class:`type-label ${category}`});
    heading.append(element('span','',{class:`type-dot ${type}`}),document.createTextNode(label),element('span',categoryLabel,{class:'row-category'}));
    row.append(heading);
    for(const member of members) {
      const key=`${type}_${category}`, cell=member.ratings[key];
      const td=element('td',null,{class:`symbol-cell ${category}`});
      const select=editable('select','',member.id,`ratings.${key}.status`,`${member.name}・${label}・${categoryLabel}`);
      select.className=`symbol-select ${cell.status}`;
      for(const [value,symbol] of STATUSES) select.append(element('option',symbol,{value}));
      select.value=cell.status;
      td.append(select,memo(cell.condition,member.id,`ratings.${key}.condition`,`${label}・${categoryLabel}のメモ`,200));
      row.append(td);
    }
    fragment.append(row);
  }
  if(!members.length) {
    const row=element('tr',null);
    row.append(element('td',all.length?'該当するメンバーがいません。':'＋から最初のメンバーを追加してください。',{class:'empty'}));
    fragment.append(row);
  }
  $('table-body').replaceChildren(fragment);
  $('member-count').textContent=String(all.length);
  $('visible-count').textContent=`${members.length}人`;
}

for(const [key,label] of TYPES) {
  const option=element('label',null,{class:'type-option'});
  option.append(element('input',null,{type:'checkbox',name:'type',value:key}),element('span','',{class:`type-dot ${key}`}),document.createTextNode(label));
  $('type-options').append(option);
}
for(const [value,symbol] of STATUSES) $('rating').append(element('option',symbol,{value}));
$('filters').addEventListener('submit',event=>{
  event.preventDefault();
  state.filters={query:$('search').value,types:new Set([...document.querySelectorAll('input[name=type]:checked')].map(input=>input.value)),category:$('category').value,status:$('rating').value};
  render(true);
});
$('reset').addEventListener('click',()=>{
  $('filters').reset(); state.filters={query:'',types:new Set(),category:'',status:''}; render(true);
});
table.addEventListener('change',event=>{
  const input=event.target;
  if(!input.dataset.field||!state.ready) return;
  let value=input.value;
  if(input.dataset.field==='name') {
    value=value.trim();
    input.setCustomValidity(value&&value.length<=60?'':'名前を1～60文字で入力してください。');
    if(!input.reportValidity()) return;
    input.value=value;
  }
  if(input.tagName==='SELECT') input.className=`symbol-select ${value}`;
  queue(input.dataset.member,input.dataset.field,value);
});
table.addEventListener('input',event=>event.target.setCustomValidity?.(''));
table.addEventListener('focusout',()=>requestAnimationFrame(()=>{if(deferred) render();}));
$('retry').addEventListener('click',()=>{failed=false;flush();});
window.addEventListener('beforeunload',event=>{
  const input=document.activeElement;
  const editing=table.contains(input)&&input?.matches('input,textarea')&&input.value!==input.defaultValue;
  if(writes.size||busy||editing) {event.preventDefault();event.returnValue='';}
});
$('add').addEventListener('click',async()=>{
  if(!state.ready||busy||writes.size) return;
  busy=true;operationError='';syncStatus();
  let number=state.members.length+1;
  while(state.members.some(member=>member.name===`メンバー${number}`)) number++;
  const ref=doc(memberCollection);
  try {
    await setDoc(ref,{...toDocument({name:`メンバー${number}`,notes:'',ratings:blankRatings()}),order:Date.now(),createdAt:serverTimestamp(),updatedAt:serverTimestamp()});
    $('search').value='';$('category').value='';$('rating').value='';
    state.filters={...state.filters,query:'',category:'',status:''};
    render(true);
    const input=document.querySelector(`#member-${ref.id} input`);
    if(input) {input.focus();input.select();}
  } catch {operationError='メンバーを追加できませんでした。接続を確認して再度お試しください。';}
  finally {busy=false;syncStatus();}
});
let deletingId;
table.addEventListener('click',event=>{
  const id=event.target.dataset.delete;
  if(!id||busy||writes.size) return;
  deletingId=id;
  $('delete-name').textContent=`「${state.members.find(member=>member.id===id)?.name||''}」を削除します。`;
  $('delete-dialog').showModal();
});
$('delete-dialog').addEventListener('close',async()=>{
  if($('delete-dialog').returnValue!=='delete'||!deletingId) return;
  const id=deletingId;deletingId=null;busy=true;operationError='';syncStatus();
  try {await deleteDoc(memberRef(id));} catch {operationError='削除できませんでした。もう一度お試しください。';}
  finally {busy=false;syncStatus();}
});
$('backup').addEventListener('click',()=>{
  const data={version:1,members:effectiveMembers().map(normalizeMember)};
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  const link=element('a',null,{href:url,download:`gymbattle-${new Date().toISOString().slice(0,10)}.json`});
  link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
$('restore').addEventListener('change',async event=>{
  const file=event.target.files[0];event.target.value='';
  if(!file||!state.ready||busy||writes.size) return;
  try {
    if(file.size>2*1024*1024) throw new Error('バックアップは2MB以下にしてください。');
    const members=parseBackup(await file.text());
    if(!members.length||!confirm(`共有表に${members.length}人を追加します。既存の行は残ります。よろしいですか？`)) return;
    busy=true;operationError='';syncStatus();
    const batch=writeBatch(db);
    members.forEach((member,index)=>batch.set(doc(memberCollection),{...toDocument(member),order:Date.now()+index,createdAt:serverTimestamp(),updatedAt:serverTimestamp()}));
    await batch.commit();
  } catch(error) {operationError=error.message||'取り込みできませんでした。';}
  finally {busy=false;syncStatus();}
});

function setup(message) {$('setup').hidden=false;$('setup-detail').textContent=message;$('connection').textContent='未接続';}
$('show-roster').addEventListener('click',()=>inventory?.show(false));
$('show-inventory').addEventListener('click',()=>inventory?.show(true));
async function start() {
  board=new URLSearchParams(window.location.hash.slice(1)).get('b');
  if(!validBoardId(board)) {setup('管理者から受け取った共有URLを開いてください。共有URLには #b= に続いて共有IDが含まれます。');return;}
  const emulator=import.meta.env.VITE_USE_EMULATORS==='true';
  if(emulator&&!['localhost','127.0.0.1'].includes(location.hostname)) {setup('テスト用の接続設定では公開できません。');return;}
  const config=emulator?{apiKey:'demo-api-key',authDomain:'localhost',projectId:'demo-gymbattle',appId:'demo-app'}:{
    apiKey:import.meta.env.VITE_FIREBASE_API_KEY,authDomain:import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId:import.meta.env.VITE_FIREBASE_PROJECT_ID,appId:import.meta.env.VITE_FIREBASE_APP_ID,
  };
  if(Object.values(config).some(value=>!value)) {setup('Firebase管理画面のWebアプリ設定を .env.local に設定してください。');return;}
  try {
    const firebase=initializeApp(config),auth=getAuth(firebase);db=getFirestore(firebase);
    if(emulator) {connectAuthEmulator(auth,'http://127.0.0.1:9098',{disableWarnings:true});connectFirestoreEmulator(db,'127.0.0.1',8085);}
    await signInAnonymously(auth);
    const info=await getDoc(doc(db,'boards',board));
    if(!info.exists()||info.data().enabled!==true) throw new Error('この共有URLは利用できません。管理者に確認してください。');
    memberCollection=collection(db,'boards',board,'members');
    inventory=createInventory(db,board);
    unsubscribe=onSnapshot(memberCollection,{includeMetadataChanges:true},snapshot=>{
      if(snapshot.metadata.hasPendingWrites) return;
      state.members=snapshot.docs.map(item=>({id:item.id,...fromDocument(item.data())}));
      inventory.updateMembers(state.members);
      state.ready=true;$('app').hidden=false;$('setup').hidden=true;
      $('connection').textContent='チームと接続中';
      render();syncStatus();
    },error=>{
      state.ready=false;$('connection').textContent='接続できません';syncStatus();
      $('app').hidden=true;setup('表を取得できません。接続・共有ID・Firestoreのルールを確認してください。');
      console.error('Subscription failed',error.code);
    });
  } catch(error) {setup(error.code==='permission-denied'?'この共有URLは利用できません。管理者に確認してください。':error.message||'Firebaseへ接続できませんでした。');}
}
window.addEventListener('offline',()=>{$('connection').textContent='オフライン';notice('通信が切れています。未保存の変更があれば画面を閉じずにお待ちください。',true);});
window.addEventListener('online',()=>{if(!failed)flush();});
start();
