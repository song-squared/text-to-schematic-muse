#!/usr/bin/env python3
"""QET 发射器（第 5 步）：把 Circuit 模型发射成 QElectroTech 工程文件 (.qet)。

设计：
- 每个符号 -> 一个 QET 自定义 element <definition>（图元按 QET 官方 wiki 的
  .elmt 格式转换：line / polygon / circle / ellipse / text / terminal），
  嵌入工程，不依赖 QET 公共库路径。
- 每个实例 -> <element>，引用嵌入定义，实例与端子均分配 UUID。
- 每根 Wire -> <conductor>，端点用 element/terminal UUID 引用。
- 自由点（电源/分支点）-> 无端子 conductor 端点（QET 侧为悬空端，按源码
  此时省略对应属性）。

验证目标（QET 无 headless，按任务书）：XML well-formed；结构尽量贴近 QET
实际格式；近似项见文末"映射说明"，不宣称 QET 可直接打开。
"""
import os
import sys
import uuid
import xml.etree.ElementTree as ET
from xml.dom import minidom

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import iec_symbols as S
from iec_symbols import TERMINALS
from circuit import Circuit, _is_free

# ---------------------------------------------------------------------------
# 映射说明（ verified = 经 QET 源码/官方文档确认；approx = 尽力而为的近似 ）
#
# [verified] conductor 属性 element1/terminal1/element2/terminal2 为 UUID，
#   另有 freezeLabel；悬空端省略对应属性。
#   来源：QET 源码 Conductor::toXml（qelectrotech.org 论坛源码 diff）。
# [verified] element <definition> 的图元格式（line/polygon/circle/text/
#   terminal）与 terminal 的 x/y/orientation。
#   来源：QET 官方 wiki "The XML structure used to describe the items"。
# [approx] 工程根 <project> / 图纸 <diagram order> / 实例 <element type x y>
#   的包装结构；嵌入定义的 <definitions> 节与 type="custom://..." 引用方案
#   为本发射器自定义约定，QET 原生未必识别，需人工导入定义或对照调整。
# [approx] ellipse 图元（wiki 0.3 版未列出，0.9+ 元素编辑器支持）；
#   端子 orientation 由端子在包络中的方位推断（上=n/下=s/左=w/右=e）。
# [approx] conductor 路径 <segment> 的格式；QET 无 segment 时会自动布线，
#   本发射器仍按直角折线写入以便对照。
# ---------------------------------------------------------------------------


class RecCtx:
    """录制型绘图上下文（同 dxf_emit.RecCtx 的精简版）。"""

    def __init__(self):
        self.ops = []
        self.WHITE = "#FFFFFF"
        self.RED = "#FF0000"
        self.FONT = "Noto Sans CJK SC"

    def wire(self, x1, y1, x2, y2, color=None, w=3, dashed=False):
        self.ops.append(("line", float(x1), float(y1), float(x2), float(y2)))

    def dot(self, x, y, r=7, color=None):
        self.ops.append(("circle", float(x), float(y), float(r)))

    def rect(self, x, y, w, h, fill="none", stroke=None, sw=3):
        self.ops.append(("rect", float(x), float(y), float(w), float(h)))

    def ellipse(self, x, y, w, h, fill="none", stroke=None, sw=3):
        self.ops.append(("ellipse", float(x), float(y), float(w), float(h)))

    def text(self, x, y, s, size=22, color=None):
        self.ops.append(("text", float(x), float(y), str(s), float(size)))

    def library_shape(self, x, y, w, h, shape, stroke=None, sw=3):
        self.ops.append(("rect", float(x), float(y), float(w), float(h)))


def _orientation(dx, dy, minx, maxx, miny, maxy):
    """由端子在包络中的方位推断 QET 朝向（近似）。"""
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    dist = {"n": dy - miny, "s": maxy - dy, "w": dx - minx, "e": maxx - dx}
    return min(dist, key=lambda k: dist[k])


