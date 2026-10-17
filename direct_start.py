#!/usr/bin/env python3
"""直接启动电路（端到端验证 v1）：实例化（位号+型号）+ 线改"连接"。

标准接线：主回路 L1/L2/L3 -> QF -> KM主触点 -> FR热元件 -> M；
控制回路 Lc -> SB1(常闭停止) -> [SB2(常开启动) // KM常开自锁] -> KM线圈
  -> FR常闭(95-96) -> N。
"""
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circuit import Circuit, Instance, Wire, P


def build():
    """组装直接启动电路，返回 Circuit。"""
    c = Circuit()

# ---------- 实例（9 个；型号为教学常用占位） ----------
    c.add_instance(Instance("QF", "circuit_breaker_3p", "QF", "DZ47-63/3P C32",
                            280, 130, label_at=(168, 161)))
    c.add_instance(Instance("KMm", "contactor_main_contact", "KM", "CJX2-1210",
                            280, 290, label_at=(168, 316)))
    c.add_instance(Instance("FRm", "thermal_relay_3p", "FR", "JR36-20",
                            130, 440, label_at=(92, 465)))
    c.add_instance(Instance("M", "motor_3ph", "M", "Y112M-4 4kW",
                            280, 660, label_at=(196, 660)))
    c.add_instance(Instance("SB1", "nc_pushbutton", "SB1", "LAY3-01",
                            1100, 190, label_at=(1008, 190)))
    c.add_instance(Instance("SB2", "pushbutton", "SB2", "LAY3-10",
                            1040, 340, label_at=(948, 340)))
    c.add_instance(Instance("KMa", "no_contact", "KM", "CJX2-1210",
                            1160, 314, label_at=(1252, 340)))
    c.add_instance(Instance("KMc", "coil", "KM", "CJX2-1210",
                            1100, 500, label_at=(982, 514)))
    # FR 辅助常闭触点：标准编号 95-96，库中 nc_contact 声明为 21/22，经重命名实现
    c.add_instance(Instance("FRa", "nc_contact", "FR", "JR36-20",
                            1100, 604, remap={"21": "95", "22": "96"},
                            label_at=(1008, 630)))

    # ---------- 接线（21 根：主回路 12 + 控制回路 9） ----------
    # 主回路 A 相
    c.add_wire(Wire(P(240, 100), "", "QF", "1"))
    c.add_wire(Wire("QF", "2", "KMm", "1", via=((240, 240), (246, 240))))
    c.add_wire(Wire("KMm", "2", "FRm", "1", via=((246, 390), (200, 390))))
    c.add_wire(Wire("FRm", "2", "M", "U", via=((200, 600), (280, 600))))
    # 主回路 B 相
    c.add_wire(Wire(P(280, 100), "", "QF", "3"))
    c.add_wire(Wire("QF", "4", "KMm", "3"))
    c.add_wire(Wire("KMm", "4", "FRm", "3", via=((280, 390), (335, 390))))
    c.add_wire(Wire("FRm", "4", "M", "V", via=((335, 640), (252, 640))))
    # 主回路 C 相
    c.add_wire(Wire(P(320, 100), "", "QF", "5"))
    c.add_wire(Wire("QF", "6", "KMm", "5", via=((320, 240), (314, 240))))
    c.add_wire(Wire("KMm", "6", "FRm", "5", via=((314, 400), (470, 400))))
    c.add_wire(Wire("FRm", "6", "M", "W", via=((470, 680), (308, 680))))
    # 主回路顶部母线
    c.add_wire(Wire(P(190, 100), "", P(370, 100), ""))

    # 控制回路
    c.add_wire(Wire(P(1100, 120), "", "SB1", "11"))          # Lc -> SB1
    c.add_wire(Wire("SB1", "12", P(1100, 270), ""))          # SB1 -> N1
    c.add_wire(Wire(P(1100, 270), "", "SB2", "13",
                    via=((1040, 270),)))                     # N1 -> SB2
    c.add_wire(Wire(P(1100, 270), "", "KMa", "13",
                    via=((1160, 270),)))                     # N1 -> KMa（自锁支路）
    c.add_wire(Wire("SB2", "14", P(1100, 410), "",
                    via=((1040, 410),)))                     # SB2 -> N2
    c.add_wire(Wire("KMa", "14", P(1100, 410), "",
                    via=((1160, 410),)))                     # KMa -> N2
    c.add_wire(Wire(P(1100, 410), "", "KMc", "A1",
                    via=((1100, 514),)))                     # N2 -> KM线圈
    c.add_wire(Wire("KMc", "A2", "FRa", "95",
                    via=((1132, 570), (1100, 570))))         # KM线圈 -> FR 95
    c.add_wire(Wire("FRa", "96", P(1100, 720), ""))          # FR 96 -> N

    return c

