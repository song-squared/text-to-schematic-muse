#!/usr/bin/env python3
"""三相电动机正反转控制原理图（自动生成）。

主回路：L1/L2/L3 母排 → QF(3P) → KM1/KM2(3P, 并联) → FR(3P) → M1。
  KM1 正转：L1→U, L2→V, L3→W（直连）。
  KM2 反转：L1→W, L2→V, L3→U（L1/L3 换相，交叉线用跨线圆弧）。
控制回路：
  Lc → SB0(NC) → [SB1(NO)‖KM1_NO] → KM2_NC → KM1线圈 → FR(95-96 NC) → N（正转支路）
  Lc → SB0(NC) → [SB2(NO)‖KM2_NO] → KM1_NC → KM2线圈 → FR(95-96 NC) → N（反转支路）
  KM1/KM2 间另有机械互锁（虚线表示，非电气连接）。

用法：python3 forward_reverse.py  → 生成 forward_reverse.drawio
"""
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circuit import Circuit, Instance, Wire, P


def build():
    c = Circuit()

    # ================= 主回路 =================
    # QF
    c.add_instance(Instance("QF", "circuit_breaker_3p", "QF", "DZ47-63/3P C32",
                            x=280, y=150, label_at=(90, 170)))
    # KM1 主触点（正转）
    c.add_instance(Instance("KM1m", "contactor_main_contact", "KM1", "CJX2-1210",
                            x=280, y=300, label_at=(90, 320)))
    # KM2 主触点（反转）
    c.add_instance(Instance("KM2m", "contactor_main_contact", "KM2", "CJX2-1210",
                            x=480, y=300, label_at=(560, 320)))
    # FR 热继电器
    c.add_instance(Instance("FRm", "thermal_relay_3p", "FR", "JR36-20",
                            x=200, y=440, label_at=(90, 460)))
    # M1 电机
    c.add_instance(Instance("M1", "motor_3ph", "M1", "Y112M-4 4kW",
                            x=280, y=580, label_at=(90, 600)))

    # ---------- 主回路接线 ----------
    # 三相母排（复用 v8 画法）
    c.add_wire(Wire(P(200, 55), "", P(240, 55), ""))
    c.add_wire(Wire(P(240, 55), "", P(350, 55), ""))
    c.add_wire(Wire(P(240, 55), "", "QF", "1"))
    c.add_wire(Wire(P(200, 80), "", P(280, 80), ""))
    c.add_wire(Wire(P(280, 80), "", P(350, 80), ""))
    c.add_wire(Wire(P(280, 80), "", "QF", "3"))
    c.add_wire(Wire(P(200, 105), "", P(320, 105), ""))
    c.add_wire(Wire(P(320, 105), "", P(350, 105), ""))
    c.add_wire(Wire(P(320, 105), "", "QF", "5"))
    # QF → KM1（直连，垂直）
    c.add_wire(Wire("QF", "2", "KM1m", "1"))
    c.add_wire(Wire("QF", "4", "KM1m", "3"))
    c.add_wire(Wire("QF", "6", "KM1m", "5"))
    # QF → KM2（并联，向右；在 QF 输出下方间隙分层走，不进 QF 符号）
    c.add_wire(Wire("QF", "2", "KM2m", "1", via=((240, 232), (440, 232))))
    c.add_wire(Wire("QF", "4", "KM2m", "3", via=((280, 254), (480, 254))))
    c.add_wire(Wire("QF", "6", "KM2m", "5", via=((320, 276), (520, 276))))
    # KM1 → FR（正转，直连）
    c.add_wire(Wire("KM1m", "2", "FRm", "1"))
    c.add_wire(Wire("KM1m", "4", "FRm", "3"))
    c.add_wire(Wire("KM1m", "6", "FRm", "5"))
    # KM2 → FR（反转，L1/L3 换相；交叉处自动画圆弧）
    # KM2:2(L1) → FR:5(W)；KM2:4(L2) → FR:3(V)；KM2:6(L3) → FR:1(U)
    c.add_wire(Wire("KM2m", "2", "FRm", "5",
                    via=((440, 375), (300, 375), (300, 435))))
    c.add_wire(Wire("KM2m", "4", "FRm", "3",
                    via=((480, 397), (260, 397), (260, 435))))
    c.add_wire(Wire("KM2m", "6", "FRm", "1",
                    via=((520, 419), (220, 419), (220, 435))))
    # FR → M1
    c.add_wire(Wire("FRm", "2", "M1", "U"))
    c.add_wire(Wire("FRm", "4", "M1", "V"))
    c.add_wire(Wire("FRm", "6", "M1", "W"))

    # ================= 控制回路 =================
    # SB0 停止（常闭）
    c.add_instance(Instance("SB0", "nc_pushbutton", "SB0", "LAY3-01",
                            x=1150, y=170, label_at=(1080, 170)))
    # SB1 正转启动（常开）
    c.add_instance(Instance("SB1", "pushbutton", "SB1", "LAY3-10",
                            x=1100, y=270, label_at=(1030, 270)))
    # SB2 反转启动（常开）
    c.add_instance(Instance("SB2", "pushbutton", "SB2", "LAY3-10",
                            x=1200, y=270, label_at=(1270, 270)))
    # KM1 自锁常开
    c.add_instance(Instance("KM1a", "no_contact", "KM1", "CJX2-1210",
                            x=1070, y=360, label_at=(1000, 380)))
    # KM2 自锁常开
    c.add_instance(Instance("KM2a", "no_contact", "KM2", "CJX2-1210",
                            x=1230, y=360, label_at=(1300, 380)))
    # KM2 互锁常闭（串在正转支路）
    c.add_instance(Instance("KM2b", "nc_contact", "KM2", "CJX2-1210",
                            x=1100, y=480, label_at=(1030, 500),
                            remap={"21": "21", "22": "22"}))
    # KM1 互锁常闭（串在反转支路）
    c.add_instance(Instance("KM1b", "nc_contact", "KM1", "CJX2-1210",
                            x=1200, y=480, label_at=(1270, 500),
                            remap={"21": "21", "22": "22"}))
    # KM1 线圈（旋转 270°，A1 上）
    c.add_instance(Instance("KM1c", "coil", "KM1", "CJX2-1210",
                            x=1100, y=580, rotation=270, label_at=(1030, 600)))
    # KM2 线圈
    c.add_instance(Instance("KM2c", "coil", "KM2", "CJX2-1210",
                            x=1200, y=580, rotation=270, label_at=(1270, 600)))
    # FR 95-96 常闭（过载保护）
    c.add_instance(Instance("FRa", "nc_contact", "FR", "JR36-20",
                            x=1150, y=680, label_at=(1080, 700),
                            remap={"21": "95", "22": "96"}))

    # ---------- 控制回路接线 ----------
    # Lc → SB0
    c.add_wire(Wire(P(1150, 120), "", "SB0", "11"))
    # SB0 → 分支点 B1
    c.add_wire(Wire("SB0", "12", P(1150, 220), ""))
    # B1 → 正转支路 SB1
    c.add_wire(Wire(P(1150, 220), "", "SB1", "13", via=((1100, 220),)))
    # B1 → 反转支路 SB2
    c.add_wire(Wire(P(1150, 220), "", "SB2", "13", via=((1200, 220),)))
    # 正转支路：SB1 → B2；KM1a 自锁并联在 SB1 两端（B1→B2）
    c.add_wire(Wire("SB1", "14", P(1100, 320), ""))
    c.add_wire(Wire(P(1150, 220), "", "KM1a", "13", via=((1070, 220),)))
    c.add_wire(Wire("KM1a", "14", P(1100, 320), "", via=((1070, 412), (1100, 412))))
    # B2 → KM2 互锁常闭 → KM1 线圈
    c.add_wire(Wire(P(1100, 320), "", "KM2b", "21"))
    c.add_wire(Wire("KM2b", "22", "KM1c", "A1"))
    # 反转支路：SB2 → B5；KM2a 自锁并联在 SB2 两端（B1→B5）
    c.add_wire(Wire("SB2", "14", P(1200, 320), ""))
    c.add_wire(Wire(P(1150, 220), "", "KM2a", "13", via=((1230, 220),)))
    c.add_wire(Wire("KM2a", "14", P(1200, 320), "", via=((1230, 412), (1200, 412))))
    # B5 → KM1 互锁常闭 → KM2 线圈
    c.add_wire(Wire(P(1200, 320), "", "KM1b", "21"))
    c.add_wire(Wire("KM1b", "22", "KM2c", "A1"))
    # 两线圈下端汇合 → FR 95-96 → N
    c.add_wire(Wire("KM1c", "A2", P(1150, 660), "", via=((1150, 632),)))
    c.add_wire(Wire("KM2c", "A2", P(1150, 660), "", via=((1150, 632),)))
    c.add_wire(Wire(P(1150, 660), "", "FRa", "95"))
    c.add_wire(Wire("FRa", "96", P(1150, 740), ""))

    return c


