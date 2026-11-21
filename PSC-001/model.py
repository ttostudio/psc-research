"""Defensive model of an internal, non-networked document editor."""
from dataclasses import dataclass
from enum import Enum

MAX_REVISION = 2


class Phase(Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    FINAL = "final"


class Action(Enum):
    REVISE = "revise"
    REVIEW = "review"
    FINALIZE = "finalize"


@dataclass(frozen=True)
class State:
    phase: Phase
    revision: int


@dataclass(frozen=True)
class Event:
    action: Action
    revision: int | None = None


INITIAL = State(Phase.DRAFT, 0)


def step(state: State, event: Event) -> State:
    if state.phase is Phase.FINAL:
        return state

    if event.action is Action.REVISE and event.revision is None:
        if state.revision < MAX_REVISION:
            return State(Phase.DRAFT, state.revision + 1)
        return state

    if event.revision != state.revision:
        return state

    if event.action is Action.REVIEW and state.phase is Phase.DRAFT:
        return State(Phase.REVIEWED, state.revision)

    if event.action is Action.FINALIZE and state.phase is Phase.REVIEWED:
        return State(Phase.FINAL, state.revision)

    return state
