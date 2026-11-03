"""
Pillar 1 — Executable library (DreamCoder-inspired).

Library ops are not prose: they expose instantiable templates. Wake progress
that claims a concept must go through call_op(); failure refutes the binding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from mathagent.formal.certify import CertificateResult, certify_algebraic_claim
from mathagent.lattice.graph import Node, NodeKind, NodeStatus, ResearchGraph


_HOLE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def render_template(template: str, binding: dict[str, str]) -> str:
    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in binding:
            raise KeyError(f"missing binding for {{{{{key}}}}}")
        return str(binding[key])

    return _HOLE.sub(repl, template)


@dataclass
class CallResult:
    ok: bool
    method: str
    detail: str
    rendered: str = ""
    op_name: str = ""
    binding: dict[str, str] = field(default_factory=dict)


def extract_executable(concept: Node) -> dict[str, Any] | None:
    """Return executable artifact dict if the concept can be called."""
    art = dict(concept.meta.get("artifact") or {})
    lib = concept.meta.get("library_op") or {}
    if not art and isinstance(lib, dict):
        art = dict(lib.get("artifact") or {})
        if lib.get("template") and not art.get("sympy_template"):
            art["sympy_template"] = lib["template"]
        if lib.get("kind"):
            art.setdefault("kind", lib["kind"])
    tmpl = art.get("sympy_template") or art.get("template") or ""
    if not tmpl and concept.meta.get("predicted_leaf_checks"):
        # Leaf sympy_hints are weak executables (constant templates)
        return {"kind": "leaf_bundle", "leaves": concept.meta["predicted_leaf_checks"]}
    if not tmpl:
        return None
    art["sympy_template"] = tmpl
    return art


def list_callable_concepts(graph: ResearchGraph) -> list[Node]:
    out = []
    for n in graph.by_kind(NodeKind.CONCEPT):
        if n.status in {NodeStatus.REJECTED, NodeStatus.HUMAN_REVIEW}:
            continue
        if extract_executable(n) is not None:
            out.append(n)
    return out


def call_op(
    concept: Node,
    *,
    binding: dict[str, str] | None = None,
    statement: str = "",
) -> CallResult:
    """
    Execute one library op under a binding.
    SymPy path: render template; optional sympy_expand identity check;
    else treat rendered expression as nonneg / identity hint.
    """
    art = extract_executable(concept)
    name = str(concept.meta.get("name") or concept.id)
    if art is None:
        return CallResult(False, "no_exec", "concept has no executable artifact", op_name=name)

    if art.get("kind") == "leaf_bundle":
        # Run first leaf with hint as the call
        for leaf in art.get("leaves") or []:
            hint = str(leaf.get("sympy_hint") or "").strip()
            if not hint:
                continue
            res = certify_algebraic_claim(hint, statement=str(leaf.get("statement") or statement))
            return CallResult(
                res.ok, res.method, res.detail, rendered=hint, op_name=name, binding=binding or {}
            )
        return CallResult(False, "no_exec", "leaf_bundle has no sympy_hint", op_name=name)

    binding = binding or {}
    # Default binding from instantiations[0] if present
    if not binding:
        inst = (concept.meta.get("library_op") or {}).get("instantiations") or art.get(
            "instantiations"
        )
        if inst and isinstance(inst, list) and inst[0].get("binding"):
            binding = {str(k): str(v) for k, v in inst[0]["binding"].items()}

    tmpl = str(art.get("sympy_template") or "")
    try:
        rendered = render_template(tmpl, binding) if _HOLE.search(tmpl) else tmpl
    except KeyError as exc:
        return CallResult(False, "bind_error", str(exc), op_name=name, binding=binding)

    expand = str(art.get("sympy_expand") or "").strip()
    if expand:
        try:
            rhs = render_template(expand, binding) if _HOLE.search(expand) else expand
        except KeyError as exc:
            return CallResult(False, "bind_error", str(exc), rendered=rendered, op_name=name)
        hint = f"{rendered} = {rhs}"
    else:
        hint = rendered

    res: CertificateResult = certify_algebraic_claim(hint, statement=statement or concept.statement)
    tel = dict(concept.meta.get("telemetry") or {})
    tel["invoke_count"] = int(tel.get("invoke_count", 0)) + 1
    if res.ok:
        tel["invoke_success_count"] = int(tel.get("invoke_success_count", 0)) + 1
    concept.meta["telemetry"] = tel
    return CallResult(
        res.ok, res.method, res.detail, rendered=hint, op_name=name, binding=binding
    )


def wake_via_library(
    graph: ResearchGraph,
    node: Node,
    *,
    on_event: Any = None,
) -> CallResult | None:
    """
    If conjecture is linked from_concept with an executable parent, require call_op.
    Returns CallResult if attempted, None if no executable parent.
    """
    emit = on_event or (lambda _m: None)
    cid = node.meta.get("from_concept")
    if not cid or cid not in graph.nodes:
        return None
    parent = graph.nodes[cid]
    if extract_executable(parent) is None:
        return None
    # Prefer binding from leaf meta
    binding = dict(node.meta.get("binding") or {})
    emit(f"[think/exec] call_op {parent.meta.get('name')} for {node.id}")
    result = call_op(parent, binding=binding, statement=node.statement)
    # If leaf has its own sympy_hint, also allow that as the rendered check when template is schema
    if not result.ok and node.meta.get("sympy_hint"):
        hint = str(node.meta["sympy_hint"])
        res = certify_algebraic_claim(hint, statement=node.statement)
        result = CallResult(
            res.ok,
            res.method,
            f"leaf_hint|{res.detail}",
            rendered=hint,
            op_name=str(parent.meta.get("name") or parent.id),
            binding=binding,
        )
    if result.ok:
        graph.admit_lemma(node.statement, certificate=f"lib:{result.method}", parent_id=node.id)
        node.status = NodeStatus.CERTIFIED
        node.certificate = result.method
        node.meta["library_call"] = {
            "op": result.op_name,
            "rendered": result.rendered,
            "binding": result.binding,
        }
    else:
        node.meta["library_call_failed"] = result.detail
    return result
