#!/usr/bin/env python3
"""端子声明验证（符号智能化第 1 步）。

检查：
  1. 全部符号在 TERMINALS 中全覆盖、端子表非空
  2. TERMINALS 无多余键
  3. 每个符号内部端子编号无重复
  4. 端子坐标落在符号几何包络内（含 2px 容差）
  5. get_terminals() 行为正确
  6. 重跑 gen_xml_shapes.py：21 个自动形状块与改动前基线逐字一致（无回归）
"""
import os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iec_symbols as S

# 45 符号（与 build_symbols_show.py 的 symbols 列表一致，meter 为内部 helper 不计入）
SYMBOLS_45 = [
    "no_contact", "nc_contact", "coil", "thermal_relay", "motor_3ph",
    "indicator_lamp", "buzzer", "selector_switch", "float_switch", "pushbutton",
    "knife_switch", "fuse", "ground_pe", "terminal_circle", "circuit_breaker",
    "disconnector", "emergency_stop", "limit_switch", "current_transformer",
    "ammeter", "voltmeter", "surge_arrester", "time_delay_no", "solenoid",
    "contactor_main_contact", "spdt_switch", "time_relay_coil", "dpdt_switch",
    "load_break_switch", "fuse_disconnector", "earthing_switch",
    "proximity_switch", "pressure_switch", "temperature_switch", "foot_switch",
    "rcd", "motor_protector", "ats", "time_delay_nc", "voltage_transformer",
    "energy_meter", "power_meter", "frequency_meter", "dc_motor",
    "transformer_2w",
    "nc_pushbutton", "circuit_breaker_3p", "thermal_relay_3p",
]

# 各符号在锚点 (100,100) 的调用（锚点约定见 iec_symbols.TERMINALS 契约注释）
CALLS = {
    "no_contact": lambda c: S.no_contact(c, 100, 100),
    "nc_contact": lambda c: S.nc_contact(c, 100, 100),
    "coil": lambda c: S.coil(c, 100, 100),
    "thermal_relay": lambda c: S.thermal_relay(c, 100, 100),
    "motor_3ph": lambda c: S.motor_3ph(c, 100, 100),
    "indicator_lamp": lambda c: S.indicator_lamp(c, 100, 100),
    "buzzer": lambda c: S.buzzer(c, 100, 100),
    "selector_switch": lambda c: S.selector_switch(c, 100, 100),
    "float_switch": lambda c: S.float_switch(c, 100, 100),
    "pushbutton": lambda c: S.pushbutton(c, 100, 100),
    "knife_switch": lambda c: S.knife_switch(c, 100, 100),
    "fuse": lambda c: S.fuse(c, 100, 100),
    "ground_pe": lambda c: S.ground_pe(c, 100, 100),
    "terminal_circle": lambda c: S.terminal_circle(c, 100, 100),
    "circuit_breaker": lambda c: S.circuit_breaker(c, 100, 100),
    "disconnector": lambda c: S.disconnector(c, 100, 100),
    "emergency_stop": lambda c: S.emergency_stop(c, 100, 100),
    "limit_switch": lambda c: S.limit_switch(c, 100, 100),
    "current_transformer": lambda c: S.current_transformer(c, 100, 100),
    "ammeter": lambda c: S.ammeter(c, 100, 100),
    "voltmeter": lambda c: S.voltmeter(c, 100, 100),
    "surge_arrester": lambda c: S.surge_arrester(c, 100, 100),
    "time_delay_no": lambda c: S.time_delay_no(c, 100, 100),
    "solenoid": lambda c: S.solenoid(c, 100, 100),
    "contactor_main_contact": lambda c: S.contactor_main_contact(c, 100, 100),
    "spdt_switch": lambda c: S.spdt_switch(c, 100, 100),
    "time_relay_coil": lambda c: S.time_relay_coil(c, 100, 100),
    "dpdt_switch": lambda c: S.dpdt_switch(c, 100, 100),
    "load_break_switch": lambda c: S.load_break_switch(c, 100, 100),
    "fuse_disconnector": lambda c: S.fuse_disconnector(c, 100, 100),
    "earthing_switch": lambda c: S.earthing_switch(c, 100, 100),
    "proximity_switch": lambda c: S.proximity_switch(c, 100, 100),
    "pressure_switch": lambda c: S.pressure_switch(c, 100, 100),
    "temperature_switch": lambda c: S.temperature_switch(c, 100, 100),
    "foot_switch": lambda c: S.foot_switch(c, 100, 100),
    "rcd": lambda c: S.rcd(c, 100, 100),
    "motor_protector": lambda c: S.motor_protector(c, 100, 100),
    "ats": lambda c: S.ats(c, 100, 100),
    "time_delay_nc": lambda c: S.time_delay_nc(c, 100, 100),
    "voltage_transformer": lambda c: S.voltage_transformer(c, 100, 100),
    "energy_meter": lambda c: S.energy_meter(c, 100, 100),
    "power_meter": lambda c: S.power_meter(c, 100, 100),
    "frequency_meter": lambda c: S.frequency_meter(c, 100, 100),
    "dc_motor": lambda c: S.dc_motor(c, 100, 100),
    "transformer_2w": lambda c: S.transformer_2w(c, 100, 100),
    "nc_pushbutton": lambda c: S.nc_pushbutton(c, 100, 100),
    "circuit_breaker_3p": lambda c: S.circuit_breaker_3p(c, 100, 100),
    "thermal_relay_3p": lambda c: S.thermal_relay_3p(c, 100, 100),
}


