# RELEASE-M6 发布留档（2026-10-17）

## 发布基本信息

| 项 | 值 |
| --- | --- |
| 发布时间 | 2026-10-17（UTC ~11:53 / 本地 ~19:53） |
| 发布 commit | `6e7f0ad`（main HEAD，M5 交付文档） |
| tag | `v0.1.0`（与 pyproject version = "0.1.0" 一致） |
| 远端 | `git@github.com:yuluo554/10-16-2-process-atlas-skill.git`（public） |
| Release 页 | https://github.com/yuluo554/10-16-2-process-atlas-skill/releases/tag/v0.1.0 |
| 附件清单 | `report.html`（examples/report.html）+ 基准数据四件套 `events.csv` / `events_variants.json` / `manifest.json` / `truth.json`（data/synthetic/） |

## CI 对账（push 数 = run 数）

| run id | 触发 | 结果 |
| --- | --- | --- |
| 39000360506 | push main（首推） | ✅ 四矩阵全绿：ubuntu×3.8（18s）/ ubuntu×3.12（11s）/ windows×3.12（25s）/ windows×3.8（1m4s） |

- 首推 1 次 = run 1 个，对账通过；首轮即绿，D8 预留的诊断预算未动用（预置≠跑过 → 本轮已实跑验证）。
- tag push（v0.1.0）未触发 CI（workflow 无 tag 触发器），不计入对账。
- 注：CI 有 Node.js 20 deprecation 警告（actions/checkout@v4、setup-python@v5），非失败，留待后续升级 action 版本。

## 网络通道备注（本机环境坑追加）

- HTTPS 443 直连 github.com 在本机被阻断（git push / curl 均超时；`https://api.github.com` 与 SSH 22 反而可达）。
- 解决：建仓/Release/下载均走 `gh` API（HTTPS api.github.com）；git push 走 SSH remote（`git@github.com:...`）。
- 后续本仓 push 一律走 SSH 通道。

## 发布物本体已验（真下载复核）

按 HANDOFF-M6 要求执行了真实下载（`gh release download` 到 `$TEMP/rel_verify`），5 个附件与仓内文件逐字节 `cmp` 比对：

- `report.html` ↔ `examples/report.html`：逐字节一致 ✅
- `events.csv` / `events_variants.json` / `manifest.json` / `truth.json` ↔ `data/synthetic/` 同名文件：逐字节一致 ✅（ALL_BYTE_IDENTICAL=1）

## HANDOFF 链自查

M1→M2→M3→M4→M5→M6 六节齐（plan/HANDOFF-M1..M6.md 全部在位），无断链。M6 为终点棒，本文件即发布留档。

## DoD checklist 对账（HANDOFF-M6 §5）

- [x] 远端已建 + main 首推成功（SSH 通道）
- [x] 四矩阵 CI 全绿；push 数 = run 数（1=1，run 39000360506）
- [x] tag v0.1.0 + GitHub Release，附件（HTML + 基准数据）真下载复核逐字节一致
- [x] plan/RELEASE-M6.md 留档入库；HANDOFF 链 M1–M6 无断链
- [x] plan/00·05·06 回写 ✅；自评表发布栏复核；提交 + push（见 M6 收尾 commit）
