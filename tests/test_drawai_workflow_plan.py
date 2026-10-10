import importlib.util
from pathlib import Path
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/drawai-readme/scripts/plan.py"
spec = importlib.util.spec_from_file_location("drawai_plan", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def request(model="gpt-5.6", **preferences):
    return {
        "environment": {"model": model, "model_source": "session_metadata", "image_generation_available": True, "image_viewing_available": True, "local_execution_available": True},
        "preferences": preferences,
    }


@pytest.mark.parametrize("model", [
    "gpt5.6", "gpt-6.1-sol", "openai/gpt-5.10", "claude-5", "Claude Sonnet 5.2",
    "anthropic/claude-opus-6", "deepseekflash v4.1 flash", "deepseek-v5-flash",
])
def test_requested_model_families_and_future_versions_route_to_session(model):
    plan = module.create_plan(request(model, skip_questions=True))
    assert plan["decisions"]["mode"] == "skill"
    assert plan["ready_to_start"]


@pytest.mark.parametrize("model", ["gpt-5.5-20991231", "claude-opus-4-6", "deepseek-v4.0-flash", "deepseek-v5-reasoner", "claude-latest", "other-model", "not-gpt-5.6"])
def test_predecessors_other_variants_and_unknown_versions_route_to_flow(model):
    assert module.create_plan(request(model, skip_questions=True))["decisions"]["mode"] == "flow"


def test_all_known_preferences_are_not_asked_again():
    data = request(reference="project", page_count=10, aspect_ratio="16:9", mode="skill")
    data["inputs"] = {"pptx_templates": ["/project/template.pptx"]}
    plan = module.create_plan(data)
    assert plan["questions"] == []
    assert plan["ready_to_start"]


def test_missing_selected_reference_is_a_real_input_blocker_even_when_questions_are_skipped():
    plan = module.create_plan(request(reference="project", skip_questions=True))
    assert plan["questions"] == []
    assert plan["blockers"]
    assert not plan["ready_to_start"]


def test_project_template_and_page_count_only_leave_ratio_and_mode_questions():
    data = request(page_count=10)
    data["inputs"] = {"pptx_templates": ["/project/template.pptx"]}
    plan = module.create_plan(data)
    assert plan["decisions"]["reference"] == "project"
    assert [q["id"] for q in plan["questions"]] == ["details", "mode"]
    assert "10" in plan["questions"][0]["title"]
    assert "页数" not in plan["questions"][0]["title"]


@pytest.mark.parametrize("flag", ["skip_questions", "workflow_specified"])
def test_no_question_and_already_specified_workflow_requests_start_with_defaults(flag):
    plan = module.create_plan(request(**{flag: True}))
    assert plan["questions"] == []
    assert plan["decisions"]["page_count"] == 8
    assert plan["decisions"]["aspect_ratio"] == "16:9"


def test_user_mode_overrides_policy_without_hiding_missing_capabilities():
    data = request("older-model", mode="skill", skip_questions=True)
    data["environment"]["local_execution_available"] = False
    plan = module.create_plan(data)
    assert plan["decisions"]["mode"] == "skill"
    assert plan["decisions"]["mode_source"] == "user"
    assert plan["blockers"]
    assert not plan["ready_to_start"]


def test_unknown_identity_and_tool_states_are_not_guessed_from_a_model_name():
    data = request(skip_questions=True)
    data["environment"]["model_source"] = "unknown"
    data["environment"]["image_generation_available"] = None
    plan = module.create_plan(data)
    assert plan["environment"]["identified_model"] is None
    assert plan["decisions"]["mode"] == "flow"
    assert plan["design"]["method"] == "local_render"


def test_provided_final_images_skip_design_and_redundant_reference_details():
    data = request(mode="skill")
    data["inputs"] = {"visual_page_count": 3, "visual_aspect_ratio": "4:3"}
    plan = module.create_plan(data)
    assert plan["design"]["method"] == "provided_visuals"
    assert plan["decisions"]["page_count"] == 3
    assert plan["questions"] == []


def test_missing_request_asks_three_points_and_does_not_start_before_answers():
    plan = module.create_plan(request())
    assert [q["id"] for q in plan["questions"]] == ["reference", "details", "mode"]
    assert not plan["ready_to_start"]


def test_string_capability_flags_and_conflicting_final_page_counts_fail_explicitly():
    data = request()
    data["environment"]["image_generation_available"] = "false"
    with pytest.raises(ValueError, match="boolean"):
        module.create_plan(data)
    data = request(page_count=4)
    data["inputs"] = {"visual_page_count": 3}
    with pytest.raises(ValueError, match="differs"):
        module.create_plan(data)
