# Executive Growth OS

Executive Growth OS 是一个本地优先、由 AI 驱动的个人高管能力成长操作系统。

它不是普通知识库，也不是简单的职业记录工具。它的核心目标是：

> “这个系统不是记录成长，而是通过标准、学习、实践、反馈、考核和再学习的循环主动制造成长。”

> “This system does not merely record growth. It creates a continuous feedback loop between standards, learning, real work, AI assessment, and deliberate practice.”

系统围绕六项能力长期运行：`Business`、`Finance`、`Strategy`、`Execution`、`Leadership`、`Influence`。

AI 有两个主要角色：

- `Teacher`：提问、教学、纠错、案例训练、评估知识理解和安排复习。
- `Executive Interviewer`：严格追问用户本人的判断、行动、取舍、数字和结果，寻找 Executive-Level Gap。

## 第一次使用

### 安装项目

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

项目要求 Python 3.13 或更高版本。

### 配置 DeepSeek

将 `.env.example` 复制为 `.env`，填写：

```dotenv
DEEPSEEK_API_KEY=你的_API_KEY
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

只有调用 AI 的命令需要 API Key。`status`、`topics`、`study path` 等本地浏览命令不调用 DeepSeek。

### 第一次查看系统

```powershell
python -m growthos status
python -m growthos topics
python -m growthos topics finance
```

不知道今天学什么：

```powershell
python -m growthos study next
```

知道具体目标：

```powershell
python -m growthos study finance working_capital
```

## 我每天应该怎么用

推荐的日常循环如下，但不要求每天把所有命令都运行一遍。

### A. 学习一项知识，约 15–30 分钟

优先运行：

```powershell
python -m growthos study next
```

如果已经知道目标：

```powershell
python -m growthos study finance ROI
```

### B. 检查旧知识是否遗忘

```powershell
python -m growthos quiz
```

`study next` 回答“下一步最值得学习或继续深入什么”；`quiz` 回答“以前学过的东西现在还会不会”。到期复习由 `quiz` 负责，不和新知识推荐混在一起。

### C. 工作结束后记录重要实践

```powershell
python -m growthos daily
```

`python -m growthos reflect` 是同一流程的别名。

Daily 不是流水账。优先记录：重要判断、复杂问题、协作与冲突、Trade-off、数字、最终结果、不理解的内容和失败的尝试。“失败”和“没搞懂”是高价值输入，因为它们能帮助系统发现 Knowledge Gap 和下一步 Practice Suggestion。

## Knowledge Engine 是什么

Knowledge Engine 管理“我知道什么，以及我是否真的会用”。

```text
Knowledge Map
→ 选择知识
→ Active Recall
→ Application Question
→ AI 评估与教学反馈
→ 更新 Knowledge Progress
→ 安排 Spaced Repetition
→ 未来由 Quiz 再次检查
```

当前 Study 会先生成一个 Recall Question 和一个 Application Question，收集两个回答后，再由 Teacher 给出教学反馈、判断理由以及两个 0–3 分数。它不是“看完文章 → 标记完成”，而是“先回答 → 暴露盲区 → 教学反馈 → 应用判断 → 未来再测试”。

## 为什么不能只背概念

以 ROI 为例：

1. “ROI 是什么？”只能测试是否记住定义。
2. “投入 100 万元，产生 20 万元收益，如何理解 ROI？”开始检查计算与解释。
3. “A 项目 ROI 更高但三年后回款；B 项目 ROI 略低但很快产生现金。公司现金紧张时如何选择？”才开始检查真实经营判断。

能复述定义不等于会做决策。Knowledge Engine 同时关注 `Conceptual Understanding` 和 `Application Ability`。

## Knowledge Map 与 topics

```powershell
python -m growthos topics
```

显示六项能力及知识点数量。当前课程共 138 个概念：Business 25、Finance 34、Strategy 21、Execution 20、Leadership 18、Influence 20。

```powershell
python -m growthos topics finance
```

显示 Finance 的分类知识地图、中文显示名、学习状态和已记录的下次复习日期，但不会进入教学。

Knowledge Map 用于解决 `unknown unknowns`：当你还不知道“自己不知道什么”时，先看到这项能力包含哪些知识，以及当前处于什么位置。

## study 命令

交互选择能力：

```powershell
python -m growthos study
```

浏览某项能力的知识地图，并按编号进入学习：

```powershell
python -m growthos study finance
```

直接学习指定概念：

```powershell
python -m growthos study finance working_capital
```

直接学习时，Teacher 会先提出 Recall 与 Application 问题，再根据两个回答给出教学反馈、评分、掌握判断和下次复习日期。Session 保存在 `logs/study/`。

## study next 如何选择下一项知识

```powershell
python -m growthos study next
```

这个命令回答：“我不知道今天应该学什么，请系统推荐。”选课使用本地规则，不调用 DeepSeek。

当前排序和过滤规则是：

```text
current_focus 中的 Capability
→ 最近 30 天 Daily / Practice Knowledge Gap
→ prerequisites 必须满足
→ 只考虑 unknown / learning / understood
→ 排除 applied / verified / needs_review
→ 排除 next_review_at 已到期内容
→ curriculum order
```

1. **Current Focus**：优先选择 `state/current_focus.md` 中明确出现的能力；多项能力按其在文件中出现的位置排序。
2. **Knowledge Gap**：读取最近 30 天 `logs/daily/` 中的 `## Knowledge Gaps` 和 `state/practice_state.json`。被明确提到的概念可以越过同一 Focus 内普通课程顺序。
3. **Prerequisites**：前置概念必须达到 `understood`、`applied` 或 `verified`。Finance 已为 Working Capital、ROI、ROIC、NPV、IRR 等关键概念设置前置关系。
4. **掌握状态**：只推荐未学习、学习中或已理解但尚未应用的内容。
5. **复习职责分离**：`needs_review` 或 `next_review_at` 已到期的概念应交给 `quiz`。
6. **推荐顺序**：其余条件相同时，根据 Curriculum 分类形成的 `order` 推荐基础概念。

