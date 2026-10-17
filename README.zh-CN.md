# ⚡ text-to-schematic-muse

[English](README.md) | [中文](README.zh-CN.md)

**一句话画电气图纸。**

用自然语言描述电路，拿回一张真正的原理图：IEC 符号的元件清单加上接线拓扑，
在 draw.io 里原生绘制。目标很简单——"画一个直接启动电路"→一张验证过的图，
不用手排。

这是 [song-squared](https://github.com/song-squared) 的第四个开源项目，
前三个是
[scientific-illustrator-muse](https://github.com/song-squared/scientific-illustrator-muse)、
[blender-for-muse](https://github.com/song-squared/blender-for-muse)、
[text-to-cad-muse](https://github.com/song-squared/text-to-cad-muse)。

## 📍 当前状态：v0.1

- **48 个 IEC 符号 / 119 个端子**——每个符号都带机器可读的端子声明
  （`iec_symbols.py` 中的 `TERMINALS`），经交叉审查，6 项自动检查全过
  （`verify_terminals.py`）。
- **实例化**——符号变成真实器件：设备位号（`-KM1`）+ 型号，一个物理器件
  一个实例（`circuit.py`）。
- **线即连接**——线不再是线段，而是"端子到端子"的连接
  `（器件，端子）→（器件，端子）`，画图前先做合法性验证。
- **首张端到端验证图**——直接启动电路（9 个实例、22 根接线），由接线表
  直接生成，电气正确性已验证：

![直接启动电路 v1](docs/direct-start-v1.png)

> **状态说明**：v0.1 为教学预览版——端子数据经交叉审查，电气正确性已验证；
> 不宣称严格 IEC/GB 合规，不可直接用于真实安装接线。

## 🚀 快速上手

```bash
git clone https://github.com/song-squared/text-to-schematic-muse
cd text-to-schematic-muse

python3 verify_terminals.py   # 48 符号 / 119 端子，6 项检查
python3 direct_start.py        # 由接线表生成 direct_start_v1.drawio

./setup.sh check              # 缺 draw.io 就装上（可反复跑，VM 重置后用它恢复）
xvfb-run -a /opt/drawio/drawio --no-sandbox --export \
  --format png --output direct_start_v1.png direct_start_v1.drawio
```

核心脚本只依赖 Python 标准库；draw.io 只在导出 PNG 时需要，
`setup.sh check` 可在 VM 重置后一键恢复。

## 🗺️ 路线图：五步走向智能图纸

| 步骤 | 内容 | 状态 |
|---|---|---|
| 1 | 每个符号声明端子 | ✅ 已完成 |
| 2 | 实例化：符号 + 设备位号 + 型号 | ✅ 已完成 |
| 3 | 线改"连接"：端子到端子的逻辑连接 | ✅ 已完成 |
| 4 | 报表：BOM、线号表、端子表（由模型查表生成） | ⬜ 下一步 |
| 5 | 发射器：`.dxf`（ezdxf）进 AutoCAD、`.qet` 借 QElectroTech 报表 | ⬜ 计划中 |

## 🧭 技术路线

- **地基自有**——结构化模型（Python 符号函数 + 端子声明 + 实例/接线拓扑）
  是咱们自己的地基，不建在 QElectroTech 上面（GPL 传染、无 headless 自检、
  受制于人）。
- **draw.io 是主场**——画图、改图、截图自检都在这儿。
- **`.dxf` / `.qet` 是发射器，不是地基**——同一套模型往外发射：给 AutoCAD
  的是纯几何（跟当年手画 CAD 一个路数：线条图块，不需要"智能符号"），
  报表借 QElectroTech 的力。借船出海，不搬家。

## 📄 开源协议

MIT — 见 [LICENSE](LICENSE)。
