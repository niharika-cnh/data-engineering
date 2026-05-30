import pandas as pd

f1 = "Racine Parts Data.xlsx"
f2 = "UPDATED Full Claims Report.xlsx"

print("--- Racine Parts Data ---")
df1 = pd.read_excel(f1)
print(df1.columns.tolist())
print(df1.head())

print("\n--- Full Claims Report ---")
print("\n--- Finding Value Overlaps ---")
# Read full data for claims
df2_paid = pd.read_excel(f2, sheet_name="Paid", header=0)

# We want to find common values between the two dataframes.
# To not get overwhelmed by common numbers or NaNs, we convert everything to string and drop small strings
def get_unique_words(df):
    words = set()
    for col in df.columns:
        # Convert column to string, drop nas, get unique values
        vals = df[col].dropna().astype(str).unique()
        for v in vals:
            v_clean = v.strip()
            # Only keep values > 3 chars to avoid matching '1', '2', '0.0', 'NaN', 'Y', 'N' etc which are meaningless overlaps
            if len(v_clean) > 3:
                words.add(v_clean)
    return words

print("Extracting unique values from Racine Parts Data...")
words1 = get_unique_words(df1)
print(f"Found {len(words1)} unique values")

print("Extracting unique values from Full Claims Report (Paid)...")
words2 = get_unique_words(df2_paid)
print(f"Found {len(words2)} unique values")

overlap = words1.intersection(words2)
print(f"Found {len(overlap)} overlapping values between the two datasets.")

if len(overlap) > 0:
    print("Sample overlapping values:")
    # Print up to 20 overlaps
    for i, val in enumerate(list(overlap)[:20]):
        print(f"  - {val}")
        
    # Now find which columns these come from
    print("\nColumns containing overlapping values:")
    
    dict1_cols = {val: [] for val in overlap}
    for col in df1.columns:
        vals = set(df1[col].dropna().astype(str).str.strip().unique())
        for v in overlap:
            if v in vals:
                dict1_cols[v].append(col)
                
    dict2_cols = {val: [] for val in overlap}
    for col in df2_paid.columns:
        vals = set(df2_paid[col].dropna().astype(str).str.strip().unique())
        for v in overlap:
            if v in vals:
                dict2_cols[v].append(col)
                
    # Find most common column pairs
    from collections import Counter
    col_pairs = []
    for v in overlap:
        if dict1_cols[v] and dict2_cols[v]:
            for c1 in dict1_cols[v]:
                for c2 in dict2_cols[v]:
                    col_pairs.append((c1, c2))
    
    pair_counts = Counter(col_pairs)
    print("\nMost common column matches (Parts Data Column -> Claims Report Column):")
    for (c1, c2), count in pair_counts.most_common(10):
        print(f"  '{c1}' -> '{c2}' ({count} shared values)")
        