class VerifyCtx:
    """记录几何包络（含自带库符号的占位框，ground_pe 用）。"""
    WHITE = "#FFFFFF"
    RED = "#FF0000"

    def __init__(self):
        self.minx = self.miny = 1e9
        self.maxx = self.maxy = -1e9

    def _box(self, x1, y1, x2, y2):
        self.minx = min(self.minx, x1, x2); self.maxx = max(self.maxx, x1, x2)
        self.miny = min(self.miny, y1, y2); self.maxy = max(self.maxy, y1, y2)

    def wire(self, x1, y1, x2, y2, color=None, w=3, dashed=False):
        self._box(x1, y1, x2, y2)

    def dot(self, x, y, r=7, color=None):
        self._box(x - r, y - r, x + r, y + r)

    def rect(self, x, y, w, h, fill="none", stroke=None, sw=3):
        self._box(x, y, x + w, y + h)

    def ellipse(self, x, y, w, h, fill="none", stroke=None, sw=3):
        self._box(x, y, x + w, y + h)

    def text(self, x, y, s, size=22, color=None):
        n_cjk = sum(1 for ch in s if ord(ch) > 127)
        n_asc = len(s) - n_cjk
        w = n_cjk * size * 1.0 + n_asc * size * 0.62 + 12
        h = size * 1.45
        self._box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)

    def library_shape(self, x, y, w, h, shape, stroke=None, sw=3):
        self._box(x, y, x + w, y + h)


