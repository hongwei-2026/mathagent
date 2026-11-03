"""
Answer equivalence checker adapted from Hendrycks MATH / ToRA grader:
https://github.com/microsoft/ToRA (MIT)
"""

from __future__ import annotations

import re
from math import isclose
from typing import Union

from sympy import N, simplify
from sympy.parsing.sympy_parser import parse_expr

try:
    from sympy.parsing.latex import parse_latex
except Exception:  # pragma: no cover
    parse_latex = None  # type: ignore


FINAL_ANSWER_RE = re.compile(
    r"(?:FINAL_ANSWER|Final Answer|答案)\s*[:：]\s*(.+)",
    re.IGNORECASE,
)
BOXED_RE = re.compile(r"\\boxed\{([^{}]+)\}")


def extract_final_answer(text: str) -> str:
    if not text:
        return ""
    matches = FINAL_ANSWER_RE.findall(text)
    if matches:
        return matches[-1].strip().strip("`").strip()
    boxed = BOXED_RE.findall(text)
    if boxed:
        return boxed[-1].strip()
    # last non-empty line fallback
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def is_digit(s: object) -> bool:
    try:
        float(str(s).replace(",", ""))
        return True
    except ValueError:
        return False


def math_equal(
    prediction: Union[bool, float, str],
    reference: Union[float, str],
    include_percentage: bool = True,
    is_close: bool = True,
) -> bool:
    try:
        if is_digit(prediction) and is_digit(reference):
            prediction_f = float(str(prediction).replace(",", ""))
            reference_f = float(str(reference).replace(",", ""))
            gt_result = (
                [reference_f / 100, reference_f, reference_f * 100]
                if include_percentage
                else [reference_f]
            )
            for item in gt_result:
                if is_close:
                    if isclose(item, prediction_f, rel_tol=1e-4):
                        return True
                elif item == prediction_f:
                    return True
            return False
    except Exception:
        pass

    if prediction in ("", None) and prediction not in [0, False]:
        return False

    reference_s = str(reference).strip()
    prediction_s = str(prediction).strip()

    pred_str, ref_str = prediction_s, reference_s
    if (
        prediction_s.startswith("[")
        and prediction_s.endswith("]")
        and not reference_s.startswith("(")
    ) or (
        prediction_s.startswith("(")
        and prediction_s.endswith(")")
        and not reference_s.startswith("[")
    ):
        pred_str = pred_str.strip("[]()")
        ref_str = ref_str.strip("[]()")
    for s in ["{", "}", "(", ")"]:
        ref_str = ref_str.replace(s, "")
        pred_str = pred_str.replace(s, "")
    if pred_str == ref_str:
        return True

    if (
        (prediction_s.startswith("[") and prediction_s.endswith("]"))
        and (reference_s.startswith("[") and reference_s.endswith("]"))
    ) or (
        (prediction_s.startswith("(") and prediction_s.endswith(")"))
        and (reference_s.startswith("(") and reference_s.endswith(")"))
    ):
        pred_parts = prediction_s[1:-1].split(",")
        ref_parts = reference_s[1:-1].split(",")
        if len(pred_parts) == len(ref_parts) and all(
            math_equal(pred_parts[i], ref_parts[i], include_percentage, is_close)
            for i in range(len(pred_parts))
        ):
            return True

    return symbolic_equal(prediction_s, reference_s)


def symbolic_equal(a: str, b: str) -> bool:
    def _parse(s: str):
        parsers = [parse_expr]
        if parse_latex is not None:
            parsers = [parse_latex, parse_expr]
        for f in parsers:
            try:
                return f(s)
            except Exception:
                continue
        return s

    aa, bb = _parse(a), _parse(b)
    try:
        if simplify(aa - bb) == 0:
            return True
    except Exception:
        pass
    try:
        if isclose(float(N(aa)), float(N(bb)), rel_tol=1e-3):
            return True
    except Exception:
        pass
    return False
