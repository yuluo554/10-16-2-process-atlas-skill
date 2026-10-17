# HANDOFF-M4（M3 已收尾 → 下一棒 M4 校验基准）

> 用法：新对话 `/goal 读取 <项目绝对路径>\plan\HANDOFF-M4.md 继续完成任务`（库内一律相对路径）。

## 1. 当前进度 + 证据

- **M3 已完成并提交**（见 git log，"M3 渲染"提交）。
- `src/process_atlas/layout.py` 落地：`compute_layout(nodes, edges)` → `{activity: {x, y, layer}}`——最长路径分层（Kahn 序 + heap，`_longest_path_layers`），回边经确定性 DFS（lex 邻序，`_back_edges`）剔除后不参与层级（含自环剔除），层内按活动名字典序；坐标 = 层 × 240 / 层内序 × 100，全整数像素，无浮点/随机/时钟。常量 `LAYER_GAP=240`、`NODE_GAP=100`。
- `src/process_atlas/render.py` 落地：`render(result)` / `write_report(result, path)`（自动建父目录，UTF-8 + LF + 结尾换行，K2/K6）。单文件 HTML（`string.Template`，禁三方模板引擎）：DFG SVG（节点=活动+频次标签、边宽∝频次封顶 8px、`<title>` 悬停、点击高亮相关变体并 dim 无关节点/边/变体条）、变体热力条（Top-N 横条 CSS 宽度=占比）、统计卡 6 张。JS 只做表达层（消费预计算 `#pa-data` JSON blob，D4）。`build_hash` = sha256(mined+layout 规范化) 前 16 hex，**禁时钟**（无 `new Date`/`Date.now`，测试守门）。
- **零外链常驻**：`assert_no_external_resources(html)` 在 `render()` 出口**每次执行**（禁 `http(s)://`、`<link>`、`<script src>`、协议相对 `//`），测试含变异探针（注入外链必红）。
- **K1 退役五处同步完成（D12）**：`STAGE_NOT_READY` 删 render（仅剩 selftest=M4）→ CLI 接线（缺文件 exit 2、成功 exit 0）→ 测试防复活（`TestRenderRetiredNotReady` + `test_render_is_wired`）→ cli.py 文档头 D12 注 → plan/06 决策记录 D12。
- `examples/report.html` 入仓（22.8KB，由 data/synthetic/events.csv 生成，build_hash `2b598e1cc98b9323`）；双跑逐字节一致；**跨解释器 3.8/3.12 render 输出位级一致**（cmp 验证）。
- **证据**：双解释器 `pytest -q` 各 **54 passed**（M0 9 + M1 14 + M2 14 + M3 17）；CLI 冒烟 exit 0 / 缺文件 exit 2 / selftest 仍 exit 3；`gen_synthetic_log.py --check` exit 0；哨兵串扫描 0 命中；变异验证（删边布局必变、扰动必检出、全活动坐标互异）。
- **诚实口径**：未接远端，CI 仍待首推验证（D8 延续）；data/synthetic/ 冻结禁手改；report.html 数字全部来自 mining 实算（K8，未硬编码 truth.json）。

## 2. 下一棒待办（M4 校验基准）

1. 实现 `src/process_atlas/logio.py` 校验器（plan/03 §M4）：列完整性（缺列/多列/空行）、timestamp 可解析、case_id/activity 非空；**逐行报错**（`line 12: timestamp not parseable: 'xxx'`），全部错误一次性收集后统一报出（非首错即停）；JSON 通路报错带数组下标。注意：logio.py 当前已是骨架文件（M0 曾有 validate 接线），先读现状再动。
2. 基准套件：恒等断言（边频次总和 = trace 长度总和 − case 数）；真值对账（已有 test_mining 承担，selftest 侧复用）；**双跑一致全管线**（解析→挖掘→布局→渲染两次运行产物逐字节一致）。
3. **探活（可证伪）**：基准内嵌注入缺陷探针——同一套 check 必须报出差异；`selftest` 对空目录返回失败（exit 非 0），防编排层空壳。
4. CLI `selftest` 接线 + K1 退役五处同步（D11/D12 模式，决策记录 D13）：`STAGE_NOT_READY` 清空 → 接线 → 测试防复活 → 文档头 → 决策记录。
5. `selftest` 出口契约：全绿 exit 0；任一基准失败 exit 非 0（建议 1 或 2，落决策记录）。
6. 收尾：DoD 验证 → plan/00·05·06 回写 → HANDOFF-M5 → commit。

## 3. 既定口径清单（K，动了会打挂测试）

