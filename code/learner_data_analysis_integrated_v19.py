#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
L2 Chinese 对-Construction Analysis - Integrated Script v19
===========================================================

Generates 9 publication-quality figures with comprehensive statistical analysis.

v19 CHANGES (June 2026):
- Error taxonomy reduced to 5 analytical categories: 'Preposition substitution'
  and 'Collocation' are MERGED into a single 'Collocation' category for all
  statistics and figures. The finer split is preserved in the data as
  'Error-Type-Old' (Collocation_Prep = preposition-slot error; Collocation_VA =
  verb-slot error) and reported descriptively only. Five categories: Omission,
  Addition, Misordering, Collocation, Non-dui-construction.
- Input now reads a SINGLE combined workbook (learner_data_updated.xlsx) whose
  'Error-Type-New' column carries the 5-category label (or 'Uncodable'); a row
  is an error iff 'Error-Type-New' is non-empty.

v19 CHANGES (June 2026):
- Error taxonomy updated to the revised 6 categories (Omission, Addition,
  Misordering, Preposition substitution, Collocation, Non-dui-construction).
  'X-Y Reversal' folded into Misordering; 'Semantic-Misalignment' folded into
  Collocation; 'Collocational' renamed 'Collocation'.
- NEW 'Uncodable' residual: uninterpretable errors count toward the overall
  error RATE (4.4.1) but are EXCLUDED from all error-TYPE analyses (4.4.2 and
  Error x Function), per Corder's interpretability criterion.
- Input now reads the two source files directly (correct + error CSVs) and
  concatenates them; no single combined file needed.
- NEW Intended-Function tabulation for Non-dui-construction errors.
- Graph 9 axis relabelled 'Constructional Function' (it plots the six
  constructional functions, not the intended functions).

V14 CHANGES (March 2026):
- Benjamini-Hochberg correction on all pairwise LLR tests
- Bootstrap 95% CIs for all Cramér's V effect sizes
- Kruskal-Wallis + Dunn's post-hoc for Accessibility (central tendency)
- Pairwise chi-square for error rate stability confirmation
- Productivity: LLR test on unique type counts across levels
- Statistical framework summary table in report
- All p-values collected and BH-corrected per analysis section

V13 Features (retained):
- Chi-square test of independence for all distribution comparisons
- Log-Likelihood Ratio (LLR/G²) for pairwise corpus comparisons
- Cramér's V effect size for chi-square tests
- Log Ratio effect size for LLR comparisons
- CRITICAL: Sections 4.1-4.3 analyse CORRECT USAGE ONLY (errors filtered)
- Section 4.4 analyses errors specifically
- Graph 9 with chi-square, standardized residuals, Cramér's V
- Graph 9b: Correspondence Analysis visualization

Statistical Framework (based on corpus linguistics standards):
- Overall distribution tests: Chi-square test of independence
- Overall central tendency (ordinal): Kruskal-Wallis H (accessibility only)
- Pairwise corpus comparisons: Log-Likelihood Ratio (Dunning 1993)
- Pairwise central tendency: Dunn's test (accessibility only)
- Effect sizes: Cramér's V with bootstrap 95% CI, Log Ratio, eta-squared
- Multiple comparison correction: Benjamini-Hochberg (all pairwise tests)

References:
- Dunning (1993) for LLR
- Gries & Paquot (2020) for reporting standards
- Benjamini & Hochberg (1995) for FDR correction

Author: Jiaqi's Dui-construction Project
Date: March 2026
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from scipy import stats
from scipy.stats import chi2_contingency
from collections import Counter
import warnings
import os
import math
from pathlib import Path
from datetime import datetime

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

# v19: the entire analysis runs from this single workbook.
# 'Error-Type-New' = 5-category label (or 'Uncodable'); 'Error-Type-Old' =
# finer 6-way split (Collocation_Prep/VA). A row is an error iff
# 'Error-Type-New' is non-empty.
COMBINED_FILE = str(Path(__file__).resolve().parent.parent / "data" / "dui_l2_annotated.csv")
OUTPUT_DIR = str(Path(__file__).resolve().parent.parent / "outputs")

Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

FIGURE_DPI = 300
FIGURE_FORMAT = ['svg', 'pdf']

# Corpus sizes (total words per proficiency level)
CORPUS_SIZES = {
    'L1': 288534,  # Beginner
    'L2': 627227,  # Intermediate
    'L3': 378467  # Advanced
}

LEVELS = ['L1', 'L2', 'L3']
LEVEL_LABELS = {'L1': 'Beginner', 'L2': 'Intermediate', 'L3': 'Advanced'}

LEVEL_COLORS = {
    'L1': '#2ecc71',  # Green - Beginner
    'L2': '#3498db',  # Blue - Intermediate
    'L3': '#9b59b6'  # Purple - Advanced
}

FUNCTIONS = ['DA', 'SI', 'MS', 'ABT', 'DISP', 'EVAL']
FUNCTION_COLORS = {
    'DA': '#e74c3c', 'SI': '#3498db', 'MS': '#2ecc71',
    'ABT': '#f39c12', 'DISP': '#9b59b6', 'EVAL': '#1abc9c'
}

SEMANTIC_CLASSES = ['Psych', 'Manner', 'Functional', 'Social', 'Attribute', 'Communication']
SEMANTIC_COLORS = {
    'Psych': '#3498db', 'Manner': '#2ecc71', 'Functional': '#e74c3c',
    'Social': '#9b59b6', 'Attribute': '#f39c12', 'Communication': '#1abc9c'
}

# v19: 5 analytical categories. 'Preposition substitution' is merged into
# 'Collocation' (the finer Prep/VA split lives in 'Error-Type-Old').
ERROR_TAXONOMY = [
    'Omission', 'Addition', 'Misordering',
    'Collocation', 'Non-dui-construction'
]

# 'Uncodable' is a residual, uninterpretable category (Corder's interpretability
# criterion). It is counted toward the overall error RATE (4.4.1) but EXCLUDED
# from every error-TYPE analysis (4.4.2 distribution, LLR, and Error x Function).
UNCODABLE_LABEL = 'Uncodable'

ERROR_COLORS = {
    'Omission': '#e74c3c', 'Addition': '#3498db', 'Misordering': '#f39c12',
    'Collocation': '#e67e22', 'Non-dui-construction': '#1abc9c'
}

# Intended (target) functions, recorded only for Non-dui-construction errors
INTENDED_FUNCTIONS = ['Perspective', 'Causative', 'Topicalisation', 'Parallel',
                      'Domain', 'Locative', 'Purpose', 'Resultative']


# ============================================================================
# STATISTICAL FUNCTIONS (V12)
# ============================================================================

def calculate_llr(o1, o2, n1, n2):
    """
    Calculate Log-Likelihood Ratio (G²) for corpus comparison.
    Standard test in corpus linguistics (Dunning 1993).

    Args:
        o1: Observed count in corpus 1
        o2: Observed count in corpus 2
        n1: Total size of corpus 1
        n2: Total size of corpus 2

    Returns:
        dict with LLR, p-value, log_ratio, direction, significance
    """
    o1 = max(o1, 0.5)
    o2 = max(o2, 0.5)

    total_obs = o1 + o2
    total_n = n1 + n2
    e1 = n1 * total_obs / total_n
    e2 = n2 * total_obs / total_n

    llr = 2 * (o1 * math.log(o1 / e1) + o2 * math.log(o2 / e2))
    p_value = 1 - stats.chi2.cdf(abs(llr), 1)

    norm1 = (o1 / n1) * 100000
    norm2 = (o2 / n2) * 100000
    log_ratio = math.log2(norm2 / norm1) if norm1 > 0 else 0
    direction = "+" if norm2 > norm1 else "-"

    if p_value < 0.001:
        sig = "***"
    elif p_value < 0.01:
        sig = "**"
    elif p_value < 0.05:
        sig = "*"
    else:
        sig = "n.s."

    return {
        'LLR': llr, 'p': p_value, 'norm1': norm1, 'norm2': norm2,
        'log_ratio': log_ratio, 'direction': direction, 'sig': sig
    }


def calculate_chi2_independence(contingency_table):
    """
    Calculate chi-square test of independence for a contingency table.

    Returns:
        dict with chi2, df, p-value, Cramér's V, effect interpretation
    """
    chi2, p, dof, expected = chi2_contingency(contingency_table)

    n = contingency_table.sum()
    min_dim = min(contingency_table.shape[0] - 1, contingency_table.shape[1] - 1)
    cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 else 0

    if cramers_v < 0.1:
        effect_interp = "negligible"
    elif cramers_v < 0.3:
        effect_interp = "small"
    elif cramers_v < 0.5:
        effect_interp = "medium"
    else:
        effect_interp = "large"

    return {
        'chi2': chi2, 'df': dof, 'p': p, 'cramers_v': cramers_v,
        'effect_size': effect_interp, 'expected': expected
    }


def format_p(p):
    """Format p-value for display."""
    if p < 0.001:
        return "p < .001"
    elif p < 0.01:
        return f"p = {p:.3f}"
    else:
        return f"p = {p:.3f}"


def calculate_standardized_residuals(observed, expected):
    """Calculate Pearson standardized residuals for chi-square."""
    with np.errstate(divide='ignore', invalid='ignore'):
        residuals = (observed - expected) / np.sqrt(expected)
        residuals = np.nan_to_num(residuals, nan=0.0, posinf=0.0, neginf=0.0)
    return residuals


def apply_bh_correction(p_values):
    """
    Apply Benjamini-Hochberg FDR correction to a list of p-values.
    Returns adjusted p-values in the same order as input.

    Reference: Benjamini & Hochberg (1995)
    """
    n = len(p_values)
    if n == 0:
        return []

    # Sort p-values and track original indices
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * n

    # BH procedure: p_adj[i] = min(p[i] * n/rank, 1.0), enforcing monotonicity
    prev = 1.0
    for rank_idx in range(n - 1, -1, -1):
        orig_idx, p_val = indexed[rank_idx]
        rank = rank_idx + 1
        adj_p = min(p_val * n / rank, prev)
        adj_p = min(adj_p, 1.0)
        adjusted[orig_idx] = adj_p
        prev = adj_p

    return adjusted


def apply_bh_to_llr_dict(llr_dict):
    """
    Apply BH correction to a dictionary of LLR results.
    Adds 'p_adj' and 'sig_adj' keys to each entry.
    Returns the modified dict and a list of (label, p_raw, p_adj) for reporting.
    """
    labels = list(llr_dict.keys())
    raw_ps = [llr_dict[k]['p'] for k in labels]
    adj_ps = apply_bh_correction(raw_ps)

    corrections = []
    for i, label in enumerate(labels):
        llr_dict[label]['p_adj'] = adj_ps[i]
        p_adj = adj_ps[i]
        if p_adj < 0.001:
            llr_dict[label]['sig_adj'] = "***"
        elif p_adj < 0.01:
            llr_dict[label]['sig_adj'] = "**"
        elif p_adj < 0.05:
            llr_dict[label]['sig_adj'] = "*"
        else:
            llr_dict[label]['sig_adj'] = "n.s."
        corrections.append((label, llr_dict[label]['p'], p_adj))

    return llr_dict, corrections


def bootstrap_cramers_v_ci(contingency_table, n_bootstrap=2000, ci=0.95):
    """
    Bootstrap 95% confidence interval for Cramér's V.

    Args:
        contingency_table: numpy array (observed counts)
        n_bootstrap: number of bootstrap samples
        ci: confidence level

    Returns:
        dict with point estimate, lower, upper bounds
    """
    observed = np.array(contingency_table, dtype=float)
    n = observed.sum()
    rows, cols = observed.shape
    min_dim = min(rows - 1, cols - 1)

    if min_dim == 0 or n == 0:
        return {'V': 0, 'ci_lower': 0, 'ci_upper': 0}

    # Point estimate
    chi2, _, _, _ = chi2_contingency(observed)
    v_point = np.sqrt(chi2 / (n * min_dim))

    # Flatten to probabilities for resampling
    probs = (observed / n).flatten()
    categories = np.arange(len(probs))

    v_samples = []
    for _ in range(n_bootstrap):
        # Resample n observations from the joint distribution
        sample = np.random.choice(categories, size=int(n), p=probs)
        # Reconstruct contingency table
        resampled = np.zeros_like(observed)
        for idx in sample:
            r, c = divmod(idx, cols)
            resampled[r, c] += 1

        # Check for empty rows/cols
        if np.any(resampled.sum(axis=0) == 0) or np.any(resampled.sum(axis=1) == 0):
            continue

        try:
            chi2_b, _, _, _ = chi2_contingency(resampled)
            v_b = np.sqrt(chi2_b / (n * min_dim))
            v_samples.append(v_b)
        except:
            continue

    if len(v_samples) < 100:
        return {'V': v_point, 'ci_lower': np.nan, 'ci_upper': np.nan}

    alpha = 1 - ci
    lower = np.percentile(v_samples, 100 * alpha / 2)
    upper = np.percentile(v_samples, 100 * (1 - alpha / 2))

    return {'V': v_point, 'ci_lower': lower, 'ci_upper': upper}


