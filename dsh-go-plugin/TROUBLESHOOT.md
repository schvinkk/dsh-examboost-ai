# 插件装上了却"用不了"？查这两处

## 1. 数据目录被陈旧副本抢占

插件按 `DATA_CANDIDATES` 顺序探测数据目录，取**第一个**存在
`stats.json` 或 `mistakes.json` 的目录。

如果你以前在别的路径装过 ExamBoost（比如 `~/ExamBoost`），那份老数据
会排在真实路径前面被选中 —— 看板就永远显示老的数字。

**排查：**

```bash
node -e "
const {existsSync}=require('fs');const {join}=require('path');const {homedir}=require('os');
const C=[process.env.EXAMBOOST_DATA, '/sdcard/AI空间/ExamBoost-AI/app/data',
  join(homedir(),'ExamBoost','data'), join(process.cwd(),'data')].filter(Boolean);
for(const p of C) console.log((existsSync(join(p,'stats.json'))?'✅':'  '), p);
"
```

**修：** 删掉陈旧目录，或设环境变量 `EXAMBOOST_DATA=/你的/真实/data` 覆盖。

## 2. 重装失败把插件从 bundles 里挤掉

`dsh plugin add` 底层走 pnpm。若 pnpm 因 `ERR_PNPM_IGNORED_BUILDS` 之类
原因退出码非 0，它可能已经把 profile 的 `package.json` 重写过一遍，
此时 `dsh.profile.bundles` 里的插件名会**消失** —— 插件在 node_modules 里
有软链、检查器也能通过，但引擎启动时根本不会加载它。

**排查：** 看引擎启动日志有没有你的插件输出；或者：

```bash
python3 -c "
import json;d=json.load(open('/root/.dsh/profiles/web/package.json'))
b=d['dsh']['profile']['bundles']
print('在 bundles 里:', 'local-examboost' in b, '| 总数:', len(b))
"
```

**修：** 手动挂回去：

```bash
python3 - <<'PY'
import json
p='/root/.dsh/profiles/web/package.json'
d=json.load(open(p,encoding='utf8'))
b=d['dsh']['profile']['bundles']
if 'local-examboost' not in b:
    b.append('local-examboost')
    json.dump(d,open(p,'w',encoding='utf8'),ensure_ascii=False,indent=2)
    print('已挂回 bundles')
PY
```

改完 **必须重启引擎**（App → 引擎 → 重启），插件代码才进内存。

## 检查器通过 ≠ 能用

`check.mjs --load` 只验清单合法性和视图能不能渲染，它**验不了**
运行时读到的是哪份数据、插件有没有被加载。真要确认能用，得像上面
那样直接跑数据探测和 bundles 检查。
