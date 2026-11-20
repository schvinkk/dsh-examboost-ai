// ExamBoost —— dsh-go 原生插件
// 直接读 ExamBoost 的学习数据文件，在 App 原生界面里呈现进度、错题与复习到期，
// 并能抽题、讲题、把做错的题记回错题本。数据与独立软件版共用同一份，不另存副本。
import { existsSync, readFileSync, writeFileSync, renameSync, mkdirSync } from 'node:fs'
import { homedir } from 'node:os'
import { join, dirname } from 'node:path'

export const name = 'local-examboost'

// ExamBoost 数据目录候选：部署位置各不相同，逐个探测，取第一个存在的
const DATA_CANDIDATES = [
  process.env.EXAMBOOST_DATA,
  join(homedir(), 'ExamBoost', 'data'),
  join(homedir(), '.examboost', 'data'),
  join(homedir(), 'dsh-examboost-ai', 'app', 'data'),
  '/sdcard/AI空间/ExamBoost-AI/app/data',
  '/storage/emulated/0/AI空间/ExamBoost-AI/app/data',
  join(process.cwd(), 'data'),
  join(process.cwd(), 'app', 'data'),
].filter(Boolean)

const REASONS = ['概念不清', '公式记错', '审题失误', '计算粗心', '方法选错', '时间不够', '蒙错', '未分类']

