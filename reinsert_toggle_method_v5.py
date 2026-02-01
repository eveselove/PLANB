
import json
import sys

nb_path = "/home/eveselove/PLANB/PLANB.ipynb"

try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    modified = False

    # Goal: Insert _toggle_settings_panel RIGHT AFTER "class PlanDashboard:" line.
    # This is the most reliable way as "class PlanDashboard:" is unique.
    
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = cell['source']
            new_source = []
            
            # Check duplication
            already_present = False
            for line in source:
                if "def _toggle_settings_panel(self, event):" in line:
                    already_present = True
                    break
            
            inserted = False
            for line in source:
                
                # Insert AFTER class definition
                if "class PlanDashboard:" in line and not inserted and not already_present:
                     new_source.append(line)
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
        print("Could not find class definition or method already exists.")

except Exception as e:
    print(f"Error: {e}")
