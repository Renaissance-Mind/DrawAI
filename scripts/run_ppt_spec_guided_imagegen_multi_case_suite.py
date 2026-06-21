#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = REPO_ROOT / "scripts"
for path in (SRC_ROOT, SCRIPTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from drawai.codex_python_sdk_imagegen import (  # noqa: E402
    invoke_codex_python_sdk_image_edit,
    invoke_codex_python_sdk_imagegen,
)
from run_ppt_spec_guided_imagegen_showcase import (  # noqa: E402
    DEFAULT_REFERENCE_STYLE_SPEC,
    DEFAULT_SLOT_SCHEMA,
    DEFAULT_SOURCE_IMAGE,
    DEFAULT_TEMPLATE_ASSET,
    DEFAULT_TEMPLATE_SPEC,
    build_image_prompt,
    load_structured_inputs,
)


DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs" / "ppt_spec_guided_imagegen_multi_case_suite"


SUITE_CASES: list[dict[str, Any]] = [
    {
        "id": "a1_kb_agent_cover",
        "group_id": "A",
        "group_name": "企业知识库 AI Agent 落地方案",
        "deck_index": 1,
        "page_type": "cover",
        "operation": "generate",
        "source_mode": "source_grounded",
        "selected_layout_role": "cover",
        "template_style": "corporate_strategy_cinematic",
        "title": "企业知识库 AI Agent 落地方案",
        "subtitle": "从知识治理到可控上线的 4 页连续方案",
        "takeaway": "先限定高价值业务场景，再用权限、评测和灰度机制降低上线风险",
        "layout_intent": "Executive consulting cover. Strong Chinese title, subtitle, three capability badges, muted corporate palette, visible PPT margins.",
        "slots_to_use": ["slot_cover_title", "slot_cover_subtitle", "slot_metric_1", "slot_metric_2", "slot_metric_3"],
        "visible_text": {
            "title": "企业知识库 AI Agent 落地方案",
            "subtitle": "知识治理 · 检索增强 · 权限控制 · 灰度上线",
            "badges": ["场景选择", "可信回答", "上线闭环"],
            "footer": "Spec-guided PPT 图像生成测试",
        },
        "sources": [
            {
                "title": "项目访谈纪要",
                "evidence": "Agent should start from constrained internal knowledge workflows with measurable answer quality and permission boundaries.",
            }
        ],
        "claims": [
            "本页只表达方案结构，不展示未提供的 ROI、成本节省或准确率数字。",
            "企业知识库 Agent 的关键约束包括知识源治理、权限边界、答案可追溯和灰度发布。",
        ],
        "features": ["spec_guided", "source_grounded", "chinese_first", "multi_page_consistency"],
    },
    {
        "id": "a2_kb_agent_workflow_edit",
        "group_id": "A",
        "group_name": "企业知识库 AI Agent 落地方案",
        "deck_index": 2,
        "page_type": "process_flow",
        "operation": "edit",
        "source_mode": "source_grounded",
        "selected_layout_role": "process_or_timeline",
        "template_style": "prisma_flow_diagram",
        "title": "企业知识库 Agent 上线流程",
        "subtitle": "用 PRISMA 式筛选流程表达从需求到上线的治理链路",
        "takeaway": "LocalImageInput 参与生成：把参考图流程语法替换为企业知识库落地流程",
        "layout_intent": "Use the PRISMA reference image as layout/style reference: yellow top bars, white rectangular nodes, arrows, left stage labels.",
        "slots_to_use": ["slot_flow_title", "slot_flow_step_1", "slot_flow_step_2", "slot_flow_step_3", "slot_flow_step_4", "slot_flow_note"],
        "visible_text": {
            "headers": ["需求与知识治理", "验证与上线闭环"],
            "stage_labels": ["输入", "筛选", "构建", "评测", "上线"],
            "nodes": [
                "业务需求池：客服、运营、销售、研发知识问答",
                "知识源盘点：制度文档、FAQ、工单、培训材料",
                "权限过滤：部门、角色、密级、审计记录",
                "RAG 原型：检索、重排、回答、引用来源",
                "质量评测：命中率、幻觉样例、拒答边界",
                "灰度上线：小团队试点、反馈收集、版本回滚",
                "进入运营：监控问题、更新知识、复盘指标",
            ],
            "checks": ["不编造 ROI", "不复制原图数字", "检查 operation=edit"],
        },
        "sources": [
            {"title": "企业知识库上线要求", "evidence": "Pilot before full rollout; logs and permission controls are mandatory."}
        ],
        "claims": ["流程节点来自用户测试主题，不复制参考 PRISMA 原图的医学内容或数字。"],
        "workbench_request": True,
        "features": [
            "spec_guided",
            "reference_image_edit",
            "reference_roles",
            "source_grounded",
            "chinese_first",
            "multi_page_consistency",
            "workbench_reference_request",
        ],
    },
    {
        "id": "a3_kb_agent_evidence_data",
        "group_id": "A",
        "group_name": "企业知识库 AI Agent 落地方案",
        "deck_index": 3,
        "page_type": "data_evidence",
        "operation": "generate",
        "source_mode": "data_driven",
        "selected_layout_role": "data_page",
        "template_style": "economist_data_story",
        "title": "试点优先级：从价值与风险同时筛选",
        "subtitle": "示例数据只用于验证页面结构，不代表真实企业指标",
        "takeaway": "优先选择价值高、权限清晰、答案可追溯的场景进入试点",
        "layout_intent": "Data evidence slide with one chart/table area, three insight cards, and a visible source note.",
        "slots_to_use": ["slot_data_title", "native_table_capability_matrix", "native_chart_phase_coverage", "slot_data_caption"],
        "visible_text": {
            "title": "试点场景优先级",
            "labels": ["场景", "业务价值", "权限风险", "试点优先级", "示例数据"],
            "source_note": "仅使用给定示例数据；不代表真实企业平均值",
        },
        "data_sources": [
            {"scenario": "客服知识问答", "business_value": 5, "permission_risk": 2, "priority": 5},
            {"scenario": "销售资料助手", "business_value": 4, "permission_risk": 3, "priority": 4},
            {"scenario": "研发规范查询", "business_value": 3, "permission_risk": 2, "priority": 3},
            {"scenario": "人事制度问答", "business_value": 3, "permission_risk": 5, "priority": 2},
        ],
        "claims": [
            "图表只能表达 data_sources 中的四个场景和三个字段。",
            "不得生成未提供的 ROI、节省工时、准确率或行业平均数。",
        ],
        "features": ["spec_guided", "data_driven", "chinese_first", "multi_page_consistency"],
    },
    {
        "id": "a4_kb_agent_rollout",
        "group_id": "A",
        "group_name": "企业知识库 AI Agent 落地方案",
        "deck_index": 4,
        "page_type": "roadmap",
        "operation": "generate",
        "source_mode": "source_grounded",
        "selected_layout_role": "content",
        "template_style": "corporate_strategy_cinematic",
        "title": "90 天落地路线图",
        "subtitle": "从小范围试点到可运营能力",
        "takeaway": "每个阶段只扩大一个变量：场景、用户、知识源或自动化权限",
        "layout_intent": "Roadmap slide with four horizontal phases, decision gates, and risk controls. Keep same corporate visual language as previous pages.",
        "slots_to_use": ["slot_content_title", "slot_card_1", "slot_card_2", "slot_card_3", "slot_content_caption"],
        "visible_text": {
            "title": "90 天落地路线图",
            "phases": ["0-15 天：场景选择", "16-45 天：原型验证", "46-75 天：灰度上线", "76-90 天：运营复盘"],
            "gates": ["知识源确认", "权限审计", "质量评测", "上线回滚"],
            "footer": "扩围前必须通过质量与安全门槛",
        },
        "sources": [
            {"title": "试点推进原则", "evidence": "Roll out through staged gates; quality and permission checks precede expansion."}
        ],
        "claims": ["不得承诺固定上线收益；路线图是执行框架，不是结果保证。"],
        "features": ["spec_guided", "source_grounded", "chinese_first", "multi_page_consistency"],
    },
    {
        "id": "b1_medical_prisma_screening_edit",
        "group_id": "B",
        "group_name": "医学文献筛选 / 系统综述 PRISMA",
        "deck_index": 1,
        "page_type": "process_flow",
        "operation": "edit",
        "source_mode": "source_grounded",
        "selected_layout_role": "process_or_timeline",
        "template_style": "prisma_flow_diagram",
        "title": "系统综述文献筛选流程",
        "subtitle": "参考 PRISMA 布局，使用用户给定的中文筛选节点",
        "takeaway": "复用 PRISMA 视觉语法，但不复制参考图的研究数量和标签",
        "layout_intent": "A PRISMA-style systematic review flow page. Keep yellow top bars, white nodes, black arrows, left stage labels.",
        "slots_to_use": ["slot_flow_title", "slot_flow_step_1", "slot_flow_step_2", "slot_flow_step_3", "slot_flow_step_4"],
        "visible_text": {
            "headers": ["数据库检索", "筛选与纳入"],
            "stage_labels": ["识别", "去重", "初筛", "全文评估", "纳入"],
            "nodes": [
                "数据库记录：用户给定检索结果",
                "补充来源：引用追踪与专家推荐",
                "去重后记录：仅显示占位，不编造数量",
                "题名摘要筛选：排除不相关研究",
                "全文评估：排除不符合标准研究",
                "最终纳入：系统综述证据池",
            ],
            "checks": ["不编造篇数", "不复制原图研究标签", "中文阶段清晰"],
        },
        "sources": [
            {"title": "用户未提供具体检索数量", "evidence": "Do not invent counts; use placeholders or qualitative labels only."}
        ],
        "claims": ["不得编造文献数量、数据库名、纳入研究篇数或排除原因数字。"],
        "features": ["spec_guided", "reference_image_edit", "reference_roles", "source_grounded", "chinese_first"],
    },
    {
        "id": "b2_medical_prisma_summary_edit",
        "group_id": "B",
        "group_name": "医学文献筛选 / 系统综述 PRISMA",
        "deck_index": 2,
        "page_type": "summary",
        "operation": "edit",
        "source_mode": "source_grounded",
        "selected_layout_role": "process_or_timeline",
        "template_style": "prisma_flow_diagram",
        "title": "筛选流程质量控制",
        "subtitle": "把参考流程图改造成质量检查清单",
        "takeaway": "将 content_reference 限定为流程语法，不继承原图事实",
        "layout_intent": "Use the PRISMA reference as a quality-control summary map with five stages and side check boxes.",
        "slots_to_use": ["layout_reference", "style_reference", "color_reference", "typography_reference", "content_reference"],
        "visible_text": {
            "headers": ["质量控制节点", "审查记录"],
            "stage_labels": ["检索式", "去重", "双人筛选", "全文评估", "证据表"],
            "nodes": [
                "检索式锁定：数据库、日期、关键词",
                "去重规则：标题、作者、年份、DOI",
                "双人筛选：分歧记录与第三方裁决",
                "全文评估：纳入/排除标准逐条记录",
                "证据表：样本、干预、结局、偏倚风险",
            ],
            "checks": ["不编造数量", "不复制原图内容", "保留流程图语法"],
        },
        "claims": ["本页是质量控制结构，不展示未提供的研究统计。"],
        "features": ["spec_guided", "reference_image_edit", "reference_roles", "source_grounded", "chinese_first"],
    },
    {
        "id": "c1_ev_sales_funnel_data",
        "group_id": "C",
        "group_name": "新能源车销售漏斗数据复盘",
        "deck_index": 1,
        "page_type": "data_evidence",
        "operation": "generate",
        "source_mode": "data_driven",
        "selected_layout_role": "data_page",
        "template_style": "infographic_dashboard",
        "title": "新能源车销售漏斗复盘",
        "subtitle": "只用给定漏斗数据，不生成额外销量或转化率",
        "takeaway": "试驾到下订是主要流失段，下一步应验证门店跟进与金融方案匹配",
        "layout_intent": "Dashboard slide with a funnel chart, conversion callouts, and right-side action notes.",
        "slots_to_use": ["slot_data_title", "native_table_capability_matrix", "native_chart_phase_coverage", "slot_data_caption"],
        "visible_text": {
            "title": "销售漏斗复盘",
            "labels": ["线索", "到店", "试驾", "报价", "下订", "给定数据"],
            "source_note": "数据为用户提供的测试样例",
        },
        "data_sources": [
            {"stage": "线索", "count": 1200},
            {"stage": "到店", "count": 420},
            {"stage": "试驾", "count": 260},
            {"stage": "报价", "count": 140},
            {"stage": "下订", "count": 68},
        ],
        "claims": [
            "漏斗图只能使用 data_sources 中的五个阶段和 count。",
            "不得补充品牌销量、市场份额、客单价或真实转化率来源。",
        ],
        "features": ["spec_guided", "data_driven", "chinese_first"],
    },
    {
        "id": "c2_ev_sales_strategy",
        "group_id": "C",
        "group_name": "新能源车销售漏斗数据复盘",
        "deck_index": 2,
        "page_type": "comparison",
        "operation": "generate",
        "source_mode": "source_grounded",
        "selected_layout_role": "content",
        "template_style": "annual_report",
        "title": "销售策略调整建议",
        "subtitle": "围绕试驾后流失做三类动作",
        "takeaway": "先提升跟进节奏和金融方案解释，再做渠道扩量",
        "layout_intent": "Business strategy slide with three action columns and one risk guardrail row.",
        "slots_to_use": ["slot_content_title", "slot_card_1", "slot_card_2", "slot_card_3", "slot_content_caption"],
        "visible_text": {
            "title": "销售策略调整建议",
            "columns": ["试驾后跟进", "金融方案解释", "竞品异议处理"],
            "actions": ["24 小时回访", "月供/置换方案可视化", "常见异议话术库"],
            "guardrail": "不得把测试漏斗数据外推为全国市场结论",
        },
        "sources": [
            {"title": "销售复盘输入", "evidence": "Largest observed drop is from test drive to quote/order in the provided sample funnel."}
        ],
        "claims": ["策略只基于给定漏斗样例，不代表真实品牌表现。"],
        "features": ["spec_guided", "source_grounded", "chinese_first"],
    },
    {
        "id": "d1_ai_safety_blue_robot",
        "group_id": "D",
        "group_name": "儿童 AI 安全课件",
        "deck_index": 1,
        "page_type": "courseware",
        "operation": "generate",
        "source_mode": "prompt_only",
        "selected_layout_role": "content",
        "template_style": "blue_robot_learning",
        "title": "和 AI 助手安全聊天",
        "subtitle": "原创蓝白圆润机器人学习风，不复刻任何受保护角色",
        "takeaway": "遇到隐私、陌生链接和奇怪要求时，先停下来问老师或家长",
        "layout_intent": "Child-friendly learning PPT slide with original blue-white rounded robot teacher, classroom panels, and clear Chinese teaching cards.",
        "slots_to_use": ["slot_content_title", "slot_card_1", "slot_card_2", "slot_card_3"],
        "visible_text": {
            "title": "和 AI 助手安全聊天",
            "rules": ["不说家庭住址", "不点陌生链接", "不上传证件照片", "不单独见网友"],
            "teacher_note": "有疑问，先问大人",
        },
        "ip_safety": {
            "must_be_original": True,
            "avoid": [
                "不要生成哆啦A梦本体",
                "不要复刻受版权保护角色",
                "不要铃铛、魔法口袋、相同脸部比例或商标符号",
            ],
        },
        "claims": ["这是原创蓝白机器人学习风，不是任何现有 IP。"],
        "features": ["spec_guided", "chinese_first", "safe_ip_cartoon"],
    },
    {
        "id": "d2_ai_safety_manga_cards",
        "group_id": "D",
        "group_name": "儿童 AI 安全课件",
        "deck_index": 2,
        "page_type": "courseware_summary",
        "operation": "generate",
        "source_mode": "prompt_only",
        "selected_layout_role": "content",
        "template_style": "manga_safe_learning",
        "title": "AI 安全小测验",
        "subtitle": "漫画分镜式学习卡，不使用任何已知动漫角色",
        "takeaway": "用选择题检查孩子是否理解隐私、来源和求助规则",
        "layout_intent": "Original manga-inspired classroom cards with four quiz panels, large readable Chinese text, and no protected character likeness.",
        "slots_to_use": ["slot_content_title", "slot_card_1", "slot_card_2", "slot_card_3", "slot_content_caption"],
        "visible_text": {
            "title": "AI 安全小测验",
            "questions": ["能告诉 AI 家庭住址吗？", "陌生链接能点吗？", "AI 说得都是真的吗？", "害怕时找谁帮忙？"],
            "answers": ["不能", "不能", "要核对", "老师或家长"],
        },
        "ip_safety": {
            "must_be_original": True,
            "avoid": ["不复刻受保护动漫角色", "不使用商标符号", "不模仿现有角色服装和脸型"],
        },
        "features": ["spec_guided", "chinese_first", "safe_ip_cartoon"],
    },
    {
        "id": "e1_product_launch_pitch",
        "group_id": "E",
        "group_name": "投资人路演 / 产品发布",
        "deck_index": 1,
        "page_type": "pitch",
        "operation": "generate",
        "source_mode": "source_grounded",
        "selected_layout_role": "cover",
        "template_style": "aurora_ui",
        "title": "AI 工作台产品发布",
        "subtitle": "把多模态输入、工具执行和结果审查放进一个协作界面",
        "takeaway": "产品价值来自可追溯工作流，而不是单次生成结果",
        "layout_intent": "Premium product-launch/pitch slide with aurora UI mood, large title, product capability tiles, and concise investor-facing structure.",
        "slots_to_use": ["slot_cover_title", "slot_cover_subtitle", "slot_metric_1", "slot_metric_2", "slot_metric_3"],
        "visible_text": {
            "title": "AI 工作台产品发布",
            "subtitle": "多模态输入 · 工具执行 · 审查闭环",
            "tiles": ["统一入口", "可追溯记录", "人工接管"],
        },
        "sources": [
            {"title": "产品定位输入", "evidence": "The product focuses on traceable workflows and human review rather than one-shot generation."}
        ],
        "claims": ["不得编造融资金额、客户数量或市场规模。"],
        "features": ["spec_guided", "source_grounded", "chinese_first"],
    },
    {
        "id": "x1_template_vs_prompt_only_contrast",
        "group_id": "X",
        "group_name": "模板约束对比",
        "deck_index": 1,
        "page_type": "comparison",
        "operation": "generate",
        "source_mode": "source_grounded",
        "selected_layout_role": "content",
        "template_style": "spec_guided_contrast",
        "title": "为什么不是 Prompt-only",
        "subtitle": "同样是 PPT 图像生成，结构化输入决定页面稳定性",
        "takeaway": "Spec-guided 把模板结构、槽位、设计 token 和参考图角色显式注入生成",
        "layout_intent": "Two-column comparison slide: Prompt-only vs Spec-guided. Show structure, facts, style, reference image, and output records.",
        "slots_to_use": ["slot_content_title", "slot_card_1", "slot_card_2", "slot_card_3", "slot_content_caption"],
        "visible_text": {
            "title": "Prompt-only vs Spec-guided",
            "left_header": "Prompt-only",
            "right_header": "Spec-guided",
            "left_points": ["风格容易漂移", "布局靠模型猜", "参考图只被文字描述"],
            "right_points": ["slot_schema 锁定结构", "design_tokens 锁定视觉", "LocalImageInput 真实参与"],
            "bottom": "当前目标：先生成高质量 PPT 图像，再进入 DrawAI 可编辑重建",
        },
        "claims": ["本页是能力对比示意，不展示真实评测分数。"],
        "features": ["spec_guided", "template_vs_prompt_only", "chinese_first"],
    },
]


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve(strict=False)
    if args.force and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source_image = args.source_image.expanduser().resolve(strict=False)
    if not source_image.is_file():
        raise FileNotFoundError(f"reference source image does not exist: {source_image}")
    source_copy = output_dir / "source_reference.jpg"
    shutil.copy2(source_image, source_copy)

    inputs = load_structured_inputs(
        template_spec_path=args.template_spec,
        slot_schema_path=args.slot_schema,
        reference_style_spec_path=args.reference_style_spec,
        template_asset_path=args.template_asset,
    )
    runtime_config: dict[str, Any] = {"timeout_seconds": args.timeout_seconds, "reasoning_effort": args.reasoning_effort}
    if args.model:
        runtime_config["model_name"] = args.model

    selected_cases = _select_cases(args)
    started_at = time.time()
    report: dict[str, Any] = {
        "schema": "drawai.ppt_spec_guided_imagegen_multi_case_suite.summary.v1",
        "status": "running",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "output_dir": str(output_dir),
        "contact_sheet": "",
        "statement": {
            "delivery": "PPT slide images as PNG/contact sheets, not PPTX output.",
            "ppt_master_usage": "PPT-master is used only as an idea: template/spec/slot/design lock for image generation.",
            "not_prompt_only": "Every payload includes template_spec, slot_schema, design_tokens, spec_lock, and reference roles.",
        },
        "input_assets": _input_asset_paths(args, source_copy=source_copy),
        "case_count": len(selected_cases),
        "cases": [],
        "feature_matrix": {},
    }
    _write_json(output_dir / "summary.json", report)

    blocked_reason = ""
    for case in selected_cases:
        case_dir = output_dir / f"{case['group_id']}{case['deck_index']:02d}_{case['id']}"
        record = None if args.force else _load_existing_record(case_dir)
        if record and _first_image_path(record):
            pass
        else:
            record = write_prompt_record(
                case,
                case_dir=case_dir,
                inputs=inputs,
                source_copy=source_copy,
                original_source_image=source_image,
            )
            if not args.prompt_only and not blocked_reason:
                try:
                    record = run_case(case, case_dir=case_dir, runtime_config=runtime_config, source_copy=source_copy, original_source_image=source_image)
                except Exception as exc:  # noqa: BLE001 - preserve prompt artifacts on live blocker.
                    blocked_reason = repr(exc)
                    record["status"] = "blocked"
                    record["blocked_reason"] = blocked_reason
                    _write_json(case_dir / "record.json", record)
            elif blocked_reason:
                record["status"] = "prompt_only"
                record["blocked_reason"] = blocked_reason
                _write_json(case_dir / "record.json", record)
        records = _load_all_records(output_dir)
        _write_topic_contact_sheets(output_dir, records)
        report.update(_build_report(args=args, output_dir=output_dir, records=records, blocked_reason=blocked_reason, started_at=started_at))
        _write_json(output_dir / "summary.json", report)

    records = _load_all_records(output_dir)
    if any(_first_image_path(record) for record in records):
        report["contact_sheet"] = str(_write_grouped_contact_sheet(output_dir, records))
    report.update(_build_report(args=args, output_dir=output_dir, records=records, blocked_reason=blocked_reason, started_at=started_at))
    _write_json(output_dir / "summary.json", report)
    _write_summary_md(output_dir, report)
    print(json.dumps(_compact_summary(report), ensure_ascii=False, indent=2))
    return 2 if blocked_reason and not any(case.get("status") == "ok" for case in report["cases"]) else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a multi-case PPT spec-guided imagegen suite.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--template-spec", type=Path, default=DEFAULT_TEMPLATE_SPEC)
    parser.add_argument("--slot-schema", type=Path, default=DEFAULT_SLOT_SCHEMA)
    parser.add_argument("--reference-style-spec", type=Path, default=DEFAULT_REFERENCE_STYLE_SPEC)
    parser.add_argument("--template-asset", type=Path, default=DEFAULT_TEMPLATE_ASSET)
    parser.add_argument("--source-image", type=Path, default=DEFAULT_SOURCE_IMAGE)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--group", default="", help="Optional group id filter such as A, B, C, D, E, X.")
    parser.add_argument("--model", default="")
    parser.add_argument("--reasoning-effort", default="low", choices=["none", "minimal", "low", "medium", "high", "xhigh"])
    parser.add_argument("--timeout-seconds", type=float, default=720.0)
    parser.add_argument("--prompt-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def build_case_payload(
    case: Mapping[str, Any],
    *,
    inputs: Mapping[str, Any],
    source_copy: Path,
    original_source_image: Path,
) -> dict[str, Any]:
    template_spec = inputs["template_spec"]
    slot_schema = inputs["slot_schema"]
    reference_style_spec = inputs["reference_style_spec"]
    template_asset = inputs["template_asset"]
    selected_layout = _select_layout(template_spec, str(case["selected_layout_role"]))
    selected_slots = _select_slots(slot_schema, case.get("slots_to_use") or [], selected_layout.get("slide_index"))
    operation = str(case["operation"])
    payload = {
        "schema": "drawai.ppt_spec_guided_imagegen.multi_case_payload.v1",
        "provider": "codex",
        "operation": operation,
        "page_type": case["page_type"],
        "case_id": case["id"],
        "group_id": case["group_id"],
        "group_name": case["group_name"],
        "deck_index": case["deck_index"],
        "template_style": case["template_style"],
        "source_mode": case["source_mode"],
        "output_format": "png",
        "size": "2048x1152",
        "quality": "high",
        "rendering_mode": "baked_text",
        "source_image_path": str(source_copy) if operation == "edit" else "",
        "reference_image_path": str(source_copy) if operation == "edit" else "",
        "reference_image_paths": [str(source_copy)] if operation == "edit" else [],
        "original_source_image_path": str(original_source_image) if operation == "edit" else "",
        "uses_local_image_input": operation == "edit",
        "workbench_request": _workbench_request(case, source_copy=source_copy) if case.get("workbench_request") else {},
        "input_assets": {
            "template_spec_path": inputs["template_spec_path"],
            "slot_schema_path": inputs["slot_schema_path"],
            "reference_style_spec_path": inputs["reference_style_spec_path"],
            "template_asset_path": inputs["template_asset_path"],
            "source_reference_path": str(source_copy),
        },
        "from_template_spec": {
            "schema": template_spec.get("schema"),
            "source_pptx": template_spec.get("source_pptx"),
            "slide_size": template_spec.get("slide_size", {}),
            "selected_layout": selected_layout,
            "design_tokens": template_spec.get("design_tokens", {}),
            "spec_lock": template_spec.get("spec_lock", {}),
        },
        "from_slot_schema": {
            "selected_slots": selected_slots,
            "slot_policy": {
                "use_slot_geometry_as_layout_hint": True,
                "keep_text_inside_slot_regions": True,
                "respect_page_type": case["page_type"],
                "keep_group_consistency": case["group_id"] in {"A", "B", "C", "D"},
            },
        },
        "from_reference_style_spec": {
            "schema": reference_style_spec.get("schema"),
            "source_image_path": reference_style_spec.get("source_image_path"),
            "reference_roles": _reference_roles(reference_style_spec),
            "design_tokens": reference_style_spec.get("design_tokens", {}),
            "spec_lock": reference_style_spec.get("spec_lock", {}),
        },
        "from_template_asset": {
            "id": template_asset.get("id"),
            "design_tokens": template_asset.get("design_tokens", {}),
            "layout": template_asset.get("layout", {}),
            "slot_schema": template_asset.get("slot_schema", {}),
            "reference_roles": template_asset.get("reference_roles", []),
        },
        "from_user_page_goal": {
            "title": case["title"],
            "subtitle": case["subtitle"],
            "takeaway": case["takeaway"],
            "layout_intent": case["layout_intent"],
            "visible_text": case["visible_text"],
            "sources": case.get("sources", []),
            "claims": case.get("claims", []),
            "data_sources": case.get("data_sources", []),
            "ip_safety": case.get("ip_safety", {}),
        },
        "quality_gates": {
            "must_be_ppt_slide_image": True,
            "must_not_output_pptx": True,
            "chinese_first_visible_text": "chinese_first" in case.get("features", []),
            "avoid_random_english": True,
            "avoid_fake_numbers_or_sources": bool(case.get("claims") or case.get("sources") or case.get("data_sources")),
            "chart_uses_only_given_data": bool(case.get("data_sources")),
            "safe_ip_no_protected_character": "safe_ip_cartoon" in case.get("features", []),
            "keep_16_9_slide_composition": True,
            "for_edit_cases_use_local_image_input": operation == "edit",
        },
        "features": list(case.get("features", [])),
    }
    payload["prompt"] = build_image_prompt(payload)
    return payload


def write_prompt_record(
    case: Mapping[str, Any],
    *,
    case_dir: Path,
    inputs: Mapping[str, Any],
    source_copy: Path,
    original_source_image: Path,
) -> dict[str, Any]:
    case_dir.mkdir(parents=True, exist_ok=True)
    payload = build_case_payload(case, inputs=inputs, source_copy=source_copy, original_source_image=original_source_image)
    _write_json(case_dir / "payload.json", payload)
    (case_dir / "prompt.txt").write_text(str(payload["prompt"]) + "\n", encoding="utf-8")
    record = {
        "schema": "drawai.ppt_spec_guided_imagegen.multi_case_record.v1",
        "case_id": case["id"],
        "group_id": case["group_id"],
        "group_name": case["group_name"],
        "deck_index": case["deck_index"],
        "page_type": case["page_type"],
        "template_style": case["template_style"],
        "source_mode": case["source_mode"],
        "operation": case["operation"],
        "status": "prompt_only",
        "case_dir": str(case_dir),
        "payload_path": str(case_dir / "payload.json"),
        "prompt_path": str(case_dir / "prompt.txt"),
        "record_path": str(case_dir / "record.json"),
        "image_path": "",
        "source_image_path": payload.get("source_image_path", ""),
        "reference_image_path": payload.get("reference_image_path", ""),
        "original_source_image_path": payload.get("original_source_image_path", ""),
        "uses_local_image_input": bool(payload.get("uses_local_image_input")),
        "features": list(case.get("features", [])),
        "slots_used": [slot.get("slot_id") or slot.get("name") or slot.get("table_id") or slot.get("chart_id") for slot in payload["from_slot_schema"]["selected_slots"]],
        "reference_roles_used": [role.get("role") for role in payload["from_reference_style_spec"]["reference_roles"]],
        "generation": None,
        "quality_notes": [],
    }
    _write_json(case_dir / "record.json", record)
    return record


def run_case(
    case: Mapping[str, Any],
    *,
    case_dir: Path,
    runtime_config: Mapping[str, Any],
    source_copy: Path,
    original_source_image: Path,
) -> dict[str, Any]:
    record = _load_existing_record(case_dir)
    if record is None:
        raise RuntimeError(f"missing prompt record: {case_dir}")
    prompt = (case_dir / "prompt.txt").read_text(encoding="utf-8")
    if case["operation"] == "edit":
        result = invoke_codex_python_sdk_image_edit(
            source_image_path=source_copy,
            prompt=prompt,
            output_dir=case_dir / "generated",
            task_name="drawai.experiment.ppt_spec_guided_multi_case.edit.v1",
            output_stem=str(case["id"]),
            runtime_config=runtime_config,
            trace_path=case_dir / "trace.jsonl",
            isolated_cwd=case_dir / "codex_cwd",
        )
    else:
        result = invoke_codex_python_sdk_imagegen(
            prompt=prompt,
            output_dir=case_dir / "generated",
            task_name="drawai.experiment.ppt_spec_guided_multi_case.generate.v1",
            output_stem=str(case["id"]),
            runtime_config=runtime_config,
            trace_path=case_dir / "trace.jsonl",
            isolated_cwd=case_dir / "codex_cwd",
        )
    first = result.images[0] if result.images else None
    if first is None:
        raise RuntimeError(f"{case['id']} returned no image")
    image_path = _copy_png(Path(first.path), case_dir / f"{case['id']}.png")
    record.update(
        {
            "status": "ok",
            "image_path": str(image_path),
            "operation": result.operation,
            "source_image_path": str(result.source_image_path) if result.source_image_path else "",
            "reference_image_path": str(result.source_image_path) if result.source_image_path else "",
            "original_source_image_path": str(original_source_image) if case["operation"] == "edit" else "",
            "uses_local_image_input": case["operation"] == "edit",
            "generation": result.to_dict(),
            "quality_notes": _basic_image_notes(image_path),
        }
    )
    _write_json(case_dir / "record.json", record)
    return record


def _select_cases(args: argparse.Namespace) -> list[dict[str, Any]]:
    cases = [case for case in SUITE_CASES if not args.group or case["group_id"].lower() == args.group.lower()]
    if args.limit:
        cases = cases[: args.limit]
    return cases


def _select_layout(template_spec: Mapping[str, Any], role: str) -> dict[str, Any]:
    layouts = [dict(item) for item in template_spec.get("layouts", [])]
    for layout in layouts:
        if layout.get("role_guess") == role:
            return {
                "id": layout.get("id"),
                "name": layout.get("name"),
                "slide_index": layout.get("slide_index"),
                "role_guess": layout.get("role_guess"),
                "slot_summary": layout.get("slot_summary", {}),
            }
    first = layouts[0] if layouts else {}
    return {
        "id": first.get("id", ""),
        "name": first.get("name", ""),
        "slide_index": first.get("slide_index"),
        "role_guess": first.get("role_guess", ""),
        "slot_summary": first.get("slot_summary", {}),
    }


def _select_slots(slot_schema: Mapping[str, Any], requested: list[str], slide_index: int | None) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for layout in slot_schema.get("layouts", []):
        if slide_index is None or layout.get("slide_index") == slide_index:
            candidates.extend(dict(slot) for slot in layout.get("slots", []))
            candidates.extend(dict(table) | {"kind": "table"} for table in layout.get("tables", []))
            candidates.extend(dict(chart) | {"kind": "chart"} for chart in layout.get("charts", []))
    selected: list[dict[str, Any]] = []
    for key in requested:
        key_lower = str(key).lower()
        for slot in candidates:
            slot_text = " ".join(str(slot.get(field, "")) for field in ("slot_id", "name", "table_id", "chart_id", "role", "kind")).lower()
            if key_lower in slot_text and slot not in selected:
                selected.append(slot)
                break
    return (selected or candidates)[:10]


def _reference_roles(reference_style_spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "role": item.get("role"),
            "weight": item.get("weight"),
            "locked_features": item.get("locked_features", []),
            "forbidden_copy": item.get("forbidden_copy", []),
        }
        for item in reference_style_spec.get("reference_roles", [])
    ]