输出会逐条说明 Focus、Knowledge Gap、前置条件、掌握状态和 Curriculum 顺序，然后询问：

```text
开始学习？ [Y/n]
```

## study path

```powershell
python -m growthos study path finance
```

它回答“Finance 从基础到进阶大概应该按什么顺序学”。当前实现以分类 Knowledge Map 展示推荐顺序和真实状态。顺序不是强制锁定；真实工作暴露出明确 Knowledge Gap 且 prerequisites 满足时，相关知识可以提前学习。

## Quiz 与间隔复习

```powershell
python -m growthos quiz
```

Quiz 不是成绩或排名系统，而是对抗遗忘。它优先选择 `next_review_at` 已到期的记录；没有到期记录时进入普通 Study 选取逻辑。Quiz 使用与 Study 相同的 Recall、Application、AI 反馈和评分流程。

`concept_score`：0 不会、1 部分理解、2 基本掌握、3 清晰掌握。

`application_score`：0 无法应用、1 提示后才能应用、2 能处理基础案例、3 能独立处理复杂案例。

当前调度规则：

- `concept_score <= 1`：1 天后；
- `concept_score >= 2` 且 `application_score <= 1`：3 天后；
- `concept_score >= 2` 且 `application_score == 2`：7 天后；
- 两项都是 3：使用 14、30、60、90 天连续成功阶梯。

当前保存流程会先增加 `consecutive_successes` 再计算间隔，因此第一次被记录为“两项都是 3”时，实际安排为 30 天。失败会将连续成功次数重置为 0，再按较短规则安排。这里描述的是当前代码行为。

## Knowledge Progress 状态

状态保存在 `state/knowledge_progress.json`：

- `unknown`：没有进度记录；
- `learning`：正在学习；
- `understood`：理解概念，但未必能稳定应用；
- `applied`：概念与应用均达到基本掌握；
- `verified`：概念与应用评分均为 3；
- `needs_review`：本次结果未达到 applied。

