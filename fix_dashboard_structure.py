
import json

nb_path = "/home/eveselove/PLANB/PLANB.ipynb"

def fix_dashboard_structure():
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    found_fix = False
    
    for cell in nb['cells']:
        source = cell.get('source', [])
        
        # Check if this cell has the issue
        # We look for "def get_sidebar" followed later by "self.corr_history ="
        # And check if they are in the wrong order relative to method structure
        
        # We'll just look for the specific lines index
        get_sidebar_idx = -1
        orphaned_start_idx = -1
        
        for i, line in enumerate(source):
            if "def get_sidebar(self):" in line:
                get_sidebar_idx = i
            if "self.corr_history, self.corr_history_idx = [], -1" in line:
                orphaned_start_idx = i
                
        if get_sidebar_idx != -1 and orphaned_start_idx != -1 and orphaned_start_idx > get_sidebar_idx:
            print(f"Found broken structure in cell. get_sidebar at {get_sidebar_idx}, orphaned code at {orphaned_start_idx}")
            
            # Identify the full block of get_sidebar
            # It starts at get_sidebar_idx.
            # It ends where the indentation drops or at orphaned_start_idx?
            # get_sidebar has "return sidebar" around line 13993 (relative to file).
            
            # Let's verify end of get_sidebar
            sidebar_end_idx = -1
            for i in range(get_sidebar_idx, orphaned_start_idx):
                if "return sidebar" in source[i]:
                    sidebar_end_idx = i + 1 # Include the return line (and maybe blank lines?)
                    break
            
            if sidebar_end_idx == -1:
                print("Could not find end of get_sidebar")
                continue
                
            # Grab the sidebar code block
            sidebar_code = source[get_sidebar_idx:sidebar_end_idx]
            
            # Grab the orphaned code block
            # It starts at orphaned_start_idx
            # It ends before the start of the next method?
            # Next method is _update_compact_stats at 14031
            next_method_idx = -1
            for i in range(orphaned_start_idx, len(source)):
                if "def _update_compact_stats(self):" in source[i]:
                    next_method_idx = i
                    break
            
            if next_method_idx == -1:
                # Maybe it's the last thing?
                next_method_idx = len(source)
                
            orphaned_code = source[orphaned_start_idx:next_method_idx]
            
            # Remove both blocks
            # We want:
            # ... previous code ...
            # orphaned_code
            # sidebar_code
            # ... next code ...
            
            # Check for any gap between sidebar_end_idx and orphaned_start_idx
            gap_code = source[sidebar_end_idx:orphaned_start_idx]
            
            new_source = source[:get_sidebar_idx] + gap_code + orphaned_code + ["\n"] + sidebar_code + ["\n"] + source[next_method_idx:]
            
            cell['source'] = new_source
            found_fix = True
            print("Fixed structure: Moved orphaned initialization code before get_sidebar.")
            break
            
    if found_fix:
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print("Notebook saved with structural fix.")
    else:
        print("No structural issue found (or already fixed).")

if __name__ == "__main__":
    try:
        fix_dashboard_structure()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