def pairwise_chi2_error_rate(level_counts, error_count_by_level, levels):
    """
    Pairwise chi-square tests for error rate comparison between adjacent levels.
    error_count_by_level is the TRUE error count per level (includes Uncodable),
    so the rate reflects all errors, not only the codable ones.
    Returns list of dicts with chi2, p, cramers_v for each pair.
    """
    results = []
    pairs = [(levels[0], levels[1]), (levels[1], levels[2])]

    for l1, l2 in pairs:
        total_l1 = level_counts[l1]
        total_l2 = level_counts[l2]
        errors_l1 = error_count_by_level[l1]
        errors_l2 = error_count_by_level[l2]
        correct_l1 = total_l1 - errors_l1
        correct_l2 = total_l2 - errors_l2

        table = np.array([[errors_l1, correct_l1], [errors_l2, correct_l2]])

        try:
            chi2, p, dof, _ = chi2_contingency(table, correction=True)  # Yates correction for 2x2
            n = table.sum()
            cramers_v = np.sqrt(chi2 / n) if n > 0 else 0
        except:
            chi2, p, dof, cramers_v = np.nan, np.nan, 1, np.nan

        results.append({
            'pair': f'{l1}→{l2}',
            'chi2': chi2, 'p': p, 'df': dof, 'cramers_v': cramers_v,
            'rate_l1': (errors_l1 / total_l1 * 100) if total_l1 > 0 else 0,
            'rate_l2': (errors_l2 / total_l2 * 100) if total_l2 > 0 else 0
        })

    # Apply BH correction to the pair of p-values
    raw_ps = [r['p'] for r in results]
    adj_ps = apply_bh_correction(raw_ps)
    for i, r in enumerate(results):
        r['p_adj'] = adj_ps[i]
        r['sig_adj'] = "***" if adj_ps[i] < 0.001 else (
            "**" if adj_ps[i] < 0.01 else ("*" if adj_ps[i] < 0.05 else "n.s."))

    return results


def kruskal_wallis_with_effect(groups_data, group_labels):
    """
    Kruskal-Wallis H test with eta-squared effect size.
    Suitable for ordinal data (e.g., accessibility scores).

    Args:
        groups_data: list of arrays, one per group
        group_labels: list of group names

    Returns:
        dict with H statistic, df, p-value, eta-squared, effect interpretation
    """
    # Filter out empty groups
    valid = [(d, l) for d, l in zip(groups_data, group_labels) if len(d) > 0]
    if len(valid) < 2:
        return {'H': np.nan, 'df': 0, 'p': np.nan, 'eta_sq': np.nan, 'effect_size': 'N/A'}

    data_arrays = [v[0] for v in valid]

    H, p = stats.kruskal(*data_arrays)

    # Eta-squared: H / (N - 1)
    N = sum(len(d) for d in data_arrays)
    k = len(data_arrays)
    eta_sq = (H - k + 1) / (N - k) if (N - k) > 0 else 0
    eta_sq = max(0, eta_sq)  # Can be slightly negative with small samples

    if eta_sq < 0.01:
        effect_interp = "negligible"
    elif eta_sq < 0.06:
        effect_interp = "small"
    elif eta_sq < 0.14:
        effect_interp = "medium"
    else:
        effect_interp = "large"

    return {
        'H': H, 'df': k - 1, 'p': p, 'eta_sq': eta_sq,
        'effect_size': effect_interp
    }


def dunns_posthoc(groups_data, group_labels):
    """
    Dunn's post-hoc test for pairwise comparisons after Kruskal-Wallis.
    Uses BH correction.

    Returns list of dicts with z-statistic, p-value, adjusted p-value.
    """
    from itertools import combinations

    # Combine all data with group labels
    all_data = []
    all_groups = []
    for data, label in zip(groups_data, group_labels):
        all_data.extend(data)
        all_groups.extend([label] * len(data))

    all_data = np.array(all_data)
    all_groups = np.array(all_groups)

    # Rank all observations
    ranks = stats.rankdata(all_data)
    N = len(ranks)

    # Mean ranks per group
    mean_ranks = {}
    group_ns = {}
    for label in group_labels:
        mask = all_groups == label
        if mask.sum() > 0:
            mean_ranks[label] = ranks[mask].mean()
            group_ns[label] = mask.sum()

    # Pairwise comparisons
    results = []
    pairs = list(combinations([l for l in group_labels if l in mean_ranks], 2))

    # Tied rank correction
    _, tie_counts = np.unique(ranks, return_counts=True)
    tie_correction = 1 - np.sum(tie_counts ** 3 - tie_counts) / (N ** 3 - N)

    for l1, l2 in pairs:
        diff = mean_ranks[l1] - mean_ranks[l2]
        se = np.sqrt(tie_correction * (N * (N + 1) / 12) * (1 / group_ns[l1] + 1 / group_ns[l2]))
        z = diff / se if se > 0 else 0
        p = 2 * (1 - stats.norm.cdf(abs(z)))  # Two-tailed

        results.append({
            'pair': f'{l1}→{l2}',
            'mean_rank_1': mean_ranks[l1],
            'mean_rank_2': mean_ranks[l2],
            'z': z, 'p': p
        })

    # BH correction
    raw_ps = [r['p'] for r in results]
    adj_ps = apply_bh_correction(raw_ps)
    for i, r in enumerate(results):
        r['p_adj'] = adj_ps[i]
        r['sig_adj'] = "***" if adj_ps[i] < 0.001 else (
            "**" if adj_ps[i] < 0.01 else ("*" if adj_ps[i] < 0.05 else "n.s."))

    return results


# ============================================================================
# DATA LOADING
# ============================================================================

def load_data_combined(combined_file):
    """v19: Load the single combined workbook.

    The workbook carries 'Error-Type-New' (the 5-category analytical label, or
    'Uncodable') and 'Error-Type-Old' (the finer 6-way split, with
    Collocation_Prep / Collocation_VA). A row is an error iff 'Error-Type-New'
    is non-empty. 'Error-Type' is set from 'Error-Type-New' for all downstream
    code; 'Error-Subtype' preserves the finer split for descriptive reporting.
    """
    print("=" * 70)
    print("LOADING DATA (combined workbook, v19)")
    print("=" * 70)

    df = pd.read_csv(combined_file, encoding='utf-8') if combined_file.endswith('.csv') \
        else pd.read_excel(combined_file)
    df.columns = df.columns.str.strip()
    if 'Concordance Line' in df.columns:
        df = df[df['Concordance Line'].notna()].copy()

    if 'Error-Type-New' not in df.columns:
        raise ValueError("Combined workbook must contain an 'Error-Type-New' column.")

    # Analytical 5-category label -> 'Error-Type'; finer split -> 'Error-Subtype'
    df['Error-Type'] = df['Error-Type-New'].fillna('').astype(str).str.strip().replace('nan', '')
    if 'Error-Type-Old' in df.columns:
        df['Error-Subtype'] = df['Error-Type-Old'].fillna('').astype(str).str.strip().replace('nan', '')
    else:
        df['Error-Subtype'] = ''

    # A row is an error iff it carries a (new) error-type label
    df['is_error'] = df['Error-Type'] != ''

    df['Level'] = df['Level'].astype(str).str.strip().str.upper()
    df = df[df['Level'].isin(LEVELS)].copy()

    df_correct = df[~df['is_error']].copy()
    df_errors = df[df['is_error']].copy()

    n_uncodable = (df_errors['Error-Type'] == UNCODABLE_LABEL).sum()
    print(f"Combined file: {combined_file} ({len(df)} rows)")
    print(f"  Correct usage: {len(df_correct)} ({len(df_correct) / len(df) * 100:.1f}%)")
    print(f"  Error instances: {len(df_errors)} ({len(df_errors) / len(df) * 100:.1f}%)")
    print(f"    of which Uncodable (excluded from error-type analysis): {n_uncodable}")
    # v19: report the Prep/VA split that the merge folds together
    if 'Error-Subtype' in df_errors.columns:
        sub = df_errors[df_errors['Error-Subtype'].isin(['Collocation_Prep', 'Collocation_VA'])]
        if len(sub):
            print("  Collocation split (descriptive only):")
            print(sub.groupby(['Error-Subtype', 'Level']).size().to_string())

    return df, df_correct, df_errors


# (v19: the former two-file load_data(correct_file, error_file) loader was
#  removed; the analysis now runs entirely from COMBINED_FILE via
#  load_data_combined() above.)


# ============================================================================
# FEATURE EXTRACTION
# ============================================================================

def extract_features(df, df_correct, df_errors):
    """Extract features for analysis."""
    print("\n" + "=" * 70)
    print("FEATURE EXTRACTION")
    print("=" * 70)

    features = {}

    # Level counts (all data for overview)
    features['level_counts'] = df['Level'].value_counts().reindex(LEVELS, fill_value=0)
    features['level_counts_correct'] = df_correct['Level'].value_counts().reindex(LEVELS, fill_value=0)

    print(f"\nLevel Distribution (All):")
    for level in LEVELS:
        all_count = features['level_counts'][level]
        correct_count = features['level_counts_correct'][level]
        print(f"  {level}: {all_count} total, {correct_count} correct")

    # Function by level - CORRECT USAGE ONLY (for sections 4.1-4.3)
    func_level = pd.crosstab(df_correct['Level'], df_correct['Functions'])
    for func in FUNCTIONS:
        if func not in func_level.columns:
            func_level[func] = 0
    func_level = func_level.reindex(index=LEVELS, fill_value=0)
    func_level = func_level[FUNCTIONS]
    features['function_by_level'] = func_level

    print(f"\nFunctions × Level (Correct Usage Only):")
    print(func_level)

    # Semantics by level - CORRECT USAGE ONLY
    if 'Semantics' in df_correct.columns:
        sem_level = pd.crosstab(df_correct['Level'], df_correct['Semantics'])
        for sem in SEMANTIC_CLASSES:
            if sem not in sem_level.columns:
                sem_level[sem] = 0
        sem_level = sem_level.reindex(index=LEVELS, fill_value=0)
        features['semantics_by_level'] = sem_level

    # Accessibility by level - CORRECT USAGE ONLY
    if 'Accessibility' in df_correct.columns:
        acc_by_level = df_correct.groupby('Level')['Accessibility'].mean()
        acc_by_level = acc_by_level.reindex(LEVELS, fill_value=0)
        features['accessibility_by_level'] = acc_by_level

        # Accessibility distribution
        acc_dist = pd.crosstab(df_correct['Level'], df_correct['Accessibility'])
        features['accessibility_distribution'] = acc_dist

    # Productivity - CORRECT USAGE ONLY
    if 'Verb' in df_correct.columns:
        productivity = df_correct.groupby('Level')['Verb'].nunique()
        productivity = productivity.reindex(LEVELS, fill_value=0)
        features['productivity_by_level'] = productivity

    # Error analysis - ERRORS ONLY (section 4.4)
    features['total_errors'] = len(df_errors)

    # Codable errors only (exclude the uninterpretable 'Uncodable' residual).
    # The error RATE uses ALL errors; error-TYPE analyses use codable only.
    df_errors_codable = df_errors[df_errors['Error-Type'] != UNCODABLE_LABEL].copy()
    features['n_uncodable'] = int((df_errors['Error-Type'] == UNCODABLE_LABEL).sum())
    features['total_errors_codable'] = len(df_errors_codable)

    if len(df_errors) > 0:
        # True error COUNT per level (includes Uncodable) -> used for the rate
        error_count = pd.Series(
            {level: int((df_errors['Level'] == level).sum()) for level in LEVELS}
        ).reindex(LEVELS, fill_value=0)
        features['error_count_by_level'] = error_count

        # Error rates by level (denominator = all instances; numerator = all errors)
        error_rates = {}
        for level in LEVELS:
            total = features['level_counts'][level]
            errors = error_count[level]
            error_rates[level] = (errors / total * 100) if total > 0 else 0
        features['error_rate_by_level'] = pd.Series(error_rates)

        # Error type by level - CODABLE ONLY
        if 'Error-Type' in df_errors_codable.columns and len(df_errors_codable) > 0:
            error_type_level = pd.crosstab(df_errors_codable['Level'], df_errors_codable['Error-Type'])
            for et in ERROR_TAXONOMY:
                if et not in error_type_level.columns:
                    error_type_level[et] = 0
            error_type_level = error_type_level.reindex(index=LEVELS, fill_value=0)
            error_type_level = error_type_level[ERROR_TAXONOMY]
            features['error_type_by_level'] = error_type_level

            # Error function matrix - CODABLE ONLY
            error_function = pd.crosstab(df_errors_codable['Error-Type'], df_errors_codable['Functions'])
            for et in ERROR_TAXONOMY:
                if et not in error_function.index:
                    error_function.loc[et] = 0
            for func in FUNCTIONS:
                if func not in error_function.columns:
                    error_function[func] = 0
            error_function = error_function.reindex(index=ERROR_TAXONOMY, columns=FUNCTIONS, fill_value=0)
            features['error_function_matrix'] = error_function

        # Intended-function distribution within Non-dui-construction errors
        if 'Intended Function' in df_errors_codable.columns:
            nd = df_errors_codable[df_errors_codable['Error-Type'] == 'Non-dui-construction'].copy()
            nd['Intended Function'] = nd['Intended Function'].astype(str).str.strip()
            intended = nd['Intended Function'].value_counts()
            intended = intended.reindex(INTENDED_FUNCTIONS, fill_value=0)
            features['intended_function_dist'] = intended
            print(f"\nIntended-Function distribution (Non-dui errors, n={int(intended.sum())}):")
            for fn in INTENDED_FUNCTIONS:
                if intended[fn] > 0:
                    print(f"  {fn:15}: {int(intended[fn])}")
        print(f"\nUncodable (excluded from error-type analysis): {features['n_uncodable']}")

    return features


