#!/usr/bin/env python3
"""最小可用电路模型（v1）：实例化（位号+型号）+ 线改"连接"。

- Instance: 符号的一次使用，id 全局唯一；同一位号可有多个实例
  （如 KM 有线圈/主触点/辅助触点三个实例）；x,y 为该符号的锚点；
  remap={库端子编号: 显示编号} 用于端子重命名（如 FR 的 95-96）。
- Wire: 只连"实例端子到实例端子"。端点引用为实例 id，或 "@x,y"
  形式的自由点（电源进线/出线、导线分支点），a_term/b_term 对自由点无意义。
- Circuit.validate(): id 唯一、symbol 存在、端子编号存在（含重命名解析）。
- Circuit.terminal_pos(ref, term): 锚点 + TERMINALS 偏移 = 绝对坐标。
- Circuit.render(...): 画实例（位号+型号标注）与直角折线导线，端子红点，
  三段以上导线交汇处自动打分支点。
"""
import xml.etree.ElementTree as ET
import os
import sys
from dataclasses import dataclass, field
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iec_symbols as S
from iec_symbols import Ctx, TERMINALS


def P(x, y):
    """自由点引用（非实例端子），如 P(1100, 270) -> "@1100,270"。"""
    return "@%g,%g" % (x, y)


def _is_free(ref):
    return isinstance(ref, str) and ref.startswith("@")


def _free_xy(ref):
    x, y = ref[1:].split(",")
    return (float(x), float(y))


@dataclass
class Instance:
    id: str          # 全局唯一
    symbol: str      # iec_symbols 中的函数名
    tag: str         # 位号，如 "KM"
    partno: str      # 型号，如 "CJX2-1210"
    x: float         # 锚点
    y: float
    remap: dict = field(default_factory=dict)   # {库端子编号: 显示编号}
    label_at: tuple = None  # 位号标注位置（绝对坐标），型号画在其下方


@dataclass
class Wire:
    a_id: str        # 实例 id 或 "@x,y" 自由点
    a_term: str      # 端子编号（显示编号；自由点时忽略）
    b_id: str
    b_term: str
    via: tuple = ()  # 中间拐点 [(x,y), ...]


class Circuit:
    def __init__(self):
        self.instances = {}
        self.wires = []

    def add_instance(self, inst):
        if inst.id in self.instances:
            raise ValueError("实例 id 重复: %s" % inst.id)
        self.instances[inst.id] = inst

    def add_wire(self, w):
        self.wires.append(w)

    @staticmethod
    def _lib_nums(symbol):
        return {num for num, _, _ in TERMINALS[symbol]}

    @staticmethod
    def resolve(inst, term):
        """显示编号 -> 库编号（经 remap 逆映射）。"""
        inv = {v: k for k, v in inst.remap.items()}
        return inv.get(term, term)

    def terminal_pos(self, ref, term):
        """端子绝对坐标。"""
        if _is_free(ref):
            return _free_xy(ref)
        inst = self.instances[ref]
        lib = self.resolve(inst, term)
        dx, dy = next((dx, dy) for n, dx, dy in TERMINALS[inst.symbol]
                      if n == lib)
        return (inst.x + dx, inst.y + dy)

    def validate(self):
        """返回错误列表；空列表 = 通过。"""
        errs = []
        for iid, inst in self.instances.items():
            if inst.symbol not in TERMINALS:
                errs.append("实例 %s: 符号 %s 不存在" % (iid, inst.symbol))
                continue
            lib_nums = self._lib_nums(inst.symbol)
            for k in inst.remap:
                if k not in lib_nums:
                    errs.append("实例 %s: remap 键 %s 不在库端子中" % (iid, k))
            if len(set(inst.remap.values())) != len(inst.remap):
                errs.append("实例 %s: remap 值重复，非双射" % iid)
        for i, w in enumerate(self.wires):
            for ref, term, side in ((w.a_id, w.a_term, "a"),
                                    (w.b_id, w.b_term, "b")):
                if _is_free(ref):
                    continue
                if ref not in self.instances:
                    errs.append("Wire[%d].%s: 实例 %s 不存在" % (i, side, ref))
                    continue
                inst = self.instances[ref]
                if inst.symbol not in TERMINALS:
                    continue
                if self.resolve(inst, term) not in self._lib_nums(inst.symbol):
                    errs.append("Wire[%d].%s: 端子 %s 不在符号 %s 的端子表中"
                                % (i, side, term, inst.symbol))
        return errs

    # ---------- 渲染 ----------

    @staticmethod
    def _manhattan(ctx, pts, w=3, color=None):
        """画直角折线；相邻两点不共线时按"先横后竖"补拐点。返回实际路径点。"""
        path = [pts[0]]
        for p in pts[1:]:
            q = path[-1]
            if q[0] != p[0] and q[1] != p[1]:
                path.append((p[0], q[1]))
            path.append(p)
        for a, b in zip(path, path[1:]):
            ctx.wire(a[0], a[1], b[0], b[1], w=w, color=color)
        return path

    def render(self, W=1600, H=1000, title="", subtitle="", notes=(),
               extra_labels=()):
        """组装 mxfile，返回 root。extra_labels: [(x, y, 文本, 字号), ...]。"""
        mxfile = ET.Element("mxfile", host="muse", type="device")
        diagram = ET.SubElement(mxfile, "diagram", id="circ", name="Page-1")
        model = ET.SubElement(diagram, "mxGraphModel",
                              pageWidth=str(W), pageHeight=str(H))
        root = ET.SubElement(model, "root")
        ET.SubElement(root, "mxCell", id="0")
        ET.SubElement(root, "mxCell", id="1", parent="0")
        ctx = Ctx(root)
        ctx.rect(0, 0, W, H, fill="#000000", stroke="#000000", sw=1)

        if title:
            ctx.text(W // 2, 42, title, 34)
        if subtitle:
            ctx.text(W // 2, 84, subtitle, 20)
        for i, n in enumerate(notes):
            ctx.text(W // 2, H - 110 + i * 36, n, 18, color="#BBBBBB")
        for x, y, s, size in extra_labels:
            ctx.text(x, y, s, size)

        # 1) 实例几何
        for inst in self.instances.values():
            getattr(S, inst.symbol)(ctx, inst.x, inst.y)

        # 2) 导线
        term_pts = set()
        for inst in self.instances.values():
            for num, dx, dy in TERMINALS[inst.symbol]:
                term_pts.add((inst.x + dx, inst.y + dy))
        end_counter = Counter()
        for w in self.wires:
            a = self.terminal_pos(w.a_id, w.a_term)
            b = self.terminal_pos(w.b_id, w.b_term)
            path = self._manhattan(ctx, [a] + list(w.via) + [b])
            for p in path:
                end_counter[(round(p[0], 3), round(p[1], 3))] += 1

        # 3) 端子红点 + 分支点红点（三段以上交汇、且非端子处）
        for inst in self.instances.values():
            for num, dx, dy in TERMINALS[inst.symbol]:
                ctx.dot(inst.x + dx, inst.y + dy, r=7)
        for (x, y), c in end_counter.items():
            if c >= 3 and (x, y) not in term_pts:
                ctx.dot(x, y, r=7)

        # 4) 位号 + 型号
        for inst in self.instances.values():
            if inst.label_at:
                lx, ly = inst.label_at
                ctx.text(lx, ly, inst.tag, 24)
                ctx.text(lx, ly + 32, inst.partno, 16, color="#CCCCCC")

        return mxfile
