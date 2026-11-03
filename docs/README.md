# MathAgent 文档

按「你要解决什么」读：

| 顺序 | 文档 | 你想弄清… |
|------|------|-----------|
| 1 | [LOW_COST_PATH.md](LOW_COST_PATH.md) | 为什么不堆 Pass@k；`econ` / formal 怎么省 token |
| 2 | [LATTICE_ARCHITECTURE.md](LATTICE_ARCHITECTURE.md) | 研究图、A→E、MDL、库学习 sleep、因果 surprise |
| 3 | [THINK_ARCHITECTURE.md](THINK_ARCHITECTURE.md) | 三柱如何逼近概念思维；验收标准与前沿锚点 |
| 4 | [TRY_LOCAL_AND_MATHLIB.md](TRY_LOCAL_AND_MATHLIB.md) | Lean / mathlib / Ollama 本地 prover |

仓库总览与 CLI 速查：根目录 [README.md](../README.md)。

### 架构图（README 插图）

| 图 | 文件 |
|----|------|
| 品牌横幅 | [assets/mathagent-banner.png](assets/mathagent-banner.png) |
| 四层总览 | [assets/stack-overview.png](assets/stack-overview.png) |
| Lattice wake/sleep | [assets/lattice-loop.png](assets/lattice-loop.png) |
| Think 三柱 | [assets/think-pillars.png](assets/think-pillars.png) |

重新生成架构 PNG：`python scripts/render_readme_assets.py`

## 模块 ↔ 文档速查

| 代码 | 文档段落 |
|------|----------|
| `formal/econ.py`, `formal/certify.py` | LOW_COST_PATH |
| `lattice/pipeline.py`, `abduction.py`, `value.py`, `mdl.py` | LATTICE_ARCHITECTURE |
| `lattice/think/*` | THINK_ARCHITECTURE |
| `lean_workspace/`, `lean_mathlib/` | TRY_LOCAL_AND_MATHLIB |

## 推荐实验路径

1. `mathagent solve` — 确认 API / 工具环  
2. `mathagent formal` / `econ` — 确认证书路径  
3. `mathagent lattice "..."` — 经典研究图  
4. `mathagent lattice "..." --concept-value` — 概念槽 + 人工门  
5. `mathagent lattice "..." --think --auto-accept` — 三柱烟测（再改用 `lattice-gate`）  
6. 查看 `data/lattice/*.json` 与 `data/lattice/evidence.jsonl`