def main():
    c = build()
    errs = c.validate()
    print("validate:", "通过" if not errs else "失败")
    for e in errs:
        print("  -", e)
    print("实例数:", len(c.instances), "| 接线数:", len(c.wires))
    if errs:
        sys.exit(1)

    W, H = 1600, 1000
    labels = [
        (180, 55, "L1", 20), (180, 80, "L2", 20), (180, 105, "L3", 20),
        (90, 130, "主回路", 22),
        (1150, 100, "Lc", 20),
        (1150, 760, "N", 20),
        (1350, 150, "控制回路", 22),
        (1150, 240, "B1", 14),
    ]
    notes = [
        "注：KM2 反转经 L1/L3 换相（KM2:2→FR:5、KM2:6→FR:1），交叉处自动画跨线圆弧",
        "KM1/KM2 各用本接触器常开自锁，对方常闭电气互锁；另有机械互锁（虚线）",
        "FR 95-96 常闭参与过载保护；型号为示例",
    ]
    # 机械互锁虚线：KM1/KM2 主触点之间、线圈之间
    mech = [((320, 326), (440, 326)), ((1100, 580), (1200, 580))]
    mxfile = c.render(W, H,
                      title="三相电动机正反转控制原理图",
                      subtitle="%d 实例 / %d 接线 · 型号为示例" % (len(c.instances), len(c.wires)),
                      notes=notes, extra_labels=labels, mech_links=mech)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "forward_reverse.drawio")
    ET.ElementTree(mxfile).write(out, encoding="unicode")
    print("written:", out)


if __name__ == "__main__":
    main()
