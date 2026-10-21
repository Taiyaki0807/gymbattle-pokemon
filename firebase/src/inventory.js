import {collection,doc,onSnapshot,runTransaction,serverTimestamp} from 'firebase/firestore';
import characters from './characters.json';
import {CANDIES,EMPTY_ENTRY,LEVEL_OPTIONS,MOVE_LEVEL_OPTIONS,filterCharacters,validateEntry} from './inventory-domain.js';

const $=id=>document.getElementById(id);
function el(tag,text,attrs={}){const node=document.createElement(tag);if(text!==null)node.textContent=text;for(const [k,v]of Object.entries(attrs))node.setAttribute(k,v);return node;}
export function createInventory(db,board){
  let memberId='',members=[],entries={},candies={},stopEntries,stopCandies,ready=false,open=false,saving=false,failed=false,deferred=false;
  const jobs=new Map();
  const table=$('inventory-table');
  function status(){
    $('inventory-status').textContent=failed?'保存できませんでした。入力を保持しています。再試行してください。':jobs.size?'保存中…':ready?'保存済み・チームと同期しています。':memberId?'読み込み中…':'メンバーを選択してください。';
    $('inventory-retry').hidden=!failed;$('inventory-member').disabled=jobs.size>0;
    $('inventory-backup').disabled=!ready||jobs.size>0;
    $('inventory-content').inert=!ready;
  }
  function effective(){const result=structuredClone(entries);for(const job of jobs.values())if(job.kind==='entry'){result[job.id]={...EMPTY_ENTRY,...result[job.id],[job.field]:job.value};}return result;}
  function showCounts(){const values=effective();$('inventory-count').textContent=`${characters.filter(c=>values[c.id]?.owned).length} / ${characters.length}体 所持`;}
  function render(){
    if(table.contains(document.activeElement)||$('candy-fields').contains(document.activeElement)){deferred=true;showCounts();return;}deferred=false;
    const values=effective(),list=filterCharacters(characters,values,{query:$('character-search').value,type:$('character-type').value,owned:$('character-owned').value});
    const fragment=document.createDocumentFragment();
    for(const c of list){const value={...EMPTY_ENTRY,...values[c.id]},row=el('tr',null,{'data-character':c.id,class:value.owned?'is-owned':''});
      const check=(field,label)=>{const input=el('input',null,{type:'checkbox','data-entry':c.id,'data-field':field,'aria-label':`${c.name}の${label}`});input.checked=value[field];return input;};
      const owned=el('td',null);owned.append(check('owned','所持'));row.append(owned);
      const picture=el('th',null,{class:'character-picture',scope:'row'});if(c.image){const image=el('img',null,{src:c.image,alt:c.name,width:'96',height:'96',loading:'lazy',decoding:'async'});image.addEventListener('error',()=>image.replaceWith(el('span',c.name.slice(0,2),{class:'character-placeholder'})),{once:true});picture.append(image);}else picture.append(el('span',c.name.slice(0,2),{class:'character-placeholder','aria-label':'画像未登録'}));picture.append(el('span',c.name,{class:'character-name'}));row.append(picture);
      for(const [field,label,options]of [['level','レベル',LEVEL_OPTIONS],['moveLevel','わざレベル',MOVE_LEVEL_OPTIONS]]){
        const td=el('td',null),select=el('select',null,{'data-entry':c.id,'data-field':field,'aria-label':`${c.name}の${label}`});select.append(el('option','未設定',{value:''}));
        if(value[field]&&!options.includes(value[field])){const old=el('option',`以前の設定：${value[field]}`,{value:String(value[field])});old.disabled=true;select.append(old);}
        for(const n of options)select.append(el('option',field==='level'?`～${n}`:String(n),{value:String(n)}));select.value=value[field]??'';if(field==='moveLevel')select.className=`move-level move-${value[field]||0}`;td.append(select);row.append(td);
      }
      const ex=el('td',null);ex.append(check('exRole','EXロール'));row.append(ex);fragment.append(row);
    }
    if(!list.length){const row=el('tr',null);row.append(el('td','該当するキャラがいません。',{colspan:'5',class:'empty'}));fragment.append(row);}
    $('inventory-body').replaceChildren(fragment);showCounts();
    for(const [key]of CANDIES){let value=candies[key]??0;const job=jobs.get(`candy/${key}`);if(job)value=job.value;$('candy-'+key).value=value;}
  }
  async function flush(){if(saving||failed)return;saving=true;
    while(jobs.size){const [key,job]=jobs.entries().next().value;status();try{
      const ref=job.kind==='entry'?doc(db,'boards',board,'members',job.member,'inventory',job.id):doc(db,'boards',board,'members',job.member,'supplies','candies');
      await runTransaction(db,async tx=>{const snapshot=await tx.get(ref);if(job.kind==='entry'){const old=snapshot.exists()?snapshot.data():EMPTY_ENTRY;const {updatedAt,...clean}=old;tx.set(ref,{...validateEntry({...clean,[job.field]:job.value}),updatedAt:serverTimestamp()});}else{const old=snapshot.exists()?snapshot.data():Object.fromEntries(CANDIES.map(([k])=>[k,0]));tx.set(ref,{...old,[job.field]:job.value,updatedAt:serverTimestamp()});}});
      if(jobs.get(key)===job)jobs.delete(key);
    }catch(error){failed=true;console.error('Inventory save failed',error.code);break;}}
    saving=false;status();render();
  }
  function queue(job){jobs.set(`${job.kind}/${job.kind==='entry'?job.id+'/':''}${job.field}`,{...job,member:memberId});status();flush();}
  function selectMember(){
    stopEntries?.();stopCandies?.();ready=false;entries={};candies={};memberId=$('inventory-member').value;status();render();if(!memberId)return;
    let entriesReady=false,candiesReady=false;
    const receive=()=>{ready=entriesReady&&candiesReady;status();render();};
    const error=()=>{ready=false;status();$('inventory-status').textContent='取得できませんでした。メンバーを選び直してください。';};
    stopEntries=onSnapshot(collection(db,'boards',board,'members',memberId,'inventory'),{includeMetadataChanges:true},snapshot=>{if(snapshot.metadata.hasPendingWrites)return;entries=Object.fromEntries(snapshot.docs.map(d=>[d.id,d.data()]));entriesReady=true;receive();},error);
    stopCandies=onSnapshot(collection(db,'boards',board,'members',memberId,'supplies'),{includeMetadataChanges:true},snapshot=>{if(snapshot.metadata.hasPendingWrites)return;candies=snapshot.docs.find(d=>d.id==='candies')?.data()||{};candiesReady=true;receive();},error);
  }
  for(const text of [...new Set(characters.map(c=>c.type))])$('character-type').append(el('option',text,{value:text}));
  for(const [key,label]of CANDIES){const field=el('label',null,{class:`candy-field candy-${key}`});field.append(el('span',key==='awakening'?'超覚醒アメ':`わざのアメ（${label}）`));field.append(el('input',null,{id:'candy-'+key,type:'number',min:'0',max:'9999',step:'1',value:'0','data-candy':key}));$('candy-fields').append(field);}
  $('inventory-filters').addEventListener('submit',event=>{event.preventDefault();render();});
  $('inventory-reset').addEventListener('click',()=>{$('inventory-filters').reset();render();});
  $('inventory-member').addEventListener('change',selectMember);
  table.addEventListener('change',event=>{const input=event.target;if(!ready||!input.dataset.entry)return;const field=input.dataset.field,value=input.type==='checkbox'?input.checked:input.value===''?null:Number(input.value);queue({kind:'entry',id:input.dataset.entry,field,value});const row=input.closest('tr');if(field==='owned')row.classList.toggle('is-owned',value);if(field==='moveLevel')input.className=`move-level move-${value||0}`;showCounts();});
  $('candy-fields').addEventListener('change',event=>{const input=event.target;if(!ready||!input.dataset.candy)return;input.setCustomValidity('');if(input.value===''||!Number.isInteger(Number(input.value))||!input.checkValidity()){input.setCustomValidity('0～9999の整数を入力してください。');input.reportValidity();return;}queue({kind:'candy',field:input.dataset.candy,value:Number(input.value)});});
  $('candy-fields').addEventListener('input',event=>event.target.setCustomValidity?.(''));
  for(const section of [table,$('candy-fields')])section.addEventListener('focusout',()=>requestAnimationFrame(()=>{if(deferred)render();}));
  $('inventory-retry').addEventListener('click',()=>{failed=false;flush();});
  $('inventory-backup').addEventListener('click',()=>{const payload={version:1,member:members.find(m=>m.id===memberId)?.name,characters:characters.map(c=>({...c,...EMPTY_ENTRY,...entries[c.id]})),candies};const link=el('a',null,{href:URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'})),download:'gymbattle-inventory.json'});link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);});
  window.addEventListener('beforeunload',event=>{if(jobs.size){event.preventDefault();event.returnValue='';}});
  return {
    updateMembers(next){members=next;const previous=memberId;$('inventory-member').replaceChildren(el('option','メンバーを選択',{value:''}),...next.slice().sort((a,b)=>(a.order||0)-(b.order||0)).map(m=>el('option',m.name,{value:m.id})));$('inventory-member').value=next.some(m=>m.id===previous)?previous:'';if(previous&&!$('inventory-member').value)selectMember();status();},
    show(value){open=value;$('roster-panel').hidden=value;$('inventory-panel').hidden=!value;$('show-roster').setAttribute('aria-pressed',String(!value));$('show-inventory').setAttribute('aria-pressed',String(value));if(open&&!memberId&&members.length){$('inventory-member').value=members[0].id;selectMember();}}
  };
}
