#!/usr/bin/env python3
"""星-三角降压启动验证：时间状态模型 + 电气拓扑。

时间模型：离散事件仿真，状态 = (km1, km2, km3, t_kt1, t_kt2)。
  KM1 = ~SB0 & (SB1 | KM1) & ~FR
  KT1/KT2 随 KM1 得电计时；KM1 失电则计时清零。
  KM2 = KM1 & ~KT1_5s & ~KM3 & ~FR        # 星形：KT1 延时 NC(5s) 断开
  KM3 = KM1 & KT2_5_5s & ~KM2 & ~FR       # 三角：KT2 延时 NO(5.5s) 闭合
机械互锁：KM2/KM3 物理触点不同时闭合（独立不变量检查）。

短路检查：电机绕组（U1-U2/V1-V2/W1-W2）建模为阻抗边，不视为导线；
  仅当两相之间存在不经绕组的导通路径时才判定为短路。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from star_delta import build, T_STAR, T_DELTA
from circuit import _is_free
import iec_symbols
import verify_common as vc

T_GAP = T_DELTA - T_STAR


def build_graph(circuit, contact_state, include_windings=True):
    """contact_state: {(inst_id, term): closed}。返回邻接表。
    include_windings=False 时绕组边不加入（用于短路判定）。
    接触器主触点按 contact_state 决定闭合；QF/FR 默认闭合。"""
    adj = {}
    def node(ref, term):
        return (ref, term) if not _is_free(ref) else ref
    def add_edge(n1, n2):
        adj.setdefault(n1, set()).add(n2)
        adj.setdefault(n2, set()).add(n1)
    for w in circuit.wires:
        add_edge(node(w.a_id, w.a_term), node(w.b_id, w.b_term))
    for (iid, term), closed in contact_state.items():
        if not closed:
            continue
        inst = circuit.instances[iid]
        terms = [t for t, _, _ in iec_symbols.TERMINALS[inst.symbol]]
        disp = [inst.remap.get(t, t) for t in terms]
        if term in disp and len(disp) == 2:
            other = disp[1 - disp.index(term)]
            add_edge((iid, term), (iid, other))
    # QF/FR 主回路默认闭合；接触器按状态
    closed_ids = {iid for (iid, t), cl in contact_state.items() if cl}
    for iid, inst in circuit.instances.items():
        if inst.symbol in ('circuit_breaker_3p', 'thermal_relay_3p'):
            do_close = True
        elif inst.symbol == 'contactor_main_contact':
            do_close = iid in closed_ids
        else:
            continue
        if do_close:
            for a, b in [('1', '2'), ('3', '4'), ('5', '6')]:
                da, db = inst.remap.get(a, a), inst.remap.get(b, b)
                add_edge((iid, da), (iid, db))
    if include_windings:
        # 电机绕组：阻抗边（短路判定时刻意排除）
        add_edge(("M1", "U1"), ("M1", "U2"))
        add_edge(("M1", "V1"), ("M1", "V2"))
        add_edge(("M1", "W1"), ("M1", "W2"))
    return adj


def reachable(adj, start, target):
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


class Sim:
    """时间状态仿真器。"""
    def __init__(self):
        self.km1 = self.km2 = self.km3 = 0
        self.t1 = self.t2 = 0.0  # KT1/KT2 计时
        self.sb0 = self.sb1 = self.fr = 0
        self.t_abs = 0.0  # 绝对时间

    def step(self, dt):
        kt1_nc = self.t1 < T_STAR - 1e-6    # 5s 后断开（容差浮点误差）
        kt2_no = self.t2 >= T_DELTA - 1e-6  # 5.5s 后闭合
        # 电气逻辑：先算 KM1，再用新值算 KM2/KM3（同拍内触点动作）
        km1_n = (not self.sb0) and (self.sb1 or self.km1) and (not self.fr)
        # 计时：KM1 新值决定走/复位
        if km1_n:
            self.t1 += dt
            self.t2 += dt
        else:
            self.t1 = self.t2 = 0.0
        kt1_nc = self.t1 < T_STAR - 1e-6
        kt2_no = self.t2 >= T_DELTA - 1e-6
        km2_n = km1_n and kt1_nc and (not self.km3) and (not self.fr)
        # 焊死建模：物理触点卡住时保持（影响 KM3 互锁判断）
        if getattr(self, 'weld_km2', False):
            km2_n = True
        km3_n = km1_n and kt2_no and (not km2_n) and (not self.fr)
        self.km1, self.km2, self.km3 = int(km1_n), int(km2_n), int(km3_n)

    def __init__(self):
        self.km1 = self.km2 = self.km3 = 0
        self.t1 = self.t2 = 0.0  # KT1/KT2 计时
        self.sb0 = self.sb1 = self.fr = 0
        self.t_abs = 0.0  # 绝对时间
    def run_until(self, t_end, dt=0.1):
        while self.t_abs < t_end - 1e-9:
            self.step(dt)
            self.t_abs += dt


def main():

    ok = True
    c = build()
    print("=== 星-三角时间状态验证 ===\n")

    # --- 场景 1：初始待机 ---
    s = Sim()
    ok &= check("初始待机：三组接触器均断开",
                (s.km1, s.km2, s.km3) == (0, 0, 0))

    # --- 场景 2：t=0 启动 ---
    s = Sim(); s.sb1 = 1; s.step(0.1); s.sb1 = 0
    ok &= check("t=0 启动：KM1、KM2 吸合，KM3 断开",
                (s.km1, s.km2, s.km3) == (1, 1, 0))

    # --- 场景 3：t=3s 仍星形 ---
    s.run_until(3.0)
    ok &= check("t=3s：仍处于星形启动", (s.km1, s.km2, s.km3) == (1, 1, 0))

    # --- 场景 4：t=5s KM2 释放，KM3 未吸合 ---
    s.run_until(5.0)
    ok &= check("t=5s：KM2 释放，KM3 尚未吸合", (s.km1, s.km2, s.km3) == (1, 0, 0))

    # --- 场景 5：t=5.5s KM3 吸合 ---
    s.run_until(5.5)
    ok &= check("t=5.5s：KM3 吸合，进入三角形运行",
                (s.km1, s.km2, s.km3) == (1, 0, 1))

    # --- 场景 6：KM2 未释放时 KM3 不能闭合（互锁） ---
    s2 = Sim(); s2.sb1 = 1; s2.step(0.1); s2.sb1 = 0
    s2.weld_km2 = True  # KM2 触点焊死
    s2.run_until(6.0)
    ok &= check("KM2 未释放：KM3 不能闭合", s2.km3 == 0)

    # --- 场景 7：星形运行中按停止 ---
    s3 = Sim(); s3.sb1 = 1; s3.step(0.1); s3.sb1 = 0
    s3.run_until(3.0)
    s3.sb0 = 1; s3.step(0.1)
    ok &= check("星形运行中按停止：全部释放并复位计时",
                (s3.km1, s3.km2, s3.km3) == (0, 0, 0) and s3.t1 == 0)

    # --- 场景 8：三角形运行中过载 ---
    s4 = Sim(); s4.sb1 = 1; s4.step(0.1); s4.sb1 = 0
    s4.run_until(6.0)
    assert (s4.km1, s4.km3) == (1, 1)
    s4.fr = 1; s4.step(0.1)
    ok &= check("三角形运行中过载：全部释放并复位计时",
                (s4.km1, s4.km2, s4.km3) == (0, 0, 0) and s4.t1 == 0)

    # --- 场景 9：失电后重新启动 ---
    s5 = Sim(); s5.sb1 = 1; s5.step(0.1); s5.sb1 = 0
    s5.run_until(6.0)  # 已进入三角形
    s5.km1 = s5.km2 = s5.km3 = 0; s5.t1 = s5.t2 = 0  # 失电
    s5.sb1 = 1; s5.step(0.1); s5.sb1 = 0  # 重新启动
    ok &= check("失电后重新启动：从星形开始",
                (s5.km1, s5.km2, s5.km3) == (1, 1, 0))

    # --- 场景 10：机械互锁不变量 ---
    print("\n=== 机械互锁 ===")
    def mech(km2_cmd, km3_cmd, m2, m3):
        if km2_cmd and km3_cmd:
            return m2, m3
        if km3_cmd and m2:
            return m2, m3
        if km2_cmd and m3:
            return m2, m3
        return (1 if km2_cmd else 0), (1 if km3_cmd else 0)
    bad = False
    for m2 in (0, 1):
        for m3 in (0, 1):
            if m2 and m3:
                continue
            for c2 in (0, 1):
                for c3 in (0, 1):
                    r2, r3 = mech(c2, c3, m2, m3)
                    if r2 and r3:
                        bad = True
    ok &= check("机械互锁：KM2/KM3 主触点永不同时闭合", not bad)

    # --- 控制回路几何连通检查（实际线段，非端点图） ---
    print("\n=== 控制回路几何连通（防旁路） ===")
    # 构建几何图：线段端点+交点为节点，线段为边
    # 简化：检查每条 Wire 的路径是否与不应接触的触点/端子相交
    def segs_of_wire(w):
        a = c.terminal_pos(w.a_id, w.a_term)
        b = c.terminal_pos(w.b_id, w.b_term)
        path = c._manhattan_pts([a] + list(w.via) + [b])
        return [(path[i], path[i+1]) for i in range(len(path)-1)]

    def pt_on_seg(px, py, seg, tol=2.0):
        (x1, y1), (x2, y2) = seg
        # 点到线段距离 < tol 且投影在线段内
        if abs(x1-x2) < 1e-9:  # 垂直
            if abs(px-x1) > tol: return False
            return min(y1,y2)-tol <= py <= max(y1,y2)+tol
        if abs(y1-y2) < 1e-9:  # 水平
            if abs(py-y1) > tol: return False
            return min(x1,x2)-tol <= px <= max(x1,x2)+tol
        return False

    # 收集所有触点端子位置（控制回路）
    ctrl_terms = {}
    for iid in ("KM1b", "KM2b", "KM3b", "KT1", "KT2", "KM1a", "SB1", "SB0"):
        if iid in c.instances:
            inst = c.instances[iid]
            for num, _, _ in iec_symbols.TERMINALS[inst.symbol]:
                disp = inst.remap.get(num, num)
                x, y = c.terminal_pos(iid, num)
                ctrl_terms[(iid, disp)] = (x, y)

    # 检查1：B2→KM2c:A1 的每条 Wire 路径必须经过 KT1 和 KM2b（不能旁路）
    # 检查2：B2→KM3c:A1 必须经过 KT2 和 KM3b
    # 检查3：所有线圈 A2→N 必须经过 FR:95-96
    # 实现：对每条控制 Wire，列出它经过的触点端子
    bypass_issues = []
    for w in c.wires:
        # 只检查控制回路（x > 900）
        a = c.terminal_pos(w.a_id, w.a_term)
        if a[0] < 900:
            continue
        segs = segs_of_wire(w)
        touched = set()
        for (iid, disp), (tx, ty) in ctrl_terms.items():
            for seg in segs:
                # 端点在触点上不算"经过"（那是正常连接）
                (x1,y1),(x2,y2) = seg
                is_endpoint = (abs(x1-tx)<1 and abs(y1-ty)<1) or (abs(x2-tx)<1 and abs(y2-ty)<1)
                if not is_endpoint and pt_on_seg(tx, ty, seg):
                    touched.add((iid, disp))
        if touched:
            bypass_issues.append((f"{w.a_id}:{w.a_term}->{w.b_id}:{w.b_term}", touched))
    ok &= check("控制 Wire 不穿过非端点触点", len(bypass_issues)==0,
                f"{bypass_issues[:3]}" if bypass_issues else "")

    # 检查4：FR 旁路——从任一线圈 A2 到 N 的几何路径必须经过 FR:95-96
    # 构建几何连通图（含线段交点）
    all_segs = []
    for w in c.wires:
        a = c.terminal_pos(w.a_id, w.a_term)
        if a[0] < 900:  # 只看控制回路
            continue
        all_segs.extend(segs_of_wire(w))
    # 简化检查：任一控制 Wire 的线段不得与 FR:95-96 之外的路径直连 N
    # （即：N 点 (1150,1090) 的所有入射线段必须来自 FR:96）
    n_pt = (1150, 1090)
    fr96 = c.terminal_pos("FRa", "96")
    bad_n = []
    for (x1,y1),(x2,y2) in all_segs:
        for (px,py) in [(x1,y1),(x2,y2)]:
            if abs(px-n_pt[0])<1 and abs(py-n_pt[1])<1:
                # 该端点在 N，另一端应在 FR:96 或其延长线上
                ox, oy = (x2,y2) if (px,py)==(x1,y1) else (x1,y1)
                # 允许：来自 FR:96 的垂直线
                if not (abs(ox-fr96[0])<1 and min(oy,fr96[1])<=n_pt[1]<=max(oy,fr96[1])):
                    # 检查是否线段经过 FR:96
                    if not pt_on_seg(fr96[0], fr96[1], ((x1,y1),(x2,y2)), tol=3.0):
                        bad_n.append(((x1,y1),(x2,y2)))
    ok &= check("N 点仅经 FR:96 接入（无旁路）", len(bad_n)==0,
                f"{len(bad_n)} 条异常" if bad_n else "")

    # 检查5：导线不得进入元件内部（只豁免端子连接点，不跳过整条Wire）
    boxes = {
        "KT1c": (1000, 750, 32, 18),
        "KT2c": (1300, 750, 32, 18),
        "KM2c": (1046, 850, 14, 32),
        "FRa": (1150, 1056, 8, 26),
    }
    def point_in_box(px, py, box):
        cx, cy, hw, hh = box
        return abs(px-cx) < hw and abs(py-cy) < hh

    def seg_hits_box_interior(seg, box, exempt_pts):
        (x1,y1),(x2,y2) = seg
        n = max(2, int(((x2-x1)**2+(y2-y1)**2)**0.5 / 2))
        for i in range(n+1):
            t = i/n
            px, py = x1+(x2-x1)*t, y1+(y2-y1)*t
            skip = any(((px-ex)**2+(py-ey)**2)**0.5 < 6 for ex, ey in exempt_pts)
            if skip: continue
            if point_in_box(px, py, box):
                return True
        return False

    intrusions = []
    for w in c.wires:
        exempt = {}
        for iid, term in [(w.a_id, w.a_term), (w.b_id, w.b_term)]:
            if iid in boxes and term:
                try:
                    exempt.setdefault(iid, []).append(c.terminal_pos(iid, term))
                except: pass
        for seg in segs_of_wire(w):
            for iid, box in boxes.items():
                if seg_hits_box_interior(seg, box, exempt.get(iid, [])):
                    intrusions.append((f"{w.a_id}:{w.a_term}->{w.b_id}:{w.b_term}", iid))
                    break
    ok &= check("导线不进入元件内部", len(intrusions)==0,
                f"{intrusions[:3]}" if intrusions else "")

    # 负向回归：旧版穿线路径必须被检出
    neg_ok = True
    for path, iid in [([(1032,750),(1000,750),(1000,1020)], "KT1c"),
                      ([(1150,1050),(1150,1030)], "FRa")]:
        box = boxes[iid]
        hit = any(seg_hits_box_interior((path[i], path[i+1]), box, [path[0]])
                  for i in range(len(path)-1))
        if not hit:
            neg_ok = False
            print(f"  负回归失败：{iid} 旧穿线未检出")
    ok &= check("负回归：旧穿线路径可检出", neg_ok)
    # 边框重合检查（复用公共库）
    bnotes = []
    bov = vc.check_no_border_overlap(c, boxes, bnotes.append)
    ok &= check("导线不沿元件边框重合", len(bov)==0,
                f"{bov[:2]}" if bov else "")
    # 第三个负回归：旧版 x=1032、y=818..882 的 64px 共边必须检出
    # 构造含旧问题线段的影子电路，调用公共库 check_no_border_overlap
    import copy
    c_shadow = copy.deepcopy(c)
    # 在影子电路中加入旧版问题线段：KT1c:A2 直下 x=1032
    from circuit import Wire, P
    c_shadow.add_wire(Wire("KT1c", "A2", P(1032, 1000), ""))
    snotes = []
    sov = vc.check_no_border_overlap(c_shadow, boxes, snotes.append)
    neg3_ok = any(iid == "KM2c" and px >= 60 for _, iid, px in sov)
    ok &= check("负回归：KM2c边框64px共边可检出", neg3_ok,
                "旧共边未检出" if not neg3_ok else "")

    # 检查6：FR 95-96 断开时，所有线圈 A2→N 均不可达（复用公共库）
    fr_zone = (1150, 1030, 1082, 5)  # cx, y1, y2, r
    n_pt = (1150, 1090)
    notes6 = []
    bad = vc.check_open_blocks(
        c,
        [c.terminal_pos(cid, "A2") for cid in ("KM1c","KM2c","KM3c","KT1c","KT2c")],
        n_pt, fr_zone, "FR断开", notes6.append, x_min=900)
    ok &= check("FR 断开时所有线圈 A2→N 不可达", len(bad)==0,
                f"{notes6[:2]}" if notes6 else "")
    # 故障注入：N 线段中途 T 形旁路必须被检出
    kt1_a2 = c.terminal_pos("KT1c", "A2")
    inj_hit = vc.fault_injection_test(
        c, [(kt1_a2, (kt1_a2[0],1086)), ((kt1_a2[0],1086),(1150,1086))],
        kt1_a2, n_pt, fr_zone, "注入", x_min=900)
    ok &= check("故障注入：N中途旁路可检出", inj_hit,
                "注入旁路未检出" if not inj_hit else "")
    def has_short(km1, km2, km3):
        """两相之间是否存在不经绕组的导通路径。"""
        st = {}
        for iid in ("KM1m", "KM2m", "KM3m"):
            v = {"KM1m": km1, "KM2m": km2, "KM3m": km3}[iid]
            for t in ("1", "2", "3", "4", "5", "6"):
                st[(iid, t)] = bool(v)
        adj = build_graph(c, st, include_windings=False)
        # 相点：母排 L1/L2/L3
        phases = ["@240,55", "@280,80", "@320,105"]
        for i in range(3):
            for j in range(i + 1, 3):
                if reachable(adj, phases[i], phases[j]):
                    return True, (i, j)
        return False, None

    for name, k1, k2, k3 in [("待机", 0, 0, 0), ("星形", 1, 1, 0),
                             ("切换间隔", 1, 0, 0), ("三角形", 1, 0, 1)]:
        short, pair = has_short(k1, k2, k3)
        ok &= check(f"{name}运行时：相间无直接短路", not short,
                    f"短路相 {pair}" if short else "")

    # 星形/三角形拓扑正确性（经绕组）
    adj = build_graph(c, {("KM1m", t): True for t in ("1", "2", "3", "4", "5", "6")} |
                         {("KM2m", t): True for t in ("1", "2", "3", "4", "5", "6")},
                      include_windings=True)
    ok &= check("星形：U2/V2/W2 经 KM2 短接",
                reachable(adj, ("M1", "U2"), ("M1", "V2")) and
                reachable(adj, ("M1", "V2"), ("M1", "W2")))
    adj = build_graph(c, {("KM1m", t): True for t in ("1", "2", "3", "4", "5", "6")} |
                         {("KM3m", t): True for t in ("1", "2", "3", "4", "5", "6")},
                      include_windings=True)
    ok &= check("三角形：U2-V1 / V2-W1 / W2-U1 经 KM3 连通",
                reachable(adj, ("M1", "U2"), ("M1", "V1")) and
                reachable(adj, ("M1", "V2"), ("M1", "W1")) and
                reachable(adj, ("M1", "W2"), ("M1", "U1")))

    # --- XML 几何 ---
    print("\n=== XML 几何 ===")
    wp = []
    for w in c.wires:
        a = c.terminal_pos(w.a_id, w.a_term)
        b = c.terminal_pos(w.b_id, w.b_term)
        wp.append(c._manhattan_pts([a] + list(w.via) + [b]))
    jumps, t_juncs = c._detect_crossings(wp)
    from collections import defaultdict as dd, Counter
    by_x = dd(list)
    for x, y in jumps:
        by_x[round(x)].append(round(y))
    min_gap = min((ys[i+1]-ys[i] for ys in by_x.values()
                   for ys in [sorted(ys)] for i in range(len(ys)-1)), default=99)
    ok &= check(f"圆弧数={len(jumps)}", len(jumps) > 0, f"实际 {len(jumps)}")
    ok &= check("同x圆弧最小间距≥16px", min_gap >= 16, f"最小间距 {min_gap}px")
    # 红点遮挡
    term_pts = set()
    for inst in c.instances.values():
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
    bad = [1 for jx, jy in jumps for tx, ty in all_dots
           if abs(jx-tx) < 12 and abs(jy-ty) < 14]
    ok &= check(f"圆弧黑底不遮挡红点（共 {len(all_dots)} 个）", len(bad) == 0)

    print("\n" + ("全部通过 ✓" if ok else "存在失败 ✗"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
