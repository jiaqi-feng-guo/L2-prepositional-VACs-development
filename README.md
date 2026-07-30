# Multidimensional development of L2 *duì*-constructions

Data, annotation scheme, and analysis code for the study

> Guo, J., Pérez-Paredes, P., & Wu, E. L. (under review). *Measuring multidimensional development of L2 prepositional verb-argument constructions.*

The study tracks how learners of Chinese deploy *duì* (对) verb-argument constructions across three proficiency levels, measuring four dimensions at once: productivity, functional complexity, lexical sophistication, and accuracy. The learner data are drawn from the Guangwai-Lancaster Chinese Learner Corpus (GLCLC).

## Repository layout

```
dui-l2-development/
├── README.md
├── LICENSE                     code licence (MIT)
├── DATA_LICENSE.md             terms for the annotated data
├── requirements.txt            Python dependencies
├── CITATION.cff                machine-readable citation
├── data/
│   ├── dui_l2_annotated.csv    1,542 annotated instances (canonical analysis input)
│   ├── data_dictionary.md      description of every column
│   └── reliability/            double-coded samples for inter-annotator agreement
│       ├── function_annotation_annotator1.csv
│       └── function_annotation_annotator2.csv
├── docs/
│   ├── annotation_scheme.md    the six constructional functions and their diagnostics
│   └── error_taxonomy.md       the five error categories and their diagnostics
├── code/
│   └── learner_data_analysis_integrated_v19.py
└── outputs/
    ├── comprehensive_analysis_report_*.txt   full statistics
    └── figures/                              generated figures (svg and pdf)
```

## Reproducing the analysis

```bash
pip install -r requirements.txt
cd code
python learner_data_analysis_integrated_v19.py
```

The script reads `data/dui_l2_annotated.csv`, writes the statistical report and the figures to `outputs/`, and prints progress. The version of the report committed here was produced from this dataset and reports the numbers that appear in the paper (1,542 instances; 1,171 correct, 371 errors).

## A note on the corpus text

The learner sentences themselves are not redistributed here. In every data file the `Concordance Line` column has been replaced with the placeholder `[GLCLC text removed]`, and the annotator free-text notes column has been removed. Everything needed to reproduce the reported statistics is retained: the level and mode of each instance, the co-occurring verb, the constructional function, the error coding, and the derived lexical measures. Researchers with GLCLC access can restore the original sentences by joining on the `Code` and `ID` fields. See `DATA_LICENSE.md`.

## Contact

Jiaqi Feng Guo, University of Turku — jiaqi.guo@utu.fi
