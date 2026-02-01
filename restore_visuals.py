import json
import re

# --- 1. NEW & FIXED CODE ---

COLORS_CODE = """
COLORS = {
    'primary': '#1f77b4',
    'secondary': '#ff7f0e', 
    'positive': '#2ca02c',
    'negative': '#d62728',
    'plan': '#3498db',
    'fact': '#2ecc71',
    'muted': '#7f7f7f',
    'background': '#f0f0f0'
}
MONTHS = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
MONTH_MAP = {m: i for i, m in enumerate(MONTHS, 1)}
MONTH_MAP_REV = {i: m for i, m in enumerate(MONTHS, 1)}

def get_cell_style(val):
    try:
        if val > 0: return '#e8f5e9', f'+{val}%'
        if val < 0: return '#ffebee', f'{val}%'
    except: pass
    return '#ffffff', '-'

def create_bokeh_chart(x_range, title='', height=200):
    from bokeh.plotting import figure
    p = figure(x_range=x_range, height=height, title=title, toolbar_location=None, tools="hover")
    p.grid.grid_line_alpha = 0.3
    p.outline_line_color = None
    return p

def add_line_with_scatter(p, source, x, y, color, line_width=2, scatter_size=5, line_dash='solid'):
    l = p.line(x, y, source=source, color=color, line_width=line_width, line_dash=line_dash)
    s = p.scatter(x, y, source=source, color=color, size=scatter_size)
    return l
"""

UPDATE_DEPTS_CODE = """    def _update_chart_depts(self):
        \"\"\"Топ-10 отделов по выручке (Bokeh)\"\"\"
        try:
            agg = self._get_cached_agg()
            if not agg or 'by_dept' not in agg:
                self.chart_depts_pane.object = None
                return
                
            df = agg['by_dept'].sort_values('План_Скорр', ascending=True).tail(10)
            if len(df) == 0:
                self.chart_depts_pane.object = None
                return

            depts = df['Отдел'].apply(lambda x: x[:30] + '..' if len(x)>30 else x).tolist()
            plan = (df['План_Скорр']/1e6).tolist()
            fact = (df['Выручка_2025']/1e6).tolist()
            
            from bokeh.models import ColumnDataSource, HoverTool, Legend
            from bokeh.plotting import figure
            from bokeh.transform import dodge

            source = ColumnDataSource(data={'dept': depts, 'plan': plan, 'fact': fact})

            p = figure(y_range=depts, height=200, title="", toolbar_location=None, tools="")
            
            r1 = p.hbar(y=dodge('dept', 0.15, range=p.y_range), right='plan', height=0.2, source=source, color='#3498db')
            r2 = p.hbar(y=dodge('dept', -0.15, range=p.y_range), right='fact', height=0.2, source=source, color='#2ecc71')

            p.x_range.start = 0
            p.ygrid.grid_line_color = None
            p.xaxis.axis_label = "Выручка, млн руб."
            p.axis.axis_label_text_font_size = "10px"
            p.axis.major_label_text_font_size = "9px"
            
            legend = Legend(items=[("План", [r1]), ("Факт 25", [r2])], location="center")
            legend.orientation = "horizontal"
            legend.label_text_font_size = "8px"
            legend.spacing = 1
            legend.padding = 2
            p.add_layout(legend, 'below')
            
            p.add_tools(HoverTool(tooltips=[('Отдел', '@dept'), ('План', '@plan{0.1f}M'), ('Факт', '@fact{0.1f}M')]))
            
            self.chart_depts_pane.object = p
        except Exception as e:
            print(f"Error in chart_depts: {e}")
            self.chart_depts_pane.object = f"<div style='color:red;font-size:9px;'>Error: {e}</div>"
"""

UPDATE_CHARTS_WRAPPER = """    def _update_charts(self):
        \"\"\"Безопасное обновление всех графиков\"\"\"
        for method_name in ['_update_chart_main', '_update_chart_branches', '_update_chart_seasonality', '_update_pivot_table', '_update_chart_depts']:
             if hasattr(self, method_name):
                try:
                    getattr(self, method_name)()
                except Exception as e:
                    print(f"❌ Error in {method_name}: {e}")
"""

