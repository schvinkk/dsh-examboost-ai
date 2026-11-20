/* ExamBoost AI — 前端逻辑（原生 JS，无构建） */
"use strict";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/* ---------------- API ---------------- */
async function api(path, opts) {
  const res = await fetch(path, opts);
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; }
  catch (e) { data = { error: `服务返回异常（HTTP ${res.status}）` }; }
  if (!res.ok && !data.error) data.error = `请求失败（HTTP ${res.status}）`;
  return data;
}
const POST = (body) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body || {}),
});

/* ---------------- Toast ---------------- */
let toastTimer = null;
function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("on");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("on"), 2400);
}

/* ---------------- 弹层 ---------------- */
function openSheet(html) {
  $("sheet").innerHTML = '<div class="grip"></div>' + html;
  $("mask").classList.add("on");
  document.body.style.overflow = "hidden";
}
function closeSheet() {
  $("mask").classList.remove("on");
  document.body.style.overflow = "";
}

/* ---------------- 视图切换 ---------------- */
// 四个一级入口：home / gen(学) / practice(练) / sources(资料) / settings(我的)
// 次级视图（模考/错题/复习/计划/AI助手）通过「练」页内的 subnav 进入
const VIEWS = {
  home: { label: "🏠 首页" },
  gen: { label: "📥 学" },
  practice: { label: "✏️ 刷题" },
  exam: { label: "📝 模考" },
  mistakes: { label: "📕 错题本" },
  review: { label: "⏰ 复习" },
  plan: { label: "📅 计划" },
  ai: { label: "🤖 AI 助手" },
  sources: { label: "🌐 资料中枢" },
  settings: { label: "👤 设置" },
};
// 一级入口映射：次级视图归属到哪个底部 tab
const PRIMARY_OF = {
  home: "home", gen: "gen", practice: "practice", exam: "practice",
  mistakes: "practice", review: "practice", plan: "practice", ai: "practice",
  sources: "sources", settings: "settings",
};
let currentView = "home";

// 已移除全局 11 项标签栏 —— 那是"菜单很乱"的根源。
// 次级导航只在「练」页面内部出现，不会和底部导航重复打架。
function renderTabs() {
  // 兼容旧调用：现在只更新「练」页内的 subnav 高亮
  document.querySelectorAll("#practiceSubnav button").forEach((b) => {
    b.classList.toggle("on", b.dataset.v === currentView);
  });
}

function go(view) {
  if (!VIEWS[view]) view = "home";
  currentView = view;
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("on"));
  $("v-" + view).classList.add("on");
  // 底部一级导航高亮（次级视图归到所属一级）
  const primary = PRIMARY_OF[view] || "home";
  document.querySelectorAll(".botnav button").forEach((b) => {
    b.classList.toggle("on", b.dataset.v === primary);
  });
  renderTabs();
  const loaders = {
    home: loadHome, practice: loadPracticeInit, exam: () => {}, mistakes: loadMistakes,
    review: loadReview, plan: loadPlan, ai: loadAiInit, gen: loadGen,
    sources: loadHub, settings: loadSettings,
  };
  (loaders[view] || (() => { }))();
  // 同步地址栏与记忆当前页
  try {
    history.replaceState(null, "", "#" + view);
    localStorage.setItem("eb_view", view);
  } catch (e) { }
  window.scrollTo({ top: 0 });
}

/* ============ v2：首启身份引导 ============ */
let obState = { stage: "", goal: "", major: "", has_material: null, target_date: "", step: 1 };
let obProfileData = null;  // 缓存 /api/profile 返回的阶段与选项

async function startOnboard() {
  if (!obProfileData) obProfileData = await api("/api/profile");
  obState = { stage: "", goal: "", major: "", has_material: null, target_date: "", step: 1 };
  const prof = obProfileData.profile || {};
  if (prof.onboarded) {
    obState = { stage: prof.stage || "", goal: prof.goal || "", major: prof.major || "",
      has_material: prof.has_material, target_date: prof.target_date || "", step: 1 };
  }
  renderObStages();
  showObStep(1);
  $("onboard").style.display = "flex";
  document.body.style.overflow = "hidden";
}
function closeOnboard() { $("onboard").style.display = "none"; document.body.style.overflow = ""; }
function renderObStages() {
  $("obStages").innerHTML = (obProfileData.stages || []).map((s) =>
    `<button class="ob-choice ${obState.stage === s.id ? "sel" : ""}" data-stage="${s.id}">
       <span class="ob-ic">${s.icon}</span><b>${s.label}</b><span class="note">${s.desc}</span></button>`).join("");
  $("obStages").querySelectorAll("[data-stage]").forEach((b) => b.onclick = () => {
    obState.stage = b.dataset.stage; renderObStages();
  });
}
function renderObGoals() {
  const goals = (obProfileData.goals || {})[obState.stage] || [];
  $("obGoals").innerHTML = goals.map((g) =>
    `<button class="ob-choice ${obState.goal === g ? "sel" : ""}" data-goal="${esc(g)}">${esc(g)}</button>`).join("");
  $("obGoals").querySelectorAll("[data-goal]").forEach((b) => b.onclick = () => {
    obState.goal = b.dataset.goal; $("obGoalCustom").value = ""; renderObGoals();
  });
}
function showObStep(n) {
  obState.step = n;
  for (let i = 1; i <= 3; i++) $("obStep" + i).style.display = (i === n ? "block" : "none");
  $("obBack").style.display = n > 1 ? "inline-block" : "none";
  $("obNext").textContent = n === 3 ? "完成，开始用 →" : "下一步";
  if (n === 2) { renderObGoals(); $("obGoalCustom").value = obState.goal && !((obProfileData.goals||{})[obState.stage]||[]).includes(obState.goal) ? obState.goal : ""; }
  if (n === 3) {
    $("obMajor").value = obState.major || "";
    $("obDate").value = obState.target_date || "";
  }
}
async function finishOnboard() {
  const custom = $("obGoalCustom").value.trim();
  if (custom) obState.goal = custom;
  obState.major = $("obMajor").value.trim();
  obState.target_date = $("obDate").value.trim();
  const d = await api("/api/profile", POST({ ...obState, onboarded: true }));
  if (d.error) { toast(d.error); return; }
  // 重新拉一次完整 profile（含服务端算好的 greeting）
  obProfileData = await api("/api/profile");
  closeOnboard();
  toast("设置好了，这就按你的情况来");
  go("home");
}
// 在 bind() 之外单独绑定引导按钮（元素始终存在）
function bindOnboard() {
  $("obNext").onclick = async () => {
    if (obState.step === 1) {
      if (!obState.stage) { toast("先选一个你的身份"); return; }
      showObStep(2); return;
    }
    if (obState.step === 2) {
      if (!obState.goal && !$("obGoalCustom").value.trim()) { toast("选一个目标，或自己写一个"); return; }
      showObStep(3); return;
    }
    await finishOnboard();
  };
  $("obBack").onclick = () => showObStep(Math.max(1, obState.step - 1));
  $("obGoalCustom").oninput = (e) => { if (e.target.value.trim()) obState.goal = ""; };
  document.querySelectorAll(".ob-choice[data-mat]").forEach((b) => b.onclick = () => {
    obState.has_material = b.dataset.mat === "yes";
    document.querySelectorAll(".ob-choice[data-mat]").forEach((x) => x.classList.remove("sel"));
    b.classList.add("sel");
  });
}

