# HANDOFF-M5（M4 已收尾 → 下一棒 M5 交付文档）

> 用法：新对话 `/goal 读取 <项目绝对路径>\plan\HANDOFF-M5.md 继续完成任务`（库内一律相对路径）。

## 1. 当前进度 + 证据

- **M0–M4 全部完成并提交**（见 git log）。
- **M4 落地**：
  - `src/process_atlas/logio.py`：`validate_csv` / `validate_json_log` / `validate_log`（按首字节分派）/ `cmd_validate`。CSV 查列完整性（缺列、多列、空行、空文件）、timestamp 可解析（`datetime.fromisoformat`，容忍尾部 `Z`）、case_id/activity 非空；**全部错误一次收集统一报出**（`line 12: timestamp not parseable: 'xxx'` 口径，非首错即停）；JSON 通路逐事件报错带数组下标（`events[3]: …`），支持数组与 `{events:[…]}` 两种顶层形态。校验失败 exit 2（K1，D9/D10 先例）。
  - `src/process_atlas/selftest.py`：六项基准 `run_selftest(data_dir=None)` → `(failures, checks)`：files_present / identity（边频次总和 = trace 长度总和 − case 数）/ truth_reconciliation（vs truth.json 逐字段全量，K8 只读）/ dual_form（CSV/JSON 双形态挖掘一致）/ double_run（全管线两次运行逐字节一致）/ falsifiable_probe（三探针：损坏变体计数、删边、布局扰动——同一套 check 必报差异；探活报不出差异即失败）。默认 data 目录 = 包文件上溯三级 `data/synthetic`；空目录/缺目录直接失败并中止后续检查。
  - **CLI `selftest`**：全绿 exit 0；任一失败 exit 1（D13）；成功摘要走 stderr、逐项 `ok <name>` 走 stdout。
  - **K1 整项退役**（D13）：`STAGE_NOT_READY` 清空、`EXIT_NOT_READY` 常量删除（exit 3 语义从此不存在）、测试防复活三断言（`TestSelftestRetiredNotReady`）、cli 文档头、plan/06 D13 五处同步。
- **证据**：双解释器 `pytest -q` 各 **82 passed**（M0 11 + M1 14 + M2 14 + M3 17 + M4 26）；CLI 冒烟：`validate` exit 0 / 坏文件 exit 2 逐行报错、`selftest` exit 0（3.8 与 3.12 双跑）、selftest 空目录 exit 1、未知命令 exit 2、`gen_synthetic_log.py --check` exit 0、`render` 输出与入仓 `examples/report.html` 逐字节一致、`mine` 双跑及跨解释器逐字节一致；哨兵串扫描 0 命中；新模块 stdlib-only 扫描通过。
- **诚实口径**：未接远端，CI 仍待首推验证（D8 延续）；data/synthetic/ 冻结禁手改；selftest 的 truth 对账与 test_mining.py 同口径（两处独立调用同一套 truth 文件）。

## 2. 下一棒待办（M5 交付文档）

1. **`SKILL.md`**（plan/03 §M5）：触发条件（用户给事件日志要"流程图/瓶颈/变体分析"）、工作流步骤（校验→挖掘→渲染→指读 HTML）、模型分工声明（表达层 only）、输入 schema、退出码表（0/1/2，**无 3**——D13）；文件名与 frontmatter 按 Agent Skill 规范，正文命令逐字可跑。
2. **`README.md`**：定位宣言、使用方式（可复制命令：validate / mine / render / selftest）、确定性声明（哪些数字可重算、如何重算、双跑一致性、K2/K3）、已知环境问题（py vs python、双解释器、cp936）。
3. **`plan/自评表.md`**：评分四栏（40/20/20/20）自评表，逐项给证据指针（测试名 / 产物路径 / selftest 输出），禁空话。
4. **交付物核对**：`examples/report.html` 已在仓（M3）；确认 README 引用的每条命令在干净环境按字面可跑（`py -3.8 -X utf8` 口径），必要时在 README 写明 `PYTHONPATH=src` 的两种跑法（源码直跑 / 仓根执行）。
5. **哨兵串扫描 + 文档一致性**：退出码表、里程碑状态、决策记录编号不得残留 exit 3 / "阶段未就绪"表述；plan/05 M5 行回写。
6. **收尾**：DoD 验证 → plan/00·05·06 回写 → HANDOFF-M6 → commit。

## 3. 既定口径清单（K，动了会打挂测试）