# ============================================================================
# COMPREHENSIVE STATISTICAL ANALYSIS (V12)
# ============================================================================

def compute_comprehensive_statistics(df, df_correct, df_errors, features):
    """Compute comprehensive statistics using improved framework."""
    print("\n" + "=" * 70)
    print("COMPUTING COMPREHENSIVE STATISTICS")
    print("=" * 70)

    stats_results = {}

    # =========================================================================
    # 4.1 PRODUCTIVITY STATISTICS
    # =========================================================================
    print("\n[4.1] PRODUCTIVITY")
    print("-" * 50)

    # Normalized frequency (per 100K words)
    freq_100k = {}
    print("\nNormalised Frequency (per 100,000 words) - CORRECT USAGE:")
    for level in LEVELS:
        count = features['level_counts_correct'][level]
        freq = (count / CORPUS_SIZES[level]) * 100000
        freq_100k[level] = freq
        print(f"  {LEVEL_LABELS[level]:12}: {count:>4} correct = {freq:>6.2f} per 100K")

    # LLR pairwise comparisons
    print("\nPairwise Comparisons (Log-Likelihood Ratio):")
    c1 = features['level_counts_correct']['L1']
    c2 = features['level_counts_correct']['L2']
    c3 = features['level_counts_correct']['L3']
    n1, n2, n3 = CORPUS_SIZES['L1'], CORPUS_SIZES['L2'], CORPUS_SIZES['L3']

    llr_L1_L2 = calculate_llr(c1, c2, n1, n2)
    llr_L2_L3 = calculate_llr(c2, c3, n2, n3)

    print(f"  L1→L2: {freq_100k['L1']:.2f} → {freq_100k['L2']:.2f}, G²={llr_L1_L2['LLR']:.2f}, "
          f"LogR={llr_L1_L2['log_ratio']:+.2f} {llr_L1_L2['sig']}")
    print(f"  L2→L3: {freq_100k['L2']:.2f} → {freq_100k['L3']:.2f}, G²={llr_L2_L3['LLR']:.2f}, "
          f"LogR={llr_L2_L3['log_ratio']:+.2f} {llr_L2_L3['sig']}")

    # Unique type count significance test
    if 'productivity_by_level' in features:
        prod = features['productivity_by_level']
        print(f"\nUnique Verb Types: L1={prod['L1']}, L2={prod['L2']}, L3={prod['L3']}")
        # LLR on type counts: are the type counts different given corpus sizes?
        llr_types_L1_L2 = calculate_llr(prod['L1'], prod['L2'], n1, n2)
        llr_types_L2_L3 = calculate_llr(prod['L2'], prod['L3'], n2, n3)
        print(
            f"  Type LLR L1→L2: G²={llr_types_L1_L2['LLR']:.2f}, LogR={llr_types_L1_L2['log_ratio']:+.2f} {llr_types_L1_L2['sig']}")
        print(
            f"  Type LLR L2→L3: G²={llr_types_L2_L3['LLR']:.2f}, LogR={llr_types_L2_L3['log_ratio']:+.2f} {llr_types_L2_L3['sig']}")
    else:
        llr_types_L1_L2 = llr_types_L2_L3 = None

    stats_results['productivity'] = {
        'freq_100k': freq_100k,
        'llr_L1_L2': llr_L1_L2,
        'llr_L2_L3': llr_L2_L3,
        'llr_types_L1_L2': llr_types_L1_L2,
        'llr_types_L2_L3': llr_types_L2_L3
    }

    # =========================================================================
    # 4.2 FUNCTIONAL COMPLEXITY STATISTICS
    # =========================================================================
    print("\n[4.2] FUNCTIONAL COMPLEXITY")
    print("-" * 50)

    func_table = features['function_by_level'].values

    # Chi-square test of independence (overall)
    chi2_func = calculate_chi2_independence(func_table)
    print(f"\nOverall Distribution Test (Level × Function):")
    print(f"  χ²({chi2_func['df']}) = {chi2_func['chi2']:.2f}, {format_p(chi2_func['p'])}")
    print(f"  Cramér's V = {chi2_func['cramers_v']:.3f} ({chi2_func['effect_size']} effect)")

    # LLR pairwise by function
    print("\nPairwise Comparisons by Function (LLR):")
    llr_func_L1_L2 = {}
    llr_func_L2_L3 = {}

    for func in FUNCTIONS:
        c1 = features['function_by_level'].loc['L1', func]
        c2 = features['function_by_level'].loc['L2', func]
        c3 = features['function_by_level'].loc['L3', func]

        llr_func_L1_L2[func] = calculate_llr(c1, c2, n1, n2)
        llr_func_L2_L3[func] = calculate_llr(c2, c3, n2, n3)

    print(f"  {'Function':<10} {'L1→L2 LogR':>12} {'Sig':>6} {'L2→L3 LogR':>12} {'Sig':>6}")
    for func in FUNCTIONS:
        lr1 = llr_func_L1_L2[func]['log_ratio']
        s1 = llr_func_L1_L2[func]['sig']
        lr2 = llr_func_L2_L3[func]['log_ratio']
        s2 = llr_func_L2_L3[func]['sig']
        print(f"  {func:<10} {lr1:>+12.2f} {s1:>6} {lr2:>+12.2f} {s2:>6}")

    stats_results['functions'] = {
        'chi2': chi2_func,
        'llr_L1_L2': llr_func_L1_L2,
        'llr_L2_L3': llr_func_L2_L3
    }

    # BH correction for function LLR pairwise tests
    print("\n  BH-corrected pairwise tests (L1→L2):")
    llr_func_L1_L2, bh_func12 = apply_bh_to_llr_dict(llr_func_L1_L2)
    llr_func_L2_L3, bh_func23 = apply_bh_to_llr_dict(llr_func_L2_L3)
    print(
        f"  {'Function':<10} {'L1→L2 raw p':>12} {'adj p':>10} {'sig':>6}  {'L2→L3 raw p':>12} {'adj p':>10} {'sig':>6}")
    for func in FUNCTIONS:
        p1 = llr_func_L1_L2[func]['p']
        pa1 = llr_func_L1_L2[func]['p_adj']
        s1 = llr_func_L1_L2[func]['sig_adj']
        p2 = llr_func_L2_L3[func]['p']
        pa2 = llr_func_L2_L3[func]['p_adj']
        s2 = llr_func_L2_L3[func]['sig_adj']
        print(f"  {func:<10} {p1:>12.4f} {pa1:>10.4f} {s1:>6}  {p2:>12.4f} {pa2:>10.4f} {s2:>6}")

    # Bootstrap CI for Cramér's V
    print("\n  Bootstrap 95% CI for Cramér's V (Functions):")
    v_ci_func = bootstrap_cramers_v_ci(func_table)
    print(f"  V = {v_ci_func['V']:.3f} [{v_ci_func['ci_lower']:.3f}, {v_ci_func['ci_upper']:.3f}]")
    stats_results['functions']['v_ci'] = v_ci_func

    # =========================================================================
    # 4.3.1 SEMANTIC CLASSES STATISTICS
    # =========================================================================
    if 'semantics_by_level' in features:
        print("\n[4.3.1] SEMANTIC CLASSES")
        print("-" * 50)

        sem_table = features['semantics_by_level'].values

        # Chi-square test of independence
        chi2_sem = calculate_chi2_independence(sem_table)
        print(f"\nOverall Distribution Test (Level × Semantics):")
        print(f"  χ²({chi2_sem['df']}) = {chi2_sem['chi2']:.2f}, {format_p(chi2_sem['p'])}")
        print(f"  Cramér's V = {chi2_sem['cramers_v']:.3f} ({chi2_sem['effect_size']} effect)")

        # LLR pairwise
        llr_sem_L1_L2 = {}
        llr_sem_L2_L3 = {}

        semantics = list(features['semantics_by_level'].columns)
        for sem in semantics:
            c1 = features['semantics_by_level'].loc['L1', sem]
            c2 = features['semantics_by_level'].loc['L2', sem]
            c3 = features['semantics_by_level'].loc['L3', sem]

            llr_sem_L1_L2[sem] = calculate_llr(c1, c2, n1, n2)
            llr_sem_L2_L3[sem] = calculate_llr(c2, c3, n2, n3)

        stats_results['semantics'] = {
            'chi2': chi2_sem,
            'llr_L1_L2': llr_sem_L1_L2,
            'llr_L2_L3': llr_sem_L2_L3
        }

        # BH correction for semantic LLR pairwise tests
        llr_sem_L1_L2, _ = apply_bh_to_llr_dict(llr_sem_L1_L2)
        llr_sem_L2_L3, _ = apply_bh_to_llr_dict(llr_sem_L2_L3)
        print("\n  BH-corrected semantic pairwise tests applied.")

        # Bootstrap CI for Cramér's V
        v_ci_sem = bootstrap_cramers_v_ci(sem_table)
        print(f"  V = {v_ci_sem['V']:.3f} [{v_ci_sem['ci_lower']:.3f}, {v_ci_sem['ci_upper']:.3f}]")
        stats_results['semantics']['v_ci'] = v_ci_sem

    # =========================================================================
    # 4.3.2 ACCESSIBILITY STATISTICS
    # =========================================================================
    if 'accessibility_distribution' in features:
        print("\n[4.3.2] ACCESSIBILITY")
        print("-" * 50)

        acc_table = features['accessibility_distribution'].values

        # Chi-square test of independence (distributional question)
        chi2_acc = calculate_chi2_independence(acc_table)
        print(f"\nDistribution Test (Level × Accessibility Scale):")
        print(f"  χ²({chi2_acc['df']}) = {chi2_acc['chi2']:.2f}, {format_p(chi2_acc['p'])}")
        print(f"  Cramér's V = {chi2_acc['cramers_v']:.3f} ({chi2_acc['effect_size']} effect)")

        # Bootstrap CI for Cramér's V
        v_ci_acc = bootstrap_cramers_v_ci(acc_table)
        print(f"  V 95% CI = [{v_ci_acc['ci_lower']:.3f}, {v_ci_acc['ci_upper']:.3f}]")

        # Kruskal-Wallis H test (central tendency question - ordinal data)
        kw_groups = []
        kw_labels = []
        for level in LEVELS:
            level_data = df_correct[df_correct['Level'] == level]['Accessibility'].dropna().values
            if len(level_data) > 0:
                kw_groups.append(level_data)
                kw_labels.append(level)

        kw_result = kruskal_wallis_with_effect(kw_groups, kw_labels)
        print(f"\nCentral Tendency Test (Kruskal-Wallis H):")
        print(f"  H({kw_result['df']}) = {kw_result['H']:.2f}, {format_p(kw_result['p'])}")
        print(f"  η² = {kw_result['eta_sq']:.3f} ({kw_result['effect_size']} effect)")

        # Dunn's post-hoc with BH correction
        if kw_result['p'] < 0.05:
            dunn_results = dunns_posthoc(kw_groups, kw_labels)
            print(f"\n  Dunn's Post-Hoc (BH-corrected):")
            for dr in dunn_results:
                print(f"    {dr['pair']}: z={dr['z']:.2f}, p_adj={dr['p_adj']:.4f} {dr['sig_adj']} "
                      f"(mean ranks: {dr['mean_rank_1']:.1f} vs {dr['mean_rank_2']:.1f})")
        else:
            dunn_results = []
            print(f"\n  Dunn's Post-Hoc: not required (omnibus n.s.)")

        # LLR pairwise by accessibility scale (with BH)
        llr_acc_L1_L2 = {}
        llr_acc_L2_L3 = {}
        acc_scales = sorted(features['accessibility_distribution'].columns)

        for scale in acc_scales:
            c1 = features['accessibility_distribution'].loc['L1', scale] if 'L1' in features[
                'accessibility_distribution'].index else 0
            c2 = features['accessibility_distribution'].loc['L2', scale] if 'L2' in features[
                'accessibility_distribution'].index else 0
            c3 = features['accessibility_distribution'].loc['L3', scale] if 'L3' in features[
                'accessibility_distribution'].index else 0

            llr_acc_L1_L2[f'Scale_{scale}'] = calculate_llr(c1, c2, n1, n2)
            llr_acc_L2_L3[f'Scale_{scale}'] = calculate_llr(c2, c3, n2, n3)

        llr_acc_L1_L2, _ = apply_bh_to_llr_dict(llr_acc_L1_L2)
        llr_acc_L2_L3, _ = apply_bh_to_llr_dict(llr_acc_L2_L3)

        print(f"\nPairwise by Scale (LLR, BH-corrected):")
        print(f"  {'Scale':<10} {'L1→L2 LogR':>12} {'adj sig':>8} {'L2→L3 LogR':>12} {'adj sig':>8}")
        for scale in acc_scales:
            key = f'Scale_{scale}'
            lr1 = llr_acc_L1_L2[key]['log_ratio']
            s1 = llr_acc_L1_L2[key]['sig_adj']
            lr2 = llr_acc_L2_L3[key]['log_ratio']
            s2 = llr_acc_L2_L3[key]['sig_adj']
            print(f"  {key:<10} {lr1:>+12.2f} {s1:>8} {lr2:>+12.2f} {s2:>8}")

        stats_results['accessibility'] = {
            'chi2': chi2_acc,
            'v_ci': v_ci_acc,
            'kruskal_wallis': kw_result,
            'dunns': dunn_results,
            'llr_L1_L2': llr_acc_L1_L2,
            'llr_L2_L3': llr_acc_L2_L3
        }

    # =========================================================================
    # 4.4 ERROR ANALYSIS STATISTICS
    # =========================================================================
    if 'error_type_by_level' in features:
        print("\n[4.4] ERROR ANALYSIS")
        print("-" * 50)

        # Error rates chi-square (rates comparison)
        # Numerator = ALL errors (incl. Uncodable); denominator = all instances.
        error_counts = []
        correct_counts = []
        for level in LEVELS:
            total = features['level_counts'][level]
            errors = features['error_count_by_level'][level]
            error_counts.append(errors)
            correct_counts.append(total - errors)

        error_rate_table = np.array([error_counts, correct_counts]).T
        chi2_error_rate = calculate_chi2_independence(error_rate_table)

        print(f"\nError Rate Comparison (Level × Error/Correct):")
        print(f"  χ²({chi2_error_rate['df']}) = {chi2_error_rate['chi2']:.2f}, {format_p(chi2_error_rate['p'])}")
        print(f"  Cramér's V = {chi2_error_rate['cramers_v']:.3f} ({chi2_error_rate['effect_size']} effect)")

        # Pairwise error rate chi-square (to confirm stability)
        pairwise_error = pairwise_chi2_error_rate(
            features['level_counts'], features['error_count_by_level'], LEVELS
        )
        print(f"\n  Pairwise Error Rate Tests (BH-corrected):")
        for pe in pairwise_error:
            print(f"    {pe['pair']}: {pe['rate_l1']:.1f}% → {pe['rate_l2']:.1f}%, "
                  f"χ²={pe['chi2']:.2f}, p_adj={pe['p_adj']:.4f} {pe['sig_adj']}")

        # Bootstrap CI for error rate Cramér's V
        v_ci_err_rate = bootstrap_cramers_v_ci(error_rate_table)
        print(f"  V 95% CI = [{v_ci_err_rate['ci_lower']:.3f}, {v_ci_err_rate['ci_upper']:.3f}]")

        # Error type distribution chi-square
        # Filter out columns (error types) with all zeros to avoid chi-square issues
        error_df = features['error_type_by_level']
        non_zero_cols = error_df.columns[error_df.sum() > 0]
        error_table_filtered = error_df[non_zero_cols].values

        # Also check for rows with all zeros
        row_sums = error_table_filtered.sum(axis=1)
        if all(row_sums > 0) and error_table_filtered.shape[1] > 1:
            chi2_error_type = calculate_chi2_independence(error_table_filtered)
            print(f"\nError Type Distribution (Level × Error-Type):")
            print(f"  χ²({chi2_error_type['df']}) = {chi2_error_type['chi2']:.2f}, {format_p(chi2_error_type['p'])}")
            print(f"  Cramér's V = {chi2_error_type['cramers_v']:.3f} ({chi2_error_type['effect_size']} effect)")
            if len(non_zero_cols) < len(error_df.columns):
                print(f"  Note: {len(error_df.columns) - len(non_zero_cols)} empty error type(s) excluded")
        else:
            chi2_error_type = {'chi2': np.nan, 'p': np.nan, 'df': 0, 'cramers_v': np.nan, 'effect_size': 'N/A'}
            print(f"\nError Type Distribution: insufficient data for chi-square test")

        # LLR pairwise for error types
        llr_error_L1_L2 = {}
        llr_error_L2_L3 = {}

        # Use error counts as corpus sizes for error type comparison
        err_n1 = features['error_type_by_level'].loc['L1'].sum()
        err_n2 = features['error_type_by_level'].loc['L2'].sum()
        err_n3 = features['error_type_by_level'].loc['L3'].sum()

        if err_n1 > 0 and err_n2 > 0 and err_n3 > 0:
            for et in ERROR_TAXONOMY:
                c1 = features['error_type_by_level'].loc['L1', et]
                c2 = features['error_type_by_level'].loc['L2', et]
                c3 = features['error_type_by_level'].loc['L3', et]

                llr_error_L1_L2[et] = calculate_llr(c1, c2, err_n1, err_n2)
                llr_error_L2_L3[et] = calculate_llr(c2, c3, err_n2, err_n3)

        stats_results['errors'] = {
            'chi2_rate': chi2_error_rate,
            'chi2_type': chi2_error_type,
            'pairwise_error_rate': pairwise_error,
            'v_ci_err_rate': v_ci_err_rate,
            'llr_L1_L2': llr_error_L1_L2,
            'llr_L2_L3': llr_error_L2_L3
        }

        # BH correction for error type LLR
        if llr_error_L1_L2:
            llr_error_L1_L2, _ = apply_bh_to_llr_dict(llr_error_L1_L2)
            llr_error_L2_L3, _ = apply_bh_to_llr_dict(llr_error_L2_L3)
            print("\n  BH-corrected error type pairwise tests applied.")

        # Error × Function matrix statistics (for Graph 9)
        if 'error_function_matrix' in features:
            ef_df = features['error_function_matrix']

            # Filter out rows/cols with all zeros for chi-square
            non_zero_rows = ef_df.index[ef_df.sum(axis=1) > 0]
            non_zero_cols = ef_df.columns[ef_df.sum(axis=0) > 0]
            ef_filtered = ef_df.loc[non_zero_rows, non_zero_cols]

            if ef_filtered.shape[0] > 1 and ef_filtered.shape[1] > 1:
                ef_matrix = ef_filtered.values
                chi2_ef = calculate_chi2_independence(ef_matrix)

                # Calculate standardized residuals for filtered matrix
                _, _, _, expected = chi2_contingency(ef_matrix)
                std_residuals = calculate_standardized_residuals(ef_matrix, expected)

                # Create full-size residuals matrix (with NaN for excluded)
                full_residuals = pd.DataFrame(
                    np.nan,
                    index=ef_df.index,
                    columns=ef_df.columns
                )
                full_residuals.loc[non_zero_rows, non_zero_cols] = std_residuals

                stats_results['error_function'] = {
                    'chi2': chi2_ef,
                    'expected': expected,
                    'std_residuals': full_residuals.values,
                    'filtered_rows': list(non_zero_rows),
                    'filtered_cols': list(non_zero_cols)
                }

                print(f"\nError × Function Association:")
                print(f"  χ²({chi2_ef['df']}) = {chi2_ef['chi2']:.2f}, {format_p(chi2_ef['p'])}")
                print(f"  Cramér's V = {chi2_ef['cramers_v']:.3f} ({chi2_ef['effect_size']} effect)")
                if len(non_zero_rows) < len(ef_df.index) or len(non_zero_cols) < len(ef_df.columns):
                    print(f"  Note: empty rows/cols excluded from chi-square")
            else:
                stats_results['error_function'] = None
                print(f"\nError × Function: insufficient data for chi-square test")

    return stats_results


