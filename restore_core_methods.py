
import json
import pandas as pd
import panel as pn

nb_path = "/home/eveselove/PLANB/PLANB.ipynb"

try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    modified = False

    restored_methods = [
        "    def _setup_table(self):\n",
        "        \"\"\"Инициализация главной таблицы\"\"\"\n",
        "        # Конфиг колонок - минимальный для начала\n",
        "        self.table = pn.widgets.Tabulator(\n",
        "            value=pd.DataFrame(),\n",
        "            pagination='remote',\n",
        "            page_size=20,\n",
        "            sizing_mode='stretch_width',\n",
        "            height=600,\n",
        "            theme='bootstrap4',\n",
        "            configuration={\n",
        "                'columnDefaults': {'headerSort': False},\n",
        "                'keybindings': {\n",
        "                    'navNext': False,\n",
        "                    'navDown': ['ArrowDown', 'Enter', 'Tab'],\n",
        "                    'navPrev': 'Shift+Tab',\n",
        "                    'navUp': 'ArrowUp'\n",
        "                }\n",
        "            },\n",
        "            disabled=False\n",
        "        )\n",
        "        # Привязка события редактирования (пока заглушка)\n",
        "        self.table.on_edit(self._on_edit)\n",
        "\n",
        "    def _on_edit(self, event):\n",
        "        \"\"\"Обработка редактирования ячейки\"\"\"\n",
        "        try:\n",
        "            row_idx = event.row\n",
        "            col = event.column\n",
        "            val = event.value\n",
        "            # self.df.loc[row_idx, col] = val # Simple update\n",
        "            # TODO: Add complex logic (history, redistribution)\n",
        "            print(f\"Edit: {row_idx}, {col} -> {val}\")\n",
        "        except Exception as e:\n",
        "            print(f\"Edit Error: {e}\")\n",
        "\n",
        "    def _get_filtered_df(self):\n",
        "        \"\"\"Фильтрация основного датафрейма\"\"\"\n",
        "        df = self.df.copy()\n",
        "        # Простейшая фильтрация (расширить при необходимости)\n",
        "        try:\n",
        "            if hasattr(self, 'filters'):\n",
        "                # Пример фильтрации по филиалу\n",
        "                if 'branch' in self.filters and self.filters['branch'].value:\n",
        "                    vals = self.filters['branch'].value\n",
        "                    if vals: df = df[df['Филиал'].isin(vals)]\n",
        "        except Exception as e:\n",
        "            print(f\"Filter Error: {e}\")\n",
        "        return df\n",
        "\n",
        "    def _get_display_df(self):\n",
        "        \"\"\"Подготовка DF для отображения\"\"\"\n",
        "        df = self._get_filtered_df()\n",
        "        # Сортировка или выбор колонок\n",
        "        cols = ['Филиал', 'Отдел', 'Месяц', 'План_Скорр']\n",
        "        safe_cols = [c for c in cols if c in df.columns]\n",
        "        # Возвращаем весь DF для простоты, Tabulator сам разберется с колонками если не заданы\n",
        "        return df\n",
        "\n",
        "    def _update_stats(self):\n",
        "        \"\"\"Обновление статистики (заглушка)\"\"\"\n",
        "        if hasattr(self, 'stats'):\n",
        "             self.stats.object = f\"<b>Rows: {len(self.table.value)}</b>\"\n",
        "\n"
    ]
    
    # Insert after `_get_csv_data` (which calls _get_display_df, so typically defined after, or python checks at runtime)\n",
    # Order inside class doesn't matter for runtime, but for reading flow.\n",
    # We will search for `_get_csv_data` we added last time.\n",
    
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = cell['source']
            new_source = []
            
            inserted = False
            for line in source:
                new_source.append(line)
                
                # Look for end of _get_csv_data\n",
                if "return io.StringIO(\"Error exporting data\")" in line and not inserted:
                    new_source.append("\n")
                    new_source.extend(restored_methods)
                    inserted = True
                    modified = True
            
            if len(new_source) != len(source):
                cell['source'] = new_source
                if inserted: \n",
                    break

    if modified:
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print("Notebook saved successfully.")
    else:
        print("Could not find insertion point (after _get_csv_data).")

except Exception as e:
    print(f"Error: {e}")
