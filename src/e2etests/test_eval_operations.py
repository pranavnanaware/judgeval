"""
Tests for evaluation operations in the JudgmentClient.
"""

import pytest

from judgeval.judgment_client import JudgmentClient
from judgeval.data import Example
from judgeval.scorers import (
    FaithfulnessScorer,
    AnswerRelevancyScorer,
    ToolOrderScorer,
)
from judgeval.data.datasets.dataset import EvalDataset
from judgeval.tracer import Tracer


def run_eval_helper(client: JudgmentClient, project_name: str, eval_run_name: str):
    """Helper function to run evaluation."""
    # Single step in our workflow, an outreach Sales Agent
    example1 = Example(
        input="Generate a cold outreach email for TechCorp. Facts: They recently launched an AI-powered analytics platform. Their CEO Sarah Chen previously worked at Google. They have 50+ enterprise clients.",
        actual_output="Dear Ms. Chen,\n\nI noticed TechCorp's recent launch of your AI analytics platform and was impressed by its enterprise-focused approach. Your experience from Google clearly shines through in building scalable solutions, as evidenced by your impressive 50+ enterprise client base.\n\nWould you be open to a brief call to discuss how we could potentially collaborate?\n\nBest regards,\nAlex",
        retrieval_context=[
            "TechCorp launched AI analytics platform in 2024",
            "Sarah Chen is CEO, ex-Google executive",
            "Current client base: 50+ enterprise customers",
        ],
    )

    example2 = Example(
        input="Generate a cold outreach email for GreenEnergy Solutions. Facts: They're developing solar panel technology that's 30% more efficient. They're looking to expand into the European market. They won a sustainability award in 2023.",
        actual_output="Dear GreenEnergy Solutions team,\n\nCongratulations on your 2023 sustainability award! Your innovative solar panel technology with 30% higher efficiency is exactly what the European market needs right now.\n\nI'd love to discuss how we could support your European expansion plans.\n\nBest regards,\nAlex",
        expected_output="A professional cold email mentioning the sustainability award, solar technology innovation, and European expansion plans",
        context=["Business Development"],
        retrieval_context=[
            "GreenEnergy Solutions won 2023 sustainability award",
            "New solar technology 30% more efficient",
            "Planning European market expansion",
        ],
    )

    scorer = FaithfulnessScorer(threshold=0.5)
    scorer2 = AnswerRelevancyScorer(threshold=0.5)

    client.run_evaluation(
        examples=[example1, example2],
        scorers=[scorer, scorer2],
        model="Qwen/Qwen2.5-72B-Instruct-Turbo",
        project_name=project_name,
        eval_run_name=eval_run_name,
        override=True,
    )


def test_run_eval(client: JudgmentClient):
    """Test basic evaluation workflow."""
    PROJECT_NAME = "OutreachWorkflow"
    EVAL_RUN_NAME = "ColdEmailGenerator-Improve-BasePrompt"

    run_eval_helper(client, PROJECT_NAME, EVAL_RUN_NAME)
    results = client.pull_eval(project_name=PROJECT_NAME, eval_run_name=EVAL_RUN_NAME)
    assert results, f"No evaluation results found for {EVAL_RUN_NAME}"

    client.delete_project(project_name=PROJECT_NAME)