# ============================================================================
# GRAPH GENERATION FUNCTIONS
# ============================================================================

def save_figure(fig, output_dir, name):
    """Save figure in multiple formats."""
    for fmt in FIGURE_FORMAT:
        filepath = os.path.join(output_dir, f'{name}.{fmt}')
        fig.savefig(filepath, format=fmt, dpi=FIGURE_DPI, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
    print(f"✓ Saved: {name}")


def generate_summary_dashboard(features, stats_results, output_dir):
    """Graph 1: Summary dashboard with key metrics."""
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)

    # 1a: Sample size by level
    ax1 = fig.add_subplot(gs[0, 0])
    counts = features['level_counts']
    bars = ax1.bar(LEVELS, counts, color=[LEVEL_COLORS[l] for l in LEVELS], edgecolor='black')
    ax1.set_xlabel('Proficiency Level', fontsize=11)
    ax1.set_ylabel('Number of Instances', fontsize=11)
    ax1.set_title('(a) Sample Distribution', fontsize=12, fontweight='bold')
    for bar, count in zip(bars, counts):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                 str(int(count)), ha='center', fontsize=10)

    # 1b: Function distribution
    ax2 = fig.add_subplot(gs[0, 1])
    func_totals = features['function_by_level'].sum()
    colors = [FUNCTION_COLORS[f] for f in func_totals.index]
    wedges, texts, autotexts = ax2.pie(func_totals, labels=func_totals.index,
                                       autopct='%1.1f%%', colors=colors, startangle=90)
    ax2.set_title('(b) Function Distribution\n(Correct Usage)', fontsize=12, fontweight='bold')

    # 1c: Error rate by level
    ax3 = fig.add_subplot(gs[0, 2])
    if 'error_rate_by_level' in features:
        error_rates = features['error_rate_by_level']
        bars = ax3.bar(LEVELS, error_rates, color=[LEVEL_COLORS[l] for l in LEVELS], edgecolor='black')
        ax3.set_xlabel('Proficiency Level', fontsize=11)
        ax3.set_ylabel('Error Rate (%)', fontsize=11)
        ax3.set_title('(c) Error Rate by Level', fontsize=12, fontweight='bold')
        for bar, rate in zip(bars, error_rates):
            ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                     f'{rate:.1f}%', ha='center', fontsize=10)

    # 1d: Productivity by level
    ax4 = fig.add_subplot(gs[1, 0])
    if 'productivity_by_level' in features:
        prod = features['productivity_by_level']
        bars = ax4.bar(LEVELS, prod, color=[LEVEL_COLORS[l] for l in LEVELS], edgecolor='black')
        ax4.set_xlabel('Proficiency Level', fontsize=11)
        ax4.set_ylabel('Unique Verbs', fontsize=11)
        ax4.set_title('(d) Lexical Productivity\n(Correct Usage)', fontsize=12, fontweight='bold')
        for bar, p in zip(bars, prod):
            ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                     str(int(p)), ha='center', fontsize=10)

    # 1e: Accessibility by level
    ax5 = fig.add_subplot(gs[1, 1])
    if 'accessibility_by_level' in features:
        acc = features['accessibility_by_level']
        bars = ax5.bar(LEVELS, acc, color=[LEVEL_COLORS[l] for l in LEVELS], edgecolor='black')
        ax5.set_xlabel('Proficiency Level', fontsize=11)
        ax5.set_ylabel('Mean Accessibility', fontsize=11)
        ax5.set_title('(e) Accessibility Score\n(Correct Usage)', fontsize=12, fontweight='bold')
        for bar, a in zip(bars, acc):
            ax5.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                     f'{a:.2f}', ha='center', fontsize=10)

    # 1f: Key statistics text
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis('off')

    stats_text = "Key Statistics:\n\n"

    if 'productivity' in stats_results:
        p = stats_results['productivity']
        stats_text += "Productivity (LLR):\n"
        stats_text += f"  L1→L2: G²={p['llr_L1_L2']['LLR']:.1f} {p['llr_L1_L2']['sig']}\n"
        stats_text += f"  L2→L3: G²={p['llr_L2_L3']['LLR']:.1f} {p['llr_L2_L3']['sig']}\n\n"

    if 'functions' in stats_results:
        f = stats_results['functions']['chi2']
        stats_text += "Functions (Level × Type):\n"
        stats_text += f"  χ²({f['df']})={f['chi2']:.1f}, V={f['cramers_v']:.3f}\n\n"

    if 'errors' in stats_results:
        e = stats_results['errors']['chi2_type']
        stats_text += "Error Types (Level × Type):\n"
        stats_text += f"  χ²({e['df']})={e['chi2']:.1f}, V={e['cramers_v']:.3f}\n"

    ax6.text(0.1, 0.9, stats_text, transform=ax6.transAxes, fontsize=10,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))

    plt.suptitle('L2 Chinese 对-Construction: Overview Dashboard', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_figure(fig, output_dir, 'graph1_summary_dashboard')
    plt.close()


def generate_normality_assessment(df, features, output_dir):
    """Graph 2: Distribution across proficiency levels with normality assessment."""
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(2, 3, figure=fig, hspace=0.35, wspace=0.3)

    # Top row: Distribution of instances across levels
    # 2a: Count distribution
    ax1 = fig.add_subplot(gs[0, 0])
    counts = features['level_counts']
    bars = ax1.bar(LEVELS, counts, color=[LEVEL_COLORS[l] for l in LEVELS],
                   edgecolor='black', alpha=0.8)
    ax1.set_xlabel('Proficiency Level', fontsize=10)
    ax1.set_ylabel('Number of Instances', fontsize=10)
    ax1.set_title('(a) Instance Distribution', fontsize=11, fontweight='bold')
    for bar, count in zip(bars, counts):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                 f'{int(count)}\n({count / counts.sum() * 100:.1f}%)',
                 ha='center', fontsize=9)

    # 2b: Function distribution by level (stacked)
    ax2 = fig.add_subplot(gs[0, 1])
    func_counts = features['function_by_level']
    bottom = np.zeros(len(LEVELS))
    for func in FUNCTIONS:
        values = func_counts[func].values
        ax2.bar(LEVELS, values, bottom=bottom, label=func,
                color=FUNCTION_COLORS[func], edgecolor='white', linewidth=0.5)
        bottom += values
    ax2.set_xlabel('Proficiency Level', fontsize=10)
    ax2.set_ylabel('Number of Instances', fontsize=10)
    ax2.set_title('(b) Functions by Level', fontsize=11, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=8, ncol=2)

    # 2c: Error vs Non-error distribution
    ax3 = fig.add_subplot(gs[0, 2])
    if 'Error' in df.columns:
        error_counts = df.groupby(['Level', 'Error']).size().unstack(fill_value=0)
        error_counts = error_counts.reindex(index=LEVELS, fill_value=0)

        x = np.arange(len(LEVELS))
        width = 0.35

        if 'N/A' in error_counts.columns:
            bars1 = ax3.bar(x - width / 2, error_counts['N/A'], width,
                            label='Correct', color='#27ae60', edgecolor='black')
        if 'Error' in error_counts.columns:
            bars2 = ax3.bar(x + width / 2, error_counts['Error'], width,
                            label='Error', color='#e74c3c', edgecolor='black')

        ax3.set_xticks(x)
        ax3.set_xticklabels(LEVELS)
        ax3.set_xlabel('Proficiency Level', fontsize=10)
        ax3.set_ylabel('Number of Instances', fontsize=10)
        ax3.set_title('(c) Error Distribution', fontsize=11, fontweight='bold')
        ax3.legend(fontsize=9)

    # Bottom row: Q-Q plots for BCC_Frequency by level
    freq_col = 'BCC_Frequency' if 'BCC_Frequency' in df.columns else None

    for idx, level in enumerate(LEVELS):
        ax_qq = fig.add_subplot(gs[1, idx])

        if freq_col:
            level_data = df[df['Level'] == level][freq_col].dropna()
            # Log transform for better normality (frequency data is often skewed)
            level_data_log = np.log1p(level_data)

            if len(level_data_log) >= 3:
                stats.probplot(level_data_log, dist="norm", plot=ax_qq)
                ax_qq.get_lines()[0].set_color(LEVEL_COLORS[level])
                ax_qq.get_lines()[0].set_markersize(4)
                ax_qq.get_lines()[1].set_color('red')

                # Shapiro-Wilk test
                if len(level_data_log) <= 5000:
                    stat, p = stats.shapiro(level_data_log[:min(5000, len(level_data_log))])
                    ax_qq.text(0.05, 0.95, f'Shapiro-Wilk\np = {p:.4f}',
                               transform=ax_qq.transAxes, fontsize=8,
                               verticalalignment='top',
                               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        ax_qq.set_title(f'({"def"[idx]}) Q-Q: {LEVEL_LABELS[level]} (n={len(df[df["Level"] == level])})',
                        fontsize=10, fontweight='bold')
        ax_qq.set_xlabel('Theoretical Quantiles', fontsize=9)
        ax_qq.set_ylabel('Sample Quantiles', fontsize=9)

    plt.suptitle('Distribution Analysis Across Proficiency Levels',
                 fontsize=14, fontweight='bold', y=0.98)

    save_figure(fig, output_dir, 'graph2_distribution_analysis')
    plt.close()


def generate_productivity_divergence(features, output_dir):
    """Figure 1: Productivity divergence (indexed-growth line chart).

    Plots two measures on a single axis, each indexed to the beginner level
    (L1 = 1x), so the divergence between them is directly visible: token
    frequency (normalised per 100K, correct usage) plateaus after the
    beginner-to-intermediate jump, while unique verb types keep rising.

    Absolute values are printed at each point (token frequency per 100K;
    count of unique verb types). All numbers are read live from the computed
    features, so the figure never goes stale when the data are re-annotated.
    """
    prod = features['productivity_by_level']       # unique verb types per level
    counts = features['level_counts_correct']      # correct token counts per level

    # Absolute values
    types_abs = {l: int(prod[l]) for l in LEVELS}
    freq_abs = {l: (counts[l] / CORPUS_SIZES[l]) * 100000 for l in LEVELS}

    # Indexed to beginner level (L1 = 1.0)
    types_idx = [types_abs[l] / types_abs['L1'] for l in LEVELS]
    freq_idx = [freq_abs[l] / freq_abs['L1'] for l in LEVELS]

    # LLR for the frequency callout (L2->L3)
    n = CORPUS_SIZES
    freq_23 = calculate_llr(counts['L2'], counts['L3'], n['L2'], n['L3'])

    freq_color = '#2c7fb8'
    type_color = '#238b74'

    fig, ax = plt.subplots(figsize=(9.4, 6.6))
    x = np.arange(len(LEVELS))

    # Shade the intermediate-to-advanced region to foreground the plateau
    ax.axvspan(1, 2, color='#000000', alpha=0.04, zorder=0)

    # Token frequency (solid) and verb types (dashed)
    ax.plot(x, freq_idx, color=freq_color, lw=2.6, marker='o', markersize=11,
            markerfacecolor='white', markeredgecolor=freq_color, markeredgewidth=2.6,
            label='Token frequency (per 100k words)', zorder=3)
    ax.plot(x, types_idx, color=type_color, lw=2.6, ls='--', marker='s', markersize=10,
            markerfacecolor='white', markeredgecolor=type_color, markeredgewidth=2.6,
            label='Unique verb types', zorder=3)

    # Absolute-value labels at each point (types above, frequency below)
    for i, l in enumerate(LEVELS):
        ax.annotate(f'{types_abs[l]}', (x[i], types_idx[i]),
                    textcoords='offset points', xytext=(0, 12), ha='center',
                    fontsize=11, color=type_color, fontweight='bold')
        ax.annotate(f'{freq_abs[l]:.1f}', (x[i], freq_idx[i]),
                    textcoords='offset points', xytext=(0, -18), ha='center',
                    fontsize=11, color=freq_color, fontweight='bold')

    # Callouts on the L2->L3 segment (percentages computed live).
    # Placed clear of both lines: the types note sits above the dashed line,
    # the frequency note below the solid line.
    gtype = (types_abs['L3'] - types_abs['L2']) / types_abs['L2'] * 100
    gfreq = (freq_abs['L3'] - freq_abs['L2']) / freq_abs['L2'] * 100
    type_mid = (types_idx[1] + types_idx[2]) / 2
    freq_mid = (freq_idx[1] + freq_idx[2]) / 2
    ax.annotate(f'types keep rising\n(+{gtype:.0f}%, p < .001)',
                xy=(1.55, type_mid),
                xytext=(1.62, type_mid + 0.60),
                fontsize=10.5, color=type_color, ha='left', va='bottom',
                arrowprops=dict(arrowstyle='-', color=type_color, lw=0.8))
    fsig = freq_23['sig'] if freq_23['sig'] != 'n.s.' else 'n.s.'
    ax.annotate(f'frequency plateaus\n(+{gfreq:.0f}%, {fsig})',
                xy=(1.55, freq_mid),
                xytext=(1.62, freq_mid - 0.95),
                fontsize=10.5, color=freq_color, ha='left', va='top',
                arrowprops=dict(arrowstyle='-', color=freq_color, lw=0.8))

    ax.set_xticks(x)
    ax.set_xticklabels([f'{l}\n({LEVEL_LABELS[l]})' for l in LEVELS], fontsize=11)
    ax.set_ylabel('Growth relative to beginner level (\u00d7)', fontsize=12)
    ax.set_ylim(0, max(types_idx + freq_idx) * 1.18)
    ax.set_title('Productivity: verb-type range diverges from token frequency',
                 fontsize=14, pad=14)
    ax.legend(loc='upper left', frameon=False, fontsize=11)
    ax.grid(axis='y', alpha=0.25)
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)

    fig.text(0.5, -0.02,
             'Values labelled at each point are absolute (token frequency per 100k words; '
             'count of unique verb types). Lines show growth\nindexed to the beginner level so '
             'the two measures share a scale.',
             ha='center', fontsize=8.5, color='#555555')

    plt.tight_layout()
    save_figure(fig, output_dir, 'figure1_productivity_divergence')
    plt.close()