def symbol_to_definition(symbol):
    """符号函数 -> QET <definition>（坐标相对锚点）。返回 (definition 元件, 包络)。"""
    rec = RecCtx()
    getattr(S, symbol)(rec, 0, 0)
    xs, ys = [], []
    for op in rec.ops:
        k = op[0]
        if k == "line":
            xs += [op[1], op[3]]; ys += [op[2], op[4]]
        elif k == "circle":
            xs += [op[1] - op[3], op[1] + op[3]]
            ys += [op[2] - op[3], op[2] + op[3]]
        elif k in ("rect", "ellipse"):
            xs += [op[1], op[1] + op[3]]; ys += [op[2], op[2] + op[4]]
        elif k == "text":
            xs.append(op[1]); ys.append(op[2])
    minx, maxx = min(xs) - 5, max(xs) + 5
    miny, maxy = min(ys) - 5, max(ys) + 5

    defi = ET.Element("definition", {
        "type": "element",
        "width": "%g" % (maxx - minx),
        "height": "%g" % (maxy - miny),
        "hotspot_x": "%g" % (-minx),   # 锚点 (0,0) 在包络中的位置
        "hotspot_y": "%g" % (-miny),
        "orientation": "dnse",
    })
    names = ET.SubElement(defi, "names")
    ET.SubElement(names, "name", {"lang": "en"}).text = symbol
    ET.SubElement(names, "name", {"lang": "zh"}).text = symbol
    info = ET.SubElement(defi, "informations")
    info.text = ("Author: text-to-schematic-muse emitter\r\n"
                 "License: MIT\r\n"
                 "Converted from iec_symbols.%s" % symbol)
    desc = ET.SubElement(defi, "description")

    def sh(v):
        return ("x1", "%g" % v[0], "y1", "%g" % v[1],
                "x2", "%g" % v[2], "y2", "%g" % v[3])

    for op in rec.ops:
        k = op[0]
        if k == "line":
            _, x1, y1, x2, y2 = op
            ET.SubElement(desc, "line", {
                "x1": "%g" % x1, "y1": "%g" % y1,
                "x2": "%g" % x2, "y2": "%g" % y2,
                "antialias": "false"})
        elif k == "circle":
            _, x, y, r = op
            ET.SubElement(desc, "circle", {
                "x": "%g" % (x - r), "y": "%g" % (y - r),
                "diameter": "%g" % (2 * r), "antialias": "true"})
        elif k == "rect":
            _, x, y, w, h = op
            ET.SubElement(desc, "polygon", {
                "x1": "%g" % x, "y1": "%g" % y,
                "x2": "%g" % (x + w), "y2": "%g" % y,
                "x3": "%g" % (x + w), "y3": "%g" % (y + h),
                "x4": "%g" % x, "y4": "%g" % (y + h),
                "closed": "true", "antialias": "false"})
        elif k == "ellipse":
            _, x, y, w, h = op
            ET.SubElement(desc, "ellipse", {
                "x": "%g" % x, "y": "%g" % y,
                "width": "%g" % w, "height": "%g" % h,
                "antialias": "true"})
        elif k == "text":
            _, x, y, s, size = op
            ET.SubElement(desc, "text", {
                "x": "%g" % x, "y": "%g" % y,
                "size": "%g" % size, "text": s})
    # 端子（display 编号；QET 端子名用显示编号）
    for num, dx, dy in TERMINALS[symbol]:
        ET.SubElement(desc, "terminal", {
            "x": "%g" % dx, "y": "%g" % dy,
            "orientation": _orientation(dx, dy, minx, maxx, miny, maxy),
            "name": num})
    return defi, (minx, miny, maxx, maxy)


def _manhattan_pts(pts):
    path = [pts[0]]
    for p in pts[1:]:
        q = path[-1]
        if q[0] != p[0] and q[1] != p[1]:
            path.append((p[0], q[1]))
        path.append(p)
    return path


