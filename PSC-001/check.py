"""Enumerate the finite graph and compare it to a separate relation.

No dependency or I/O except reading local Python modules and writing test output.
"""
from collections import Counter, deque
from itertools import product
import json
import sys

from model import Action, Event, INITIAL, MAX_REVISION, Phase, State, step

# Specification encoded as a table, independent of the step() control flow. The cap
# is intentionally fixed in both places and is asserted on the test boundary.
assert MAX_REVISION == 2, "Updating the model's bound requires a spec decision."
REVISIONS = (0, 1, 2)
STATES = tuple((p, r) for p, r in product(("draft", "reviewed", "final"), REVISIONS))
ALPHABET = tuple(product(("revise", "review", "finalize"), (None, 0, 1, 2)))


def relation():
    allowed = {}
    for r in REVISIONS:
        allowed[(("draft", r), ("review", r))] = ("reviewed", r)
        allowed[(("reviewed", r), ("finalize", r))] = ("final", r)
    for lo, hi in zip(REVISIONS, REVISIONS[1:]):
        for phase in ("draft", "reviewed"):
            allowed[((phase, lo), ("revise", None))] = ("draft", hi)
    return allowed


def key(state):
    return state.phase.value, state.revision


def validate_implementation():
    allowed = relation()
    actual = {}
    for phase, rev in STATES:
        state = State(Phase(phase), rev)
        for name, event_rev in ALPHABET:
            event = Event(Action(name), event_rev)
            after = step(state, event)
            actual[(key(state), (name, event_rev))] = key(after)
            expected = allowed.get((key(state), (name, event_rev)), key(state))
            assert key(after) == expected, (state, event, after, expected)
            assert key(after) in STATES, (state, event, after)

    assert Counter(
        a == b for (a, _), b in actual.items()
    ) == {True: 98, False: 10}
    return actual


def validate_reachability(actual):
    # Ghost data: visited states carry the revision last reviewed, if any.
    # Track per path's abstract history; reset on revision; never trust status.
    initial = (key(INITIAL), None)
    seen = {initial}
    pending = deque([initial])
    checks = 0
    while pending:
        old, last_review = pending.popleft()
        if old[0] in ("reviewed", "final"):
            assert last_review == old[1], (old, last_review)
        for event in ALPHABET:
            checks += 1
            after = actual[(old, event)]
            next_review = last_review
            if after != old:
                if event[0] == "review":
                    next_review = event[1]
                elif event[0] == "revise":
                    next_review = None
            if old[0] == "final":
                assert old == after, (old, event, after)
            result = (after, next_review)
            if result not in seen:
                seen.add(result)
                pending.append(result)
    assert {s for s, _ in seen} == set(STATES), seen
    return seen, checks


# Demonstrate that the acceptance set is not vacuous. These are internal
# typed workflow actions over an in-memory toy state, not a real target.
def scenarios(actual):
    draft0 = key(INITIAL)
    examples = [
        ("no_review", [("finalize", 0)], ("draft", 0)),
        ("review_and_finalize", [("review", 0), ("finalize", 0)], ("final", 0)),
        ("changed_revision_requires_review", [
            ("review", 0), ("revise", None), ("finalize", 1)
        ], ("draft", 1)),
        ("old_revision_does_not_seal_current_review", [
            ("review", 0), ("revise", None), ("review", 1), ("finalize", 0)
        ], ("reviewed", 1)),
        ("latest_revision_can_seal", [
            ("review", 0), ("revise", None), ("review", 1), ("finalize", 1)
        ], ("final", 1)),
        ("final_state_cannot_be_edited", [
            ("review", 0), ("finalize", 0), ("revise", None)
        ], ("final", 0)),
        ("revision_cap", [
            ("revise", None), ("revise", None), ("revise", None)
        ], ("draft", 2)),
    ]
    out = {}
    for name, events, expected in examples:
        state = draft0
        for event in events:
            state = actual[(state, event)]
        assert state == expected, (name, state, expected)
        out[name] = state
    return out


if __name__ == "__main__":
    if not __debug__:
        sys.exit("Assertions must be enabled. Run without Python -O.")
    transitions = validate_implementation()
    reachable, checked = validate_reachability(transitions)
    print(json.dumps({
        "id": "PSC-001", "level": "L2", "scope": "SEC-004 toy model",
        "interpreter": sys.version.split()[0],
        "revision_domain": REVISIONS, "event_values": len(ALPHABET),
        "state_event_pairs": len(transitions),
        "state_changes": sum(a != b for (a, _), b in transitions.items()),
        "unchanged_pairs": sum(a == b for (a, _), b in transitions.items()),
        "reachable_history_augmented_states": len(reachable),
        "reachable_history_augmented_edges_checked": checked,
        "scenarios": scenarios(transitions), "status": "PASS"
    }, indent=2))