def generate_four_dimension_summary(features, output_dir):
    """Figure 4 (manuscript): four dimensions develop out of step.

    A 2x2 small-multiple summarising the whole developmental picture on one
    page: Productivity (token frequency per 100K + unique verb types, twin
    axes), Complexity (functional diversity in bits, Shannon entropy of the
    six-function distribution), Sophistication (mean verb accessibility;
    higher = less accessible), and Accuracy (error rate %). Every value is
    read live from the computed features, so the figure tracks the data.
    """
    counts = features['level_counts_correct']
    prod = features['productivity_by_level']
    func = features['function_by_level']            # correct-usage function counts
    acc = features['accessibility_by_level']         # mean accessibility per level
    err = features['error_rate_by_level']            # % errors per level

    freq = {l: (counts[l] / CORPUS_SIZES[l]) * 100000 for l in LEVELS}
    types = {l: int(prod[l]) for l in LEVELS}

    # Complexity = Shannon entropy (bits) of the function distribution per level
    def entropy_bits(row):
        p = np.asarray(row, dtype=float)
        p = p[p > 0]
        p = p / p.sum()
        return float(-(p * np.log2(p)).sum()) if p.size else 0.0
    bits = {l: entropy_bits(func.loc[l].values) for l in LEVELS}

    x = np.arange(len(LEVELS))
    xt = [f'{l}\n({LEVEL_LABELS[l]})' for l in LEVELS]
    freq_color, type_color = '#2c7fb8', '#238b74'
    comp_color, soph_color, acc_color = '#7b3fbf', '#e08214', '#e8483b'

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    (axP, axC), (axS, axA) = axes

    def style(ax, ylabel, title, tcolor):
        ax.set_xticks(x); ax.set_xticklabels([l for l in LEVELS], fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title, fontsize=13, fontweight='bold', color=tcolor, pad=8)
        ax.grid(axis='y', linestyle=':', alpha=0.5)
        for s in ['top', 'right']:
            ax.spines[s].set_visible(False)
        ax.tick_params(length=0)

    # ---- Productivity (twin axis) ----
    fvals = [freq[l] for l in LEVELS]
    tvals = [types[l] for l in LEVELS]
    axP.plot(x, fvals, color=freq_color, lw=2.4, marker='o', markersize=8,
             markerfacecolor='white', markeredgecolor=freq_color, markeredgewidth=2.2)
    axP.set_ylabel('tokens / 100k', fontsize=10, color=freq_color)
    axP.tick_params(axis='y', colors=freq_color)
    axP.set_ylim(0, max(fvals) * 1.25)
    axPt = axP.twinx()
    axPt.plot(x, tvals, color=type_color, lw=2.4, ls='--', marker='s', markersize=8,
              markerfacecolor='white', markeredgecolor=type_color, markeredgewidth=2.2)
    axPt.set_ylabel('verb types', fontsize=10, color=type_color)
    axPt.tick_params(axis='y', colors=type_color)
    axPt.set_ylim(0, max(tvals) * 1.25)
    for s in ['top']:
        axPt.spines[s].set_visible(False)
    style(axP, 'tokens / 100k', 'Productivity', freq_color)

    # ---- Complexity ----
    cvals = [bits[l] for l in LEVELS]
    axC.plot(x, cvals, color=comp_color, lw=2.4, marker='o', markersize=8,
             markerfacecolor='white', markeredgecolor=comp_color, markeredgewidth=2.2)
    for xi, v in zip(x, cvals):
        axC.annotate(f'{v:.2f}', (xi, v), textcoords='offset points',
                     xytext=(0, 9), ha='center', fontsize=9, color=comp_color)
    pad = (max(cvals) - min(cvals)) or 0.1
    axC.set_ylim(min(cvals) - pad * 0.8, max(cvals) + pad * 1.2)
    style(axC, 'function diversity (bits)', 'Complexity', comp_color)

    # ---- Sophistication ----
    svals = [float(acc[l]) for l in LEVELS]
    axS.plot(x, svals, color=soph_color, lw=2.4, marker='o', markersize=8,
             markerfacecolor='white', markeredgecolor=soph_color, markeredgewidth=2.2)
    for xi, v in zip(x, svals):
        axS.annotate(f'{v:.2f}', (xi, v), textcoords='offset points',
                     xytext=(0, 9), ha='center', fontsize=9, color=soph_color)
    padS = (max(svals) - min(svals)) or 0.1
    axS.set_ylim(min(svals) - padS * 0.8, max(svals) + padS * 1.3)
    style(axS, 'mean verb accessibility\n(higher = less accessible)', 'Sophistication', soph_color)

    # ---- Accuracy ----
    avals = [float(err[l]) for l in LEVELS]
    axA.plot(x, avals, color=acc_color, lw=2.4, marker='o', markersize=8,
             markerfacecolor='white', markeredgecolor=acc_color, markeredgewidth=2.2)
    for xi, v in zip(x, avals):
        axA.annotate(f'{v:.1f}%', (xi, v), textcoords='offset points',
                     xytext=(0, 9), ha='center', fontsize=9, color=acc_color)
    axA.set_ylim(0, max(avals) * 1.35)
    style(axA, 'error rate (%)', 'Accuracy', acc_color)

    fig.suptitle('Four dimensions develop out of step: volume-driven early, qualitative later',
                 fontsize=14, y=0.99)
    fig.text(0.5, -0.01,
             'L1\u2192L2: productivity surges while complexity, sophistication and accuracy hold.   '
             'L2\u2192L3: tokens plateau but types, function diversity and sophistication rise; '
             'accuracy stays flat.',
             ha='center', fontsize=8.5, color='#555555')
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    save_figure(fig, output_dir, 'figure4_four_dimension_summary')
    plt.close()


