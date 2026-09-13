# DrawAI Evaluation

Standalone reconstruction and editability evaluation for final SVG predictions.
The protocol contains **39 metrics: 9 rule-based metrics and 30 rubric metrics**.

Dataset: [caopu/DrawAI-Bench-Lite](https://huggingface.co/datasets/caopu/DrawAI-Bench-Lite)
(private; access required). It contains 80 images across knowledge maps, posters,
presentation slides, and scientific figures, together with element annotations.

## Required Inputs

**Provide the final SVG produced by the method you want to evaluate.** Each SVG
must correspond to one of the dataset's 80 `bench_id` values. A complete run of
one method/model setting contains 80 SVGs; a smaller completed subset is also
supported and its coverage is reported.

| File | Provided by | Used for |
|---|---|---|
| Original reference image | Downloaded dataset | Visual reconstruction target |
| GT element annotation JSON | Downloaded dataset | Target object kinds, text, geometry, and positions |
| Final candidate `.svg` | Your method's output | Reconstructed appearance and editable object structure |
| `candidates.jsonl` | You | Associates each SVG with its `bench_id`, method, model, and completion status |
| Candidate `rendered.png` | Generated automatically by the evaluator | Visual comparison with the reference image |

The evaluator renders each candidate SVG with Chromium. Rule metrics compare
the rendered pixels and parsed SVG objects against the reference and annotations.
The Rubric judge reads the reference image, GT JSON, final SVG, and generated
PNG. You do not need to supply candidate PNGs, run SAM/OCR, or provide generation
logs or intermediate application files. Standard SVGs from other methods are
accepted; DrawAI-specific element IDs are optional.

The full 39-metric evaluator accepts SVG predictions. PNG/JPEG alone do not
contain the object structure needed for editability metrics. PPTX, PDF, and
DrawIO files are not parsed directly by this package; export them to SVG first.
The scores then describe that exported SVG. Preserve editable text and vector
objects during export, since a raster-only export loses that structure.

## Install

Python 3.12 on Linux or macOS and a Chromium-based browser are required.

```bash
git clone --single-branch --branch drawAI_evaluation git@github.com:Renaissance-Mind/DrawAI-dev.git
cd DrawAI-dev
python3.12 -m venv .venv
source .venv/bin/activate
pip install --pre -e .
```

The Rule dependencies are pinned to the validated versions. Rubric evaluation
uses `openai-codex==0.1.0b3` and the fixed judge `gpt-5.6-sol` with `high` reasoning.
The benchmark was run with Codex CLI 0.144.4:

```bash
npm install --prefix .runtime @openai/codex@0.144.4
.runtime/node_modules/.bin/codex login
```

The judge reads the authenticated user's `~/.codex/auth.json` into an ephemeral
home and removes that temporary home after each attempt. Set `--host-codex-home`
when the authentication file is stored elsewhere. No credentials belong in
candidate manifests or result archives.

Chrome, Chromium, or Edge is discovered automatically. An explicit browser
executable can be selected with `DRAWAI_SVG_RENDERER_BROWSER`.

## Dataset

```bash
hf auth login
drawai-dataset download --local-dir data/DrawAI-Bench-Lite
drawai-dataset verify --local-dir data/DrawAI-Bench-Lite
```

The default dataset revision is `b53667b7cf0f1acd8a52aed33c22e952ab6eddd4`.
Use `--revision <dataset-commit>` to select another snapshot. Images retain their original
resolution; `canvas` in the annotation JSON defines the element coordinate
system. The scorer resizes the reference image to that canvas before comparison.
Dataset verification checks the original-image and annotation checksums.

## Predictions

For example, keep a completed SVG and its manifest together in this layout:

```text
candidates.jsonl
predictions/
  kmap_ai_013.svg
```

Create `candidates.jsonl` with one JSON object per line, one row per prediction:

```json
{"bench_id":"knowledge_maps/ai_generated_50/kmap_ai_013","method":"my-method","model":"my-model","candidate_svg":"predictions/kmap_ai_013.svg","status":"completed"}
```

| Field | Meaning |
|---|---|
| `bench_id` | Exact case identifier from the dataset's `manifest.json` |
| `candidate_svg` | Final SVG path, absolute or relative to `candidates.jsonl` |
| `method` | Label for your method; use a non-empty name without path separators |
| `model` | Label for the generating model, also without path separators |
| `status` | Set to `completed` only when the final SVG is ready; other states are skipped |

`model` is a result-grouping label; it does not select the Rubric judge. The
judge remains `gpt-5.6-sol`. SVG filenames are arbitrary because `bench_id`
provides the association. Multiple settings can share a manifest, with one
unique completed row per `(bench_id, method, model)`.

Embed image/font resources in the SVG or keep local references resolvable from
its directory. Remote resources must be embedded for reproducibility. The asset
audit records missing local images, and the rendering is scored as submitted.

## Evaluate

```bash
drawai-evaluate \
  --dataset data/DrawAI-Bench-Lite \
  --candidates candidates.jsonl \
  --output-root results/my-experiment \
  --codex-bin .runtime/node_modules/.bin/codex
```

Defaults are Rule concurrency 8, Rubric concurrency 40, three attempts, and an
1800-second timeout per attempt. The CLI freezes completed predictions in a
snapshot, renders and scores them, runs the rubric groups required by the GT
elements, and merges only fully validated candidates. A per-output-directory
lock prevents duplicate batch launches.

For deterministic Rule evaluation without judge calls:

```bash
drawai-evaluate --dataset data/DrawAI-Bench-Lite \
  --candidates candidates.jsonl --output-root results/my-experiment --rule-only
```

Run the same command after adding completed predictions to evaluate incrementally.
Unchanged Rule outputs and strictly validated Rubric outputs are reused. Changes
to annotations, SVGs, images, renders, or referenced local assets invalidate the
affected evidence. Judge usage-limit exits return code 75; wait until the reported
retry time before resuming. Other nonzero exits preserve diagnostics under
`sdk_runs/<group>/attempt_*`. The runner never fills missing scores with zero.

## Outputs and Scores

Each candidate has `rendered.png`, `rule_based_eval.json`, `rule_provenance.json`,
`rubric/*.json`, `sdk_runs/`, and a `full_evaluation.json` with exactly 39 metrics.
The output root contains the candidate snapshot, asset audit, task manifest,
scheduler summary, metric catalog, and long/wide comparison CSVs. During Rubric
evaluation, partial merges expose only candidates whose required groups pass
schema and provenance validation.

```bash
drawai-scores --evaluation-root results/my-experiment
```

The summary reports the mean per-candidate Overall, Reconstruction, Editability,
Rule, and Rubric scores on a 0-100 scale. MSE-based metrics are converted with
`1 - score`; inapplicable metrics are omitted from the mean. Candidate means are
averaged with equal candidate weight. These are benchmark scores, not a
classification accuracy percentage. Compare settings on the same case set, and
report coverage alongside partial results.

The judge's evidence is limited to the GT JSON, reference image, final SVG, and
rendered PNG. Every relevant GT element is scored; text content, whole-page
visual similarity, and object editability use their respective metrics. A
Rubric output counts as complete only when its schema, element coverage, input
hashes, output hash, and completed SDK result agree.

## Development

```bash
pip install --pre -e '.[dev]'
pytest -q
```

`src/drawai_evaluation/` contains the Rule scorer, isolated Rubric scheduler,
Chromium renderer, batch runner, dataset loader, merger, and score aggregator.
See [docs/metrics.md](docs/metrics.md) for the full metric catalog.
