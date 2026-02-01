
import json

nb_path = "/home/eveselove/PLANB/PLANB.ipynb"

try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # Assumes last cell defining PlanDashboard is the one
    definitions = [c for c in nb['cells'] if "class PlanDashboard" in "".join(c.get('source', []))]
    if definitions:
        cell = definitions[-1]
        src = "".join(cell.get('source', []))
        
        # Regex to capture __init__ method
        import re
        match = re.search(r"def __init__\(self.*?\):(.*?)def ", src, re.DOTALL)
        if match:
             init_code = match.group(1)
             print(init_code[:3000]) # print first 3000 chars of init
        else:
             print("Could not parse __init__")
             
except Exception as e:
    print(f"Error: {e}")
