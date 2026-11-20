"""离线刷题工具生成器：把一批题目打包成**单个 HTML 文件**。

特性：零依赖、双击即用、完全离线、localStorage 持久化（进度/错题/统计/笔记），
手机与电脑通用，可自由分发。这是本项目的核心亮点之一。
"""
import json
from html import escape

TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#4f46e5">
<title>__TITLE__</title>
<style>
:root{
  --p:#4f46e5;--p2:#7c73ff;--bg:#f1f5f9;--card:#fff;--bd:#e2e8f0;
  --tx:#0f172a;--mu:#64748b;--ok:#059669;--okbg:#ecfdf5;--err:#dc2626;--errbg:#fef2f2;
  --warn:#d97706;--warnbg:#fffbeb;--r:14px;--sh:0 1px 3px rgba(15,23,42,.06),0 8px 24px rgba(15,23,42,.05);
}
@media(prefers-color-scheme:dark){
  :root{--bg:#0b1120;--card:#151e31;--bd:#26314b;--tx:#e6edf7;--mu:#93a4c0;
  --okbg:#052e26;--errbg:#2a1214;--warnbg:#2a2008;--sh:0 1px 3px rgba(0,0,0,.4)}
}
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html{scroll-behavior:smooth}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  background:var(--bg);color:var(--tx);line-height:1.6;font-size:15px;min-height:100vh}
.hd{background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;padding:16px 18px calc(16px + env(safe-area-inset-bottom));
  position:sticky;top:0;z-index:20;box-shadow:var(--sh)}
.hd h1{font-size:17px;font-weight:700;letter-spacing:.2px}
.hd .sub{font-size:12px;opacity:.88;margin-top:3px}
.hd .row{display:flex;justify-content:space-between;align-items:center;gap:12px}
.hd .pill{background:rgba(255,255,255,.2);border-radius:999px;padding:3px 10px;font-size:11px;white-space:nowrap}
.bar{display:flex;gap:4px;padding:8px 10px;background:var(--card);border-bottom:1px solid var(--bd);
  overflow-x:auto;position:sticky;top:66px;z-index:19;-webkit-overflow-scrolling:touch;scrollbar-width:none}
.bar::-webkit-scrollbar{display:none}
.bar button{flex:0 0 auto;padding:8px 14px;border:1px solid transparent;background:none;font-size:13px;
  color:var(--mu);cursor:pointer;border-radius:999px;white-space:nowrap;font-family:inherit;transition:.15s}
