// Dependency-free rendering smoke test. Does not replace Windows browser checks.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const nodes = new Map();
const node = key => {
  if (!nodes.has(key)) nodes.set(key, {textContent:'',innerHTML:'',className:'',addEventListener(){}});
  return nodes.get(key);
};
const snapshot = {
  version:'0.1.0', adapter:{connected:false,message:'影刀尚未接入'},
  devices:[{id:1,name:'手机01',serial:'test-001',model:'',login_account:'',connection_state:'unknown'}],
  targets:[{id:1,name:'<img src=x onerror=alert(1)>',account_id:'abc',profile_url:'',verification:'pending'}],
  tasks:[{id:1,device_id:1,target_id:1,keyword:'关键词',content_type:'video',status:'pending'}],
  contents:[{id:1,target_id:1,title:'内容',author_account:'abc',url:'',identity_result:'pending'}],
  logs:[{id:1,entity:'devices',entity_id:1,event:'created',detail:'新增',created_at:'2026-10-03T07:00:00Z'}],
};
const context=vm.createContext({
  document:{querySelector:node,querySelectorAll:()=>[],addEventListener(){}},
  fetch:async()=>({ok:true,json:async()=>snapshot}),
  console,Date,Error,FormData:class{},prompt:()=>null,
});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8'),context);
(async()=>{
  await vm.runInContext('reload()',context);
  for(const tab of ['overview','devices','targets','tasks','contents','logs']){
    vm.runInContext(`current=${JSON.stringify(tab)};render()`,context);
    assert.ok(node('#workspace').innerHTML.length>100);
    assert.ok(!node('#workspace').innerHTML.includes('<img src=x'));
  }
  vm.runInContext("current='targets';render()",context);
  assert.ok(node('#workspace').innerHTML.includes('&lt;img'));
  vm.runInContext("state.devices=[];state.targets=[];state.tasks=[];state.contents=[];state.logs=[];current='tasks';render()",context);
  assert.ok(node('#workspace').innerHTML.includes('暂无记录'));
  console.log('PASS: 6 UI sections, empty data, text escaping');
})().catch(e=>{console.error(e);process.exitCode=1;});
