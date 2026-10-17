#!/usr/bin/env python3
"""第 4 步：报表——从电路模型做确定性查表聚合，全部由数据算出。

- bom(circuit): 按（位号，符号，型号）分组计数
- wire_list(circuit): 接线表 W1..Wn
- terminal_list(circuit): 逐实例逐端子
- 每个返回结构化数据（list[dict]），附 to_markdown()
- check_consistency(): 三项一致性校验
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iec_symbols as S
from iec_symbols import TERMINALS
from circuit import P, _is_free

# 自由点坐标 -> 可读名（与 direct_start.py 的版式标注一致）
FREE_NAMES = {
    P(240, 55): "L1", P(280, 80): "L2", P(320, 105): "L3",
    P(200, 55): "L1母排", P(350, 55): "L1母排",
    P(200, 80): "L2母排", P(350, 80): "L2母排",
    P(200, 105): "L3母排", P(350, 105): "L3母排",
    P(1100, 120): "Lc", P(1100, 270): "N1",
    P(1100, 410): "N2", P(1100, 720): "N",
}


def sym_name(symbol):
    """符号中文名：取函数 docstring 首段，去掉末尾位号，如 "三极断路器 QF"->"三极断路器"。"""
    doc = (getattr(S, symbol).__doc__ or symbol).strip()
    s = doc.split("（")[0].strip()
    s = re.sub(r"\s+[A-Z0-9]+$", "", s)
    return s or symbol


def end_desc(circuit, ref, term):
    """接线端点的人类可读描述。term 为显示编号（Wire 里存的就是显示编号）。"""
    if _is_free(ref):
        return FREE_NAMES.get(ref, "外部点")
    return "%s:%s" % (circuit.instances[ref].tag, term)


def bom(circuit):
    """按（位号，符号，型号）分组计数。返回 list[dict]。"""
    groups = {}
    order = []
    for inst in circuit.instances.values():
        key = (inst.tag, inst.symbol, inst.partno)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(inst.id)
    rows = []
    for i, key in enumerate(order, 1):
        tag, symbol, partno = key
        rows.append({"序号": i, "位号": tag, "名称": sym_name(symbol),
                     "型号": partno, "数量": len(groups[key]),
                     "实例": ",".join(groups[key])})
    return rows


def wire_list(circuit):
    """接线表，W1..Wn，按 Circuit.wires 顺序。"""
    rows = []
    for i, w in enumerate(circuit.wires, 1):
        rows.append({"线号": "W%d" % i,
                     "起点": end_desc(circuit, w.a_id, w.a_term),
                     "终点": end_desc(circuit, w.b_id, w.b_term)})
    return rows


def terminal_list(circuit):
    """逐实例逐端子。连接去向标注对端（位号:端子）与线号。"""
    conn = {}
    for i, w in enumerate(circuit.wires, 1):
        ends = [(w.a_id, w.a_term), (w.b_id, w.b_term)]
        for (ref, term), (oref, oterm) in ((ends[0], ends[1]),
                                           (ends[1], ends[0])):
            if _is_free(ref):
                continue
            conn.setdefault((ref, term), []).append(
                (i, end_desc(circuit, oref, oterm)))
    rows = []
    for inst in circuit.instances.values():
        for lib_num, _dx, _dy in TERMINALS[inst.symbol]:
            disp = inst.remap.get(lib_num, lib_num)
            hits = conn.get((inst.id, disp), [])
            if hits:
                to = "; ".join("%s [W%d]" % (d, wi) for wi, d in hits)
                rows.append({"位号": inst.tag, "端子": disp,
                             "状态": "已接", "连接去向": to})
            else:
                rows.append({"位号": inst.tag, "端子": disp,
                             "状态": "空闲", "连接去向": ""})
    return rows


def check_consistency(circuit, bom_rows, wire_rows, term_rows):
    """三项一致性校验。返回 (ok: bool, 说明: list[str])。"""
    notes = []
    ok = True
    n_inst, n_wire = len(circuit.instances), len(circuit.wires)
    s = sum(r["数量"] for r in bom_rows)
    ok &= (s == n_inst)
    notes.append("BOM 数量之和 %d == 实例数 %d：%s"
                 % (s, n_inst, "通过" if s == n_inst else "失败"))
    ok &= (len(wire_rows) == n_wire)
    notes.append("接线表 %d 条 == 接线数 %d：%s"
                 % (len(wire_rows), n_wire,
                    "通过" if len(wire_rows) == n_wire else "失败"))
    free_ends = sum(1 for w in circuit.wires
                    for ref in (w.a_id, w.b_id) if _is_free(ref))
    used = sum(1 for r in term_rows if r["状态"] == "已接")
    expect = 2 * n_wire - free_ends
    ok &= (used == expect)
    notes.append('端子表"已接" %d == 2×%d−自由点端点%d = %d：%s'
                 % (used, n_wire, free_ends, expect,
                    "通过" if used == expect else "失败"))
    idle = ["%s:%s" % (r["位号"], r["端子"]) for r in term_rows
            if r["状态"] == "空闲"]
    notes.append("空闲端子：%s" % ("无" if not idle else "、".join(idle)))
    return ok, notes


def _md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(r[h]) for h in headers) + " |")
    return "\n".join(out)


def to_markdown(title, circuit, bom_rows, wire_rows, term_rows, ok, notes):
    parts = ["# %s\n" % title,
             "%d 个实例 / %d 根接线，由电路模型确定性查表聚合生成，未经手工编辑。\n"
             % (len(circuit.instances), len(wire_rows)),
             "## 一、BOM 表（按位号·符号·型号分组）\n",
             _md_table(["序号", "位号", "名称", "型号", "数量"],
                       bom_rows) + "\n",
             "## 二、接线表\n",
             _md_table(["线号", "起点", "终点"], wire_rows) + "\n",
             "## 三、端子表（逐实例逐端子）\n",
             _md_table(["位号", "端子", "状态", "连接去向"], term_rows) + "\n",
             "## 一致性校验\n",
             "\n".join("- %s" % n for n in notes),
             "\n结论：%s\n" % ("全部通过" if ok else "存在不一致，见上")]
    return "\n".join(parts)


# ---------- PNG 渲染（PIL，黑底白字，手机可读） ----------

def _load_font(size):
    """中文字体按候选路径依次尝试，缺失则回退 PIL 内置字体（不崩溃）。"""
    from PIL import ImageFont
    import glob
    for pat in (
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ):
        hits = glob.glob(pat)
        if hits:
            return ImageFont.truetype(hits[0], size)
    return ImageFont.load_default()  # 无中文字体时降级（中文显示为方框，但不崩）


def render_png(path, bom_rows, wire_rows, term_rows, title="直接启动电路 · 报表 v1"):
    from PIL import Image, ImageDraw
    f_title = _load_font(40)
    f_head = _load_font(24)
    f_cell = _load_font(22)

    tables = [
        ("一、BOM 表", ["序号", "位号", "名称", "型号", "数量"], bom_rows),
        ("二、接线表", ["线号", "起点", "终点"], wire_rows),
        ("三、端子表", ["位号", "端子", "状态", "连接去向"], term_rows),
    ]
    W, pad, row_h = 1500, 24, 40
    # 先算每表列宽与总高
    tmp = Image.new("RGB", (10, 10))
    d0 = ImageDraw.Draw(tmp)

    def tw(s, f):
        return d0.textbbox((0, 0), str(s), font=f)[2]

    plan = []
    total_h = 130
    for tname, headers, rows in tables:
        widths = []
        for h in headers:
            wmax = max([tw(h, f_head)] +
                       [tw(r[h], f_cell) for r in rows])
            widths.append(wmax + 36)
        # 表格过宽则整体缩放列宽
        if sum(widths) > W - 2 * pad:
            k = (W - 2 * pad) / sum(widths)
            widths = [w * k for w in widths]
        th = 60 + (len(rows) + 1) * row_h + 40
        plan.append((tname, headers, rows, widths, total_h))
        total_h += th

    img = Image.new("RGB", (W, total_h + 30), "#000000")
    d = ImageDraw.Draw(img)
    d.text((W // 2, 30), title, font=f_title, fill="#FF3333", anchor="ma")
    d.text((W // 2, 82), "由电路模型查表聚合生成 · BOM %d 项 / 接线 %d 条 / 端子 %d 个"
           % (len(bom_rows), len(wire_rows), len(term_rows)),
           font=f_cell, fill="#BBBBBB", anchor="ma")

    for tname, headers, rows, widths, y0 in plan:
        d.text((pad, y0), tname, font=f_head, fill="#FF3333")
        y = y0 + 56
        xcols = [pad]
        for wcol in widths:
            xcols.append(xcols[-1] + wcol)
        # 表头
        for j, h in enumerate(headers):
            d.text((xcols[j] + 18, y + 6), h, font=f_head, fill="#FFFF00")
        d.line([(pad, y), (xcols[-1], y)], fill="#888888", width=2)
        y += row_h
        d.line([(pad, y), (xcols[-1], y)], fill="#888888", width=2)
        for r in rows:
            for j, h in enumerate(headers):
                fill = "#FFFFFF"
                if h == "状态":
                    fill = "#7CFC00" if r[h] == "已接" else "#FFA500"
                d.text((xcols[j] + 18, y + 6), str(r[h]), font=f_cell,
                       fill=fill)
            y += row_h
            d.line([(pad, y), (xcols[-1], y)], fill="#333333", width=1)
        # 纵线
        for x in xcols:
            d.line([(x, y0 + 56), (x, y)], fill="#555555", width=1)

    img.save(path)
    return path


def main(version="v1"):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    if version == "v8":
        from direct_start import build_v2 as build
        tag = "v8"
    elif version == "v7":
        from direct_start import build_v2 as build
        tag = "v7"
    elif version == "v6":
        from direct_start import build_v2 as build
        tag = "v6"
    elif version == "v5":
        from direct_start import build_v2 as build
        tag = "v5"
    elif version == "v3":
        from direct_start import build_v2 as build
        tag = "v3"
    else:
        from direct_start import build
        tag = "v1"
    c = build()
    errs = c.validate()
    assert not errs, errs
    b = bom(c)
    w = wire_list(c)
    t = terminal_list(c)
    ok, notes = check_consistency(c, b, w, t)
    md = to_markdown(f"直接启动电路 · 报表 {tag}", c, b, w, t, ok, notes)
    md_path = os.path.expanduser(f"~/workspace/your_files/直接启动电路-报表-{tag}.md")
    open(md_path, "w", encoding="utf-8").write(md)
    png_path = os.path.expanduser(f"~/workspace/your_files/直接启动电路-报表-{tag}.png")
    render_png(png_path, b, w, t, title=f"直接启动电路 · 报表 {tag}")
    print("校验:", "全部通过" if ok else "有问题")
    for n in notes:
        print(" -", n)
    print("written:", md_path)
    print("written:", png_path)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "v1")
