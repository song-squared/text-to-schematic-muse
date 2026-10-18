"""text-to-schematic-muse 公共几何验证库

从 direct_start / forward_reverse / star_delta 三轮挑战的审查教训中抽出。
新电路的 verify 脚本应复用本库，而不是各自重写几何检查。

核心教训：时序仿真通过 ≠ 接线正确。必须检查实际 Wire 几何。
"""
from collections import defaultdict


# ---------------------------------------------------------------------------
# 基础：线段
# ---------------------------------------------------------------------------
def segs_of_wire(circuit, w):
    """Wire 的实际几何线段（含 via 的曼哈顿路径）。"""
    a = circuit.terminal_pos(w.a_id, w.a_term)
    b = circuit.terminal_pos(w.b_id, w.b_term)
    path = circuit._manhattan_pts([a] + list(w.via) + [b])
    return [(path[i], path[i + 1]) for i in range(len(path) - 1)]


def all_segs(circuit, x_min=None):
    """电路所有 Wire 的几何线段。x_min 过滤（如只看控制回路）。"""
    out = []
    for w in circuit.wires:
        a = circuit.terminal_pos(w.a_id, w.a_term)
        if x_min is not None and a[0] < x_min:
            continue
        out.extend(segs_of_wire(circuit, w))
    return out


# ---------------------------------------------------------------------------
# 几何分割：在 T 形交点 / 端点触中段 / X 形交叉处分裂线段
# ---------------------------------------------------------------------------
def split_at_intersections(segs):
    def pt_on_seg(px, py, s, margin=0.6):
        (x1, y1), (x2, y2) = s
        if abs(x1 - x2) < 1e-9:
            return abs(px - x1) < margin and min(y1, y2) + margin < py < max(y1, y2) - margin
        if abs(y1 - y2) < 1e-9:
            return abs(py - y1) < margin and min(x1, x2) + margin < px < max(x1, x2) - margin
        return False

    cuts = {}
    all_pts = [(x, y) for s in segs for x, y in s]
    for i, s in enumerate(segs):
        for px, py in all_pts:
            if pt_on_seg(px, py, s):
                cuts.setdefault(i, []).append((px, py))

    result, xpts = [], []
    for i, ((x1, y1), (x2, y2)) in enumerate(segs):
        pts = [(x1, y1), (x2, y2)] + cuts.get(i, [])
        uniq = []
        for p in pts:
            if not any(abs(p[0] - q[0]) < 0.5 and abs(p[1] - q[1]) < 0.5 for q in uniq):
                uniq.append(p)
        if abs(x1 - x2) >= abs(y1 - y2):
            uniq.sort(key=lambda p: p[0] if x2 >= x1 else -p[0])
        else:
            uniq.sort(key=lambda p: p[1] if y2 >= y1 else -p[1])
        for k in range(len(uniq) - 1):
            if abs(uniq[k][0] - uniq[k + 1][0]) > 0.5 or abs(uniq[k][1] - uniq[k + 1][1]) > 0.5:
                result.append((uniq[k], uniq[k + 1]))

    # X 形交叉点
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            (x1, y1), (x2, y2) = segs[i]
            (x3, y3), (x4, y4) = segs[j]
            if abs(y1 - y2) < 1e-9 and abs(x3 - x4) < 1e-9:
                if min(x1, x2) < x3 < max(x1, x2) and min(y3, y4) < y1 < max(y3, y4):
                    xpts.append((x3, y1))
            elif abs(x1 - x2) < 1e-9 and abs(y3 - y4) < 1e-9:
                if min(x3, x4) < x1 < max(x3, x4) and min(y1, y2) < y3 < max(y1, y2):
                    xpts.append((x1, y3))
    return result, xpts


def build_geo_graph(segs, skip_zone=None):
    """从几何线段建连通图。skip_zone=(cx, y1, y2, r) 跳过该区域（如断开的触点）。"""
    real, xpts = split_at_intersections(segs)
    g = defaultdict(set)

    def in_skip(mx, my):
        if not skip_zone:
            return False
        cx, zy1, zy2, r = skip_zone
        return abs(mx - cx) < r and zy1 <= my <= zy2

    for (x1, y1), (x2, y2) in real:
        if in_skip((x1 + x2) / 2, (y1 + y2) / 2):
            continue
        p1, p2 = (round(x1, 1), round(y1, 1)), (round(x2, 1), round(y2, 1))
        if p1 != p2:
            g[p1].add(p2)
            g[p2].add(p1)
    # X 形交点连通
    for xp, yp in xpts:
        passing = []
        for (x1, y1), (x2, y2) in real:
            if abs(y1 - y2) < 1e-9 and abs(yp - y1) < 1 and min(x1, x2) < xp < max(x1, x2):
                passing.append(((round(x1, 1), round(y1, 1)), (round(x2, 1), round(y2, 1))))
            elif abs(x1 - x2) < 1e-9 and abs(xp - x1) < 1 and min(y1, y2) < yp < max(y1, y2):
                passing.append(((round(x1, 1), round(y1, 1)), (round(x2, 1), round(y2, 1))))
        for a1, a2 in passing:
            g[a1].add(a2)
            g[a2].add(a1)
    return g


