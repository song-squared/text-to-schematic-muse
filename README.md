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
- **Second proof: forward/reverse motor control** — 15 instances, 42 wires,
  with self-locking, electrical + mechanical interlocking, and automatic
  cross-over arcs (`forward_reverse.py`, `verify_forward_reverse.py`):
- **Reports** — BOM, wire list, and terminal list generated from the model
  by deterministic lookup (`reports.py`).
- **Emitters** — the same model emits `.dxf` (ezdxf, for AutoCAD) and `.qet`
  (for QElectroTech reports).

![direct-on-line starter, v8](docs/direct-start-v8.png)

![forward/reverse starter](docs/forward-reverse.png)

> **About the PNG previews**: this repo intentionally does not carry PNG
> binaries — automated pushes can't upload them (a GitHub connector
> limitation), and manually uploading after every update wastes everyone's
> time. The previews are generated locally with draw.io any time you need
> them; the export command is in Quickstart above. If an image shows as
> broken here, that's why — run the export and you'll have the identical file.

> **Status**: v0.1 is a teaching preview — terminal data is cross-reviewed and
> electrical correctness verified. It does not claim strict IEC/GB compliance
> and is not intended for real installation wiring.

## 🚀 Quickstart

```bash
git clone https://github.com/song-squared/text-to-schematic-muse
cd text-to-schematic-muse

python3 verify_terminals.py   # 48 symbols / 119 terminals, all checks
python3 direct_start.py v8     # generates direct_start_v8.drawio from the connection list
python3 forward_reverse.py       # generates forward_reverse.drawio (forward/reverse control)
python3 verify_forward_reverse.py  # topology-based verification, all checks

./setup.sh check              # installs draw.io if missing (re-run after a VM reset)
xvfb-run -a /opt/drawio/drawio --no-sandbox --export \
  --format png --output 直接启动电路-v8.png direct_start_v8.drawio
```

Core scripts depend only on the Python standard library; draw.io is needed
only for PNG export.

## 👶 For beginners: use it without touching the command line

You don't need to clone anything yourself. If you use
[Muse](https://muse.ai) (this project's authoring agent), the whole flow is
conversational:

1. **"Take a look at the text-to-schematic-muse open-source project."**
   Muse reads the repo — symbols, wiring model, examples, reports.
2. **"Install it on the remote computer."**
   Muse runs `./setup.sh check` on its own machine and verifies draw.io
   export works.
3. **"Draw me a motor forward/reverse starter circuit."**
   Muse builds the connection list, validates every wire, and generates the
   `.drawio` schematic plus the verification report.
4. **Collect the result.** You get back:
   - a PNG preview (check it on your phone),
   - the editable `.drawio` file (open in draw.io, tweak anything),
   - the BOM / wire list / terminal list,
   - `.dxf` for AutoCAD and `.qet` for QElectroTech, if you need them
     (`python3 dxf_emit.py forward_reverse`,
     `python3 qet_emit.py forward_reverse` — pass any circuit module name,
     no code changes needed).

That's it — describe the circuit in one sentence, receive a verified diagram.

## 🗺️ Roadmap

| Step | | Status |
|---|---|---|
| 1 | Terminal declarations for every symbol | ✅ Done |
| 2 | Instantiation: symbol + device tag + part number | ✅ Done |
| 3 | Wires as connections: terminal-to-terminal logic | ✅ Done |
| 4 | Reports: BOM, wire list, terminal list, generated from the model | ✅ Done |
| 5 | Emitters: `.dxf` (ezdxf) for AutoCAD, `.qet` for QElectroTech reports | ✅ Done |

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
