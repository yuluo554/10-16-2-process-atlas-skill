# RELEASE v0.2.0 发布留档（2026-10-20）

## 发布基本信息

| 项 | 值 |
| --- | --- |
| 发布类型 | 二次迭代收尾（元数据现代化 + CI 卫生 + 安装态契约显式化） |
| tag | `v0.2.0`（与 pyproject `version = "0.2.0"` = `src/process_atlas/__init__.py __version__` 一致） |
| 远端 | `git@github.com:yuluo554/10-16-2-process-atlas-skill.git`（public，SSH 通道） |
| 上一版 | `v0.1.0` → `6e7f0ad`（Release 5 附件保持不动，不删不改） |
| 附件清单 | 同 v0.1.0 形态：`report.html`（`examples/report.html`）+ 基准数据四件套 `events.csv` / `events_variants.json` / `manifest.json` / `truth.json`（`data/synthetic/`） |

## 破坏性变更（0.1.0 → 0.2.0 主因）

**`requires-python` 由 `>=3.8` 抬到 `>=3.12`。**

不是偏好，是硬冲突：PEP 639 的 SPDX `license = "MIT"` 字段要求 setuptools ≥ 77，而 setuptools 77+ 的 `requires-python` 为 `>=3.9`（84.0.0 起 `>=3.10`）；3.8 上 pip 只能解析到 setuptools 75.3.2，它对该字段直接报 `ValueError: invalid pyproject.toml config: project.license`。故二者只能二选一，本次选"修 license + 抬 floor"。

实测负控：`py -3.8` venv 中 `pip install -e ".[dev]"` → exit 1（`No matching distribution found for setuptools>=77`）。

## 变更清单

| 类别 | 内容 |
| --- | --- |
| 元数据 | `license = {text = "MIT"}` → `license = "MIT"`（SPDX）；`build-system` `setuptools>=61` → `>=77`。setuptools 84.0.0 下元数据 warning **`[]`**（改前 `['SetuptoolsDeprecationWarning']`），`License-Expression: MIT` |
| 解释器 | `requires-python` `>=3.8` → `>=3.12`；CI 矩阵四格 → 两格（windows/ubuntu × 3.12） |
| CI 卫生 | `actions/checkout@v4` → `@v5`、`actions/setup-python@v5` → `@v6`；新增 `permissions: contents: read` 与 `concurrency`（同 ref 取消旧跑） |
| 安装态契约 | README「不承诺 wheel 安装面」由声明升级为**显式契约 + 可执行断言**：新增 `tests/test_install_surface.py`（3 断言：wheel 无 `data/`、装态 `selftest` exit 1 且点名 `files_present`、`validate` exit 2），由 `tests/conftest.py` 在未设 `PROCESS_ATLAS_INSTALL_SURFACE=1` 时 `collect_ignore`，默认收集数仍 82 |
| 文档同步 | README:13/29/79、`plan/02` 选型与目录注释、`plan/05` 顶部退役说明（历史数字不改）、`plan/06` 新增 D16/D17 |
| 版本 | `0.1.0` → `0.2.0`（`pyproject.toml` + `src/process_atlas/__init__.py`） |

## 不变项（本轮明确未动）

- `mining.py` / `layout.py` / `render.py` / `logio.py` / `selftest.py` / `cli.py` 判定语义：**零改动**。
- `data/synthetic/**` 字节：**零改动**，`--check` 仍「4 files byte-identical」。
- `examples/report.html`：**零改动**，sha256 仍 `2198a12f…417a8`（`build_hash` 由 result+layout 派生，不含 `__version__`，已实证版本号抬升不影响它）。
- 退出码契约 0/1/2：不变（`exit 3` 仍退役，`TestSelftestRetiredNotReady` 三断言仍绿）。
- tag `v0.1.0` 与它的 Release：**未删未改**。

## 附件 sha256（发布前实算，用于对撞）

```
071aa3c3335bc438dbc0a4b8c6b75f52586cadc3bb9abb72c64598b57b4ef07b  events.csv
c21cf053e6b50bb02ab9577d5f0726239f9044671dbf577cc2fb1ed6da6a3fba  events_variants.json
17a97e9f57398b84c722a7d83ef8db21d424f0464e47b850646e59e6fb35e99a  manifest.json
eb1f9051a90d3f9240a2adc4a9b823f639902bf6f9aa69eb39fb47bb577623fb  truth.json
2198a12f2ce75743b6b02e37edaec3651c88bdab33de571ffebf3cb32ca417a8  report.html
```

