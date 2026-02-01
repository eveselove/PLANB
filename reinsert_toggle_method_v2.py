
import json
import sys

nb_path = "/home/eveselove/PLANB/PLANB.ipynb"

try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    modified = False

    # Goal: Insert _toggle_settings_panel into PlanDashboard class (which starts at 6046 in previous view)
    # search for "class PlanDashboard:"
    # insert method after __init__
    
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = cell['source']
            new_source = []
            
            # Check if already exists (again, to be safe)
            already_present = False
            for line in source:
                if "def _toggle_settings_panel(self, event):" in line:
                    already_present = True
                    break
            
            if already_present:
                 print("Method seems to be present already.")
                 # If present, maybe I should print it to debug where it is?
                 pass 
                 
            inserted = False
            for line in source:
                if "self._cached_filtered_df = None" in line and not inserted and not already_present:
                     # Insert correct method definition in __init__? NO.
                     # It should be a method of the class, not inside init.
                     pass 
                
                # Let's insert it AFTER __init__ method finishes? 
                # Finding the end of __init__ is hard reliably without parsing.
                # But we can find the NEXT method definition usually.
                
                # Let's look for "    def _init_ui(self):" or similar, or just insert at the end of cell if the cell contains the whole class?
                # Usually class is split across cells or in one big cell.
                # In previous view, class starts at line 6046.
                
                # Let's try to insert it before "def view(self):" again, but making sure we are inside the class.
                # The previous reinsert failed because "def view(self):" might be in a different cell?
                
                # Let's search for any method starting with "    def _" inside the class.
                pass

            # Search for "def _get_display_df(self):" or "def _update_stats(self):" which are likely methods.
            for line in source:
                if "    def view(self):" in line and not inserted and not already_present:
                     new_source.append("    def _toggle_settings_panel(self, event):\n")
                     new_source.append("        \"\"\"Переключает видимость панели настроек\"\"\"\n")
                     new_source.append("        try:\n")
                     new_source.append("            new_state = event.new\n")
                     new_source.append("            if hasattr(self, '_sliders_container'):\n")
                     new_source.append("                self._sliders_container.visible = new_state\n")
                     new_source.append("            if hasattr(self, '_sliders_btn'):\n")
                     new_source.append("                self._sliders_btn.name = '⚙️ Скрыть' if new_state else '⚙️ Настройки'\n")
                     new_source.append("        except Exception as e:\n")
                     new_source.append("            print(f\"Toggle error: {e}\")\n")
                     new_source.append("\n")
                     new_source.append(line)
                     inserted = True
                     modified = True
                else:
                    new_source.append(line)
            
            if len(new_source) != len(source) or modified:
                cell['source'] = new_source
                if modified:
                     break

    if modified:
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print("Notebook saved successfully.")
    else:
        print("Still could not find insertion point!")

except Exception as e:
    print(f"Error: {e}")
