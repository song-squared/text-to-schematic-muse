# ⚡ text-to-schematic-muse

[English](README.md) | [中文](README.zh-CN.md)

**One-sentence electrical schematic generation.**

Describe a circuit in plain language — get back a real schematic: an IEC
symbol bill of materials plus wiring topology, drawn natively in draw.io.
The goal is simple: *"draw me a direct-on-line motor starter"* → one
verified diagram, no drafting.

This is the fourth open project from
[song-squared](https://github.com/song-squared), after
[scientific-illustrator-muse](https://github.com/song-squared/scientific-illustrator-muse),
[blender-for-muse](https://github.com/song-squared/blender-for-muse), and
[text-to-cad-muse](https://github.com/song-squared/text-to-cad-muse).

## 📍 Status: v0.1

- **48 IEC symbols / 119 terminals** — every symbol carries machine-readable
  terminal declarations (`TERMINALS` in `iec_symbols.py`), cross-reviewed
  and verified by 6 automated checks (`verify_terminals.py`).
- **Instantiation** — a symbol becomes a real device: device tag (`-KM1`)
  + part number, one instance per physical device (`circuit.py`).
- **Wires are connections** — a wire is no longer a line segment; it is a
  terminal-to-terminal connection `(device, terminal) → (device, terminal)`,
  validated before anything is drawn.
- **First end-to-end proof** — a direct-on-line motor starter (9 instances,
  22 connections), drawn from the connection list, electrically verified:

![direct-on-line starter, v1](docs/direct-start-v1.png)

> **Status note**: v0.1 is a teaching preview — terminal data is cross-reviewed
> and electrical correctness verified. It does not claim strict IEC/GB
> compliance and is not for real installation wiring.

## 🚀 Quickstart

```bash
git clone https://github.com/song-squared/text-to-schematic-muse
cd text-to-schematic-muse

python3 verify_terminals.py   # 6 checks over 48 symbols / 119 terminals
python3 direct_start.py        # writes direct_start_v1.drawio from the wire list

./setup.sh check              # install draw.io if missing (safe to re-run)
xvfb-run -a /opt/drawio/drawio --no-sandbox --export \
  --format png --output direct_start_v1.png direct_start_v1.drawio
```

Core scripts need only the Python standard library. draw.io is only needed
for PNG export (and `setup.sh check` restores it after a VM reset).

## 🗺️ Roadmap: 5 steps to smart schematics

| Step | What | Status |
|---|---|---|
| 1 | Terminal declarations on every symbol | ✅ done |
| 2 | Instantiation: symbol + device tag + part number | ✅ done |
| 3 | Wires as terminal-to-terminal connections | ✅ done |
| 4 | Reports: BOM, wire list, terminal list (from the model) | ⬜ next |
| 5 | Emitters: `.dxf` (via ezdxf) for AutoCAD, `.qet` for QElectroTech reports | ⬜ planned |

## 🧭 Architecture

- **Our own structured model is the foundation** — Python symbol functions +
  terminal declarations + instance/wire topology. It is not built on top of
  QElectroTech (GPL copyleft, no headless self-check loop, vendor lock-in).
- **draw.io is home base** — drawing, editing, and screenshot self-review
  all happen here.
- **`.dxf` / `.qet` are emitters, not the foundation** — the same model
  emits plain geometry for AutoCAD (the way hand-drafted CAD always worked:
  lines and blocks, no "smart symbols" required) and borrows QElectroTech
  for reports. Ride the boat, don't move house.

## 📄 License

MIT — see [LICENSE](LICENSE).