/* ============ 首页（按画像个性化） ============ */
function obIcon(stage) {
  const s = (obProfileData?.stages || []).find((x) => x.id === stage);
  return s ? s.icon : "🎯";
}
function obLabel(stage) {
  const s = (obProfileData?.stages || []).find((x) => x.id === stage);
  return s ? s.label : "学习者";
}
async function loadHome() {
  if (!obProfileData) obProfileData = await api("/api/profile");
  const prof = obProfileData.profile || {};
  $("heroAvatar").textContent = obLabel(prof.stage);
  $("heroTitle").textContent = prof.onboarded
    ? `${obLabel(prof.stage)} · ${prof.goal || "备考中"}` : "先认识一下你";
  $("heroGreeting").textContent = obProfileData.greeting || "先告诉我你的情况。";
  renderHomeRecommend(prof);
  const [s, rev] = await Promise.all([api("/api/stats"), api("/api/review")]);
  const st = [
    { n: s.total_answered || 0, l: "已答题", c: "" },
    { n: (s.accuracy || 0) + "%", l: "正确率", c: (s.accuracy || 0) >= 80 ? "ok" : (s.accuracy || 0) >= 60 ? "warn" : "err" },
    { n: s.mistakes_pending || 0, l: "待消灭错题", c: (s.mistakes_pending || 0) > 0 ? "err" : "ok" },
    { n: rev.total_due || 0, l: "今日待复习", c: (rev.total_due || 0) > 0 ? "warn" : "" },
  ];
  $("homeStats").innerHTML = st.map((x) =>
    `<div class="stat"><div class="n ${x.c}">${x.n}</div><div class="l">${x.l}</div></div>`).join("");
  window._homeStats = { s, rev };
  loadHomeAdvice();
}
function renderHomeRecommend(prof) {
  const box = $("recommendActions");
  if (!prof.onboarded) {
    box.innerHTML = `<div class="note">还没设置身份和目标。先花 30 秒设置，我才知道给你什么内容。</div>
      <button class="btn mt8" id="recOnboard">🎯 30 秒设置我的情况</button>`;
    $("recOnboard").onclick = startOnboard;
    return;
  }
  const acts = [];
  if (prof.has_material) acts.push({ i:"📥", t:"导入我的资料", d:"传 PDF/Word/图片，AI 按你的资料出题并标出处", v:"gen" });
  else acts.push({ i:"🌐", t:"帮我找资料", d:"官方源 + 全网检索，找到的都是能核对出处的", v:"sources" });
  acts.push({ i:"✏️", t:"先做几题摸底", d:"系统会据此算出薄弱点，推荐才准", v:"practice" });
  box.innerHTML = acts.map((a) => `<div class="kv"><div><b>${a.i} ${a.t}</b><div class="note">${a.d}</div></div>
    <button class="btn xs" data-go="${a.v}">去</button></div>`).join("");
  box.querySelectorAll("[data-go]").forEach((b) => b.onclick = () => go(b.dataset.go));
}
function loadHomeAdvice() {
  const { s, rev } = window._homeStats || {};
  if (!s) return;
  const list = [];
  if (!s.total_answered) {
    list.push({ i: "🚀", t: "先做 5 题摸清底子", d: "系统会据此算出你的薄弱科目，之后的推荐才准", a: ["去刷题", "practice"] });
  } else {
    if ((rev.total_due || 0) > 0) list.push({ i: "⏰", t: `今天有 ${rev.total_due} 题到期复习`, d: "按 FSRS 记忆曲线复习，比刷新题更划算", a: ["去复习", "review"] });
    if ((s.mistakes_pending || 0) > 0) list.push({ i: "📕", t: `${s.mistakes_pending} 道错题待消灭`, d: "同一道题错两次以上，说明方法没掌握", a: ["去错题本", "mistakes"] });
    if (s.weakest && s.weakest.prob < 0.6) list.push({ i: "🎯", t: `最薄弱：${s.weakest.subject}（${Math.round(s.weakest.prob * 100)}%）`, d: "建议用「只刷薄弱」定向补这块", a: ["刷薄弱", "practice"] });
    if (!s.weakest || (s.weakest.prob >= 0.6 && !rev.total_due && !s.mistakes_pending)) {
      list.push({ i: "📈", t: "基础不错，可以上强度", d: "试试限时模考，或用你的资料让 AI 出模拟卷", a: ["去模考", "exam"] });
    }
  }
  $("adviceList").innerHTML = list.map((x) => `
    <div class="kv"><div><b>${esc(x.t)}</b><div class="note">${esc(x.d)}</div></div>
    <button class="btn xs" data-go="${x.a[1]}">${x.a[0]}</button></div>`).join("");
  $("adviceList").querySelectorAll("[data-go]").forEach((b) => (b.onclick = () => go(b.dataset.go)));
}

/* ============ v2：资料导入 + 溯源出题 ============ */
async function loadGen() {
  const d = await api("/api/materials");
  const mats = d.materials || [];
  $("matList").innerHTML = mats.length
    ? mats.map((m) => `<div class="kv"><div><b>${esc(m.name)}</b>
        <div class="note">${m.char_count} 字 · ${m.exam || "未分类"} · ${esc((m.created||"").slice(0,10))}</div></div>
        <button class="btn xs ghost" data-del="${m.id}">删除</button></div>`).join("")
    : '<div class="empty">还没导入资料。上面粘贴或上传一份试试。</div>';
  $("matList").querySelectorAll("[data-del]").forEach((b) => b.onclick = async () => {
    if (!confirm("删除这份资料？")) return;
    await api("/api/material/" + b.dataset.del, { method: "DELETE" });
    toast("已删除"); loadGen();
  });
  $("genMatId").innerHTML = mats.length
    ? mats.map((m) => `<option value="${m.id}">${esc(m.name)}</option>`).join("")
    : '<option value="">（先导入资料）</option>';
  if (!obProfileData) obProfileData = await api("/api/profile");
  if (!$("genSubject").value && obProfileData.profile?.goal) $("genSubject").value = obProfileData.profile.goal;
}
async function onFileSelected(e) {
  const f = e.target.files[0];
  if (!f) return;
  $("matFileStatus").textContent = `已选：${f.name}（${(f.size/1024).toFixed(0)} KB），正在提取文字…`;
  $("matFileStatus").classList.remove("err");
  if (!$("matName").value) $("matName").value = f.name.replace(/\.[^.]+$/, "");
  try {
    const text = await extractFileText(f);
    $("matText").value = text;
    const d = await api("/api/analyze-file", POST({ filename: f.name, text }));
    $("matPassageCount").textContent = d.ok ? `提取 ${d.char_count} 字 / ${d.passages} 段` : "";
    $("matFileStatus").textContent = d.ok
      ? `✅ 提取完成，请在下方校对后点「导入」（${d.char_count} 字）`
      : (d.error || "提取完成，请校对");
  } catch (err) {
    $("matFileStatus").textContent = "提取失败：" + err.message + "。可直接把文字粘贴到下方。";
    $("matFileStatus").classList.add("err");
  }
}
async function extractFileText(file) {
  const name = file.name.toLowerCase();
  if (name.endsWith(".pdf")) return pdfToText(file);
  if (/\.(docx|doc)$/.test(name)) return docxToText(file);
  if (name.endsWith(".txt") || name.endsWith(".md")) return file.text();
  if (/\.(png|jpg|jpeg|webp)$/.test(name)) return imageToText(file);
  throw new Error("暂不支持该格式，请用 PDF/Word/TXT/图片，或粘贴文字");
}
async function loadScript(src) {
  await new Promise((res, rej) => { const s = document.createElement("script"); s.src = src; s.onload = res; s.onerror = rej; document.head.appendChild(s); });
}
async function pdfToText(file) {
  if (!window.pdfjsLib) await loadScript("https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.min.mjs");
  const buf = await file.arrayBuffer();
  const pdf = await window.pdfjsLib.getDocument({ data: buf }).promise;
  let out = "";
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const tc = await page.getTextContent();
    out += `\n【第${i}页】\n` + tc.items.map((x) => x.str).join(" ") + "\n";
  }
  return out.trim();
}
async function docxToText(file) {
  if (!window.mammoth) await loadScript("https://cdn.jsdelivr.net/npm/mammoth@1.9.0/mammoth.browser.min.js");
  const buf = await file.arrayBuffer();
  const r = await window.mammoth.extractRawText({ arrayBuffer: buf });
  return r.value.trim();
}
async function imageToText(file) {
  if (!window.Tesseract) await loadScript("https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js");
  $("matFileStatus").textContent = "图片 OCR 识别中（首次较慢）…";
  const { data } = await window.Tesseract.recognize(file, "chi_sim+eng", {
    logger: (m) => { if (m.status === "recognizing text") $("matFileStatus").textContent = `OCR 识别中 ${Math.round(m.progress*100)}%`; }
  });
  return data.text.trim();
}
async function importMaterial() {
  const text = $("matText").value.trim();
  if (text.length < 20) { toast("资料太短（至少 20 字），请粘贴或上传"); return; }
  const d = await api("/api/materials", POST({
    name: $("matName").value.trim(), text,
    exam: $("genSubject").value.trim(),
  }));
  if (d.error) { toast(d.error); return; }
  toast(`${d.action === "updated" ? "已更新" : "已导入"}：${d.passages} 段`);
  $("matText").value = ""; $("matFile").value = "";
  loadGen();
}
async function generateFromMaterial() {
  const mid = $("genMatId").value;
  if (!mid) { toast("先导入并选择一份资料"); return; }
  const btn = $("btnMatGen"); const old = btn.textContent;
  btn.textContent = "生成中…（免费模型较慢，请等一会儿）"; btn.disabled = true;
  $("genResult").innerHTML = '<div class="note">AI 正在按你的资料出题，逐句标出处，通常需要 30 秒～2 分钟…</div>';
  const d = await api(`/api/material/${mid}/generate`, POST({
    count: +$("genCount").value || 5, subject: $("genSubject").value.trim() || "综合",
  }));
  btn.textContent = old; btn.disabled = false;
  if (d.error) { $("genResult").innerHTML = `<div class="tag err">${esc(d.error)}</div>`; return; }
  const pv = d.provenance || {};
  const qs = d.questions || [];
  const tagOf = { material: ["🟢","来自资料","ok"], ai: ["🟡","AI补充","warn"], generated: ["⚠️","AI生成","err"] };
  $("genResult").innerHTML = `
    <div class="note mb8">生成 ${d.count} 题 · 🟢资料 ${pv.material||0} / 🟡补充 ${pv.ai||0} / ⚠️生成 ${pv.generated||0}</div>
    ${qs.map((q,i) => {
      const t = tagOf[q.provenance] || tagOf.generated;
      return `<div class="gen-q"><div class="row nowrap"><span class="tag ${t[2]}">${t[0]} ${t[1]}</span>
        ${q.source_para ? `<span class="tag plain">出处 ${esc(q.source_para)}</span>` : ""}</div>
        <div class="mt8"><b>${i+1}. ${esc(q.question)}</b></div>
        <div class="note mt8">${esc(q.explanation||"")}</div></div>`;
    }).join("")}
    <div class="row mt8"><button class="btn sm sec" id="btnDownloadGrounded">⬇️ 把题目做成离线刷题网页</button></div>
    <div class="note mt8">点上面按钮会下载一个单独的 HTML 文件，双击就能刷题，答题记录存在浏览器里，下次打开还在，也能发给别人用。</div>`;
  // Download the REAL offline quiz HTML built from the generated questions.
  window._groundedHtml = d.html || '';
  window._groundedTitle = `${mat_name_for_download()}·溯源练习`;
  $("btnDownloadGrounded").onclick = () => {
    if (!window._groundedHtml) { toast('没有可下载的内容，请重新生成'); return; }
    downloadHtml(window._groundedHtml, (window._groundedTitle || '题库') + '.html');
    toast('已下载，双击打开即可离线刷题');
  };
}
function mat_name_for_download() {
  const sel = $('genMatId');
  return (sel && sel.selectedOptions[0] ? sel.selectedOptions[0].text : '我的题库') || '我的题库';
}

