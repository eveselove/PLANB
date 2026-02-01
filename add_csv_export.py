import json

nb_path = "/home/eveselove/PLANB/PLANB.ipynb"
with open(nb_path, 'r') as f:
    nb = json.load(f)

code = """
# SAFETY EXPORT TO CSV
try:
    print("Saving to CSV...")
    df_export = dashboard.df.copy()
    # Convert list/array columns to string if needed to avoid csv issues, but standard csv handles it ok mostly
    df_export.to_csv('/home/eveselove/PLAN/dashboard_data.csv', index=False)
    print("✅ Saved dashboard_data.csv")
    
    if hasattr(dashboard, 'df_roles') and dashboard.df_roles is not None:
         dashboard.df_roles.to_csv('/home/eveselove/PLAN/dashboard_roles.csv', index=False)
except Exception as e:
    print(f"❌ Error saving CSV: {e}")
"""

# Append to end
cell = {
 "cell_type": "code",
 "execution_count": None,
 "metadata": {},
 "outputs": [],
 "source": [code]
}
nb['cells'].append(cell)

with open(nb_path, 'w') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    
print("Added CSV export cell.")
