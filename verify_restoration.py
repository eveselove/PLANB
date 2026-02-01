
import json
import re

nb_path = "/home/eveselove/PLANB/PLANB.ipynb"

try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    full_source = ""
    for cell in nb['cells']:
        full_source += "".join(cell.get('source', [])) + "\n"

    required_methods = [
        "_get_elasticity_filepath",
        "_update_indicators",
        "_build_city_dept_limits_panel",
        "_setup_elasticity_sliders",
        "_apply_elasticity",
        "view"
    ]

    print("Checking for methods in PLANB.ipynb...")
    for method in required_methods:
        # Simple regex check for "def method_name"
        if re.search(rf"def\s+{method}", full_source):
             print(f"[OK] {method} found.")
        else:
             print(f"[MISSING] {method} NOT found.")

except Exception as e:
    print(f"Error: {e}")