/* ============ v2：资料中枢 ============ */
let hubData = null;
async function loadHub() {
  hubData = await api("/api/sources/hub");
  const rec = hubData.recommended || [];
  $("hubRecommended").innerHTML = rec.length
    ? rec.map((s) => sourceCard(s)).join("")
    : '<div class="note">还没设置目标。设置后这里会按你的考试推荐官方源。</div>';
  $("hubOfficial").innerHTML = (hubData.official || []).map((s) => sourceCard(s)).join("");
  loadHubFavs();
}
function sourceCard(s) {
  const verified = s.verified === true ? '<span class="tag ok">已核验</span>'
    : s.verified === false ? '<span class="tag err">不可达</span>' : '<span class="tag plain">待核验</span>';
  return `<div class="kv"><div><b>${esc(s.name)}</b> ${verified}
    <div class="note">${esc(s.exam||"")} · ${esc(s.provides||"")}</div>
    <div class="note mono" style="word-break:break-all">${esc(s.url)}</div></div>
    ${s.url ? `<a class="btn xs" href="${esc(s.url)}" target="_blank" rel="noopener">打开</a>` : ""}</div>`;
}
function renderHubSearch() {
  const kw = $("hubKw").value.trim();
  if (!kw) { toast("输入关键词"); return; }
  const links = (hubData.search || []).filter((s) => s.base).map((s) => {
    const url = s.base + encodeURIComponent(s.tpl.replace("{kw}", kw));
    return `<a class="btn sm sec" style="display:inline-block;margin:4px 6px 0 0" href="${url}" target="_blank" rel="noopener">${esc(s.name)} ↗</a>`;
  }).join("");
  $("hubSearchLinks").innerHTML = links;
  $("hubSearchNote").textContent = `已生成「${kw}」的检索入口，点开后请核对来源可靠性。`;
}
async function loadHubFavs() {
  const d = await api("/api/pan-search");
  const favs = d.favorites || [];
  $("panFavList").innerHTML = favs.length
    ? favs.map((f) => `<div class="kv"><div><b>${esc(f.title)}</b><div class="note mono">${esc(f.url)}</div></div>
        <a class="btn xs" href="${esc(f.url)}" target="_blank" rel="noopener">打开</a></div>`).join("")
    : '<div class="note">还没有收藏。找到好资料可存这里。</div>';
}

/* ============ 亮点：把题库做成离线刷题网页 ============ */
async function openBankSheet() {
  const d = await api("/api/bank/stats");
  const facData = await api("/api/offline-bank?subjects=1");
  const cleanSubjects = facData.subjects || [];
  openSheet(`
    <h3>📦 做离线题库网页</h3>
    <p class="note">下载一个单独的 HTML 文件，双击就能像软件一样刷题。答题记录存在浏览器本地，下次打开还在，可发给别人用。题目自动按科目分栏，可切换。</p>
    <div class="note mt8">当前题库：内置 ${d.builtin||0} + 我的 ${d.user||0} 题</div>
    <label class="mt8">打包范围</label>
    <select id="bankScope">
      <option value="all">全部题目（内置 + 我的）</option>
      <option value="mine">只要我的资料/AI 生成的题</option>
    </select>
    <label class="mt8">只要某一科（可选）</label>
    <select id="bankSubject"><option value="">全部科目</option>${cleanSubjects.map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join('')}</select>
    <div class="row mt14">
      <button class="btn" id="btnBankDownload">⬇️ 下载离线题库</button>
    </div>
    <button class="btn full mt8" onclick="closeSheet()">关闭</button>`);
  $("btnBankDownload").onclick = () => {
    const scope = $("bankScope").value;
    const subj = $("bankSubject").value;
    const url = `/api/offline-bank?only=${encodeURIComponent(scope)}&subject=${encodeURIComponent(subj)}`;
    const a = document.createElement("a");
    a.href = url; a.download = ""; document.body.appendChild(a); a.click(); a.remove();
    toast("已开始下载，双击 HTML 即可离线刷题");
    closeSheet();
  };
}

/* ---------------- 首页 ---------------- */
function loadHomeAdvice() {
  const { s, rev } = window._homeStats || {};
  if (!s) return;
  const list = [];
  if (!s.total_answered) {
    list.push({ i: "🚀", t: "先做 5 题摸清底子", d: "系统会据此算出你的薄弱科目，之后的推荐才准", a: ["去刷题", "practice"] });
  } else {
    if ((rev.total_due || 0) > 0) list.push({ i: "⏰", t: `今天有 ${rev.total_due} 题到期复习`, d: "按 FSRS 记忆曲线复习，比刷新题更划算", a: ["去复习", "review"] });
    if ((s.mistakes_pending || 0) > 0) list.push({ i: "📕", t: `${s.mistakes_pending} 道错题待消灭`, d: "同一道题错两次以上，说明方法没掌握", a: ["去错题本", "mistakes"] });
  }
  $("adviceList").innerHTML = list.map((x) => `
    <div class="kv"><div><b>${esc(x.t)}</b><div class="note">${esc(x.d)}</div></div>
    <button class="btn xs" data-go="${x.a[1]}">${x.a[0]}</button></div>`).join("");
  $("adviceList").querySelectorAll("[data-go]").forEach((b) => (b.onclick = () => go(b.dataset.go)));
}

/* ---------------- AI 状态条 ---------------- */
let providersCache = [];
async function refreshAiChip() {
  try {
    const d = await api("/api/ai/providers");
    providersCache = d.providers || [];
    const active = providersCache.find((p) => p.id === d.active);
    const chip = $("aiChip");
    if (active) {
      chip.classList.remove("off");
      $("aiChipText").textContent = active.label + (active.anon ? "" : " ✓");
    } else {
      chip.classList.add("off");
      $("aiChipText").textContent = "AI 未就绪";
    }
  } catch (e) {
    $("aiChipText").textContent = "离线";
  }
}
async function refreshAi() {
  toast("正在扫描可用模型…");
  await api("/api/ai/config", POST({ auto: true }));
  await refreshAiChip();
  toast("扫描完成");
}

