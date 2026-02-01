
import json

nb_path = "/home/eveselove/PLANB/PLANB.ipynb"

try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    last_cell = nb['cells'][-1]
    print("Last cell source:")
    print("".join(last_cell['source']))

except Exception as e:
    print(f"Error: {e}")