- **K1 退出码契约（D6/D11/D12/D13）**：0 成功 / 1 selftest 失败 / 2 用法与输入错误。**exit 3 已整项退役**：`STAGE_NOT_READY` 为空且 `EXIT_NOT_READY` 常量不存在（测试防复活，别再加回来）。校验器/完整性失败归 exit 2（D9/D10）。
- **K2 序列化冻结契约**：一切 JSON `json.dumps(sort_keys=True, ensure_ascii=False, indent=2)` + LF + 结尾换行；无时间戳字段落盘；同输入双跑逐字节一致。HTML 同禁时钟（build_hash 内容派生，M3 已落）。
- **K3 确定性 RNG**：合成日志 splitmix64（禁 stdlib random，`test_no_stdlib_random_in_generator` 守门；selftest 源码亦有 no-random 扫描）。
- **K4 tie-break 口径（D5）**：时间戳并列以源行号 tie-break；分位 = 线性插值。mining.py 与生成器各有一份 `quantile()` 独立实现（同口径，D11 注明未上提共用）。
- **K5 Top-N 排名**：频次降序、并列字典序；占比分母 = case 总数。
- **K6 编码守卫**：CLI 入口 `_ensure_utf8_stdio()` 已挂；库模块不自挂。文件读写显式 `encoding="utf-8"`，写文件 `newline="\n"` 防 CRLF。
- **K7 品牌隔离**：比较性表述只作事实引用，不含 PM4Py/Celonis/ProM 商标词；文档不写漂移硬数字。
- **K8 真值纪律**：truth.json 只读比对，禁改冻结产物；渲染数字以 mining 实算为准。

## 4. 本机环境坑（只写实测过的）

- 用 `py` 不是 `python`（后者是商店占位符）；一律 `py -X utf8`。本机 3.8 与 3.12 双通道，每棒双解释器全量跑。
- 跑法：`PYTHONPATH=<repo>/src PYTHONDONTWRITEBYTECODE=1 py -3.8 -X utf8 -m pytest tests/ -q`（Git Bash）。
- **test_skeleton.py 的 `_load_cli()` 按路径加载 cli.py**：cli.py 函数体内相对导入（`from .logio import` / `from .selftest import`）在按路径加载的模块里调 main() 对应分支会炸 ImportError。骨架测试只断子命令存在或 `STAGE_NOT_READY` 结构，**不要在 test_skeleton 里调 main(["validate"/"mine"/"render"/"selftest"])**；功能测试一律 `from process_atlas import cli` 包导入（test_logio.py / test_selftest.py 先例）。
- pytest 下测试文件顶层 `sys.path.insert(0, src)` + `from process_atlas import ...` 是可靠通路；不要用 `spec_from_file_location` 加载含相对导入的模块。
- argparse 子命令未知选择抛 SystemExit(2)，测试断 `.code == 2`。
- Windows 控制台 cp936：`-X utf8` 跑法下无编码坑；`mine` 打印走 `sys.stdout.write`，`render`/`validate`/`selftest` 摘要走 `sys.stderr.write`（stdout 保持干净）。
- `/tmp` 在 Git Bash 侧 `py`（Windows 原生）不可见——临时文件用 `tempfile` 或 pytest `tmp_path`，不要 shell 层 `/tmp`。
- `selftest._default_data_dir()` 从 `src/process_atlas/selftest.py` 上溯三级定位仓库根；测试里要换数据目录用 `run_selftest(data_dir)` 或 monkeypatch `_default_data_dir`（test_selftest.py 先例），不要改默认路径常量。

## 5. DoD 逐项 checklist（M5 出口）

- [ ] `SKILL.md` 在位：触发条件 / 工作流 / 模型分工 / 输入 schema / 退出码表（0/1/2，无 3）
- [ ] `README.md` 命令逐字可跑（干净环境按字面复制执行）
- [ ] `plan/自评表.md` 四栏评分逐项带证据指针
- [ ] 文档一致性：无 exit 3 / "阶段未就绪"残留；里程碑状态回写
- [ ] 双解释器 pytest 全绿（M0 11 + M1 14 + M2 14 + M3 17 + M4 26 = 82）
- [ ] plan/00·05·06 回写 ✅；HANDOFF-M6 六节齐落盘；提交

## 6. 关键命令速查

```bash
cd <repo>
export PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1
py -3.8 -X utf8 -m pytest tests/ -q               # 全量测试（3.12 同）
py -3.8 -X utf8 -m process_atlas.cli validate data/synthetic/events.csv
py -3.8 -X utf8 -m process_atlas.cli mine data/synthetic/events.csv
py -3.8 -X utf8 -m process_atlas.cli render data/synthetic/events.csv -o examples/report.html
py -3.8 -X utf8 -m process_atlas.cli selftest      # 全绿 exit 0；失败 exit 1
py -3.8 -X utf8 tools/gen_synthetic_log.py --check
```
