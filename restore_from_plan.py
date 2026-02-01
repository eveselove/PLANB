
import json

src_path = "/home/eveselove/PLAN/PLAN.ipynb"
dst_path = "/home/eveselove/PLANB/PLANB.ipynb"

try:
    with open(src_path, 'r', encoding='utf-8') as f:
        src_nb = json.load(f)
    
    with open(dst_path, 'r', encoding='utf-8') as f:
        dst_nb = json.load(f)
        
    cells_to_copy = []
    
    # Identify cells to copy from PLAN
    # We want the logic cells.
    # Typically: prepare_baseline, calculate_planning_weights, business rules, PlanDashboard class.
    
    # Helper to find cell by content
    def find_cells_with(nb, text):
        matches = []
        for cell in nb['cells']:
            src = "".join(cell.get('source', []))
            if text in src:
                matches.append(cell)
        return matches

    baseline_cells = find_cells_with(src_nb, "def prepare_baseline")
    dashboard_cells = find_cells_with(src_nb, "class PlanDashboard")
    
    if not baseline_cells:
        print("Warning: Could not find prepare_baseline in source.")
    if not dashboard_cells:
        print("Warning: Could not find PlanDashboard in source.")
        
    # We will insert them before the last cell of PLANB (which is the execution cell)
    # Actually, we should try to be smarter.
    # Let's insert them at index -1 (before last).
    
    # We also need to be careful about duplicates if I run this multiple times.
    # But currently PLANB is missing them.
    
    insert_idx = len(dst_nb['cells']) - 1
    if insert_idx < 0: insert_idx = 0
    
    # Copy baseline cells
    count = 0
    for cell in baseline_cells:
        dst_nb['cells'].insert(insert_idx, cell)
        insert_idx += 1
        count += 1
        
    # Copy dashboard cells
    for cell in dashboard_cells:
        dst_nb['cells'].insert(insert_idx, cell)
        insert_idx += 1
        count += 1
        
    print(f"Restored {count} cells from PLAN.")
    
    with open(dst_path, 'w', encoding='utf-8') as f:
        json.dump(dst_nb, f, indent=1, ensure_ascii=False)
        
except Exception as e:
    print(f"Error: {e}")
