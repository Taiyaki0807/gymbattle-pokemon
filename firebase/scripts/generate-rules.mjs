import {writeFileSync} from 'node:fs';
import {CELL_KEYS} from '../src/domain.js';
const keys=CELL_KEYS.map(key=>`'${key}'`).join(', ');
const checks=CELL_KEYS.map(key=>`validCondition(c.${key})`).join('\n        && ');
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
      }
    }
  }
}
`;
writeFileSync(new URL('../firestore.rules',import.meta.url),rules);