# --- 2. EXTRACTION LOGIC ---

def extract_method(source_lines, method_name):
    start_idx = -1
    for i, line in enumerate(source_lines):
        if f"def {method_name}" in line:
            start_idx = i
            break
    if start_idx == -1: return None
    
    end_idx = len(source_lines)
    base_indent = len(source_lines[start_idx]) - len(source_lines[start_idx].lstrip())
    
    for i in range(start_idx + 1, len(source_lines)):
        line = source_lines[i]
        if line.strip() and not line.startswith('#'):
            indent = len(line) - len(line.lstrip())
            if indent <= base_indent:
                end_idx = i
                break
    return "".join(source_lines[start_idx:end_idx])

# --- 3. MAIN EXECUTION ---

targets = ["/home/eveselove/PLANB/PLANB.ipynb", "/home/eveselove/PLAN/PLAN.ipynb"]
source_path = "/home/eveselove/PLAN/PLAN.ipynb"

# Extract original methods from source
with open(source_path, 'r') as f:
    src_nb = json.load(f)
    
extracted_methods = {}
src_cells = src_nb['cells']
# Flatten source lines for extraction if needed, or search cells
# We assume methods are in the class cell.
for cell in src_cells:
    src = cell.get('source', [])
    full_src = "".join(src)
    if "class PlanDashboard" in full_src:
        for m in ['_update_chart_main', '_update_chart_branches', '_update_chart_seasonality', '_update_pivot_table', 'view']:
            code = extract_method(src, m)
            if code: extracted_methods[m] = code

# Override/Add our fixes
extracted_methods['_update_chart_depts'] = UPDATE_DEPTS_CODE
extracted_methods['_update_charts'] = UPDATE_CHARTS_WRAPPER

for fpath in targets:
    try:
        with open(fpath, 'r') as f:
            nb = json.load(f)
            
        print(f"Patching {fpath}...")
        
        # 1. Update Constants Cell
        for cell in nb['cells']:
            src = "".join(cell.get('source', []))
            if "MONTH_MAP =" in src:
                # Replace content logic or append?
                # Safer to append constants if missing, but we rewrite the cell if it looks like the constants cell
                if "COLORS =" not in src:
                    cell['source'] = [src + "\n" + COLORS_CODE]
                elif "'muted':" not in src:
                     # Patch muted color
                     cell['source'] = [src.replace("COLORS = {", COLORS_CODE + "\n# Old COLORS replaced\n_OLD_COLORS = {")]
                break
        
        # 2. Update Class Methods and Init
        for cell in nb['cells']:
             src = cell.get('source', [])
             full_src = "".join(src)
             if "class PlanDashboard" in full_src:
                 new_source = []
                 # Fix __init__ for Bokeh pane
                 for line in src:
                     if "self.chart_depts_pane =" in line and "HTML" in line:
                         line = "        self.chart_depts_pane = pn.pane.Bokeh(sizing_mode='stretch_width', height=200)\n"
                     new_source.append(line)
                 
                 # Append new methods at the end of the class
                 # Find last indented line
                 last_idx = len(new_source)
                 for i in range(len(new_source)-1, 0, -1):
                     if new_source[i].strip():
                         last_idx = i + 1
                         break
                 
                 # Inject methods source
                 injection = "\n"
                 for m_name, m_code in extracted_methods.items():
                     if m_code:
                         # Simple check to avoid double definition (though python allows redef)
                         # We append, so it overrides any previous definition in the cell
                         injection += "\n" + m_code + "\n"
                 
                 # Insert before end
                 new_source.insert(last_idx, injection)
                 cell['source'] = new_source
                 break
        
        with open(fpath, 'w') as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print(f"Updated {fpath}")
        
    except Exception as e:
        print(f"Error processing {fpath}: {e}")

