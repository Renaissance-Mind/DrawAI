import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";
import ts from "../node_modules/typescript/lib/typescript.js";

const PREVIEW_OPTIONS = {
  nodeWidth: 128,
  nodeHeight: 50,
  columnGap: 46,
  rowGap: 66,
  nodeGap: 18,
  paddingX: 18,
  paddingY: 16
};

test("adjacent one-to-many edges share one short source fork", async () => {
  const { buildWorkflowPreviewLayout } = await loadLayoutModule();
  const layout = buildWorkflowPreviewLayout(imageToPptxTemplate(), PREVIEW_OPTIONS);
  const ocrEdge = edgeById(layout, "input_ocr_parse");
  const samEdge = edgeById(layout, "input_sam_parse");
  const ocrPoints = pathPoints(ocrEdge.d);
  const samPoints = pathPoints(samEdge.d);

  assert.deepEqual(ocrPoints[0], samPoints[0]);
  assert.deepEqual(ocrPoints[1], samPoints[1]);
});

test("adjacent many-to-one edges share one short target merge", async () => {
  const { buildWorkflowPreviewLayout } = await loadLayoutModule();
  const layout = buildWorkflowPreviewLayout(imageToPptxTemplate(), PREVIEW_OPTIONS);
  const ocrEdge = edgeById(layout, "ocr_parse_page_spec_fuse");
  const samEdge = edgeById(layout, "sam_parse_page_spec_fuse");
  const ocrPoints = pathPoints(ocrEdge.d);
  const samPoints = pathPoints(samEdge.d);

  assert.deepEqual(ocrPoints.at(-1), samPoints.at(-1));
  assert.deepEqual(ocrPoints.at(-2), samPoints.at(-2));
});

test("adjacent second-row flow remains a compact direct connection", async () => {
  const { buildWorkflowPreviewLayout } = await loadLayoutModule();
  const layout = buildWorkflowPreviewLayout(imageToPptxTemplate(), PREVIEW_OPTIONS);
  const edge = edgeById(layout, "asset_prepare_svg_compose");
  const points = pathPoints(edge.d);

  assert.equal(points.length, 2);
  assert.equal(points[0].y, points[1].y);
});

test("long-range shortcuts to lower rows leave bottom and enter target top", async () => {
  const { buildWorkflowPreviewLayout } = await loadLayoutModule();
  const layout = buildWorkflowPreviewLayout(imageToPptxTemplate(), PREVIEW_OPTIONS);
  const source = nodeById(layout, "input");
  const target = nodeById(layout, "svg_compose");
  const edge = edgeById(layout, "input_svg_compose");
  const points = pathPoints(edge.d);

  assert.equal(edge.start.y, source.y + source.height);
  assert.ok(edge.start.x > source.x && edge.start.x < source.x + source.width);
  assert.equal(edge.end.y, target.y);
  assert.ok(edge.end.x > target.x && edge.end.x < target.x + target.width);
  assert.ok(
    points.some((point) => point.y > source.y + source.height && point.y < target.y),
    `expected shortcut edge to use the gap between rows, got: ${edge.d}`
  );
});

test("long-range shortcuts in the same row gap use separate rails", async () => {
  const { buildWorkflowPreviewLayout } = await loadLayoutModule();
  const layout = buildWorkflowPreviewLayout(imageToPptxTemplate(), PREVIEW_OPTIONS);
  const railYs = corridorRailYs(layout, ["input_asset_prepare", "input_svg_compose"]);

  assert.equal(railYs.size, 2);
});

test("running edge animation only applies to edges entering the running node", async () => {
  const { dagRunEdgeState } = await loadTsModule("../src/workflowRunState.ts");

  assert.equal(dagRunEdgeState("done", "running"), "running");
  assert.equal(dagRunEdgeState("running", "waiting"), "waiting");
  assert.equal(dagRunEdgeState("done", "done"), "done");
});

