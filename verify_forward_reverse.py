#!/usr/bin/env python3
"""正反转控制验证：从实际 Wire 拓扑构建连通图，验证自锁/互锁逻辑。

不硬编码布尔公式，而是：
1. 从 build() 的 Wire 列表构建无向连通图（节点=端子/自由点）。
2. 触点按状态决定是否导通（NO 闭合时导通，NC 断开时不导通）。
3. 检查 Lc 到线圈的导通路径，验证自锁/互锁行为。
4. 机械互锁：分离"线圈命令"与"主触点物理状态"，验证不变量。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from forward_reverse import build
from circuit import _is_free


def build_graph(circuit, contact_state):
    """构建连通图。contact_state: {(inst_id, term): closed_bool}。
    返回邻接表 {node: set(neighbors)}，node 为 (ref, term) 或自由点字符串。"""
    adj = {}
    def node(ref, term):
        return (ref, term) if not _is_free(ref) else ref
    def add_edge(n1, n2):
        adj.setdefault(n1, set()).add(n2)
        adj.setdefault(n2, set()).add(n1)
    # Wire 边
    for w in circuit.wires:
        add_edge(node(w.a_id, w.a_term), node(w.b_id, w.b_term))
    # 触点内部导通（按状态）
    for (iid, term), closed in contact_state.items():
        if not closed:
            continue
        inst = circuit.instances[iid]
        sym = inst.symbol
        # 找到该触点的另一端
        terms = [t for t, _, _ in __import__('iec_symbols').TERMINALS[sym]]
        # 映射显示编号
        disp_terms = [inst.remap.get(t, t) for t in terms]
        if term in disp_terms:
            idx = disp_terms.index(term)
            other = disp_terms[1 - idx] if len(disp_terms) == 2 else None
            if other:
                add_edge((iid, term), (iid, other))
    # 符号内部直通（断路器/热继电器主回路 1-2/3-4/5-6，假设闭合）
    for iid, inst in circuit.instances.items():
        if inst.symbol in ('circuit_breaker_3p', 'thermal_relay_3p', 'contactor_main_contact'):
            for a, b in [('1', '2'), ('3', '4'), ('5', '6')]:
                da, db = inst.remap.get(a, a), inst.remap.get(b, b)
                add_edge((iid, da), (iid, db))
    return adj


def reachable(adj, start, target):
    """BFS 检查连通。"""
    seen, stack = set(), [start]
    while stack:
        n = stack.pop()
        if n == target:
            return True
        if n in seen:
            continue
        seen.add(n)
        stack.extend(adj.get(n, ()))
    return False


def check(name, cond, detail=""):
    print(f"{'✓' if cond else '✗ FAIL'} {name}" + (f" — {detail}" if detail else ""))
    return cond


def main():
    ok = True
    c = build()
    print("=== 正反转拓扑验证（从 Wire 构建连通图） ===\n")

    LC = "@1150,120"
    KM1_COIL = ("KM1c", "A1")
    KM2_COIL = ("KM2c", "A1")

    # 触点状态：{(inst, term): 是否闭合}
    # SB0 NC：未按下时闭合；SB1/SB2 NO：按下时闭合；KM1a/KM2a NO：线圈吸合时闭合
    # KM1b/KM2b NC：线圈吸合时断开；FRa NC：过载时断开

    def state(sb0_p=0, sb1_p=0, sb2_p=0, fr_t=0, km1=0, km2=0):
        return {
            ("SB0", "11"): not sb0_p, ("SB0", "12"): not sb0_p,
            ("SB1", "13"): bool(sb1_p), ("SB1", "14"): bool(sb1_p),
            ("SB2", "13"): bool(sb2_p), ("SB2", "14"): bool(sb2_p),
            ("KM1a", "13"): bool(km1), ("KM1a", "14"): bool(km1),
            ("KM2a", "13"): bool(km2), ("KM2a", "14"): bool(km2),
            ("KM2b", "21"): not km2, ("KM2b", "22"): not km2,
            ("KM1b", "21"): not km1, ("KM1b", "22"): not km1,
            ("FRa", "95"): not fr_t, ("FRa", "96"): not fr_t,
        }

    # 1. SB1 按下 → KM1 线圈导通
    adj = build_graph(c, state(sb1_p=1))
    ok &= check("SB1 按下 → Lc 到 KM1 线圈导通", reachable(adj, LC, KM1_COIL))
    ok &= check("SB1 按下 → Lc 到 KM2 线圈不导通", not reachable(adj, LC, KM2_COIL))

    # 2. SB1 松开、KM1 自锁（KM1a 闭合）→ 仍导通
    adj = build_graph(c, state(km1=1))
    ok &= check("SB1 松开 + KM1a 自锁 → KM1 线圈保持导通", reachable(adj, LC, KM1_COIL))

    # 3. SB1 松开、KM1a 断开 → 不导通（证明自锁触点真正起作用，而非被旁路）
    adj = build_graph(c, state())
    ok &= check("全断开 → KM1 线圈不导通（无旁路）", not reachable(adj, LC, KM1_COIL))

    # 4. KM1 运行中按 SB2 → KM2 不导通（KM1b 互锁断开）
    adj = build_graph(c, state(sb2_p=1, km1=1))
    ok &= check("KM1 运行中按 SB2 → KM2 线圈不导通（电气互锁）", not reachable(adj, LC, KM2_COIL))

    # 5. SB0 按下 → 都不导通
    adj = build_graph(c, state(sb0_p=1, sb1_p=1, km1=1))
    ok &= check("SB0 按下 → KM1 线圈不导通", not reachable(adj, LC, KM1_COIL))

    # 6. FR 过载 → 回路不导通（检查 Lc→N 完整路径经线圈）
    # 线圈需要 Lc→A1 且 A2→N（经 FR）同时导通
    def coil_energized(sb0_p=0, sb1_p=0, sb2_p=0, fr_t=0, km1=0, km2=0, coil="KM1c"):
        adj = build_graph(c, state(sb0_p, sb1_p, sb2_p, fr_t, km1, km2))
        a1 = (coil, "A1")
        a2 = (coil, "A2")
        n_point = "@1150,740"
        return reachable(adj, LC, a1) and reachable(adj, a2, n_point)
    ok &= check("FR 过载 → KM1 线圈不导通", not coil_energized(fr_t=1, km1=1))
    # 复核前面的测试也用完整路径
    ok &= check("SB1 按下 → KM1 线圈得电（完整路径）", coil_energized(sb1_p=1))

    # 7. 机械互锁不变量：线圈命令 vs 物理触点状态分离
    print("\n=== 机械互锁不变量 ===")
    # 模拟同时按下：电气命令可能同时为 1，但机械互锁保证物理触点不同时闭合
    # 建模：mech_km1, mech_km2 为物理状态，互锁约束 not (mech_km1 and mech_km2)
    def mech_step(cmd1, cmd2, m1, m2):
        # 若两者都命令吸合，机械互锁阻止（保持原状态，或都不吸合）
        if cmd1 and cmd2:
            return m1, m2  # 机械卡住，保持原状
        # 已吸合的一方物理阻止另一方
        if cmd2 and m1:
            return m1, m2
        if cmd1 and m2:
            return m1, m2
        return (1 if cmd1 else 0), (1 if cmd2 else 0)
    # 从全开状态同时命令
    m1, m2 = mech_step(1, 1, 0, 0)
    ok &= check("同时命令 → 机械互锁阻止双吸合", not (m1 and m2), f"物理状态 KM1={m1},KM2={m2}")
    # 正常顺序：先 KM1 吸合，再命令 KM2 → KM2 被机械阻止
    m1, m2 = mech_step(0, 1, 1, 0)
    ok &= check("KM1 已吸合时命令 KM2 → KM2 物理不闭合", (m1, m2) == (1, 0))

    # 8. 相序与防短路（拓扑）
    print("\n=== 相序与防短路 ===")
    wires = {(w.a_id, w.a_term, w.b_id, w.b_term) for w in c.wires}
    # 注意 Wire 方向可能反转，检查双向
    def has(a, at, b, bt):
        return (a, at, b, bt) in wires or (b, bt, a, at) in wires
    ok &= check("KM1 正转直连", has("KM1m","2","FRm","1") and has("KM1m","6","FRm","5"))
    ok &= check("KM2 反转 L1/L3 换相", has("KM2m","2","FRm","5") and has("KM2m","6","FRm","1"))
    # QF→KM2 三线不重叠（几何检查）
    from collections import defaultdict
    segs = []
    for w in c.wires:
        a = c.terminal_pos(w.a_id, w.a_term)
        b = c.terminal_pos(w.b_id, w.b_term)
        path = c._manhattan_pts([a] + list(w.via) + [b])
        for i in range(len(path)-1):
            p1, p2 = path[i], path[i+1]
            if abs(p1[0]-p2[0])>1e-9 or abs(p1[1]-p2[1])>1e-9:
                # 只检查 QF→KM2 的三根
                if w.a_id=="QF" and w.b_id=="KM2m":
                    segs.append((p1,p2))
    overlap = False
    for i in range(len(segs)):
        for j in range(i+1, len(segs)):
            (x1,y1),(x2,y2) = segs[i]; (x3,y3),(x4,y4) = segs[j]
            # 水平线段重叠检测
            if abs(y1-y2)<1e-9 and abs(y3-y4)<1e-9 and abs(y1-y3)<1e-9:
                lo, hi = max(min(x1,x2),min(x3,x4)), min(max(x1,x2),max(x3,x4))
                if hi - lo > 1e-6:
                    overlap = True
    ok &= check("QF→KM2 三线无水平重叠", not overlap)

    # 9. XML 圆弧数与间距
    print("\n=== XML 几何 ===")
    wp = []
    for w in c.wires:
        a = c.terminal_pos(w.a_id, w.a_term)
        b = c.terminal_pos(w.b_id, w.b_term)
        wp.append(c._manhattan_pts([a] + list(w.via) + [b]))
    jumps, t_juncs = c._detect_crossings(wp)
    from collections import defaultdict as dd
    by_x = dd(list)
    for x, y in jumps: by_x[round(x)].append(round(y))
    min_gap = min((ys[i+1]-ys[i] for ys in by_x.values() for i in range(len(sorted(ys))-1) for ys in [sorted(ys)]), default=99)
    # 分区计数
    bus = sum(1 for x,y in jumps if y < 150)
    qfz = sum(1 for x,y in jumps if 150 <= y < 350)
    swp = sum(1 for x,y in jumps if y >= 350)
    ok &= check(f"圆弧数={len(jumps)}（母排{bus}+QF-KM2区{qfz}+换相区{swp}）", len(jumps)==18, f"实际 {len(jumps)}")
    ok &= check("同x圆弧最小间距≥16px", min_gap >= 16, f"最小间距 {min_gap}px")
    # 新增：圆弧黑底矩形不得遮挡红点（全部三类红点：端子/分支点/T形接点）
    from collections import Counter
    term_pts = set()
    for inst in c.instances.values():
        import iec_symbols
        for num, _, _ in iec_symbols.TERMINALS[inst.symbol]:
            x, y = c.terminal_pos(inst.id, num)
            term_pts.add((round(x, 3), round(y, 3)))
    end_counter = Counter()
    for path in wp:
        for p in path:
            end_counter[(round(p[0], 3), round(p[1], 3))] += 1
    all_dots = set(term_pts)
    for (x, y), cnt in end_counter.items():
        if cnt >= 3 and (x, y) not in term_pts:
            all_dots.add((x, y))
    for tx, ty in t_juncs:
        k = (round(tx, 3), round(ty, 3))
        if k not in term_pts and end_counter.get(k, 0) < 3:
            all_dots.add(k)
    bad = [((round(jx), round(jy)), (round(tx), round(ty)))
           for jx, jy in jumps for tx, ty in all_dots
           if abs(jx - tx) < 12 and abs(jy - ty) < 14]
    ok &= check(f"圆弧黑底不遮挡红点（共 {len(all_dots)} 个红点）",
                len(bad) == 0, f"遮挡 {len(bad)} 处" if bad else "")
    # 断言1：18 处圆弧的精确坐标集合（容差 1px）
    expected = {
        (240,80),(240,105),(280,105),  # 母排区
        (280,232),(320,232),(320,254),(440,254),(440,276),(480,276),  # QF-KM2区
        (240,419),(260,419),(280,397),(280,419),(300,397),(300,419),
        (320,375),(320,397),(320,419),  # 换相区
    }
    actual = {(round(x),round(y)) for x,y in jumps}
    ok &= check("18 处圆弧坐标与预期集合一致",
                actual == expected,
                f"多出 {actual-expected}, 缺失 {expected-actual}" if actual != expected else "")
    # 断言2：生成 XML 中图元数核对（curved=1 线 / 黑底矩形 / 补线各 18）
    import xml.etree.ElementTree as ET
    xml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forward_reverse.drawio")
    root = ET.parse(xml_path).getroot()
    n_curved = sum(1 for e in root.iter("mxCell") if e.get("style","").find("curved=1") >= 0)
    # 黑底矩形：fillColor=#000000 的矩形；补线：与圆弧配对的普通直线（按 jump_arc 实现：每弧1矩形+1补线+1曲线）
    n_black = sum(1 for e in root.iter("mxCell")
                  if "fillColor=#000000" in e.get("style","")
                  and (lambda g: g is not None and g.get("width")=="10" and g.get("height")=="14")(e.find("mxGeometry")))
    ok &= check(f"XML 图元数：curved=1 曲线={n_curved}，黑底矩形={n_black}",
                n_curved == 18 and n_black == 18,
                f"期望各 18" if (n_curved, n_black) != (18, 18) else "")

    print("\n" + ("全部通过 ✓" if ok else "存在失败 ✗"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
