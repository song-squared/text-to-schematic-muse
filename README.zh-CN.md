# ⚡ text-to-schematic-muse

[English](README.md) | [中文](README.zh-CN.md)

**一句话，画出电气图纸。**

text-to-schematic-muse 把自然语言变成经过验证的电气原理图：从你的描述生成
IEC 符号的元件清单与接线拓扑，逐条验证每个连接，再在 draw.io 里原生绘制。

"画一个直接启动电路" → 一张验证过的图。不用手排。

这是 [song-squared](https://github.com/song-squared) 的第四个开源项目，
前三个是
[scientific-illustrator-muse](https://github.com/song-squared/scientific-illustrator-muse)、
[blender-for-muse](https://github.com/song-squared/blender-for-muse)、
[text-to-cad-muse](https://github.com/song-squared/text-to-cad-muse)。

## ✨ v0.1 已实现

- **48 个 IEC 符号 / 119 个端子**——每个符号都带机器可读的端子声明，
  经交叉审查与自动化检查全覆盖。
- **实例化**——符号变成真实器件：设备位号（`-KM1`）+ 型号，
  一个物理器件一个实例。
- **线即连接**——线不再是线段，而是"端子到端子"的逻辑连接
  `（器件，端子）→（器件，端子）`，绘制前先做合法性验证。
- **首张端到端验证图**——直接启动电路（9 个实例、22 根接线），
  由接线表直接生成，电气正确性已验证：
- **报表**——BOM、接线表、端子表由模型查表生成（`reports.py`）。
- **发射器**——同一模型发射 `.dxf`（ezdxf，进 AutoCAD）与 `.qet`
 （QElectroTech 报表）。

![直接启动电路 v6](docs/direct-start-v6.png)

> **状态说明**：v0.1 为教学预览版——端子数据经交叉审查，电气正确性已验证；
> 不宣称严格 IEC/GB 合规，不可直接用于真实安装接线。

## 🚀 快速上手

```bash
git clone https://github.com/song-squared/text-to-schematic-muse
cd text-to-schematic-muse

python3 verify_terminals.py   # 48 符号 / 119 端子，全部检查通过
python3 direct_start.py v6     # 由接线表生成 direct_start_v6.drawio

./setup.sh check              # 缺 draw.io 就装上（VM 重置后跑这个恢复）
xvfb-run -a /opt/drawio/drawio --no-sandbox --export \
  --format png --output 直接启动电路-v6.png direct_start_v6.drawio
```

核心脚本只依赖 Python 标准库；draw.io 只在导出 PNG 时需要。

## 🗺️ 路线图

| 步骤 | 内容 | 状态 |
|---|---|---|
| 1 | 每个符号声明端子 | ✅ 已完成 |
| 2 | 实例化：符号 + 设备位号 + 型号 | ✅ 已完成 |
| 3 | 线改"连接"：端子到端子的逻辑连接 | ✅ 已完成 |
| 4 | 报表：BOM、线号表、端子表（由模型查表生成） | ✅ 已完成 |
| 5 | 发射器：`.dxf`（ezdxf）进 AutoCAD、`.qet` 借 QElectroTech 报表 | ✅ 已完成 |

## 🧭 技术路线

- **地基自有**——结构化模型（Python 符号函数 + 端子声明 + 实例/接线拓扑）
  完全自主，不依附于 QElectroTech（GPL 约束、无 headless 自检、受制于人）。
- **draw.io 是主场**——绘制、修改、截图自检都在这里完成。
- **发射器，而非地基**——`.dxf` / `.qet` 是同一模型的不同输出：给 AutoCAD
  的是纯几何（电气图历来如此——线条与图块，不需要"智能符号"），
  报表则借 QElectroTech 之力。

## 📄 开源协议

MIT — 见 [LICENSE](LICENSE)。
