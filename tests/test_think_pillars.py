from pathlib import Path

from mathagent.lattice.graph import Node, NodeKind, NodeStatus, ResearchGraph
from mathagent.lattice.think.arena import eliminate_losers
from mathagent.lattice.think.evidence import EvidenceLedger, apply_evidence_priors
from mathagent.lattice.think.executable import call_op, render_template, wake_via_library


def test_render_and_call_op_binomial():
    g = ResearchGraph(project_id="t1")
    c = g.admit_concept(
        "binomial square macro",
        name="binomial_square",
        scores={"conceptual_value": 0.6, "mdl_gain": 10, "compression": 0.7, "minimality": 0.8, "systematicity": 0.5, "surprise": 0.3},
        human_gate=False,
    )
    c.meta["artifact"] = {
        "kind": "sympy_template",
        "sympy_template": "({{a}}+{{b}})**2",
        "sympy_expand": "{{a}}**2 + 2*{{a}}*{{b}} + {{b}}**2",
    }
    assert render_template("({{a}}+{{b}})**2", {"a": "x", "b": "y"}) == "(x+y)**2"
    res = call_op(c, binding={"a": "x", "b": "y"})
    assert res.ok, res.detail


def test_wake_via_library_certifies_leaf():
    g = ResearchGraph(project_id="t2")
    c = g.admit_concept("op", name="sq", human_gate=False)
    c.meta["artifact"] = {
        "sympy_template": "({{a}}-{{b}})**2",
        "sympy_expand": "{{a}}**2 - 2*{{a}}*{{b}} + {{b}}**2",
    }
    leaf = Node.new(
        NodeKind.CONJECTURE,
        "(x-y)**2 identity",
        from_concept=c.id,
        binding={"a": "x", "b": "y"},
        sympy_hint="(x-y)**2 = x**2 - 2*x*y + y**2",
    )
    g.add(leaf)
    result = wake_via_library(g, leaf)
    assert result is not None and result.ok
    assert leaf.status == NodeStatus.CERTIFIED


def test_arena_eliminates_loser(tmp_path):
    g = ResearchGraph(project_id="arena")
    gap = g.add_gap("shared gap G")
    strong = g.admit_concept(
        "good",
        name="good",
        closes_gap_ids=[gap.id],
        scores={"conceptual_value": 0.8, "mdl_gain": 30, "compression": 0.8, "minimality": 0.8, "systematicity": 0.8, "surprise": 0.4},
        human_gate=False,
    )
    weak = g.admit_concept(
        "bad",
        name="bad",
        closes_gap_ids=[gap.id],
        scores={"conceptual_value": 0.2, "mdl_gain": -20, "compression": 0.2, "minimality": 0.5, "systematicity": 0.2, "surprise": 0.1},
        human_gate=False,
    )
    for parent, ok in ((strong, True), (weak, False)):
        leaf = Node.new(NodeKind.CONJECTURE, f"leaf-{parent.id}", from_concept=parent.id)
        leaf.status = NodeStatus.CERTIFIED if ok else NodeStatus.BLOCKED
        g.add(leaf)
    reports = eliminate_losers(g)
    assert reports
    assert weak.status == NodeStatus.REJECTED
    assert strong.status in {NodeStatus.ACCEPTED, NodeStatus.OPEN}


def test_evidence_ledger_roundtrip(tmp_path):
    path = Path(tmp_path) / "evidence.jsonl"
    ledger = EvidenceLedger(path=path)
    g = ResearchGraph(project_id="ev")
    g.meta["graph_dl_start"] = 100.0
    c = g.admit_concept(
        "hist",
        name="binomial_square",
        scores={"conceptual_value": 0.7, "mdl_gain": 12},
        human_gate=False,
    )
    c.status = NodeStatus.ACCEPTED
    c.meta["arena_win"] = {"arena": "x"}
    recs = ledger.commit_graph(g, graph_dl_before=100.0)
    assert len(recs) == 1
    assert recs[0].delta_graph_dl != 0 or recs[0].graph_dl_before == 100.0
    assert path.exists()
    assert ledger.prior_boost("binomial_square") > 0
    g2 = ResearchGraph(project_id="ev2")
    c2 = g2.admit_concept("hist2", name="binomial_square", scores={"conceptual_value": 0.5}, human_gate=False)
    n = apply_evidence_priors(g2, ledger)
    assert n == 1
    assert c2.meta["scores"]["conceptual_value"] > 0.5


def test_cheap_tests_kill_all_fail_hypothesis():
    from mathagent.lattice.think.cheap_tests import run_cheap_discriminators

    g = ResearchGraph(project_id="ct")
    gap = g.add_gap("shared")
    good = g.admit_concept(
        "good",
        name="good",
        closes_gap_ids=[gap.id],
        human_gate=False,
    )
    good.meta["predicted_leaf_checks"] = [
        {"statement": "sq", "sympy_hint": "(a-b)**2"}
    ]
    bad = g.admit_concept(
        "bad",
        name="bad",
        closes_gap_ids=[gap.id],
        human_gate=False,
    )
    bad.meta["predicted_leaf_checks"] = [
        {"statement": "bogus", "sympy_hint": "this_is_not_valid_sympy@@@"}
    ]
    reps = run_cheap_discriminators(g)
    assert reps
    assert bad.status == NodeStatus.REJECTED
    assert good.status in {NodeStatus.ACCEPTED, NodeStatus.OPEN}
