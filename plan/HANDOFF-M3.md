# HANDOFF-M3（M2 已收尾 → 下一棒 M3 渲染）

> 用法：新对话 `/goal 读取 <项目绝对路径>\plan\HANDOFF-M3.md 继续完成任务`（库内一律相对路径）。

## 1. 当前进度 + 证据

- **M2 已完成并提交**（见 git log，"M2 挖掘算法"提交）。
- `src/process_atlas/mining.py` 落地：`load_events`（CSV/JSON 双通路按首字符 sniff，timestamp=`datetime` naive 口径 + 源行号 row_no）、`mine_dfg`（(case_id 内 (timestamp,row_no) 排序取相邻对计数，**K4 源行号 tie-break 对 M1 的 19 个并列 case 直接生效**）、`mine_variants`（Top-N 频次降序、并列按序列字典序，ratio 分母 = case 总数，K5）、`bottlenecks`（中位数/P95 线性插值自实现 `quantile()`，按中位降序、(from,to) 字典序排 rank）、`case_stats`（min/median/p95/max）、`mine()`/`mine_to_json()`（K2 序列化口径）。
- CLI `mine` 接线：缺文件/解析失败 → exit 2；成功打印 JSON（exit 0）。**K1 退役五处同步完成**：`STAGE_NOT_READY` 删 mine → CLI 接线 → 测试（删 `test_mine_is_not_ready`，新增 `test_mine_not_in_stage_not_ready` + 缺文件 exit 2 防复活）→ cli.py 文档头退出码表补 D11 注 → plan/06 决策记录 D11。
- **真值对账全绿**：`tests/test_mining.py` 对 `data/synthetic/truth.json` 逐字段相等（dfg_edges 全集 / variants 全集含 rank+ratio / bottlenecks 含 median+p95 / case_durations / nodes / case_count），全量实跑非抽样；CSV 与 JSON 双形态挖掘结果相等（D5）。
- **纯度守门**：mining.py 源码逐 import 行白名单扫描 + 运行期 sys.modules 增量断言，全标准库。
- **确定性**：同输入双跑逐字节一致（库函数 + CLI 双验证）；跨解释器 3.8/3.12 `mine` 输出位级一致。
- **证据**：双解释器 `pytest -q` 各 **36 passed**（M0 8 + M1 14 + M2 14）；CLI 冒烟 exit 0 / 缺文件 exit 2 / render 仍 exit 3；`gen_synthetic_log.py --check` exit 0；哨兵串扫描 0 命中。
- **诚实口径**：未接远端，CI 仍待首推验证（D8 延续）；data/synthetic/ 冻结禁手改。

## 2. 下一棒待办（M3 渲染）

1. 实现 `src/process_atlas/layout.py`（plan/03 §M3）：分层布局（Sugiyama 类简化版）——按活动拓扑层级分层（最长路径层、Kahn 序；回边不参与层级），同层内按活动名字典序；坐标 = (层 × 固定层距, 层内序 × 固定间距)，全程无浮点随机项，坐标整数像素；输出 `{activity: {x, y, layer}}`。
2. 实现 `src/process_atlas/render.py`：单文件 HTML（`string.Template`，禁三方模板引擎）——DFG SVG（节点=活动+频次标签、边宽∝频次、悬停中位/P95、点击高亮变体）、变体热力条（Top-N 横条，CSS 宽度=占比）、汇总统计卡（case/活动/边/变体数）。
3. **零 CDN 硬断言常驻**：`assert_no_external_resources(html)` 在 render 出口每次执行（禁 `http(s)://`、协议相对 `//src`、`<link>`/`<script src>` 外链），非仅测试期验一次。
4. `build_hash`：由内容派生的版本标识入 HTML；**禁时钟/时间戳**入 HTML（K2）。
5. CLI `render` 子命令接线 + K1 退役五处同步（同 D11 模式：删条目 → 接线 → 测试防复活 → 文档头 → 决策记录 D12）。
6. 示例产物 `examples/report.html`（由 data/synthetic/events.csv 生成并入仓）；双跑逐字节一致断言。
7. 收尾：DoD 验证 → plan/00·05·06 回写 → HANDOFF-M4 → commit。

## 3. 既定口径清单（K，动了会打挂测试）

- **K1 退出码契约（D6/D11）**：0 成功 / 2 用法与输入错误 / 3 阶段未就绪。模块落地时语义整项退役五处同步（见 D11 先例）。当前 `STAGE_NOT_READY` 仅剩 render(M3)/selftest(M4)。
- **K2 序列化冻结契约**：一切 JSON `json.dumps(sort_keys=True, ensure_ascii=False, indent=2)` + LF + 结尾换行；无时间戳字段落盘；同输入双跑逐字节一致。HTML 同禁时钟。
- **K3 确定性 RNG**：合成日志 splitmix64（禁 stdlib random，`test_no_stdlib_random_in_generator` 守门）。
- **K4 tie-break 口径（D5）**：时间戳并列以源行号 tie-break；分位 = 线性插值。**mining.py 与生成器各有一份 `quantile()` 独立实现（同口径），D11 已注明未上提共用**；M3 若需分位，优先复用 `mining.quantile`。
- **K5 Top-N 排名**：频次降序、并列字典序；占比分母 = case 总数。
- **K6 编码守卫**：CLI 入口 `_ensure_utf8_stdio()` 已挂；库模块不自挂。文件读写显式 `encoding="utf-8"`，写文件 `newline="\n"` 防 CRLF。
- **K7 品牌隔离**：比较性表述只作事实引用，不含 PM4Py/Celonis/ProM 商标词；文档不写漂移硬数字。
- **K8 真值纪律**：truth.json 只读比对，禁改冻结产物（M3 渲染数字以 mining 实算为准，不以 truth.json 硬编码入 HTML）。

## 4. 本机环境坑（只写实测过的）

- 用 `py` 不是 `python`（后者是商店占位符）；一律 `py -X utf8`。本机 3.8 与 3.12 双通道，每棒双解释器全量跑。
- 跑法：`PYTHONPATH=<repo>/src PYTHONDONTWRITEBYTECODE=1 py -3.8 -X utf8 -m pytest tests/ -q`（Git Bash）。
- **test_skeleton.py 的 `_load_cli()` 按路径加载 cli.py（spec 名 `process_atlas_cli`）**：cli.py 现含 `from .mining import`（函数体内），按路径加载的模块在 `main()` 调用到 mine 分支时会炸相对导入——M2 已处理（test_mining.py 用 `from process_atlas import cli` 正常包导入）。**M3 接线 render 后不要给 test_skeleton 加 render 的 main() 调用**；新测试一律包导入。
- pytest 下测试文件顶层 `sys.path.insert(0, src)` + `from process_atlas import ...` 是可靠通路（M2 实测）；不要用 `spec_from_file_location` 加载含相对导入的模块。
- argparse 子命令未知选择抛 SystemExit(2)，测试断 `.code == 2`。
- Windows 控制台 cp936：`-X utf8` 跑法下无编码坑；`mine` 打印走 `sys.stdout.write`（JSON 已含结尾换行）。

## 5. DoD 逐项 checklist（M3 出口）

- [ ] `render` 子命令对合成日志输出单文件 HTML（examples/report.html 入仓）
- [ ] 零外链断言常驻（render 出口每次执行）+ 双跑逐字节一致 + build_hash 内容派生
- [ ] 布局确定性：坐标全整数、无随机项；变异验证（布局扰动必红，见 plan/05 M3 门）
- [ ] K1 退役五处同步完成（render 不再 exit 3；测试防复活）
- [ ] 双解释器 pytest 全绿（M0 8 + M1 14 + M2 14 + M3 新增）
- [ ] plan/00·05·06 回写 ✅；HANDOFF-M4 六节齐落盘；提交

## 6. 关键命令速查

```bash
cd <repo>
export PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1
py -3.8 -X utf8 -m pytest tests/ -q     # 全量测试（3.12 同）
py -3.8 -X utf8 -m process_atlas.cli mine data/synthetic/events.csv   # 挖掘 JSON
py -3.8 -X utf8 -m process_atlas.cli render data/synthetic/events.csv -o examples/report.html  # M3 落地后
py -3.8 -X utf8 tools/gen_synthetic_log.py --check       # 数据完整性随时可验
```