.bar button.on{background:var(--p);color:#fff;font-weight:600}
.bar button:not(.on):active{background:var(--bg)}
.subjbar{display:flex;gap:6px;padding:8px 12px;background:var(--card);border-bottom:1px solid var(--bd);overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch}
.subjbar::-webkit-scrollbar{display:none}
.subjbar button{flex:0 0 auto;padding:5px 12px;border:1px solid var(--bd);border-radius:999px;background:var(--bg);color:var(--mu);font-size:12px;cursor:pointer;font-family:inherit;white-space:nowrap}
.subjbar button.on{background:var(--p);color:#fff;border-color:var(--p);font-weight:600}
.wrap{max-width:820px;margin:0 auto;padding:14px 14px calc(80px + env(safe-area-inset-bottom))}
.pg{display:none}.pg.on{display:block;animation:fade .2s}
@keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.card{background:var(--card);border:1px solid var(--bd);border-radius:var(--r);padding:16px;margin-bottom:12px;box-shadow:var(--sh)}
.card h3{font-size:14px;margin-bottom:10px;display:flex;align-items:center;gap:6px;font-weight:650}
.tag{display:inline-block;background:#eef2ff;color:#4338ca;border-radius:999px;padding:2px 9px;font-size:11px;font-weight:500}
.tag.g{background:var(--okbg);color:var(--ok)}.tag.r{background:var(--errbg);color:var(--err)}
.tag.w{background:var(--warnbg);color:var(--warn)}
.qtext{font-size:15.5px;line-height:1.75;margin:10px 0 14px;white-space:pre-wrap;word-break:break-word}
.opts{display:flex;flex-direction:column;gap:9px}
.opt{display:flex;align-items:flex-start;gap:10px;text-align:left;background:var(--card);border:1.5px solid var(--bd);
  border-radius:11px;padding:12px 13px;font-size:14.5px;cursor:pointer;transition:.15s;font-family:inherit;color:var(--tx);width:100%}
.opt:hover:not(:disabled){border-color:var(--p);background:color-mix(in srgb,var(--p) 4%,var(--card))}
.opt:disabled{cursor:default;opacity:.95}
.opt .lt{flex:0 0 24px;height:24px;border-radius:7px;background:var(--bg);display:grid;place-items:center;
  font-size:12px;font-weight:700;color:var(--mu);margin-top:1px}
.opt.sel{border-color:var(--p)}.opt.sel .lt{background:var(--p);color:#fff}
.opt.ok{border-color:var(--ok);background:var(--okbg)}.opt.ok .lt{background:var(--ok);color:#fff}
.opt.bad{border-color:var(--err);background:var(--errbg)}.opt.bad .lt{background:var(--err);color:#fff}
.opt .tx{flex:1;word-break:break-word}
.expl{border-radius:11px;padding:13px;font-size:13.5px;line-height:1.7;margin-top:13px;white-space:pre-wrap;word-break:break-word}
.expl.good{background:var(--okbg);border:1px solid color-mix(in srgb,var(--ok) 30%,transparent)}
.expl.bad{background:var(--errbg);border:1px solid color-mix(in srgb,var(--err) 30%,transparent)}
.expl .h{font-weight:650;margin-bottom:5px;display:flex;align-items:center;gap:6px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;background:var(--p);color:#fff;border:none;
  border-radius:10px;padding:11px 18px;font-size:14px;cursor:pointer;font-family:inherit;font-weight:600;transition:.15s}
.btn:hover:not(:disabled){opacity:.92;transform:translateY(-1px)}
.btn:disabled{opacity:.45;cursor:not-allowed}
.btn.sec{background:var(--card);color:var(--p);border:1.5px solid var(--p)}
.btn.ghost{background:var(--bg);color:var(--tx);border:1px solid var(--bd)}
.btn.sm{padding:7px 13px;font-size:12.5px;border-radius:9px}
.btn.full{width:100%}
.nav{display:flex;gap:9px;margin-top:14px;align-items:center}
.nav .sp{flex:1}
.prog{height:5px;background:var(--bd);border-radius:999px;overflow:hidden;margin-bottom:12px}
.prog i{display:block;height:100%;background:linear-gradient(90deg,var(--p),var(--p2));transition:width .3s;border-radius:999px}
.stat{display:grid;grid-template-columns:repeat(auto-fit,minmax(96px,1fr));gap:9px;margin-bottom:12px}
.st{background:var(--card);border:1px solid var(--bd);border-radius:var(--r);padding:13px 10px;text-align:center;box-shadow:var(--sh)}
.st .n{font-size:21px;font-weight:750;color:var(--p);line-height:1.2}
.st .n.g{color:var(--ok)}.st .n.r{color:var(--err)}
.st .l{font-size:11.5px;color:var(--mu);margin-top:3px}
.item{border:1px solid var(--bd);border-radius:12px;padding:13px;margin-bottom:10px;background:var(--card)}
.item .q{font-size:13.5px;line-height:1.65;cursor:pointer;word-break:break-word}
.item .meta{font-size:11.5px;color:var(--mu);margin-top:7px;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.empty{text-align:center;color:var(--mu);font-size:13.5px;padding:34px 16px}
.empty .big{font-size:34px;margin-bottom:8px;opacity:.6}
.seg{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:12px}
.seg button{padding:7px 13px;border:1.5px solid var(--bd);border-radius:999px;background:var(--card);
  font-size:12.5px;cursor:pointer;color:var(--mu);font-family:inherit}
.seg button.on{border-color:var(--p);background:var(--p);color:#fff;font-weight:600}
input,select,textarea{width:100%;padding:11px 12px;border:1.5px solid var(--bd);border-radius:10px;font-size:14px;
  margin-bottom:10px;font-family:inherit;background:var(--card);color:var(--tx)}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--p)}
label{font-size:12px;color:var(--mu);display:block;margin-bottom:5px;font-weight:500}
.note{font-size:12px;color:var(--mu);line-height:1.6}
.foot{text-align:center;padding:18px 12px calc(18px + env(safe-area-inset-bottom));color:var(--mu);font-size:11px}
.toast{position:fixed;left:50%;bottom:calc(28px + env(safe-area-inset-bottom));transform:translateX(-50%) translateY(20px);
  background:var(--tx);color:var(--card);padding:11px 20px;border-radius:999px;font-size:13px;opacity:0;
  transition:.25s;z-index:99;pointer-events:none;max-width:88vw;box-shadow:var(--sh)}
.toast.on{opacity:1;transform:translateX(-50%)}
.timer{font-variant-numeric:tabular-nums;font-weight:650}
.kv{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--bd);font-size:13px}
.kv:last-child{border:none}
.kv b{font-weight:650}
@media(max-width:600px){.wrap{padding:11px 11px calc(80px + env(safe-area-inset-bottom))}.card{padding:14px}
 .hd h1{font-size:16px}.bar{top:62px}.qtext{font-size:15px}.opt{font-size:14px;padding:11px 12px}}
</style>
</head>
<body>
<div class="hd">
  <div class="row">
    <div><h1 id="hdTitle">__TITLE__</h1><div class="sub" id="hdSub"></div></div>
    <div class="pill" id="hdPill">0%</div>
  </div>
</div>
<div class="bar">
  <button data-pg="do" class="on">✏️ 刷题</button>
  <button data-pg="br">🗂 背题</button>
  <button data-pg="mk">📕 错题</button>
  <button data-pg="rv">⏰ 复习</button>
  <button data-pg="st">📊 统计</button>
  <button data-pg="set">⚙️ 设置</button>
</div>
<div class="subjbar" id="subjbar" style="display:none"></div>
<div class="wrap">

  <div class="pg on" id="pg-do">
    <div class="prog"><i id="doProg" style="width:0%"></i></div>
    <div class="card">
      <h3><span id="doMeta"></span></h3>
      <div class="qtext" id="doQ"></div>
      <div class="opts" id="doOpts"></div>
      <div id="doExpl"></div>
      <div class="nav">
        <button class="btn ghost sm" id="doPrev">← 上一题</button>
        <button class="btn ghost sm" id="doFlag">🚩 标记</button>
        <span class="sp"></span>
        <button class="btn sm" id="doNext">下一题 →</button>
      </div>
    </div>
    <div class="card" id="doJump"><h3>题目导航</h3><div class="seg" id="doJumpList"></div></div>
  </div>

  <div class="pg" id="pg-br">
    <div class="card">
      <h3>🗂 背题模式</h3>
      <p class="note">直接看题干与答案，适合考前快速过一遍。左右滑动或按钮翻题。</p>
      <div class="qtext" id="brQ" style="margin-top:12px"></div>
      <div id="brAns"></div>
      <div class="nav">
        <button class="btn ghost sm" id="brPrev">← 上一题</button>
        <span class="sp"></span>
        <button class="btn ghost sm" id="brNext">下一题 →</button>
      </div>
    </div>
  </div>

  <div class="pg" id="pg-mk">
    <div class="seg">
      <button class="on" data-mkf="all">全部</button>
      <button data-mkf="pending">未消灭</button>
      <button data-mkf="cleared">已消灭</button>
    </div>
    <div id="mkList"></div>
  </div>

  <div class="pg" id="pg-rv">
    <div class="card">
      <h3>⏰ 间隔复习（SM-2）</h3>
      <p class="note">答错的题会自动排入复习队列，按记忆曲线到期提醒。自评记忆效果，间隔会随之调整。</p>
    </div>
    <div id="rvList"></div>
  </div>

  <div class="pg" id="pg-st">
    <div class="stat">
      <div class="st"><div class="n" id="sDone">0</div><div class="l">已作答</div></div>
      <div class="st"><div class="n g" id="sOk">0</div><div class="l">答对</div></div>
      <div class="st"><div class="n" id="sAcc">0%</div><div class="l">正确率</div></div>
      <div class="st"><div class="n r" id="sMk">0</div><div class="l">错题</div></div>
      <div class="st"><div class="n" id="sTime">0:00</div><div class="l">用时</div></div>
    </div>
    <div class="card"><h3>分知识点正确率</h3><div id="sKnow"></div></div>
    <div class="card"><h3>答题记录</h3><div id="sList"></div></div>
  </div>

  <div class="pg" id="pg-set">
    <div class="card">
      <h3>⚙️ 刷题设置</h3>
      <label><input type="checkbox" id="cRand" style="width:auto;margin-right:6px">随机顺序出题</label>
      <label><input type="checkbox" id="cInstant" style="width:auto;margin-right:6px">点选后立即显示答案</label>
      <label><input type="checkbox" id="cLoop" style="width:auto;margin-right:6px">循环模式（只刷错题）</label>
      <button class="btn sm sec" id="btnApply">应用设置</button>
    </div>
    <div class="card">
      <h3>💾 数据管理</h3>
      <p class="note">所有进度保存在本机浏览器（localStorage），关掉再打开还在。换设备可先导出存档。</p>
      <div class="nav" style="margin-top:12px">
        <button class="btn sm sec" id="btnExport">导出存档</button>
        <button class="btn sm ghost" id="btnImport">导入存档</button>
        <button class="btn sm danger" id="btnReset" style="background:var(--err)">清空进度</button>
      </div>
      <input type="file" id="fileImport" accept=".json,application/json" style="display:none">
    </div>
    <div class="card">
      <h3>ℹ️ 关于</h3>
      <p class="note">ExamBoost 离线刷题工具 · 单文件零依赖 · 双击即用<br>题目均为<b>模拟原创题</b>，非真题；解析供参考，请以官方教材与大纲为准。</p>
    </div>
  </div>

</div>
<div class="foot" id="foot">ExamBoost · 数据仅保存在本机浏览器</div>
<div class="toast" id="toast"></div>

<script>
"use strict";
window.QUIZ=__QUIZ_JSON__;
const QS=QUIZ.questions||[];
const SUBJECTS=[...new Set(QS.map(q=>String(q.subject||'').trim()).filter(Boolean))];
const KEY='ebq_'+QUIZ.id;
const $=id=>document.getElementById(id);
let S=load();
let order=buildOrder();
let cur=0,t0=Date.now(),timer=null;

function load(){
  try{const d=JSON.parse(localStorage.getItem(KEY)||'null');
    if(d&&d.v===2)return d;}catch(e){}
  return {v:2,answers:{},wrong:{},cleared:{},flags:{},cards:{},notes:{},subj:'',
    settings:{rand:false,instant:true,loop:false},ms:0,order:null};
}
function save(){try{localStorage.setItem(KEY,JSON.stringify(S));}catch(e){toast('保存失败：浏览器存储已满或被禁用');}}
function buildOrder(){
  let idx=QS.map((_,i)=>i);
  if(S.subj)idx=idx.filter(i=>String(QS[i].subject||'').trim()===S.subj);
  if(S.settings.loop&&Object.keys(S.wrong).length){
    const w=Object.keys(S.wrong).map(Number).filter(i=>!S.cleared[i]&&i<idx.length);
    if(w.length)return w;
  }
  if(S.settings.rand){for(let i=idx.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[idx[i],idx[j]]=[idx[j],idx[i]];}}
  return idx;
}
function real(i){return order[i];}
function norm(a){return String(a||'').trim().toUpperCase();}
function letterOf(opt,i){
  const m=/^\s*([A-F])\s*[..、\)）]/.exec(String(opt||''));
  return m?m[1].toUpperCase():String.fromCharCode(65+i);
}
function fmt(ms){const s=Math.floor(ms/1000),m=Math.floor(s/60);
  return s<3600?m+':'+String(s%60).padStart(2,'0'):Math.floor(m/60)+':'+String(m%60).padStart(2,'0')+':'+String(s%60).padStart(2,'0');}
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
let toastT=null;
function toast(msg){const t=$('toast');t.textContent=msg;t.classList.add('on');
  clearTimeout(toastT);toastT=setTimeout(()=>t.classList.remove('on'),2200);}

// ---------- 科目筛选 ----------
function renderSubjectBar(){
  const bar=$('subjbar');
  if(SUBJECTS.length<2){bar.style.display='none';return;}
  bar.style.display='flex';
  const all=['全部',...SUBJECTS];
  const active=S.subj||'全部';
  bar.innerHTML=all.map(x=>'<button class="'+(x===active?'on':'')+'" data-s="'+esc(x===active?'':x)+'">'+(x==='全部'?'📚 全部':esc(x))+'</button>').join('');
  bar.querySelectorAll('button').forEach(b=>b.onclick=()=>{
    S.subj=b.dataset.s||'';
    order=buildOrder();cur=0;
    save();renderSubjectBar();renderDo();
    const jp=document.getElementById('pg-do');if(jp)window.scrollTo({top:0,behavior:'smooth'});
  });
}

// ---------- 刷题 ----------
function renderDo(){
  if(!QS.length){$('doQ').innerHTML='<div class="empty"><div class="big">📭</div>本卷没有题目</div>';
    $('doOpts').innerHTML='';$('doMeta').textContent='';return;}
  cur=Math.max(0,Math.min(cur,order.length-1));
  const i=real(cur),q=QS[i],a=S.answers[i];
  $('doMeta').innerHTML='<span class="tag">'+(cur+1)+' / '+order.length+'</span> '+
    (q.knowledge?'<span class="tag g">'+esc(q.knowledge)+'</span>':'')+
    (q.subject?'<span class="tag">'+esc(q.subject)+'</span>':'')+
    (S.flags[i]?' <span class="tag w">🚩 已标记</span>':'');
  $('doQ').textContent=q.question;
  const box=$('doOpts');box.innerHTML='';
  (q.options||[]).forEach((op,j)=>{
    const L=letterOf(op,j),b=document.createElement('button');
    b.className='opt';
    let cls='';
    if(a){
      if(L===norm(q.answer))cls=' ok';
      else if(L===a&&a!==norm(q.answer))cls=' bad';
      b.disabled=true;
    }
    b.innerHTML='<span class="lt">'+L+'</span><span class="tx">'+esc(String(op).replace(/^\s*[A-F]\s*[..、\)）]\s*/,''))+'</span>';
    if(cls)b.className='opt'+cls;
    b.onclick=()=>choose(i,L);
    box.appendChild(b);
  });
  const ex=$('doExpl');
  if(a){
    const ok=a===norm(q.answer);
    ex.innerHTML='<div class="expl '+(ok?'good':'bad')+'"><div class="h">'+(ok?'✅ 回答正确':'❌ 回答错误 · 正确答案 '+norm(q.answer))+'</div>'+
      (q.explanation?esc(q.explanation):'（本题暂无解析）')+'</div>';
  }else ex.innerHTML='';
  const done=order.filter(i=>S.answers[i]!==undefined).length,pct=order.length?Math.round(done/order.length*100):0;
  $('doProg').style.width=pct+'%';
  $('hdPill').textContent=pct+'%';
  $('hdSub').textContent=(S.subj||QUIZ.subject||'全部')+' · 本页 '+order.length+' 题 · 已做 '+done;
  $('doPrev').disabled=cur===0;
  $('doNext').disabled=cur>=order.length-1;
  $('doFlag').textContent=S.flags[i]?'🚩 取消标记':'🚩 标记';
  renderJump();
}
function choose(i,L){
  const q=QS[i];
  if(S.answers[i]!==undefined)return;
  S.answers[i]=L;
  if(L!==norm(q.answer)){S.wrong[i]={q:q.question,a:q.answer,e:q.explanation,k:q.knowledge};delete S.cleared[i];
    enqueueCard(i);}
  save();renderDo();
  if(S.settings.instant)setTimeout(()=>{const n=document.querySelector('.opt.bad');if(n)n.scrollIntoView({block:'nearest'});},50);
}
function enqueueCard(i){
  const q=QS[i];
  S.cards[i]={reps:0,interval:0,ease:2.5,due:todayStr(),q:q.question,a:q.answer,k:q.knowledge};
}
function todayStr(){const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');}
function renderJump(){
  const box=$('doJumpList');box.innerHTML='';
  const max=order.length>120?120:order.length;
  for(let k=0;k<max;k++){
    const i=real(k),a=S.answers[i],b=document.createElement('button');
    b.textContent=i+1;
    if(a!==undefined)b.className=(a===norm(QS[i].answer)?'on':'');
    if(k===cur&&!b.className)b.className='on';
    if(a!==undefined&&a!==norm(QS[i].answer))b.style.background='var(--err)',b.style.borderColor='var(--err)',b.style.color='#fff';
    b.onclick=()=>{cur=k;renderDo();window.scrollTo({top:0,behavior:'smooth'});};
    box.appendChild(b);
  }
  if(order.length>120){const s=document.createElement('span');s.className='note';s.textContent='（仅显示前 120 题）';box.appendChild(s);}
}

// ---------- 背题 ----------
let brCur=0;
function renderBr(){
  if(!QS.length){$('brQ').innerHTML='<div class="empty">本卷没有题目</div>';$('brAns').innerHTML='';return;}
  brCur=Math.max(0,Math.min(brCur,order.length-1));
  const i=real(brCur),q=QS[i];
  $('brQ').textContent=(i+1)+'. '+q.question;
  const opts=(q.options||[]).map((op,j)=>{const L=letterOf(op,j);
    const good=L===norm(q.answer);
    return '<div class="opt'+(good?' ok':'')+'" style="cursor:default;margin-bottom:8px"><span class="lt">'+L+
      '</span><span class="tx">'+esc(String(op).replace(/^\s*[A-F]\s*[..、\)）]\s*/,''))+'</span></div>';}).join('');
  $('brAns').innerHTML='<div class="opts">'+opts+'</div>'+
    (q.explanation?'<div class="expl good"><div class="h">💡 解析</div>'+esc(q.explanation)+'</div>':'');
}

// ---------- 错题 ----------
let mkFilter='all';
function renderMk(){
  const ids=Object.keys(S.wrong).map(Number).sort((a,b)=>a-b);
  const list=$('mkList');
  const shown=ids.filter(i=>mkFilter==='all'?true:mkFilter==='cleared'?!!S.cleared[i]:!S.cleared[i]);
  if(!shown.length){list.innerHTML='<div class="empty"><div class="big">🎉</div>'+(mkFilter==='pending'?'没有待消灭的错题，太棒了！':'还没有错题记录')+'</div>';return;}
  list.innerHTML=shown.map(i=>{const w=S.wrong[i];
    return '<div class="item"><div class="q"><b>'+(i+1)+'.</b> '+esc(w.q)+'</div>'+
      '<div class="meta"><span class="tag r">你答 '+(S.answers[i]||'—')+'</span><span class="tag g">正确 '+esc(w.a)+'</span>'+
      (w.k?'<span class="tag">'+esc(w.k)+'</span>':'')+(S.cleared[i]?'<span class="tag g">已消灭</span>':'<span class="tag w">待消灭</span>')+'</div>'+
      (w.e?'<div class="expl good" style="margin-top:9px">'+esc(w.e)+'</div>':'')+
      '<div class="nav"><button class="btn sm sec" onclick="relearn('+i+')">重做本题</button>'+
      '<button class="btn sm ghost" onclick="clearWrong('+i+')">'+(S.cleared[i]?'恢复为待消灭':'标记已掌握')+'</button></div></div>';
  }).join('');
}
window.relearn=function(i){
  delete S.answers[i];delete S.wrong[i];delete S.cleared[i];delete S.cards[i];
  save();order=buildOrder();
  const pos=order.indexOf(i);if(pos>=0)cur=pos;
  switchPg('do');renderDo();toast('已移出错题本，重新作答');
};
window.clearWrong=function(i){S.cleared[i]=!S.cleared[i];save();renderMk();toast(S.cleared[i]?'已标记掌握':'已恢复为待消灭');};

// ---------- 复习 ----------
function sm2(c,quality){
  if(quality>=3){c.interval=c.reps===0?1:c.reps===1?3:Math.max(1,Math.round(c.interval*c.ease));c.reps++;}
  else{c.reps=0;c.interval=1;}
  c.ease=Math.max(1.3,Math.min(3,c.ease+(0.1-(5-quality)*(0.08+(5-quality)*0.02))));
  const d=new Date();d.setDate(d.getDate()+c.interval);
  c.due=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
  return c;
}
function renderRv(){
  const td=todayStr(),ids=Object.keys(S.cards).map(Number).filter(i=>S.cards[i].due<=td).sort();
  const all=Object.keys(S.cards).length;
  const list=$('rvList');
  if(!all){list.innerHTML='<div class="empty"><div class="big">🗓</div>复习队列为空<br><span class="note">答错的题会自动加入复习队列</span></div>';return;}
  if(!ids.length){list.innerHTML='<div class="empty"><div class="big">✅</div>今日复习已完成（队列 '+all+' 题）</div>';return;}
  list.innerHTML=ids.map(i=>{const c=S.cards[i];
    return '<div class="item"><div class="q"><b>'+(i+1)+'.</b> '+esc(c.q)+'</div>'+
      '<div class="meta"><span class="tag">'+esc(c.k||'知识点')+'</span><span class="tag g">下次间隔 '+c.interval+' 天</span>'+
      '<span class="tag">已复习 '+c.reps+' 次</span></div>'+
      '<div class="nav"><button class="btn sm" style="background:var(--err)" onclick="grade('+i+',1)">😵 忘了</button>'+
      '<button class="btn sm" style="background:var(--warn)" onclick="grade('+i+',3)">🤔 模糊</button>'+
      '<button class="btn sm" style="background:var(--ok)" onclick="grade('+i+',5)">😄 记得</button></div></div>';
  }).join('');
}
window.grade=function(i,q){S.cards[i]=sm2(S.cards[i],q);save();renderRv();toast('已记录，下次间隔 '+S.cards[i].interval+' 天');};

// ---------- 统计 ----------
function renderSt(){
  const ids=Object.keys(S.answers);
  const ok=ids.filter(i=>S.answers[i]===norm(QS[i].answer)).length;
  $('sDone').textContent=ids.length;
  $('sOk').textContent=ok;
  $('sAcc').textContent=(ids.length?Math.round(ok/ids.length*100):0)+'%';
  $('sMk').textContent=Object.keys(S.wrong).length;
  $('sTime').textContent=fmt(S.ms);
  const by={};
  ids.forEach(i=>{const k=QS[i].knowledge||'其他';by[k]=by[k]||{t:0,c:0};by[k].t++;
    if(S.answers[i]===norm(QS[i].answer))by[k].c++;});
  const rows=Object.entries(by).sort((a,b)=>b[1].t-a[1].t).slice(0,30);
  $('sKnow').innerHTML=rows.length?rows.map(([k,v])=>{const p=Math.round(v.c/v.t*100);
    return '<div class="kv"><span>'+esc(k)+' <span class="note">('+v.t+'题)</span></span>'+
      '<b style="color:'+(p>=80?'var(--ok)':p>=60?'var(--warn)':'var(--err)')+'">'+p+'%</b></div>';}).join('')
    :'<div class="empty">暂无数据</div>';
  $('sList').innerHTML=ids.length?QS.map((q,i)=>{const a=S.answers[i];
    return '<div class="item"><div class="q">'+(i+1)+'. '+esc(q.question.slice(0,80))+(q.question.length>80?'…':'')+'</div>'+
      '<div class="meta">'+(a===undefined?'<span class="tag">未作答</span>':
        (a===norm(q.answer)?'<span class="tag g">你答 '+a+' ✅</span>':'<span class="tag r">你答 '+a+' ❌ · 正确 '+norm(q.answer)+'</span>'))+
      (S.flags[i]?'<span class="tag w">🚩</span>':'')+'</div></div>';}).join('')
    :'<div class="empty"><div class="big">📊</div>还没有答题记录</div>';
}

// ---------- 导航 ----------
function switchPg(p){
  document.querySelectorAll('.bar button').forEach(b=>b.classList.toggle('on',b.dataset.pg===p));
  document.querySelectorAll('.pg').forEach(x=>x.classList.remove('on'));
  $('pg-'+p).classList.add('on');
  if(p==='mk')renderMk();if(p==='rv')renderRv();if(p==='st')renderSt();if(p==='br')renderBr();
  window.scrollTo({top:0});
}
document.querySelectorAll('.bar button').forEach(b=>b.onclick=()=>switchPg(b.dataset.pg));
document.querySelectorAll('[data-mkf]').forEach(b=>b.onclick=()=>{
  mkFilter=b.dataset.mkf;document.querySelectorAll('[data-mkf]').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');renderMk();});
$('doPrev').onclick=()=>{if(cur>0){cur--;renderDo();window.scrollTo({top:0});}};
$('doNext').onclick=()=>{if(cur<order.length-1){cur++;renderDo();window.scrollTo({top:0});}else toast('已是最后一题');};
$('doFlag').onclick=()=>{const i=real(cur);S.flags[i]=!S.flags[i];save();renderDo();};
$('brPrev').onclick=()=>{if(brCur>0){brCur--;renderBr();}};
$('brNext').onclick=()=>{if(brCur<order.length-1){brCur++;renderBr();}};
$('btnApply').onclick=()=>{S.settings.rand=$('cRand').checked;S.settings.instant=$('cInstant').checked;
  S.settings.loop=$('cLoop').checked;order=buildOrder();cur=0;save();renderDo();toast('设置已应用');};
$('btnExport').onclick=()=>{const blob=new Blob([JSON.stringify({quiz:QUIZ.id,exported:new Date().toISOString(),state:S},null,2)],
  {type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download=(QUIZ.title||'quiz')+'-存档.json';a.click();URL.revokeObjectURL(a.href);toast('存档已导出');};
$('btnImport').onclick=()=>$('fileImport').click();
$('fileImport').onchange=e=>{const f=e.target.files[0];if(!f)return;
  const r=new FileReader();r.onload=()=>{try{const d=JSON.parse(r.result);
    if(d&&d.state&&d.state.v===2){S=d.state;save();order=buildOrder();cur=0;renderDo();toast('存档已导入');}
    else toast('存档格式不正确');}catch(err){toast('解析失败：'+err.message);}};
  r.readAsText(f);e.target.value='';};
$('btnReset').onclick=()=>{if(!confirm('确定清空全部答题进度？此操作不可撤销。'))return;
  localStorage.removeItem(KEY);S=load();order=buildOrder();cur=0;renderDo();renderSt();toast('进度已清空');};

// 计时
timer=setInterval(()=>{S.ms+=1000;save();
  const el=$('sTime');if(el&&$('pg-st').classList.contains('on'))el.textContent=fmt(S.ms);},1000);

// 键盘
document.addEventListener('keydown',e=>{
  if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA')return;
  const p=document.querySelector('.bar button.on');if(!p)return;
  if(p.dataset.pg==='do'){
    if(e.key==='ArrowLeft')$('doPrev').click();
    else if(e.key==='ArrowRight')$('doNext').click();
    else{const m=/^([1-6])$/.exec(e.key);
      if(m){const i=real(cur),q=QS[i];if(q&&S.answers[i]===undefined){
        const j=+m[1]-1;if(j<(q.options||[]).length)choose(i,letterOf(q.options[j],j));}}}
  }else if(p.dataset.pg==='br'){if(e.key==='ArrowLeft')$('brPrev').click();else if(e.key==='ArrowRight')$('brNext').click();}
});

// 初始化
(function init(){
  $('hdTitle').textContent=QUIZ.title||'离线刷题';
  $('cRand').checked=S.settings.rand;$('cInstant').checked=S.settings.instant;$('cLoop').checked=S.settings.loop;
  if(S.order&&S.order.length===QS.length){/* 保留上次顺序 */}
  const firstUn=QS.findIndex((q,i)=>S.answers[i]===undefined);
  if(firstUn>=0){const pos=order.indexOf(firstUn);if(pos>=0)cur=pos;}
  renderSubjectBar();
  renderDo();
  if(!QS.length)$('foot').innerHTML='本卷题目为空，请回到 ExamBoost 重新生成';
})();
</script>
</body>
</html>'''


def make_quiz_html(title, subject, questions, quiz_id=None):
    """生成自包含的离线刷题 HTML。

    questions: [{question, options, answer, explanation, knowledge, subject}, ...]
    """
    clean = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        text = str(q.get("question") or "").strip()
        if not text:
            continue
        opts = q.get("options") or []
        clean.append({
            "question": text,
            "options": [str(o).strip() for o in opts if str(o).strip()],
            "answer": (str(q.get("answer") or "").strip().upper()[:1]),
            "explanation": str(q.get("explanation") or "").strip(),
            "knowledge": str(q.get("knowledge") or "").strip(),
            "subject": str(q.get("subject") or subject or "").strip(),
        })
    if not quiz_id:
        quiz_id = "q_" + str(abs(hash((title, len(clean), clean[0]["question"] if clean else ""))))[:9]
    payload = {
        "id": quiz_id,
        "title": str(title or "模拟试卷"),
        "subject": str(subject or "综合"),
        "generated": __import__("datetime").datetime.now().strftime("%Y-%m-%d"),
        "count": len(clean),
        "questions": clean,
    }
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    safe_title = escape(payload["title"], quote=True)
    return TEMPLATE.replace("__QUIZ_JSON__", blob).replace("__TITLE__", safe_title)