def generate_productivity_slope(features, output_dir):
    """Graph 3: Productivity dual panel.

    (a) Token frequency (normalised per 100K, correct usage only) and
    (b) verb type diversity (unique verb types, correct usage only), side by
    side, with LLR significance brackets on each adjacent transition. All
    values are read live from the computed features, so the figure always
    reflects the current data.
    """
    prod = features['productivity_by_level']          # unique verb types per level
    counts = features['level_counts_correct']          # correct token counts per level

    # Normalised token frequency per 100K words
    freq = {l: (counts[l] / CORPUS_SIZES[l]) * 100000 for l in LEVELS}

    # LLR significance markers for the brackets (raw G²; productivity has only
    # two adjacent comparisons per measure, matching the 4.1 reporting).
    n = CORPUS_SIZES
    tok_12 = calculate_llr(counts['L1'], counts['L2'], n['L1'], n['L2'])['sig']
    tok_23 = calculate_llr(counts['L2'], counts['L3'], n['L2'], n['L3'])['sig']
    typ_12 = calculate_llr(int(prod['L1']), int(prod['L2']), n['L1'], n['L2'])['sig']
    typ_23 = calculate_llr(int(prod['L2']), int(prod['L3']), n['L2'], n['L3'])['sig']

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(14, 6.5))
    x = np.arange(len(LEVELS))
    colors = [LEVEL_COLORS[l] for l in LEVELS]
    xticklabels = [f'{l}\n({LEVEL_LABELS[l]})' for l in LEVELS]

    def sig_bracket(ax, x1, x2, y, label):
        """Draw a significance bracket between two bars."""
        h = y * 0.03
        ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], lw=1.3, color='black')
        ax.text((x1 + x2) / 2, y + h, label, ha='center', va='bottom',
                fontsize=12, fontweight='bold',
                color='gray' if label == 'n.s.' else 'black')

    # ---- Panel (a): Token Frequency ----
    fvals = [freq[l] for l in LEVELS]
    top = max(fvals)
    barsA = axA.bar(x, fvals, color=colors, edgecolor='black', alpha=0.85, width=0.62)
    for bar, l, v in zip(barsA, LEVELS, fvals):
        axA.text(bar.get_x() + bar.get_width() / 2, v + top * 0.015,
                 f'{v:.1f}', ha='center', fontsize=12, fontweight='bold')
        axA.text(bar.get_x() + bar.get_width() / 2, top * 0.045,
                 f'n={counts[l]}', ha='center', fontsize=9,
                 color='white', fontweight='bold')
    sig_bracket(axA, 0, 1, top * 1.08, tok_12)
    sig_bracket(axA, 1, 2, top * 1.20, tok_23)
    axA.set_ylim(0, top * 1.42)
    axA.set_xticks(x)
    axA.set_xticklabels(xticklabels, fontsize=11)
    axA.set_ylabel('Frequency per 100K Words', fontsize=12)
    axA.set_title('(a) Token Frequency\n(Correct Usage Only)',
                  fontsize=13, fontweight='bold')
    axA.grid(axis='y', alpha=0.3)

    # ---- Panel (b): Verb Type Diversity ----
    tvals = [int(prod[l]) for l in LEVELS]
    topb = max(tvals)
    barsB = axB.bar(x, tvals, color=colors, edgecolor='black', alpha=0.85, width=0.62)
    for bar, v in zip(barsB, tvals):
        axB.text(bar.get_x() + bar.get_width() / 2, v + topb * 0.015,
                 f'{v}', ha='center', fontsize=12, fontweight='bold')
    sig_bracket(axB, 0, 1, topb * 1.08, typ_12)
    sig_bracket(axB, 1, 2, topb * 1.20, typ_23)
    axB.set_ylim(0, topb * 1.42)
    axB.set_xticks(x)
    axB.set_xticklabels(xticklabels, fontsize=11)
    axB.set_ylabel('Number of Unique Verb Types', fontsize=12)
    axB.set_title('(b) Verb Type Diversity\n(Correct Usage Only)',
                  fontsize=13, fontweight='bold')
    axB.grid(axis='y', alpha=0.3)

    # Growth percentages annotation on panel (b)
    if prod['L1'] > 0:
        g12 = (prod['L2'] - prod['L1']) / prod['L1'] * 100
        g23 = (prod['L3'] - prod['L2']) / prod['L2'] * 100 if prod['L2'] > 0 else 0
        axB.text(0.97, 0.97, f'L1→L2: +{g12:.0f}%\nL2→L3: +{g23:.0f}%',
                 transform=axB.transAxes, fontsize=10, ha='right', va='top',
                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.85))

    fig.suptitle('Figure 1: Development of Productivity Across Proficiency Levels',
                 fontsize=15, fontweight='bold', y=1.0)
    plt.tight_layout()
    save_figure(fig, output_dir, 'graph3_productivity_slope')
    plt.close()


def generate_functions_radar(features, output_dir):
    """Graph 4: Functions radar chart by level."""
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))

    categories = FUNCTIONS
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    # Plot each level
    for level in LEVELS:
        values = features['function_by_level'].loc[level].values.tolist()
        total = sum(values)
        if total > 0:
            values = [v / total * 100 for v in values]
        values += values[:1]

        ax.plot(angles, values, 'o-', linewidth=2, label=f'{level} ({LEVEL_LABELS[level]})',
                color=LEVEL_COLORS[level])
        ax.fill(angles, values, alpha=0.1, color=LEVEL_COLORS[level])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=11)
    ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.0))

    plt.title('Functional Distribution by Proficiency Level\n(Correct Usage Only)',
              fontsize=14, fontweight='bold', y=1.08)
    save_figure(fig, output_dir, 'graph4_functions_radar')
    plt.close()


def generate_semantics_stacked(features, output_dir):
    """Graph 5: Stacked bar chart for semantic categories by level."""
    if 'semantics_by_level_pct' not in features:
        print("⚠ Skipping Graph 5: No semantics data")
        return

    fig, ax = plt.subplots(figsize=(12, 8))

    sem_pct = features['semantics_by_level_pct']

    # Get all semantic categories
    categories = sem_pct.columns.tolist()

    # Create stacked bars
    bottom = np.zeros(len(LEVELS))

    for cat in categories:
        color = SEMANTIC_COLORS.get(cat, '#95a5a6')
        values = sem_pct[cat].values
        ax.bar(LEVELS, values, bottom=bottom, label=cat, color=color,
               edgecolor='white', linewidth=0.5)
        bottom += values

    ax.set_xlabel('Proficiency Level', fontsize=12)
    ax.set_ylabel('Percentage (%)', fontsize=12)
    ax.set_title('Semantic Category Distribution by Level\n(Correct Usage Only)', fontsize=14, fontweight='bold')
    ax.legend(title='Semantic Category', bbox_to_anchor=(1.02, 1), loc='upper left')
    ax.set_ylim(0, 100)

    plt.tight_layout()
    save_figure(fig, output_dir, 'graph5_semantics_stacked')
    plt.close()


