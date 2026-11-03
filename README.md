# MathAgent

低资源 **AI-for-Math** 栈：从竞赛工具环（ToRA / MathChat）做到研究型 **MathLattice**，再到逼近「概念思维」的 **Think 三柱**（可执行库 · 假说竞技场 · 跨项目证据）。

> **诚实边界：** 不声称用一次 API 证明 Fields 级结果。本仓库最大化 *可认证的进展*，并把开放缺口写成显式 `Gap` / `HUMAN_REVIEW`。

仓库：https://github.com/hongwei-2026/mathagent

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [docs/README.md](docs/README.md) | 文档总览与阅读顺序 |
| [docs/LOW_COST_PATH.md](docs/LOW_COST_PATH.md) | 低成本证明路径（econ / 选择性 CoT） |
| [docs/LATTICE_ARCHITECTURE.md](docs/LATTICE_ARCHITECTURE.md) | MathLattice：图记忆 · A→E · MDL / 库学习 sleep |
| [docs/THINK_ARCHITECTURE.md](docs/THINK_ARCHITECTURE.md) | Think 三柱：可执行库 · 竞技场 · 证据账本 |
| [docs/TRY_LOCAL_AND_MATHLIB.md](docs/TRY_LOCAL_AND_MATHLIB.md) | Lean / mathlib / 本地 7B prover |

---

## 四层能力（由浅入深）

![MathAgent four-layer stack](docs/assets/stack-overview.svg)

| 层 | CLI | 何时用 |
|----|-----|--------|
| ① | `mathagent solve` / `eval` / UI | 标准题、工具自洽 |
| ② | `mathagent formal` / `econ` / `lean-check` | 要证书（SymPy/Lean），预算紧 |
| ③ | `mathagent lattice` / `lattice-gate` | 开放题、理论草图、诚实 gaps |
| ④ | `mathagent lattice --think` | 概念竞争、库算子、跨项目证据 |

---

## ① Tool Agent（ToRA / MathChat）

