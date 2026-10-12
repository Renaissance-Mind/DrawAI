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
def test_all_session_models_stay_in_the_current_agent(model):
    assert module.create_plan(request(model, skip_questions=True))["decisions"]["mode"] == "skill"


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


def test_project_template_and_page_count_only_leave_ratio_question():
    data = request(page_count=10)
    data["inputs"] = {"pptx_templates": ["/project/template.pptx"]}
    plan = module.create_plan(data)
    assert plan["decisions"]["reference"] == "project"
    assert [q["id"] for q in plan["questions"]] == ["details"]
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
    assert plan["decisions"]["mode"] == "skill"
    assert plan["design"]["method"] == "local_render"


def test_provided_final_images_skip_design_and_redundant_reference_details():
    data = request(mode="skill")
    data["inputs"] = {"visual_page_count": 3, "visual_aspect_ratio": "4:3"}
    plan = module.create_plan(data)
    assert plan["design"]["method"] == "provided_visuals"
    assert plan["decisions"]["page_count"] == 3
    assert plan["questions"] == []


def test_missing_content_preferences_are_asked_without_replacing_the_agent():
    plan = module.create_plan(request())
    assert [q["id"] for q in plan["questions"]] == ["reference", "details"]
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


@pytest.mark.parametrize("agent,model", [("claude", "claude-opus-4-6"), ("codex", "gpt-6.1-sol"), ("custom-host", None)])
def test_session_implementation_preserves_the_callers_configuration(agent, model):
    data = request(model, skip_questions=True)
    data["environment"]["agent"] = agent
    plan = module.create_plan(data)
    assert plan["implementation"] == {"executor": "current_session", "agent": agent, "model": model, "configuration_source": "caller_session"}


def test_missing_session_tools_block_without_silently_delegating_to_flow():
    data = request(skip_questions=True)
    data["environment"]["local_execution_available"] = False
    data["environment"]["flow_available"] = True
    plan = module.create_plan(data)
    assert plan["decisions"]["mode"] == "skill"
    assert not plan["ready_to_start"]


def test_api_visual_generation_is_independent_of_the_implementation_agent():
    data = request("claude-latest", image_generation="api", image_connection="personal-images", skip_questions=True)
    data["environment"].update(agent="claude", image_api_available=True)
    plan = module.create_plan(data)
    assert plan["design"]["method"] == "image_generation_api"
    assert plan["implementation"]["agent"] == "claude"
    assert plan["decisions"]["mode"] == "skill"


def test_explicit_missing_image_connection_is_reported_instead_of_using_host_tools():
    data = request(image_generation="api", image_connection="unconfigured", skip_questions=True)
    data["environment"]["image_api_available"] = False
    plan = module.create_plan(data)
    assert plan["design"]["method"] == "image_generation_api"
    assert plan["blockers"]


def test_standalone_environment_uses_configured_flow_and_user_choice_still_wins():
    data = request(skip_questions=True)
    data["environment"]["context"] = "workbench"
    assert module.create_plan(data)["decisions"]["mode"] == "flow"
    data["environment"]["context"] = "session"
    data["preferences"]["mode"] = "flow"
    data["environment"]["agent"] = "claude"
    assert module.create_plan(data)["decisions"]["mode"] == "flow"


def test_explicit_other_agent_requires_confirmed_execution_capability():
    data = request(implementation_agent="claude", skip_questions=True)
    assert not module.create_plan(data)["ready_to_start"]
    data["environment"]["external_agent_available"] = True
    plan = module.create_plan(data)
    assert plan["implementation"]["executor"] == "explicit_agent"
    assert plan["implementation"]["agent"] == "claude"



def test_explicit_session_flow_carries_current_agent_parameters_without_credentials():
    data = request("claude-opus-4-6", mode="flow", skip_questions=True)
    data["environment"].update(agent="claude", agent_config={"reasoning_effort": "high", "api_key": "must-not-copy"})
    plan = module.create_plan(data)
    assert plan["implementation"]["flow_agent_settings"] == {"selected_provider_id": "claude_cli", "model": "claude-opus-4-6", "reasoning_effort": "high"}
    assert plan["implementation"]["configuration_source"] == "caller_session"


def test_unknown_caller_in_explicit_flow_needs_agent_identity_or_user_override():
    data = request(mode="flow", skip_questions=True)
    assert module.create_plan(data)["blockers"]
    data["preferences"]["implementation_agent"] = "configured"
    assert module.create_plan(data)["implementation"]["configuration_source"] == "workbench"


def test_explicit_current_session_model_is_not_silently_ignored_or_falsely_applied():
    data = request("caller-model", implementation_model="requested-model", skip_questions=True)
    plan = module.create_plan(data)
    assert plan["implementation"]["model"] == "caller-model"
    assert plan["implementation"]["requested_model"] == "requested-model"
    assert plan["blockers"]
    data["environment"]["model"] = "requested-model"
    assert module.create_plan(data)["ready_to_start"]
