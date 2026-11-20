# ExamBoost 独立软件部署说明

当 AI 收到用户「部署 ExamBoost 到本地」的指令时，按以下步骤执行：

## Step 1: 检查环境
```bash
python3 --version
```
未安装 Python 3.8+ 时，提示用户安装。

## Step 2: 定位部署脚本
找到本 Skill 所在目录的 `app/deploy.sh`（在项目源码中）或执行：
```bash
ls ~/dsh-examboost-ai/app/deploy.sh
```

## Step 3: 执行部署
```bash
bash ~/dsh-examboost-ai/app/deploy.sh
```

## Step 4: 确认结果
- 检查 `http://localhost:3000` 是否可访问
- 读取 `~/ExamBoost/server.log` 确认服务启动
- 告知用户本机访问地址和手机/平板访问地址（同一 WiFi 下 `http://电脑IP:3000`）

## 说明
- 数据保存到 `~/ExamBoost/data/`，不上传
- 端口默认 3000，冲突时修改 `app/deploy.sh` 中 PORT
- 手机/平板：同一 WiFi 下用 `http://电脑IP:3000` 访问，或添加到主屏（PWA）
