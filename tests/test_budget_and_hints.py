from mathagent.formal.budget import Budget
from mathagent.formal.tactic_hints import skeleton_prompt_block


def test_budget_exhaustion():
    b = Budget(max_tokens=1000, max_llm_calls=2)
    assert b.can_call(100)
    b.record("a", 600)
    b.record("b", 600)
    assert b.exhausted or not b.can_call(100)


def test_skeleton_prompt_nonempty():
    block = skeleton_prompt_block()
    assert "simp" in block
    assert "omega" in block
