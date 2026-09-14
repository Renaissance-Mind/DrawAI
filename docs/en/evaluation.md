# DrawAI Evaluation

[简体中文](../zh-CN/evaluation.md) | **English** | [DrawAI](../../README-en.md)

Reconstruction and editability evaluation for final SVG predictions, included in
DrawAI's `main` branch as the independent `drawai_evaluation` package. No DrawAI
generation setup or local SAM/OCR service is needed to evaluate existing SVGs.
The protocol contains **39 metrics: 9 rule-based metrics and 30 rubric metrics**.

Dataset: [caopu/DrawAI-Bench-Lite](https://huggingface.co/datasets/caopu/DrawAI-Bench-Lite).
It contains 80 images across knowledge maps, posters,
presentation slides, and scientific figures, together with element annotations.
It is a standalone dataset with continuous sample IDs `0001` through `0080`.
Images are `images/0001.png` through `images/0080.png`; matching annotations are
`annotations/0001.json` through `annotations/0080.json`. Domain and source type
are metadata fields rather than directory names.

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
| Sample ID (single) or SVG directory (batch) | You | Matches predictions to benchmark cases |
| Internal candidate manifest | Generated automatically by the evaluator | Records the matched IDs and SVG paths |
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

From the DrawAI repository root, install the optional evaluation dependencies.
All commands in this guide run from that root with the environment activated:

```bash
uv sync --locked --extra evaluation
source .venv/bin/activate
```

Alternatively, with Python 3.12 already installed:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --pre -e '.[evaluation]'
```

Prefer `uv sync --locked` for the exact dependency versions recorded in `uv.lock`.
Evaluation shares compatible core dependencies with DrawAI; the `evaluation`
extra adds the image-scoring and dataset-download dependencies. Rubric evaluation
uses `openai-codex==0.1.0b3` and the fixed judge `gpt-5.6-sol` with `high` reasoning.
The benchmark was run with Codex CLI 0.144.4. Install and authenticate it before
full evaluation; skip this step for `--rule-only`:

```bash
npm install --prefix .runtime @openai/codex@0.144.4
.runtime/node_modules/.bin/codex login
```

The evaluator discovers this local `.runtime` installation automatically. You
can also use a `codex` executable on `PATH`, set `DRAWBENCH_CODEX_BIN` once, or
pass `--codex-bin` explicitly. The Rubric judge runs through the **Codex Python
SDK**; the 9 Rule metrics use local Python computation and Chromium rendering.

The judge reads the authenticated user's `~/.codex/auth.json` into an ephemeral
home and removes that temporary home after each attempt. Set `--host-codex-home`
when the authentication file is stored elsewhere. No credentials belong in
candidate manifests or result archives.

Chrome, Chromium, or Edge is discovered automatically. An explicit browser
executable can be selected with `DRAWAI_SVG_RENDERER_BROWSER`.

## Dataset

```bash
drawai-dataset download --local-dir data/DrawAI-Bench-Lite
drawai-dataset verify --local-dir data/DrawAI-Bench-Lite
```

After this one-time setup, the evaluation commands below need no dataset flag.
Dataset discovery uses `--dataset` when given, then `DRAWAI_EVALUATION_DATASET`,
then `data/DrawAI-Bench-Lite` in the current directory, then the pinned Hugging
Face cache. The default local copy must match the published dataset version.
If no current local dataset is available, the evaluator downloads the images
and annotations automatically from Hugging Face. For a dataset stored elsewhere,
configure it once:

```bash
export DRAWAI_EVALUATION_DATASET=/path/to/DrawAI-Bench-Lite
```

The default dataset is version `2.0.0`, pinned to revision
`711808882430bb59526e89218f6621baa1dda4d0`.
Use `drawai-dataset download --revision <dataset-commit>` to select another snapshot.
Images retain their original resolution; `canvas` in the annotation JSON defines the element coordinate
system. The scorer resizes the reference image to that canvas before comparison.
Dataset verification checks the original-image and annotation checksums.
`drawai-dataset download` updates the managed files and removes unchanged files
that are no longer listed in the dataset manifest after the new files validate.

## Single-Image Evaluation

Provide the sample ID and your final SVG path:

```bash
drawai-evaluate --id 0001 --svg ./result.svg
```

`--id` uses the dataset's four-digit ID. Numeric input such as `--id 1` also
resolves to `0001`. The single-image SVG filename can be arbitrary. IDs outside
the dataset are rejected.

The command prints the result directory and, when the full evaluation finishes,
the Overall, Reconstruction, Editability, Rule, and Rubric scores. To run only
the deterministic Rule stage:

```bash
drawai-evaluate --id 0001 --svg ./result.svg --rule-only
```

## Directory Evaluation

Use one flat folder and name predictions after the dataset sample IDs. For
example, dataset `images/0001.png` corresponds to `predictions/0001.svg`:

```text
predictions/
  0001.svg
  0002.svg
  ...
  0080.svg
```

Then specify only the directory:

```bash
drawai-evaluate --svg-dir ./predictions
```

Folder filenames must use all four digits, including leading zeros. Only exact
sample filenames are matched; unrelated SVGs (for example, asset files) are
listed as ignored.

Place final SVGs in the matching paths. Missing cases are skipped and listed in
`coverage.json`, so you can evaluate a completed subset and rerun the command as
more SVGs become available. Existing malformed SVGs raise errors. Keep unfinished
outputs under temporary names until they are ready. To require all 80 cases:

```bash
drawai-evaluate --svg-dir ./predictions --require-all
```

## Options and Execution

`--dataset`, `--output-root`, `--method`, and `--model` are optional. The default
output directory is `results/<input-name>-<hash>` under the current working
directory; its name is stable for the same input path and labels, enabling reuse.
The default labels are `candidate` and `unspecified`. For named comparisons:

```bash
drawai-evaluate --svg-dir ./predictions \
  --method my-method --model my-model --output-root results/my-experiment
```

`--model` labels the generating model. It does not change the Rubric judge,
which remains `gpt-5.6-sol` with `high` reasoning by default.

Embed image/font resources in the SVG or keep local references resolvable from
its directory. Remote resources must be embedded for reproducibility. The asset
audit records missing local images, and the rendering is scored as submitted.

Defaults are Rule concurrency 8, Rubric concurrency 40, three attempts, and an
1800-second timeout per attempt. Use `--rule-concurrency` and
`--rubric-concurrency` to change worker counts; Rubric supports 1-150 workers.
Keep `--reasoning-effort high` for benchmark-comparable runs. The CLI freezes completed predictions in a
snapshot, renders and scores them, runs the rubric groups required by the GT
elements, and merges only fully validated candidates. A per-output-directory
lock prevents duplicate batch launches.

Run the same command after adding completed predictions to evaluate incrementally.
Unchanged Rule outputs and strictly validated Rubric outputs are reused. Changes
to annotations, SVGs, images, renders, or referenced local assets invalidate the
affected evidence. Judge usage-limit exits return code 75; wait until the reported
retry time before resuming. Other nonzero exits preserve diagnostics under
`sdk_runs/<group>/attempt_*`. The runner never fills missing scores with zero.

## Advanced Manifest Input

The existing manifest interface remains available for arbitrary file layouts
or multiple method/model settings in one run:

```bash
drawai-evaluate --candidates candidates.jsonl
```

Each JSONL row contains the four-digit `bench_id`, SVG path, labels, and completion state:

```json
{"bench_id":"0001","method":"my-method","model":"my-model","candidate_svg":"predictions/0001.svg","status":"completed"}
```

Paths are absolute or relative to the manifest. Only `completed` rows are
evaluated. The `(bench_id, method, model)` combination must be unique; labels
must be non-empty names without path separators. A JSON array or JSON object
with a `candidates` array is also accepted. `--svg`, `--svg-dir`, and `--candidates`
are mutually exclusive.

## Outputs and Scores

Each candidate has `rendered.png`, `rule_based_eval.json`, `rule_provenance.json`,
`rubric/*.json`, `sdk_runs/`, and a `full_evaluation.json` with exactly 39 metrics.
The output root contains `input_candidates.json`, `coverage.json`, the candidate
snapshot, asset audit, task manifest,
scheduler summary, metric catalog, and long/wide comparison CSVs. During Rubric
evaluation, partial merges expose only candidates whose required groups pass
schema and provenance validation.

`coverage.json` lists which benchmark cases were found or missing. The merged
summary's `partial` field describes scoring completion of the selected predictions;
it does not mean that a partial prediction folder covered all 80 benchmark cases.

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
uv sync --locked --extra evaluation --extra dev
source .venv/bin/activate
pytest -q tests/evaluation tests/test_drawai_project_naming.py
```

`src/drawai_evaluation/` contains the Rule scorer, isolated Rubric scheduler,
Chromium renderer, batch runner, dataset loader, merger, and score aggregator.
Tests live in `tests/evaluation/`. See the [metric catalog](evaluation-metrics.md)
for all 39 metrics and the [bilingual JSON catalog](../evaluation/metric_catalog.json)
for stable machine-readable metric identifiers.