function openProviderSheet() {
  const rows = providersCache.map((p) => `
    <div class="item">
      <div class="row"><b>${esc(p.label)}</b>
        <span class="tag ${p.available ? "ok" : "plain"}">${p.available ? "可用" : "不可用"}</span>
        ${p.anon ? '<span class="tag">免登录</span>' : ""}</div>
      <div class="note">${esc(p.desc)}${p.error ? "<br>⚠️ " + esc(p.error) : ""}</div>
      <div class="acts">
        <button class="btn xs ${p.id === (window.__activeId || "") ? "" : "sec"}" onclick="chooseProvider('${p.id}')">用这一路</button>
        ${p.switch_hint ? '<span class="note">需先在 DSH 设置里打开「本地转发」</span>' : ""}
      </div>
    </div>`).join("");
  openSheet(`<h3>🤖 选择模型来源</h3>
    <p class="note">按顺序自动回落：排在前面的失败会自动试下一个。免登录池无需任何配置。</p>
    <div class="mt8">${rows || '<div class="empty">没有检测到候选</div>'}</div>
    <button class="btn full mt8" onclick="closeSheet()">关闭</button>`);
}
async function chooseProvider(id) {
  const d = await api("/api/ai/config", POST({ preferred: id }));
  if (d.ok) { toast("已切换：" + (d.label || id)); closeSheet(); await refreshAiChip(); }
  else toast(d.error || "切换失败");
}

/* ---------------- 刷题 ---------------- */
let quiz = { list: [], idx: 0, answered: {}, mode: "normal" };

function filters() {
  return {
    stage: $("fStage").value,
    subject: $("fSubject").value,
    type: $("fType").value,
    difficulty: $("fDiff").value,
    keyword: $("fKeyword").value.trim(),
  };
}

async function loadPracticeInit() {
  const f = await api("/api/facets");
  fillSelect($("fStage"), Object.keys(f.stages || {}), $("fStage").value);
  const stage = $("fStage").value;
  const subs = Object.keys(f.subjects || {}).filter((k) => !stage || k.startsWith(stage + "/"))
    .map((k) => k.split("/")[1]);
  fillSelect($("fSubject"), subs, $("fSubject").value);
  fillSelect($("fType"), Object.keys(f.types || {}), $("fType").value);
  const total = Object.values(f.stages || {}).reduce((a, b) => a + b, 0);
  $("poolCount").textContent = total;
  $("fStage").onchange = () => loadPracticeInit();
}

function fillSelect(sel, values, keep) {
  const cur = keep !== undefined ? keep : sel.value;
  sel.innerHTML = '<option value="">全部</option>' +
    values.map((v) => `<option ${v === cur ? "selected" : ""}>${esc(v)}</option>`).join("");
}

async function drawQuestions(count, extra) {
  const f = filters();
  const qs = new URLSearchParams();
  if (f.stage) qs.set("stage", f.stage);
  if (f.subject) qs.set("subject", f.subject);
  if (f.type) qs.set("type", f.type);
  if (f.difficulty && f.difficulty !== "0") qs.set("difficulty", f.difficulty);
  if (f.keyword) qs.set("keyword", f.keyword);
  if (extra) Object.entries(extra).forEach(([k, v]) => qs.set(k, v));
  qs.set("count", count);
  const d = await api("/api/questions?" + qs.toString());
  if (d.error) { toast(d.error); return; }
  if (!d.questions || !d.questions.length) {
    toast(d.hint || "没有符合条件的题目");
    return;
  }
  quiz = { list: d.questions, idx: 0, answered: {}, mode: d.mode || "normal" };
  renderQuestion();
}

function renderQuestion() {
  const area = $("practiceArea");
  if (!quiz.list.length) { area.innerHTML = ""; return; }
  const q = quiz.list[quiz.idx];
  const done = Object.keys(quiz.answered).length;
  const opts = (q.options || []).map((op, i) => {
    const letter = /^[A-F][..、)）]/.test(op.trim()) ? op.trim()[0].toUpperCase() : String.fromCharCode(65 + i);
    const text = op.replace(/^\s*[A-F]\s*[..、)）]\s*/, "");
    const chosen = quiz.answered[q.id];
    let cls = "opt";
    if (chosen) {
      if (letter === q.answer) cls += " right";
      else if (letter === chosen) cls += " wrong";
    }
    return `<button class="${cls}" data-l="${letter}" ${chosen ? "disabled" : ""}>
      <span class="lt">${letter}</span><span class="tx">${esc(text)}</span></button>`;
  }).join("");
  const chosen = quiz.answered[q.id];
  const expl = chosen ? explHtml(chosen === q.answer, q) : "";
  area.innerHTML = `
    <div class="card">
      <div class="row">
        <span class="tag">${quiz.idx + 1} / ${quiz.list.length}</span>
        ${q.subject ? `<span class="tag plain">${esc(q.subject)}</span>` : ""}
        ${q.type ? `<span class="tag plain">${esc(q.type)}</span>` : ""}
        ${q.knowledge ? `<span class="tag ok">${esc(q.knowledge)}</span>` : ""}
        <span class="sp"></span>
        <span class="note">${"★".repeat(q.difficulty || 1)}</span>
      </div>
      <div class="q-text">${esc(q.question)}</div>
      <div class="opts">${opts || '<div class="note">本题为开放题，请自评</div>'}</div>
      ${expl}
      <div class="row mt14">
        <button class="btn sm ghost" id="qPrev" ${quiz.idx === 0 ? "disabled" : ""}>← 上一题</button>
        <button class="btn sm ghost" id="qExplain">💡 让 AI 讲解</button>
        <span class="sp"></span>
        <button class="btn sm" id="qNext" ${quiz.idx >= quiz.list.length - 1 ? "disabled" : ""}>下一题 →</button>
      </div>
      ${done === quiz.list.length ? `<div class="alert ok mt8">本组 ${quiz.list.length} 题已完成，正确 ${countRight()} 题。要不要<a href="javascript:go('review')" style="color:inherit">去复习</a>？</div>` : ""}
    </div>`;
  area.querySelectorAll(".opt:not([disabled])").forEach((b) => (b.onclick = () => answer(b.dataset.l)));
  $("qPrev").onclick = () => { quiz.idx--; renderQuestion(); };
  $("qNext").onclick = () => { if (quiz.idx < quiz.list.length - 1) { quiz.idx++; renderQuestion(); } };
  $("qExplain").onclick = () => explainQuestion(q);
}

function countRight() {
  return Object.entries(quiz.answered).filter(([id, a]) => {
    const q = quiz.list.find((x) => x.id === id);
    return q && a === q.answer;
  }).length;
}

function explHtml(ok, q) {
  return `<div class="expl ${ok ? "ok" : "err"}">
    <div class="h">${ok ? "✅ 回答正确" : "❌ 回答错误 · 正确答案 " + esc(q.answer)}</div>
    ${esc(q.explanation || "这题没有解析。可以让 AI 讲解一下。")}</div>`;
}

