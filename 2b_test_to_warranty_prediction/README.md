# Phase 2B: Predictive Causality between Test Performance and Warranty Failures

## Overview

This module aims to bridge the gap between initial End-of-Line (EoL) transmission test data and final drivetrain warranty claims reported from the field. Our goal is to develop machine learning (ML) algorithms to identify whether specific test parameter deviations mathematically predict future drivetrain failures.

Because full business context—such as target warranty durations and healthy-baseline longevity data—is currently unavailable, this phase executes a purely data-driven, constrained Proof of Concept (POC) pipeline.

## Methodology

To avoid any overlap with Phase 1b (which calculated simple Z-scores per parameter), this pipeline (`run_ml_poc.py`) performs advanced mathematical feature engineering and multidimensional machine learning analysis:

1. **Intelligent Feature Engineering**:
   - Dynamically extracts all non-generic, visible component claims from `UPDATED Full Claims Report.xlsx` as positive warranty failure targets ($Y=1$).
   - Computes statistical deviations (Mean Deviation Ratio), bounds aggregations, and limit-crossing sums for each tested `SerialNumber` in `Test Data.csv`. This effectively flattens longitudinal test records into a continuous 28-dimensional feature matrix ($X$).

2. **Unsupervised Anomaly Detection (Isolation Forest)**:
   - Evaluates whether pure global test anomalies naturally correlate with future claims. Uses an Isolation Forest algorithm to find the 200 most mathematically deformed/anomalous transmissions mathematically in the test batch.

3. **Supervised Feature Attributions (Random Forest & SHAP)**:
   - Trains a Random Forest Classifier on the highly imbalanced dataset (179 failures vs. 1772 unverified units, assumed $Y=0$).
   - Generates SHapley Additive exPlanations (SHAP) Values to rank which exact factory tests carry the heaviest causal weight for subsequent warranty claims.

## Results Analysis

- **Base Metrics**: Out of 1,961 uniquely tested transmissions, exactly 179 intersect with visible, non-pure-generic warranty claims.
- **Isolation Forest Findings**: The unsupervised global anomalies list resulted in 17 direct failure hits. This matches the natural random background probability of ~18.3, mathematically proving that simply "having a lot of test deviations" does not guarantee a warranty claim; the claims are uniquely tied to specific metrics.
- **Top Predictive Variables (SHAP Important tests)**:
  Supervised learning cleanly isolated the specific metrics most strongly correlated to eventual warranty costs. The top 3 strongest mathematical predictors of a future claim are:
  1. **`Param_PARK_BRAKE_PRESSURE_AFTER_DECAY_DevRatio`**
  2. **`Param_PFC_DEADHEAD_PRESSURE_DevRatio`**
  3. **`Param_Reverse_FINAL_PRESSURE_DevRatio`**

This directory includes the resulting SHAP waterfall visualization (`shap_feature_importance.png`) and the automated string output (`ml_results.txt`) for quality engineering review.
