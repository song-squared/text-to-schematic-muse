#!/usr/bin/env python3
"""DXF 发射器（第 5 步）：把 Circuit 模型发射成 DXF，供 AutoCAD / LibreCAD 打开。

设计：
- 图层：SYMBOLS（符号几何）/ WIRES（导线）/ DOTS（端子与分支点）/ TEXTS（文字）。
- 录制：RecCtx 复刻 iec_symbols.Ctx 的接口，符号函数原样调用，只记录图元。
- 坐标：draw.io 为 y 向下；DXF 为 y 向上，按画布高度 H 翻转（整体翻转，
  文字不镜像）。
- 版本：R2010（AC1024），老 AutoCAD 可开。
- 中文文字：按 unicode 原样写入 TEXT 实体，显示效果取决于看图者的字体。
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ezdxf
from ezdxf.enums import TextEntityAlignment

import iec_symbols as S
from iec_symbols import TERMINALS
from circuit import Circuit

ACI_WHITE, ACI_RED, ACI_YELLOW, ACI_GRAY = 7, 1, 2, 8


class RecCtx:
    """录制型绘图上下文：接口同 iec_symbols.Ctx，只记录图元。"""

    def __init__(self):
        self.ops = []
        self.WHITE = "#FFFFFF"
        self.RED = "#FF0000"
        self.FONT = "Noto Sans CJK SC"

    def wire(self, x1, y1, x2, y2, color=None, w=3, dashed=False):
        self.ops.append(("line", float(x1), float(y1), float(x2), float(y2),
                         bool(dashed)))

    def dot(self, x, y, r=7, color=None):
        self.ops.append(("circle", float(x), float(y), float(r)))

    def rect(self, x, y, w, h, fill="none", stroke=None, sw=3):
        self.ops.append(("rect", float(x), float(y), float(w), float(h)))

    def ellipse(self, x, y, w, h, fill="none", stroke=None, sw=3):
        self.ops.append(("ellipse", float(x), float(y), float(w), float(h)))

    def text(self, x, y, s, size=22, color=None):
        self.ops.append(("text", float(x), float(y), str(s), float(size)))

    def library_shape(self, x, y, w, h, shape, stroke=None, sw=3):
        # draw.io 自带库符号无纯几何定义：发射为包络框 + 形状名标注
        self.ops.append(("libshape", float(x), float(y), float(w), float(h),
                         str(shape)))


def _manhattan_pts(pts):
    """与 Circuit._manhattan 相同的直角折线算法，返回路径点列。"""
    path = [pts[0]]
    for p in pts[1:]:
        q = path[-1]
        if q[0] != p[0] and q[1] != p[1]:
            path.append((p[0], q[1]))
        path.append(p)
    return path


def _display_num(inst, lib_num):
    """库端子编号 -> 显示编号（remap 为 {库编号: 显示编号}）。"""
    return inst.remap.get(lib_num, lib_num)


def emit_dxf(circuit, path, W=1600, H=1000, title="", subtitle="", notes=(),
             extra_labels=()):
    """把 circuit 发射成 DXF 文件。返回 (doc, 统计 dict)。"""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    for name, color in (("SYMBOLS", ACI_WHITE), ("WIRES", ACI_WHITE),
                        ("DOTS", ACI_RED), ("TEXTS", ACI_YELLOW)):
        doc.layers.add(name, color=color)
    if "DASHED" not in doc.linetypes:
        doc.linetypes.add("DASHED", pattern=[0.6, 0.3, 0.1])

    fy = lambda y: H - y  # draw.io y向下 -> DXF y向上

    def add_text(s, x, y, size, color=ACI_YELLOW):
        t = msp.add_text(str(s), height=size,
                         dxfattribs={"layer": "TEXTS", "color": color})
        t.set_placement((x, fy(y)), align=TextEntityAlignment.CENTER)
        return t

    stats = Counter()

    # 1) 实例几何 -> SYMBOLS
    from circuit import RotCtx
    for inst in circuit.instances.values():
        rec = RecCtx()
        rctx = RotCtx(rec, inst.x, inst.y, inst.rotation)
        getattr(S, inst.symbol)(rctx, inst.x, inst.y)
        for op in rec.ops:
            k = op[0]
            if k == "line":
                _, x1, y1, x2, y2, dashed = op
                msp.add_line((x1, fy(y1)), (x2, fy(y2)),
                             dxfattribs={"layer": "SYMBOLS",
                                         "linetype": "DASHED" if dashed
                                         else "BYLAYER"})
                stats["line"] += 1
            elif k == "circle":
                _, x, y, r = op
                msp.add_circle((x, fy(y)), r,
                               dxfattribs={"layer": "SYMBOLS"})
                stats["circle"] += 1
            elif k == "rect":
                _, x, y, w, h = op
                pts = [(x, fy(y)), (x + w, fy(y)),
                       (x + w, fy(y + h)), (x, fy(y + h))]
                msp.add_lwpolyline(pts, close=True,
                                   dxfattribs={"layer": "SYMBOLS"})
                stats["rect"] += 1
            elif k == "ellipse":
                _, x, y, w, h = op
                cx, cy = x + w / 2, fy(y + h / 2)
                if w >= h:
                    major, ratio = (w / 2, 0), (h / w if w else 1)
                else:
                    major, ratio = (0, h / 2), (w / h if h else 1)
                msp.add_ellipse((cx, cy), major_axis=major, ratio=ratio,
                                dxfattribs={"layer": "SYMBOLS"})
                stats["ellipse"] += 1
            elif k == "text":
                _, x, y, s, size = op
                add_text(s, x, y, size)
                stats["text"] += 1
            elif k == "libshape":
                _, x, y, w, h, shape = op
                pts = [(x, fy(y)), (x + w, fy(y)),
                       (x + w, fy(y + h)), (x, fy(y + h))]
                msp.add_lwpolyline(pts, close=True,
                                   dxfattribs={"layer": "SYMBOLS",
                                               "linetype": "DASHED"})
                add_text("[" + shape.split(".")[-1] + "]",
                         x + w / 2, y + h / 2, 12, ACI_GRAY)
                stats["libshape"] += 1

    # 2) 导线 -> WIRES（LWPOLYLINE）
    end_counter = Counter()
    for w in circuit.wires:
        a = circuit.terminal_pos(w.a_id, w.a_term)
        b = circuit.terminal_pos(w.b_id, w.b_term)
        wpath = _manhattan_pts([a] + list(w.via) + [b])
        msp.add_lwpolyline([(x, fy(y)) for x, y in wpath],
                           dxfattribs={"layer": "WIRES"})
        stats["wire"] += 1
        for p in wpath:
            end_counter[(round(p[0], 3), round(p[1], 3))] += 1

    # 3) 端子点 + 分支点 -> DOTS
    term_pts = set()
    for inst in circuit.instances.values():
        for num, dx, dy in TERMINALS[inst.symbol]:
            px, py = circuit.terminal_pos(inst.id, num)
            term_pts.add((round(px, 3), round(py, 3)))
            msp.add_circle((px, fy(py)), 7,
                           dxfattribs={"layer": "DOTS"})
            stats["term_dot"] += 1
            add_text(_display_num(inst, num), px, py - 20, 12)
            stats["term_text"] += 1
    for (x, y), c in end_counter.items():
        if c >= 3 and (x, y) not in term_pts:
            msp.add_circle((x, fy(y)), 7, dxfattribs={"layer": "DOTS"})
            stats["branch_dot"] += 1

    # 4) 文字 -> TEXTS
    if title:
        add_text(title, W / 2, 42, 34, ACI_RED)
    if subtitle:
        add_text(subtitle, W / 2, 84, 20, ACI_RED)
    for i, n in enumerate(notes):
        add_text(n, W / 2, H - 110 + i * 36, 14, ACI_GRAY)
    for x, y, s, size in extra_labels:
        add_text(s, x, y, size, ACI_RED)
    for inst in circuit.instances.values():
        if inst.label_at:
            lx, ly = inst.label_at
            add_text(inst.tag, lx, ly, 24, ACI_WHITE)
            add_text(inst.partno, lx, ly + 32, 16, ACI_GRAY)

    doc.saveas(path)
    stats["dxf_version"] = doc.dxfversion
    return doc, dict(stats)


def verify_dxf(path):
    """读回验证：版本、图层、实体数。返回 (ok, 报告 dict)。"""
    try:
        doc = ezdxf.readfile(path)
    except Exception as e:
        return False, {"error": "读回失败: %s" % e}
    msp = doc.modelspace()
    layers = Counter()
    types = Counter()
    for e in msp:
        try:
            layers[e.dxf.layer] += 1
            types[e.dxftype()] += 1
        except Exception:
            types["<unreadable>"] += 1
    rep = {"dxfversion": doc.dxfversion,
           "entities": sum(layers.values()),
           "by_layer": dict(layers), "by_type": dict(types)}
    ok = (doc.dxfversion == "AC1024" and sum(layers.values()) > 0
          and "<unreadable>" not in types)
    return ok, rep


if __name__ == "__main__":
    import importlib
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    # 用法：python3 dxf_emit.py [电路模块名]，缺省 direct_start；新电路无需改代码
    mod_name = sys.argv[1] if len(sys.argv) > 1 else "direct_start"
    build = importlib.import_module(mod_name).build
    out_name = {"direct_start": "direct_start_v1.dxf"}.get(mod_name, mod_name + ".dxf")
    c = build()
    errs = c.validate()
    assert not errs, errs
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), out_name)
    labels = [
        (240, 70, "L1", 20), (280, 70, "L2", 20), (320, 70, "L3", 20),
        (90, 130, "主回路", 22),
        (1100, 748, "N", 20),
        (1150, 142, "Lc", 20),
        (1300, 150, "控制回路", 22),
        (1140, 248, "N1", 16), (1140, 434, "N2", 16),
    ]
    notes = [
        "注：型号为示例占位；FR 辅助常闭触点标准编号 95-96，经端子重命名（21→95、22→96）实现",
        "DXF R2010 发射：图层 SYMBOLS / WIRES / DOTS / TEXTS；中文显示取决于看图者字体",
    ]
    _, stats = emit_dxf(
        c, out, title="直接启动电路（端到端验证 v1）",
        subtitle="9 实例 / 22 接线 · DXF 发射",
        notes=notes, extra_labels=labels)
    print("written:", out)
    print("emit stats:", stats)
    ok, rep = verify_dxf(out)
    print("verify:", "通过" if ok else "失败", rep)
    sys.exit(0 if ok else 1)
