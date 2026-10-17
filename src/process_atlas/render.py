"""Zero-CDN single-file HTML renderer (M3 module).

Discipline (plan/02 §3, plan/03 M3):
  - Template = string.Template only; all JS is inline expression layer that
    consumes pre-computed coordinates/counts (no numbers computed in JS, D4).
  - build_hash derives from report content (sha256 over canonical JSON of the
    mined result + layout); no clock / timestamp ever enters the HTML (K2).
  - assert_no_external_resources runs at every render() exit — not only in
    tests: bans http(s)://, protocol-relative //src, and any external
    <link>/<script src>.

Pure stdlib only.
"""

import hashlib
import json
import os
from string import Template

try:
    from . import layout
except ImportError:  # pragma: no cover - direct path-based load
    import layout


_EDGE_WIDTH_BASE = 1.0
_EDGE_WIDTH_SCALE = 0.6  # px per edge count unit, capped below
_EDGE_WIDTH_MAX = 8.0
_NODE_FREQ_MAX_W = 140.0  # node bar max width for frequency label scaling


def build_hash(result, layout_map):
    """Content-derived version identifier (16 hex); no clock, K2."""
    payload = json.dumps(
        {"result": result, "layout": layout_map},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def render(result):
    """Mine-result dict -> complete single-file HTML string (deterministic)."""
    layout_map = layout.compute_layout(result["nodes"], [(e["from"], e["to"]) for e in result["edges"]])
    node_freq = _node_frequencies(result)
    svg = _render_svg(result, layout_map, node_freq)
    bars = _render_variant_bars(result)
    stats = _render_stats_cards(result)
    data_blob = json.dumps(
        {
            "nodes": result["nodes"],
            "edges": result["edges"],
            "layout": layout_map,
            "nodeFreq": node_freq,
            "variants": result["variants"],
            "bottlenecks": result["bottlenecks"],
            "caseStats": result["case_stats"],
            "caseCount": result["case_count"],
            "buildHash": build_hash(result, layout_map),
        },
        sort_keys=True, ensure_ascii=False,
    )
    html = _TEMPLATE.substitute(
        svg=svg,
        variant_bars=bars,
        stats_cards=stats,
    )
    html = html.replace("__PA_DATA__", data_blob)
    assert_no_external_resources(html)
    return html


def write_report(result, path):
    """Render to file: UTF-8, LF endings, trailing newline (K2/K6)."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    html = render(result)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    return html


# ---------- zero-CDN hard assertion (resident at render exit) ----------


def assert_no_external_resources(html):
    """Raise AssertionError if the HTML references any external resource."""
    low = html.lower()
    for scheme in ("http://", "https://", "ftp://"):
        assert scheme not in low, "external resource found: %s" % scheme
    assert "<link" not in low, "external <link> tag found (all CSS must be inline)"
    # Any <script src=...> is external by construction (all JS is inline here).
    idx = low.find("<script")
    while idx != -1:
        tag_end = low.find(">", idx)
        tag = low[idx:tag_end if tag_end != -1 else len(low)]
        assert "src" not in tag.split("type=")[0], "external <script src> found"
        idx = low.find("<script", idx + 1)
    # Protocol-relative references in src/href/url(...) attributes.
    for marker in ("src=\"//", "href=\"//", "url(//", "url('//", "url(\"//"):
        assert marker not in low, "protocol-relative reference found: %s" % marker


# ---------- piece renderers (all deterministic) ----------


def _node_frequencies(result):
    """Activity -> event count, over edges is insufficient (start/end acts);
    recompute from variants: sum of seq occurrences weighted by variant count."""
    freq = dict((n, 0) for n in result["nodes"])
    for v in result["variants"]:
        for act in v["seq"]:
            freq[act] += v["count"]
    return freq


def _edge_width(count, max_count):
    if max_count <= 0:
        return _EDGE_WIDTH_BASE
    w = _EDGE_WIDTH_BASE + _EDGE_WIDTH_SCALE * count
    return round(min(w, _EDGE_WIDTH_MAX), 1)


def _escape(text):
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _render_svg(result, layout_map, node_freq):
    edges = result["edges"]
    max_count = max((e["count"] for e in edges), default=0)
    xs = [p["x"] for p in layout_map.values()] or [0]
    ys = [p["y"] for p in layout_map.values()] or [0]
    width = max(xs) + layout.LAYER_GAP
    height = max(ys) + layout.NODE_GAP + 60

    parts = []
    parts.append(
        '<svg id="dfg-svg" viewBox="0 0 %d %d" width="100%%" '
        'preserveAspectRatio="xMinYMin meet" role="img" aria-label="DFG">' % (width, height)
    )
    parts.append(
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#8a94a6"/></marker></defs>'
    )
    edge_keys = {}
    for e in sorted(edges, key=lambda e: (e["from"], e["to"])):
        a, b = layout_map[e["from"]], layout_map[e["to"]]
        w = _edge_width(e["count"], max_count)
        key = "edge:%s>%s" % (e["from"], e["to"])
        edge_keys[key] = e
        parts.append(
            '<line class="dfg-edge" data-edge="%s" x1="%d" y1="%d" x2="%d" y2="%d" '
            'stroke="#8a94a6" stroke-width="%s" marker-end="url(#arrow)"/>'
            % (_escape(key), a["x"] + 40, a["y"] + 20, b["x"] + 40, b["y"] + 20, w)
        )
    for name in result["nodes"]:
        p = layout_map[name]
        cx, cy = p["x"] + 40, p["y"] + 20
        key = "node:%s" % name
        parts.append('<g class="dfg-node" data-node="%s" transform="translate(%d,%d)">'
                     % (_escape(name), cx - 40, cy - 20))
        parts.append('<rect x="0" y="0" rx="10" ry="10" width="80" height="40" '
                     'fill="#eef2f7" stroke="#4a5a77" stroke-width="1.5"/>')
        parts.append('<text x="40" y="18" text-anchor="middle" class="node-name">%s</text>'
                     % _escape(name))
        parts.append('<text x="40" y="33" text-anchor="middle" class="node-freq">%d 次</text>'
                     % node_freq[name])
        parts.append('<title>%s · %d 次</title>' % (_escape(name), node_freq[name]))
        parts.append('</g>')
    parts.append('</svg>')
    return "".join(parts)


def _render_variant_bars(result):
    total = float(result["case_count"])
    parts = []
    for v in result["variants"]:
        pct = v["ratio"] * 100.0
        parts.append(
            '<div class="variant-row">'
            '<span class="variant-rank">#%d</span>'
            '<span class="variant-seq">%s</span>'
            '<span class="variant-bar-track">'
            '<span class="variant-bar" data-variant="%d" style="width:%s%%" '
            'title="%d cases · %s%%"></span></span>'
            '<span class="variant-count">%d · %s%%</span>'
            '</div>'
            % (
                v["rank"],
                _escape(" → ".join(v["seq"])),
                v["rank"],
                _fmt_num(pct),
                v["count"],
                _fmt_num(pct),
                v["count"],
                _fmt_num(pct),
            )
        )
    return "".join(parts)


def _render_stats_cards(result):
    cards = [
        ("case 数", result["case_count"]),
        ("活动数", len(result["nodes"])),
        ("边数", len(result["edges"])),
        ("变体数", len(result["variants"])),
        ("案例时长中位数", "%ss" % _fmt_num(result["case_stats"]["median_s"])),
        ("案例时长 P95", "%ss" % _fmt_num(result["case_stats"]["p95_s"])),
    ]
    parts = []
    for label, value in cards:
        parts.append(
            '<div class="stat-card"><div class="stat-value">%s</div>'
            '<div class="stat-label">%s</div></div>' % (_escape(str(value)), _escape(label))
        )
    return "".join(parts)


def _fmt_num(x):
    s = ("%.3f" % x).rstrip("0").rstrip(".")
    return s if s else "0"


_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<title>流程发现图报告 · Process Atlas</title>
<style>
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", "Microsoft YaHei", sans-serif; margin: 0;
       background: #f7f9fc; color: #24324a; }
header { padding: 20px 32px; background: #24324a; color: #fff; }
header h1 { margin: 0 0 4px; font-size: 20px; }
header .meta { font-size: 12px; opacity: .75; }
main { max-width: 1100px; margin: 0 auto; padding: 24px 32px 64px; }
section { margin-bottom: 36px; }
h2 { font-size: 16px; border-left: 4px solid #4a5a77; padding-left: 10px; }
.stats { display: flex; flex-wrap: wrap; gap: 12px; }
.stat-card { background: #fff; border: 1px solid #dde4ee; border-radius: 8px;
             padding: 12px 20px; min-width: 130px; }
.stat-value { font-size: 22px; font-weight: 600; color: #24324a; }
.stat-label { font-size: 12px; color: #6b7a94; margin-top: 2px; }
.graph-panel { background: #fff; border: 1px solid #dde4ee; border-radius: 8px;
               padding: 16px; overflow-x: auto; }
.dfg-node { cursor: pointer; }
.dfg-node rect { transition: fill .15s; }
.dfg-node:hover rect { fill: #d7e3f4; }
.dfg-node.dim { opacity: .25; }
.dfg-edge.dim { opacity: .12; }
.node-name { font-size: 12px; fill: #24324a; }
.node-freq { font-size: 10px; fill: #6b7a94; }
.variant-row { display: flex; align-items: center; gap: 10px; margin: 6px 0; font-size: 12px; }
.variant-rank { width: 34px; color: #6b7a94; flex: none; }
.variant-seq { width: 300px; flex: none; overflow: hidden; text-overflow: ellipsis;
               white-space: nowrap; }
.variant-bar-track { flex: 1; background: #e8edf5; border-radius: 4px; height: 14px; }
.variant-bar { display: block; height: 14px; border-radius: 4px;
               background: #4a7dc9; min-width: 2px; }
.variant-count { width: 120px; flex: none; color: #6b7a94; text-align: right; }
#tooltip { position: fixed; display: none; pointer-events: none; z-index: 10;
           background: #24324a; color: #fff; font-size: 12px; padding: 8px 10px;
           border-radius: 6px; max-width: 320px; line-height: 1.5; }
footer { font-size: 11px; color: #8a94a6; padding: 0 32px 40px; }
</style>
</head>
<body>
<header>
  <h1>流程发现图报告</h1>
  <div class="meta">确定性单文件报告 · 零外部请求 · build <span id="build-hash"></span></div>
</header>
<main>
<section>
  <h2>汇总统计</h2>
  <div class="stats">$stats_cards</div>
</section>
<section>
  <h2>流程图（DFG）</h2>
  <div class="graph-panel">$svg</div>
  <p style="font-size:12px;color:#6b7a94">悬停节点/边查看等待统计；点击节点高亮相关变体。</p>
</section>
<section>
  <h2>变体热力条（Top-N，按 case 占比）</h2>
  <div id="variant-list">$variant_bars</div>
</section>
</main>
<footer>所有数字由确定性代码离线计算并内嵌本文件；本页面发起零外部网络请求。</footer>
<div id="tooltip"></div>
<script type="application/json" id="pa-data">__PA_DATA__</script>
<script>
(function () {
  "use strict";
  var data = JSON.parse(document.getElementById("pa-data").textContent);
  document.getElementById("build-hash").textContent = data.buildHash;
  var tip = document.getElementById("tooltip");

  function edgeInfoRaw(from, to) {
    for (var i = 0; i < data.edges.length; i++) {
      var e = data.edges[i];
      if (e.from === from && e.to === to) { return e; }
    }
    return null;
  }
  function bottleneckOf(from, to) {
    for (var i = 0; i < data.bottlenecks.length; i++) {
      var b = data.bottlenecks[i];
      if (b.from === from && b.to === to) { return b; }
    }
    return null;
  }
  function variantsTouching(activity) {
    var hits = [];
    for (var i = 0; i < data.variants.length; i++) {
      var v = data.variants[i];
      for (var j = 0; j < v.seq.length; j++) {
        if (v.seq[j] === activity) { hits.push(v); break; }
      }
    }
    return hits;
  }

  function showTip(html, x, y) {
    tip.innerHTML = html;
    tip.style.display = "block";
    tip.style.left = (x + 14) + "px";
    tip.style.top = (y + 14) + "px";
  }
  function hideTip() { tip.style.display = "none"; }

  var nodes = document.querySelectorAll(".dfg-node");
  var edges = document.querySelectorAll(".dfg-edge");

  nodes.forEach(function (n) {
    var name = n.getAttribute("data-node");
    n.addEventListener("mousemove", function (ev) {
      var freq = data.nodeFreq[name];
      var hits = variantsTouching(name);
      var lines = ["<b>" + name + "</b> · " + freq + " 次",
                   "相关变体 " + hits.length + " 个"];
      showTip(lines.join("<br/>"), ev.clientX, ev.clientY);
    });
    n.addEventListener("mouseleave", hideTip);
    n.addEventListener("click", function () {
      var active = n.classList.contains("active");
      nodes.forEach(function (m) { m.classList.remove("dim", "active"); });
      edges.forEach(function (m) { m.classList.remove("dim"); });
      document.querySelectorAll(".variant-bar").forEach(function (b) {
        b.style.outline = "";
      });
      if (active) { return; }
      n.classList.add("active");
      var hits = variantsTouching(name);
      var keep = {};
      hits.forEach(function (v) {
        for (var j = 0; j < v.seq.length - 1; j++) {
          keep[v.seq[j] + ">" + v.seq[j + 1]] = 1;
        }
      });
      nodes.forEach(function (m) {
        var nm = m.getAttribute("data-node");
        var inHit = hits.some(function (v) { return v.seq.indexOf(nm) !== -1; });
        if (!inHit) { m.classList.add("dim"); }
      });
      edges.forEach(function (m) {
        var key = m.getAttribute("data-edge").slice(5);
        if (!keep[key]) { m.classList.add("dim"); }
      });
      hits.forEach(function (v) {
        var bar = document.querySelector('.variant-bar[data-variant="' + v.rank + '"]');
        if (bar) { bar.style.outline = "2px solid #24324a"; }
      });
    });
  });

  edges.forEach(function (m) {
    m.addEventListener("mousemove", function (ev) {
      var key = m.getAttribute("data-edge").slice(5);
      var sep = key.indexOf(">");
      var from = key.slice(0, sep), to = key.slice(sep + 1);
      var e = edgeInfoRaw(from, to);
      if (!e) { return; }
      var b = bottleneckOf(from, to);
      var lines = ["<b>" + from + " → " + to + "</b>",
                   "频次 " + e.count];
      if (b) {
        lines.push("等待中位数 " + b.median_wait_s + "s · P95 " + b.p95_wait_s + "s");
      }
      showTip(lines.join("<br/>"), ev.clientX, ev.clientY);
    });
    m.addEventListener("mouseleave", hideTip);
  });
})();
</script>
</body>
</html>
""")
