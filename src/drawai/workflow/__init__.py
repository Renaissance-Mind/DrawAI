"""Lazy workflow exports keep optional execution dependencies out of Session setup."""
from importlib import import_module

_EXPORTS = {'AgentOutputDeclaration': 'agents', 'AgentPreset': 'agents', 'AgentPrompt': 'agents', 'AgentProviderSpec': 'agents', 'AgentScriptSpec': 'agents', 'agent_preset_by_id': 'agents', 'default_agent_provider_registry': 'agents', 'render_agent_prompt': 'agents', 'run0_agent_preset': 'agents', 'svg_agent_preset': 'agents', 'AgentExecutionError': 'agent_execution', 'AgentExecutionRequest': 'agent_execution', 'AgentExecutionResult': 'agent_execution', 'execute_agent_prompt': 'agent_execution', 'FormatSpec': 'formats', 'FormatValidationResult': 'formats', 'default_format_contract_descriptions': 'formats', 'default_format_registry': 'formats', 'validate_format_file': 'formats', 'NodeRunRecord': 'node_runs', 'begin_node_run': 'node_runs', 'finish_node_run_blocked': 'node_runs', 'finish_node_run_failed': 'node_runs', 'finish_node_run_ok': 'node_runs', 'mark_node_run_stale': 'node_runs', 'node_run_dir': 'node_runs', 'write_input_manifest': 'node_runs', 'NodeHandler': 'runner', 'NodeRunContext': 'runner', 'NodeRunSummary': 'runner', 'WorkflowRunner': 'runner', 'WorkflowRunResult': 'runner', 'WorkflowEdge': 'schema', 'WorkflowNode': 'schema', 'WorkflowPort': 'schema', 'WorkflowTemplate': 'schema', 'WorkflowValidationError': 'schema', 'WorkflowValidationResult': 'schema', 'DEFAULT_WORKFLOW_TEMPLATE_ID': 'templates', 'builtin_workflow_templates': 'templates', 'copy_builtin_template_to_workspace': 'templates', 'copy_builtin_template': 'templates', 'default_drawai_workflow_template': 'templates', 'list_workflow_templates': 'templates', 'load_workflow_template': 'templates', 'load_workflow_template_by_id': 'templates', 'save_workflow_template': 'templates', 'user_workflow_template_path': 'templates', 'workflow_template_from_dict': 'templates', 'workflow_templates_dir': 'templates', 'validate_workflow_template': 'validation'}
__all__ = list(_EXPORTS)

def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(name)
    value = getattr(import_module("." + _EXPORTS[name], __name__), name)
    globals()[name] = value
    return value
