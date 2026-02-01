
import json
import sys

nb_path = "/home/eveselove/PLANB/PLANB.ipynb"

try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    modified = False

    # Goal: Insert _toggle_settings_panel into PlanDashboard class (starts at 6048 in last view)
    # The previous attempts failed to find the insertion point because they were looking for lines that might be split differently or whitespaces.
    
    # We will look for "def __init__(self, df, gc_client=None, df_roles=None):"
    
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = cell['source']
            new_source = []
            
            # Check if already present to avoid duplication
            already_present = False
            for line in source:
                if "def _toggle_settings_panel(self, event):" in line:
                    already_present = True
                    break
            
            inserted = False
            for line in source:
                # Inserting before __init__ is inside the class if indented properly
                if "def __init__(self, df, gc_client=None, df_roles=None):" in line and not inserted and not already_present:
                     # Add method BEFORE __init__
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
            
            # If we didn't insert before init, maybe init is the first method?
            # Let's try to append AFTER Init block if we didn't do it yet?
            # No, that's complex.
            
            if len(new_source) != len(source) or modified:
                cell['source'] = new_source
                if modified:
                     break

    if modified:
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print("Notebook saved successfully.")
    else:
        print("Could not find insertion point!")

except Exception as e:
    print(f"Error: {e}")