当前自动评分主要写入 `applied`、`verified` 或 `needs_review`；`unknown` 由缺少记录表示，`learning` 和 `understood` 可以由已有或人工维护的状态显示。

真实字段包括：

```text
capability
status
first_learned_at
last_reviewed_at
next_review_at
review_count
consecutive_successes
last_concept_score
last_application_score
```

## Practice Engine

```powershell
python -m growthos daily
```

Practice Engine 关注“我实际做到了什么”。AI 会从自然语言记录中提取 Analysis、Evidence、Knowledge Gaps、Practice Suggestions 和 Responsibility Hint。

例如：

> 销售希望给 Distributor Net 90。我和财务讨论后建议 Net 60，并增加信用控制，销售最后接受。

系统可能识别 Finance / Working Capital / E3、Business / Distributor Economics / E3，以及 Influence / Legal to Business / E3。由于缺少最终经营结果，它可能指出这暂时不是 E4。

原始输入保存在 `logs/daily/YYYY-MM-DD.md` 的 `## Raw Input`。符合结构的 Evidence 分别写入 `evidence/YYYY-MM-DD_<slug>.md`；`state/practice_state.json` 更新 Evidence 数量、最后 Daily 日期和责任等级提示。

## Knowledge 与 Practice 如何连接

```text
真实工作
→ Daily
→ AI 发现 Knowledge Gap
→ study next 提高相关概念优先级
→ Teacher 提问与教学
→ Application Question
→ 回到真实工作中应用
→ 产生更高质量的 Practice Evidence
```

例如 Daily 出现 Distributor Net 90，AI 将其识别为 Working Capital 知识盲区。只要前置知识满足，`study next` 就能提高相关概念优先级。学习后再次面对账期决策时，用户应能更好地分析 Accounts Receivable、现金占用和 Cash Conversion Cycle。

系统的价值不是完成 138 个 Concept，而是让真实工作不断告诉系统“接下来应该学什么”，再让学习提高真实工作的判断质量。

## 长期记忆如何工作

DeepSeek API 本身没有跨 Session 的自然长期记忆。本项目使用本地文件建立可检查、可编辑、Git 友好的记忆。

主要状态：

- `state/current_state.md`：当前能力与总体状态摘要；
- `state/current_focus.md`：近期训练重点；
- `state/knowledge_progress.json`：Concept 学习与复习状态；
- `state/practice_state.json`：Practice 汇总和责任等级提示；
- `state/review_schedule.json`：复习相关配置数据。

历史保存在 `logs/`、`evidence/`、`reviews/` 和 `interviews/`。

当前 Context Builder 每次加载 `SYSTEM.md`、`USER_PROFILE.md`、Current State、Current Focus、能力/Evidence/Responsibility 标准和 Knowledge Progress。普通交互还读取最近约 30 天的 Daily、Study、Evidence 和 Interview；指定 Capability 时只保留相关历史。

系统不会每次把全部文件发送给模型。随着状态和历史积累，Teacher 会逐渐知道用户是谁、最近做过什么、学过什么、暴露过哪些弱点，因此越来越像一个了解用户背景的私人老师。

## Monthly Review

```powershell
python -m growthos review monthly
```

建议每月运行一次。当前实现读取 Core Memory、Knowledge Progress 和 `logs/daily/` 中的全部 Daily 文件，由 AI 生成 Markdown Review，并重写：

- `state/current_state.md`；
- `state/current_focus.md`。

报告保存在 `reviews/monthly/YYYY-MM.md`。重点关注能力变化、反复弱点、Knowledge Gap、Practice Gap、强 Evidence 和下月训练重点。

当前代码尚未按自然月过滤 Daily，也没有在 Monthly Review 中显式加载完整 Study 和 Evidence 目录，因此这里不宣称它已经完成“完整月度全资料评估”。

## Quarterly Mock Executive Review

```powershell
python -m growthos review quarterly
```

建议每三个月运行一次。这不是普通总结，而是三轮 Mock Executive Interview。Interviewer 基于近 120 天上下文提问，访谈保存在 `interviews/YYYY-MM-DD_quarterly.md`。

