import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import IsolationForest, RandomForestClassifier
import shap

def build_ml_pipeline():
    print("Loading datasets...")
    # Load Test Data
    df_test = pd.read_csv('/Users/yizhengjiang/Desktop/Git/f2025_s2026_wl_cnh_dataengineering/2b_test_to_warranty_prediction/original_records/Test Data.csv')
    
    # Load claims data (to establish the 179 target SNs)
    # We will compute the visible SNs dynamically to be 100% accurate
    claims_file = '/Users/yizhengjiang/Desktop/Git/f2025_s2026_wl_cnh_dataengineering/2b_test_to_warranty_prediction/original_records/UPDATED Full Claims Report.xlsx'
    
    # Load clone to find visible rows
    import openpyxl
    wb = openpyxl.load_workbook(claims_file, data_only=True)
    ws = wb['Paid']
    df_clone = pd.read_excel(claims_file, sheet_name='Paid', header=1)
    
    visible_indices = []
    for i in range(len(df_clone)):
        excel_row = i + 3
        if not ws.row_dimensions[excel_row].hidden:
            visible_indices.append(i)
            
    df_visible = df_clone.loc[visible_indices].copy()
    
    # Exclude PURE_GENERIC (Using simpler representation of 2a_analysis tokenization logic)
    import re
    generic_keywords = {'O-RING', 'ORING', 'BOLT', 'SCREW', 'WASHER', 'NUT', 'PIN', 'SEAL', 'GASKET', 'TIE', 'CIRCLIP', 'RING'}
    def is_pure_generic(desc):
        if pd.isna(desc): return False
        clean_desc = re.sub(r'[^A-Z0-9\s]', ' ', str(desc).upper())
        tokens = set(clean_desc.split())
        return bool(tokens.intersection(generic_keywords)) and not bool(tokens.intersection({'CAB', 'FRAME', 'PTO', 'HYDRAULIC', 'ENGINE', 'ROOF', 'AXLE', 'PUMP', 'DOOR', 'GLASS', 'WHEEL', 'SEAT', 'STEERING', 'TRANSMISSION', 'HOSE', 'VALVE', 'FILTER', 'CYLINDER'}))
    
    df_visible['pure_generic'] = df_visible['Causal Part Descriprion'].apply(is_pure_generic)
    df_visible = df_visible[~df_visible['pure_generic']]
    
    # ==========================
    # TRUE DRIVETRAIN DEFINITION
    # ==========================
    # 1. Load transmission related components
    df_components = pd.read_excel(claims_file, sheet_name='Unique Component Descriptions')
    tx_components = set(df_components[df_components['Is Transmission Related'] == 1]['Component Description'].dropna())

    # 2. Filter true drivetrain failures (Functional, Severe, Internal Leaks, Noise)
    true_failure_codes = {104.0, 214.0, 213.0, 413.0, 551.0, 621.0, 1199.0, 124.0, 1010.0, 47.0, 50.0, 125.0, 121.0, 702.0, 202.0, 221.0}
    
    df_drivetrain = df_visible[
        (df_visible['Component Description'].isin(tx_components)) & 
        (df_visible['Failure Index Code'].isin(true_failure_codes))
    ].copy()
    
    # 3. Extract Warranty & Usage Features for these specific failures
    df_drivetrain['Base Warranty Start Date'] = pd.to_datetime(df_drivetrain['Base Warranty Start Date'], errors='coerce')
    df_drivetrain['Failure Date'] = pd.to_datetime(df_drivetrain['Failure Date'], errors='coerce')
    df_drivetrain['Time_To_Failure_Days'] = (df_drivetrain['Failure Date'] - df_drivetrain['Base Warranty Start Date']).dt.days
    df_drivetrain['Usage_Hours'] = pd.to_numeric(df_drivetrain['Worked Hours\\ Mileage km'], errors='coerce')
    
    # If a transmission failed multiple times under true drivetrain criteria, take the earliest one
    df_drivetrain['Transmission Number'] = df_drivetrain['Transmission Number'].astype(str).str.strip().str.upper()
    df_drivetrain_unique = df_drivetrain.sort_values('Time_To_Failure_Days').drop_duplicates(subset=['Transmission Number'])
    
    target_sns = set(df_drivetrain_unique['Transmission Number'].dropna().unique())
    
    print(f"Target True Drivetrain Failures (1s) count: {len(target_sns)}")
    
    # ==========================
    # 1. Feature Engineering
    # ==========================
    print("Extracting features from Test Data...")
    df_test['SerialNumber'] = df_test['SerialNumber'].astype(str).str.strip().str.upper()
    
    # Convert value to numeric, coercing errors
    df_test['Value'] = pd.to_numeric(df_test['Value'].astype(str).str.replace(',', ''), errors='coerce')
    df_test['Minimum'] = pd.to_numeric(df_test['Minimum'].astype(str).str.replace(',', ''), errors='coerce')
    df_test['Maximum'] = pd.to_numeric(df_test['Maximum'].astype(str).str.replace(',', ''), errors='coerce')
    
    df_test = df_test.dropna(subset=['Value'])
    
    # Calculate difference from mean bounds
    df_test['Bound_Center'] = (df_test['Maximum'] + df_test['Minimum']) / 2
    df_test['Bound_Range'] = (df_test['Maximum'] - df_test['Minimum'])
    
    # Handle division by zero
    df_test['Deviation_Ratio'] = np.where(
        df_test['Bound_Range'] > 0,
        abs(df_test['Value'] - df_test['Bound_Center']) / (df_test['Bound_Range'] / 2),
        0
    )
    
    df_test['Out_Of_Bounds'] = ((df_test['Value'] > df_test['Maximum']) | (df_test['Value'] < df_test['Minimum'])).astype(int)
    
    # Aggregate to Serial Number level
    agg_funcs = {
        'Value': ['mean', 'std', 'max', 'min'],
        'Deviation_Ratio': ['mean', 'max'],
        'Out_Of_Bounds': ['sum']
    }
    
    # Also create Pivot features: Mean deviation ratio per TOP parameter
    # Let's pick top 20 most tested parameters
    top_params = df_test['Parameter'].value_counts().nlargest(20).index
    df_top_params = df_test[df_test['Parameter'].isin(top_params)]
    
    pivot_df = df_top_params.pivot_table(
        index='SerialNumber',
        columns='Parameter',
        values='Deviation_Ratio',
        aggfunc='mean'
    ).fillna(0)
    
    pivot_df.columns = [f"Param_{col}_DevRatio" for col in pivot_df.columns]
    
    # Global aggregates
    global_agg = df_test.groupby('SerialNumber').agg(agg_funcs)
    global_agg.columns = ['_'.join(col).strip() for col in global_agg.columns.values]
    
    # Combine features
    feature_matrix = global_agg.join(pivot_df, how='left').fillna(0)
    feature_matrix['Target_Failure'] = feature_matrix.index.isin(target_sns).astype(int)
    
    # Attach warranty time/usage labels to the matrix (will be NaN for non-failures)
    warranty_info = df_drivetrain_unique.set_index('Transmission Number')[['Time_To_Failure_Days', 'Usage_Hours']]
    feature_matrix = feature_matrix.join(warranty_info, how='left')
    
    print(f"Feature matrix shape: {feature_matrix.shape}")
    
    X = feature_matrix.drop(columns=['Target_Failure', 'Time_To_Failure_Days', 'Usage_Hours'])
    y = feature_matrix['Target_Failure']
    
    # ==========================
    # 2. Isolation Forest (Unsupervised)
    # ==========================
    print("Running Isolation Forest...")
    clf = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
    clf.fit(X)
    
    # Score: lower is more anomalous
    scores = clf.decision_function(X)
    feature_matrix['Anomaly_Score'] = scores
    
    # Get top 200 most anomalous
    top_200_anomalies = feature_matrix.sort_values('Anomaly_Score').head(200)
    
    hit_count = top_200_anomalies['Target_Failure'].sum()
    print(f"\n--- Isolation Forest Results ---")
    print(f"Top 200 most anomalous transmissions contain {hit_count} actual warranty failures.")
    baseline_rate = y.mean() * 200
    print(f"Random chance would have captured approx ~{baseline_rate:.1f} failures.")
    
    # ==========================
    # 3. Random Forest & SHAP (Supervised)
    # ==========================
    print("\nRunning Random Forest...")
    # Clean feature names to remove illegal characters like spaces, brackets
    import re
    cleaned_feature_names = [re.sub(r'[\[\]< ]', '_', col) for col in X.columns]
    X_clean = X.copy()
    X_clean.columns = cleaned_feature_names
    
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    
    rf_model.fit(X_clean, y)
    
    print("Extracting SHAP values...")
    explainer = shap.TreeExplainer(rf_model)
    # For RandomForest, shap_values is a list for both classes, we want class 1
    shap_vals = explainer.shap_values(X_clean)
    if isinstance(shap_vals, list):
        shap_values_target = shap_vals[1]
    else:
        # Shap 0.45+ sometimes returns an Explainer object with .values array
        shap_values_target = getattr(shap_vals, 'values', shap_vals)
        if len(shap_values_target.shape) == 3:
            shap_values_target = shap_values_target[:, :, 1]
    
    # Plot SHAP summary
    plt.figure(figsize=(16, 10))
    shap.summary_plot(shap_values_target, X_clean, plot_type="bar", show=False)
    plt.title("Random Forest Feature Importance (SHAP - Data Extremes vs Warranty Claims)")
    plt.tight_layout()
    plot_path = '/Users/yizhengjiang/Desktop/Git/f2025_s2026_wl_cnh_dataengineering/2b_test_to_warranty_prediction/shap_feature_importance.png'
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"Saved SHAP plot to {plot_path}")
    
    # Save a quick summary text
    with open('/Users/yizhengjiang/Desktop/Git/f2025_s2026_wl_cnh_dataengineering/2b_test_to_warranty_prediction/ml_results.txt', 'w') as f:
        f.write("--- ML Proof of Concept Results ---\n")
        f.write(f"Total Transmissions Analyzed: {len(y)}\n")
        f.write(f"Total True Failures (Target=1): {sum(y)}\n\n")
        f.write("1. Unsupervised Anomaly Detection (Isolation Forest)\n")
        f.write(f"Top 200 anomalies contained {hit_count} true failures (baseline random expectation: {baseline_rate:.1f}).\n\n")
        
        f.write("2. Random Forest Feature Importance\n")
        # Get top 10 features by mean absolute SHAP value
        feature_importance = pd.DataFrame({
            'Feature': X_clean.columns,
            'Importance': np.abs(shap_values_target).mean(0)
        }).sort_values('Importance', ascending=False).head(10)
        f.write("Top 10 mathematically strongest predictors of failure:\n")
        f.write(feature_importance.to_string(index=False))

if __name__ == "__main__":
    build_ml_pipeline()