async function answer(letter) {
  const q = quiz.list[quiz.idx];
  if (quiz.answered[q.id]) return;
  const d = await api("/api/answer", POST({
    id: q.id, answer: letter, reason: "未分类",
  }));
  if (d.error) { toast(d.error); return; }
  if (d.self_grade) {
    quiz.answered[q.id] = letter;
    renderQuestion();
    toast("本题无标准答案，请自评");
    return;
  }
  quiz.answered[q.id] = letter;
  renderQuestion();
  if (!d.correct) setTimeout(() => {
    const bad = document.querySelector(".opt.wrong");
    if (bad) bad.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, 60);
}

async function explainQuestion(q) {
  toast("AI 正在讲解…");
  const d = await api("/api/ai/explain", POST({ question: q.question + "\n选项：" + (q.options || []).join(" ") }));
  if (d.error) { toast(d.error); return; }
  openSheet(`<h3>💡 AI 讲解</h3>
    <div class="q-text" style="font-size:14px">${esc(q.question)}</div>
    <div class="expl ok">${esc(d.content)}</div>
    <button class="btn full mt8" onclick="closeSheet()">知道了</button>`);
}

/* ---------------- 模考 ---------------- */
let exam = null;

async function startExam() {
  const count = parseInt($("examCount").value) || 20;
  const f = filters();
  const qs = new URLSearchParams();
  Object.entries(f).forEach(([k, v]) => { if (v && v !== "0") qs.set(k, v); });
  qs.set("count", count);
  const d = await api("/api/questions?" + qs.toString());
  if (!d.questions || !d.questions.length) { toast("没有可用题目"); return; }
  exam = {
    list: d.questions, answers: {}, idx: 0,
    deadline: Date.now() + Math.max(3, Math.round(d.questions.length * 1.2)) * 60000,
    submitted: false,
  };
  renderExam();
  exam.timer = setInterval(renderExamClock, 1000);
}

function renderExamClock() {
  if (!exam || exam.submitted) return;
  const left = Math.max(0, exam.deadline - Date.now());
  const m = Math.floor(left / 60000), s = Math.floor((left % 60000) / 1000);
  const el = $("examClock");
  if (el) {
    el.textContent = `${m}:${String(s).padStart(2, "0")}`;
    el.style.color = left < 60000 ? "var(--err)" : "";
  }
  if (left === 0) submitExam(true);
}

function renderExam() {
  const area = $("examArea");
  if (!exam) { area.innerHTML = ""; return; }
  const q = exam.list[exam.idx];
  const opts = (q.options || []).map((op, i) => {
    const L = /^[A-F][..、)）]/.test(op.trim()) ? op.trim()[0].toUpperCase() : String.fromCharCode(65 + i);
    const sel = exam.answers[q.id] === L ? " sel" : "";
    return `<button class="opt${sel}" data-l="${L}"><span class="lt">${L}</span>
      <span class="tx">${esc(op.replace(/^\s*[A-F]\s*[..、)）]\s*/, ""))}</span></button>`;
  }).join("");
  const nav = exam.list.map((it, i) =>
    `<button class="btn xs ${i === exam.idx ? "" : "ghost"}" style="${exam.answers[it.id] ? "background:var(--p);color:#fff" : ""}"
      onclick="examJump(${i})">${i + 1}</button>`).join(" ");
  area.innerHTML = `
    <div class="card">
      <div class="row">
        <span class="tag">${exam.idx + 1} / ${exam.list.length}</span>
        <span class="sp"></span>
        <span class="note">剩余 <b class="mono" id="examClock">--:--</b></span>
      </div>
      <div class="q-text">${esc(q.question)}</div>
      <div class="opts">${opts}</div>
      <div class="row mt14">
        <button class="btn sm ghost" onclick="examJump(${exam.idx - 1})" ${exam.idx === 0 ? "disabled" : ""}>← 上一题</button>
        <button class="btn sm ghost" onclick="examJump(${exam.idx + 1})" ${exam.idx >= exam.list.length - 1 ? "disabled" : ""}>下一题 →</button>
        <span class="sp"></span>
        <button class="btn sm err" onclick="submitExam(false)">交卷</button>
      </div>
    </div>
    <div class="card tight"><h3>答题卡</h3><div class="row" style="gap:6px">${nav}</div></div>`;
  area.querySelectorAll(".opt").forEach((b) => (b.onclick = () => {
    exam.answers[q.id] = b.dataset.l; renderExam(); renderExamClock();
  }));
  renderExamClock();
}
window.examJump = (i) => { if (exam && i >= 0 && i < exam.list.length) { exam.idx = i; renderExam(); } };

async function submitExam(auto) {
  if (!exam || exam.submitted) return;
  exam.submitted = true;
  clearInterval(exam.timer);
  const payload = exam.list.map((q) => ({ id: q.id, answer: exam.answers[q.id] || "" }));
  const d = await api("/api/answer-batch", POST({ answers: payload }));
  const right = exam.list.filter((q) => exam.answers[q.id] === q.answer).length;
  const blank = exam.list.filter((q) => !exam.answers[q.id]).length;
  const detail = exam.list.map((q, i) => {
    const a = exam.answers[q.id];
    const ok = a === q.answer;
    return `<div class="item"><div class="row"><span class="tag ${ok ? "ok" : "err"}">${i + 1} ${ok ? "✓" : "✗"}</span>
      <span class="note">${esc(q.subject || "")} ${esc(q.knowledge || "")}</span></div>
      <div class="q" style="margin-top:7px">${esc(q.question)}</div>
      <div class="meta">你的答案：${a || "未作答"} · 正确：${esc(q.answer)}</div>
      ${q.explanation ? `<div class="expl ${ok ? "ok" : "err"}" style="margin-top:8px">${esc(q.explanation)}</div>` : ""}</div>`;
  }).join("");
  $("examArea").innerHTML = `
    <div class="card hero"><h3 style="color:#fff">${auto ? "⏰ 时间到，已自动交卷" : "📝 交卷完成"}</h3>
      <div class="grid c3" style="margin-top:10px">
        <div class="stat"><div class="n">${right}</div><div class="l">答对</div></div>
        <div class="stat"><div class="n err">${exam.list.length - right - blank}</div><div class="l">答错</div></div>
        <div class="stat"><div class="n warn">${blank}</div><div class="l">未作答</div></div>
      </div>
      <p class="mt8">正确率 ${Math.round(right / exam.list.length * 100)}%，错题已自动进错题本与复习队列。</p>
    </div>
    <div class="card"><h3>逐题解析</h3>${detail}</div>`;
  toast("成绩已记录");
}

async function offlineExamPack() {
  toast("正在组卷…");
  const f = filters();
  const qs = new URLSearchParams();
  Object.entries(f).forEach(([k, v]) => { if (v && v !== "0") qs.set(k, v); });
  qs.set("count", "30");
  const d = await api("/api/questions?" + qs.toString());
  if (!d.questions || !d.questions.length) { toast("没有可用题目"); return; }
  const g = await api("/api/generate-tool", POST({
    title: (f.subject || f.stage || "综合") + " 练习卷",
    subject: f.subject || f.stage || "综合",
    questions: d.questions,
  }));
  if (g.error) { toast(g.error); return; }
  downloadHtml(g.html, g.title + ".html");
  toast(`已生成 ${g.count} 题离线包`);
}

/* ---------------- 错题本 ---------------- */
let mistakeFilter = "";
async function loadMistakes() {
  const qs = mistakeFilter ? "?status=" + encodeURIComponent(mistakeFilter) : "";
  const d = await api("/api/mistakes" + qs);
  const list = $("mistakeList");
  const items = (d.mistakes || []).slice().reverse();
  if (!items.length) {
    list.innerHTML = `<div class="card"><div class="empty"><div class="big">🎉</div>这里没有错题${mistakeFilter ? "（当前筛选）" : ""}</div></div>`;
    return;
  }
  list.innerHTML = items.map((m) => {
    const opts = (m.options || []).map((op) => {
      const L = /^[A-F][..、)）]/.test(String(op).trim()) ? String(op).trim()[0].toUpperCase() : "";
      let cls = "opt";
      if (L && L === m.correct_answer) cls += " right";
      else if (L && L === m.answer) cls += " wrong";
      return `<div class="${cls}" style="cursor:default"><span class="lt">${L || "?"}</span>
        <span class="tx">${esc(String(op).replace(/^\s*[A-F]\s*[..、)）]\s*/, ""))}</span></div>`;
    }).join("");
    return `<div class="item">
      <div class="row"><span class="tag plain">${esc(m.subject || m.stage || "错题")}</span>
        ${m.knowledge ? `<span class="tag ok">${esc(m.knowledge)}</span>` : ""}
        ${m.count > 1 ? `<span class="tag err">错 ${m.count} 次</span>` : ""}
        <span class="tag ${m.status === "已消灭" ? "ok" : "warn"}">${esc(m.status)}</span></div>
      <div class="q mt8">${esc(m.question)}</div>
      ${opts ? `<div class="opts mt8">${opts}</div>` : ""}
      ${m.explanation ? `<div class="expl err">${esc(m.explanation)}</div>` : ""}
      <div class="meta">你的答案：${esc(m.answer || "—")} · 正确：${esc(m.correct_answer || "—")} · 错因：${esc(m.reason || "未分类")}
        · ${esc((m.created || "").slice(0, 10))}</div>
      <div class="acts">
        <button class="btn xs sec" onclick="relearn('${esc(m.qid || "")}','${esc(m.id)}')">重做这题</button>
        <button class="btn xs ghost" onclick="clearMistake('${esc(m.id)}')">${m.status === "已消灭" ? "恢复为待消灭" : "标记已掌握"}</button>
      </div></div>`;
  }).join("");
}
window.clearMistake = async (id) => {
  await api("/api/mistakes/clear", POST({ id }));
  toast("已更新"); loadMistakes();
};
window.relearn = async (qid, mid) => {
  if (!qid) { toast("该题已不在题库中，无法重做"); return; }
  const q = await api("/api/question/" + encodeURIComponent(qid));
  if (q.error || !q.question) { toast("题目已不存在"); return; }
  quiz = { list: [q], idx: 0, answered: {}, mode: "retry" };
  go("practice");
  renderQuestion();
  toast("已载入，重新作答");
};

