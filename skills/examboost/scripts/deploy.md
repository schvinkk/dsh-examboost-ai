# ExamBoost 独立软件部署说明

用户说「部署 ExamBoost 到本地 / 装成软件 / 我想在手机上看」时，按下面顺序做。目标是**一次做完、能打开、说清地址**，不要中途让用户去装别的东西。

## Step 1 找到项目目录

按顺序找，找到就用，别猜：

```bash
for d in . .. ~/ExamBoost ~/dsh-examboost-ai ~/AI空间/ExamBoost-AI; do
  [ -f "$d/app/server.py" ] && echo "FOUND: $d/app" && break
done
```

都没有就 clone：

```bash
git clone https://github.com/schvinkk/dsh-examboost-ai.git
```

## Step 2 检查 Python

```bash
python3 --version    # 需要 3.8+
```

后端只用标准库，**不需要 pip install 任何东西**。缺 Python 就告诉用户装法（Debian/Ubuntu `sudo apt-get install -y python3`，macOS `brew install python3`），不要自己去装系统包。

## Step 3 部署并启动

```bash
cd <项目目录>/app
bash deploy.sh
```

脚本自己做：检查环境 → 复制到 `~/ExamBoost` → 端口占用时自动换邻近端口 → `setsid` 后台常驻 → 尝试开浏览器 → 打印访问地址，并写 `server.pid`。

想换端口或把数据放到别处：

```bash
bash deploy.sh --port 8080 --data-dir ~/my-study
```

## Step 4 验证真的能用（别跳过）

```bash
PORT=$(grep -oE 'http://localhost:[0-9]+' ~/ExamBoost/server.log | head -1 | grep -oE '[0-9]+$')
curl -s "http://127.0.0.1:$PORT/api/health"      # 期望 {"ok":true,...}
curl -s "http://127.0.0.1:$PORT/api/status"      # 期望 total_questions > 300
curl -s "http://127.0.0.1:$PORT/api/ai/providers" # 看 ready 是不是 true
```

`ai/providers` 里 `ready:false` 时，把每路的 `error` 念给用户（通常是没网），并告诉他可以在「设置 → 模型接入」填自己的服务地址。不要谎称 AI 功能正常。

## Step 5 告诉用户这三件事

1. **本机地址**：`http://localhost:<实际端口>`（端口可能被自动改过，以日志为准）
2. **手机地址**：日志里打印的 `http://<局域网IP>:<端口>`，前提是手机连同一 WiFi
3. **怎么停**：`kill $(cat ~/ExamBoost/server.pid)`；重启就再跑一次 `deploy.sh`

建议用户第一轮这样点：刷题页抽一题故意答错 → 看错题本和复习页有没有多出条目 → 生成页粘一段资料点「AI 出题」→ 下载离线包双击打开。这四步走完，功能是否正常一目了然。

## 注意

- 数据全在 `app/data/`（或 `--data-dir` 指定处），不上传；`llm_config.json` 权限 0600
- 匿名免费模型通道会经过第三方网关，通常记录 prompt。提醒用户别把身份证号、账号密码粘进去
- 内置题库在 `app/data_bank/`，只读，升级不覆盖用户数据
- 手机锁屏时开不了浏览器，先让用户解锁
