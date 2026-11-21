"""Offline experiment: conditional replacement of one fictional document."""
from dataclasses import dataclass
from itertools import permutations, product
import json


@dataclass(frozen=True)
class Draft:
    version: int
    words: tuple[str, ...]


@dataclass(frozen=True)
class Edit:
    base: int
    replacement: tuple[str, ...]


def save(draft: Draft, edit: Edit, compare: bool) -> tuple[Draft, str]:
    if compare and edit.base != draft.version:
        return draft, "conflict"
    return Draft(draft.version + 1, edit.replacement), "saved"


def require(valid: bool, context: object) -> None:
    if not valid:
        raise RuntimeError(f"verification failed: {context!r}")


def run() -> None:
    checked = 0
    policy_counts = dict(unconditional_overwrite=0, conditional_conflict=0, resolved=0)
    example = None
    for version, word_pair in product(range(4), permutations(("A", "B", "C"), 2)):
        start = Draft(version, ("original",))
        first, second = (Edit(version, start.words + (word,)) for word in word_pair)
        # Expected states are calculated independently from the two ordered edits.
        for compare in (False, True):
            after_first, first_outcome = save(start, first, compare)
            after_second, second_outcome = save(after_first, second, compare)
            require((after_first.version, after_first.words, first_outcome) ==
                    (version + 1, first.replacement, "saved"), (version, word_pair, compare, "first"))
            expected = ((version + 1, first.replacement, "conflict") if compare else
                        (version + 2, second.replacement, "saved"))
            require((after_second.version, after_second.words, second_outcome) == expected,
                    (version, word_pair, compare, "second"))
            if not compare:
                require(word_pair[0] not in after_second.words, word_pair)
                policy_counts["unconditional_overwrite"] += 1
            else:
                policy_counts["conditional_conflict"] += 1
                # Merge is explicitly supplied by an editor, not performed by save.
                resubmission = Edit(after_second.version, after_second.words + (word_pair[1],))
                merged, retry = save(after_second, resubmission, True)
                require((merged.version, merged.words, retry) ==
                        (version + 2, ("original", *word_pair), "saved"), (version, word_pair, "retry"))
                policy_counts["resolved"] += 1
            checked += 1
        if version == 0 and word_pair == ("A", "B"):
            example = dict(order=list(word_pair), unconditional=list(second.replacement),
                           conditional=list(first.replacement), after_explicit_retry=["original", *word_pair])
    print(json.dumps(dict(paired_scenarios=checked // 2, policy_runs=checked,
                          **policy_counts, example=example), indent=2))


if __name__ == "__main__":
    run()