export function apply(ctx) {
  ctx.inject(['dshGo'], (ctx) => {
    let dataDir = null
    const zh = (locale) => !String(locale || '').startsWith('en')

    // ---------- 数据读写 ----------
    function findDataDir() {
      if (dataDir && existsSync(dataDir)) return dataDir
      for (const p of DATA_CANDIDATES) {
        if (existsSync(p) && (existsSync(join(p, 'stats.json')) || existsSync(join(p, 'mistakes.json')))) {
          dataDir = p
          return p
        }
      }
      return null
    }

    function readJson(name, fallback) {
      const dir = findDataDir()
      if (!dir) return fallback
      try {
        const raw = readFileSync(join(dir, name), 'utf-8')
        return raw.trim() ? JSON.parse(raw) : fallback
      } catch {
        return fallback
      }
    }

    function writeJson(name, value) {
      const dir = findDataDir()
      if (!dir) return false
      try {
        const tmp = join(dir, `${name}.plugin-tmp`)
        writeFileSync(tmp, JSON.stringify(value, null, 2), 'utf-8')
        renameSync(tmp, join(dir, name))
        return true
      } catch {
        return false
      }
    }

    function snapshot() {
      const stats = readJson('stats.json', { total: 0, correct: 0, by_subject: {}, by_day: {} })
      const mistakes = readJson('mistakes.json', [])
      const cards = readJson('cards.json', [])
      const knowledge = readJson('knowledge.json', {})
      const profile = readJson('profile.json', {})
      const materials = readJson('materials.json', [])
      const today = new Date().toISOString().slice(0, 10)
      const due = cards.filter((c) => (c.due || today) <= today)
      const pending = mistakes.filter((m) => m.status !== '已消灭')
      const total = stats.total || 0
      const acc = total ? Math.round(((stats.correct || 0) / total) * 100) : 0
      const weak = Object.entries(knowledge)
        .filter(([, v]) => v && typeof v.prob === 'number' && v.prob < 0.6)
        .sort((a, b) => a[1].prob - b[1].prob)
      return { today, total, correct: stats.correct || 0, acc, mistakes, pending, cards, due, knowledge, weak, byDay: stats.by_day || {}, dir: findDataDir(), profile, materials }
    }

    // ---------- 抽题 ----------
    function pickQuestion(subjectHint) {
      const dir = findDataDir()
      if (!dir) return null
      const banks = []
      for (const f of ['kaogong.json', 'other.json']) {
        try {
          const p = join(dirname(dir), 'data_bank', f)
          if (existsSync(p)) banks.push(...JSON.parse(readFileSync(p, 'utf-8')))
        } catch { /* 忽略单个文件问题 */ }
      }
      const custom = readJson('questions_custom.json', [])
      const ai = readJson('questions_ai.json', [])
      const all = [...banks, ...custom, ...ai]
      if (!all.length) return null
      let pool = all
      const hint = String(subjectHint || '').trim()
      if (hint) {
        const hit = all.filter((q) => (q.subject || '').includes(hint) || (q.knowledge || '').includes(hint) || (q.stage || '').includes(hint))
        if (hit.length) pool = hit
      }
      const s = snapshot()
      const wrongIds = new Set(s.pending.map((m) => m.qid))
      const preferWrong = pool.filter((q) => wrongIds.has(q.id))
      const chosen = (preferWrong.length ? preferWrong : pool)[Math.floor(Math.random() * (preferWrong.length ? preferWrong.length : pool.length))]
      return chosen
    }

    function formatQuestion(q, isZh) {
      const opts = (q.options || []).map((o, i) => `  ${String.fromCharCode(65 + i)}. ${String(o).replace(/^\s*[A-F]\s*[..、)）]\s*/, '')}`).join('\n')
      // 三级溯源标签：让用户知道这题的依据来自哪里
      const PV = { material: ['🟢', isZh ? '来自你的资料' : 'from your material'], ai: ['🟡', isZh ? 'AI补充' : 'AI added'], generated: ['⚠️', isZh ? 'AI生成·请核对' : 'AI made up · verify'] }
      const pv = PV[q.provenance]
      const provenanceLine = pv
        ? `\n${pv[0]} ${pv[1]}${q.source_para ? ' ' + q.source_para : ''}\n`
        : ''
      return [
        isZh ? `请出这道题让我练习，等我作答后再判分并讲解（${q.subject || q.stage || '综合'} · ${q.knowledge || '知识点'}）：`
             : `Have me practise this question; grade and explain only after I answer (${q.subject || q.stage} · ${q.knowledge}):`,
        provenanceLine,
        '', q.question, opts, '',
        isZh ? `（标准答案：${q.answer || '—'}，题目 ID：${q.id || '—'}）` : `(answer: ${q.answer || '—'}, id: ${q.id || '—'})`,
      ].join('\n')
    }

    // ---------- 错题入库 ----------
    function addMistake(item) {
      const list = readJson('mistakes.json', [])
      list.push({
        id: `m_${Date.now()}`,
        qid: item.qid || '',
        stage: item.stage || '',
        subject: item.subject || '',
        knowledge: item.knowledge || '',
        question: item.question || '',
        options: item.options || [],
        answer: item.answer || '',
        correct_answer: item.correct_answer || '',
        explanation: item.explanation || '',
        reason: item.reason || '未分类',
        status: '待复习',
        count: 1,
        created: new Date().toISOString(),
      })
      return writeJson('mistakes.json', list)
    }

    function enqueueCard(item) {
      // 手动记的错题没有 qid，改用题干指纹去重；卡片本身按 id 被服务端调度，不依赖 qid
      const stem = String(item.question || '').replace(/\s+/g, '')
      if (!stem) return false
      const key = item.qid || ('h_' + stem.length + '_' + [...stem].reduce((a, c) => ((a << 5) - a + c.charCodeAt(0)) | 0, 0))
      const cards = readJson('cards.json', [])
      if (cards.some((c) => (c.qid || c.key) === key)) return false
      const today = new Date().toISOString().slice(0, 10)
      cards.push({
        id: `c_${Date.now()}`, key, qid: item.qid || '', subject: item.subject || '',
        knowledge: item.knowledge || '', question: item.question || '',
        answer: item.correct_answer || '', explanation: item.explanation || '',
        provenance: item.provenance || '', source_material: item.source_material || '',
        reps: 0, lapses: 0, due: today, created: new Date().toISOString(),
      })
      return writeJson('cards.json', cards)
    }

    // ---------- 胶囊：抽一题 ----------
    ctx.dshGo.on('eb-ask', (scope, event) => {
      const isZh = zh(event.locale)
      if (!findDataDir()) {
        return { toast: isZh ? '还没找到 ExamBoost 数据，先部署独立软件' : 'No ExamBoost data yet — deploy the app first' }
      }
      const q = pickQuestion((scope.draft || '').slice(0, 12))
      if (!q) return { toast: isZh ? '题库是空的，先导入题目' : 'Question bank is empty' }
      return { insert: formatQuestion(q, isZh).slice(0, 2000) }
    })

    // ---------- 胶囊：讲这题 ----------
    ctx.dshGo.on('eb-explain', (scope, event) => {
      const isZh = zh(event.locale)
      const text = String(scope.draft || '').trim()
      if (!text) return { toast: isZh ? '输入框里没有题目内容' : 'Nothing in the input box' }
      return {
        insert: (isZh
          ? `请讲解下面这道题：先点出考查的知识点，再给解题步骤，最后提醒易错点，不要只给答案。\n\n${text}`
          : `Explain this question: name the concept, walk through the steps, then flag the common trap.\n\n${text}`).slice(0, 2000),
      }
    })

    // ---------- 菜单项：记入错题本 ----------
    ctx.dshGo.on('eb-log', (scope, event) => {
      const isZh = zh(event.locale)
      const body = String(scope.message || '').trim()
      if (!body) return { toast: isZh ? '这条回复没有内容' : 'This message is empty' }
      if (!findDataDir()) return { toast: isZh ? '还没找到 ExamBoost 数据目录' : 'No ExamBoost data dir found' }

      // AI 回复格式五花八门，先剥掉 markdown 标记再解析，否则标签会被 ** 打断
      const clean = body
        .replace(/\*\*([^*]+)\*\*/g, '$1')
        .replace(/^#+\s*/gm, '')
        .replace(/`{1,3}([^`]*)`{1,3}/g, '$1')
        .replace(/^\s*[-*]\s+/gm, '')
        .replace(/[ \t]+/g, ' ')
      // 题干要止于「答案/解析」，否则会把整段说明当成题干
      const STOP = String.raw`(?=\n?\s*(?:标准答案|正确答案|参考答案|参考解答|答案|解析|解答|Explanation|Answer\s*:)|$)`
      const qMatch = new RegExp(String.raw`(?:题目|题干|问题|Question)\s*[:：]?\s*([\s\S]{4,400}?)` + STOP, 'i').exec(clean)
      const aMatch = /(?:标准答案|正确答案|参考答案|答案|Answer)\s*[:：是为]?\s*([A-F])\b(?![.、)）])/i.exec(clean)
        || /(?:所以选|应选|应选择|正确选项是?)\s*([A-F])\b/i.exec(clean)
      const eMatch = /(?:解析|解答|说明|Explanation)\s*[:：]?\s*([\s\S]{4,900})/i.exec(clean)
      // 知识点标签要收紧：「考查的是X」里的「考查」会误抓，只认带冒号或「知识点/专题」
      const kMatch = /(?:知识点|专题|考点|Knowledge)\s*[:：]\s*([^\n，,。；;]{2,40})/i.exec(clean)
      const question = (qMatch ? qMatch[1] : clean.split('\n')[0]).trim().slice(0, 400)
      const item = {
        question,
        subject: '',
        knowledge: kMatch ? kMatch[1].trim() : '',
        correct_answer: aMatch ? aMatch[1].toUpperCase() : '',
        answer: '',
        explanation: (eMatch ? eMatch[1] : clean).trim().slice(0, 1200),
        reason: REASONS[0],
      }
      const ok = addMistake(item)
      if (ok && item.correct_answer) enqueueCard(item)
      if (!ok) return { toast: isZh ? '写入失败，检查数据目录权限' : 'Write failed — check folder permissions' }
      return { toast: isZh ? '已记入错题本，去网页版可重做' : 'Saved to mistakes' }
    })

    // ---------- 状态条 ----------
    ctx.dshGo.strip('eb-strip', (scope, emit, caps) => {
      const isZh = zh(caps.locale)
      const tick = () => {
        const s = snapshot()
        if (!s.dir) { emit({ text: isZh ? 'ExamBoost 未部署' : 'ExamBoost not deployed', tone: 'muted' }); return }
        emit({
          text: isZh
            ? `今日复习 ${s.due.length} · 错题 ${s.pending.length} · 正确率 ${s.acc}%`
            : `Due ${s.due.length} · Wrong ${s.pending.length} · ${s.acc}%`,
          tone: s.due.length > 0 ? 'warn' : 'ok',
        })
      }
      tick()
      const timer = setInterval(tick, 30_000)
      return () => clearInterval(timer)
    })

    // ---------- 面板：学习看板 ----------
    ctx.dshGo.panel('eb-dash', {
      view: (scope, caps) => {
        const isZh = zh(caps.locale)
        const s = snapshot()
        if (!s.dir) {
          return {
            type: 'stack',
            title: isZh ? 'ExamBoost 学习看板' : 'ExamBoost Dashboard',
            children: [
              { type: 'callout', text: isZh ? '还没有找到学习数据。先在电脑上或本机部署 ExamBoost 独立软件（仓库里的 app/deploy.sh），部署完这里就会自动显示。' : 'No study data found yet. Deploy the ExamBoost app first (app/deploy.sh), then this panel fills itself in.', tone: 'warn' },
            ],
          }
        }
        const days = Object.keys(s.byDay).sort().slice(-7)
        const STAGE_LABEL = { primary:'小学生', middle:'中学生', high:'高中生', college:'大学生', kaoyan:'考研', kaogong:'考公考编', cert:'考证', adult:'在职/自学' }
        const children = []
        if (s.profile && s.profile.onboarded) {
          children.push({ type: 'callout', tone: 'info', text: isZh
            ? `你的目标：${STAGE_LABEL[s.profile.stage] || ''} · ${s.profile.goal || ''}${s.profile.major ? ' · ' + s.profile.major : ''}${s.profile.has_material ? ' · 已导入资料 ' + s.materials.length + ' 份' : ' · 还没导入资料'}`
            : `Your goal: ${s.profile.goal || ''}${s.profile.major ? ' · ' + s.profile.major : ''}` })
        } else {
          children.push({ type: 'callout', tone: 'warn', text: isZh
            ? '还没设置你的考试目标。去独立网页版首页花 30 秒设置，出题和找资料才会按你的情况来。'
            : 'Set your exam goal in the web app first.' })
        }
        children.push({ type: 'row', children: [
          { type: 'metric', label: isZh ? '已答题' : 'Answered', value: String(s.total) },
            { type: 'metric', label: isZh ? '正确率' : 'Accuracy', value: `${s.acc}%`, tone: s.acc >= 80 ? 'good' : s.acc >= 60 ? 'warn' : 'bad' },
            { type: 'metric', label: isZh ? '待复习' : 'Due today', value: String(s.due.length), tone: s.due.length ? 'warn' : 'good' },
          ] },
          { type: 'row', children: [
            { type: 'metric', label: isZh ? '错题待消灭' : 'Open mistakes', value: String(s.pending.length), tone: s.pending.length ? 'bad' : 'good' },
            { type: 'metric', label: isZh ? '复习卡' : 'Cards', value: String(s.cards.length) },
            { type: 'metric', label: isZh ? '科目数' : 'Subjects', value: String(Object.keys(s.knowledge).length) },
          ] })
        if (days.length) {
          children.push({
            type: 'chart', kind: 'bar',
            title: isZh ? '近 7 天答题量' : 'Answers, last 7 days',
            categories: days.map((d) => d.slice(5)),
            series: [{ name: isZh ? '题数' : 'count', values: days.map((d) => s.byDay[d]?.total || 0) }],
          })
        }
        if (s.weak.length) {
          children.push({
            type: 'list', title: isZh ? '薄弱科目（优先补）' : 'Weakest subjects',
            items: s.weak.slice(0, 6).map(([name, v]) => ({
              title: name,
              subtitle: isZh ? `掌握度 ${Math.round(v.prob * 100)}%` : `mastery ${Math.round(v.prob * 100)}%`,
              tone: v.prob < 0.4 ? 'bad' : 'warn',
              action: { id: 'drill', args: { subject: name } },
            })),
          })
        } else if (s.total) {
          children.push({ type: 'callout', text: isZh ? '没有明显薄弱科目，可以上强度了：试试限时模考。' : 'No weak spots stand out — time a full mock next.', tone: 'good' })
        }
        children.push({
          type: 'actions', items: [
            { label: isZh ? '抽一题练' : 'Quiz me', action: 'ask', style: 'primary' },
            { label: isZh ? '看错题' : 'Mistakes', action: 'openMistakes' },
            { label: isZh ? '去复习' : 'Review', action: 'openReview' },
            { label: isZh ? '刷新' : 'Refresh', action: 'refresh' },
          ],
        })
        children.push({ type: 'text', text: isZh ? `数据目录：${s.dir}` : `Data folder: ${s.dir}`, tone: 'muted' })
        return { type: 'stack', title: isZh ? 'ExamBoost 学习看板' : 'ExamBoost Dashboard', children }
      },
      data: (scope, emit, caps) => {
        const s = snapshot()
        emit({ total: s.total, acc: s.acc, due: s.due.length, pending: s.pending.length })
        return () => {}
      },
      actions: {
        ask: (scope, event) => {
          const isZh = zh(event.locale)
          const q = pickQuestion('')
          if (!q) return { toast: isZh ? '题库是空的' : 'Question bank empty' }
          return { insert: formatQuestion(q, isZh).slice(0, 2000) }
        },
        drill: (scope, event) => {
          const isZh = zh(event.locale)
          const subject = String(event.value?.subject || '')
          const q = pickQuestion(subject)
          if (!q) return { toast: isZh ? `${subject} 没有题目` : `No questions for ${subject}` }
          return { insert: formatQuestion(q, isZh).slice(0, 2000) }
        },
        openMistakes: (scope, event) => ({ open: 'panel:eb-mistakes' }),
        openReview: (scope, event) => ({ open: 'panel:eb-review' }),
        refresh: () => ({ refresh: true }),
      },
    })

    // ---------- 面板：错题本 ----------
    ctx.dshGo.panel('eb-mistakes', {
      view: (scope, caps) => {
        const isZh = zh(caps.locale)
        const s = snapshot()
        if (!s.dir) return { type: 'stack', title: isZh ? '错题本' : 'Mistakes', children: [{ type: 'callout', text: isZh ? '还没找到 ExamBoost 数据目录' : 'No data folder found', tone: 'warn' }] }
        const items = s.pending.slice(-20).reverse()
        const children = [
          { type: 'text', text: isZh ? `未消灭错题 ${s.pending.length} 道（显示最近 20 道）` : `${s.pending.length} open mistakes (showing latest 20)`, tone: 'muted' },
        ]
        if (!items.length) {
          children.push({ type: 'emptyState', title: isZh ? '没有待消灭的错题' : 'Nothing to clear' })
        } else {
          children.push({
            type: 'list',
            items: items.map((m) => ({
              title: String(m.question || '').slice(0, 46),
              subtitle: isZh
                ? `${m.subject || m.stage || '综合'} · ${m.knowledge || '知识点'} · 错 ${m.count || 1} 次`
                : `${m.subject || m.stage || 'mixed'} · ${m.knowledge || 'concept'} · ×${m.count || 1}`,
              trailing: m.correct_answer ? isZh ? `答 ${m.correct_answer}` : `ans ${m.correct_answer}` : '',
              tone: 'bad',
              action: { id: 'redrill', args: { qid: m.qid || '', question: String(m.question || '').slice(0, 300) } },
            })),
          })
        }
        children.push({
          type: 'actions', items: [
            { label: isZh ? '重刷错题' : 'Redrill', action: 'redrillAny', style: 'primary' },
            { label: isZh ? '回看板' : 'Dashboard', action: 'back' },
          ],
        })
        return { type: 'stack', title: isZh ? '错题本' : 'Mistakes', children }
      },
      actions: {
        redrill: (scope, event) => {
          const isZh = zh(event.locale)
          const q = event.value?.qid ? findQuestion(event.value.qid) : null
          const text = q ? formatQuestion(q, isZh)
                         : (isZh ? `这道题我错了，请换个说法再考我一遍，并讲清方法：\n\n${event.value?.question || ''}`
                                  : `I got this wrong. Re-test me in a different wording and explain the method:\n\n${event.value?.question || ''}`)
          return { insert: text.slice(0, 2000) }
        },
        redrillAny: (scope, event) => {
          const isZh = zh(event.locale)
          const s = snapshot()
          if (!s.pending.length) return { toast: isZh ? '没有待消灭的错题' : 'Nothing open' }
          const m = s.pending[Math.floor(Math.random() * s.pending.length)]
          const q = m.qid ? findQuestion(m.qid) : null
          const text = q ? formatQuestion(q, isZh)
                         : (isZh ? `请让我重做这道错题，判分后讲方法：\n\n${m.question}\n（正确答案：${m.correct_answer || '—'}）`
                                  : `Have me redo this mistake, then grade and explain:\n\n${m.question}\n(answer: ${m.correct_answer || '—'})`)
          return { insert: text.slice(0, 2000) }
        },
        back: () => ({ open: 'panel:eb-dash' }),
      },
    })

    // ---------- 面板：今日复习 ----------
    ctx.dshGo.panel('eb-review', {
      view: (scope, caps) => {
        const isZh = zh(caps.locale)
        const s = snapshot()
        if (!s.dir) return { type: 'stack', title: isZh ? '今日复习' : 'Today\'s Review', children: [{ type: 'callout', text: isZh ? '还没找到 ExamBoost 数据目录' : 'No data folder found', tone: 'warn' }] }
        const children = []
        if (!s.cards.length) {
          children.push({ type: 'emptyState', title: isZh ? '复习队列是空的' : 'Queue is empty' })
          children.push({ type: 'text', text: isZh ? '答错的题会自动进入这里，按记忆曲线到期提醒。' : 'Missed questions land here automatically, scheduled by the forgetting curve.', tone: 'muted' })
        } else if (!s.due.length) {
          children.push({ type: 'callout', text: isZh ? `今日复习已完成，队列里还有 ${s.cards.length} 张卡` : `All done today — ${s.cards.length} cards still scheduled`, tone: 'good' })
        } else {
          children.push({ type: 'progress', value: s.due.length, max: s.cards.length, label: isZh ? `今日到期 ${s.due.length} / ${s.cards.length}` : `${s.due.length} of ${s.cards.length} due` })
          children.push({
            type: 'list',
            items: s.due.slice(0, 20).map((c) => ({
              title: String(c.question || '').slice(0, 46),
              subtitle: isZh ? `${c.subject || '综合'} · 已复习 ${c.repetitions || 0} 次` : `${c.subject || 'mixed'} · reviewed ×${c.repetitions || 0}`,
              trailing: c.answer || '',
              action: { id: 'show', args: { qid: c.qid || '' } },
            })),
          })
          children.push({
            type: 'actions', items: [
              { label: isZh ? '开始复习' : 'Start', action: 'next', style: 'primary' },
              { label: isZh ? '回看板' : 'Dashboard', action: 'back' },
            ],
          })
        }
        return { type: 'stack', title: isZh ? '今日复习' : 'Today Review', children }
      },
      actions: {
        next: (scope, event) => {
          const isZh = zh(event.locale)
          const s = snapshot()
          if (!s.due.length) return { toast: isZh ? '今日没有到期卡片' : 'Nothing due today' }
          const c = s.due[0]
          const q = c.qid ? findQuestion(c.qid) : null
          const text = isZh
            ? `带我复习这道到期卡片，先只给题干等我答，再判分并按 FSRS-5 调整下次间隔（忘记/吃力/良好/轻松四档）：\n\n${c.question}\n（知识点：${c.knowledge || '—'}，答案：${q ? q.answer : c.answer || '—'}，卡片 ID：${c.id}）`
            : `Review this due card with me: show the stem first, grade after I answer, then reschedule with FSRS-5 (again/hard/good/easy).\n\n${c.question}\n(concept: ${c.knowledge || '—'}, answer: ${q ? q.answer : c.answer || '—'}, card: ${c.id})`
          return { insert: text.slice(0, 2000) }
        },
        show: (scope, event) => {
          const isZh = zh(event.locale)
          const q = event.value?.qid ? findQuestion(event.value.qid) : null
          if (!q) return { toast: isZh ? '原题已不在题库，可用「开始复习」' : 'Original not in bank — use Start' }
          return { insert: formatQuestion(q, isZh).slice(0, 2000) }
        },
        back: () => ({ open: 'panel:eb-dash' }),
      },
    })

    // 在面板视图之外复用的题目查找
    function findQuestion(qid) {
      const dir = findDataDir()
      if (!dir || !qid) return null
      const pools = []
      for (const f of ['kaogong.json', 'other.json']) {
        try {
          const p = join(dirname(dir), 'data_bank', f)
          if (existsSync(p)) pools.push(...JSON.parse(readFileSync(p, 'utf-8')))
        } catch { /* 忽略 */ }
      }
      pools.push(...readJson('questions_custom.json', []), ...readJson('questions_ai.json', []))
      return pools.find((q) => q && q.id === qid) || null
    }
  })
}