async function loadLayoutModule() {
  layoutModulePromise ||= loadTsModule("../src/workflowPreviewLayout.ts");
  return layoutModulePromise;
}

let layoutModulePromise;

async function loadTsModule(relativePath) {
  const source = readFileSync(new URL(relativePath, import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2020
    }
  });
  const dir = mkdtempSync(join(tmpdir(), "drawai-workflow-layout-"));
  const modulePath = join(dir, `${relativePath.split("/").at(-1).replace(/\.ts$/, "")}.mjs`);
  writeFileSync(modulePath, outputText);
  return import(pathToFileURL(modulePath).href);
}

function imageToPptxTemplate() {
  const nodes = [
    node("input", "input"),
    node("sam_parse", "processor"),
    node("ocr_parse", "processor"),
    node("page_spec_fuse", "processor"),
    node("page_spec_refine", "agent"),
    node("asset_prepare", "processor"),
    node("svg_compose", "agent"),
    node("svg_to_ppt", "export"),
    node("output", "output")
  ];
  return {
    schema: "drawai.workflow_template.v1",
    template_id: "image_to_pptx",
    name: "Image-to-PPTX",
    description: "",
    version: 1,
    nodes,
    edges: [
      edge("input", "sam_parse"),
      edge("input", "ocr_parse"),
      edge("input", "page_spec_refine"),
      edge("input", "asset_prepare"),
      edge("input", "svg_compose"),
      edge("sam_parse", "page_spec_fuse"),
      edge("ocr_parse", "page_spec_fuse"),
      edge("page_spec_fuse", "page_spec_refine"),
      edge("page_spec_refine", "asset_prepare"),
      edge("asset_prepare", "svg_compose"),
      edge("svg_compose", "svg_to_ppt"),
      edge("asset_prepare", "svg_to_ppt"),
      edge("svg_compose", "output"),
      edge("svg_to_ppt", "output")
    ],
    defaults: {}
  };
}

function node(nodeId, nodeType) {
  return {
    node_id: nodeId,
    node_type: nodeType,
    title: nodeId,
    inputs: [port("in")],
    outputs: [port("out")],
    config: {},
    position: {},
    description: ""
  };
}

function port(portId) {
  return {
    port_id: portId,
    label: portId,
    types: ["image"],
    required: true,
    cardinality: "single",
    formats: [],
    description: ""
  };
}

function edge(sourceNodeId, targetNodeId) {
  return {
    edge_id: `${sourceNodeId}_${targetNodeId}`,
    source_node_id: sourceNodeId,
    source_port_id: "out",
    target_node_id: targetNodeId,
    target_port_id: "in",
    enabled_types: ["image"]
  };
}

function edgeById(layout, edgeId) {
  const item = layout.edges.find((edgeLayout) => edgeLayout.edge.edge_id === edgeId);
  assert.ok(item, `expected edge ${edgeId}`);
  return item;
}

function nodeById(layout, nodeId) {
  const item = layout.nodes.find((nodeLayout) => nodeLayout.node.node_id === nodeId);
  assert.ok(item, `expected node ${nodeId}`);
  return item;
}

function pathPoints(path) {
  return [...path.matchAll(/[ML]\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)/g)].map((match) => ({
    x: Number(match[1]),
    y: Number(match[2])
  }));
}

function corridorRailYs(layout, edgeIds) {
  const ys = new Set();
  for (const edgeId of edgeIds) {
    const edge = edgeById(layout, edgeId);
    const source = nodeById(layout, edge.edge.source_node_id);
    const target = nodeById(layout, edge.edge.target_node_id);
    const points = pathPoints(edge.d);
    for (let index = 0; index < points.length - 1; index += 1) {
      const current = points[index];
      const next = points[index + 1];
      if (current.y === next.y && current.y > source.y + source.height && current.y < target.y) {
        ys.add(current.y);
      }
    }
  }
  return ys;
}