def _workbench_request(case: Mapping[str, Any], *, source_copy: Path) -> dict[str, Any]:
    return {
        "provider": "codex",
        "prompt": case["title"],
        "source_image_path": str(source_copy),
        "reference_image_path": str(source_copy),
        "reference_image_paths": [str(source_copy)],
        "template_id": case.get("template_style", ""),
        "source_mode": case.get("source_mode", ""),
        "language": "zh",
        "rendering_mode": "baked_text",
    }


def _build_report(
    *,
    args: argparse.Namespace,
    output_dir: Path,
    records: list[dict[str, Any]],
    blocked_reason: str,
    started_at: float,
) -> dict[str, Any]:
    return {
        "status": "blocked" if blocked_reason else "ok",
        "blocked_reason": blocked_reason,
        "elapsed_seconds": round(time.time() - started_at, 3),
        "cases": [_case_summary(record) for record in records],
        "case_count": len(records),
        "feature_matrix": build_feature_matrix(records),
        "topic_contact_sheets": _topic_contact_sheet_paths(output_dir, records),
        "quality_review": _quality_review(records),
        "input_assets": _input_asset_paths(args, source_copy=output_dir / "source_reference.jpg"),
    }


def build_feature_matrix(records: list[Mapping[str, Any]]) -> dict[str, list[str]]:
    matrix: dict[str, list[str]] = {
        "spec_guided": [],
        "reference_image_edit": [],
        "reference_roles": [],
        "source_grounded": [],
        "data_driven": [],
        "chinese_first": [],
        "multi_page_consistency": [],
        "template_vs_prompt_only": [],
        "safe_ip_cartoon": [],
        "workbench_reference_request": [],
    }
    for record in records:
        case_id = str(record.get("case_id", ""))
        features = set(record.get("features", []))
        for feature in matrix:
            if feature in features:
                matrix[feature].append(case_id)
        if record.get("uses_local_image_input") and case_id not in matrix["reference_image_edit"]:
            matrix["reference_image_edit"].append(case_id)
        if record.get("reference_roles_used") and case_id not in matrix["reference_roles"]:
            matrix["reference_roles"].append(case_id)
    return matrix


