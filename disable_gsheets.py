
import json
import sys

nb_path = "/home/eveselove/PLANB/PLANB.ipynb"

try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    modified = False

    # Goal: In _load_corrections, comment out usage of self.gc to force local JSON usage.
    # Also in _save_elasticity_coefficients and others if present.
    
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = cell['source']
            new_source = []
            
            for line in source:
                # Disable loading from sheets
                if "if self.gc:" in line:
                    if "corrections = load_corrections_from_sheets(self.gc)" in "".join(source): # context check
                         new_source.append(f"# {line}") # Comment out
                         modified = True
                         continue
                
                # Check specific call
                if "corrections = load_corrections_from_sheets(self.gc)" in line:
                    new_source.append(f"# {line}")
                    modified = True
                    continue

                # Also saving
                # if "save_elasticity_to_sheets(self.gc, coefficients)" in line:
                #    new_source.append(f"# {line}")
                #    modified = True
                #    continue

                new_source.append(line)
            
            if len(new_source) != len(source):
                cell['source'] = new_source

    if modified:
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print("Notebook saved successfully: Google Sheets usage disabled in code.")
    else:
        print("No active Google Sheets calls found to disable.")

except Exception as e:
    print(f"Error: {e}")
