# HANDOFF-M1（M0 已收尾 → 下一棒 M1 数据先行）

> 用法：新对话 `/goal 读取 <项目绝对路径>\plan\HANDOFF-M1.md 继续完成任务`（库内一律相对路径）。

## 1. 当前进度 + 证据

- **M0 骨架已完成并提交**（见 git log，"M0 骨架"提交）。
- plan/02–06 六份计划文档已落盘（阶段 0 完整出口）。
- 骨架在位：`src/process_atlas/`（cli/logio/mining/layout/render 五模块，后四个为文档桩）、`pyproject.toml`（零依赖 + dev extra 仅 pytest + console script `process-atlas`）、`tools/gen_synthetic_log.py` 桩（exit 3）、`tests/test_skeleton.py`、`.github/workflows/ci.yml` 预置（windows/ubuntu × 3.8/3.12 四矩阵，`PYTHONUTF8=1`）。
- **证据**：双解释器 `pytest -q` 各 6 passed；CLI 冒烟：`--help` exit 0、`mine x.csv` exit 3、`validate missing.csv` exit 2、未知命令 exit 2（argparse SystemExit，契约即退出码）、`tools/gen_synthetic_log.py` exit 3。
- **诚实口径**：未接远端，CI 待首推验证（预置 workflow 从未被实跑，M6 首推预算至少一轮诊断，D8）。

## 2. 下一棒待办（M1 数据先行）

1. 实现 `tools/gen_synthetic_log.py`：splitmix64 自研 RNG（**禁 stdlib random**）、固定 seed、"报销审批（虚构）"场景、6–8 活动 / 12–20 变体 / ~200 cases；植入长等待边、罕见变体、并列时间戳样本（tie-break 覆盖）。
2. 产出四件套到 `data/synthetic/`：`events.csv`、`events_variants.json`（同内容双形态）、`truth.json`（**只存输入与期望，禁 observed 字段**，期望可由输入独立复算）、`manifest.json`（sha256 台账，生成器实算）。
3. 生成器自身断言恒等式：边频次总和 = trace 长度总和 − case 数。
4. `--check` 通路：重生成到临时目录与冻结产物逐字节比对；守门测试两层（冻结产物形态 + 重生成比对）。
5. 落盘后冻结：`data/synthetic/` 只读，禁手改。
6. 收尾：DoD 验证 → plan/00·05·06 回写 → HANDOFF-M2 → commit。

## 3. 既定口径清单（K，动了会打挂测试）

- **K1 退出码契约（D6）**：0 成功 / 2 用法与输入错误 / 3 阶段未就绪。模块落地时对应语义**整项退役**：删 `STAGE_NOT_READY` 条目 → 改 CLI → 改测试（`not hasattr` 防复活）→ 改文档退出码表 → 决策记录，五处同步。
- **K2 序列化冻结契约**：一切 JSON 落盘 `json.dumps(sort_keys=True, ensure_ascii=False, indent=2)` + LF + 结尾换行；落盘产物无时间戳；同输入双跑逐字节一致。
- **K3 确定性 RNG**：合成日志生成用 splitmix64 自研（stdlib random 跨版本序列不承诺一致）；seed 显式传参。
- **K4 tie-break 口径（D5）**：时间戳并列时活动次序以**源行号** tie-break；分位数 = 线性插值（自实现）。生成器必须产出并列时间戳样本覆盖此口径。
- **K5 Top-N 排名**：频次降序、并列按活动序列字典序；变体占比分母 = case 总数。
- **K6 编码守卫**：所有可执行入口（cli + tools/）挂 `_ensure_utf8_stdio()`；`gen_synthetic_log.py` 落地时必须挂上。
- **K7 品牌隔离**：比较性表述只作事实引用，不含 PM4Py/Celonis/ProM 商标词于仓库名/skill 名；文档不写漂移硬数字（星标类随检索式+基准日成对）。
- **K8 真值纪律**：truth.json 只存输入与期望；真值由生成器程序化派生，严禁手抄数字；禁 `observed` 字段。

## 4. 本机环境坑（只写实测过的）

- 用 `py` 不是 `python`（后者是商店占位符）；一律 `py -X utf8`。本机有 **3.8 与 3.12 两条通道**（`py -0p` 实测），每棒双解释器全量跑。
- 测试/脚本跑法：`PYTHONPATH=<repo>/src PYTHONDONTWRITEBYTECODE=1 py -3.8 -X utf8 -m pytest tests/ -q`（Git Bash）；骨架测试按文件路径加载 cli.py，不依赖安装。
- argparse 子命令未知选择抛 **SystemExit(2)**——契约是退出码本身，测试用 `pytest.raises(SystemExit)` 断 `.code == 2`（M0 实测踩过：`main()` 返回值断言测不到该路径）。

## 5. DoD 逐项 checklist（M1 出口）

- [ ] `tools/gen_synthetic_log.py` 一条命令产出四件套，无 stdlib random、无时钟字段落盘
- [ ] truth.json 恒等式断言通过（边频次总和 = trace 长度总和 − case 数）；无 `observed` 字段
- [ ] `--check` 重生成逐字节一致（守门测试两层齐）
- [ ] `manifest.json` sha256 与实盘文件一致；data/synthetic/ 冻结
- [ ] 双解释器 pytest 全绿（M0 6 项 + M1 新增）
- [ ] plan/00·05·06 回写 ✅；HANDOFF-M2 六节齐落盘；提交

## 6. 关键命令速查

```bash
cd <repo>
export PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1
py -3.8 -X utf8 -m pytest tests/ -q     # 全量测试（3.12 同）
py -3.8 -X utf8 -m process_atlas.cli --help
py -3.8 -X utf8 tools/gen_synthetic_log.py --seed 20261017   # M1 落地后
py -3.8 -X utf8 tools/gen_synthetic_log.py --check           # M1 落地后
```
