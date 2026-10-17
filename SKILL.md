---
name: process-atlas
description: Event log to deterministic process discovery graph (DFG, variants, bottlenecks) as a zero-CDN single-file HTML report. Use when the user provides an event log (CSV/JSON with case_id, activity, timestamp) and asks for a process map / flow diagram, bottleneck analysis, or variant analysis. All numbers are computed by deterministic stdlib-only Python code — the model never produces frequencies or coordinates.
---

# process-atlas：事件日志 → 确定性流程发现图

把一份事件日志确定性挖出流程模型——直接跟随图（DFG）、变体、瓶颈、案例统计——渲染成零 CDN 的单文件交互式 HTML。所有数字（边频次、变体占比、等待分位数、布局坐标）全部由纯标准库 Python 代码产出，同输入双跑逐字节一致；模型只做表达层（解读报告、向用户复述结论），永不产出或"心算"任何数字。

## 触发条件

用户给了事件日志（CSV 或 JSON，字段 `case_id, activity, timestamp`），并要求以下任一项：

- 画流程图 / 流程实际怎么走（DFG 流程发现图）；
- 瓶颈 / 卡点分析（哪一步等待最久）；
- 变体分析（流程实际有哪几条走法、各占多少）；
- 案例时长分布。

不适用于：日志采集（本 skill 只消费不产生日志）、Petri net / alpha miner、token replay 完整版符合度（首期未实现，见 README roadmap）、需要联网渲染的场景（输出零外部请求，纯本地）。

## 工作流

按顺序执行，每步的退出码见下表；任何一步非 0 都先向用户报告原始错误输出，不要跳过校验直接挖掘。

### 第 1 步：校验日志

```bash
PYTHONPATH=src py -X utf8 -m process_atlas.cli validate <日志路径>
```

- 通过则 exit 0（stderr 打印 `validation ok`）。
- 失败则 exit 2，stderr 逐行列出全部错误（`line 12: timestamp not parseable: 'xxx'`；JSON 通路为 `events[3]: …`），把输出原样转述给用户并停止。
- 错误信息已带行号/下标，可直接指给用户修数据；不要替用户"猜测修复"后重跑。

### 第 2 步：挖掘

```bash
PYTHONPATH=src py -X utf8 -m process_atlas.cli mine <日志路径>
```

- 成功 exit 0，stdout 输出结果 JSON（schema：`{nodes, edges[{from,to,count,median_wait_s,p95_wait_s}], variants[{seq,count,ratio,rank}], case_stats}`，UTF-8、键排序、缩进 2）。
- 失败 exit 2（文件缺失 / 解析失败，stderr 带原因）。

### 第 3 步：渲染 HTML 报告

```bash
PYTHONPATH=src py -X utf8 -m process_atlas.cli render <日志路径> -o <输出.html>
```

- 成功 exit 0，stderr 打印 `report written: <输出.html>`；产物是单文件 HTML（内嵌 SVG + 数据，零 CDN、零外部请求），把该文件的绝对路径指给用户在浏览器打开。
- 之后向用户解读报告：Top 变体、最长等待边、案例时长——**只引用 mine/validate 的输出数字，不要自己重算**。

### 第 4 步（可选）：自检基准

```bash
PYTHONPATH=src py -X utf8 -m process_atlas.cli selftest
```

六项基准（文件在位 / 恒等式 / 真值对账 / CSV-JSON 双形态 / 双跑一致 / 可证伪探针），全绿 exit 0，任一失败 exit 1。怀疑安装环境有问题时跑一次即可。

## 输入 schema

| 字段 | 类型 | 要求 |
| --- | --- | --- |
| `case_id` | 字符串 | 非空；同一 case 的事件归属同组 |
| `activity` | 字符串 | 非空；活动名 |
| `timestamp` | 字符串 | ISO 8601 可解析（容忍尾部 `Z`）；无时区按 naive 处理（口径见 README） |

- CSV：须含且仅含上述三列表头（多余列报错）；JSON：顶层数组或 `{"events": [...]}`。
- 隐私红线：日志与 HTML 产物全程纯本地处理、零上传；**用户须自行确认日志可被处理**。
- 想先看可跑通的样例：仓库自带 `data/synthetic/events.csv`（"报销审批（虚构）"合成日志）。

## 模型分工声明

- **模型只做表达层**：活动名语义归并建议（如 "Approve"/"Approved" 是否合并）、对报告的自然语言解读、视觉风格偏好沟通。
- **模型永不产出频次、占比、等待分位数、布局坐标**——全部由确定性代码计算；解读时逐字引用工具输出，不得估算。

## 退出码表（K1 契约，锁进测试）

| 退出码 | 含义 | 场景 |
| --- | --- | --- |
| 0 | 成功 | validate 通过 / mine 出 JSON / render 写出报告 / selftest 全绿 |
| 1 | selftest 失败 | 仅 `selftest`：自检发现缺陷（产品本身有问题） |
| 2 | 用法与输入错误 | 缺文件、schema 校验失败、JSON 解析失败、未知子命令 |

没有退出码 3（历史"阶段未就绪"语义已整项退役，D13）。

## 排序与统计口径（固定，不得由模型临场解释）

- 时间戳并列时事件次序以源行号 tie-break（K4）；分位数 = 线性插值。
- 变体 Top-N = 频次降序、并列按活动序列字典序；占比分母 = case 总数（K5）。
- 瓶颈 = 边等待时长中位数排名靠前的边，规则固定。
