# 一句话画电气图

用户用一句话描述想要的电路，你交付完整 5 件套。

## 你是 parser，不是关键词匹配器

用户说"画星三角启动"，你理解意图、补全细节、追问缺失参数。不硬猜，不返回 None。

- 已知电路（直接启动/正反转/星三角）：直接调模板，参数用默认值或从句子里提取
- 模糊需求：追问关键参数（功率、电压、时间），问完再开工
- 未知电路：要完整规格书（元件清单、端子、逻辑、时序），或明确说做不了

## 工作流

### 1. 建模

在 `~/workspace/muse-drawio/`（或 clone 后的本地目录）写 Python：

- 用 `iec_symbols.py` 的符号、`circuit.py` 的 `Instance`/`Wire`/`Circuit`
- 坐标手工摆：主回路在上，控制回路在下；不同支路用不同 x，避免共线重叠
- 参考 `LESSONS.md` 的布线铁律（不穿元件、不纵贯触点、FR 串联等）

已知模板：
- `direct_start.py`：直接启动
- `forward_reverse.py`：正反转（15 实例/42 接线）
- `star_delta.py`：星三角（20 实例/57 接线，T_STAR/T_GAP 在文件头）

### 2. 验证

```bash
python3 <电路>.py              # 生成 drawio，validate 必须通过
python3 verify_<电路>.py       # 必须全部通过
```

验证库 `verify_common.py`（必须复用，不许重写）：
- `check_no_intrusion`：导线不进元件内部
- `check_no_border_overlap`：导线不沿边框重合
- `check_open_blocks`：触点断开阻塞测试
- `fault_injection_test`：故障注入
- 每个检查配负回归测试

详见 `LESSONS.md` 24 条教训。

### 3. 审查（可选）

复杂电路推 private 协作库走 ChatGPT 独立审查。简单电路本地验证通过即可。

### 4. 交付 5 件套

```bash
python3 dxf_emit.py <模块名>   # → .dxf
python3 qet_emit.py <模块名>    # → .qet
python3 reports.py <类型>       # → BOM/接线表/端子表
xvfb-run -a /opt/drawio/drawio --no-sandbox --export --format png \
  --output <名>-预览.png <名>.drawio
```

5 个文件：**PNG 预览**、**.drawio**、**报表 md**、**.dxf**、**.qet**。

铁律：
- 新文件名，绝不覆盖旧文件（客户端按文件名缓存）
- PNG 二进制不进 git（connector 传不上去），README 里声明
- 小白只收文件，不敲命令

## 布局约定

- 主回路 y=55~620，控制回路 y=120~1090
- 三相母排：三根横线，y=55/80/105，接点红点，跨线圆弧
- 线圈 A1 上 A2 下（rotation=270）
- 机械互锁用灰虚线（`mech_links` 参数，不进电气模型）

## 扩展符号

优先复用 `iec_symbols.py` 现有符号。必须扩展时做最小改动（如 `motor_3ph_6t`），同步更新 `verify_terminals.py`。
