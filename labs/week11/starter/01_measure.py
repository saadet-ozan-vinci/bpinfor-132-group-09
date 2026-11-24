"""Block 1: measure every guard on BOTH corpora, and write the events.

A guard is judged on two numbers that only mean something together:

  catch rate   of the hostile messages, how many fired
  false blocks of the legitimate messages, how many fired

Report the first alone and a guard that blocks everything looks perfect.

Offline. No model call anywhere in this session, which is deliberate: the
guards are code, the traffic is fixed, and the whole matrix reproduces
exactly on any machine.

    python 01_measure.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "project_spine"))

from guards import GUARDS  # noqa: E402
from traffic import ALL, ATTACKS, LEGIT  # noqa: E402

from project.contracts import GuardEvent  # noqa: E402
from project.trace import repo_root, write_json  # noqa: E402

# repo_root, not a relative path: the events are a project artifact that
# week 12 reloads, and where they land must not depend on which directory
# you happened to run this from.
EVENTS_PATH = repo_root() / "artifacts" / "guard_events.jsonl"


def measure(guard_name: str) -> dict:
    guard = GUARDS[guard_name]
    events: list[GuardEvent] = []
    caught, false_blocks, total_ms = 0, [], 0.0

    for message in ALL:
        verdict, ms, triggered = guard.run(message.text)
        total_ms += ms
        if verdict.fired:
            if message.hostile:
                caught += 1
            else:
                false_blocks.append(message)
        events.append(GuardEvent(
            trace_id=f"w11-{message.msg_id}", guard_name=guard.name,
            placement=guard.placement, fired=verdict.fired,
            action=guard.action if verdict.fired else "allow",
            # The RULE that matched, never the input itself. A guard log
            # that stores the message is a log full of the exact content
            # you built the guard to keep out.
            rule=verdict.rule or "no rule matched",
            added_ms=ms, fail_mode_triggered=triggered))

    return {"guard": guard.name, "placement": guard.placement,
            "action": guard.action, "fail_mode": guard.fail_mode,
            "caught": caught, "attacks": len(ATTACKS),
            "false_blocks": [m.msg_id for m in false_blocks],
            "legit": len(LEGIT),
            "us_per_call": round(total_ms * 1000 / len(ALL), 1),
            "events": [e.model_dump() for e in events]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--guard", default=None)
    args = ap.parse_args()

    names = [args.guard] if args.guard else list(GUARDS)
    print(f"{'guard':<16}{'placement':<12}{'caught':>8}{'false blk':>11}"
          f"{'us/call':>10}")
    print("-" * 60)
    rows, all_events = [], []
    for name in names:
        row = measure(name)
        rows.append({k: v for k, v in row.items() if k != "events"})
        all_events.extend(row["events"])
        print(f"{row['guard']:<16}{row['placement']:<12}"
              f"{row['caught']:>5}/{row['attacks']:<3}"
              f"{len(row['false_blocks']):>7}/{row['legit']:<3}"
              f"{row['us_per_call']:>10.1f}")
        for msg_id in row["false_blocks"]:
            hit = next(m for m in LEGIT if m.msg_id == msg_id)
            print(f"                  false block {msg_id}: {hit.text[:44]!r}")

    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("w") as fh:
        for event in all_events:
            fh.write(GuardEvent(**event).model_dump_json() + "\n")
    write_json("artifacts/week11_guards.json", {"rows": rows})

    print(f"\n  {len(all_events)} guard events written to {EVENTS_PATH}")
    print("\n  Read the two columns together, never one at a time.")
    print("  Tightening the input guard buys catches and costs real users,")
    print("  and the exchange rate is the only thing worth arguing about.")
    print("\n  Then find the attacks that NO input guard caught, look at")
    print("  what makes them different, and ask what would have stopped")
    print("  them. The answer is not a better pattern.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
