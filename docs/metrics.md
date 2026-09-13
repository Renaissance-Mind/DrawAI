# Metric Catalog

The hierarchy contains 39 metrics: 9 Rule and 30 Rubric.

| Primary | Secondary | Metric | Calculator | Method | Direction |
|---|---|---|---|---|---|
| Reconstruction | Global Visual Fidelity | Structural match | SSIM | rule | up |
| Reconstruction | Global Visual Fidelity | Edge alignment | Edge F1 | rule | up |
| Reconstruction | Global Visual Fidelity | Pixel error | MSE | rule | down |
| Reconstruction | Global Visual Fidelity | Overall readability | VLM Score | rubric | up |
| Reconstruction | Global Visual Fidelity | Layout skeleton | Layout QA | rubric | up |
| Reconstruction | Global Visual Fidelity | Visual hierarchy | Hierarchy QA | rubric | up |
| Reconstruction | Text Fidelity | Text content | Text F1 | rule | up |
| Reconstruction | Text Fidelity | Position lines | Layout QA | rubric | up |
| Reconstruction | Text Fidelity | Alignment spacing | Layout QA | rubric | up |
| Reconstruction | Text Fidelity | Overflow occlusion | Occlusion QA | rubric | up |
| Reconstruction | Text Fidelity | Color emphasis | Style QA | rubric | up |
| Reconstruction | Text Fidelity | Font appearance | Style QA | rubric | up |
| Reconstruction | Text Fidelity | Style consistency | Style QA | rubric | up |
| Reconstruction | Image Fidelity | Image Regions | Region MSE | rule | down |
| Reconstruction | Image Fidelity | Image Alignment | Image mIoU | rule | up |
| Reconstruction | Formula Fidelity | Symbol retention | Formula QA | rubric | up |
| Reconstruction | Formula Fidelity | Structure relation | Formula QA | rubric | up |
| Reconstruction | Formula Fidelity | Position readability | Formula QA | rubric | up |
| Reconstruction | Shape Fidelity | Existence coverage | Shape QA | rubric | up |
| Reconstruction | Shape Fidelity | Visual attributes | Shape QA | rubric | up |
| Reconstruction | Shape Fidelity | Neighbor relation | Shape QA | rubric | up |
| Reconstruction | Connector Fidelity | Path presence | Connector QA | rubric | up |
| Reconstruction | Connector Fidelity | Endpoint direction | Connector QA | rubric | up |
| Reconstruction | Connector Fidelity | Line style noise | Connector QA | rubric | up |
| Reconstruction | Table Fidelity | Grid structure | Table QA | rubric | up |
| Reconstruction | Table Fidelity | Content ownership | Table QA | rubric | up |
| Reconstruction | Table Fidelity | Readability alignment | Table QA | rubric | up |
| Editability | Text Editability | Text boxes | Box Recall | rule | up |
| Editability | Image Editability | Image Sources | Image Recall | rule | up |
| Editability | Shape Editability | Object independence | VLM-QA | rubric | up |
| Editability | Shape Editability | Box placement | BBox QA | rubric | up |
| Editability | Shape Editability | Conflict diagnosis | VLM-QA | rubric | up |
| Editability | Connector Editability | Independent path | VLM-QA | rubric | up |
| Editability | Connector Editability | Endpoint control | VLM-QA | rubric | up |
| Editability | Connector Editability | Mis merge check | VLM-QA | rubric | up |
| Editability | Formula Editability | Editable representation | Object Recall | rule | up |
| Editability | Table Editability | Table region independence | VLM-QA | rubric | up |
| Editability | Table Editability | Editable grid | VLM-QA | rubric | up |
| Editability | Table Editability | Text ownership | VLM-QA | rubric | up |

Raw MSE scores are lower-is-better. Aggregate scores normalize those rows with `1 - score`.
A metric scoped to an absent GT kind is marked `not_applicable`, with a null score.
