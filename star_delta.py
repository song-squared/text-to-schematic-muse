#!/usr/bin/env python3
"""三相异步电动机星-三角降压启动原理图（自动生成）。

主回路：L1/L2/L3 母排 → QF(3P) → KM1(3P 主) → FR(3P) → M1(六端子)。
  KM2(星形)：U2/V2/W2 短接成星点。
  KM3(三角形)：U2→V1、V2→W1、W2→U1 交叉连接。
控制回路：
  Lc → SB0(NC) → [SB1(NO)‖KM1_NO] → KM1线圈 → FR(95-96) → N
  KT1/KT2 与 KM1 同时得电计时：
    KM2 支路：KM1_NO → KT1 延时 NC(15-16, 5s) → KM3_NC → KM2线圈
    KM3 支路：KM1_NO → KT2 延时 NO(15-18, 5.5s) → KM2_NC → KM3线圈
  KM2/KM3 电气互锁 + 机械互锁（虚线）。

用法：python3 star_delta.py  → 生成 star_delta.drawio
"""
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circuit import Circuit, Instance, Wire, P

# 时间参数（秒，可配置）
T_STAR = 5.0    # 星形启动持续
T_GAP = 0.5     # 切换间隔
T_DELTA = T_STAR + T_GAP  # 三角形投入


