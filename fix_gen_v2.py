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
            stripped = line.strip()
            if stripped.startswith('%') or stripped.startswith('!'):
                continue
            if 'display(' in line or '.view()' in line or 'print(' in line: 
                # Заменяем на pass, чтобы не ломать блоки if/else/try
                # Но print полезен для отладки. Ладно, print оставляем, display заменяем.
                if 'display(' in line or '.view()' in line:
                     lines.append("    pass # skipped UI")
                else:
                     lines.append(line)
            else:
                lines.append(line)
        py_source += "\n".join(lines) + "\n\n"

py_source += """
print("--- SAVING ---")
if 'df_result' in locals():
    # Сохаряем в CSV и PKL (на всякий случай чистый PKL)
    df_result.to_csv('/home/eveselove/PLAN/dashboard_data.csv', index=False)
    with open('/home/eveselove/PLAN/clean_data.pkl', 'wb') as f:
        pickle.dump({'df_result': df_result}, f)
    print("✅ Saved dashboard_data.csv and clean_data.pkl")
else:
    print("❌ df_result missing")
"""

with open("/home/eveselove/PLANB/gen_clean.py", "w") as f:
    f.write(py_source)
