'use strict';
let state=null, current='overview';
const names={overview:'概览',devices:'设备与登录账号',targets:'目标账号库',tasks:'核验任务',contents:'内容记录',logs:'操作日志'};
const statusName={pending:'待核验',active:'核验中',paused:'已暂停',completed:'已完成',failed:'失败',cancelled:'已停止',verified:'已确认',unknown:'待确认',matched:'身份相符',mismatched:'身份不符',not_found:'未找到'};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const date=v=>v?new Date(v).toLocaleString('zh-CN'):'';
const badge=v=>`<span class="badge">${esc(statusName[v]||v)}</span>`;
const lookup=(entity,id)=>state[entity].find(r=>r.id===id)?.name||`#${id}`;
function notice(text,error=false){const n=document.querySelector('#notice');n.textContent=text;n.className=error?'error':'';}
async function api(path,body){const r=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw Error(data.error||'请求失败');return data;}
async function reload(){state=await api('/api/state');render();}
function input(label,key,required=false,placeholder=''){return `<label>${esc(label)}${required?' *':''}<input name="${key}" ${required?'required':''} maxlength="2000" placeholder="${esc(placeholder)}"></label>`;}
function select(label,key,options){return `<label>${esc(label)}<select name="${key}" required>${options}</select></label>`;}
function options(rows,empty){return `<option value="">${empty}</option>`+rows.map(r=>`<option value="${r.id}">${esc(r.name)}${r.serial?' · '+esc(r.serial):''}</option>`).join('');}
function form(entity,fields){return `<section class="panel"><h2>新增${names[entity]}</h2><form data-entity="${entity}" class="forms">${fields}<div class="submit"><button class="primary" type="submit">保存</button></div></form></section>`;}
function grid(headers,rows){if(!rows.length)return '<div class="empty">暂无记录，请先添加。</div>';return `<div class="table-wrap"><table><thead><tr>${headers.map(x=>`<th>${esc(x)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(x=>`<td>${x}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;}
function records(title,headers,rows){return `<section class="panel"><div class="topline"><h2>${title}</h2><span class="subtle">${rows.length} 条</span></div>${grid(headers,rows)}</section>`;}
function render(){
 document.querySelector('#heading').textContent=names[current];
 document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('selected',b.dataset.tab===current));
 let html='';
 if(current==='overview'){
  html=`<div class="metrics">${[['设备',state.devices.length],['目标账号',state.targets.length],['进行中核验',state.tasks.filter(t=>t.status==='active').length],['内容记录',state.contents.length]].map(([n,v])=>`<div class="metric"><span class="subtle">${n}</span><strong>${v}</strong></div>`).join('')}</div><section class="panel adapter"><div class="statusline"><h2>影刀连接</h2><span class="badge">尚未接入</span></div><p>${esc(state.adapter.message)}</p><p class="subtle">当前任务用于人工核验和记录。添加设备不会自动连接手机；连接和自动读取需要完成影刀接入。</p></section><section class="panel"><h2>从这里开始</h2><div class="steps"><div><strong>1 添加设备</strong><p>区分手机标识与当前登录账号。</p></div><div><strong>2 保存目标账号</strong><p>记录抖音号或主页链接，标明确认状态。</p></div><div><strong>3 建立核验任务</strong><p>按设备登记任务，保存核验结果与日志。</p></div></div></section>`;
 }else if(current==='devices'){
  html=form('devices',input('设备标识','serial',true,'与影刀设备标识保持一致')+input('设备备注名','name',true,'例如 手机01')+input('手机型号','model')+input('当前登录账号','login_account')+input('备注','note'))+records('设备列表',['标识','备注名','型号','登录账号','连接状态','备注'],state.devices.map(r=>[esc(r.serial),esc(r.name),esc(r.model),esc(r.login_account),badge(r.connection_state),esc(r.note)]));
 }else if(current==='targets'){
  html=form('targets',input('昵称','name',true)+input('抖音号','account_id')+input('主页链接','profile_url')+input('头像参考路径','avatar_ref')+input('分组','group_name')+select('身份确认状态','verification','<option value="pending">待确认</option><option value="verified">人工已确认</option>')+input('备注','note'))+records('目标账号列表',['昵称','抖音号','主页链接','分组','身份状态','确认时间'],state.targets.map(r=>[esc(r.name),esc(r.account_id),esc(r.profile_url),esc(r.group_name),badge(r.verification),esc(date(r.verified_at))]));
 }else if(current==='tasks'){
  html=form('tasks',select('设备','device_id',options(state.devices,'请选择设备'))+select('目标账号','target_id',options(state.targets,'请选择账号'))+input('关键词','keyword')+select('内容类型','content_type','<option value="all">全部</option><option value="video">视频</option><option value="image">图文</option>'))+records('人工核验任务',['编号','设备','目标账号','关键词','类型','状态','记录与操作'],state.tasks.map(r=>{
   const allowed={pending:['active','cancelled'],active:['paused','completed','failed','cancelled'],paused:['active','cancelled']}[r.status]||[];
   const captions={active:r.status==='paused'?'恢复核验':'开始核验',paused:'暂停',completed:'完成',failed:'失败',cancelled:'停止'};
   return [r.id,esc(lookup('devices',r.device_id)),esc(lookup('targets',r.target_id)),esc(r.keyword),esc({all:'全部',video:'视频',image:'图文'}[r.content_type]),badge(r.status),`${esc(r.note)}<br>${allowed.map(x=>`<button data-task="${r.id}" data-status="${x}">${captions[x]}</button>`).join('')}`];
  }));
 }else if(current==='contents'){
  html=form('contents',select('目标账号','target_id',options(state.targets,'请选择账号'))+select('关联任务','task_id','<option value="">不关联任务</option>'+state.tasks.map(t=>`<option value="${t.id}">#${t.id} · ${esc(lookup('targets',t.target_id))}</option>`).join(''))+input('内容标题或记录说明','title',true)+input('作品链接','url')+input('发布时间','published_at')+input('作者抖音号','author_account')+select('核验结果','identity_result','<option value="pending">待确认</option><option value="matched">身份相符</option><option value="mismatched">身份不符</option><option value="not_found">未找到</option>')+input('截图路径','screenshot_ref')+input('备注','note'))+records('核验记录',['标题','目标账号','作者账号','作品链接','结果','保存时间'],state.contents.map(r=>[esc(r.title),esc(lookup('targets',r.target_id)),esc(r.author_account),esc(r.url),badge(r.identity_result),esc(date(r.created_at))]));
 }else{
  html=records('最近操作日志',['时间','类型','编号','事件','内容'],state.logs.map(r=>[esc(date(r.created_at)),esc(names[r.entity]||r.entity),r.entity_id,esc({created:'新增',restart_paused:'重启暂停',...statusName}[r.event]||r.event),esc(r.detail)]));
 }
 document.querySelector('#workspace').innerHTML=html;
}
document.addEventListener('click',async e=>{
 const nav=e.target.closest('[data-tab]');if(nav){current=nav.dataset.tab;notice('');render();return;}
 const action=e.target.closest('[data-task]');if(!action)return;
 let note='';if(action.dataset.status==='failed'){note=prompt('请填写失败原因');if(note===null)return;}
 action.disabled=true;
 try{await api(`/api/tasks/${action.dataset.task}/status`,{status:action.dataset.status,note});await reload();notice('任务状态已保存');}catch(err){notice(err.message,true);action.disabled=false;}
});
document.addEventListener('submit',async e=>{
 const f=e.target.closest('form[data-entity]');if(!f)return;e.preventDefault();
 const body=Object.fromEntries(new FormData(f));['device_id','target_id','task_id'].forEach(k=>{if(k in body)body[k]=body[k]?Number(body[k]):null;});
 const b=f.querySelector('button[type=submit]');b.disabled=true;
 try{await api('/api/'+f.dataset.entity,body);await reload();notice('记录已保存');}catch(err){notice(err.message,true);b.disabled=false;}
});
document.querySelector('#refresh').addEventListener('click',()=>reload().then(()=>notice('已刷新')).catch(e=>notice(e.message,true)));
reload().catch(e=>notice('无法连接本地服务：'+e.message,true));