def reachable(g, p_from, p_to, tol=2.0):
    """BFS 可达性。"""
    start = (round(p_from[0], 1), round(p_from[1], 1))
    seen, stack = set(), [start]
    while stack:
        n = stack.pop()
        if abs(n[0] - p_to[0]) < tol and abs(n[1] - p_to[1]) < tol:
            return True
        if n in seen:
            continue
        seen.add(n)
        stack.extend(g.get(n, ()))
    return False


# ---------------------------------------------------------------------------
# 元件包络盒：导线不得进入元件内部
# ---------------------------------------------------------------------------
def check_no_intrusion(circuit, boxes, check_fn):
    """boxes: {iid: (cx, cy, half_w, half_h)}。

    只豁免端子连接点 6px 范围，不跳过整条 Wire。
    返回 [(wire_desc, iid)] 入侵列表。
    """
    def point_in_box(px, py, box):
        cx, cy, hw, hh = box
        return abs(px - cx) < hw and abs(py - cy) < hh

    def seg_hits(seg, box, exempt_pts):
        (x1, y1), (x2, y2) = seg
        n = max(2, int(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 / 2))
        for i in range(n + 1):
            t = i / n
            px, py = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
            if any(((px - ex) ** 2 + (py - ey) ** 2) ** 0.5 < 6 for ex, ey in exempt_pts):
                continue
            if point_in_box(px, py, box):
                return True
        return False

    intrusions = []
    for w in circuit.wires:
        exempt = {}
        for iid, term in [(w.a_id, w.a_term), (w.b_id, w.b_term)]:
            if iid in boxes and term:
                try:
                    exempt.setdefault(iid, []).append(circuit.terminal_pos(iid, term))
                except Exception:
                    pass
        for seg in segs_of_wire(circuit, w):
            for iid, box in boxes.items():
                if seg_hits(seg, box, exempt.get(iid, [])):
                    intrusions.append((f"{w.a_id}:{w.a_term}->{w.b_id}:{w.b_term}", iid))
                    break
    for desc, iid in intrusions:
        check_fn(f"入侵: {desc} -> {iid}")
    return intrusions


def check_no_border_overlap(circuit, boxes, check_fn, tol=4.0):
    """检测导线沿元件边框共线重合（如压在线圈边框上）。

    boxes: {iid: (cx, cy, half_w, half_h)}。
    返回 [(wire_desc, iid, overlap_px)]。
    """
    overlaps = []
    for w in circuit.wires:
        # 跳过连接到该元件的 wire（正常引出线）
        for seg in segs_of_wire(circuit, w):
            (x1, y1), (x2, y2) = seg
            for iid, (cx, cy, hw, hh) in boxes.items():
                if iid in (w.a_id, w.b_id):
                    continue
                # 检查是否与左右边框共线重合
                for bx in (cx - hw, cx + hw):
                    if abs(x1 - bx) < tol and abs(x2 - bx) < tol:
                        oy1, oy2 = max(min(y1, y2), cy - hh), min(max(y1, y2), cy + hh)
                        if oy2 - oy1 > 10:  # 重合超过 10px 才报
                            overlaps.append(
                                (f"{w.a_id}:{w.a_term}->{w.b_id}:{w.b_term}",
                                 iid, round(oy2 - oy1)))
                # 检查是否与上下边框共线重合
                for by in (cy - hh, cy + hh):
                    if abs(y1 - by) < tol and abs(y2 - by) < tol:
                        ox1, ox2 = max(min(x1, x2), cx - hw), min(max(x1, x2), cx + hw)
                        if ox2 - ox1 > 10:
                            overlaps.append(
                                (f"{w.a_id}:{w.a_term}->{w.b_id}:{w.b_term}",
                                 iid, round(ox2 - ox1)))
    seen = set()
    uniq = []
    for o in overlaps:
        k = (o[0], o[1])
        if k not in seen:
            seen.add(k); uniq.append(o)
    for desc, iid, px in uniq:
        check_fn(f"边框重合: {desc} 沿 {iid} 边框 {px}px")
    return uniq


# ---------------------------------------------------------------------------
# 触点断开测试：指定触点断开时，A 点到 B 点不可达
# ---------------------------------------------------------------------------
def check_open_blocks(circuit, src_pts, dst_pt, skip_zone, label, check_fn, x_min=None):
    """src_pts: [(x,y)] 起点列表；skip_zone: 断开区域；dst_pt: 终点。

    断开 skip_zone 后，所有起点到终点都应不可达。
    """
    g = build_geo_graph(all_segs(circuit, x_min=x_min), skip_zone=skip_zone)
    bad = [s for s in src_pts if reachable(g, s, dst_pt)]
    for s in bad:
        check_fn(f"{label}: {s} 绕过断开点到达 {dst_pt}")
    return bad


# ---------------------------------------------------------------------------
# 故障注入：验证检测能力
# ---------------------------------------------------------------------------
def fault_injection_test(circuit, inject_segs, src_pt, dst_pt, skip_zone,
                         label, x_min=None):
    """注入旁路线段后，src→dst 应变为可达（证明检测器能抓到旁路）。

    返回 True 表示检测器正常工作（注入被检出）。
    """
    base = all_segs(circuit, x_min=x_min)
    g = build_geo_graph(base + inject_segs, skip_zone=skip_zone)
    return reachable(g, src_pt, dst_pt)