def test_run_eval_append(client: JudgmentClient):
    """Test evaluation append behavior."""
    PROJECT_NAME = "OutreachWorkflow"
    EVAL_RUN_NAME = "ColdEmailGenerator-Improve-BasePrompt"

    run_eval_helper(client, PROJECT_NAME, EVAL_RUN_NAME)
    results = client.pull_eval(project_name=PROJECT_NAME, eval_run_name=EVAL_RUN_NAME)
    results = results["examples"]
    assert results, f"No evaluation results found for {EVAL_RUN_NAME}"
    assert len(results) == 2

    example1 = Example(
        input="Generate a cold outreach email for TechCorp. Facts: They recently launched an AI-powered analytics platform. Their CEO Sarah Chen previously worked at Google. They have 50+ enterprise clients.",
        actual_output="Dear Ms. Chen,\n\nI noticed TechCorp's recent launch of your AI analytics platform and was impressed by its enterprise-focused approach. Your experience from Google clearly shines through in building scalable solutions, as evidenced by your impressive 50+ enterprise client base.\n\nWould you be open to a brief call to discuss how we could potentially collaborate?\n\nBest regards,\nAlex",
        retrieval_context=[
            "TechCorp launched AI analytics platform in 2024",
            "Sarah Chen is CEO, ex-Google executive",
            "Current client base: 50+ enterprise customers",
        ],
    )
    scorer = FaithfulnessScorer(threshold=0.5)

    client.run_evaluation(
        examples=[example1],
        scorers=[scorer],
        model="Qwen/Qwen2.5-72B-Instruct-Turbo",
        project_name=PROJECT_NAME,
        eval_run_name=EVAL_RUN_NAME,
        append=True,
    )

    results = client.pull_eval(project_name=PROJECT_NAME, eval_run_name=EVAL_RUN_NAME)
    assert results, f"No evaluation results found for {EVAL_RUN_NAME}"
    results = results["examples"]
    assert len(results) == 3
    assert results[0]["scorer_data"][0]["score"] == 1.0
    client.delete_project(project_name=PROJECT_NAME)


def test_run_append_without_existing(client: JudgmentClient, project_name: str):
    """Test evaluation append behavior when the eval run does not exist."""
    EVAL_RUN_NAME = "ColdEmailGenerator-Improve-BasePrompt"

    example1 = Example(
        input="Generate a cold outreach email for TechCorp. Facts: They recently launched an AI-powered analytics platform. Their CEO Sarah Chen previously worked at Google. They have 50+ enterprise clients.",
        actual_output="Dear Ms. Chen,\n\nI noticed TechCorp's recent launch of your AI analytics platform and was impressed by its enterprise-focused approach. Your experience from Google clearly shines through in building scalable solutions, as evidenced by your impressive 50+ enterprise client base.\n\nWould you be open to a brief call to discuss how we could potentially collaborate?\n\nBest regards,\nAlex",
        retrieval_context=[
            "TechCorp launched AI analytics platform in 2024",
            "Sarah Chen is CEO, ex-Google executive",
            "Current client base: 50+ enterprise customers",
        ],
    )
    scorer = AnswerRelevancyScorer(threshold=0.5)

    results = client.run_evaluation(
        examples=[example1],
        scorers=[scorer],
        model="gpt-4o-mini",
        project_name=project_name,
        eval_run_name=EVAL_RUN_NAME,
        append=True,
    )
    assert results, f"No evaluation results found for {EVAL_RUN_NAME}"
    assert len(results) == 1
    print(results)
    assert results[0].success


@pytest.mark.asyncio
async def test_assert_test(client: JudgmentClient, project_name: str):
    """Test assertion functionality."""
    # Create examples and scorers as before
    example = Example(
        input="What if these shoes don't fit?",
        actual_output="We offer a 30-day full refund at no extra cost.",
        retrieval_context=[
            "All customers are eligible for a 30 day full refund at no extra cost."
        ],
    )

    example1 = Example(
        input="How much are your croissants?",
        actual_output="Sorry, we don't accept electronic returns.",
    )

    example2 = Example(
        input="Who is the best basketball player in the world?",
        actual_output="No, the room is too small.",
    )

    scorer = AnswerRelevancyScorer(threshold=0.5)

    with pytest.raises(AssertionError):
        await client.assert_test(
            eval_run_name="test_eval",
            project_name=project_name,
            examples=[example, example1, example2],
            scorers=[scorer],
            model="Qwen/Qwen2.5-72B-Instruct-Turbo",
            override=True,
        )


def test_evaluate_dataset(client: JudgmentClient, project_name: str):
    """Test dataset evaluation."""
    example1 = Example(
        input="What if these shoes don't fit?",
        actual_output="We offer a 30-day full refund at no extra cost.",
        retrieval_context=[
            "All customers are eligible for a 30 day full refund at no extra cost."
        ],
    )

    example2 = Example(
        input="How do I reset my password?",
        actual_output="You can reset your password by clicking on 'Forgot Password' at the login screen.",
        expected_output="You can reset your password by clicking on 'Forgot Password' at the login screen.",
        name="Password Reset",
        context=["User Account"],
        retrieval_context=["Password reset instructions"],
        additional_metadata={"difficulty": "medium"},
    )

    dataset = EvalDataset(examples=[example1, example2])
    res = client.run_evaluation(
        examples=dataset.examples,
        scorers=[FaithfulnessScorer(threshold=0.5)],
        model="Qwen/Qwen2.5-72B-Instruct-Turbo",
        project_name=project_name,
        eval_run_name="test_eval_run",
        override=True,
    )
    assert res, "Dataset evaluation failed"


