
import json

nb_path = "/home/eveselove/PLANB/PLANB.ipynb"

try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    print(f"Total cells: {len(nb['cells'])}")
    
    for i, cell in enumerate(nb['cells']):
        cell_type = cell.get('cell_type', 'unknown')
        source = "".join(cell.get('source', []))
        summary = source[:50].replace('\n', ' ')
        print(f"Cell {i} ({cell_type}): {summary}...")
        
        if "class PlanDashboard" in source:
            print(f"  --> FOUND PlanDashboard in cell {i}!")
        if "def prepare_baseline" in source:
             print(f"  --> FOUND prepare_baseline in cell {i}!")

except Exception as e:
    print(f"Error: {e}")
