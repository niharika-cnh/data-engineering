import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

def run_analysis():
    print("==================================================")
    print("1. Data Loading & Column Standardization")
    print("==================================================")
    
    # Create required output directories
    os.makedirs('visible_records', exist_ok=True)
    
    parts_file = 'original_records/Racine Parts Data.xlsx'
    claims_file = 'original_records/UPDATED Full Claims Report.xlsx'
    
    # Load Parts
    print("Loading Parts Data...")
    df_parts = pd.read_excel(parts_file)
    
    # Standardize column names for Parts
    df_parts = df_parts.rename(columns={
        'ActivityConsumption|ItemID': 'Part_Number',
        'ItemID Description': 'Part_Description',
        'WorkStation|ID': 'Assembly_Station_ID',
        'WorkStation|Description': 'Assembly_Station_Desc',
        'ActivityLocal|OperatorID': 'Operator_ID'
    })
    
    print(f"Parts Data successfully loaded. Shape: {df_parts.shape}")
    
    # Load Claims
    print("\nLoading Claims Data...")
    df_claims = pd.read_excel(claims_file, sheet_name='Paid', header=1)
    
    print("Dynamically inspecting claims columns (Top 5):")
    print(df_claims.columns.tolist()[:5])
    
    # Standardize column names for Claims
    df_claims = df_claims.rename(columns={
        'Causal Part Code': 'Part_Number',
        'Causal Part Descriprion': 'Part_Description_Claims',
        'Total Amount with Standard Net Local Currency': 'Warranty_Cost',
        'Production Plant Code': 'Plant_Code'
    })
    
    # Fill NA cost with 0 for aggregation
    df_claims['Warranty_Cost'] = df_claims['Warranty_Cost'].fillna(0)
    
    print(f"\nClaims Data successfully loaded. Shape: {df_claims.shape}")
    
    print("\nValidating Primary Key uniqueness in Parts Data...")
    # Clean parts primary key
    df_parts['Part_Number'] = df_parts['Part_Number'].astype(str).str.strip().str.upper()
    df_parts = df_parts.dropna(subset=['Part_Number'])
    
    is_unique = df_parts['Part_Number'].is_unique
    print(f"Is 'Part_Number' unique in Racine Parts Data? {is_unique}")
    
    if not is_unique:
        print("Handling duplicates in Parts Data by keeping the first occurrence...")
        df_parts = df_parts.drop_duplicates(subset=['Part_Number'], keep='first')
        print(f"Parts Data shape after dropping duplicates: {df_parts.shape}")
        
    print("\nCalculating Null Rate for Part Number in Claims dataset...")
    total_claims = len(df_claims)
    null_claims = df_claims['Part_Number'].isna().sum()
    print(f"Null Rate for Part_Number in Claims: {null_claims/total_claims:.2%}")
    
    print("\n==================================================")
    print("2. Correlation / Merging")
    print("==================================================")
    
    print("Standardizing Part Numbers in Claims Data...")
    df_claims['Part_Number'] = df_claims['Part_Number'].astype(str).str.strip().str.upper()
    df_claims['Part_Description_Claims'] = df_claims['Part_Description_Claims'].astype(str).str.strip().str.upper()
    
    print("Implementing Intelligent Generic Classifier (Regex Tokenization)...")
    import re
    
    generic_keywords = {'O-RING', 'ORING', 'BOLT', 'SCREW', 'WASHER', 'NUT', 'PIN', 'SEAL', 'GASKET', 'TIE', 'CIRCLIP', 'RING'}
    contextual_keywords = {'CAB', 'FRAME', 'PTO', 'HYDRAULIC', 'ENGINE', 'ROOF', 'AXLE', 'PUMP', 'DOOR', 'GLASS', 'WHEEL', 'SEAT', 'STEERING', 'TRANSMISSION', 'HOSE', 'VALVE', 'FILTER', 'CYLINDER'}
    
    def classify_description(desc):
        if pd.isna(desc):
            return 'NON_GENERIC'
            
        # Strip punctuation and tokenize into a set of uppercase words
        # Using regex to replace non-alphanumeric chars with space, then split
        clean_desc = re.sub(r'[^A-Z0-9\s]', ' ', str(desc).upper())
        tokens = set(clean_desc.split())
        
        has_generic = bool(tokens.intersection(generic_keywords))
        has_contextual = bool(tokens.intersection(contextual_keywords))
        
        if has_generic and has_contextual:
            return 'CONTEXTUAL_GENERIC'
        elif has_generic and not has_contextual:
            return 'PURE_GENERIC'
        else:
            return 'NON_GENERIC'
            
    df_claims['generic_classification'] = df_claims['Part_Description_Claims'].apply(classify_description)
    
    # Calculate Impact Statistics
    class_counts = df_claims['generic_classification'].value_counts()
    print("\n--- Classification Results ---")
    for cls, count in class_counts.items():
        print(f"{cls}: {count} ({count/len(df_claims):.1%})")
        
    # PURE_GENERIC exclusion
    exclude_mask = df_claims['generic_classification'] == 'PURE_GENERIC'
    df_ignored_generic = df_claims[exclude_mask].copy()
    
    print(f"\nAction: Excluded {len(df_ignored_generic)} PURE_GENERIC claims. Retained CONTEXTUAL and NON_GENERIC.")
    df_claims = df_claims[~exclude_mask].copy()
    
    print("\nExporting cleaned claims dataset to 'cleaned_claims_report.xlsx' for manual verification...")
    # Load a fresh copy to guarantee 100% identical column names, order, and unmodified values (like NA)
    df_clone = pd.read_excel(claims_file, sheet_name='Paid', header=1)
    df_clone['Causal Part Code'] = df_clone['Causal Part Code'].astype(str).str.strip().str.upper()
    
    print("Exporting a purely VISIBLE version of the cleaned claims report...")
    import openpyxl
    wb = openpyxl.load_workbook(claims_file, data_only=True)
    ws = wb['Paid']
    
    # Pandas index i corresponds to Excel row i + 3 (header is at row 2)
    # Must run this loop based on the ORIGINAL unabridged length of df_clone
    visible_indices = []
    for i in range(len(df_clone)):
        excel_row = i + 3
        if not ws.row_dimensions[excel_row].hidden:
            visible_indices.append(i)
            
    # Apply identical intelligent filter to df_clone
    df_clone['generic_classification'] = df_clone['Causal Part Descriprion'].apply(classify_description)
    df_clone_filtered = df_clone[df_clone['generic_classification'] != 'PURE_GENERIC'].copy()
    
    valid_visible_clone_indices = df_clone_filtered.index.intersection(visible_indices)
    df_visible = df_clone_filtered.loc[valid_visible_clone_indices]
    df_visible.to_excel('visible_records/visible_cleaned_claims_report.xlsx', index=False)
    print(f"Exported visible, non-pure-generic claims: {len(df_visible)} out of {len(df_clone)} original rows.")
    
    # Compute base totals before merge
    original_claim_count = len(df_claims)
    original_total_cost = df_claims['Warranty_Cost'].sum()
    
    print("Performing controlled left join...")
    df_merged = df_claims.merge(
        df_parts[['Part_Number', 'Assembly_Station_ID', 'Assembly_Station_Desc', 'Operator_ID']], 
        on='Part_Number', 
        how='left'
    )
    
    mapped_claims = df_merged[df_merged['Assembly_Station_ID'].notna()]
    unmapped_claims = df_merged[df_merged['Assembly_Station_ID'].isna()]
    
    mapping_rate = len(mapped_claims) / original_claim_count
    
    print(f"Total claims: {original_claim_count}")
    print(f"Successfully mapped claims: {len(mapped_claims)}")
    print(f"Mapping rate: {mapping_rate:.2%}")
    
    print("\n--- Processing VISIBLE claims subset only ---")
    valid_visible_indices = df_claims.index.intersection(visible_indices)
    df_visible_claims = df_claims.loc[valid_visible_indices].copy()
    visible_original_count = len(df_visible_claims)
    
    visible_ignored_generic = df_ignored_generic.loc[df_ignored_generic.index.intersection(visible_indices)].copy()
    if len(visible_ignored_generic) > 0:
        visible_ignored_generic.to_excel('visible_records/visible_ignored_generic_claims.xlsx', index=False)
    
    df_visible_merged = df_visible_claims.merge(
        df_parts[['Part_Number', 'Assembly_Station_ID', 'Assembly_Station_Desc', 'Operator_ID']], 
        on='Part_Number', 
        how='left'
    )
    
    visible_mapped_claims = df_visible_merged[df_visible_merged['Assembly_Station_ID'].notna()]
    visible_unmapped_claims = df_visible_merged[df_visible_merged['Assembly_Station_ID'].isna()]
    visible_mapping_rate = len(visible_mapped_claims) / visible_original_count if visible_original_count > 0 else 0
    
    print(f"Total VISIBLE claims: {visible_original_count}")
    print(f"Successfully mapped VISIBLE claims: {len(visible_mapped_claims)}")
    print(f"VISIBLE Mapping rate: {visible_mapping_rate:.2%}")
    
    print("Generating VISIBLE Claims Correlation Visual...")
    mapped_cost = visible_mapped_claims['Warranty_Cost'].sum()
    unmapped_cost = visible_unmapped_claims['Warranty_Cost'].sum()
    
    fig_corr, (ax_corr1, ax_corr2) = plt.subplots(1, 2, figsize=(12, 5), facecolor='white')
    
    labels_corr = ['Correlated to Workstation', 'Unmapped']
    colors_corr = ['#4CAF50', '#F44336'] # Green for mapped, Red for unmapped
    
    # Chart 1: By Count
    counts_corr = [len(visible_mapped_claims), len(visible_unmapped_claims)]
    ax_corr1.pie(counts_corr, labels=labels_corr, autopct='%1.1f%%', startangle=140, colors=colors_corr, wedgeprops=dict(edgecolor='white', linewidth=2))
    ax_corr1.set_title(f'By Number of Claims\n(Total: {visible_original_count})', fontsize=12)
    
    # Chart 2: By Cost
    costs_corr = [mapped_cost, unmapped_cost]
    total_cost_viz = mapped_cost + unmapped_cost
    ax_corr2.pie(costs_corr, labels=labels_corr, autopct='%1.1f%%', startangle=140, colors=colors_corr, wedgeprops=dict(edgecolor='white', linewidth=2))
    ax_corr2.set_title(f'By Warranty Cost ($)\n(Total: ${total_cost_viz:,.2f})', fontsize=12)
    
    plt.suptitle('Warranty Claims Correlation Success Rate (VISIBLE Records)', fontsize=14, y=1.05)
    plt.tight_layout()
    out_corr = 'visible_records/visible_correlation_rate.png'
    plt.savefig(out_corr, dpi=300, bbox_inches='tight')
    plt.close(fig_corr)
    print(f"Saved -> {out_corr}")
    
    print("Exporting visible_full_mapped_claims.xlsx and visible_unmatched_claims.xlsx...")
    visible_full_mapped = visible_mapped_claims.drop(columns=['Assembly_Station_ID', 'Assembly_Station_Desc']).merge(
        df_parts,
        on='Part_Number',
        how='left'
    )
    visible_full_mapped.to_excel('visible_records/visible_full_mapped_claims.xlsx', index=False)
    visible_unmapped_claims.to_excel('visible_records/visible_unmatched_claims.xlsx', index=False)
    
    print("Performing secondary validation check (Description mapping)...")
    # Clean descriptions
    df_parts['Part_Description'] = df_parts['Part_Description'].astype(str).str.strip().str.upper()
    unmapped_claims_subset = unmapped_claims.copy()
    unmapped_claims_subset['Part_Description_Claims'] = unmapped_claims_subset['Part_Description_Claims'].astype(str).str.strip().str.upper()
    
    # Try merging remaining on description
    desc_merge = unmapped_claims_subset.merge(
        df_parts[['Part_Description', 'Assembly_Station_ID']].drop_duplicates(subset=['Part_Description']),
        left_on='Part_Description_Claims',
        right_on='Part_Description',
        how='inner'
    )
    print(f"Secondary check matched {len(desc_merge)} additional claims based on Description.")
    
    print("\n==================================================")
    print("3. Aggregation & Pareto")
    print("==================================================")
    
    # Verify row counts and costs before proceeding
    assert len(df_merged) == original_claim_count, "Row count changed after merge! Duplicate keys existed."
    assert np.isclose(df_merged['Warranty_Cost'].sum(), original_total_cost), "Total warranty cost changed after merge!"
    
    print("Row count and Total Warranty Cost successfully verified post-merge.")
    
    print("\n--- Generating Aggregations and Pareto for VISIBLE Records ---")
    df_visible_filtered = df_visible_merged[df_visible_merged['Plant_Code'].notna()].copy()
    
    # Fill NaN Assembly_Station_Desc with Assembly_Station_ID to prevent groupby from dropping rows
    df_visible_filtered['Assembly_Station_Desc'] = df_visible_filtered['Assembly_Station_Desc'].fillna(df_visible_filtered['Assembly_Station_ID'])
    
    print(f"VISIBLE claims remaining after Plant filter: {len(df_visible_filtered)}")
    
    visible_agg_df = df_visible_filtered.groupby(['Assembly_Station_ID', 'Assembly_Station_Desc']).agg(
        Claim_Occurrences=('Claim Number', 'count'),
        Total_Warranty_Cost=('Warranty_Cost', 'sum')
    ).reset_index()
    
    visible_agg_df = visible_agg_df.sort_values(by='Total_Warranty_Cost', ascending=False).reset_index(drop=True)
    visible_total_cost_agg = visible_agg_df['Total_Warranty_Cost'].sum()
    visible_agg_df['Percentage_Contribution'] = (visible_agg_df['Total_Warranty_Cost'] / visible_total_cost_agg) * 100
    visible_agg_df['Cumulative_Percentage'] = visible_agg_df['Percentage_Contribution'].cumsum()
    
    if len(visible_agg_df) > 0:
        visible_max_cum_pct = visible_agg_df['Cumulative_Percentage'].iloc[-1]
        print(f"VISIBLE Cumulative percentage adds up to: {visible_max_cum_pct:.2f}% (Expected ~100.0%)")
    
    print("Exporting VISIBLE aggregated results...")
    visible_agg_df.to_excel('visible_records/visible_aggregated_results.xlsx', index=False)
    
    print("Generating VISIBLE Pareto Chart...")
    
    color_bar = '#fffae3'
    color_text = 'black'
    color_line = 'black'
    from matplotlib.colors import LinearSegmentedColormap
    cmap_custom = LinearSegmentedColormap.from_list("custom_yellow", ["#fffae3", "#ffc000", "#ff5722"])
    
    fig_v, ax1_v = plt.subplots(figsize=(12, 6))
    plot_df_v = visible_agg_df.head(15)
    
    color_bar = '#fffae3'
    color_text = 'black'
    color_line = 'black'
    
    ax1_v.set_xlabel('Assembly Station', color=color_text)
    ax1_v.set_ylabel('Total Warranty Cost ($)', color=color_text)
    sns.barplot(x='Assembly_Station_ID', y='Total_Warranty_Cost', data=plot_df_v, color=color_bar, ax=ax1_v, edgecolor='black')
    ax1_v.set_ylim(0, plot_df_v['Total_Warranty_Cost'].max() * 1.25)
    ax1_v.tick_params(axis='y', labelcolor=color_text)
    ax1_v.set_xticklabels(ax1_v.get_xticklabels(), rotation=45, ha='right')
    
    ax2_v = ax1_v.twinx()  
    ax2_v.set_ylabel('Cumulative Percentage (%)', color=color_text)  
    ax2_v.plot(plot_df_v['Assembly_Station_ID'], plot_df_v['Cumulative_Percentage'], color=color_line, marker='o', ms=5)
    ax2_v.tick_params(axis='y', labelcolor=color_text)
    ax2_v.set_ylim([0, 105])
    
    for p in ax1_v.patches:
        height = p.get_height()
        if height > 0:
            ax2_v.text(p.get_x() + p.get_width() / 2., height + (plot_df_v['Total_Warranty_Cost'].max() * 0.02),
                       f'${height:,.0f}', ha='center', va='bottom', color=color_text,
                       transform=ax1_v.transData,
                       bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=0.5))
    
    plt.title('VISIBLE Pareto Chart of Warranty Costs by Assembly Station (Top 15)', color=color_text)
    fig_v.tight_layout()  
    plt.savefig('visible_records/visible_pareto_chart_costs.png', dpi=300)
    print("Saved -> visible_pareto_chart_costs.png")
    
    print("Generating VISIBLE Pareto Chart for Claim Occurrences...")
    # Sort by Occurrences
    visible_agg_df_occ = visible_agg_df.sort_values(by='Claim_Occurrences', ascending=False).reset_index(drop=True)
    visible_total_occ_agg = visible_agg_df_occ['Claim_Occurrences'].sum()
    visible_agg_df_occ['Percentage_Contribution_Occ'] = (visible_agg_df_occ['Claim_Occurrences'] / visible_total_occ_agg) * 100
    visible_agg_df_occ['Cumulative_Percentage_Occ'] = visible_agg_df_occ['Percentage_Contribution_Occ'].cumsum()
    
    fig_v_occ, ax1_v_occ = plt.subplots(figsize=(12, 6))
    plot_df_v_occ = visible_agg_df_occ.head(15)
    
    ax1_v_occ.set_xlabel('Assembly Station', color=color_text)
    ax1_v_occ.set_ylabel('Number of Claims (Occurrences)', color=color_text)
    sns.barplot(x='Assembly_Station_ID', y='Claim_Occurrences', data=plot_df_v_occ, color='#87CEEB', ax=ax1_v_occ, edgecolor='black')
    ax1_v_occ.set_ylim(0, plot_df_v_occ['Claim_Occurrences'].max() * 1.25)
    ax1_v_occ.tick_params(axis='y', labelcolor=color_text)
    ax1_v_occ.tick_params(axis='x', labelcolor=color_text)
    ax1_v_occ.set_xticks(range(len(plot_df_v_occ)))
    ax1_v_occ.set_xticklabels(plot_df_v_occ['Assembly_Station_ID'], rotation=45, ha='right')
    
    ax2_v_occ = ax1_v_occ.twinx()  
    ax2_v_occ.set_ylabel('Cumulative Percentage (%)', color=color_text)  
    ax2_v_occ.plot(plot_df_v_occ['Assembly_Station_ID'], plot_df_v_occ['Cumulative_Percentage_Occ'], color=color_line, marker='o', ms=5)
    ax2_v_occ.tick_params(axis='y', labelcolor=color_text)
    ax2_v_occ.set_ylim([0, 105])
    
    for p in ax1_v_occ.patches:
        height = p.get_height()
        if height > 0:
            ax2_v_occ.text(p.get_x() + p.get_width() / 2., height + (plot_df_v_occ['Claim_Occurrences'].max() * 0.02),
                           f'{height:,.0f}', ha='center', va='bottom', color=color_text, rotation=0,
                           transform=ax1_v_occ.transData,
                           bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=0.5))
    
    plt.title('VISIBLE Pareto Chart of Claim Occurrences by Assembly Station (Top 15)', color=color_text)
    fig_v_occ.tight_layout()  
    out_pareto_occ = 'visible_records/visible_pareto_chart_occurrences.png'
    plt.savefig(out_pareto_occ, dpi=300)
    plt.close(fig_v_occ)
    print(f"Saved -> {out_pareto_occ}")
    
    print("Generating VISIBLE Pareto Chart with Operator Grouped...")
    top_stations_v = plot_df_v['Assembly_Station_ID'].tolist()
    
    # Save visible operator breakdown to excel
    agg_operator_df_v = df_visible_filtered.groupby(['Assembly_Station_ID', 'Assembly_Station_Desc', 'Operator_ID']).agg(
        Total_Warranty_Cost=('Warranty_Cost', 'sum'),
        Claim_Occurrences=('Claim Number', 'count')
    ).reset_index()
    agg_operator_df_v = agg_operator_df_v.sort_values(by=['Assembly_Station_ID', 'Total_Warranty_Cost'], ascending=[True, False])
    agg_operator_df_v.to_excel('visible_records/visible_operator_breakdown.xlsx', index=False)
    print("Exported VISIBLE Operator Breakdown -> visible_records/visible_operator_breakdown.xlsx")
    
    x_pos_v = []
    heights_v = []
    labels_v = []
    station_centers_v = []
    current_x_v = 0
    
    for station in top_stations_v:
        station_ops = df_visible_filtered[df_visible_filtered['Assembly_Station_ID'] == station].groupby('Operator_ID')['Warranty_Cost'].sum().sort_values(ascending=False)
        
        start_x_v = current_x_v
        for i, (op, cost) in enumerate(station_ops.items()):
            x_pos_v.append(current_x_v)
            heights_v.append(cost)
            labels_v.append(f"Op: {op}\n({station})")
            current_x_v += 1
            
        if len(station_ops) > 0:
            station_centers_v.append((start_x_v + current_x_v - 1) / 2.0)
        else:
            station_centers_v.append(current_x_v)
            
        current_x_v += 1 # Gap between stations
        
    fig_v2, ax1_v2 = plt.subplots(figsize=(max(24, len(x_pos_v) * 0.6), 8))
    
    if heights_v:
        norm_v = plt.Normalize(0, max(heights_v))
        colors_bar_v = [cmap_custom(norm_v(h)) for h in heights_v]
    else:
        colors_bar_v = ['#fffae3'] * len(x_pos_v)
        
    bars_v2 = ax1_v2.bar(x_pos_v, heights_v, width=0.8, color=colors_bar_v, edgecolor='black')
    ax1_v2.set_xlabel('Assembly Station & Operator ID', color=color_text)
    ax1_v2.set_ylabel('Total Warranty Cost ($)', color=color_text)
    ax1_v2.tick_params(axis='y', labelcolor=color_text)
    ax1_v2.tick_params(axis='x', labelcolor=color_text)
    ax1_v2.set_xticks(x_pos_v)
    ax1_v2.set_xticklabels(labels_v, rotation=45, ha='right')

    for bar in bars_v2:
        height = bar.get_height()
        if height > 0:
            ax1_v2.text(
                bar.get_x() + bar.get_width() / 2,
                height + (max(heights_v) * 0.02),
                f'${height:,.0f}',
                ha='left',
                va='bottom',
                fontsize=9,
                color='black',
                rotation=45
            )

    ax1_v2.set_ylim(0, max(heights_v) * 1.35 if heights_v else 1)

    ax2_v2 = ax1_v2.twinx()  
    ax2_v2.set_ylabel('Cumulative Percentage (%)', color=color_text)  
    ax2_v2.plot(station_centers_v, plot_df_v['Cumulative_Percentage'], color=color_line, marker='o', ms=5)
    ax2_v2.tick_params(axis='y', labelcolor=color_text)
    ax2_v2.set_ylim([0, 105])

    plt.title('VISIBLE Pareto Chart of Warranty Costs by Assembly Station & Operator (Top 15)', color=color_text)
    fig_v2.tight_layout()  
    plt.savefig('visible_records/visible_pareto_chart_costs_by_operator.png', dpi=300)
    print("Saved -> visible_pareto_chart_costs_by_operator.png")
    
    # Can also plot for occurrences...
    
    print("\n==================================================")
    print("4. Manual Category Classification Mapping")
    print("==================================================")
    
    class_file = 'original_records/classified_claims_new.xlsx'
    if os.path.exists(class_file):
        print(f"Detected classification file '{class_file}'. Mapping categories...")
        df_class = pd.read_excel(class_file)
        
        # Map row-by-row sequentially for the length of df_class based on the FIRST n visible indices
        df_class['Claim Number'] = df_visible_claims['Claim Number'].iloc[:len(df_class)].values
        df_class['Dealer Comments'] = df_visible_claims['Dealer Comments'].iloc[:len(df_class)].values
        
        def normalize(s):
            if pd.isna(s): return ""
            return str(s).strip().lower()

        df_class['norm_comment'] = df_class['Dealer Comments'].apply(normalize)

        claim_to_cat = df_class.dropna(subset=['Claim Number', 'category']).drop_duplicates(subset=['Claim Number']).set_index('Claim Number')['category'].to_dict()
        comment_to_cat = df_class.dropna(subset=['norm_comment', 'category']).drop_duplicates(subset=['norm_comment']).set_index('norm_comment')['category'].to_dict()

        visible_full_mapped['norm_comment'] = visible_full_mapped['Dealer Comments'].apply(normalize)

        def assign_category(row):
            cn = row['Claim Number']
            nc = row['norm_comment']
            if cn in claim_to_cat:
                return claim_to_cat[cn]
            if nc in comment_to_cat:
                return comment_to_cat[nc]
            return pd.NA

        visible_full_mapped['category'] = visible_full_mapped.apply(assign_category, axis=1)
        visible_full_mapped = visible_full_mapped.drop(columns=['norm_comment'])
        out_file = 'visible_records/visible_full_mapped_claims_with_categories.xlsx'
        visible_full_mapped.to_excel(out_file, index=False)
        print(f"Exported enriched categories -> {out_file}")
        
        print("\nGenerating Category Breakdown Charts...")
        df_cat = visible_full_mapped.dropna(subset=['category']).copy()
        counts_cat = df_cat['category'].value_counts()
        
        if len(counts_cat) > 0:
            colors_cat = ["#F4D160", "#F4A261", "#E9ECEF"]
            color_bg_cat = 'white'
            color_text_cat = '#333333'
            
            plt.style.use('default')
            fig_cat, (ax1_cat, ax2_cat) = plt.subplots(1, 2, figsize=(12, 5.5), facecolor=color_bg_cat)
            
            sns.barplot(x=counts_cat.index, y=counts_cat.values, hue=counts_cat.index, palette=colors_cat[:len(counts_cat)], ax=ax1_cat, edgecolor='#cccccc', legend=False)
            ax1_cat.set_title('Category Occurrences', fontsize=13, color=color_text_cat, pad=15)
            ax1_cat.set_ylabel('Number of Claims', fontsize=11, color=color_text_cat)
            ax1_cat.set_xlabel('Category', fontsize=11, color=color_text_cat)
            ax1_cat.tick_params(colors=color_text_cat)
            
            ax1_cat.spines['top'].set_visible(False)
            ax1_cat.spines['right'].set_visible(False)
            ax1_cat.spines['left'].set_color('#dddddd')
            ax1_cat.spines['bottom'].set_color('#dddddd')
            ax1_cat.grid(axis='y', linestyle='-', alpha=0.3, color='#dddddd')
            
            max_val_cat = max(counts_cat.values)
            ax1_cat.set_ylim(0, max_val_cat * 1.4)
            
            for i, v in enumerate(counts_cat.values):
                ax1_cat.text(i, v + (max_val_cat * 0.03), str(v), ha='center', va='bottom', fontsize=11, color=color_text_cat)
                
            wedges_cat, texts_cat, autotexts_cat = ax2_cat.pie(
                counts_cat.values, 
                labels=counts_cat.index,
                colors=colors_cat[:len(counts_cat)],
                autopct='%1.1f%%',
                startangle=140,
                pctdistance=0.75,
                wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2),
                textprops={'color': color_text_cat, 'fontsize': 11}
            )
            
            ax2_cat.set_title('Category Percentage Distribution', fontsize=13, color=color_text_cat, pad=15)
            
            for autotext in autotexts_cat:
                autotext.set_fontweight('normal')
                autotext.set_color(color_text_cat)
            for text in texts_cat:
                text.set_fontweight('normal')
                text.set_color(color_text_cat)
                
            plt.suptitle('Warranty Claims Category Classification', fontsize=15, color='#222222', y=1.02)
            plt.tight_layout()
            output_img_cat = 'visible_records/category_distribution_chart.png'
            plt.savefig(output_img_cat, dpi=300, bbox_inches='tight')
            print(f"Saved -> {output_img_cat}")
            plt.close(fig_cat)
            
            print("\nGenerating Cross-Dimensional Station/Category Charts (Warranty Cost)...")
            # Ensure Warranty_Cost is numeric
            df_cat['Warranty_Cost'] = pd.to_numeric(df_cat['Warranty_Cost'], errors='coerce').fillna(0)

            # Group by Station and Category
            cross_df = df_cat.groupby(['Assembly_Station_ID', 'category'])['Warranty_Cost'].sum().reset_index()
            
            # Find Top 15 Stations by Total Warranty Cost
            top_stations = cross_df.groupby('Assembly_Station_ID')['Warranty_Cost'].sum().nlargest(15).index.tolist()
            cross_df_top = cross_df[cross_df['Assembly_Station_ID'].isin(top_stations)]
            
            # Pivot table for plotting
            pivot_df = cross_df_top.pivot(index='Assembly_Station_ID', columns='category', values='Warranty_Cost').fillna(0)
            
            # Reorder rows to match Top 15 (largest at top/left)
            pivot_df = pivot_df.loc[top_stations]
            
            # ==========================================
            # Chart 1: Stacked Bar Chart
            # ==========================================
            fig_stack, ax_stack = plt.subplots(figsize=(15, 12), facecolor='white')
            
            # Plot stacked bar
            pivot_df.plot(kind='bar', stacked=True, ax=ax_stack, colormap='tab20', edgecolor='gray', linewidth=0.5)
            
            ax_stack.set_title('Top 15 Assembly Stations by Warranty Cost (Category Breakdown)', fontsize=15, color='#333333', pad=15)
            ax_stack.set_xlabel('Assembly Station', fontsize=12, color='#333333')
            ax_stack.set_ylabel('Total Warranty Cost ($)', fontsize=12, color='#333333')
            ax_stack.tick_params(colors='#333333')
            
            totals = pivot_df.sum(axis=1)
            max_total = totals.max() if totals.max() > 0 else 1
            threshold = max_total * 0.035  # Filter out smallest segments to make room for larger font
            
            for c in ax_stack.containers:
                labels = [f"${v:,.0f}" if v >= threshold else "" for v in c.datavalues]
                ax_stack.bar_label(
                    c, labels=labels, label_type='center', fontsize=9.5, color='#111111',
                    bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=0.0)
                )
                
            # Keep ylim tight so bars stretch out vertically as much as possible
            ax_stack.set_ylim(0, max_total * 1.05)
            
            # Clean spines
            ax_stack.spines['top'].set_visible(False)
            ax_stack.spines['right'].set_visible(False)
            plt.xticks(rotation=45, ha='right')
            ax_stack.legend(title='Category', bbox_to_anchor=(1.05, 1), loc='upper left')
            ax_stack.grid(axis='y', linestyle='--', alpha=0.5)
            
            fig_stack.tight_layout()
            out_stacked = 'visible_records/station_category_stacked_bar.png'
            plt.savefig(out_stacked, dpi=300, bbox_inches='tight', facecolor=fig_stack.get_facecolor())
            print(f"Saved -> {out_stacked}")
            plt.close(fig_stack)
            
            # ==========================================
            # Chart 2: Heatmap
            # ==========================================
            fig_heat, ax_heat = plt.subplots(figsize=(14, 8), facecolor='white')
            
            # Generate heatmap with values
            sns.heatmap(pivot_df, cmap='YlOrRd', annot=True, fmt=".0f", linewidths=.5, ax=ax_heat, cbar_kws={'label': 'Warranty Cost ($)'})
            
            ax_heat.set_title('Heatmap: Warranty Cost by Station and Category', fontsize=14, color='#333333', pad=15)
            ax_heat.set_xlabel('Category', fontsize=12, color='#333333')
            ax_heat.set_ylabel('Assembly Station', fontsize=12, color='#333333')
            
            # Rotate axes for better readability
            plt.xticks(rotation=45, ha='right')
            plt.yticks(rotation=0)
            
            fig_heat.tight_layout()
            out_heatmap = 'visible_records/station_category_heatmap.png'
            plt.savefig(out_heatmap, dpi=300, bbox_inches='tight', facecolor=fig_heat.get_facecolor())
            print(f"Saved -> {out_heatmap}")
            plt.close(fig_heat)

        else:
            print("No category matches found. Skipped charting.")
    else:
        print("\nNo classification file found. Skipping category distribution mapping.")

    print("\nDone!")

if __name__ == '__main__':
    run_analysis()