@pytest.mark.asyncio
async def test_run_trace_eval(
    client: JudgmentClient, project_name: str, random_name: str
):
    EVAL_RUN_NAME = random_name
    tracer = Tracer(project_name=project_name)

    @tracer.observe(span_type="tool")
    def simple_function(text: str):
        return "finished {text}"

    example1 = Example(
        input="input",
        expected_tools=[
            {"tool_name": "simple_function", "parameters": {"text": "input"}}
        ],
    )

    example2 = Example(
        input="input2",
        expected_tools=[
            {"tool_name": "simple_function", "parameters": {"text": "input2"}}
        ],
    )

    scorer = ToolOrderScorer(threshold=0.5)
    results = client.run_trace_evaluation(
        examples=[example1, example2],
        function=simple_function,
        tracer=tracer,
        scorers=[scorer],
        project_name=project_name,
        eval_run_name=EVAL_RUN_NAME,
        override=True,
    )
    assert results, (
        f"No evaluation results found for {EVAL_RUN_NAME} in project {project_name}"
    )
    assert len(results) == 2, f"Expected 2 trace results but got {len(results)}"

    assert results[0].success
    assert results[1].success


@pytest.mark.asyncio
async def test_run_trace_eval_with_project_mismatch(
    client: JudgmentClient, project_name: str, random_name: str
):
    EVAL_RUN_NAME = random_name

    tracer = Tracer(project_name="mismatching-project")
    scorer = ToolOrderScorer(threshold=0.5)
    example = Example(input="hello")

    @tracer.observe(span_type="tool")
    def simple_function(text: str):
        return f"Processed: {text.upper()}"

    with pytest.raises(
        ValueError, match="Project name mismatch between run_trace_eval and tracer."
    ):
        client.run_trace_evaluation(
            examples=[example],
            function=simple_function,
            tracer=tracer,
            scorers=[scorer],
            project_name=project_name,
            eval_run_name=EVAL_RUN_NAME,
            override=True,
        )


def test_override_eval(client: JudgmentClient, project_name: str, random_name: str):
    """Test evaluation override behavior."""
    example1 = Example(
        input="What if these shoes don't fit?",
        actual_output="We offer a 30-day full refund at no extra cost.",
        retrieval_context=[
            "All customers are eligible for a 30 day full refund at no extra cost."
        ],
    )

    scorer = FaithfulnessScorer(threshold=0.5)

    EVAL_RUN_NAME = random_name

    # First run should succeed
    client.run_evaluation(
        examples=[example1],
        scorers=[scorer],
        model="Qwen/Qwen2.5-72B-Instruct-Turbo",
        project_name=project_name,
        eval_run_name=EVAL_RUN_NAME,
        override=False,
    )

    # This should fail because the eval run name already exists
    with pytest.raises(ValueError, match="already exists"):
        client.run_evaluation(
            examples=[example1],
            scorers=[scorer],
            model="Qwen/Qwen2.5-72B-Instruct-Turbo",
            project_name=project_name,
            eval_run_name=EVAL_RUN_NAME,
            override=False,
        )

    # Third run with override=True should succeed
    try:
        client.run_evaluation(
            examples=[example1],
            scorers=[scorer],
            model="Qwen/Qwen2.5-72B-Instruct-Turbo",
            project_name=project_name,
            eval_run_name=EVAL_RUN_NAME,
            override=True,
        )
    except ValueError as e:
        print(f"Unexpected error in override run: {e}")
        raise

    # Final non-override run should fail
    with pytest.raises(ValueError, match="already exists"):
        client.run_evaluation(
            examples=[example1],
            scorers=[scorer],
            model="Qwen/Qwen2.5-72B-Instruct-Turbo",
            project_name=project_name,
            eval_run_name=EVAL_RUN_NAME,
            override=False,
        )