def generate_accessibility_area(df, features, output_dir):
    """Graph 6: Area chart for accessibility distribution."""
    fig, ax = plt.subplots(figsize=(12, 7))

    # Create KDE for each level
    x_range = np.linspace(0, 7, 200)

    for level in reversed(LEVELS):  # Reverse for proper layering
        level_data = df[df['Level'] == level]['Accessibility'].dropna()
        if len(level_data) < 2:
            continue

        kde = stats.gaussian_kde(level_data)
        y = kde(x_range)

        ax.fill_between(x_range, y, alpha=0.4, color=LEVEL_COLORS[level],
                        label=f'{LEVEL_LABELS[level]} (μ={level_data.mean():.2f})')
        ax.plot(x_range, y, color=LEVEL_COLORS[level], linewidth=2)

    ax.set_xlabel('Accessibility Score', fontsize=12)
    ax.set_ylabel('Density', fontsize=12)
    ax.set_title('Accessibility Score Distribution by Level\n(Correct Usage Only)', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(alpha=0.3)

    save_figure(fig, output_dir, 'graph6_accessibility_area')
    plt.close()


def generate_error_rates_bullet(features, output_dir):
    """Graph 7: Bullet chart for error rates by level."""
    if 'error_rate_by_level' not in features:
        print("⚠ Skipping Graph 7: No error data")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    error_rates = features['error_rate_by_level']

    # Target and comparison values
    overall_rate = error_rates.mean()

    y_positions = np.arange(len(LEVELS))

    for idx, level in enumerate(LEVELS):
        rate = error_rates[level]
        color = LEVEL_COLORS[level]

        # Background bar (target zone)
        ax.barh(idx, overall_rate * 1.5, height=0.6, color='lightgray', alpha=0.5)

        # Actual bar
        ax.barh(idx, rate, height=0.4, color=color, edgecolor='black')

        # Value annotation
        ax.text(rate + 0.5, idx, f'{rate:.1f}%', va='center', fontsize=11, fontweight='bold')

    # Target line
    ax.axvline(overall_rate, color='red', linestyle='--', linewidth=2,
               label=f'Mean: {overall_rate:.1f}%')

    ax.set_yticks(y_positions)
    ax.set_yticklabels([f'{l} ({LEVEL_LABELS[l]})' for l in LEVELS], fontsize=11)
    ax.set_xlabel('Error Rate (%)', fontsize=12)
    ax.set_title('Error Rate by Proficiency Level', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(axis='x', alpha=0.3)

    save_figure(fig, output_dir, 'graph7_error_rates_bullet')
    plt.close()


def generate_error_types_heatmap(features, output_dir):
    """Graph 8: Error types heatmap by level."""
    if 'error_type_by_level' not in features:
        print("⚠ Skipping Graph 8: No error type data")
        return

    fig, ax = plt.subplots(figsize=(12, 6))

    data = features['error_type_by_level']

    # Normalize by row (level)
    row_sums = data.sum(axis=1)
    data_norm = data.div(row_sums, axis=0) * 100

    im = ax.imshow(data_norm.values, aspect='auto', cmap='YlOrRd')

    ax.set_xticks(np.arange(len(ERROR_TAXONOMY)))
    ax.set_yticks(np.arange(len(LEVELS)))
    ax.set_xticklabels(ERROR_TAXONOMY, rotation=45, ha='right', fontsize=10)
    ax.set_yticklabels([f'{l} ({LEVEL_LABELS[l]})' for l in LEVELS], fontsize=11)

    # Add values
    for i in range(len(LEVELS)):
        for j in range(len(ERROR_TAXONOMY)):
            raw = data.iloc[i, j]
            pct = data_norm.iloc[i, j]
            ax.text(j, i, f'{raw}\n({pct:.1f}%)', ha='center', va='center', fontsize=9)

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Percentage within Level (%)', fontsize=11)

    plt.title('Error Type Distribution by Proficiency Level\n(5-Category Taxonomy)',
              fontsize=14, fontweight='bold')
    plt.tight_layout()
    save_figure(fig, output_dir, 'graph8_error_types_heatmap')
    plt.close()


def generate_error_trajectories(features, output_dir):
    """Figure 4 (manuscript): error-type developmental trajectories.

    Each error type plotted as a SHARE of codable errors within each level
    (same denominator as Table 8 / the heatmap: composition, not a per-100k
    rate). The adjacent-level change(s) that survive Benjamini-Hochberg
    correction are drawn bold and starred; the omnibus chi-square is shown as a
    subtitle. Fully data-driven: counts and significance are recomputed from
    features['error_type_by_level'].
    """
    if 'error_type_by_level' not in features:
        print("\u26a0 Skipping Figure 4 (trajectories): No error type data")
        return

    counts = features['error_type_by_level'].reindex(index=LEVELS,
                                                     columns=ERROR_TAXONOMY).fillna(0)
    row_tot = counts.sum(axis=1)
    pct = counts.div(row_tot, axis=0) * 100  # % of codable errors within level

    # Omnibus chi-square on the level x type counts table
    try:
        chi2, p_omni, dof, _ = chi2_contingency(counts.values)
        n_tot = counts.values.sum()
        k = min(counts.shape) - 1
        cv = np.sqrt(chi2 / (n_tot * k)) if n_tot and k else float('nan')
        omni = (r'Distribution differs across levels: '
                r'$\chi^2$(%d) = %.2f, $p$ = %.3f, $V$ = %.3f' % (dof, chi2, p_omni, cv))
    except Exception:
        omni = ''

    # Per-type adjacent-level LLR (composition basis), BH-corrected; flag sig segments
    transitions = [(0, 1), (1, 2)]  # L1->L2, L2->L3
    pvals, keys = [], []
    for etype in ERROR_TAXONOMY:
        for a, b in transitions:
            res = calculate_llr(counts.iloc[b][etype], counts.iloc[a][etype],
                                row_tot.iloc[b], row_tot.iloc[a])
            pvals.append(res['p'])
            keys.append((etype, a, b))
    padj = apply_bh_correction(pvals)
    sig = {k: pa < 0.05 for k, pa in zip(keys, padj)}
    sig_labels = [f'{e} {LEVELS[a]}\u2192{LEVELS[b]}'
                  for (e, a, b), s in sig.items() if s]

    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    x = list(range(len(LEVELS)))
    for etype in ERROR_TAXONOMY:
        y = [pct.iloc[i][etype] for i in x]
        color = ERROR_COLORS.get(etype, '#555555')
        for a, b in transitions:
            on = sig.get((etype, a, b))
            ax.plot([x[a], x[b]], [y[a], y[b]], color=color,
                    linewidth=4.2 if on else 2.4, zorder=4 if on else 3)
            if on:
                mx, my = (x[a] + x[b]) / 2, (y[a] + y[b]) / 2
                ax.annotate('*', xy=(mx, my), xytext=(mx - 0.05, my + 1.3),
                            fontsize=22, color=color, fontweight='bold',
                            ha='center', zorder=6)
        ax.plot(x, y, marker='o', markersize=7, linestyle='none', color=color,
                markerfacecolor='white', markeredgewidth=2, markeredgecolor=color, zorder=5)
        ax.annotate(etype, xy=(x[-1], y[-1]), xytext=(x[-1] + 0.08, y[-1]),
                    va='center', ha='left', fontsize=10.5, color=color, fontweight='bold')
        for xi, yi in zip(x, y):
            ax.annotate(f'{yi:.1f}', xy=(xi, yi), xytext=(0, 8),
                        textcoords='offset points', ha='center', fontsize=8.5, color=color)

    ax.set_xticks(x)
    ax.set_xticklabels([f'{l}\n({LEVEL_LABELS[l]})' for l in LEVELS], fontsize=10.5)
    ax.set_xlim(-0.25, len(LEVELS) - 1 + 0.95)
    ax.set_ylim(0, max(55, pct.values.max() * 1.15))
    ax.set_ylabel('% of codable errors at each level', fontsize=11)
    ax.set_title('Developmental trajectories of error types across proficiency',
                 fontsize=12.5, pad=26 if omni else 12)
    if omni:
        ax.text(0.5, 1.035, omni, transform=ax.transAxes, ha='center',
                fontsize=9.5, color='#444')
    ax.grid(axis='y', linestyle=':', alpha=0.5)
    for s in ['top', 'right']:
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    if sig_labels:
        note = ('Bold segment(s) marked * : only adjacent-level change(s) significant after '
                'Benjamini\u2013Hochberg correction (' + '; '.join(sig_labels)
                + '). All other transitions n.s.')
    else:
        note = ('No individual adjacent-level change survives Benjamini\u2013Hochberg '
                'correction; see the omnibus test above.')
    fig.text(0.02, -0.02, note, fontsize=8.3, color='#555', ha='left', va='top', wrap=True)
    plt.tight_layout()
    save_figure(fig, output_dir, 'Figure4_error_trajectories')
    plt.close()


def generate_error_function_graph(features, stats_results, output_dir):
    """Graph 9: Error × Function with statistical analysis."""
    if 'error_function_matrix' not in features:
        print("⚠ Skipping Graph 9: No error-function data")
        return

    matrix = features['error_function_matrix']

    # Get statistics
    chi2_result = stats_results.get('error_function', {}).get('chi2', {})
    std_residuals = stats_results.get('error_function', {}).get('std_residuals', None)

    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)

    # 9a: Raw counts heatmap
    ax1 = fig.add_subplot(gs[0, 0])
    im1 = ax1.imshow(matrix.values, aspect='auto', cmap='Blues')
    ax1.set_xticks(np.arange(len(FUNCTIONS)))
    ax1.set_yticks(np.arange(len(ERROR_TAXONOMY)))
    ax1.set_xticklabels(FUNCTIONS, fontsize=10)
    ax1.set_yticklabels(ERROR_TAXONOMY, fontsize=10)
    for i in range(len(ERROR_TAXONOMY)):
        for j in range(len(FUNCTIONS)):
            ax1.text(j, i, str(int(matrix.iloc[i, j])), ha='center', va='center', fontsize=9)
    plt.colorbar(im1, ax=ax1, label='Count')
    ax1.set_title('(a) Error × Function: Raw Counts', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Constructional Function')
    ax1.set_ylabel('Error Type')

    # 9b: Standardized residuals heatmap
    ax2 = fig.add_subplot(gs[0, 1])
    if std_residuals is not None:
        im2 = ax2.imshow(std_residuals, aspect='auto', cmap='RdBu_r', vmin=-4, vmax=4)
        ax2.set_xticks(np.arange(len(FUNCTIONS)))
        ax2.set_yticks(np.arange(len(ERROR_TAXONOMY)))
        ax2.set_xticklabels(FUNCTIONS, fontsize=10)
        ax2.set_yticklabels(ERROR_TAXONOMY, fontsize=10)

        for i in range(len(ERROR_TAXONOMY)):
            for j in range(len(FUNCTIONS)):
                val = std_residuals[i, j]
                sig = "***" if abs(val) > 3.29 else ("**" if abs(val) > 2.58 else ("*" if abs(val) > 1.96 else ""))
                ax2.text(j, i, f'{val:.2f}{sig}', ha='center', va='center', fontsize=8)

        cbar2 = plt.colorbar(im2, ax=ax2)
        cbar2.set_label('Standardized Residual')
    ax2.set_title('(b) Standardized Residuals\n(Pearson)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Constructional Function')
    ax2.set_ylabel('Error Type')

    # 9c: Bar chart by error type
    ax3 = fig.add_subplot(gs[1, 0])
    error_totals = matrix.sum(axis=1)
    colors = [ERROR_COLORS.get(et, 'gray') for et in ERROR_TAXONOMY]
    bars = ax3.barh(ERROR_TAXONOMY, error_totals, color=colors, edgecolor='black')
    ax3.set_xlabel('Count')
    ax3.set_title('(c) Total Errors by Type', fontsize=12, fontweight='bold')
    for bar, count in zip(bars, error_totals):
        ax3.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                 str(int(count)), va='center', fontsize=9)

    # 9d: Statistics summary
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis('off')

    stats_text = "Statistical Analysis Summary\n"
    stats_text += "=" * 40 + "\n\n"

    if chi2_result:
        stats_text += f"Chi-Square Test of Independence:\n"
        stats_text += f"  χ²({chi2_result.get('df', 'N/A')}) = {chi2_result.get('chi2', 0):.2f}\n"
        stats_text += f"  {format_p(chi2_result.get('p', 1))}\n"
        stats_text += f"  Cramér's V = {chi2_result.get('cramers_v', 0):.3f} ({chi2_result.get('effect_size', 'N/A')})\n\n"

    if std_residuals is not None:
        stats_text += "Significant Associations (|z| > 1.96):\n"
        for i, et in enumerate(ERROR_TAXONOMY):
            for j, func in enumerate(FUNCTIONS):
                if abs(std_residuals[i, j]) > 1.96:
                    direction = "+" if std_residuals[i, j] > 0 else "−"
                    sig = "***" if abs(std_residuals[i, j]) > 3.29 else (
                        "**" if abs(std_residuals[i, j]) > 2.58 else "*")
                    stats_text += f"  {et} × {func}: z={std_residuals[i, j]:.2f}{sig}\n"

    stats_text += "\n" + "-" * 40 + "\n"
    stats_text += "Significance: * p<.05, ** p<.01, *** p<.001"

    ax4.text(0.05, 0.95, stats_text, transform=ax4.transAxes, fontsize=10,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    plt.suptitle('Graph 9: Error Type × Constructional Function Analysis', fontsize=14, fontweight='bold', y=0.98)
    save_figure(fig, output_dir, 'graph9_error_function_analysis')
    plt.close()


def generate_correspondence_analysis(features, output_dir):
    """Graph 9b: Correspondence Analysis visualization."""
    if 'error_function_matrix' not in features:
        return

    matrix = features['error_function_matrix'].values

    # Correspondence Analysis
    row_totals = matrix.sum(axis=1, keepdims=True)
    col_totals = matrix.sum(axis=0, keepdims=True)
    total = matrix.sum()

    # Avoid division by zero
    row_totals = np.where(row_totals == 0, 1, row_totals)
    col_totals = np.where(col_totals == 0, 1, col_totals)

    expected = row_totals @ col_totals / total
    std_residuals = (matrix - expected) / np.sqrt(expected)
    std_residuals = np.nan_to_num(std_residuals, nan=0.0, posinf=0.0, neginf=0.0)

    # SVD
    try:
        U, s, Vt = np.linalg.svd(std_residuals, full_matrices=False)
    except:
        print("⚠ SVD failed for correspondence analysis")
        return

    # Calculate coordinates
    row_weights = np.sqrt(row_totals.flatten() / total)
    col_weights = np.sqrt(col_totals.flatten() / total)

    row_weights = np.where(row_weights == 0, 1, row_weights)
    col_weights = np.where(col_weights == 0, 1, col_weights)

    row_coords = (U[:, :2] * s[:2]) / row_weights[:, np.newaxis]
    col_coords = (Vt[:2, :].T * s[:2]) / col_weights[:, np.newaxis]

    total_inertia = np.sum(s ** 2)
    if total_inertia > 0:
        dim1_inertia = (s[0] ** 2 / total_inertia) * 100
        dim2_inertia = (s[1] ** 2 / total_inertia) * 100
    else:
        dim1_inertia = dim2_inertia = 0

    # Plot
    fig, ax = plt.subplots(figsize=(12, 10))

    error_labels = ERROR_TAXONOMY
    func_labels = FUNCTIONS

    # Plot error types (rows)
    for i, label in enumerate(error_labels):
        ax.scatter(row_coords[i, 0], row_coords[i, 1], s=150, marker='s',
                   color=ERROR_COLORS.get(label, 'gray'), edgecolor='black', linewidth=1.5, zorder=3)
        ax.annotate(label, (row_coords[i, 0], row_coords[i, 1]),
                    xytext=(8, 8), textcoords='offset points', fontsize=10, fontweight='bold')

    # Plot functions (columns)
    for i, label in enumerate(func_labels):
        ax.scatter(col_coords[i, 0], col_coords[i, 1], s=150, marker='o',
                   color=FUNCTION_COLORS.get(label, 'gray'), edgecolor='black', linewidth=1.5, zorder=3)
        ax.annotate(label, (col_coords[i, 0], col_coords[i, 1]),
                    xytext=(8, -12), textcoords='offset points', fontsize=10, fontweight='bold')

    # Reference lines
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    ax.axvline(x=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)

    ax.set_xlabel(f'Dimension 1 ({dim1_inertia:.1f}% inertia)', fontsize=12)
    ax.set_ylabel(f'Dimension 2 ({dim2_inertia:.1f}% inertia)', fontsize=12)
    ax.set_title('Correspondence Analysis: Error Type × Constructional Function\n'
                 f'(Total variance explained: {dim1_inertia + dim2_inertia:.1f}%)',
                 fontsize=14, fontweight='bold')

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor='gray', edgecolor='black', label='Error Types (■)'),
        mpatches.Patch(facecolor='gray', edgecolor='black', label='Functions (●)')
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    save_figure(fig, output_dir, 'graph9b_correspondence_analysis')
    plt.close()


def generate_all_graphs(df, df_correct, features, stats_results, output_dir):
    """Generate all 9 graphs."""
    print("\n" + "=" * 70)
    print("GENERATING GRAPHS (1-9)")
    print("=" * 70 + "\n")

    # Graph 1: Summary Dashboard
    generate_summary_dashboard(features, stats_results, output_dir)

    # Graph 2: Distribution Analysis
    generate_normality_assessment(df, features, output_dir)

    # Figure 1: Productivity divergence (indexed-growth line chart)
    generate_productivity_divergence(features, output_dir)

    # Figure 4: Four-dimension summary (2x2 small-multiple)
    generate_four_dimension_summary(features, output_dir)

    # Graph 3: Productivity Slope (dual-panel; supplementary)
    generate_productivity_slope(features, output_dir)

    # Graph 4: Functions Radar
    generate_functions_radar(features, output_dir)

    # Graph 5: Semantics Stacked
    generate_semantics_stacked(features, output_dir)

    # Graph 6: Accessibility Area (uses correct usage only)
    generate_accessibility_area(df_correct, features, output_dir)

    # Graph 7: Error Rates Bullet
    generate_error_rates_bullet(features, output_dir)

    # Graph 8: Error Types Heatmap
    generate_error_types_heatmap(features, output_dir)

    # Figure 4 (manuscript): error-type trajectories (share of codable errors)
    generate_error_trajectories(features, output_dir)

    # Graph 9: Error × Function Analysis
    generate_error_function_graph(features, stats_results, output_dir)

    # Graph 9b: Correspondence Analysis
    generate_correspondence_analysis(features, output_dir)

    print("\n" + "=" * 70)
    print("ALL 9 GRAPHS GENERATED SUCCESSFULLY")
    print("=" * 70)


# ============================================================================
# COMPREHENSIVE REPORT GENERATION
# ============================================================================

def generate_comprehensive_report(df, df_correct, df_errors, features, stats_results, output_dir):
    """Generate comprehensive analysis report with all statistics."""

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = os.path.join(output_dir, f'comprehensive_analysis_report_{timestamp}.txt')

    lines = []

    def add(text=""):
        lines.append(text)

    def section(title):
        add()
        add("=" * 70)
        add(title)
        add("=" * 70)
        add()

    def subsection(title):
        add()
        add("-" * 50)
        add(title)
        add("-" * 50)
        add()

    # Header
    add("=" * 70)
    add("L2 CHINESE 对-CONSTRUCTION: COMPREHENSIVE STATISTICAL REPORT")
    add("=" * 70)
    add()
    add(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    add(f"Script Version: v19 (5-category taxonomy, no Uncodable; adds Figure 1 productivity divergence)")
    add()

    # Methodology note
    section("STATISTICAL METHODOLOGY")
    add("This analysis employs a comprehensive statistical framework based on")
    add("corpus linguistics standards (Dunning 1993; Rayson & Garside 2000):")
    add()
    add("  Overall Distribution Tests:")
    add("    - Chi-square test of independence (contingency tables)")
    add("    - Effect size: Cramér's V")
    add()
    add("  Pairwise Comparisons:")
    add("    - Log-Likelihood Ratio (G²/LLR)")
    add("    - Effect size: Log Ratio (log₂ of normalised frequency ratio)")
    add()
    add("  CRITICAL METHODOLOGICAL NOTE:")
    add("    - Sections 4.1-4.3: Analyse CORRECT USAGE ONLY (errors filtered)")
    add("    - Section 4.4: Analyses error patterns specifically")
    add("    - This ensures productivity measures reflect acquired competence,")
    add("      not merely attempted usage.")
    add()
    add("  Effect Size Interpretation (Cramér's V):")
    add("    - < 0.10: Negligible")
    add("    - 0.10-0.29: Small")
    add("    - 0.30-0.49: Medium")
    add("    - ≥ 0.50: Large")

    # Data overview
    section("1. DATA OVERVIEW")
    add(f"Total instances: {len(df)}")
    add(f"Correct usage: {len(df_correct)} ({len(df_correct) / len(df) * 100:.1f}%)")
    add(f"Error instances: {len(df_errors)} ({len(df_errors) / len(df) * 100:.1f}%)")
    add()
    add("Distribution by Level:")
    add(f"  {'Level':<10} {'Total':>10} {'Correct':>10} {'Errors':>10} {'Error Rate':>12}")
    add("  " + "-" * 54)
    for level in LEVELS:
        total = features['level_counts'][level]
        correct = features['level_counts_correct'][level]
        errors = total - correct
        rate = (errors / total * 100) if total > 0 else 0
        add(f"  {level:<10} {total:>10} {correct:>10} {errors:>10} {rate:>11.1f}%")

    # 4.1 Productivity
    section("4.1 PRODUCTIVITY (Correct Usage Only)")

    if 'productivity' in stats_results:
        p = stats_results['productivity']

        add("Normalised Frequency (per 100,000 words):")
        for level in LEVELS:
            freq = p['freq_100k'][level]
            count = features['level_counts_correct'][level]
            add(f"  {level} ({LEVEL_LABELS[level]}): {count} instances = {freq:.2f} per 100K")

        subsection("Pairwise Comparisons (Log-Likelihood Ratio)")
        add(f"  L1 → L2:")
        llr = p['llr_L1_L2']
        add(f"    {p['freq_100k']['L1']:.2f} → {p['freq_100k']['L2']:.2f} per 100K")
        add(f"    G² = {llr['LLR']:.2f}, {format_p(llr['p'])}, Log Ratio = {llr['log_ratio']:+.2f} {llr['sig']}")
        add()
        add(f"  L2 → L3:")
        llr = p['llr_L2_L3']
        add(f"    {p['freq_100k']['L2']:.2f} → {p['freq_100k']['L3']:.2f} per 100K")
        add(f"    G² = {llr['LLR']:.2f}, {format_p(llr['p'])}, Log Ratio = {llr['log_ratio']:+.2f} {llr['sig']}")

    # 4.2 Functions
    section("4.2 FUNCTIONAL COMPLEXITY (Correct Usage Only)")

    if 'functions' in stats_results:
        f = stats_results['functions']
        chi2 = f['chi2']

        add("Overall Distribution Test (Level × Function):")
        add(f"  χ²({chi2['df']}) = {chi2['chi2']:.2f}, {format_p(chi2['p'])}")
        add(f"  Cramér's V = {chi2['cramers_v']:.3f} ({chi2['effect_size']} effect)")

        subsection("Pairwise Comparisons by Function (LLR)")
        add(f"  {'Function':<10} {'L1→L2 LogR':>12} {'Sig':>6} {'L2→L3 LogR':>12} {'Sig':>6}")
        add("  " + "-" * 48)
        for func in FUNCTIONS:
            lr1 = f['llr_L1_L2'][func]['log_ratio']
            s1 = f['llr_L1_L2'][func]['sig']
            lr2 = f['llr_L2_L3'][func]['log_ratio']
            s2 = f['llr_L2_L3'][func]['sig']
            add(f"  {func:<10} {lr1:>+12.2f} {s1:>6} {lr2:>+12.2f} {s2:>6}")

    # 4.3.1 Semantics
    if 'semantics' in stats_results:
        section("4.3.1 SEMANTIC CLASSES (Correct Usage Only)")
        s = stats_results['semantics']
        chi2 = s['chi2']

        add("Overall Distribution Test (Level × Semantics):")
        add(f"  χ²({chi2['df']}) = {chi2['chi2']:.2f}, {format_p(chi2['p'])}")
        add(f"  Cramér's V = {chi2['cramers_v']:.3f} ({chi2['effect_size']} effect)")

    # 4.3.2 Accessibility
    if 'accessibility' in stats_results:
        section("4.3.2 ACCESSIBILITY (Correct Usage Only)")
        a = stats_results['accessibility']
        chi2 = a['chi2']

        add("Overall Distribution Test (Level × Accessibility):")
        add(f"  χ²({chi2['df']}) = {chi2['chi2']:.2f}, {format_p(chi2['p'])}")
        add(f"  Cramér's V = {chi2['cramers_v']:.3f} ({chi2['effect_size']} effect)")

    # 4.4 Errors
    if 'errors' in stats_results:
        section("4.4 ERROR ANALYSIS")
        e = stats_results['errors']

        subsection("4.4.1 Error Rate Comparison")
        chi2 = e['chi2_rate']
        add(f"  χ²({chi2['df']}) = {chi2['chi2']:.2f}, {format_p(chi2['p'])}")
        add(f"  Cramér's V = {chi2['cramers_v']:.3f} ({chi2['effect_size']} effect)")

        subsection("4.4.2 Error Type Distribution")
        chi2 = e['chi2_type']
        add(f"  χ²({chi2['df']}) = {chi2['chi2']:.2f}, {format_p(chi2['p'])}")
        add(f"  Cramér's V = {chi2['cramers_v']:.3f} ({chi2['effect_size']} effect)")

        if e.get('llr_L1_L2'):
            subsection("4.4.3 Error Type Pairwise Comparisons (LLR)")
            add(f"  {'Error Type':<25} {'L1→L2 LogR':>12} {'Sig':>6} {'L2→L3 LogR':>12} {'Sig':>6}")
            add("  " + "-" * 63)
            for et in ERROR_TAXONOMY:
                if et in e['llr_L1_L2']:
                    lr1 = e['llr_L1_L2'][et]['log_ratio']
                    s1 = e['llr_L1_L2'][et]['sig']
                    lr2 = e['llr_L2_L3'][et]['log_ratio']
                    s2 = e['llr_L2_L3'][et]['sig']
                    add(f"  {et:<25} {lr1:>+12.2f} {s1:>6} {lr2:>+12.2f} {s2:>6}")

    # Error × Function
    if 'error_function' in stats_results:
        section("4.5 ERROR × FUNCTION ASSOCIATION")
        ef = stats_results['error_function']
        chi2 = ef['chi2']

        add("Chi-Square Test of Independence:")
        add(f"  χ²({chi2['df']}) = {chi2['chi2']:.2f}, {format_p(chi2['p'])}")
        add(f"  Cramér's V = {chi2['cramers_v']:.3f} ({chi2['effect_size']} effect)")

        subsection("Significant Associations (Standardized Residuals)")
        std_res = ef['std_residuals']
        add(f"  {'Error Type':<25} {'Function':<10} {'z':>8} {'Sig':>6}")
        add("  " + "-" * 51)

        for i, et in enumerate(ERROR_TAXONOMY):
            for j, func in enumerate(FUNCTIONS):
                z = std_res[i, j]
                if abs(z) > 1.96:
                    sig = "***" if abs(z) > 3.29 else ("**" if abs(z) > 2.58 else "*")
                    add(f"  {et:<25} {func:<10} {z:>+8.2f} {sig:>6}")

    # Intended-Function distribution (Non-dui errors) + Uncodable note
    if 'intended_function_dist' in features:
        section("4.6 INTENDED FUNCTION OF NON-DUI-CONSTRUCTION ERRORS")
        intended = features['intended_function_dist']
        total_nd = int(intended.sum())
        add(f"Non-dui-construction errors with an identified target function: {total_nd}")
        add()
        add(f"  {'Intended Function':<18} {'n':>5} {'%':>7}")
        add("  " + "-" * 32)
        for fn in INTENDED_FUNCTIONS:
            n = int(intended[fn])
            if n > 0:
                pct = n / total_nd * 100 if total_nd > 0 else 0
                add(f"  {fn:<18} {n:>5} {pct:>6.1f}%")
        add()
        add(f"Uncodable (uninterpretable) errors, excluded from error-type")
        add(f"analysis but counted in the overall error rate: {features.get('n_uncodable', 0)}")
        add(f"Codable errors analysed in 4.4.2: {features.get('total_errors_codable', 0)}")

    # Footer
    add()
    add("=" * 70)
    add("END OF REPORT")
    add("=" * 70)

    # Write report
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"\n✓ Comprehensive report saved: {report_path}")
    return report_path


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function."""
    print("\n" + "=" * 70)
    print("L2 CHINESE 对-CONSTRUCTION ANALYSIS v19")
    print("Comprehensive Statistical Framework")
    print("=" * 70 + "\n")

    # Load data (v19: single combined workbook)
    df, df_correct, df_errors = load_data_combined(COMBINED_FILE)

    # Extract features
    features = extract_features(df, df_correct, df_errors)

    # Compute comprehensive statistics
    stats_results = compute_comprehensive_statistics(df, df_correct, df_errors, features)

    # Generate graphs
    generate_all_graphs(df, df_correct, features, stats_results, OUTPUT_DIR)

    # Generate comprehensive report
    report_path = generate_comprehensive_report(df, df_correct, df_errors, features, stats_results, OUTPUT_DIR)

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\nOutputs saved to: {OUTPUT_DIR}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()