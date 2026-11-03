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
    c.meta["predicted_leaf_checks"] = [
        {
            "statement": "(x+y)^2 = x^2 + 2*x*y + y^2",
            "certify_hint": "sympy",
            "sympy_hint": "expand((x+y)**2 - (x**2 + 2*x*y + y**2))",
        }
    ]
    spawned = spawn_leaf_conjectures_from_concepts(g)
    assert len(spawned) == 1
    assert spawned[0].meta.get("from_concept") == c.id
    report = curator_report(g)
    assert report["concepts"] == 1


def test_analogy_unchecked_without_hint():
    verified, claimed = verify_analogy_maps(
        [{"domain_a": "groups", "domain_b": "rings", "maps": [{"a": "hom", "b": "hom"}]}]
    )
    assert claimed == 1
    assert verified == 0
