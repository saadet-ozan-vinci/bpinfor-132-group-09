"""Week 4 reference solution: the two tools and their schemas.

The implementations are unchanged from the starter. The schemas are the
completed answers to TODO 1 and TODO 2, and the comments say what each clause
is defending against rather than what it does.

These are defensible descriptions, not the only good ones. Read them as an
argument and disagree where you have measured something different.
"""

import ast
import operator
from typing import Any, Dict, List

# The RAG stage retrieves commune information before the agent runs. The
# agent only receives compute as a tool, for arithmetic on retrieved facts.

_BINARY = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow,
    ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_CALLS = {"round": round, "min": min, "max": max, "abs": abs}


def _eval_node(node: ast.AST) -> float:
    """Walk a parsed expression, allowing only arithmetic."""

    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        return _BINARY[type(node.op)](_eval_node(node.left),
                                      _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval_node(node.operand))
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in _CALLS and not node.keywords):
        return _CALLS[node.func.id](*[_eval_node(a) for a in node.args])
    raise ValueError(
        "only arithmetic is allowed: numbers, + - * / // % **, parentheses, "
        "and round, min, max, abs")


def compute(expression: str) -> float:
    """Evaluate one arithmetic expression and return a number."""

    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("expression must be a non-empty string")
    if len(expression) > 200:
        raise ValueError("expression too long, at most 200 characters")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"could not parse the expression: {exc.msg}") from exc
    return round(float(_eval_node(tree)), 6)


# TODO 2 answered.
#
# The worked example is the load-bearing part. A description that says
# "evaluates an arithmetic expression" produces arguments like
# "26 collections * 8.50 EUR", which the evaluator rejects, which costs a
# full extra step. One example of a valid argument fixes it.
#
# The second half is a policy rather than a mechanism: it tells the model
# that arithmetic done in prose is not acceptable here. The reason given in
# the description ("the result is checkable") is deliberate. A rule with a
# reason attached is followed more reliably than a bare instruction, and it
# is also the reason a human reviewer would accept.
#
# We chose not to promise that repeated calls are free. The tool is
# read-only and idempotent, so an extra call costs money and nothing else,
# but saying "call it as often as you like" measurably increases the number
# of calls, and every call is a step against the cap.

COMPUTE_SCHEMA: Dict[str, Any] = {
    "name": "compute",
    "description": (
        "Evaluate one arithmetic expression and return the number. "
        "The expression may contain numbers, + - * / // % **, parentheses, "
        "and round, min, max, abs. It may NOT contain units, words, currency "
        "symbols, or variable names. "
        "Example of a valid expression: '26 * 8.50 + 24.00'. "
        "Use it for ANY arithmetic on figures you retrieved, instead of "
        "calculating in your answer, because a computed "
        "result can be checked and a number written out in prose cannot."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": ("Digits and operators only, for example "
                                "'40 * 2.50' or 'max(100, 150.00)'."),
            },
        },
        "required": ["expression"],
    },
}


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------

REGISTRY = {
    "compute": compute,
}

SCHEMAS = [COMPUTE_SCHEMA]


if __name__ == "__main__":
    print(compute("26 * 8.50 + 24.00"))
    try:
        compute("__import__('os').system('ls')")
    except ValueError as exc:
        print("rejected, as it should be:", exc)
