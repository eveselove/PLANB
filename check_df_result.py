
import json

nb_path = "/home/eveselove/PLANB/PLANB.ipynb"

try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # Find cell with prepare_baseline
    for cell in nb['cells']:
        src = "".join(cell.get('source', []))
        if "def prepare_baseline" in src:
            print("--- CELL WITH prepare_baseline ---")
            print(src[:500] + "..." + src[-500:])
            # Check if it assigns df_result
            if "df_result =" in src:
                 print("\n[OK] Contains df_result assignment")
            else:
                 print("\n[WARNING] Does NOT contain df_result assignment")
    
except Exception as e:
    print(f"Error: {e}")
