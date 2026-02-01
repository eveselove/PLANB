
import json
import sys

nb_path = "/home/eveselove/PLANB/PLANB.ipynb"

try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    modified = False

    # Goal: Replace "_setup_widgets(self):" with "_setup_widgets(self):" 
    # BUT explicitly remove the lines that set up undo_btn if they are flawed or re-write them.
    # Actually, we might want to check the Indentation.
    
    # Let's inspect the `_setup_widgets` method in the notebook.
    
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = cell['source']
            new_source = []
            
            in_setup_widgets = False
            for line in source:
                if "def _setup_widgets(self):" in line:
                    in_setup_widgets = True
                    new_source.append(line)
                    continue
                
                if in_setup_widgets:
                    # Check if we exited the function (next def or unindented)
                    if line.strip() != "" and not line.startswith("    "): # Assuming 4 spaces indent for method body?
                        # ACTUALLY, "    def ..." is level 1. Body is level 2 (8 spaces).
                        # If line starts with "    def", we exited.
                        if line.startswith("    def "):
                            in_setup_widgets = False
                    
                    if in_setup_widgets:
                         # Ensure undo_btn lines use correct method references
                         if "self.undo_btn.on_click(self._undo_correction)" in line:
                             # This line crashed because _undo_correction was missing.
                             # We added it back, but maybe it wasn't seen?
                             # Or maybe the indentation of the added methods was wrong?
                             pass
                
                new_source.append(line)
    
    # let's try to re-add the methods AGAIN but very carefully at the END of the class to be safe?
    # Or check if they exist.
    
    class_cell_idx = -1
    for idx, cell in enumerate(nb['cells']):
        if cell['cell_type'] == 'code' and "class PlanDashboard:" in "".join(cell['source']):
            class_cell_idx = idx
            break
            
    if class_cell_idx != -1:
        source = nb['cells'][class_cell_idx]['source']
        has_undo = any("def _undo_correction" in line for line in source)
        
        if not has_undo:
             print("Methods missing! Re-adding...")
             # Append to the end of the cell
             source.append("\n")
             source.append("    def _undo_correction(self, event=None):\n")
             source.append("        if self.corr_history_idx >= 0:\n")
             source.append("            item = self.corr_history[self.corr_history_idx]\n")
             source.append("            self._apply_history_item(item, use_old=True)\n")
             source.append("            self.corr_history_idx -= 1\n")
             source.append("\n")
             source.append("    def _redo_correction(self, event=None):\n")
             source.append("        if self.corr_history_idx < len(self.corr_history) - 1:\n")
             source.append("            self.corr_history_idx += 1\n")
             source.append("            item = self.corr_history[self.corr_history_idx]\n")
             source.append("            self._apply_history_item(item, use_old=False)\n")
             source.append("\n")
             
             nb['cells'][class_cell_idx]['source'] = source
             modified = True
        else:
             print("Methods exist. Maybe indentation issue?")
             # Let's inspect indentation of _undo_correction
             for line in source:
                 if "def _undo_correction" in line:
                     print(f"Found: '{line.rstrip()}'")
                     if not line.startswith("    def "):
                         print("BAD INDENTATION suspected.")

    if modified:
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print("Notebook saved successfully.")
    else:
        print("No changes needed (methods exist).")

except Exception as e:
    print(f"Error: {e}")
