"""Deterministic layered layout (Sugiyama-style simplified), M3 module.

Conventions (plan/03 M3; plan/02 D2, D4):
  - Layer = longest-path layer over the DFG graph (Kahn order). Back edges
    (cycle-closing edges detected by a deterministic DFS) and self-loops are
    excluded from layering, so cyclic logs still layer deterministically.
  - Within a layer, activities are ordered lexicographically.
  - Coordinates: x = layer * LAYER_GAP, y = order_in_layer * NODE_GAP.
    All integer pixels; no floating point, no randomness, no clock (K2/K3).

Output schema: {activity: {"x": int, "y": int, "layer": int}}.
Pure stdlib only.
"""

import heapq

LAYER_GAP = 240
NODE_GAP = 100


def compute_layout(nodes, edges):
    """Layer `nodes` by longest-path level over `edges` (excluding back edges).

    nodes: iterable of activity names; edges: iterable of (from, to) pairs.
    Returns {activity: {"x", "y", "layer"}} with integer coordinates.
    """
    node_list = sorted(set(nodes))
    node_set = set(node_list)
    edge_set = sorted(set((f, t) for f, t in edges if f != t and f in node_set and t in node_set))
    back = _back_edges(node_list, edge_set)
    dag_edges = [e for e in edge_set if e not in back]
    layers = _longest_path_layers(node_list, dag_edges)

    by_layer = {}
    for name in node_list:
        by_layer.setdefault(layers[name], []).append(name)

    pos = {}
    for layer_no in sorted(by_layer):
        for order, name in enumerate(sorted(by_layer[layer_no])):
            pos[name] = {"x": layer_no * LAYER_GAP, "y": order * NODE_GAP, "layer": layer_no}
    return pos


def _back_edges(node_list, edge_set):
    """Cycle-closing edges via DFS; node/neighbor order fixed (lex) for determinism."""
    succs = {}
    for f, t in edge_set:
        succs.setdefault(f, []).append(t)
    for k in succs:
        succs[k].sort()

    color = dict((n, 0) for n in node_list)  # 0 white, 1 gray (on stack), 2 black
    back = set()
    for root in node_list:
        if color[root] != 0:
            continue
        color[root] = 1
        stack = [(root, iter(succs.get(root, ())))]
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                color[node] = 2
                stack.pop()
            elif color[nxt] == 1:
                back.add((node, nxt))
            elif color[nxt] == 0:
                color[nxt] = 1
                stack.append((nxt, iter(succs.get(nxt, ()))))
    return back


def _longest_path_layers(node_list, dag_edges):
    """layer(v) = longest path length from any source (Kahn with heap queue)."""
    succs = dict((n, []) for n in node_list)
    indeg = dict((n, 0) for n in node_list)
    for f, t in dag_edges:
        succs[f].append(t)
        indeg[t] += 1
    layer = dict((n, 0) for n in node_list)
    heap = [n for n in node_list if indeg[n] == 0]
    heapq.heapify(heap)
    while heap:
        u = heapq.heappop(heap)
        for v in succs[u]:
            if layer[u] + 1 > layer[v]:
                layer[v] = layer[u] + 1
            indeg[v] -= 1
            if indeg[v] == 0:
                heapq.heappush(heap, v)
    return layer