# ---------- 校验 ----------
def main(version="v1"):
    if version == "v6":
        return main_v6()
    if version == "v5":
        return main_v5()
    if version == "v4":
        return main_v4()
    if version == "v3":
        return main_v3()
    if version == "v2":
        return main_v2()
    c = build()
    errs = c.validate()
    print("validate:", "通过" if not errs else "失败")
    for e in errs:
        print("  -", e)
    print("实例数:", len(c.instances), "| 接线数:", len(c.wires))
    if errs:
        sys.exit(1)

    # ---------- 渲染 ----------
    W, H = 1600, 1000
    labels = [
        (240, 70, "L1", 20), (280, 70, "L2", 20), (320, 70, "L3", 20),
        (90, 130, "主回路", 22),
        (1100, 748, "N", 20),
        (1150, 142, "Lc", 20),
        (1300, 150, "控制回路", 22),
        (1140, 248, "N1", 16), (1140, 434, "N2", 16),
    ]
    notes = [
        "注：型号为示例占位；FR 辅助常闭触点标准编号 95-96，本图以 nc_contact 符号经端子重命名（21→95、22→96）实现",
        "三极符号极距统一 80px（QF/KM 主触点/FR），相间垂线笔直，电气连接正确优先",
        "N1、N2 为导线分支点（红点）；SB2 与 KM 常开触点并联构成自锁",
    ]
    mxfile = c.render(W, H,
                      title="直接启动电路（端到端验证 v1）",
                      subtitle="9 实例 / 22 接线 · 位号+型号实例化 · 线=端子间连接 · 型号为示例",
                      notes=notes, extra_labels=labels)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "direct_start_v1.drawio")
    ET.ElementTree(mxfile).write(out, encoding="unicode")
    print("written:", out)