def build():
    c = Circuit()

    # ================= 主回路 =================
    c.add_instance(Instance("QF", "circuit_breaker_3p", "QF", "DZ47-63/3P C32",
                            x=280, y=150, label_at=(90, 170)))
    c.add_instance(Instance("KM1m", "contactor_main_contact", "KM1", "CJX2-1210",
                            x=280, y=300, label_at=(90, 320)))
    c.add_instance(Instance("KM2m", "contactor_main_contact", "KM2", "CJX2-1210",
                            x=520, y=300, label_at=(600, 320)))
    c.add_instance(Instance("KM3m", "contactor_main_contact", "KM3", "CJX2-1210",
                            x=760, y=300, label_at=(840, 320)))
    c.add_instance(Instance("FRm", "thermal_relay_3p", "FR", "JR36-20",
                            x=200, y=440, label_at=(90, 460)))
    c.add_instance(Instance("M1", "motor_3ph_6t", "M1", "Y132S-4 5.5kW",
                            x=280, y=620, label_at=(90, 640)))

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
    # KM1 → FR（直连）
    c.add_wire(Wire("KM1m", "2", "FRm", "1"))
    c.add_wire(Wire("KM1m", "4", "FRm", "3"))
    c.add_wire(Wire("KM1m", "6", "FRm", "5"))
    # FR → M1 上端（U1/V1/W1）
    c.add_wire(Wire("FRm", "2", "M1", "U1"))
    c.add_wire(Wire("FRm", "4", "M1", "V1"))
    c.add_wire(Wire("FRm", "6", "M1", "W1"))
    # KM2 星形：U2/V2/W2 → KM2:2/4/6；KM2:1/3/5 短接成星点
    c.add_wire(Wire("M1", "U2", "KM2m", "2", via=((240, 700), (480, 700))))
    c.add_wire(Wire("M1", "V2", "KM2m", "4", via=((280, 720), (520, 720))))
    c.add_wire(Wire("M1", "W2", "KM2m", "6", via=((320, 740), (560, 740))))
    c.add_wire(Wire("KM2m", "1", "KM2m", "3", via=((480, 280),)))
    c.add_wire(Wire("KM2m", "3", "KM2m", "5", via=((520, 280),)))
    # KM3 三角形：U2→V1、V2→W1、W2→U1
    #   KM3:1 ← FR:4(V1)，KM3:2 → M1:U2
    #   KM3:3 ← FR:6(W1)，KM3:4 → M1:V2
    #   KM3:5 ← FR:2(U1)，KM3:6 → M1:W2
    c.add_wire(Wire("FRm", "4", "KM3m", "1", via=((280, 500), (700, 500), (700, 300))))
    c.add_wire(Wire("KM3m", "2", "M1", "U2", via=((720, 600), (240, 600))))
    c.add_wire(Wire("FRm", "6", "KM3m", "3", via=((320, 520), (740, 520), (740, 300))))
    c.add_wire(Wire("KM3m", "4", "M1", "V2", via=((760, 620), (280, 620))))
    c.add_wire(Wire("FRm", "2", "KM3m", "5", via=((240, 540), (780, 540), (780, 300))))
    c.add_wire(Wire("KM3m", "6", "M1", "W2", via=((800, 640), (320, 640))))

    # ================= 控制回路 =================
    c.add_instance(Instance("SB0", "nc_pushbutton", "SB0", "LAY3-01",
                            x=1150, y=170, label_at=(1080, 170)))
    c.add_instance(Instance("SB1", "pushbutton", "SB1", "LAY3-10",
                            x=1150, y=270, label_at=(1080, 270)))
    c.add_instance(Instance("KM1a", "no_contact", "KM1", "CJX2-1210",
                            x=1070, y=360, label_at=(1000, 380)))
    c.add_instance(Instance("KM1b", "no_contact", "KM1", "CJX2-1210",
                            x=1150, y=450, label_at=(1080, 470)))
    c.add_instance(Instance("KM2b", "nc_contact", "KM3", "CJX2-1210",
                            x=1060, y=540, label_at=(990, 560),
                            remap={"21": "21", "22": "22"}))
    c.add_instance(Instance("KM3b", "nc_contact", "KM2", "CJX2-1210",
                            x=1240, y=540, label_at=(1310, 560),
                            remap={"21": "21", "22": "22"}))
    c.add_instance(Instance("KT1", "time_delay_nc", "KT1", "JSZ3A",
                            x=1100, y=630, label_at=(1030, 650),
                            remap={"15": "15", "16": "16"}))
    c.add_instance(Instance("KT2", "time_delay_no", "KT2", "JSZ3A",
                            x=1200, y=630, label_at=(1270, 650),
                            remap={"15": "15", "18": "18"}))
    c.add_instance(Instance("KM1c", "coil", "KM1", "CJX2-1210",
                            x=1150, y=750, rotation=270, label_at=(1080, 770)))
    c.add_instance(Instance("KM2c", "coil", "KM2", "CJX2-1210",
                            x=1060, y=850, rotation=270, label_at=(990, 870)))
    c.add_instance(Instance("KM3c", "coil", "KM3", "CJX2-1210",
                            x=1240, y=850, rotation=270, label_at=(1310, 870)))
    c.add_instance(Instance("KT1c", "time_relay_coil", "KT1", "JSZ3A",
                            x=1000, y=750, label_at=(930, 770)))
    c.add_instance(Instance("KT2c", "time_relay_coil", "KT2", "JSZ3A",
                            x=1300, y=750, label_at=(1370, 770)))
    c.add_instance(Instance("FRa", "nc_contact", "FR", "JR36-20",
                            x=1150, y=1030, label_at=(1080, 1050),
                            remap={"21": "95", "22": "96"}))

    # ---------- 控制回路接线 ----------
    # Lc → SB0 → B1
    c.add_wire(Wire(P(1150, 120), "", "SB0", "11"))
    c.add_wire(Wire("SB0", "12", P(1150, 220), ""))
    # B1 → SB1 → B2；B1 → KM1a(自锁) → B2
    c.add_wire(Wire(P(1150, 220), "", "SB1", "13", via=((1150, 220),)))
    c.add_wire(Wire("SB1", "14", P(1150, 320), ""))
    c.add_wire(Wire(P(1150, 220), "", "KM1a", "13", via=((1070, 220),)))
    c.add_wire(Wire("KM1a", "14", P(1150, 320), "", via=((1070, 412), (1150, 412))))
    # B2 → KM1 线圈 → FR → N（经 FR 95-96 串联，无旁路）
    c.add_wire(Wire(P(1150, 320), "", "KM1c", "A1"))
    c.add_wire(Wire("KM1c", "A2", P(1170, 1000), "", via=((1170, 802),)))
    # B2 → KT1/KT2 线圈（与 KM1 同时得电；走两侧，不穿触点）
    c.add_wire(Wire(P(1150, 320), "", "KT1c", "A1", via=((1000, 320),)))
    c.add_wire(Wire("KT1c", "A2", P(1060, 1000), "",
                via=((1070, 750), (1070, 1000))))
    c.add_wire(Wire(P(1150, 320), "", "KT2c", "A1", via=((1300, 320),)))
    c.add_wire(Wire("KT2c", "A2", P(1332, 1000), ""))
    # 返回母线 y=1000（分段，T 形汇接），经 FR:95 → FR:96 → N
    c.add_wire(Wire(P(1070, 1000), "", P(1060, 1000), ""))
    c.add_wire(Wire(P(1060, 1000), "", P(1150, 1000), ""))
    c.add_wire(Wire(P(1150, 1000), "", P(1170, 1000), ""))
    c.add_wire(Wire(P(1170, 1000), "", P(1240, 1000), ""))
    c.add_wire(Wire(P(1240, 1000), "", P(1332, 1000), ""))
    c.add_wire(Wire(P(1150, 1000), "", "FRa", "95"))
    # FR:96 → N（唯一返回路径）
    c.add_wire(Wire("FRa", "96", P(1150, 1090), ""))
    # KM2 星形支路：B2 → KM1b(NO) → KM2b(NC互锁) → KT1延时NC → KM2线圈
    c.add_wire(Wire(P(1150, 320), "", "KM1b", "13"))
    c.add_wire(Wire("KM1b", "14", "KM2b", "21", via=((1060, 502),)))
    c.add_wire(Wire("KM2b", "22", "KT1", "15", via=((1060, 630),)))
    c.add_wire(Wire("KT1", "16", "KM2c", "A1", via=((1060, 682), (1060, 818))))
    c.add_wire(Wire("KM2c", "A2", P(1060, 1000), ""))
    # KM3 三角支路：B2 → KM1b → KM3b(NC互锁) → KT2延时NO → KM3线圈
    c.add_wire(Wire("KM1b", "14", "KM3b", "21", via=((1240, 502),)))
    c.add_wire(Wire("KM3b", "22", "KT2", "15", via=((1240, 630),)))
    c.add_wire(Wire("KT2", "18", "KM3c", "A1", via=((1240, 682), (1240, 818))))
    c.add_wire(Wire("KM3c", "A2", P(1240, 1000), ""))

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

    W, H = 1700, 1250
    labels = [
        (180, 55, "L1", 20), (180, 80, "L2", 20), (180, 105, "L3", 20),
        (90, 130, "主回路", 22),
        (1150, 100, "Lc", 20),
        (1150, 1110, "N", 20),
        (1400, 150, "控制回路", 22),
        (1150, 240, "B1", 14),
    ]
    notes = [
        "注：星形启动 %gs → 切换间隔 %gs → 三角形运行；KM2 星点短接 U2/V2/W2，KM3 交叉接成三角形" % (T_STAR, T_GAP),
        "KM1 自锁；KT1 延时 NC 切星形，KT2 延时 NO 投三角形；KM2/KM3 电气互锁 + 机械互锁（虚线）",
        "FR 95-96 常闭参与过载保护；型号为示例",
    ]
    mech = [((560, 326), (720, 326))]
    mxfile = c.render(W, H,
                      title="三相异步电动机星-三角降压启动原理图",
                      subtitle="%d 实例 / %d 接线 · 型号为示例" % (len(c.instances), len(c.wires)),
                      notes=notes, extra_labels=labels, mech_links=mech)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "star_delta.drawio")
    ET.ElementTree(mxfile).write(out, encoding="unicode")
    print("written:", out)


if __name__ == "__main__":
    main()