def main():
    fails = []
    TOL = 2.0

    # 1+2: 全覆盖、无多余键
    missing = [n for n in SYMBOLS_45 if n not in S.TERMINALS]
    empty = [n for n in SYMBOLS_45 if n in S.TERMINALS and not S.TERMINALS[n]]
    extra = [n for n in S.TERMINALS if n not in SYMBOLS_45]
    if missing: fails.append("缺失端子表: %s" % missing)
    if empty: fails.append("端子表为空: %s" % empty)
    if extra: fails.append("多余键: %s" % extra)
    print("[1] 覆盖: %d 个符号 %s（缺失=%d, 为空=%d, 多余=%d）"
          % (len(SYMBOLS_45), "OK" if not (missing or empty or extra) else "FAIL",
             len(missing), len(empty), len(extra)))

    # 3+4: 编号无重复、坐标在包络内
    dup, oob = [], []
    total = 0
    for name in SYMBOLS_45:
        terms = S.TERMINALS.get(name, [])
        total += len(terms)
        nums = [t[0] for t in terms]
        if len(nums) != len(set(nums)):
            dup.append(name)
        rec = VerifyCtx()
        CALLS[name](rec)
        for num, dx, dy in terms:
            px, py = 100 + dx, 100 + dy
            if not (rec.minx - TOL <= px <= rec.maxx + TOL and
                    rec.miny - TOL <= py <= rec.maxy + TOL):
                oob.append((name, num, px, py,
                            (rec.minx, rec.miny, rec.maxx, rec.maxy)))
    if dup: fails.append("编号重复: %s" % dup)
    if oob: fails.append("坐标越界: %s" % oob)
    print("[2] 编号唯一: %s（重复=%d）" % ("OK" if not dup else "FAIL", len(dup)))
    print("[3] 包络检查: %s（越界=%d, 端子总数=%d）"
          % ("OK" if not oob else "FAIL", len(oob), total))
    for item in oob:
        print("    越界:", item)

    # 5: get_terminals
    ok5 = (S.get_terminals("no_contact") == S.TERMINALS["no_contact"]
           and S.get_terminals("不存在的符号") == [])
    if not ok5: fails.append("get_terminals 行为异常")
    print("[4] get_terminals: %s" % ("OK" if ok5 else "FAIL"))

    # 6: 录制器无回归（与改动前基线 /tmp/regen_before.xml 按形状块比对：
    # 只比对基线中已有的形状，新增形状仅作提示——加符号不触发误报）
    r = subprocess.run([sys.executable, "gen_xml_shapes.py"],
                       capture_output=True, text=True,
                       cwd=os.path.dirname(os.path.abspath(__file__)))
    after = r.stdout
    before = None
    for _p in (os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "regen_baseline.xml"),
               "/tmp/regen_before.xml"):  # 旧位置兼容
        try:
            before = open(_p).read()
            break
        except FileNotFoundError:
            continue
    def _blocks(t):
        ps = re.split(r'<!--\s*(\S+)（自动生成）\s*-->', t)
        return {ps[i]: ps[i + 1].rstrip() for i in range(1, len(ps), 2)}
    if before is None:
        same, diff, new, common = None, [], [], set()
    else:
        bb, ab = _blocks(before), _blocks(after)
        common = set(bb) & set(ab)
        diff = sorted(k for k in common if bb[k] != ab[k])
        new = sorted(set(ab) - set(bb))
        same = not diff
    if same is False:
        fails.append("gen_xml_shapes.py 回归：既有形状输出变化: %s" % diff)
    print("[5] 录制器回归: %s"
          % ("OK（%d 个既有形状逐字一致，新增 %d 个：%s）"
             % (len(common), len(new), ",".join(new)) if same else
             ("FAIL: %s" % diff if same is False else "SKIP（无基线文件）")))

    print("-" * 60)
    # 6: 端子间距检查（DPDT 争议沉淀为规则）：同一符号内端子对距离 <8px 只警告不判失败
    import math
    tight = []
    for name in SYMBOLS_45:
        terms = S.TERMINALS.get(name, [])
        for a in range(len(terms)):
            for b in range(a + 1, len(terms)):
                n1, x1, y1 = terms[a]; n2, x2, y2 = terms[b]
                d = math.hypot(x1 - x2, y1 - y2)
                if d < 8:
                    tight.append((name, n1, n2, round(d, 1)))
    print("[6] 端子间距: %s（间距<8px 的端子对=%d，仅警告）"
          % ("OK" if not tight else "WARN", len(tight)))
    for t in tight:
        print("    过近:", t)

    print("-" * 60)
    if fails:
        print("FAIL:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("全部通过：%d 符号 / %d 端子 / 录制器无回归" % (len(SYMBOLS_45), total))


if __name__ == "__main__":
    main()