# ---------- v2：极距统一 80px + KM 线圈旋转 ----------
def build_v2():
    """直接启动电路 v2：三极符号极距统一 80px（三相垂线笔直）；
    KM 线圈 rotation=270（A1 上、A2 下），纵向控制回路无多余折弯。"""
    c = Circuit()

    # ---------- 实例（9 个；型号为教学常用占位） ----------
    c.add_instance(Instance("QF", "circuit_breaker_3p", "QF", "DZ47-63/3P C32",
                            280, 130, label_at=(168, 161)))
    c.add_instance(Instance("KMm", "contactor_main_contact", "KM", "CJX2-1210",
                            280, 290, label_at=(168, 316)))
    c.add_instance(Instance("FRm", "thermal_relay_3p", "FR", "JR36-20",
                            200, 440, label_at=(92, 465)))
    c.add_instance(Instance("M", "motor_3ph", "M", "Y112M-4 4kW",
                            280, 660, label_at=(196, 660)))
    c.add_instance(Instance("SB1", "nc_pushbutton", "SB1", "LAY3-01",
                            1100, 190, label_at=(1008, 190)))
    c.add_instance(Instance("SB2", "pushbutton", "SB2", "LAY3-10",
                            1040, 340, label_at=(948, 340)))
    c.add_instance(Instance("KMa", "no_contact", "KM", "CJX2-1210",
                            1160, 314, label_at=(1252, 340)))
    # KM 线圈旋转 270°：A1 上、A2 下（按 _rot 公式；视觉上即顺时针 90°）
    c.add_instance(Instance("KMc", "coil", "KM", "CJX2-1210",
                            1114, 500, rotation=270, label_at=(982, 500)))
    # FR 辅助常闭触点：标准编号 95-96，库中 nc_contact 声明为 21/22，经重命名实现
    c.add_instance(Instance("FRa", "nc_contact", "FR", "JR36-20",
                            1100, 604, remap={"21": "95", "22": "96"},
                            label_at=(1008, 630)))

    # ---------- 接线（21 根；三相垂线 x=240/280/320 笔直） ----------
    # 三相独立引下（L1/L2/L3 各自独立，顶部不再用横线短接）
    c.add_wire(Wire(P(240, 100), "", "QF", "1"))
    c.add_wire(Wire(P(280, 100), "", "QF", "3"))
    c.add_wire(Wire(P(320, 100), "", "QF", "5"))
    # QF -> KM 主触点（笔直垂线）
    c.add_wire(Wire("QF", "2", "KMm", "1"))
    c.add_wire(Wire("QF", "4", "KMm", "3"))
    c.add_wire(Wire("QF", "6", "KMm", "5"))
    # KM 主触点 -> FR（笔直垂线）
    c.add_wire(Wire("KMm", "2", "FRm", "1"))
    c.add_wire(Wire("KMm", "4", "FRm", "3"))
    c.add_wire(Wire("KMm", "6", "FRm", "5"))
    # FR -> M（电机端子一字排开，笔直垂线零折弯）
    c.add_wire(Wire("FRm", "2", "M", "U"))
    c.add_wire(Wire("FRm", "4", "M", "V"))
    c.add_wire(Wire("FRm", "6", "M", "W"))

    # 控制回路
    c.add_wire(Wire(P(1100, 120), "", "SB1", "11"))          # Lc -> SB1
    c.add_wire(Wire("SB1", "12", P(1100, 270), ""))          # SB1 -> N1
    c.add_wire(Wire(P(1100, 270), "", "SB2", "13",
                    via=((1040, 270),)))                     # N1 -> SB2
    c.add_wire(Wire(P(1100, 270), "", "KMa", "13",
                    via=((1160, 270),)))                     # N1 -> KMa（自锁支路）
    c.add_wire(Wire("SB2", "14", P(1100, 410), "",
                    via=((1040, 410),)))                     # SB2 -> N2
    c.add_wire(Wire("KMa", "14", P(1100, 410), "",
                    via=((1160, 410),)))                     # KMa -> N2
    c.add_wire(Wire(P(1100, 410), "", "KMc", "A1"))           # N2 -> A1（笔直）
    c.add_wire(Wire("KMc", "A2", "FRa", "95"))               # A2 -> FR 95（笔直）
    c.add_wire(Wire("FRa", "96", P(1100, 720), ""))          # FR 96 -> N（笔直）

    return c


