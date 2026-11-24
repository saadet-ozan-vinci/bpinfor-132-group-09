"""Block 2: layering, and what happens when a guard itself breaks.

Two questions block 1 could not answer.

  --layers  which attacks does the WHOLE stack miss, and what do the
            survivors have in common?
  --failmode what does the pipeline do when a guard raises, and does the
            declared fail mode actually decide it?

    python 02_layers.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "project_spine"))

from guards import GUARDS, Guard, Verdict  # noqa: E402
from traffic import ATTACKS, LEGIT  # noqa: E402

from project.trace import write_json  # noqa: E402

ORDER = ["input_naive", "input_tighter", "output_marker", "tool_argument"]


def layers() -> dict:
    print("WHICH LAYER CATCHES WHICH ATTACK\n")
    print(f"{'attack':<7}" + "".join(f"{n[:11]:>13}" for n in ORDER)
          + "   what it is")
    print("-" * 98)
    rows, uncaught = [], []
    for attack in ATTACKS:
        cells = []
        for name in ORDER:
            verdict, _, _ = GUARDS[name].run(attack.text)
            cells.append(bool(verdict.fired))
        covered = any(cells)
        if not covered:
            uncaught.append(attack)
        rows.append({"msg_id": attack.msg_id, "note": attack.note,
                     "covered": covered,
                     "by": [n for n, c in zip(ORDER, cells) if c]})
        print(f"{attack.msg_id:<7}"
              + "".join(f"{'FIRED' if c else '.':>13}" for c in cells)
              + f"   {attack.note[:30]}"
              + ("" if covered else "  <-- UNCAUGHT"))

    print(f"\n  {len(uncaught)} of {len(ATTACKS)} attacks pass every layer:")
    for attack in uncaught:
        print(f"    {attack.msg_id}  {attack.note}")
    print("\n  Both survivors say the same thing as the caught ones. They")
    print("  differ only in spelling, and a pattern is a spelling test.")
    print("  You cannot close this gap by adding patterns: the attacker")
    print("  writes the next one after seeing which one you added.")

    print("\n  Now read the columns instead of the rows. The pre_action")
    print("  guard catches fewer attacks than the input guards and is the")
    print("  only one that PREVENTS anything, because of where it sits.")
    print("  Detection and prevention are different jobs and placement,")
    print("  not cleverness, decides which one you built.")
    return {"rows": rows, "uncaught": [a.msg_id for a in uncaught]}


def failmode() -> dict:
    """A guard that raises has not made a decision. Something still must."""
    print("\n\nWHEN THE GUARD ITSELF BREAKS\n")

    def broken(_text: str) -> Verdict:
        raise RuntimeError("regex engine exploded")

    results = []
    for mode in ("open", "closed"):
        guard = Guard(f"broken_{mode}", "pre_model", "block", mode, broken)
        verdict, ms, triggered = guard.run("How much is the vignette?")
        outcome = "BLOCKED" if verdict.fired else "allowed through"
        results.append({"fail_mode": mode, "blocked": verdict.fired,
                        "fail_mode_triggered": triggered, "rule": verdict.rule})
        print(f"  fail_mode={mode:<7} a legitimate message is {outcome:<16}"
              f"  triggered={triggered}")

    print("\n  Neither answer is correct in general, and that is the point.")
    print("  Fail closed and a broken guard takes your service down for")
    print("  everyone. Fail open and a broken guard is indistinguishable")
    print("  from a guard that approved. You have to choose, per guard,")
    print("  and write the choice down beside the guard rather than")
    print("  discovering it during an incident.")
    print("\n  What is NOT optional is the record. Every event carries")
    print("  fail_mode_triggered, so 'the guard passed it' and 'the guard")
    print("  was not working' are two different rows and not one.")
    return {"cases": results}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", action="store_true")
    ap.add_argument("--failmode", action="store_true")
    args = ap.parse_args()
    if not (args.layers or args.failmode):
        args.layers = args.failmode = True

    out = {}
    if args.layers:
        out["layers"] = layers()
    if args.failmode:
        out["failmode"] = failmode()
    write_json("artifacts/week11_layers.json", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