/* ---------------- 复习 ---------------- */
async function loadReview() {
  const d = await api("/api/review");
  $("rvTotal").textContent = d.total_cards;
  $("rvDue").textContent = d.total_due;
  const list = $("reviewList");
  if (!d.due.length) {
    list.innerHTML = `<div class="card"><div class="empty"><div class="big">${d.total_cards ? "✅" : "🗓"}</div>
      ${d.total_cards ? "今日复习已完成，队列里还有 " + d.total_cards + " 题" : "复习队列为空<br><span class='note'>答错的题会自动进入队列</span>"}</div></div>`;
    return;
  }
  list.innerHTML = d.due.map((c) => `
    <div class="card">
      <div class="row"><span class="tag plain">${esc(c.subject || "")}</span>
        ${c.knowledge ? `<span class="tag ok">${esc(c.knowledge)}</span>` : ""}
        <span class="sp"></span><span class="note">已复习 ${c.repetitions || 0} 次</span></div>
      <div class="q-text">${esc(c.question)}</div>
      <div class="opts">${(c.options || []).map((op, i) => {
        const L = /^[A-F][..、)）]/.test(String(op).trim()) ? String(op).trim()[0].toUpperCase() : String.fromCharCode(65 + i);
        return `<div class="opt${L === c.answer ? " right" : ""}" style="cursor:default">
          <span class="lt">${L}</span><span class="tx">${esc(String(op).replace(/^\s*[A-F]\s*[..、)）]\s*/, ""))}</span></div>`;
      }).join("")}</div>
      ${c.explanation ? `<div class="expl ok">${esc(c.explanation)}</div>` : ""}
      <label class="mt8">回忆得怎么样？</label>
      <div class="row">
        <button class="btn sm err" onclick="gradeCard('${esc(c.id)}',1)">😵 忘了</button>
        <button class="btn sm" style="background:var(--warn)" onclick="gradeCard('${esc(c.id)}',3)">🤔 模糊</button>
        <button class="btn sm ok" onclick="gradeCard('${esc(c.id)}',5)">😄 记得</button>
      </div>
    </div>`).join("");
}
window.gradeCard = async (id, quality) => {
  const d = await api("/api/review/submit", POST({ id, quality }));
  if (d.error) { toast(d.error); return; }
  toast(`已记录，下次 ${d.card.interval} 天后复习`);
  loadReview();
};

/* ---------------- 计划 ---------------- */
async function loadPlan() {
  const d = await api("/api/plan");
  if (d.plan) renderPlan(d.plan);
}
async function genPlan() {
  const d = await api("/api/plan", POST({
    exam_date: $("planDate").value,
    daily_hours: parseFloat($("planHours").value) || 3,
    subject: $("planSubject").value || "综合",
  }));
  if (d.error) { toast(d.error); return; }
  renderPlan(d.plan);
  toast("计划已生成并保存");
}
function renderPlan(p) {
  const phases = p.phases.map((x) => `
    <div class="card" style="border-left:4px solid var(--p)">
      <h3>${esc(x.name)}<span class="sp"></span><span class="tag plain">${x.days} 天 · ${x.hours} 小时</span></h3>
      <div class="note">${esc(x.start)} ~ ${esc(x.end)}</div>
      <p class="mt8">${esc(x.focus)}</p>
      <ul style="margin:8px 0 0 18px;font-size:13px;color:var(--mu);line-height:1.8">
        ${x.tasks.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>
    </div>`).join("");
  const weeks = (p.weekly || []).slice(0, 12).map((w) =>
    `<div class="kv"><span>第 ${w.week} 周 · ${esc(w.phase)} <span class="note">${esc(w.start)}</span></span>
     <b>${w.hours}h</b></div>`).join("");
  $("planArea").innerHTML = `
    <div class="card hero"><h3 style="color:#fff">📅 ${esc(p.subject)} 冲刺计划</h3>
      <div class="grid c3" style="margin-top:10px">
        <div class="stat"><div class="n">${p.days_left}</div><div class="l">剩余天数</div></div>
        <div class="stat"><div class="n">${p.daily_hours}h</div><div class="l">每日投入</div></div>
        <div class="stat"><div class="n">${p.total_hours}</div><div class="l">总时长</div></div>
      </div>
      <p class="mt8">考试日 ${esc(p.exam_date)}。按基础 → 强化 → 冲刺推进，每周末回看错题本清零。</p>
    </div>${phases}
    <div class="card"><h3>🗓 每周里程碑</h3>${weeks || '<div class="note">周期太短，无需按周拆分</div>'}</div>`;
}

/* ---------------- AI 助手 ---------------- */
const chatHistory = [];
const QUICKS = [
  "帮我出 5 道行测资料分析题",
  "讲讲申论归纳概括的采分点",
  "用口诀帮我记马原唯物论",
  "结构化面试综合分析怎么搭框架",
  "把这段知识点编成 3 道选择题",
  "我高数薄弱，给一周补强安排",
];
function loadAiInit() {
  if (!$("aiQuick").dataset.done) {
    $("aiQuick").innerHTML = QUICKS.map((q) => `<button>${esc(q)}</button>`).join("");
    $("aiQuick").querySelectorAll("button").forEach((b) => (b.onclick = () => {
      $("chatInput").value = b.textContent; sendChat();
    }));
    $("aiQuick").dataset.done = "1";
  }
}
async function sendChat() {
  const text = $("chatInput").value.trim();
  if (!text) return;
  $("chatInput").value = "";
  const box = $("chatBox");
  box.insertAdjacentHTML("beforeend",
    `<div class="msg me"><div class="av">我</div><div class="bub">${esc(text)}</div></div>`);
  const loadId = "ld" + Date.now();
  box.insertAdjacentHTML("beforeend",
    `<div class="msg" id="${loadId}"><div class="av">🤖</div><div class="bub"><span class="spin dark"></span> 正在思考…</div></div>`);
  box.scrollTop = box.scrollHeight;
  chatHistory.push({ role: "user", content: text });
  const d = await api("/api/ai/chat", POST({ messages: chatHistory.slice(-12) }));
  const node = $(loadId);
  if (node) node.remove();
  if (d.ok) {
    chatHistory.push({ role: "assistant", content: d.content });
    $("aiUsedTag").textContent = d.provider || "";
    box.insertAdjacentHTML("beforeend",
      `<div class="msg"><div class="av">🤖</div><div class="bub">${esc(d.content)}
        ${d.fallbacks ? `<div class="note mt8" style="opacity:.7">（已自动回落 ${d.fallbacks} 次）</div>` : ""}</div></div>`);
  } else {
    box.insertAdjacentHTML("beforeend",
      `<div class="msg"><div class="av">⚠️</div><div class="bub err">${esc(d.error || "调用失败")}
        <div class="row mt8"><button class="btn xs" onclick="go('settings')">去检查模型配置</button></div></div></div>`);
  }
  box.scrollTop = box.scrollHeight;
}