def main_v2():
    c = build_v2()
    errs = c.validate()
    print("validate:", "通过" if not errs else "失败")
    for e in errs:
        print("  -", e)
    print("实例数:", len(c.instances), "| 接线数:", len(c.wires))
    if errs:
        sys.exit(1)

    W, H = 1600, 1000
    labels = [
        (240, 70, "L1", 20), (280, 70, "L2", 20), (320, 70, "L3", 20),
        (90, 130, "主回路", 22),
        (1100, 748, "N", 20),
        (1150, 142, "Lc", 20),
        (1300, 150, "控制回路", 22),
        (1140, 248, "N1", 16), (1140, 434, "N2", 16),
    ]
    notes = [
        "注：型号为示例占位；FR 辅助常闭触点标准编号 95-96，本图以 nc_contact 符号经端子重命名（21→95、22→96）实现",
        "三极符号极距统一 80px（QF/KM 主触点/FR），三相垂线笔直无折线；KM 线圈旋转 270°（A1 上、A2 下），控制回路无多余折弯",
        "N1、N2 为导线分支点（红点）；SB2 与 KM 常开触点并联构成自锁",
    ]
    mxfile = c.render(W, H,
                      title="直接启动电路（端到端验证 v2）",
                      subtitle="9 实例 / 22 接线 · 极距统一 80px · 实例旋转 · 型号为示例",
                      notes=notes, extra_labels=labels)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "direct_start_v2.drawio")
    ET.ElementTree(mxfile).write(out, encoding="unicode")
    print("written:", out)


def main_v3():
    """v3：FR 去大外框（三个独立热元件），其余同 v2。"""
    c = build_v2()
    errs = c.validate()
    print("validate:", "通过" if not errs else "失败")
    for e in errs:
        print("  -", e)
    print("实例数:", len(c.instances), "| 接线数:", len(c.wires))
    if errs:
        sys.exit(1)

    W, H = 1600, 1000
    labels = [
        (240, 70, "L1", 20), (280, 70, "L2", 20), (320, 70, "L3", 20),
        (90, 130, "主回路", 22),
        (1100, 748, "N", 20),
        (1150, 142, "Lc", 20),
        (1300, 150, "控制回路", 22),
        (1140, 248, "N1", 16), (1140, 434, "N2", 16),
    ]
    notes = [
        "注：型号为示例占位；FR 辅助常闭触点标准编号 95-96，本图以 nc_contact 符号经端子重命名（21→95、22→96）实现",
        "三极符号极距统一 80px（QF/KM 主触点/FR）；FR 为三个独立热元件（无外框），每相一个；KM 线圈旋转 270°（A1 上、A2 下）",
        "N1、N2 为导线分支点（红点）；SB2 与 KM 常开触点并联构成自锁",
    ]
    mxfile = c.render(W, H,
                      title="直接启动电路（端到端验证 v3）",
                      subtitle="9 实例 / 22 接线 · 极距统一 80px · FR 独立热元件 · 型号为示例",
                      notes=notes, extra_labels=labels)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "direct_start_v3.drawio")
    ET.ElementTree(mxfile).write(out, encoding="unicode")
    print("written:", out)


def main_v4():
    """v4：v3 + FR→M 电机线改走线（折弯挪到电机端，FR 端笔直）。"""
    c = build_v2()
    errs = c.validate()
    print("validate:", "通过" if not errs else "失败")
    for e in errs:
        print("  -", e)
    print("实例数:", len(c.instances), "| 接线数:", len(c.wires))
    if errs:
        sys.exit(1)

    W, H = 1600, 1000
    labels = [
        (240, 70, "L1", 20), (280, 70, "L2", 20), (320, 70, "L3", 20),
        (90, 130, "主回路", 22),
        (1100, 748, "N", 20),
        (1150, 142, "Lc", 20),
        (1300, 150, "控制回路", 22),
        (1140, 248, "N1", 16), (1140, 434, "N2", 16),
    ]
    notes = [
        "注：型号为示例占位；FR 辅助常闭触点标准编号 95-96，本图以 nc_contact 符号经端子重命名（21→95、22→96）实现",
        "三极符号极距统一（QF/KM 主触点/FR 相邻极距 40px）；FR 为三个独立热元件（无外框），每相一个；KM 线圈旋转 270°（A1 上、A2 下）",
        "N1、N2 为导线分支点（红点）；SB2 与 KM 常开触点并联构成自锁",
    ]
    mxfile = c.render(W, H,
                      title="直接启动电路（端到端验证 v4）",
                      subtitle="9 实例 / 22 接线 · 极距统一 · FR 独立热元件 · 型号为示例",
                      notes=notes, extra_labels=labels)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "direct_start_v4.drawio")
    ET.ElementTree(mxfile).write(out, encoding="unicode")
    print("written:", out)


