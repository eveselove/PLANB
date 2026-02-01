
import json

nb_path = "/home/eveselove/PLANB/PLANB.ipynb"

try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # Find all cells defining PlanDashboard
    definitions = []
    for i, cell in enumerate(nb['cells']):
        src = "".join(cell.get('source', []))
        if "class PlanDashboard" in src:
            definitions.append(i)
            print(f"Found PlanDashboard definition in cell {i}")
            
    if definitions:
        last_def_idx = definitions[-1]
        print(f"Checking __init__ in cell {last_def_idx}...")
        cell = nb['cells'][last_def_idx]
        src = "".join(cell.get('source', []))
        
        # Check for compact_stats init
        if "self.compact_stats =" in src:
            print("[OK] self.compact_stats initialization FOUND in __init__ (or somewhere in class)")
        else:
            print("[FAIL] self.compact_stats initialization NOT found in class definition")
            
        # Check for _update_compact_stats
        if "def _update_compact_stats" in src:
             print("[OK] _update_compact_stats method FOUND")
        else:
             print("[FAIL] _update_compact_stats method NOT found")
             
    else:
        print("No PlanDashboard definition found.")

except Exception as e:
    print(f"Error: {e}")