| 灵感 | 复用什么 |
|------|----------|
| [ToRA](https://github.com/microsoft/ToRA) | 交织推理 + 工具；MATH 式判分 |
| [MathChat](https://arxiv.org/abs/2306.01337) | 多轮 agent ↔ 工具反馈 |
| Neuro-Symbolic Math Solver | SymPy 作确定性执行器 |
| GSM8K / MATH | HuggingFace 评测 |

```text
问题 → LLM 规划/工具调用 → sandbox (run_python / sympy_*) → 自纠 ≤N → FINAL_ANSWER → grader
```

**相对朴素基线的优化：** 多厂商 OpenAI 兼容 API；纯算术快路径；AST 沙箱；工具错误回灌；离线 samples + HF；CLI + Streamlit。

```bash
mathagent solve "Solve 2x+5=17"
mathagent eval --dataset samples --limit 5
streamlit run src/mathagent/ui_app.py
```

---

## ② Formal / Econ（低成本证明）

OpenAI 级 IMO 烧 RL + 海量 test-time；开源更可走的轴是：**便宜模型先试 → Lean 轻量修复 → 分解 → 失败才升 reasoner**。

```bash
mathagent econ "theorem add_comm (a b : Nat) : a + b = b + a := by" --out outputs/econ.json
mathagent formal "Prove AM-GM: (x+y)/2 >= sqrt(xy) for x,y>0" --out outputs/amgm.json
```

细节：[docs/LOW_COST_PATH.md](docs/LOW_COST_PATH.md)

### Lean 4（本机 D:，非必须上云）

| 路径 | 用途 |
|------|------|
| `D:\lean\elan` | `ELAN_HOME` + toolchains |
| `D:\mathagent\lean_workspace` | lake 草图 |
| `D:\mathagent\lean_mathlib` | mathlib 试验（见 TRY_LOCAL 文档） |

```powershell
$env:ELAN_HOME='D:\lean\elan'
$env:Path = "D:\lean\elan\bin;$env:Path"
mathagent lean-check --code "theorem t : True := trivial"
```

本地 7B：`mathagent econ --local ...`（Ollama + GGUF，见 TRY_LOCAL 文档）。

---

## ③ MathLattice（研究级图记忆）

竞赛 prover ≠ 研究数学。Lattice 吸收 Ansatz 图记忆、DreamProver wake/sleep、猜想优先形式化等，在笔记本预算上跑：

![MathLattice wake/sleep loop](docs/assets/lattice-loop.svg)

### Concept-value（A→E）

| 步 | 模块 | 作用 |
|----|------|------|
| A Abduction | `lattice/abduction.py` | 用新语言解释 gaps |
| B Concept slots | `graph.admit_concept` | 类型化概念 + 分数 |
| C Analogy | `lattice/analogy.py` | 结构映射廉价见证 |
| D Curator | `lattice/curator.py` | 按概念价值排序 / spawn 叶 |
| E Human gate | `mathagent lattice-gate` | 共谋 accept/reject |

另有 **MDL 压缩分**（`mdl.py`）、**库学习 sleep**（gated `library_ops`）、**因果 surprise**（leaf 认证率更新信念）。

```bash
# 经典 Lattice
mathagent lattice "Twin primes: map certifiable lemmas and mark the open gap" --out outputs/lattice.json

# 概念价值环
mathagent lattice "..." --concept-value --out outputs/cv.json

# 人工门
mathagent lattice-gate <project_id> <cpt_id> accept --note "keep hard core"
```

设计：[docs/LATTICE_ARCHITECTURE.md](docs/LATTICE_ARCHITECTURE.md)

---

## ④ Think 三柱（逼近「概念思维」）

**问题：** 只有纪律外壳时，Concept 仍是叙事 JSON——不能调用、不能淘汰、不能跨次复利。

![Think three pillars](docs/assets/think-pillars.svg)

| 柱 | 前沿锚点 | 代码 | 硬约束 |
|----|----------|------|--------|
| **1 可执行库** | DreamCoder：wake 必须 *call* 原语 | `lattice/think/executable.py` | `from_concept` 叶优先 `call_op`；空 hint 不能 manual-proved |
| **2 假说竞技场** | Robot Scientist / Lakatos | `cheap_tests.py` + `arena.py` | 同 gap 多 Concept → 廉价否证 → 败者 `REJECTED` |
| **3 证据账本** | CoEvo / LeanAgent lifelong | `think/evidence.py` | `data/lattice/evidence.jsonl`；Δ`graph_dl`；历史负 MDL 降权 |

```bash
mathagent lattice "Compress (a+b)^2 via a reusable macro, not term-churn" \
  --think --auto-accept --wake-rounds 1 --max-wake 3 --out outputs/think.json
```

> `--auto-accept` 仅用于烟测；正经研究请走 `lattice-gate`。

设计：[docs/THINK_ARCHITECTURE.md](docs/THINK_ARCHITECTURE.md)

---

## 快速开始

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"

copy .env.example .env   # 填 MATHAGENT_API_KEY / MODEL / BASE_URL

mathagent solve "Solve 2x+5=17"
mathagent formal "Prove that there are infinitely many primes."
mathagent lattice "..." --think --auto-accept
python scripts/smoke_tools.py
pytest -q
```

### 环境变量示例

```env
# DeepSeek（推荐）
MATHAGENT_API_KEY=sk-...
MATHAGENT_BASE_URL=https://api.deepseek.com
MATHAGENT_MODEL=deepseek-chat
MATHAGENT_FORMAL_MODEL=deepseek-reasoner

# Ollama
MATHAGENT_API_KEY=ollama
MATHAGENT_BASE_URL=http://127.0.0.1:11434/v1
MATHAGENT_MODEL=qwen2.5:14b
```

---

## 数据与持久化

| 路径 | 说明 |
|------|------|
| `data/samples/problems.jsonl` | 离线样例题 |
| `data/lattice/<project>.json` | 研究图（gitignored 工作态） |
| `data/lattice/evidence.jsonl` | Think 跨项目证据账本 |
| `scripts/download_data.py` | 拉 GSM8K / MATH |

```bash
mathagent eval --dataset gsm8k --limit 20 --out outputs/gsm8k_pred.jsonl
```

---

## 代码布局

```text
src/mathagent/
  agent.py, prompts.py, tools/, eval/     # ① 工具 agent
  formal/                                 # ② certify / econ / Lean / budget
  lattice/
    graph.py  conjecture.py  wake.py  sleep.py
    abduction.py  analogy.py  value.py  mdl.py  causal.py  curator.py
    pipeline.py
    think/                                # ④ 三柱
      executable.py  cheap_tests.py  arena.py  evidence.py  loop.py
  cli.py  ui_app.py  config.py

docs/           架构与低成本路径
tests/          pytest（含 concept-value / think pillars）
lean_workspace/ lean_mathlib/   本地 Lean
```

### 主要 CLI

| 命令 | 作用 |
|------|------|
| `solve` / `eval` | 工具解题与评测 |
| `formal` / `econ` / `lean-check` | 形式化分解与廉价证明 |
| `lattice` | 研究图；`--concept-value` / `--think` / `--auto-accept` |
| `lattice-gate` | 人工 accept/reject Concept，accept 后 spawn 叶 |

---

## 测试

```bash
pytest -q
# 重点：tests/test_concept_value.py  tests/test_think_pillars.py
```

---

## 设计立场（短）

1. **证书诚实：** 无硬见证（SymPy/Lean/finite）不成 `Lemma`；sleep 抽象不得伪装成已证。  
2. **概念有代价：** MDL / 公理询问 / 新开 gap；高 V 默认 `HUMAN_REVIEW`。  
3. **思考三约束：** 可调用 × 可淘汰 × 可跨次记账——缺一则仍是概率搜索包装。  
4. **架构 > 蛮力：** 优先分解与选择性升级，而非 Pass@k 堆采样。

---

## Citation

若用于研究，请同时引用上游（节选）：

```bibtex
@inproceedings{gou2024tora,
  title={ToRA: A Tool-Integrated Reasoning Agent for Mathematical Problem Solving},
  author={Gou, Zhibin and Shao, Zhihong and Gong, Yeyun and Shen, Yelong and Yang, Yujiu and Huang, Minlie and Duan, Nan and Chen, Weizhu},
  booktitle={ICLR},
  year={2024}
}
```

DreamCoder / EconProver / 相关形式化工作见各文档内链接。

## License

MIT — 见 [LICENSE](LICENSE)。判分逻辑改编自 ToRA / Hendrycks MATH（MIT）。