- **K1 退出码契约（D6/D11/D12）**：0 成功 / 2 用法与输入错误 / 3 阶段未就绪。M4 落地 selftest 后 `STAGE_NOT_READY` 清空，exit 3 语义整项退役（D13，五处同步）。校验失败/完整性失败归 exit 2（D9/D10 先例）。
- **K2 序列化冻结契约**：一切 JSON `json.dumps(sort_keys=True, ensure_ascii=False, indent=2)` + LF + 结尾换行；无时间戳字段落盘；同输入双跑逐字节一致。HTML 同禁时钟（build_hash 内容派生，M3 已落）。
- **K3 确定性 RNG**：合成日志 splitmix64（禁 stdlib random，`test_no_stdlib_random_in_generator` 守门）。
- **K4 tie-break 口径（D5）**：时间戳并列以源行号 tie-break；分位 = 线性插值。mining.py 与生成器各有一份 `quantile()` 独立实现（同口径，D11 注明未上提共用）。
- **K5 Top-N 排名**：频次降序、并列字典序；占比分母 = case 总数。
- **K6 编码守卫**：CLI 入口 `_ensure_utf8_stdio()` 已挂；库模块不自挂。文件读写显式 `encoding="utf-8"`，写文件 `newline="\n"` 防 CRLF。
- **K7 品牌隔离**：比较性表述只作事实引用，不含 PM4Py/Celonis/ProM 商标词；文档不写漂移硬数字。
- **K8 真值纪律**：truth.json 只读比对，禁改冻结产物；渲染数字以 mining 实算为准。

## 4. 本机环境坑（只写实测过的）

- 用 `py` 不是 `python`（后者是商店占位符）；一律 `py -X utf8`。本机 3.8 与 3.12 双通道，每棒双解释器全量跑。
- 跑法：`PYTHONPATH=<repo>/src PYTHONDONTWRITEBYTECODE=1 py -3.8 -X utf8 -m pytest tests/ -q`（Git Bash）。
- **test_skeleton.py 的 `_load_cli()` 按路径加载 cli.py（spec 名 `process_atlas_cli`）**：cli.py 函数体内相对导入（`from .mining import` / `from .render import`）在按路径加载的模块里调 main() 对应分支会炸 ImportError。**M2/M3 已处理：骨架测试只断子命令存在（`build_parser().format_help()`）或断 `not in STAGE_NOT_READY`，不调 main() 的 mine/render 分支；功能测试一律 `from process_atlas import cli` 包导入（test_mining.py/test_render.py 先例）。M4 的 selftest 接线测试同样不要在 test_skeleton 里调 main(["selftest"])。**
- pytest 下测试文件顶层 `sys.path.insert(0, src)` + `from process_atlas import ...` 是可靠通路；不要用 `spec_from_file_location` 加载含相对导入的模块。
- argparse 子命令未知选择抛 SystemExit(2)，测试断 `.code == 2`。
- Windows 控制台 cp936：`-X utf8` 跑法下无编码坑；`mine` 打印走 `sys.stdout.write`，`render` 成功消息走 `sys.stderr.write`（stdout 保持干净）。
- `/tmp` 在 Git Bash 侧 `py`（Windows 原生）不可见——临时文件用 `tempfile` 或 pytest `tmp_path`，不要 shell 层 `/tmp`。

## 5. DoD 逐项 checklist（M4 出口）

- [ ] `selftest` 一条命令全绿（exit 0）：恒等断言 + 真值对账 + 双跑一致 + 探活探针
- [ ] 探活可证伪：注入缺陷必报差异；对空目录 selftest 必失败（exit 非 0）
- [ ] logio 逐行报错（非首错即停）+ JSON 通路报错带数组下标，锁测试
- [ ] K1 退役五处同步完成（selftest 不再 exit 3；`STAGE_NOT_READY` 清空；测试防复活）
- [ ] 双解释器 pytest 全绿（M0 9 + M1 14 + M2 14 + M3 17 + M4 新增）
- [ ] plan/00·05·06 回写 ✅；HANDOFF-M5 六节齐落盘；提交

## 6. 关键命令速查

```bash
cd <repo>
export PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1
py -3.8 -X utf8 -m pytest tests/ -q     # 全量测试（3.12 同）
py -3.8 -X utf8 -m process_atlas.cli validate data/synthetic/events.csv
py -3.8 -X utf8 -m process_atlas.cli mine data/synthetic/events.csv
py -3.8 -X utf8 -m process_atlas.cli render data/synthetic/events.csv -o examples/report.html
py -3.8 -X utf8 -m process_atlas.cli selftest   # M4 落地后
py -3.8 -X utf8 tools/gen_synthetic_log.py --check       # 数据完整性随时可验
```
