# Data dictionary

`dui_l2_annotated.csv` contains 1,542 rows, one per attested *duì* instance. Encoding is UTF-8. Empty cells are genuine missing values (for example, an error instance may have no coded constructional function).

| Column | Type | Values | Description |
|---|---|---|---|
| `Code` | string | e.g. `S_B_F_AF_TG` | Composite participant/instance code. `Mode` and `Level` are also given as explicit columns below, so the code does not need to be parsed for analysis. |
| `ID` | string | | Instance identifier. With `Code`, lets a GLCLC-licensed user rejoin the original sentence. |
| `Mode` | string | `S`, `W` | Spoken or written. |
| `Level` | string | `L1`, `L2`, `L3` | Proficiency within the three-year instructed programme. `L1` beginner, `L2` intermediate, `L3` advanced. |
| `Nationality` | string | 62 values | Learner nationality. |
| `L1` | string | 12 values | Learner first language. |
| `Concordance Line` | string | `[GLCLC text removed]` | Placeholder. The original learner sentence is withheld (see `DATA_LICENSE.md`). |
| `Verb` | string | Chinese | The verb co-occurring with *duì* in the construction. |
| `BCC_COLL` | string | `Attracted`, `Repelled` | Direction of the collostructional association between the verb and *duì* in the BCC reference corpus. |
| `Functions` | string | `DA`, `SI`, `MS`, `ABT`, `DISP`, `EVAL` | Constructional function of the instance. See `docs/annotation_scheme.md`. |
| `Intended Function` | string | `Perspective`, `Causative`, `Topicalisation`, `Parallel`, `Beneficiary`, `Domain`, `Locative`, `Purpose`, `Source`, `Resultative` | Target function, recorded for Non-*duì*-construction errors where the intended meaning is not a *duì* function. Empty otherwise. |
| `Error` | string | `Error`, empty | Marks whether the instance is an error. |
| `Error-Type-New` | string | `Omission`, `Addition`, `Misordering`, `Collocation`, `Non-dui-construction`, empty | Five-category analytical error label used for all statistics and figures. Empty for correct instances. See `docs/error_taxonomy.md`. |
| `Error-Type-Old` | string | as above, with `Collocation` split into `Collocation_Prep` and `Collocation_VA` | Finer error label. The Collocation split is recorded here and reported descriptively only; it is combined into `Collocation` for analysis. |
| `BCC_Frequency` | numeric | 0–63,257 | Frequency of the verb in the BCC reference corpus. |
| `CSL_Score` | numeric | 0–385.55 | Lexical sophistication measure for the verb, derived from a Chinese-as-a-second-language resource. |
| `CSL_COLL` | string | `Attracted`, `Repelled` | Direction of the collostructional association in the CSL resource. |
| `Accessibility` | numeric | 1–6 | Accessibility band for the verb, a hybrid of word difficulty and timing of first encounter in instruction. Lower is more accessible. |
| `Semantics` | string | `Psych`, `Functional`, `Communication`, `Attribute`, `Manner`, `Social`, `Physical` | Semantic class of the verb. |

Full definitions of the measures are given in the methodology section of the paper.

## Reliability files

`reliability/function_annotation_annotator1.csv` and `reliability/function_annotation_annotator2.csv` hold the independently double-coded samples used to assess inter-annotator agreement. They share the columns above where applicable; `annotator2` additionally carries a `Reliability` field. Their `Concordance Line` columns are masked in the same way.
