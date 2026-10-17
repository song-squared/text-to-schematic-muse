# ⚡ text-to-schematic-muse

[English](README.md) | [中文](README.zh-CN.md)

**Describe a circuit in plain language — get back a real schematic.**

text-to-schematic-muse turns natural language into verified electrical schematics.
It builds an IEC symbol bill of materials plus wiring topology from your
description, validates every connection, and draws the diagram natively in
draw.io.

*"Draw me a direct-on-line motor starter"* → one verified diagram. No drafting.

This is the fourth open-source project from
[song-squared](https://github.com/song-squared), after
[scientific-illustrator-muse](https://github.com/song-squared/scientific-illustrator-muse),
[blender-for-muse](https://github.com/song-squared/blender-for-muse), and
[text-to-cad-muse](https://github.com/song-squared/text-to-cad-muse).

## ✨ What it does today (v0.1)

- **48 IEC symbols, 119 terminals** — every symbol carries machine-readable
  terminal declarations, cross-reviewed and covered by automated checks.
- **Instantiation** — symbols become real devices: device tags (`-KM1`) plus
  part numbers, one instance per physical device.
- **Wires as connections** — a wire is no longer a line segment but a logical
  connection `(device, terminal) → (device, terminal)`, validated before
  anything is drawn.
- **First end-to-end proof** — a direct-on-line motor starter (9 instances,
  22 connections), generated from its connection list and electrically
  verified:

![direct-on-line starter, v1](docs/direct-start-v1.png)

> **Status**: v0.1 is a teaching preview — terminal data is cross-reviewed and
> electrical correctness verified. It does not claim strict IEC/GB compliance
> and is not intended for real installation wiring.

## 🚀 Quickstart

```bash
git clone https://github.com/song-squared/text-to-schematic-muse
cd text-to-schematic-muse

python3 verify_terminals.py   # 48 symbols / 119 terminals, all checks
python3 direct_start.py        # generates direct_start_v1.drawio from the connection list

./setup.sh check              # installs draw.io if missing (re-run after a VM reset)
xvfb-run -a /opt/drawio/drawio --no-sandbox --export \
  --format png --output direct_start_v1.png direct_start_v1.drawio
```

Core scripts depend only on the Python standard library; draw.io is needed
only for PNG export.

## 🗺️ Roadmap

| Step | | Status |
|---|---|---|
| 1 | Terminal declarations for every symbol | ✅ Done |
| 2 | Instantiation: symbol + device tag + part number | ✅ Done |
| 3 | Wires as connections: terminal-to-terminal logic | ✅ Done |
| 4 | Reports: BOM, wire list, terminal list, generated from the model | ⬜ Next |
| 5 | Emitters: `.dxf` (ezdxf) for AutoCAD, `.qet` for QElectroTech reports | ⬜ Planned |

## 🧭 Architecture

- **Own the foundation** — the structured model (Python symbol functions,
  terminal declarations, instance/wiring topology) is ours. It is not built
  on QElectroTech (GPL constraints, no headless self-check, external
  dependency).
- **draw.io is home** — drawing, editing, and screenshot self-review all
  happen here.
- **Emitters, not foundations** — `.dxf` and `.qet` are outputs of the same
  model: pure geometry for AutoCAD (the way schematics have always been
  drafted — lines and blocks, no "smart symbols" required), and QElectroTech
  for its reporting strength.

## 📄 License

MIT — see [LICENSE](LICENSE).