/* ---------------- 生成刷题 ---------------- */
async function genFromText() {
  const text = $("genText").value.trim();
  if (text.length < 10) { toast("请先粘贴学习资料（至少 10 字）"); return; }
  $("genResult").innerHTML = '<div class="alert info"><span class="spin"></span> AI 正在出题，资料长时可能需要 1-2 分钟…</div>';
  $("btnGenAi").disabled = true;
  const d = await api("/api/ai/generate", POST({
    text, count: parseInt($("genCount").value) || 10,
    subject: $("genSubject").value || "综合",
    title: $("genTitle").value || "模拟试卷",
    type: $("genType").value,
  }));
  $("btnGenAi").disabled = false;
  if (d.error) {
    $("genResult").innerHTML = `<div class="alert err">${esc(d.error)}</div>
      ${d.raw ? `<details><summary class="note" style="cursor:pointer">查看模型原始返回</summary>
      <div class="mono" style="white-space:pre-wrap;font-size:11px">${esc(d.raw)}</div></details>` : ""}`;
    return;
  }
  window.__lastGen = d;
  $("genResult").innerHTML = `
    <div class="alert ok">✅ 已生成 ${d.count} 道题（模型：${esc(d.provider || "—")}）</div>
    <div class="row">
      <button class="btn sm" onclick="downloadGen()">⬇️ 下载离线刷题包</button>
      <button class="btn sm sec" onclick="saveGenToBank()">存进我的题库</button>
      <button class="btn sm ghost" onclick="previewGen()">预览题目</button>
    </div>`;
}
function downloadGen() {
  const d = window.__lastGen;
  if (!d) return;
  downloadHtml(d.html, (d.title || "试卷") + ".html");
  toast("已下载，双击即可离线刷题");
}
async function saveGenToBank() {
  const d = window.__lastGen;
  if (!d) return;
  const r = await api("/api/questions/import", POST({ questions: d.questions, source: "ai" }));
  if (r.error) { toast(r.error); return; }
  toast(`已入库 ${r.added} 题${r.skipped ? "（跳过重复 " + r.skipped + "）" : ""}`);
}
function previewGen() {
  const d = window.__lastGen;
  if (!d) return;
  openSheet(`<h3>👀 题目预览（${d.count} 题）</h3>` +
    d.questions.map((q, i) => `<div class="item"><div class="q"><b>${i + 1}.</b> ${esc(q.question)}</div>
      <div class="opts mt8">${(q.options || []).map((op) => `<div class="opt" style="cursor:default"><span class="tx">${esc(op)}</span></div>`).join("")}</div>
      <div class="meta">答案 ${esc(q.answer)} · ${esc(q.knowledge || "")}</div></div>`).join("") +
    `<button class="btn full mt8" onclick="closeSheet()">关闭</button>`);
}
async function analyzeMaterial() {
  const text = $("genText").value.trim();
  if (text.length < 20) { toast("资料太短，无法拆解"); return; }
  $("genResult").innerHTML = '<div class="alert info"><span class="spin"></span> 正在拆解知识点…</div>';
  const d = await api("/api/ai/analyze-material", POST({ text }));
  if (d.error) { $("genResult").innerHTML = `<div class="alert err">${esc(d.error)}</div>`; return; }
  if (!d.points.length) {
    $("genResult").innerHTML = `<div class="alert warn">没解析出结构化结果，模型原始输出：<div class="mono mt8">${esc(d.raw || "")}</div></div>`;
    return;
  }
  $("genResult").innerHTML = `<div class="alert ok">✅ 拆出 ${d.points.length} 个知识点</div>` +
    d.points.map((p) => `<div class="item"><b>${esc(p.knowledge || "")}</b>
      <ul style="margin:6px 0 0 18px;font-size:13px;color:var(--mu)">${(p.points || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
      ${p.exam ? `<div class="meta">可能考法：${esc(p.exam)}</div>` : ""}</div>`).join("") +
    `<button class="btn full mt8" onclick="closeSheet()">完成</button>`;
}
async function importJson(makeQuiz) {
  let items;
  try { items = JSON.parse($("genJson").value.trim()); }
  catch (e) { $("genJsonResult").innerHTML = `<div class="alert err">JSON 格式错误：${esc(e.message)}</div>`; return; }
  if (!Array.isArray(items) || !items.length) {
    $("genJsonResult").innerHTML = '<div class="alert err">请粘贴题目数组（以 [ 开头）</div>'; return;
  }
  const r = await api("/api/questions/import", POST({ questions: items, source: "custom" }));
  if (r.error) { $("genJsonResult").innerHTML = `<div class="alert err">${esc(r.error)}</div>`; return; }
  let msg = `<div class="alert ok">✅ 入库 ${r.added} 题，跳过 ${r.skipped} 题</div>`;
  if (makeQuiz) {
    const g = await api("/api/generate-tool", POST({
      title: $("genTitle").value || "手动组卷", subject: $("genSubject").value || "综合", questions: items,
    }));
    if (g.html) { downloadHtml(g.html, (g.title || "试卷") + ".html"); msg += `<div class="note">离线包已下载（${g.count} 题）</div>`; }
    else msg += `<div class="alert err">${esc(g.error || "生成失败")}</div>`;
  }
  $("genJsonResult").innerHTML = msg;
}
function downloadHtml(html, filename) {
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

/* ---------------- 资源中心 ---------------- */
let allSources = [], srcFilter = "";
async function loadSources() {
  const d = await api("/api/sources");
  allSources = d.sources || [];
  renderSources();
}
function renderSources() {
  const list = $("sourceList");
  let items = srcFilter ? allSources.filter((s) => (s.category || "自定义") === srcFilter) : allSources;
  if (!items.length) { list.innerHTML = '<div class="card"><div class="empty">该分类暂无信息源</div></div>'; return; }
  const groups = { "官方": "🏛️ 官方考试平台（公告 / 考纲）", "培训机构": "🎓 培训机构（资源 / 资料）", "自定义": "➕ 自定义" };
  list.innerHTML = Object.entries(groups).map(([g, title]) => {
    const arr = items.filter((s) => (s.category || "自定义") === g);
    if (!arr.length) return "";
    return `<div class="card tight"><h3>${title}</h3>` + arr.map((s) => `
      <div class="kv"><div style="min-width:0"><b>${esc(s.name)}</b>
        <div class="note">${esc(s.desc || "")}${s.note ? " · ⚠️ " + esc(s.note) : ""}</div></div>
        <div class="row nowrap"><span class="tag plain">${esc(s.exam || "")}</span>
          <a class="btn xs" href="${esc(s.url)}" target="_blank" rel="noopener">打开</a>
          ${s.custom ? `<button class="btn xs ghost" onclick="delSource('${esc(s.id)}')">删</button>` : ""}</div></div>`).join("") + "</div>";
  }).join("");
}
window.delSource = async (id) => {
  await api("/api/sources", POST({ action: "delete", id }));
  await api("/api/sources/delete", POST({ id }));
  loadSources();
};
function addSourceSheet() {
  openSheet(`<h3>➕ 添加信息源</h3>
    <label>名称 *</label><input id="nsName" placeholder="如：某省人事考试网">
    <label>网址 *</label><input id="nsUrl" placeholder="https://…">
    <label>分类</label><select id="nsCat"><option>官方</option><option>培训机构</option><option>自定义</option></select>
    <label>适用考试</label><input id="nsExam" placeholder="如：公务员">
    <label>说明</label><input id="nsDesc" placeholder="这个网站提供什么">
    <button class="btn full mt8" onclick="saveSource()">保存</button>`);
}
window.saveSource = async () => {
  const d = await api("/api/sources", POST({
    name: $("nsName").value.trim(), url: $("nsUrl").value.trim(),
    category: $("nsCat").value, exam: $("nsExam").value.trim(), desc: $("nsDesc").value.trim(),
  }));
  if (d.error) { toast(d.error); return; }
  closeSheet(); toast("已添加"); loadSources();
};

/* ---------------- 网盘搜 ---------------- */
let panServices = [];
async function loadPan() {
  const d = await api("/api/pan-search");
  panServices = d.services || [];
  const sel = $("panService");
  sel.innerHTML = panServices.map((s) => `<option value="${esc(s.id)}">${esc(s.name)}</option>`).join("");
  renderPanDetail();
  renderPanFav(d.favorites || []);
}
function renderPanDetail() {
  const s = panServices.find((x) => x.id === $("panService").value);
  if (!s) { $("panSvcDetail").textContent = ""; return; }
  $("panSvcDetail").innerHTML = `${esc(s.desc)}<br>作者：${esc(s.author)} · ${esc(s.license)} ·
    <a href="${esc(s.repo)}" target="_blank" rel="noopener">仓库</a>
    ${s.docker && s.docker.startsWith("docker") ? `<div class="mono mt8" style="background:var(--bg);padding:8px;border-radius:8px;overflow-x:auto">${esc(s.docker)}</div>` : ""}`;
}
function panSearch() {
  const kw = $("panKw").value.trim();
  if (!kw) { toast("请输入关键词"); return; }
  const s = panServices.find((x) => x.id === $("panService").value);
  if (!s) return;
  window.open((s.search || s.home).replace("{kw}", encodeURIComponent(kw)), "_blank");
}
function renderPanFav(favs) {
  $("panFavCount").textContent = favs.length;
  const list = $("panFavList");
  if (!favs.length) { list.innerHTML = '<div class="empty">还没有收藏</div>'; return; }
  list.innerHTML = favs.slice().reverse().map((f) => `
    <div class="kv"><div style="min-width:0"><b>${esc(f.title)}</b>
      ${f.desc ? `<div class="note">${esc(f.desc)}</div>` : ""}</div>
      <div class="row nowrap"><a class="btn xs" href="${esc(f.url)}" target="_blank" rel="noopener">打开</a>
        <button class="btn xs ghost" onclick="delFav('${esc(f.id)}')">删</button></div></div>`).join("");
}
window.delFav = async (id) => {
  await api("/api/pan-search", POST({ action: "delete", id }));
  loadPan();
};

/* ---------------- 设置 ---------------- */
async function loadSettings() {
  const [cfg, prov] = await Promise.all([api("/api/ai/config"), api("/api/ai/providers")]);
  providersCache = prov.providers || [];
  window.__activeId = cfg.active ? cfg.active.id : "";
  const list = $("providerList");
  list.innerHTML = providersCache.map((p) => `
    <div class="item"><div class="row"><b>${esc(p.label)}</b>
      <span class="tag ${p.available ? "ok" : "plain"}">${p.available ? "可用" : "不可用"}</span>
      ${cfg.active && cfg.active.id === p.id ? '<span class="tag">使用中</span>' : ""}
      ${p.anon ? '<span class="tag plain">免登录</span>' : ""}</div>
      <div class="note">${esc(p.desc)}${p.error ? "<br>⚠️ " + esc(p.error) : ""}</div>
      <div class="acts"><button class="btn xs ${cfg.active && cfg.active.id === p.id ? "" : "sec"}"
        onclick="chooseProvider('${p.id}')">${cfg.active && cfg.active.id === p.id ? "正在使用" : "切换到这里"}</button></div></div>`).join("");

  $("llmUrl").value = cfg.base_url || "";
  $("llmModel").value = cfg.model || "";
  if (cfg.has_key) $("llmKey").placeholder = `已设置（${cfg.key_fingerprint}），留空不修改`;

  const bank = await api("/api/bank/stats");
  $("myBankCount").textContent = bank.user;
}
async function saveLlm() {
  const body = { base_url: $("llmUrl").value.trim(), model: $("llmModel").value.trim() };
  if ($("llmKey").value) body.api_key = $("llmKey").value.trim();
  const d = await api("/api/ai/config", POST(body));
  if (d.error) { $("llmResult").innerHTML = `<div class="alert err">${esc(d.error)}</div>`; return; }
  $("llmResult").innerHTML = `<div class="alert ok">✅ 已保存${d.label ? "，当前使用：" + esc(d.label) : ""}</div>`;
  await refreshAiChip(); await loadSettings();
}
async function testLlm() {
  await saveLlm();
  $("llmResult").innerHTML = '<div class="alert info"><span class="spin"></span> 正在连接…</div>';
  const d = await api("/api/ai/test");
  if (d.ok) {
    $("llmResult").innerHTML = `<div class="alert ok">✅ 连接成功，${d.count} 个模型：<div class="row mt8" style="gap:5px">
      ${d.models.slice(0, 20).map((m) => `<span class="tag plain">${esc(m)}</span>`).join("")}</div></div>`;
    if (d.models.length && !$("llmModel").value) $("llmModel").value = d.models[0];
  } else {
    $("llmResult").innerHTML = `<div class="alert err">❌ ${esc(d.error || "连接失败")}</div>`;
  }
}
async function viewMyBank() {
  const d = await api("/api/questions?source=user&count=100");
  const box = $("myBankList");
  if (!d.questions.length) { box.innerHTML = '<div class="note">还没有自己的题目</div>'; return; }
  box.innerHTML = d.questions.map((q) => `
    <div class="kv"><div style="min-width:0"><div class="note" style="font-size:12.5px">${esc(q.question.slice(0, 60))}</div>
      <span class="tag plain">${esc(q.subject || "")}</span></div>
      <button class="btn xs ghost" onclick="delQuestion('${esc(q.id)}')">删除</button></div>`).join("");
}
window.delQuestion = async (id) => {
  const res = await fetch("/api/question/" + encodeURIComponent(id), { method: "DELETE" });
  const d = await res.json();
  if (d.ok) { toast("已删除"); viewMyBank(); } else toast(d.error || "删除失败");
};
async function clearMyBank() {
  if (!confirm("确定清空自己导入的所有题目？错题与统计不受影响。")) return;
  const d = await api("/api/questions?source=user&count=500");
  for (const q of d.questions) {
    await fetch("/api/question/" + encodeURIComponent(q.id), { method: "DELETE" });
  }
  toast("已清空"); loadSettings();
}
function about() {
  openSheet(`<h3>ℹ️ 关于 ExamBoost</h3>
    <p class="note">综合备考学习引擎 v1.0.0 · MIT 开源</p>
    <div class="mt8">
      <div class="kv"><span>形态</span><b>独立软件 + Skill + dsh-go 原生插件</b></div>
      <div class="kv"><span>数据</span><b>全部存本机 data/，不上传</b></div>
      <div class="kv"><span>依赖</span><b>Python 3 标准库，零第三方</b></div>
      <div class="kv"><span>AI</span><b>本机免费模型 → 匿名池自动回落</b></div>
      <div class="kv"><span>题目</span><b>模拟原创题，非真题</b></div>
    </div>
    <div class="alert warn mt8">免费模型池可能记录请求内容，请勿粘贴身份证号等敏感信息。</div>
    <button class="btn full mt8" onclick="closeSheet()">关闭</button>`);
}
async function resetData() {
  if (!confirm("这会删除全部答题记录、错题、复习队列与计划。确认？")) return;
  const d = await api("/api/reset", POST({ confirm: "YES" }));
  if (d.ok) { toast("已清空，可重新开始"); go("home"); } else toast(d.error || "失败");
}

/* ---------------- 绑定 ---------------- */
function bind() {
  document.querySelectorAll(".botnav button").forEach((b) => (b.onclick = () => go(b.dataset.v)));
  document.querySelectorAll("#practiceSubnav button").forEach((b) => (b.onclick = () => go(b.dataset.v)));
  $("btnPick1").onclick = () => drawQuestions(1);
  $("btnPick5").onclick = () => drawQuestions(5);
  $("btnPick10").onclick = () => drawQuestions(10);
  $("btnWeak").onclick = () => drawQuestions(10, { mode: "weak" });
  $("btnMistakeMode").onclick = () => drawQuestions(20, { mode: "mistakes" });
  $("btnPoolRefresh").onclick = async () => { await loadPracticeInit(); toast("统计已刷新"); };
  $("btnExamStart").onclick = startExam;
  $("btnExamOffline").onclick = offlineExamPack;
  $("btnPlanGen").onclick = genPlan;
  $("btnChatSend").onclick = sendChat;
  $("chatInput").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); } });
  // —— v2 新增：画像 / 资料 / 溯源出题 / 资料中枢 ——
  $("btnEditProfile").onclick = startOnboard;
  $("hlFind").onclick = () => go("sources");
  $("hlBank").onclick = openBankSheet;
  $("btnRefreshAdvice").onclick = loadHomeAdvice;
  $("btnMatImport").onclick = importMaterial;
  $("matFile").onchange = onFileSelected;
  $("btnMatGen").onclick = generateFromMaterial;
  $("btnHubSearch").onclick = renderHubSearch;
  $("hubKw").addEventListener("keydown", (e) => { if (e.key === "Enter") renderHubSearch(); });
  $("btnPanFav").onclick = async () => {
    const d = await api("/api/pan-search", POST({ action: "add", title: $("panFavTitle").value.trim(), url: $("panFavUrl").value.trim() }));
    if (d.error) { toast(d.error); return; }
    $("panFavTitle").value = ""; $("panFavUrl").value = ""; toast("已收藏"); loadHubFavs();
  };
  $("btnRescan").onclick = async () => { await refreshAi(); await loadSettings(); toast("扫描完成"); };
  $("btnLlmSave").onclick = saveLlm;
  $("btnLlmTest").onclick = testLlm;
  $("btnMyBankView").onclick = viewMyBank;
  $("btnMyBankClear").onclick = clearMyBank;
  $("btnAbout").onclick = about;
  $("btnReset").onclick = resetData;
  document.querySelectorAll("#mkFilter button").forEach((b) => (b.onclick = () => {
    mistakeFilter = b.dataset.f;
    document.querySelectorAll("#mkFilter button").forEach((x) => x.className = "btn xs sec");
    b.className = "btn xs";
    loadMistakes();
  }));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeSheet();
    if (/^[1-6]$/.test(e.key) && currentView === "practice" && !e.target.matches("input,textarea,select")) {
      const q = quiz.list[quiz.idx];
      if (q && !quiz.answered[q.id]) {
        const i = +e.key - 1;
        if (i < (q.options || []).length) {
          const L = /^[A-F][..、)）]/.test(q.options[i].trim()) ? q.options[i].trim()[0].toUpperCase() : String.fromCharCode(65 + i);
          answer(L);
        }
      }
    }
    if ((e.key === "ArrowLeft" || e.key === "ArrowRight") && currentView === "practice") {
      const btn = e.key === "ArrowLeft" ? $("qPrev") : $("qNext");
      if (btn && !btn.disabled) btn.click();
    }
  });
}

/* ---------------- 启动 ---------------- */
function viewFromHash() {
  const h = String(location.hash || "").replace(/^#\/?/, "").trim();
  return VIEWS[h] ? h : null;
}

(async function boot() {
  bind();
  bindOnboard();
  renderTabs();
  // 先加载画像，决定是否弹引导
  obProfileData = await api("/api/profile");
  const prof = obProfileData.profile || {};
  if (!prof.onboarded) {
    startOnboard();   // 首启：先问身份，不上来刷题
    return;
  }
  // 入口优先级：地址栏 hash（PWA 快捷方式）> 上次停留页 > 首页
  let start = viewFromHash();
  if (!start) { try { start = localStorage.getItem("eb_view"); } catch (e) { } }
  if (start && VIEWS[start] && start !== "home") go(start); else loadHome();
  window.addEventListener("hashchange", () => {
    const v = viewFromHash();
    if (v && v !== currentView) go(v);
  });
  const s = await api("/api/status");
  if (s.version) $("topSub").textContent = `综合备考引擎 v${s.version} · ${s.total_questions || 0} 题`;
  await refreshAiChip();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => { });
})();
