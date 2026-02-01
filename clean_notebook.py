import json

nb_path = "/home/eveselove/PLANB/PLANB.ipynb"
with open(nb_path, 'r') as f:
    nb = json.load(f)

# Keep cells: 0..13 and 15 (export)
# Note: 13 is the big cell with class and initialization
# 14 is diagnostics (remove)
# 15 is export (keep)
# 16+ is diagnostics/garbage (remove)

keep_indices = list(range(14)) + [15]
new_cells = [nb['cells'][i] for i in keep_indices if i < len(nb['cells'])]

# Add final View cell
view_cell = {
 "cell_type": "code",
 "execution_count": None,
 "metadata": {},
 "outputs": [],
 "source": [
  "# Запуск отображения\n",
  "dashboard.view()"
 ]
}
new_cells.append(view_cell)

# Clear outputs and execution counts
for cell in new_cells:
    if "outputs" in cell:
        cell["outputs"] = []
    if "execution_count" in cell:
        cell["execution_count"] = None

nb['cells'] = new_cells

# Remove widgets state if present (clean metadata)
if "widgets" in nb.get("metadata", {}):
    del nb["metadata"]["widgets"]

with open(nb_path, 'w') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Notebook cleaned.")