def main_v5():
    """v5：v4 + 电机改为顶部接线盒式端子（U/V/W 一字排开），FR→M 笔直垂线零折弯。"""
    c = build_v2()
    errs = c.validate()
    print("validate:", "通过" if not errs else "失败")
    for e in errs:
        print("  -", e)
    print("实例数:", len(c.instances), "| 接线数:", len(c.wires))
    if errs:
        sys.exit(1)

    W, H = 1600, 1000
    labels = [
        (240, 70, "L1", 20), (280, 70, "L2", 20), (320, 70, "L3", 20),
        (90, 130, "主回路", 22),
        (1100, 748, "N", 20),
        (1150, 142, "Lc", 20),
        (1300, 150, "控制回路", 22),
        (1140, 248, "N1", 16), (1140, 434, "N2", 16),
    ]
    notes = [
        "注：型号为示例占位；FR 辅助常闭触点标准编号 95-96，本图以 nc_contact 符号经端子重命名（21→95、22→96）实现",
        "三极符号极距统一（QF/KM 主触点/FR 相邻极距 40px）；FR 为三个独立热元件（无外框），每相一个；KM 线圈旋转 270°（A1 上、A2 下）",
        "电机为顶部接线盒式（U/V/W 一字排开 40px），FR→M 三线笔直垂线零折弯",
        "N1、N2 为导线分支点（红点）；SB2 与 KM 常开触点并联构成自锁",
    ]
    mxfile = c.render(W, H,
                      title="直接启动电路（端到端验证 v5）",
                      subtitle="9 实例 / 22 接线 · 极距统一 · FR 独立热元件 · 电机接线盒 · 型号为示例",
                      notes=notes, extra_labels=labels)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "direct_start_v5.drawio")
    ET.ElementTree(mxfile).write(out, encoding="unicode")
    print("written:", out)


def main_v6():
    """v6：v5 去掉顶部三相短接横线（W1），L1/L2/L3 独立引下；RotCtx.dot 修 color 透传。"""
    c = build_v2()
    errs = c.validate()
    print("validate:", "通过" if not errs else "失败")
    for e in errs:
        print("  -", e)
    print("实例数:", len(c.instances), "| 接线数:", len(c.wires))
    if errs:
        sys.exit(1)

    W, H = 1600, 1000
    labels = [
        (240, 70, "L1", 20), (280, 70, "L2", 20), (320, 70, "L3", 20),
        (90, 130, "主回路", 22),
        (1100, 748, "N", 20),
        (1150, 142, "Lc", 20),
        (1300, 150, "控制回路", 22),
        (1140, 248, "N1", 16), (1140, 434, "N2", 16),
    ]
    notes = [
        "注：型号为示例占位；FR 辅助常闭触点标准编号 95-96，本图以 nc_contact 符号经端子重命名（21→95、22→96）实现",
        "三极符号极距统一（QF/KM 主触点/FR 相邻极距 40px）；FR 为三个独立热元件（无外框），每相一个；KM 线圈旋转 270°（A1 上、A2 下）",
        "电机为顶部接线盒式（U/V/W 一字排开 40px），FR→M 三线笔直垂线零折弯；L1/L2/L3 独立引下，顶部无横线",
        "N1、N2 为导线分支点（红点）；SB2 与 KM 常开触点并联构成自锁",
    ]
    mxfile = c.render(W, H,
                      title="直接启动电路（端到端验证 v6）",
                      subtitle="9 实例 / 21 接线 · 极距统一 · FR 独立热元件 · 电机接线盒 · 型号为示例",
                      notes=notes, extra_labels=labels)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "direct_start_v6.drawio")
    ET.ElementTree(mxfile).write(out, encoding="unicode")
    print("written:", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "v1")