随后系统结合近 120 天上下文与 Transcript 生成 `reviews/quarterly/YYYY-QX.md`，并更新 Current State 和 Current Focus。

典型追问包括：为什么、数字是什么、有哪些选择、放弃了什么、谁反对、如何影响对方、最终结果是什么、本人和团队分别做了什么。目的不是“表现得好”，而是发现 Executive-Level Gap。

## 推荐使用节奏

每天或按需要：

```powershell
python -m growthos study next
python -m growthos quiz
python -m growthos daily
```

Knowledge 学习建议 15–30 分钟，Daily 建议 5–10 分钟，Quiz 根据到期复习需要运行。

每周查看：

```powershell
python -m growthos status
```

每月运行：

```powershell
python -m growthos review monthly
```

每季度运行：

```powershell
python -m growthos review quarterly
```

## 典型使用场景

### 不知道 Finance 应该学什么

```powershell
python -m growthos topics finance
python -m growthos study path finance
python -m growthos study next
```

### 工作遇到 DSO 但不理解

运行 `daily` 如实记录问题。AI 提取 Knowledge Gap 后，`study next` 可以在前置条件满足时提高 DSO、Accounts Receivable 或 Working Capital 的优先级。

### ROI 以前学过但忘了

运行 `quiz`。如果 ROI 已到 `next_review_at`，系统会重新测试并调整复习时间。

### 想知道三个月成长得怎么样

运行 `review quarterly`，完成三轮 Mock Executive Interview，再查看季度报告。

## 数据目录

```text
curriculum/            YAML 课程与知识地图
state/                 当前状态和 JSON 进度
logs/daily/            工作反思
logs/study/            学习 Session
evidence/              独立实践证据
reviews/monthly/       月度评估
reviews/quarterly/     季度评估
interviews/            Mock Interview 记录
prompts/               AI Prompt
src/growthos/          Python 实现
tests/                 自动化测试
```

重要状态写入使用临时文件和原子替换。`.env` 与 `.env.local` 已加入 `.gitignore`，API Key 不应进入 Prompt、日志或版本库。

## 如何退出、撤销和检查学习记录

在 Recall 或 Application 回答阶段输入以下任一命令，可安全取消：

```text
q
quit
exit
/quit
```

命令大小写不敏感。取消、Ctrl+C、EOF、DeepSeek 错误或未通过最终保存确认，都不会写入 Study Log，也不会更新 `state/knowledge_progress.json`。

AI 完成评估后会先显示 Concept Score、Application Score、Status、Next Review 和反馈，再询问：

```text
保存本次学习结果？ [Y/n]
```

只有确认后才正式提交。

查看最近记录：

```powershell
python -m growthos study history
python -m growthos study history finance
```

查看单条完整记录：

```powershell
python -m growthos study show <id>
```

将错误记录标记为无效并重新计算该 Concept 的进度：

```powershell
python -m growthos study invalidate <id>
```

恢复被作废的记录：

```powershell
python -m growthos study restore <id>
```

撤销最近一次有效学习：

```powershell
python -m growthos study undo
```

如需从所有有效 Study History 重建 Knowledge Progress：

```powershell
python -m growthos study rebuild
```

系统默认使用 `invalidate` 而不是永久删除，因为错误记录本身也是审计历史。Invalid Session 会保留 `invalidated_at` 和 `invalidated_reason`，但不参与 Knowledge Progress、Spaced Repetition 和 Context Builder 的有效 Study History。## 最重要的使用原则

- 不要为了让 AI 认为自己优秀而包装答案；
- 不知道就直接说不知道；
- 失败经历比流水账更有学习价值；
- Daily 记录判断、冲突、决策和结果；
- Study 不要提前搜索答案；
- Quiz 不要为了“答对”临时查资料；
- AI 判断可能出错，可以人工检查状态文件；
- 目标不是把 138 个 Concept 全部打勾，而是提升真实管理能力；
- Knowledge 和 Practice 必须同时成长；
- Monthly 和 Quarterly Review 中失败的问题，应成为下一周期的重要学习材料。