def _case_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "case_id": record.get("case_id"),
        "group_id": record.get("group_id"),
        "group_name": record.get("group_name"),
        "deck_index": record.get("deck_index"),
        "page_type": record.get("page_type"),
        "template_style": record.get("template_style"),
        "source_mode": record.get("source_mode"),
        "operation": record.get("operation"),
        "status": record.get("status"),
        "image_path": record.get("image_path", ""),
        "payload_path": record.get("payload_path", ""),
        "prompt_path": record.get("prompt_path", ""),
        "record_path": record.get("record_path", ""),
        "source_image_path": record.get("source_image_path", ""),
        "reference_image_path": record.get("reference_image_path", ""),
        "uses_local_image_input": record.get("uses_local_image_input", False),
        "features": record.get("features", []),
        "slots_used": record.get("slots_used", []),
        "reference_roles_used": record.get("reference_roles_used", []),
        "quality_notes": record.get("quality_notes", []),
        "blocked_reason": record.get("blocked_reason", ""),
    }


def _quality_review(records: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [record for record in records if record.get("status") == "ok"]
    edits = [record for record in ok if record.get("operation") == "edit"]
    return {
        "script_check": {
            "png_count": len(ok),
            "edit_png_count": len(edits),
            "all_ok_have_png": all(_first_image_path(record) is not None for record in ok),
            "edit_records_use_local_image_input": all(record.get("uses_local_image_input") for record in edits),
        },
        "manual_review_targets": [
            "总 contact sheet 是否有 PPT 页面感",
            "A 组 4 页是否像连续 deck",
            "B 组 edit 页是否明显参考 PRISMA 图",
            "C 组 data-driven 页是否只呈现给定数据",
            "D 组卡通页是否 IP 安全且中文可读",
        ],
    }


def _write_topic_contact_sheets(output_dir: Path, records: list[dict[str, Any]]) -> None:
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        if _first_image_path(record) is None:
            continue
        groups.setdefault(str(record.get("group_id", "")), []).append(record)
    for group_id, group_records in groups.items():
        group_records.sort(key=lambda item: int(item.get("deck_index") or 0))
        _write_contact_sheet(output_dir / f"group_{group_id}_topic_contact_sheet.jpg", group_records, title=group_records[0].get("group_name", group_id))


def _write_grouped_contact_sheet(output_dir: Path, records: list[dict[str, Any]]) -> Path:
    Image, ImageDraw, _ = _pil()
    records = [record for record in records if _first_image_path(record) is not None]
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault(str(record.get("group_id", "")), []).append(record)
    thumb_w = 500
    thumb_h = 281
    margin = 22
    label_h = 56
    group_h = 48
    cols = 2
    rows_total = 0
    for group_records in groups.values():
        rows_total += 1 + (len(group_records) + cols - 1) // cols
    width = margin * (cols + 1) + cols * thumb_w
    height = margin + rows_total * (thumb_h + label_h + margin) + len(groups) * group_h
    sheet = Image.new("RGB", (width, height), (246, 247, 249))
    draw = ImageDraw.Draw(sheet)
    y = margin
    for group_id in sorted(groups):
        group_records = sorted(groups[group_id], key=lambda item: int(item.get("deck_index") or 0))
        group_name = str(group_records[0].get("group_name") or group_id)
        draw.rounded_rectangle((margin, y, width - margin, y + group_h), radius=10, fill=(15, 23, 42))
        draw.text((margin + 18, y + 11), f"{group_id}. {group_name}", fill=(255, 255, 255), font=_font(22))
        y += group_h + margin
        for index, record in enumerate(group_records):
            row = index // cols
            col = index % cols
            x = margin + col * (thumb_w + margin)
            tile_y = y + row * (thumb_h + label_h + margin)
            _draw_record_tile(sheet, record, x=x, y=tile_y, width=thumb_w, height=thumb_h, label_h=label_h)
        y += ((len(group_records) + cols - 1) // cols) * (thumb_h + label_h + margin)
    path = output_dir / "contact_sheet.jpg"
    sheet.save(path, quality=92)
    return path


def _write_contact_sheet(path: Path, records: list[dict[str, Any]], *, title: str) -> Path:
    Image, ImageDraw, _ = _pil()
    records = [record for record in records if _first_image_path(record) is not None]
    thumb_w = 620
    thumb_h = 349
    label_h = 62
    margin = 20
    cols = 2
    rows = (len(records) + cols - 1) // cols
    width = margin * (cols + 1) + cols * thumb_w
    height = margin * 2 + 54 + rows * (label_h + thumb_h + margin)
    sheet = Image.new("RGB", (width, height), (246, 247, 249))
    draw = ImageDraw.Draw(sheet)
    draw.text((margin, margin), title, fill=(15, 23, 42), font=_font(26))
    y0 = margin + 54
    for index, record in enumerate(records):
        row = index // cols
        col = index % cols
        x = margin + col * (thumb_w + margin)
        y = y0 + row * (label_h + thumb_h + margin)
        _draw_record_tile(sheet, record, x=x, y=y, width=thumb_w, height=thumb_h, label_h=label_h)
    sheet.save(path, quality=92)
    return path


def _draw_record_tile(sheet: Any, record: Mapping[str, Any], *, x: int, y: int, width: int, height: int, label_h: int) -> None:
    Image, ImageDraw, _ = _pil()
    draw = ImageDraw.Draw(sheet)
    op = "LocalImageInput/edit" if record.get("uses_local_image_input") else "spec-guided generate"
    draw.text((x, y), f"{record.get('deck_index')}. {record.get('page_type')} / {record.get('case_id')}", fill=(15, 23, 42), font=_font(17))
    draw.text((x, y + 24), f"{record.get('template_style')} · {op}", fill=(37, 99, 235), font=_font(13))
    thumb_y = y + label_h
    draw.rounded_rectangle((x, thumb_y, x + width, thumb_y + height), radius=8, fill=(226, 232, 240), outline=(203, 213, 225))
    path = _first_image_path(record)
    if path is None:
        draw.text((x + 20, thumb_y + 20), "missing image", fill=(148, 27, 27), font=_font(18))
        return
    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        sheet.paste(image, (x + (width - image.width) // 2, thumb_y + (height - image.height) // 2))


def _topic_contact_sheet_paths(output_dir: Path, records: list[Mapping[str, Any]]) -> dict[str, str]:
    paths: dict[str, str] = {}
    for record in records:
        group_id = str(record.get("group_id", ""))
        path = output_dir / f"group_{group_id}_topic_contact_sheet.jpg"
        if path.is_file():
            paths[group_id] = str(path)
    return paths


def _write_summary_md(output_dir: Path, report: Mapping[str, Any]) -> None:
    lines = [
        "# PPT Spec-guided Imagegen Multi-case Suite",
        "",
        "本轮交付是 PPT 图像 PNG/contact sheet，不是 PPTX。PPT-master 只用于 template/spec/slot/design lock 思想，所有 payload 都包含 template_spec、slot_schema、design_tokens、spec_lock 和 reference roles。",
        "",
        f"- Status: {report.get('status')}",
        f"- Output dir: `{report.get('output_dir')}`",
        f"- Contact sheet: `{report.get('contact_sheet', '')}`",
        "",
        "## Topic Contact Sheets",
    ]
    for group_id, path in sorted((report.get("topic_contact_sheets") or {}).items()):
        lines.append(f"- {group_id}: `{path}`")
    lines.extend(
        [
            "",
            "## Cases",
            "| Group | Case | Page type | Operation | Source mode | Image | Features |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for case in report.get("cases", []):
        lines.append(
            "| {group} | {case_id} | {page_type} | {operation} | {source_mode} | `{image}` | {features} |".format(
                group=case.get("group_id", ""),
                case_id=case.get("case_id", ""),
                page_type=case.get("page_type", ""),
                operation=case.get("operation", ""),
                source_mode=case.get("source_mode", ""),
                image=case.get("image_path", ""),
                features=", ".join(case.get("features", [])),
            )
        )
    lines.extend(["", "## Feature Matrix"])
    for feature, cases in (report.get("feature_matrix") or {}).items():
        lines.append(f"- `{feature}`: {', '.join(cases)}")
    lines.extend(
        [
            "",
            "## Quality Review Targets",
            "- 总 contact sheet 是否有 PPT 页面感。",
            "- A 组 4 页是否像连续 deck。",
            "- B 组 edit 页是否明显参考 PRISMA 图。",
            "- C 组 data-driven 页是否只表达给定数据。",
            "- D 组卡通页是否 IP 安全且中文可读。",
        ]
    )
    if report.get("manual_contact_sheet_review"):
        lines.extend(["", "## Manual Review"])
        for key, value in report["manual_contact_sheet_review"].items():
            lines.append(f"- {key}: {value}")
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _input_asset_paths(args: argparse.Namespace, *, source_copy: Path) -> dict[str, str]:
    return {
        "template_spec_path": str(args.template_spec.resolve(strict=False)),
        "slot_schema_path": str(args.slot_schema.resolve(strict=False)),
        "reference_style_spec_path": str(args.reference_style_spec.resolve(strict=False)),
        "template_asset_path": str(args.template_asset.resolve(strict=False)),
        "source_reference_path": str(source_copy.resolve(strict=False)),
    }


def _load_all_records(output_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for case in SUITE_CASES:
        path = output_dir / f"{case['group_id']}{case['deck_index']:02d}_{case['id']}" / "record.json"
        record = _load_existing_record(path.parent)
        if record is not None:
            records.append(record)
    return records


def _load_existing_record(case_dir: Path) -> dict[str, Any] | None:
    path = case_dir / "record.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _copy_png(source: Path, target: Path) -> Path:
    Image, _, _ = _pil()
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".png":
        shutil.copy2(source, target)
        return target
    with Image.open(source) as image:
        image.save(target)
    return target


def _basic_image_notes(path: Path) -> list[str]:
    notes: list[str] = []
    if not path.is_file():
        return ["missing PNG"]
    Image, _, _ = _pil()
    with Image.open(path) as image:
        ratio = image.width / max(1, image.height)
        if image.width < 1200 or image.height < 675:
            notes.append(f"resolution below expected draft: {image.width}x{image.height}")
        if ratio < 1.55 or ratio > 1.9:
            notes.append(f"aspect ratio may not be 16:9: {image.width}x{image.height}")
    return notes


def _first_image_path(record: Mapping[str, Any]) -> Path | None:
    direct = Path(str(record.get("image_path") or ""))
    if direct.is_file():
        return direct
    generation = record.get("generation") or {}
    if isinstance(generation, Mapping):
        for image in generation.get("images", []):
            path = Path(str(image.get("path") or ""))
            if path.is_file():
                return path
    return None


def _compact_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status"),
        "output_dir": report.get("output_dir"),
        "contact_sheet": report.get("contact_sheet"),
        "case_count": report.get("case_count"),
        "ok_cases": sum(1 for case in report.get("cases", []) if case.get("status") == "ok"),
        "edit_cases": [case.get("case_id") for case in report.get("cases", []) if case.get("operation") == "edit"],
        "topic_contact_sheets": report.get("topic_contact_sheets"),
        "blocked_reason": report.get("blocked_reason", ""),
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _font(size: int) -> Any:
    _, _, ImageFont = _pil()
    for candidate in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/arial.ttf"):
        path = Path(candidate)
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _pil() -> tuple[Any, Any, Any]:
    from PIL import Image, ImageDraw, ImageFont

    return Image, ImageDraw, ImageFont


if __name__ == "__main__":
    raise SystemExit(main())
