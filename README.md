# process-atlas

**把一份事件日志确定性挖出流程模型——直接跟随图 DFG、变体、瓶颈、符合度——渲染成可交互单文件 HTML，所有数字可被独立重算。**

流程挖掘在学术上有成熟算法、工程上有 PM4Py、ProM、Celonis 等实现（此处仅作事实引用），但一直以重型库或商用 SaaS 形态存在。process-atlas 把核心能力（DFG 计数、变体枚举、瓶颈统计、确定性布局渲染）用 **Python 纯标准库**自实现，并以 Agent Skill（`SKILL.md`）+ 命令行双形态交付：零第三方依赖、零 CDN、零上传。

- 输入：事件日志 CSV 或 JSON，三列/三字段 `case_id, activity, timestamp`
- 输出：单文件交互式 HTML（DFG 网络图 + 变体热力条 + 统计卡），双击即可打开
- 隐私红线：**纯本地处理，零上传**；HTML 零外部请求。使用前请自行确认日志可被处理。

## 使用方式

要求 Python ≥ 3.8（仅标准库；跑测试需 `pip install pytest` 或 `pip install -e .[dev]`）。以下命令均从仓库根执行（Windows 用 `py` 而非 `python`；`PYTHONPATH=src` 指向源码）。另一种跑法是先 `pip install -e .`，之后 `PYTHONPATH` 与 `-m` 前缀可省略（`process-atlas validate …`）。

```bash
# 1. 校验日志（逐行报错，全部错误一次报出）
PYTHONPATH=src py -X utf8 -m process_atlas.cli validate data/synthetic/events.csv

# 2. 挖掘（stdout 输出结果 JSON）
PYTHONPATH=src py -X utf8 -m process_atlas.cli mine data/synthetic/events.csv

# 3. 渲染单文件 HTML 报告
PYTHONPATH=src py -X utf8 -m process_atlas.cli render data/synthetic/events.csv -o examples/report.html

# 4. 自检基准（六项，全绿 exit 0）
PYTHONPATH=src py -X utf8 -m process_atlas.cli selftest

# 全量测试套件
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 py -3.8 -X utf8 -m pytest tests/ -q
```

退出码契约：**0** 成功；**1** 仅 `selftest` 失败（自检发现缺陷）；**2** 用法与输入错误（缺文件、schema 校验失败、未知子命令）。没有退出码 3（历史"阶段未就绪"语义已退役）。

Linux/macOS 把 `py -X utf8` 换成 `python3` 即可；`-X utf8` 在 Windows cp936 控制台下防编码坑。

合成日志可用 `tools/gen_synthetic_log.py` 再生成并自校验（`--check` 与冻结产物逐字节比对）：

```bash
PYTHONPATH=src py -X utf8 tools/gen_synthetic_log.py --check
```

## 确定性声明：哪些数字可重算、怎么重算

所有分析结果由确定性代码产出，**同输入两次运行逐字节一致**；模型（LLM）只做表达层，不产出任何数字。

| 数字 | 重算方式 |
| --- | --- |
| DFG 边频次 | 日志精确计数。恒等式守门：边频次总和 = trace 长度总和 − case 数（`selftest` 的 identity 基准） |
| 变体及占比 | 按 case_id 分组、组内按 timestamp 排序（并列以源行号 tie-break）→ 活动序列计数；占比分母 = case 总数。Top-N = 频次降序、并列按序列字典序 |
| 瓶颈等待 | 每条边的等待时长 = 同 case 相邻后继事件 timestamp − 前驱事件 timestamp，输出中位数/P95（线性插值） |
| 案例时长分布 | 每 case 首末事件时间差，min/中位数/P95/max（线性插值） |
| 布局坐标 | 确定性分层布局（最长路径分层，Kahn 序；回边确定性 DFS 剔除；层内按活动名字典序；整数像素） |

一条命令复核以上全部承诺：

```bash
PYTHONPATH=src py -X utf8 -m process_atlas.cli selftest
```

六项基准：files_present（数据四件套在位）/ identity（恒等式）/ truth_reconciliation（挖掘输出 vs `data/synthetic/truth.json` 逐字段全量对账）/ dual_form（CSV 与 JSON 双形态挖掘结果一致）/ double_run（全管线两次运行逐字节一致）/ falsifiable_probe（注入缺陷必报差异，探针失灵即失败）。

序列化冻结口径：一切 JSON 落盘 `json.dumps(sort_keys=True, ensure_ascii=False, indent=2)` + LF + 结尾换行；HTML 落盘 LF、UTF-8 无 BOM、无时钟（版本标识 `build_hash` 由内容 sha256 派生）。

## 仓库结构

```
SKILL.md                 Agent Skill 主入口（触发条件/工作流/退出码表）
src/process_atlas/       cli（编排+退出码）、logio（校验）、mining（DFG/变体/瓶颈）、layout（分层布局）、render（单文件 HTML）
tools/gen_synthetic_log.py  合成日志+真值生成器（splitmix64 确定性 RNG，禁 stdlib random）
data/synthetic/          冻结产物：events.csv / events_variants.json / truth.json / manifest.json（禁手改）
examples/report.html     示例产物（由合成日志生成，可直接双击打开）
tests/                   pytest 套件（含真值对账、双跑一致、零外链、可证伪探针）
plan/                    题目文档、架构、里程碑、决策记录、自评表
```

## 已知环境问题

- **Windows 用 `py` 不用 `python`**：后者常是微软商店占位符。一律 `py -X utf8`（UTF-8 模式防 cp936 控制台编码坑）。
- **双解释器**：本仓库在 Python 3.8 与 3.12 双通道下全量测试通过；`py -3.8` / `py -3.12` 可显式指定。
- **Git Bash 的 `/tmp`**：Windows 原生 Python 看不见 Git Bash 的 `/tmp`，临时文件请用系统临时目录。
- **源码直跑 vs 安装跑**：`PYTHONPATH=src` 是源码直跑口径；`pip install -e .` 后 `process-atlas` 命令等价。首期交付形态为源码包（clone 即用），不承诺 wheel 安装面。

## 边界与 roadmap（首期不做）

token replay 完整版符合度（首期为简化口径，接口已定）、时间线动画回放、PM4Py 互导、完整 Petri net / alpha miner。日志由用户提供，本工具只消费不采集。

## License

MIT
