# 通用学习模块（General Study）

功能设计参考并致谢：
- StudyHub（EricWang1358，MIT）- 资料变题目、间隔复习
- dsh-plugin-lookatstudy（Kaiji-Z，MIT）- 引导式课程、BKT、SM-2
- dsh-bili-learn（jin-ni，MIT）- 多格式资料处理
- dsh-learning-hub（ZBC-QRLA，MIT）- 本地学习中枢
- study-coach（geyadawang-boop，MIT）- 资料分层、七段讲题、FSRS
- RetainCraft（kaixiad，MIT）- 循证学习科学

## 资料解析
- 支持格式：PDF、Word、PPT、Markdown、TXT、图片、代码
- PDF 用 pypdf 抽取文字；Office 用 python-docx/pptx
- 扫描件需 OCR（提示用户）

## 知识点抽取
- 模型将资料整理为结构化知识点
- 每个知识点带来源页码/出处

## 间隔复习
- SM-2 算法（借鉴 dsh-plugin-lookatstudy）
- FSRS 算法（借鉴 StudyBros / study-coach）
- 复习计划：1/3/7/14 天

## 掌握度追踪
- BKT 模型（借鉴 dsh-plugin-lookatstudy）
- 课程掌握度取最弱概念
- 薄弱点标记（⚡😣）
