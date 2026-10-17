#!/usr/bin/env python3
"""verify_rotation.py - 旋转回归测试：48 符号 × 4 角度渲染全过。

v5 增量审查发现 RotCtx.dot 接口与 Ctx.dot 不兼容（位置传 color 报 TypeError），
6 个符号在任意 rotation（含 0°）下渲染失败。本测试防止回归。
用法：python3 verify_rotation.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from circuit import Circuit, Instance
from iec_symbols import TERMINALS


def main():
    failures = []
    total = 0
    for symbol in TERMINALS:
        for angle in (0, 90, 180, 270):
            total += 1
            c = Circuit()
            c.add_instance(Instance("test", symbol, "TEST", "demo",
                                    150, 150, rotation=angle))
            try:
                errs = c.validate()
                assert not errs, errs
                for num, _, _ in TERMINALS[symbol]:
                    c.terminal_pos("test", num)
                c.render(W=400, H=400)
            except Exception as exc:  # noqa: BLE001
                failures.append((symbol, angle, repr(exc)))
    ok = total - len(failures)
    print(f"旋转渲染测试: {ok}/{total} 通过")
    for sym, ang, err in failures:
        print(f"  FAIL {sym} @ {ang}°: {err}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
