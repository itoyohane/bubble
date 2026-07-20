from bubble_agent.agents.policies import policy_for
from bubble_agent.domain.schemas import Depth


def test_depth_policies_change_real_execution_controls() -> None:
    spark = policy_for(Depth.SPARK)
    builder = policy_for(Depth.BUILDER)
    architect = policy_for(Depth.ARCHITECT)

    assert spark.max_questions < builder.max_questions < architect.max_questions
    assert not spark.enable_divergence
    assert builder.enable_divergence and architect.enable_divergence
    assert (spark.critic_rounds, builder.critic_rounds, architect.critic_rounds) == (0, 1, 2)
    assert len(spark.artifact_types) < len(builder.artifact_types) < len(architect.artifact_types)
