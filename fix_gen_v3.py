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
                
            # Заменяем проблемные вызовы на безопасные, сохраняя структуру
            outline = line.replace("display(", "print('UI Skipped: ' + str(").replace("dashboard.view()", "pass")
            # Закрываем скобку если заменили display
            if "print('UI Skipped: ' + str(" in outline:
                outline += ")"
            
            lines.append(outline)
            
        py_source += "\n".join(lines) + "\n\n"

py_source += """
print("--- SAVING ---")
if 'df_result' in locals():
    # Сохаряем в CSV и PKL
    df_result.to_csv('/home/eveselove/PLAN/dashboard_data.csv', index=False)
    with open('/home/eveselove/PLAN/clean_data.pkl', 'wb') as f:
        pickle.dump({'df_result': df_result}, f)
    print("✅ Saved dashboard_data.csv")
else:
    print("❌ df_result missing")
"""

with open("/home/eveselove/PLANB/gen_clean.py", "w") as f:
    f.write(py_source)
