from mathagent.lattice.analogy import verify_analogy_maps
from mathagent.lattice.curator import curator_report, spawn_leaf_conjectures_from_concepts
from mathagent.lattice.graph import NodeKind, NodeStatus, ResearchGraph
from mathagent.lattice.value import (
    conceptual_value,
    needs_human_gate,
    score_proposal,
    surprise_score,
)


def test_score_proposal_and_gate():
    prop = {
        "closes_gap_ids": ["g1", "g2", "g3"],
        "opens_gap_ids": [],
        "axiom_ask": [{"id": "A1"}],
        "baseline_asks": 0,
        "analogies": [{"check_status": "unchecked"}],
        "belief": {"p_before": 0.15, "p_after": 0.7},
    }
    scores = score_proposal(prop)
    assert 0.0 <= scores["conceptual_value"] <= 1.0
    assert scores["compression"] > 0.5
    assert surprise_score(0.15, 0.7) > 0.2
    # low systematicity → human gate
    assert needs_human_gate(scores, axiom_asks=1) is True


def test_admit_concept_human_review():
    g = ResearchGraph(project_id="cv")
    gap = g.add_gap("missing language for X")
    scores = {
        "compression": 0.8,
        "minimality": 0.7,
        "systematicity": 0.2,
        "surprise": 0.5,
    }
    scores["conceptual_value"] = conceptual_value(scores)
    c = g.admit_concept(
        "Introduce functor F that compresses X",
        name="functor-F",
        closes_gap_ids=[gap.id],
        scores=scores,
        human_gate=True,
    )
    assert c.kind == NodeKind.CONCEPT
    assert c.status == NodeStatus.HUMAN_REVIEW
    assert g.conceptual_frontier(1)[0].id == c.id


def test_spawn_leaves_and_curator():
    g = ResearchGraph(project_id="cv2")
    c = g.admit_concept(
        "ring homomorphism view",
        name="ring-hom",
        scores={"conceptual_value": 0.7, "compression": 0.6, "surprise": 0.4},
        human_gate=False,
    )
    assert c.status == NodeStatus.OPEN
    c.meta["predicted_leaf_checks"] = [
        {
            "statement": "(x+y)^2 = x^2 + 2*x*y + y^2",
            "certify_hint": "sympy",
            "sympy_hint": "(x+y)**2 = x**2 + 2*x*y + y**2",
        }
    ]
    spawned = spawn_leaf_conjectures_from_concepts(g)
    assert len(spawned) == 1
    assert spawned[0].meta.get("from_concept") == c.id
    report = curator_report(g)
    assert report["concepts"] == 1


def test_spawn_skips_human_review():
    g = ResearchGraph(project_id="cv3")
    c = g.admit_concept("gated concept", name="gated", human_gate=True)
    c.meta["predicted_leaf_checks"] = [
        {"statement": "leaf should not spawn", "sympy_hint": "(a-b)**2"}
    ]
    assert c.status == NodeStatus.HUMAN_REVIEW
    assert spawn_leaf_conjectures_from_concepts(g) == []
    c.status = NodeStatus.ACCEPTED
    assert len(spawn_leaf_conjectures_from_concepts(g)) == 1


def test_analogy_unchecked_without_hint():
    verified, claimed = verify_analogy_maps(
        [{"domain_a": "groups", "domain_b": "rings", "maps": [{"a": "hom", "b": "hom"}]}]
    )
    assert claimed == 1
    assert verified == 0


def test_empty_hint_does_not_manual_prove():
    from mathagent.formal.certify import certify_subgoal

    res = certify_subgoal(
        {"certify": "sympy", "sympy_hint": "", "statement": "anything"},
        {"status": "proved"},
    )
    assert not res.ok


def test_mdl_gain_positive_when_closing_gaps():
    from mathagent.lattice.mdl import concept_mdl_gain, graph_dl, mdl_compression_score

    gain = concept_mdl_gain(
        gaps_closed=3,
        gaps_opened=0,
        axiom_asks=0,
        concept_statement="short def",
    )
    assert gain > 0
    assert mdl_compression_score(gain) > 0.5
    g = ResearchGraph(project_id="mdl")
    gap = g.add_gap("expensive unexplained gap about X")
    dl0 = graph_dl(g)
    assert dl0 > 0
    # Graph-aware: closing the real active gap credits its obligation
    gain2 = concept_mdl_gain(
        graph=g,
        closes_gap_ids=[gap.id],
        opens_gap_ids=[],
        axiom_ask=[],
        concept_statement="def",
    )
    assert gain2 > 0


def test_library_op_requires_leaves_and_classic_silent():
    from mathagent.lattice.sleep import admit_library_op

    g = ResearchGraph(project_id="lib")
    assert (
        admit_library_op(
            g, {"name": "x", "statement": "op without leaves", "from": ["L1"]}
        )
        is None
    )
    node = admit_library_op(
        g,
        {
            "name": "binom",
            "statement": "(a+b)^2 identity schema",
            "from": ["lem"],
            "predicted_leaf_checks": [
                {
                    "statement": "(x+y)**2 = x**2+2*x*y+y**2",
                    "certify_hint": "sympy",
                    "sympy_hint": "(x+y)**2 = x**2 + 2*x*y + y**2",
                }
            ],
        },
    )
    assert node is not None
    assert node.meta.get("origin") == "sleep"
    assert node.status == NodeStatus.HUMAN_REVIEW
    assert len(g.by_kind(NodeKind.CONCEPT)) == 1


def test_negative_mdl_triggers_gate():
    prop = {
        "statement": "x" * 200,
        "closes_gap_ids": [],
        "opens_gap_ids": ["o1", "o2"],
        "axiom_ask": [{"id": "A1"}, {"id": "A2"}, {"id": "A3"}],
        "analogies": [{"check_status": "sympy"}],
        "belief": {"p_before": 0.4, "p_after": 0.41},
    }
    scores = score_proposal(prop)
    assert scores["mdl_gain"] < 0
    assert needs_human_gate(scores, axiom_asks=3) is True


def test_causal_surprise_from_leaves():
    from mathagent.lattice.causal import apply_causal_surprise
    from mathagent.lattice.graph import Node

    g = ResearchGraph(project_id="causal")
    c = g.admit_concept(
        "C",
        name="C",
        scores={"compression": 0.5, "minimality": 0.5, "systematicity": 0.5, "surprise": 0.2},
        human_gate=False,
    )
    c.meta["belief"] = {"p_before": 0.2, "p_after": 0.8}
    c.meta["scores"] = {
        "compression": 0.5,
        "minimality": 0.5,
        "systematicity": 0.5,
        "surprise": 0.2,
        "conceptual_value": 0.4,
    }
    leaf = Node.new(NodeKind.CONJECTURE, "leaf", from_concept=c.id)
    leaf.status = NodeStatus.CERTIFIED
    g.add(leaf)
    leaf2 = Node.new(NodeKind.CONJECTURE, "leaf2", from_concept=c.id)
    leaf2.status = NodeStatus.BLOCKED
    g.add(leaf2)
    reps = apply_causal_surprise(g)
    assert reps
    assert c.meta["belief"]["p_empirical"] == 0.5
    assert "surprise_llm" in c.meta["scores"]
