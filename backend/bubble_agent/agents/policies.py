from __future__ import annotations

from dataclasses import asdict, dataclass

from bubble_agent.domain.schemas import Depth


@dataclass(frozen=True, slots=True)
class DepthPolicy:
    depth: Depth
    max_questions: int
    enable_divergence: bool
    critic_rounds: int
    artifact_types: tuple[str, ...]
    token_budget: int

    def to_state(self) -> dict[str, object]:
        result = asdict(self)
        result["depth"] = self.depth.value
        result["artifact_types"] = list(self.artifact_types)
        return result


DEPTH_POLICIES: dict[Depth, DepthPolicy] = {
    Depth.SPARK: DepthPolicy(
        depth=Depth.SPARK,
        max_questions=2,
        enable_divergence=False,
        critic_rounds=0,
        artifact_types=("prd", "mvp"),
        token_budget=4_000,
    ),
    Depth.BUILDER: DepthPolicy(
        depth=Depth.BUILDER,
        max_questions=5,
        enable_divergence=True,
        critic_rounds=1,
        artifact_types=("prd", "mvp", "technical_plan"),
        token_budget=10_000,
    ),
    Depth.ARCHITECT: DepthPolicy(
        depth=Depth.ARCHITECT,
        max_questions=8,
        enable_divergence=True,
        critic_rounds=2,
        artifact_types=("prd", "mvp", "technical_plan", "architecture_draft"),
        token_budget=18_000,
    ),
}


def policy_for(depth: Depth | str) -> DepthPolicy:
    value = depth if isinstance(depth, Depth) else Depth(depth)
    return DEPTH_POLICIES[value]