def emit_qet(circuit, path, title="text-to-schematic-muse"):
    """把 circuit 发射成 .qet 文件。返回统计 dict。"""
    stats = {"elements": 0, "conductors": 0, "definitions": 0}
    project = ET.Element("project", {"version": "0.9", "title": title})

    # 1) 嵌入自定义 element 定义（按符号去重）
    defs_el = ET.SubElement(project, "definitions")
    seen = {}
    for inst in circuit.instances.values():
        if inst.symbol not in seen:
            defi, _ = symbol_to_definition(inst.symbol)
            defi.set("id", "tsm:" + inst.symbol)
            defs_el.append(defi)
            seen[inst.symbol] = defi
            stats["definitions"] += 1

    # 2) 图纸：实例 + 导线
    diagram = ET.SubElement(project, "diagram", {"order": "0"})

    elem_uuid, term_uuid = {}, {}
    for inst in circuit.instances.values():
        eu = str(uuid.uuid4())
        elem_uuid[inst.id] = eu
        el = ET.SubElement(diagram, "element", {
            "type": "custom://text-to-schematic-muse/" + inst.symbol,
            "x": "%g" % inst.x, "y": "%g" % inst.y,
            "uuid": eu,
            "label": "%s %s" % (inst.tag, inst.partno),
        })
        for num, dx, dy in TERMINALS[inst.symbol]:
            disp = inst.remap.get(num, num)  # 库编号 -> 显示编号
            tu = str(uuid.uuid4())
            term_uuid[(inst.id, disp)] = tu
            px, py = circuit.terminal_pos(inst.id, num)
            ET.SubElement(el, "terminal_ref", {
                "uuid": tu, "name": disp,
                "x": "%g" % px, "y": "%g" % py})
        stats["elements"] += 1

    for w in circuit.wires:
        cond = ET.SubElement(diagram, "conductor", {"freezeLabel": "false"})
        for ref, term in ((w.a_id, w.a_term), (w.b_id, w.b_term)):
            if _is_free(ref):
                continue  # 悬空端：按 QET 源码省略对应属性
            n = 1 if (ref, term) == (w.a_id, w.a_term) else 2
            cond.set("element%d" % n, elem_uuid[ref])
            cond.set("terminal%d" % n, term_uuid[(ref, term)])
        a = circuit.terminal_pos(w.a_id, w.a_term)
        b = circuit.terminal_pos(w.b_id, w.b_term)
        for p, q in zip(_manhattan_pts([a] + list(w.via) + [b])[:-1],
                        _manhattan_pts([a] + list(w.via) + [b])[1:]):
            ET.SubElement(cond, "segment", {
                "x1": "%g" % p[0], "y1": "%g" % p[1],
                "x2": "%g" % q[0], "y2": "%g" % q[1]})
        stats["conductors"] += 1

    xml = minidom.parseString(ET.tostring(project, encoding="unicode"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml.toprettyxml(indent="  ", encoding=None))
    return stats


def verify_qet(path):
    """验证：well-formed；关键结构存在；conductor 引用可解析。"""
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        return False, {"error": "XML 解析失败: %s" % e}
    root = tree.getroot()
    rep = {"root": root.tag, "definitions": 0, "elements": 0,
           "conductors": 0, "dangling": 0, "unresolved": []}
    uuids = set()
    for d in root.iter("definition"):
        rep["definitions"] += 1
    for el in root.iter("element"):
        rep["elements"] += 1
        if el.get("uuid"):
            uuids.add(el.get("uuid"))
        for t in el.iter("terminal_ref"):
            if t.get("uuid"):
                uuids.add(t.get("uuid"))
    for c in root.iter("conductor"):
        rep["conductors"] += 1
        for n in ("1", "2"):
            e, t = c.get("element" + n), c.get("terminal" + n)
            if e is None or t is None:
                rep["dangling"] += 1
            elif e not in uuids or t not in uuids:
                rep["unresolved"].append((e, t))
    ok = (root.tag == "project" and rep["definitions"] > 0
          and rep["elements"] > 0 and not rep["unresolved"])
    return ok, rep


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    which = sys.argv[1] if len(sys.argv) > 1 else "direct_start"
    if which == "fr":
        from forward_reverse import build
        out_name = "forward_reverse.qet"
    else:
        from direct_start import build
        out_name = "direct_start.qet"
    c = build()
    assert not c.validate()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), out_name)
    stats = emit_qet(c, out, title="直接启动电路（端到端验证 v1）")
    print("written:", out)
    print("emit stats:", stats)
    ok, rep = verify_qet(out)
    print("verify:", "通过" if ok else "失败", rep)
    sys.exit(0 if ok else 1)
