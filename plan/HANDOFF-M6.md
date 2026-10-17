# HANDOFF-M6（M5 已收尾 → 下一棒 M6 发布）

> 用法：新对话 `/goal 读取 <项目绝对路径>\plan\HANDOFF-M6.md 继续完成任务`（库内一律相对路径）。

## 1. 当前进度 + 证据

- **M0–M5 全部完成并提交**（见 git log）。
- **M5 落地**：
  - `SKILL.md`（仓根）：Agent Skill 规范 frontmatter（name/description 含触发词）；触发条件四类（流程图/瓶颈/变体分析/案例时长）；四步工作流 validate→mine→render→selftest 每步命令 + 退出码行为 + stderr 文案（`validation ok` 等，与代码逐字核对）；输入 schema 表；模型分工声明（表达层 only，逐字引用工具输出禁心算）；退出码表 0/1/2 **无 3**（D13）；排序口径段（K4/K5）。
  - `README.md`（仓根）：定位宣言、六条可复制命令（validate/mine/render/selftest/pytest/--check，全部 `PYTHONPATH=src py -X utf8` 源码直跑口径 + `pip install -e .` 等价跑法）、确定性声明表（每类数字的重算方式）、已知环境问题四条、边界 roadmap、MIT。
  - `plan/自评表.md`：四栏 40/20/20/20 逐项证据指针，自评 88/100（扣分项全部为 roadmap/时点因素：fitness 简化版 −3、SKILL 无外部实测 −1、无增强交互 −2、发布三件套+CI 未首推 −6）；M6 后复核。
  - **README 命令逐字复制实测全通（3.8）**：validate exit 0 / mine exit 0 / render exit 0（输出与入仓 `examples/report.html` `cmp` 逐字节一致）/ selftest exit 0（六项 ok）/ `--check` exit 0；selftest 双解释器（3.8 与 3.12）均 exit 0。
  - 文档一致性：plan/02 退出码契约段同步 D13 现状；plan/06 D14 决策 + P3 采纳回写 + M5 门勾；plan/00/05 M5 状态 ✅；哨兵串扫描（`NotImplementedError`/`TODO: 实现`/`placeholder`）0 命中；"阶段未就绪"仅存于退役说明语境与 D6 历史记录。
- **证据**：双解释器 `pytest -q` 各 **82 passed**；CLI 冒烟同上；`examples/report.html` 与 render 重跑输出逐字节一致。

## 2. 下一棒待办（M6 发布）

1. **建仓 + 首推**（P1/P2 待定决策需用户拍板，见 plan/06 §4；默认：账号 `yuluo554`、仓库名 `10-16-2-process-atlas-skill`、public）：
   - `git remote add origin <url>` → push main → 观察四矩阵 CI（windows/ubuntu × 3.8/3.12）首轮结果，**至少预留一轮诊断预算**（D8：预置≠跑过）。
   - CI 对账：push 数 = run 数（plan/05 诚实口径要求据实补记 run id）。
2. **tag + Release**：tag（建议 `v0.1.0`，与 pyproject 版本一致）→ `gh release create` 附 HTML 产物（`examples/report.html`）与基准数据（`data/synthetic/` 四件套）；**发布物本体已验（真下载复核）**——下载附件解压与仓内逐字节比对，不得只看 Release 页面存在。
3. **发布留档三件套**：`plan/RELEASE-M6.md`（发布时间/commit/tag/run id/附件清单/下载验证记录）；HANDOFF 链无断链自查（M1–M6 六节齐）。
4. **CI 绿后收尾**：若 CI 红，修因 → 重跑对账；README/plan 中"CI 待首推验证"措辞据实更新（历史措辞保留不改，只追加）。
5. **收尾**：DoD 验证 → plan/00·05·06 回写 M6 → commit（有远端后 push 等 CI 绿）。

## 3. 既定口径清单（K，动了会打挂测试）

- **K1 退出码契约（D6/D11/D12/D13/D14）**：0 成功 / 1 selftest 失败 / 2 用法与输入错误。**exit 3 已整项退役**（`STAGE_NOT_READY` 为空、`EXIT_NOT_READY` 不存在，测试防复活）。
- **K2 序列化冻结契约**：一切 JSON `json.dumps(sort_keys=True, ensure_ascii=False, indent=2)` + LF + 结尾换行；无时间戳字段落盘；同输入双跑逐字节一致；HTML 禁时钟（build_hash 内容派生）。
- **K3 确定性 RNG**：splitmix64，禁 stdlib random（生成器 + selftest 双守门）。
- **K4 tie-break**：时间戳并列以源行号 tie-break；分位 = 线性插值。
- **K5 Top-N**：频次降序、并列字典序；占比分母 = case 总数。
- **K6 编码守卫**：CLI 入口 `_ensure_utf8_stdio()`；文件读写显式 utf-8，写文件 `newline="\n"`。
- **K7 品牌隔离**：PM4Py/Celonis/ProM 只作事实引用；不写漂移硬数字。
- **K8 真值纪律**：truth.json 只读；渲染数字以 mining 实算为准。

## 4. 本机环境坑（只写实测过的）

- 用 `py` 不是 `python`；一律 `py -X utf8`；3.8/3.12 双通道每棒双解释器全量跑。
- 跑法：`PYTHONPATH=<repo>/src PYTHONDONTWRITEBYTECODE=1 py -3.8 -X utf8 -m pytest tests/ -q`（Git Bash）。
- test_skeleton.py 按路径加载 cli.py——不要在骨架测试里调 `main(["validate"/"mine"/"render"/"selftest"])`（相对导入会炸）；功能测试一律 `from process_atlas import cli` 包导入。
- argparse 未知子命令抛 SystemExit(2)，测试断 `.code == 2`。
- Windows cp936：`-X utf8` 下无编码坑；mine 走 stdout，render/validate/selftest 摘要走 stderr。
- Git Bash `/tmp` 对 Windows 原生 py 不可见——临时文件用 `$TEMP` 或 tempfile/tmp_path。
- `selftest._default_data_dir()` 上溯三级定位仓库根；换数据目录用 `run_selftest(data_dir)` 或 monkeypatch。
- `gh` CLI 建仓/Release 走题面 D 决策通道；账号名待 P1 用户确认后才可执行（未答复前不建仓）。

## 5. DoD 逐项 checklist（M6 出口）

- [ ] 远端已建 + main 首推成功
- [ ] 四矩阵 CI 全绿；push 数 = run 数对账（据实补记 run id）
- [ ] tag + GitHub Release，附件（HTML + 基准数据）**真下载复核**逐字节一致
- [ ] `plan/RELEASE-M6.md` 留档入库；HANDOFF 链 M1–M6 无断链
- [ ] plan/00·05·06 回写 ✅；自评表发布栏复核；提交（+push 等 CI 绿）

## 6. 关键命令速查

```bash
cd <repo>
export PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1
py -3.8 -X utf8 -m pytest tests/ -q               # 全量测试（3.12 同）
py -3.8 -X utf8 -m process_atlas.cli selftest     # 全绿 exit 0
py -3.8 -X utf8 tools/gen_synthetic_log.py --check
# M6（P1 确认后）：
# git remote add origin git@github.com:yuluo554/10-16-2-process-atlas-skill.git
# git push -u origin main && gh run watch
# git tag v0.1.0 && git push origin v0.1.0
# gh release create v0.1.0 examples/report.html data/synthetic/* --title ... --notes ...
```
