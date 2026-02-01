import json

with open("/home/eveselove/PLANB/PLANB.ipynb", "r") as f:
    nb = json.load(f)

py_source = "import pandas as pd\nimport numpy as np\nimport pickle\nimport os\n"

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        if "class PlanDashboard" in source:
             break
        
        lines = []
        for line in source.split('\n'):
            if line.strip().startswith('%') or line.strip().startswith('!'):
                continue
            # Safe replacement
            outline = line.replace("display(", "print('UI Skipped: ' + str(").replace("dashboard.view()", "pass")
            if "print('UI Skipped: ' + str(" in outline:
                outline += ")"
            lines.append(outline)
            
        py_source += "\n".join(lines) + "\n\n"

py_source += """
print("--- SAVING V4 ---")
target_df = None
if 'df_result' in locals():
    target_df = df_result
    print("Found df_result")
elif 'df_app' in locals():
    target_df = df_app
    print("Found df_app")
elif 'df_sales_2023_2025' in locals():
    target_df = df_sales_2023_2025
    print("Found df_sales_2023_2025 as fallback")

if target_df is not None:
    # Ensure Month/Year int
    try:
        if 'Месяц' in target_df.columns: target_df['Месяц'] = target_df['Месяц'].astype(int)
        if 'Год' in target_df.columns: target_df['Год'] = target_df['Год'].astype(int)
    except: pass
    
    target_df.to_csv('/home/eveselove/PLAN/dashboard_data.csv', index=False)
    
    # Save pkl for compatibility logic (optional)
    try:
        with open('/home/eveselove/PLAN/dashboard_data.pkl', 'wb') as f:
            pickle.dump({'df_result': target_df, 'df_roles': None}, f)
        print("✅ Saved dashboard_data.pkl (new version)")
    except Exception as e:
        print(f"Pkl error: {e}")
        
    print("✅ Saved dashboard_data.csv")
else:
    print("❌ No DataFrame found!")
"""

with open("/home/eveselove/PLANB/gen_clean.py", "w") as f:
    f.write(py_source)