与 v0.1.0 的 5 个 digest **逐字符一致**（本轮不重打包、不改数据）。

## 发布门禁（发布前实跑）

| 门禁 | 结果 |
| --- | --- |
| `pytest -o addopts="" -q` | `82 passed`，exit 0 |
| `selftest` | `selftest passed: 6 check(s)`，六项全 ok，exit 0 |
| `gen_synthetic_log.py --check` | `4 files byte-identical`，exit 0 |
| `validate` | `validation ok`，exit 0 |

## 待补（发布后回写）

- 本次 commit sha / push 触发的 run id / tag 指向 / Release 页 URL / 真下载复核结果 → 见文末「发布后回写」段。

## 发布后回写（2026-10-20）

| 项 | 值 |
| --- | --- |
| 发布 commit | `7b006b35596a3dace51a904ae82e6ca019034890`（main HEAD） |
| tag | `v0.2.0`（annotated）→ **`7b006b3`**（与发布 commit 同一提交；`git describe --tags --exact-match` = `v0.2.0`） |
| Release 页 | https://github.com/yuluo554/10-16-2-process-atlas-skill/releases/tag/v0.2.0 |
| Release 标记 | `isLatest = true`；`draft = false`；`prerelease = false` |
| 附件数 | **5**（与 v0.1.0 同形态） |

### CI 对账（push 数 = run 数）

| run id | 触发 | 结果 |
| --- | --- | --- |
| 39306725020 | push main（`22b8b18..7b006b3`） | ✅ 2 job 全绿：`test (windows-latest, 3.12)` / `test (ubuntu-latest, 3.12)` |
| 39306861806 | push tag `v0.2.0` | ✅ 2 job 全绿（同上两格） |

- 矩阵已按 DEC1=B 收缩为**两格**（实见 check-run 名称只有 `3.12` 两格，无 `3.8`）。
- **`Node.js 20 is deprecated` 注解 = 0 条**（D2 已消）。check-run annotations 现仅剩平台级 notice：
  `"The ubuntu-latest label will migrate to Ubuntu 26 beginning October 19, 2026."` —— 这是 runner 镜像迁移提示，**不是** action 版本弃用，与 actions/checkout@v5、setup-python@v6 无关。

### 发布物本体已验（真下载复核）

`gh release download v0.2.0` 到 `%TEMP%\rel_verify_v020` 后逐个 `cmp`：

| 附件 | 下载后 sha256 | ↔ 仓库文件 | cmp |
| --- | --- | --- | --- |
| `events.csv` | `071aa3c3…ef07b` | `data/synthetic/events.csv` | **0** |
| `events_variants.json` | `c21cf053…a3fba` | `data/synthetic/events_variants.json` | **0** |
| `manifest.json` | `17a97e9f…5e99a` | `data/synthetic/manifest.json` | **0** |
| `truth.json` | `eb1f9051…23fb` | `data/synthetic/truth.json` | **0** |
| `report.html` | `2198a12f…417a8` | `examples/report.html` | **0** |

**5/5 逐字节一致**；GitHub 侧 `assets[].digest` 与本地实算的 5 个值逐字符相同。

### 「数字可被独立重算」端到端实证

从 GitHub **重新 clone**（`git clone git@github.com:… pa-clone`，检出 `7b006b3` = `v0.2.0`），在新 clone 里建 venv 跑门禁，再用**下载下来的 Release 附件**做源头重算：

- clone 后 `pip install -e ".[dev]"` → 0；`pytest` → `82 passed`；`selftest` → `6 check(s)` 全 ok；
  `--check` → `4 files byte-identical`；`validate` → ok；`process_atlas.__version__` = `0.2.0`。
- `validate <下载的 events.csv>` → exit 0。
- `render <下载的 events.csv> -o recomputed.html` → exit 0，且 `recomputed.html` 与 **下载的 `report.html`** `cmp` **0**，
  其 sha256 = `2198a12f…417a8`。

即：只拿 Release 页上的两个附件（日志 + 报告），任何人都能用本仓代码重算出**完全相同的 HTML**。

### 未改动项确认

- tag `v0.1.0`（→ `6e7f0ad`）与其 Release（5 附件）**未删、未改、未重传**；`gh release list` 仍见两条，旧版 `isLatest = false`。

