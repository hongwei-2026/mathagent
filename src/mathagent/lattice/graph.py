"""Typed research graph memory (Ansatz-inspired, laptop-scale)."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterator


class NodeKind(str, Enum):
    TARGET = "target"
    CONJECTURE = "conjecture"
    LEMMA = "lemma"
    PLAN = "plan"
    GAP = "gap"
    COUNTEREXAMPLE = "counterexample"
    CONCEPT = "concept"  # new language / definition (structure-learning slot)
    ABDUCTION = "abduction"  # explanatory proposal awaiting conceptual scoring


class NodeStatus(str, Enum):
    OPEN = "open"
    CERTIFIED = "certified"
    REFUTED = "refuted"
    BLOCKED = "blocked"
    ABSTRACTED = "abstracted"
    HUMAN_REVIEW = "human_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class Node:
    id: str
    kind: NodeKind
    statement: str
    status: NodeStatus = NodeStatus.OPEN
    score: float = 0.5
    certificate: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @staticmethod
    def new(kind: NodeKind, statement: str, **meta: Any) -> "Node":
        # Distinct prefixes: conjecture/concept both start with "con"
        prefix = {
            NodeKind.TARGET: "tgt",
            NodeKind.CONJECTURE: "cj",
            NodeKind.LEMMA: "lem",
            NodeKind.PLAN: "pln",
            NodeKind.GAP: "gap",
            NodeKind.COUNTEREXAMPLE: "cex",
            NodeKind.CONCEPT: "cpt",
            NodeKind.ABDUCTION: "abd",
        }.get(kind, kind.value[:3])
        return Node(
            id=f"{prefix}_{uuid.uuid4().hex[:10]}",
            kind=kind,
            statement=statement,
            meta=meta,
        )


@dataclass
class Edge:
    src: str
    dst: str
    relation: str  # depends | refutes | abstracts | supports | plans


@dataclass
class ResearchGraph:
    project_id: str
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    def add(self, node: Node) -> Node:
        self.nodes[node.id] = node
        return node

    def link(self, src: str, dst: str, relation: str) -> None:
        self.edges.append(Edge(src=src, dst=dst, relation=relation))

    def by_kind(self, kind: NodeKind) -> list[Node]:
        return [n for n in self.nodes.values() if n.kind == kind]

    def frontier(self, limit: int = 8) -> list[Node]:
        open_c = [
            n
            for n in self.nodes.values()
            if n.kind
            in {
                NodeKind.CONJECTURE,
                NodeKind.TARGET,
                NodeKind.GAP,
                NodeKind.CONCEPT,
                NodeKind.ABDUCTION,
            }
            and n.status in {NodeStatus.OPEN, NodeStatus.BLOCKED, NodeStatus.HUMAN_REVIEW}
        ]
        open_c.sort(key=lambda n: -n.score)
        return open_c[:limit]

    def conceptual_frontier(self, limit: int = 5) -> list[Node]:
        """Prefer Concept/Abduction ranked by conceptual_value meta score."""
        cands = [
            n
            for n in self.nodes.values()
            if n.kind in {NodeKind.CONCEPT, NodeKind.ABDUCTION}
            and n.status in {NodeStatus.OPEN, NodeStatus.HUMAN_REVIEW, NodeStatus.ACCEPTED}
        ]

        def _v(n: Node) -> float:
            scores = (n.meta or {}).get("scores") or {}
            return float(scores.get("conceptual_value", n.score))

        cands.sort(key=_v, reverse=True)
        return cands[:limit]

    def admit_concept(
        self,
        statement: str,
        *,
        name: str = "",
        closes_gap_ids: list[str] | None = None,
        scores: dict[str, float] | None = None,
        human_gate: bool = True,
    ) -> Node:
        node = Node.new(
            NodeKind.CONCEPT,
            statement,
            name=name or statement[:60],
            closes_gap_ids=closes_gap_ids or [],
            scores=scores or {},
            human_gate={"required": human_gate, "notes": ""},
        )
        if scores and "conceptual_value" in scores:
            node.score = float(scores["conceptual_value"])
        node.status = NodeStatus.HUMAN_REVIEW if human_gate else NodeStatus.OPEN
        self.add(node)
        for gid in closes_gap_ids or []:
            if gid in self.nodes:
                self.link(node.id, gid, "abstracts")
        return node

    def admit_lemma(self, statement: str, certificate: str, parent_id: str | None = None) -> Node:
        node = Node.new(NodeKind.LEMMA, statement, source=parent_id)
        node.status = NodeStatus.CERTIFIED
        node.certificate = certificate
        node.score = 0.9
        self.add(node)
        if parent_id:
            self.link(parent_id, node.id, "supports")
        return node

    def add_gap(self, statement: str, parent_id: str | None = None, reason: str = "") -> Node:
        node = Node.new(NodeKind.GAP, statement, reason=reason)
        node.status = NodeStatus.BLOCKED
        node.score = 0.2
        self.add(node)
        if parent_id:
            self.link(parent_id, node.id, "depends")
        return node

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for n in self.nodes.values():
            key = f"{n.kind.value}:{n.status.value}"
            counts[key] = counts.get(key, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "nodes": [asdict(n) | {"kind": n.kind.value, "status": n.status.value} for n in self.nodes.values()],
            "edges": [asdict(e) for e in self.edges],
            "summary": self.summary(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchGraph":
        g = cls(project_id=data["project_id"])
        for raw in data.get("nodes", []):
            g.nodes[raw["id"]] = Node(
                id=raw["id"],
                kind=NodeKind(raw["kind"]),
                statement=raw["statement"],
                status=NodeStatus(raw["status"]),
                score=float(raw.get("score", 0.5)),
                certificate=raw.get("certificate", ""),
                meta=raw.get("meta") or {},
                created_at=raw.get("created_at", ""),
            )
        for e in data.get("edges", []):
            g.edges.append(Edge(**e))
        return g


class GraphStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path("data/lattice")
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, project_id: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_id)[:80]
        return self.root / f"{safe}.json"

    def save(self, graph: ResearchGraph) -> Path:
        path = self.path_for(graph.project_id)
        path.write_text(json.dumps(graph.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, project_id: str) -> ResearchGraph | None:
        path = self.path_for(project_id)
        if not path.exists():
            return None
        return ResearchGraph.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def iter_projects(self) -> Iterator[Path]:
        yield from self.root.glob("*.json")
