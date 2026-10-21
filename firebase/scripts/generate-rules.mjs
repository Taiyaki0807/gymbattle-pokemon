import {readFileSync,writeFileSync} from 'node:fs';
import {CELL_KEYS} from '../src/domain.js';
const keys=CELL_KEYS.map(key=>`'${key}'`).join(', ');
const checks=CELL_KEYS.map(key=>`validCondition(c.${key})`).join('\n        && ');
const catalog=JSON.parse(readFileSync(new URL('../src/characters.json',import.meta.url),'utf8'));
if(!Array.isArray(catalog)||!catalog.length||catalog.some(c=>!/^pair-\d{3,}$/.test(c.id))||new Set(catalog.map(c=>c.id)).size!==catalog.length)throw Error('キャラIDには重複しない pair-090 のような値を使ってください。');
const characterIds=catalog.map(c=>`'${c.id}'`).join(',');
const candyKeys=['yellow','green','red','orange','blue','purple','awakening'];
const rules=`rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    function signedIn() { return request.auth != null; }
    function validBoardId(id) { return id.matches('[a-zA-Z0-9_-]{32,80}'); }
    function activeBoard(id) {
      return signedIn() && validBoardId(id)
        && get(/databases/$(database)/documents/boards/$(id)).data.enabled == true;
    }
    function validCondition(c) {
      return c is string && c.size() <= 200;
    }
    function validRatings(r) {
      return r is map && r.keys().hasAll([${keys}]) && r.keys().hasOnly([${keys}])
        && r.values().hasOnly(['excellent','yes','conditional','no','unset']);
    }
    function validConditions(c) {
      return c is map && c.keys().hasAll([${keys}]) && c.keys().hasOnly([${keys}])
        && ${checks};
    }
    function validMember(d) {
      return d.keys().hasAll(['name','notes','ratings','conditions','order','createdAt','updatedAt'])
        && d.keys().hasOnly(['name','notes','ratings','conditions','order','createdAt','updatedAt'])
        && d.name is string && d.name.size() > 0 && d.name.size() <= 60 && d.name.matches('.*[^ ].*')
        && d.notes is string && d.notes.size() <= 1000
        && d.order is int && d.order >= 0 && d.order <= 9999999999999
        && d.createdAt is timestamp && d.updatedAt == request.time
        && validRatings(d.ratings) && validConditions(d.conditions);
    }
    function validInventory(d) {
      return d.keys().hasAll(['owned','level','moveLevel','exRole','updatedAt'])
        && d.keys().hasOnly(['owned','level','moveLevel','exRole','updatedAt'])
        && d.owned is bool && d.exRole is bool
        && (d.level == null || (d.level is int && d.level >= 1 && d.level <= 200))
        && (d.moveLevel == null || (d.moveLevel is int && d.moveLevel >= 1 && d.moveLevel <= 10))
        && d.updatedAt == request.time;
    }
    function validCandies(d) {
      return d.keys().hasAll(['yellow','green','red','orange','blue','purple','awakening','updatedAt'])
        && d.keys().hasOnly(['yellow','green','red','orange','blue','purple','awakening','updatedAt'])
        && ${candyKeys.map(k=>`d.${k} is int && d.${k} >= 0 && d.${k} <= 9999`).join('\n        && ')}
        && d.updatedAt == request.time;
    }
    match /boards/{boardId} {
      allow get: if signedIn() && validBoardId(boardId) && resource.data.enabled == true;
      allow list, create, update, delete: if false;
      match /members/{memberId} {
        allow read: if activeBoard(boardId);
        allow create: if activeBoard(boardId) && validMember(request.resource.data)
          && request.resource.data.createdAt == request.time;
        allow update: if activeBoard(boardId) && validMember(request.resource.data)
          && request.resource.data.createdAt == resource.data.createdAt
          && request.resource.data.order == resource.data.order;
        allow delete: if activeBoard(boardId);
        match /inventory/{characterId} {
          allow read: if activeBoard(boardId) && exists(/databases/$(database)/documents/boards/$(boardId)/members/$(memberId));
          allow create, update: if activeBoard(boardId)
            && exists(/databases/$(database)/documents/boards/$(boardId)/members/$(memberId))
            && characterId in [${characterIds}] && validInventory(request.resource.data);
          allow delete: if false;
        }
        match /supplies/{supplyId} {
          allow read: if activeBoard(boardId) && exists(/databases/$(database)/documents/boards/$(boardId)/members/$(memberId));
          allow create, update: if activeBoard(boardId)
            && exists(/databases/$(database)/documents/boards/$(boardId)/members/$(memberId))
            && supplyId == 'candies' && validCandies(request.resource.data);
          allow delete: if false;
        }
      }
    }
  }
}
`;
writeFileSync(new URL('../firestore.rules',import.meta.url),rules);
