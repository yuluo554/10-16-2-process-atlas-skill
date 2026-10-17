# HANDOFF-M2（M1 已收尾 → 下一棒 M2 挖掘算法）

> 用法：新对话 `/goal 读取 <项目绝对路径>\plan\HANDOFF-M2.md 继续完成任务`（库内一律相对路径）。

## 1. 当前进度 + 证据

- **M1 已完成并提交**（见 git log，"M1 数据先行"提交）。
- `tools/gen_synthetic_log.py` 落地：splitmix64 自研 RNG（K3，无 stdlib random，测试守门）、seed 显式 `--seed`（默认 20261017）、"报销审批（虚构）"场景、8 活动 / 14 变体 / 200 cases / 1232 events。
- 四件套冻结入 `data/synthetic/`：`events.csv`、`events_variants.json`（与 CSV 同内容双形态，测试断言逐行相等）、`truth.json`（只存 `input`+`expected`，无 `observed` 字段）、`manifest.json`（sha256 台账生成器实算，与实盘一致）。
- **埋点齐**：瓶颈边 财务复核→打款（等待 25h–70h，中位 ~169805s 排第 1）；罕见变体 14 个全部 count≥1；**并列时间戳 19 个 case**（K4 tie-break 覆盖）。
- 恒等式：边频次总和 1032 = trace 长度总和 − case 数 = 1232 − 200，生成器 `derive_truth()` 自身断言 + 测试双覆盖。
- `--check` 通路：重生成到临时目录与冻结产物逐字节比对（exit 0）；篡改/缺失冻结产物 exit 2（D10）。
- **证据**：双解释器 `pytest -q` 各 **20 passed**（M0 6 + M1 14，见 `tests/test_data_guard.py` 两层守门）；CLI 冒烟 `--help` exit 0；哨兵串扫描（NotImplementedError/TODO: 实现/placeholder）0 命中。
- **诚实口径**：未接远端，CI 仍待首推验证（D8 延续）；data/synthetic/ 冻结禁手改，改动走生成器 + `--check`。

## 2. 下一棒待办（M2 挖掘算法）

1. 实现 `src/process_atlas/mining.py`（plan/03 §M2 为实现级规格）：`load_events`（CSV/JSON 双通路，timestamp=`datetime`，naive 口径）、`mine_dfg`（(case_id, timestamp, 源行号) 稳定排序取相邻对计数——**源行号 tie-break 直接对 M1 的 19 个并列 case 生效**）、`mine_variants`（Top-N = 频次降序、并列按序列字典序，占比分母 = case 总数）、`bottlenecks`（中位数/P95 线性插值自实现，复用口径 K4/K5）、案例时长分布。
2. CLI `mine` 子命令接线：输出 JSON（schema 见 plan/03 §M2），**K1 退役流程五处同步**——删 `STAGE_NOT_READY["mine"]` → 改 CLI → 改测试（`test_mine_is_not_ready` 删除 + `not hasattr` 防复活）→ 改 cli.py 文档头退出码表 → plan/06 决策记录补记。
3. **真值对账**：mining 输出 vs `data/synthetic/truth.json` 逐字段相等（dfg_edges 全集、variants 全集含 rank/ratio、bottlenecks 含 median/p95、case_durations），全量实跑非抽样。
4. 无三方 import 守门测试（mining.py 源码扫描 + sys.modules 断言）。
5. 双跑一致：`mine` 同输入两次输出逐字节一致。
6. 收尾：DoD 验证 → plan/00·05·06 回写 → HANDOFF-M3 → commit。

## 3. 既定口径清单（K，动了会打挂测试）

- **K1 退出码契约（D6）**：0 成功 / 2 用法与输入错误 / 3 阶段未就绪。模块落地时对应语义**整项退役**：删 `STAGE_NOT_READY` 条目 → 改 CLI → 改测试（`not hasattr` 防复活）→ 改文档退出码表 → 决策记录，五处同步。**注意**：`--check` 已把"完整性失败"归 exit 2（D10 先例）。
- **K2 序列化冻结契约**：一切 JSON 落盘/输出 `json.dumps(sort_keys=True, ensure_ascii=False, indent=2)` + LF + 结尾换行；无时间戳字段落盘；同输入双跑逐字节一致。`mine` 打印的 JSON 同此参数。
- **K3 确定性 RNG**：合成日志生成用 splitmix64 自研（禁 stdlib random，测试守门在 `test_no_stdlib_random_in_generator`）。
- **K4 tie-break 口径（D5）**：时间戳并列时活动次序以**源行号** tie-break；分位数 = 线性插值（自实现，生成器里已有参考实现 `quantile()`，mining 侧独立实现或上提共用需在 plan/03 注明）。M1 已植入 19 个并列 case 供对账。
- **K5 Top-N 排名**：频次降序、并列按活动序列字典序；变体占比分母 = case 总数。
- **K6 编码守卫**：所有可执行入口（cli + tools/）挂 `_ensure_utf8_stdio()`；mining 作为库模块无需自挂，CLI 入口已挂。
- **K7 品牌隔离**：比较性表述只作事实引用，不含 PM4Py/Celonis/ProM 商标词；文档不写漂移硬数字。
- **K8 真值纪律**：truth.json 只存输入与期望；禁 `observed` 字段（测试守门）；M2 消费 truth.json 时**只读比对**，禁改冻结产物。

## 4. 本机环境坑（只写实测过的）

- 用 `py` 不是 `python`（后者是商店占位符）；一律 `py -X utf8`。本机有 **3.8 与 3.12 两条通道**（`py -0p` 实测），每棒双解释器全量跑。
- 测试/脚本跑法：`PYTHONPATH=<repo>/src PYTHONDONTWRITEBYTECODE=1 py -3.8 -X utf8 -m pytest tests/ -q`（Git Bash）；测试按文件路径加载 cli.py / gen_synthetic_log.py，不依赖安装。
- argparse 子命令未知选择抛 **SystemExit(2)**——契约是退出码本身，测试用 `pytest.raises(SystemExit)` 断 `.code == 2`。
- Windows 控制台 cp936：`_ensure_utf8_stdio()` 对 cp936/gbk 刻意跳过 reconfigure（项目口径），`-X utf8` 跑法下无编码坑；文件读写显式 `encoding="utf-8"` + `newline="\n"`（CSV 生成器实测防 CRLF）。

## 5. DoD 逐项 checklist（M2 出口）

- [ ] `mine` 子命令对合成日志输出 JSON，schema 与 plan/03 §M2 一致（nodes/edges/variants/case_stats）
- [ ] 真值对账逐字段全绿（dfg_edges / variants / bottlenecks / case_durations vs truth.json）
- [ ] K1 退役五处同步完成（mine 不再 exit 3；测试防复活）
- [ ] 无三方 import 守门通过；双跑输出逐字节一致
- [ ] 双解释器 pytest 全绿（M0 6 + M1 14 + M2 新增）
- [ ] plan/00·05·06 回写 ✅；HANDOFF-M3 六节齐落盘；提交

## 6. 关键命令速查

```bash
cd <repo>
export PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1
py -3.8 -X utf8 -m pytest tests/ -q     # 全量测试（3.12 同）
py -3.8 -X utf8 -m process_atlas.cli mine data/synthetic/events.csv   # M2 落地后
py -3.8 -X utf8 tools/gen_synthetic_log.py --check       # 数据完整性随时可验
```
