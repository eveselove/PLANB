
import pandas as pd
_orig_read = pd.read_csv
def _read_patched(*args, **kwargs):
    try:
        df = _orig_read(*args, **kwargs)
    except Exception as e:
        print(f"Read error: {e}")
        return pd.DataFrame()
        
    # Patch columns missing in dashboard_data.csv but required by notebook logic
    if 'Филиал' in df.columns:
        if 'Филиал Корр' not in df.columns: df['Филиал Корр'] = df['Филиал']
    
    if 'Код эксперта' not in df.columns: df['Код эксперта'] = 0
    if 'Площадь' not in df.columns: df['Площадь'] = 100 # Dummy
    if 'Правило' not in df.columns: df['Правило'] = ''
    
    return df

pd.read_csv = _read_patched


def display(*args): pass
import matplotlib.pyplot as plt
def show(*args): pass
plt.show = show
#!/usr/bin/env python
# coding: utf-8

# In[1]:


pass #.system('pip install panel --break-system-packages -q')


# In[2]:


import panel as pn
pn.extension('tabulator')


# In[3]:


import pandas as pd

# ID таблицы из ссылки
sheet_id = '1q_hU5hQJ2aQXadGKJak2BY2DWltGTrhpi_7UyRVbXVM'
# Формируем ссылку для экспорта в формате CSV
url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv'

# Чтение данных в DataFrame
df = pd.read_csv(url)

# Вывод первых 5 строк таблицы
display(df.head())


# In[4]:


# @title План 2026
# Преобразование (unpivot) таблицы: месяцы из колонок переносим в строки
# Используем новое имя колонки 'Филиал'
df_plan_2026 = df.melt(id_vars=['Филиал'], var_name='Месяц', value_name='План')

# Изменение порядка столбцов: Месяц, Филиал, План
df_plan_2026 = df_plan_2026[['Месяц', 'Филиал', 'План']]

# Для совместимости с предыдущим кодом
df_melted = df_plan_2026

# Вывод первых строк преобразованной таблицы
display(df_plan_2026.head())


# In[5]:


# @title Корректировка продаж Владимир
import pandas as pd

sheet_id_3 = '1Uh_5wP8MFJUgaHm_JLJkwQvzKWTyWqQW5LOr3p29h_o'
gid_3 = '129997454'
url_3 = '/home/eveselove/PLAN/dashboard_data.csv'

df_sales_detail = pd.read_csv(url_3)

# Преобразование (melt) таблицы: месяцы из колонок переносим в строки
df_sales_detail = df_sales_detail if 'Выручка' in df_sales_detail.columns else df_sales_detail.melt(
    id_vars=['Филиал', 'Отдел', 'Код эксперта', 'Филиал Корр'],
    var_name='Месяц',
    value_name='Выручка'
)

# Преобразование выручки в число (обработка запятых и пробелов)
df_sales_detail['Выручка'] = df_sales_detail['Выручка'].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
df_sales_detail['Выручка'] = pd.to_numeric(df_sales_detail['Выручка'], errors='coerce')

# Удаление строк с NaN значениями
df_sales_detail = df_sales_detail.dropna(subset=['Выручка'])

# Создание сводной таблицы (группировка и суммирование)
df_sales_summary = df_sales_detail.groupby(
    ['Филиал', 'Отдел', 'Филиал Корр', 'Месяц'], as_index=False
)['Выручка'].sum()

# Добавление колонки Год
df_sales_summary['Год'] = 2025

print("Сводная таблица (первые 5 строк):")
display(df_sales_summary.head())


# In[6]:


import pandas as pd
import numpy as np

# 1. Загрузка данных о продажах
# ID таблицы продаж
sales_sheet_id = '1Uh_5wP8MFJUgaHm_JLJkwQvzKWTyWqQW5LOr3p29h_o'
# Ссылка для экспорта
sales_url = f'https://docs.google.com/spreadsheets/d/{sales_sheet_id}/export?format=csv'

df_sales_2023_2025 = pd.read_csv(sales_url)

print(f"После pd.read_csv (исходное количество строк): {len(df_sales_2023_2025)}")

# 2. Преобразование 'Выручка' в числовой тип
# Удаление пробелов (разделителей тысяч) и замена запятых на точки
df_sales_2023_2025['Выручка'] = df_sales_2023_2025['Выручка'].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
df_sales_2023_2025['Выручка'] = pd.to_numeric(df_sales_2023_2025['Выручка'], errors='coerce')

# Очистка строковых колонок от лишних пробелов
df_sales_2023_2025['Филиал'] = df_sales_2023_2025['Филиал'].astype(str).str.strip()
df_sales_2023_2025['Отдел'] = df_sales_2023_2025['Отдел'].astype(str).str.strip()
df_sales_2023_2025['Месяц'] = df_sales_2023_2025['Месяц'].astype(str).str.strip()

# --- УДАЛЕНИЕ ДУБЛИКАТОВ ---
# Удаляем строки, которые полностью совпадают по измерениям И сумме выручки
before_dedup = len(df_sales_2023_2025)
df_sales_2023_2025.drop_duplicates(subset=['Филиал', 'Отдел', 'Год', 'Месяц', 'Выручка'], inplace=True)
after_dedup = len(df_sales_2023_2025)
print(f"Удалено полных дубликатов (с учетом выручки): {before_dedup - after_dedup}")

# Агрегация оставшихся записей: группировка по ключевым столбцам и суммирование Выручки и Чеков
# Это объединит разрозненные транзакции (если они есть), которые не являются полными дублями
df_sales_2023_2025 = df_sales_2023_2025.groupby(
    ['Филиал', 'Отдел', 'Год', 'Месяц'], as_index=False
).agg({'Выручка': 'sum', 'Чеки': 'sum'})

print(f"После groupby и агрегации (итоговое количество строк): {len(df_sales_2023_2025)}")

# 3. Создание DataFrame для вычетов
# Агрегируем df_sales_summary перед созданием deductions, чтобы избежать дубликатов при слиянии
deductions = df_sales_summary.groupby(['Филиал', 'Отдел', 'Месяц', 'Год'])['Выручка'].sum().reset_index().rename(columns={'Выручка': 'Deduction'})

# 4. Создание DataFrame для добавлений
# Агрегируем df_sales_summary перед созданием additions, чтобы избежать дубликатов при слиянии
# ВАЖНО: Выбираем только нужные колонки перед переименованием, чтобы избежать дублирования столбца 'Филиал'
additions_temp = df_sales_summary[['Филиал Корр', 'Отдел', 'Месяц', 'Год', 'Выручка']].rename(columns={'Филиал Корр': 'Филиал'})
additions = additions_temp.groupby(['Филиал', 'Отдел', 'Месяц', 'Год'])['Выручка'].sum().reset_index().rename(columns={'Выручка': 'Addition'})

# 5. Объединение и применение вычетов
df_sales_2023_2025 = pd.merge(df_sales_2023_2025, deductions, on=['Филиал', 'Отдел', 'Месяц', 'Год'], how='left')
df_sales_2023_2025['Выручка'] = df_sales_2023_2025['Выручка'] - df_sales_2023_2025['Deduction'].fillna(0)
df_sales_2023_2025.drop(columns=['Deduction'], inplace=True)

# 6. Объединение и применение добавлений
df_sales_2023_2025 = pd.merge(df_sales_2023_2025, additions, on=['Филиал', 'Отдел', 'Месяц', 'Год'], how='left')
df_sales_2023_2025['Выручка'] = df_sales_2023_2025['Выручка'] + df_sales_2023_2025['Addition'].fillna(0)
df_sales_2023_2025.drop(columns=['Addition'], inplace=True)

# 7. Округление и преобразование в целое число
df_sales_2023_2025['Выручка'] = df_sales_2023_2025['Выручка'].fillna(0).round(0).astype(int)

# 8. Алиас и отображение
df_sales = df_sales_2023_2025
display(df_sales_2023_2025.head())

print(f"После всех операций и мерджей: Всего строк {len(df_sales_2023_2025)}")
print(f"После всех операций и мерджей: Уникальных комбинаций {len(df_sales_2023_2025.drop_duplicates(subset=['Филиал', 'Отдел', 'Год', 'Месяц']))}")


# In[7]:


import numpy as np

# Преобразование колонки 'Выручка' в числовой тип (замена запятой на точку)
# Сначала приводим к строке, чтобы метод .str работал корректно, затем заменяем и конвертируем
df_sales_2023_2025['Выручка'] = df_sales_2023_2025['Выручка'].astype(str).str.replace(',', '.').astype(float)

# Расчет колонки 'Средний Чек'
df_sales_2023_2025['Средний Чек'] = df_sales_2023_2025['Выручка'] / df_sales_2023_2025['Чеки']

# Замена бесконечных значений (inf) и пустых (NaN) на 0 для Среднего Чека
df_sales_2023_2025['Средний Чек'] = df_sales_2023_2025['Средний Чек'].replace([np.inf, -np.inf], 0).fillna(0)

# Округление Среднего Чека до целого
df_sales_2023_2025['Средний Чек'] = df_sales_2023_2025['Средний Чек'].round(0).astype(int)

# Округление Выручки до целого (с обработкой пустых значений)
df_sales_2023_2025['Выручка'] = df_sales_2023_2025['Выручка'].fillna(0).round(0).astype(int)

# Вывод первых строк с новой колонкой
display(df_sales_2023_2025.head())


# In[8]:


# @title Площади магазинов
# ID третьей таблицы
area_sheet_id = '1yPANhEDRwf_CKMLLz5Wdov4Tx8HCgfS0ckyW7jv1ugQ'
# Формируем ссылку для экспорта
area_url = '/home/eveselove/PLAN/dashboard_data.csv'

# Чтение данных в DataFrame
df_area = pd.read_csv(area_url)

# Преобразование (unpivot) таблицы: филиалы из колонок переносим в строки
df_area = df_area.melt(id_vars=['Год', 'Месяц', 'Отдел'], var_name='Филиал', value_name='Площадь')

# --- Дополнение данных (2023-2026) ---
# Список месяцев для правильной сортировки
months_order = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
month_map = {m: i+1 for i, m in enumerate(months_order)}

# Уникальные значения
branches = df_area['Филиал'].unique()
departments = df_area['Отдел'].unique()
years = [2023, 2024, 2025, 2026]

# Создание полной сетки (Grid) всех комбинаций: Филиал * Отдел * Год * Месяц
# Используем MultiIndex для генерации
index = pd.MultiIndex.from_product([branches, departments, years, months_order], names=['Филиал', 'Отдел', 'Год', 'Месяц'])
df_full = pd.DataFrame(index=index).reset_index()

# Добавляем числовой номер месяца для сортировки
df_full['Month_Num'] = df_full['Месяц'].map(month_map)

# Объединяем с исходными данными
df_merged = pd.merge(df_full, df_area, on=['Филиал', 'Отдел', 'Год', 'Месяц'], how='left')

# Сортируем данные для корректного заполнения (по времени)
df_merged = df_merged.sort_values(by=['Филиал', 'Отдел', 'Год', 'Month_Num'])

# Заполняем пропуски методом forward fill (протягиваем последнее известное значение)
df_merged['Площадь'] = df_merged.groupby(['Филиал', 'Отдел'])['Площадь'].ffill()

# --- Фильтрация данных ---
# Оставляем данные только начиная с 2024 года
df_merged = df_merged[df_merged['Год'] >= 2024]

# Оставляем нужные колонки в правильном порядке
df_area = df_merged[['Филиал', 'Отдел', 'Месяц', 'Год', 'Площадь']]

# Вывод первых строк и примера заполнения для 2026 года
print("Первые строки (2024 год):")
display(df_area.head())
print("\nПример данных за 2026 год (заполненные):")
display(df_area[df_area['Год'] == 2026].head())

# --- Проверка заполнения площадей для 2024 и 2025 года ---
print("\n--- Проверка заполнения площадей (2024-2025) ---")

df_check_area = df_area[(df_area['Год'] >= 2024) & (df_area['Год'] <= 2025)].copy()

# Группировка для проверки заполнения всех месяцев
missing_area_entries = df_check_area[(df_check_area['Площадь'].isnull()) | (df_check_area['Площадь'] == 0)]

if not missing_area_entries.empty:
    print(f"⚠️ Обнаружены незаполненные или нулевые площади в 2024-2025 годах ({len(missing_area_entries)} записей):")
    display(missing_area_entries)
else:
    print("✅ Все месяцы в 2024 и 2025 годах заполнены данными по площадям (значения > 0).")

# Дополнительная сводка по годам
summary_2024_2025 = df_check_area.groupby('Год')['Площадь'].apply(lambda x: (x > 0).sum()).reset_index()
summary_2024_2025.columns = ['Год', 'Количество_записей_с_площадью_>_0']

total_entries_2024_2025 = df_check_area.groupby('Год').size().reset_index(name='Общее_количество_записей')

summary_final = pd.merge(total_entries_2024_2025, summary_2024_2025, on='Год', how='left')
summary_final['Процент_заполнения'] = (summary_final['Количество_записей_с_площадью_>_0'] / summary_final['Общее_количество_записей']) * 100

print("\nСводка заполнения площадей по 2024 и 2025 годам:")
display(summary_final)

# --- Дополнительная таблица для Тамбова (2024-2025) ---
print("\n--- Суммарные площади для филиала 'Тамбов' (2024-2025) ---")

df_tambov_area = df_area[
    (df_area['Филиал'] == 'Тамбов') &
    (df_area['Год'].isin([2024, 2025]))
].copy()

# Добавляем числовой номер месяца для сортировки
df_tambov_area['Month_Num'] = df_tambov_area['Месяц'].map(month_map)

# Группируем по году и месяцу, суммируем площади
summary_tambov_area = df_tambov_area.groupby(['Год', 'Месяц', 'Month_Num'])['Площадь'].sum().reset_index()

# Сортируем по году и номеру месяца
summary_tambov_area = summary_tambov_area.sort_values(by=['Год', 'Month_Num'])

# Убираем вспомогательную колонку
summary_tambov_area = summary_tambov_area[['Год', 'Месяц', 'Площадь']]

# Выводим результат
display(summary_tambov_area)

# --- Итоговая таблица с площадями по всем филиалам, отделам и месяцам ---
print("\n--- Итоговая таблица площадей после дополнения (все филиалы и отделы) ---")
display(df_area)


# In[9]:


# @title Правила для структуры продаж
# ID таблицы и GID (идентификатор листа)
new_sheet_id = '1yPANhEDRwf_CKMLLz5Wdov4Tx8HCgfS0ckyW7jv1ugQ'
gid = '2130598218'

# Формируем ссылку для экспорта конкретного листа
new_url = f'https://docs.google.com/spreadsheets/d/{new_sheet_id}/export?format=csv&gid={gid}'

# Чтение данных в DataFrame
df_rules_structure = pd.read_csv(new_url)

# Для совместимости
df_new_table = df_rules_structure

# Вывод первых строк
display(df_rules_structure.head())


# In[10]:


# @title Форматы магазинов
# Словарь для преобразования названий месяцев
month_map = {'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6, 'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12}

try:
    # --- Создание справочника форматов ---
    data_formats = {
        'Филиал': [
            'Вологда ТЦ', 'Иваново', 'Ярославль', 'Кострома Стройка', 'ЯрославльФрунзе',
            'Череповец ТЦ', 'Рыбинск', 'Тамбов', 'Владимир Розница', 'Владимир Лента',
            'Воронеж', 'Воронеж Московский Проспект', 'Москва Хаб'
        ],
        'Формат': [
            'Флагман', 'Флагман', 'Средний', 'Средний', 'Средний',
            'Средний', 'Средний', 'Средний', 'Мини', 'Мини',
            'Микро', 'Микро', 'Интернет'
        ]
    }
    df_formats = pd.DataFrame(data_formats)

    # --- Анализ старта продаж ---
    # Создаем копию для анализа
    df_temp = df_sales_2023_2025.copy()

    # Формируем дату для сортировки
    df_temp['Month_Num'] = df_temp['Месяц'].map(month_map)
    df_temp['Date'] = pd.to_datetime(df_temp['Год'].astype(str) + '-' + df_temp['Month_Num'].astype(str) + '-01')

    # Сортируем по дате (от ранней к поздней)
    df_temp = df_temp.sort_values('Date')

    # Оставляем только первую запись для каждого филиала
    df_start_sales = df_temp.drop_duplicates(subset=['Филиал'], keep='first')[['Филиал', 'Месяц', 'Год']]

    # Переименуем колонки для ясности
    df_start_sales = df_start_sales.rename(columns={'Месяц': 'Первый Месяц', 'Год': 'Первый Год'})

    # Объединяем с данными о форматах
    df_store_formats = pd.merge(df_start_sales, df_formats, on='Филиал', how='left')

    # Вывод результата
    print("Форматы магазинов:")
    display(df_store_formats.reset_index(drop=True))

except NameError:
    print("⚠️ Ошибка: Переменная 'df_sales_2023_2025' не найдена.")
    print("Пожалуйста, убедитесь, что вы выполнили ячейки с загрузкой и подготовкой данных о продажах (Продажи 2023-2025) перед запуском этой ячейки.")


# In[11]:


# @title 🔍 Глубокая проверка дубликатов (Audit)
# --- 1. Проверка СЫРЫХ данных (из файла) ---
print("--- 1. Проверка ИСХОДНЫХ данных (из файла) ---")
raw_check = pd.read_csv(sales_url)

# Нормализация
raw_check['Выручка_Clean'] = raw_check['Выручка'].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
raw_check['Выручка_Clean'] = pd.to_numeric(raw_check['Выручка_Clean'], errors='coerce')
raw_check['Филиал'] = raw_check['Филиал'].astype(str).str.strip()
raw_check['Отдел'] = raw_check['Отдел'].astype(str).str.strip()
raw_check['Месяц'] = raw_check['Месяц'].astype(str).str.strip()

# Фильтр 2024-2025
raw_check = raw_check[raw_check['Год'].isin([2024, 2025])]

# Полные дубликаты (включая сумму)
full_dupes = raw_check[raw_check.duplicated(subset=['Филиал', 'Отдел', 'Год', 'Месяц', 'Выручка_Clean'], keep=False)]
print(f"Полных дубликатов в исходнике: {len(full_dupes)}")

if len(full_dupes) > 0:
    display(full_dupes.head())
else:
    print("✅ В исходном файле полных дублей нет.")

# --- 2. Проверка ОБРАБОТАННЫХ данных (df_sales_2023_2025) ---
print("\n--- 2. Проверка ОБРАБОТАННЫХ данных (используемых в расчете) ---")
try:
    # Проверка уникальности ключей
    processed_dupes = df_sales_2023_2025[df_sales_2023_2025.duplicated(subset=['Филиал', 'Отдел', 'Год', 'Месяц'], keep=False)]
    print(f"Дубликатов ключей в итоговой таблице: {len(processed_dupes)}")

    if len(processed_dupes) > 0:
        print("⚠️ Найдено дублирование строк в итоговой таблице!")
        display(processed_dupes.sort_values(['Филиал', 'Отдел', 'Год', 'Месяц']).head())
    else:
        print("✅ Итоговая таблица чиста: каждая комбинация (Филиал+Отдел+Год+Месяц) уникальна.")

    # Конкретный пример
    print("\nПример: Ярославль / Краски / июл 2025:")
    example = df_sales_2023_2025[
        (df_sales_2023_2025['Филиал'] == 'Ярославль') &
        (df_sales_2023_2025['Отдел'] == '8. Краски') &
        (df_sales_2023_2025['Год'] == 2025) &
        (df_sales_2023_2025['Месяц'] == 'июл')
    ]
    display(example)

except NameError:
    print("⚠️ Переменная df_sales_2023_2025 не найдена. Запустите основной код расчета.")


# In[12]:


import pandas as pd

# ID таблицы и GID новой вкладки
sheet_id_new = '1q_hU5hQJ2aQXadGKJak2BY2DWltGTrhpi_7UyRVbXVM'
gid_new = '358837029'
url_new = '/home/eveselove/PLAN/dashboard_data.csv'

# Чтение данных
df_raw_new = pd.read_csv(url_new)

print("Исходные колонки:", df_raw_new.columns.tolist())
display(df_raw_new.head())


# In[13]:


# --- Local Storage Setup ---
import json
import os

DATA_DIR = 'data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Dummy credentials object to avoid breaking code that expects it, though we'll ignore it
creds = None
gc = None

from datetime import datetime
import pandas as pd

# Преобразование в плоскую таблицу
# Определяем id_vars (колонки, которые НЕ являются месяцами)
id_vars = [col for col in df_raw_new.columns if col in ['Отдел', 'Филиал']]

# Если нужных колонок нет, пробуем найти похожие или используем все не-месяцы
if not id_vars:
    id_vars = df_raw_new.columns[:2].tolist()

df_flat = df_raw_new if 'Выручка' in df_raw_new.columns else df_raw_new.melt(
    id_vars=id_vars,
    var_name='Месяц',
    value_name='Выручка'
)

# 1. Очистка и преобразование Выручки в число (убираем пробелы)
df_flat['Выручка'] = df_flat['Выручка'].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
df_flat['Выручка'] = pd.to_numeric(df_flat['Выручка'], errors='coerce')

# 2. Подготовка формата под "Таблицу корректировок"
# Переименование Выручка -> Корректировка
df_flat = df_flat.rename(columns={'Выручка': 'Корректировка'})

# Добавление даты и времени
df_flat['Дата'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Добавление пустой колонки Корр_Дельта
df_flat['Корр_Дельта'] = None

# Упорядочивание колонок: Филиал | Отдел | Месяц | Корректировка | Корр_Дельта | Дата
export_cols = ['Филиал', 'Отдел', 'Месяц', 'Корректировка', 'Корр_Дельта', 'Дата']

# Проверяем наличие всех колонок, добавляем если нет
for col in export_cols:
    if col not in df_flat.columns:
        df_flat[col] = None

# Итоговая выборка в нужном порядке
df_export = df_flat[export_cols]

print(f"Подготовлено к выгрузке: {len(df_export)} строк")
display(df_export.head())

# --- Экспорт в Google Sheets ---
export_sheet_id = '1q_hU5hQJ2aQXadGKJak2BY2DWltGTrhpi_7UyRVbXVM'
export_gid = '1311408195'

try:
    # Используем глобальный gc, если он есть, иначе авторизуемся
    if 'gc' not in globals() or gc is None:
        # from google.colab import auth
        # from google.auth import default
        # import gspread
        pass # auth.authenticate_user()
        creds = None
        gc = None

    sh = gc.open_by_key(export_sheet_id) if gc else None
    # Поиск вкладки по GID
    ws = next((w for w in sh.worksheets() if str(w.id) == export_gid), None) if sh else None

    if ws:
        ws.clear()
        # Подготовка данных: заголовки + строки
        # fillna('') заменяет пустые значения для корректной записи
        data_to_export = [df_export.columns.tolist()] + df_export.fillna('').astype(str).values.tolist()

        # Запись данных начиная с ячейки A1
        ws.update('A1', data_to_export)
        print(f"✅ Данные успешно выгружены во вкладку: {ws.title} (GID: {export_gid})")
    else:
        print(f"❌ Вкладка с GID {export_gid} не найдена в таблице.")

except Exception as e:
    print(f"⚠️ Ошибка при выгрузке: {e}")


# In[14]:


# === ГИБРИДНЫЙ ДАШБОРД ===
# === ВНЕДРЕННАЯ ЛОГИКА НАЧАЛО ===
# Доступ к файловой системе ограничен, поэтому логика встроена напрямую (Авто-обновление).

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import panel as pn
import logging
import json
import os
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, Legend
from bokeh.models.widgets.tables import HTMLTemplateFormatter
from bokeh.palettes import Category10

# Configure logging and warnings
warnings.filterwarnings('ignore')
warnings.simplefilter('ignore')

for logger_name in ['bokeh', 'panel', 'param', 'tornado', 'asyncio', 'websockets', 'root']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)
    logging.getLogger(logger_name).disabled = True

logging.disable(logging.CRITICAL)
pn.extension('tabulator', console_output='disable', notifications=False)

# --- Local Storage Setup ---
DATA_DIR = 'data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Dummy credentials object
creds = None
gc = None

# ============================================================================
# ПОЛНЫЙ ЦИКЛ: РАСЧЕТ + ДАШБОРД v37
# Двери: сезонный рост по кварталам (0→20→40→60→100%)
# Пол = MAX(Факт2024, Факт2025×1.06), Потолок = ручная корректировка
# Авто_Корр защищает от перезаписи при redistribute
# v37: Сохранение в Google Sheets вместо JSON
#   - Корр/Корр_Дельта → лист "Корректировки"
#   - K_up/K_down слайдеры → лист "Эластичность"
#   - Макс. прирост → лист "Лимиты_роста"
#   - Фильтры → лист "Фильтры"
# ============================================================================



# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

CONFIG = {
    'rounding_step': 10000,
    'corrections_sheet_id': '1q_hU5hQJ2aQXadGKJak2BY2DWltGTrhpi_7UyRVbXVM',
    'corrections_gid': '388745370',
    'coefficients_gid': '1109139095',  # Лист для хранения коэффициентов
    # Листы для сохранения настроек дашборда
    'settings_sheet_id': '1q_hU5hQJ2aQXadGKJak2BY2DWltGTrhpi_7UyRVbXVM',
    'gid_corrections': '2051875626',    # Корректировки
    'gid_elasticity': '1132562573',     # Эластичность
    'gid_limits': '1538821834',         # Лимиты роста
    'gid_compressor': '1304780210',     # Компрессор
    'gid_multipliers': '1405891321',    # Множители прироста/падения
    'gid_filters': '2113302054',        # Фильтры
}

# ============================================================================
# ОГРАНИЧЕНИЯ РОСТА ПО ОТДЕЛАМ
# ============================================================================

GROWTH_LIMITS = {
    'inflation_cap_pct': 6,
    'exempt_formats': ['Мини', 'Микро', 'Интернет', 'Интернет магазин'],
    'exempt_depts_inflation': ['8. Краски'],
    'branch_growth_cap_depts': ['4. Обои, плитка потолочная'],
}

# Бизнес-правила для расчёта плана
BUSINESS_RULES = {
    'MIN_PLAN_THRESHOLD': 20000,  # Минимальный порог плана (меньше - обнуляем)
}


def save_limits_local(limits_dict):
    """
    Сохраняет лимиты макс. роста в data/limits.json.
    limits_dict: {(branch, dept): max_growth_pct} или {"branch|||dept": max_growth_pct}
    """
    try:
        filepath = os.path.join(DATA_DIR, 'limits.json')
        # Конвертируем ключи-кортежи в строки
        limits_json = {}
        for k, v in limits_dict.items():
            if isinstance(k, tuple):
                key = f"{k[0]}|||{k[1]}"
            else:
                key = k
            if v is not None and v != '':
                limits_json[key] = int(v)

        data = {
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'limits': limits_json
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Лимиты сохранены: {len(limits_json)} записей")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения лимитов: {e}")
        return False


def load_limits_local():
    """
    Загружает лимиты макс. роста из data/limits.json.
    Возвращает {"branch|||dept": max_growth_pct}
    """
    try:
        filepath = os.path.join(DATA_DIR, 'limits.json')
        if not os.path.exists(filepath):
            return {}
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        limits = data.get('limits', {})
        print(f"📂 Лимиты загружены: {len(limits)} записей")
        return limits
    except Exception as e:
        print(f"⚠️ Ошибка загрузки лимитов: {e}")
        return {}


def save_compressor_local(compressor_dict):
    """
    Сохраняет настройки компрессора в data/compressor.json.
    compressor_dict: {(branch, dept): {'growth': float, 'decline': float}}
    """
    try:
        filepath = os.path.join(DATA_DIR, 'compressor.json')
        # Конвертируем ключи-кортежи в строки
        compressor_json = {}
        for k, v in compressor_dict.items():
            if isinstance(k, tuple):
                key = f"{k[0]}|||{k[1]}"
            else:
                key = k
            growth = v.get('growth', 1.0)
            decline = v.get('decline', 1.0)
            # Сохраняем только изменённые
            if growth != 1.0 or decline != 1.0:
                compressor_json[key] = {'growth': growth, 'decline': decline}

        data = {
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'compressor': compressor_json
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Компрессор сохранён: {len(compressor_json)} записей")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения компрессора: {e}")
        return False


def load_compressor_local():
    """
    Загружает настройки компрессора из data/compressor.json.
    Возвращает {(branch, dept): {'growth': float, 'decline': float}}
    """
    try:
        filepath = os.path.join(DATA_DIR, 'compressor.json')
        if not os.path.exists(filepath):
            return {}
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        compressor_json = data.get('compressor', {})
        compressor = {}
        for key, vals in compressor_json.items():
            parts = key.split('|||')
            if len(parts) == 2:
                branch, dept = parts
                compressor[(branch, dept)] = vals
        print(f"📂 Компрессор загружен: {len(compressor)} записей")
        return compressor
    except Exception as e:
        print(f"⚠️ Ошибка загрузки компрессора: {e}")
        return {}

DEFAULT_LOAD_COEFFICIENT = 1.0


def save_corrections_local(corrections_list):
    """
    Сохраняет корректировки в data/corrections.json.
    """
    try:
        filepath = os.path.join(DATA_DIR, 'corrections.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(corrections_list, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ Ошибка сохранения корректировок: {e}")
        return False



def load_corrections_local():
    """
    Загружает корректировки из data/corrections.json.
    """
    try:
        filepath = os.path.join(DATA_DIR, 'corrections.json')
        if not os.path.exists(filepath):
            return []

        with open(filepath, 'r', encoding='utf-8') as f:
            corrections = json.load(f)
        return corrections
    except Exception as e:
        print(f"⚠️ Ошибка загрузки корректировок: {e}")
        return []


def parse_month(val):
    """Преобразует месяц (число или текст) в int 1-12"""
    if val is None or val == '':
        return 0
    # Если уже число
    if isinstance(val, (int, float)):
        return int(val)
    # Если строка-число
    val_str = str(val).strip().lower()
    if val_str.isdigit():
        return int(val_str)
    # Текстовое название
    return MONTH_MAP.get(val_str, 0)


def save_filters_local(filters_dict):
    """
    Сохраняет фильтры в data/filters.json.
    """
    try:
        filepath = os.path.join(DATA_DIR, 'filters.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(filters_dict, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ Ошибка сохранения фильтров: {e}")
        return False



def load_filters_local():
    """
    Загружает фильтры из data/filters.json.
    """
    try:
        filepath = os.path.join(DATA_DIR, 'filters.json')
        if not os.path.exists(filepath):
            return {}
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Ошибка загрузки фильтров: {e}")
        return {}


def extract_city_from_branch(branch):
    """Извлекает город из названия филиала.

    Примеры:
        'ЯрославльФрунзе' → 'Ярославль'
        'КостромаСвердлова' → 'Кострома'
        'Рыбинск' → 'Рыбинск'
    """
    if pd.isna(branch):
        return 'Другой'

    branch_str = str(branch)

    # Ищем известные города
    for city in KNOWN_CITIES:
        if branch_str.startswith(city) or city in branch_str:
            return city

    # Если не нашли — возвращаем как есть (может быть сам город)
    return branch_str


def get_load_category(row):
    """Определяет категорию для коэффициента: Краски, Обои, Стратегический или Сопутствующий"""
    dept = row.get('Отдел', '')
    role = row.get('Роль', 'Сопутствующий')

    if '8. Краски' in dept or 'Краски' in dept:
        return 'Краски'
    elif '4. Обои' in dept or 'Обои' in dept:
        return 'Обои'
    else:
        return role  # Стратегический или Сопутствующий


def apply_load_coefficients(df, coefficients_growth=None, coefficients_decline=None, limits=None):
    """
    Применяет коэффициенты нагрузки по Магазин × Категория.

    Логика нормировки:
    1. V_i = Факт_i × Ползунок_i (виртуальный объём)
    2. K = План_Филиала / Σ(V_i) (нормировочный множитель)
    3. План_i = V_i × K

    Это гарантирует что сумма планов = цель, а ползунки управляют
    относительным распределением нагрузки между категориями.
    """
    if coefficients_growth is None:
        coefficients_growth = LOAD_COEFFICIENTS_GROWTH
    if coefficients_decline is None:
        coefficients_decline = LOAD_COEFFICIENTS_DECLINE
    if limits is None:
        limits = GROWTH_LIMITS

    df = df.copy()

    # Определяем категорию для каждой строки
    df['_load_category'] = df.apply(get_load_category, axis=1)

    # Определяем направление плана: рост или снижение
    if 'Выручка_2025' in df.columns:
        branch_totals = df.groupby(['Филиал', 'Месяц']).agg({
            'План': 'first',
            'Выручка_2025': 'sum'
        })
        branch_totals['_direction'] = np.where(
            branch_totals['План'] >= branch_totals['Выручка_2025'],
            'growth',
            'decline'
        )
        direction_map = branch_totals['_direction'].to_dict()
    else:
        direction_map = {}

    def get_direction(row):
        key = (row['Филиал'], row['Месяц'])
        return direction_map.get(key, 'growth')

    df['_plan_direction'] = df.apply(get_direction, axis=1)

    # Получаем коэффициент (ползунок) для каждой строки
    def get_coeff(row):
        branch = row['Филиал']
        category = row['_load_category']
        direction = row['_plan_direction']

        if direction == 'decline':
            coeffs = coefficients_decline
        else:
            coeffs = coefficients_growth

        branch_coeffs = coeffs.get(branch, {})
        return branch_coeffs.get(category, DEFAULT_LOAD_COEFFICIENT)

    df['_slider'] = df.apply(get_coeff, axis=1)

    # Виртуальный объём: V_i = Факт_i × Ползунок_i
    # Используем Rev_2025_Norm (нормализованную выручку) если есть, иначе Выручка_2025
    # Это важно для филиалов, которые были на ремонте (Владимир Лента)
    base_rev = df['Rev_2025_Norm'] if 'Rev_2025_Norm' in df.columns else df['Выручка_2025']
    # Fallback если колонка есть, но там NaN (хотя fillna(0) ниже поможет)

    df['_V'] = base_rev.fillna(0) * df['_slider']

    # Нормировочный множитель K для каждого филиала-месяца
    # K = План / Σ(V_i)
    df['_sum_V'] = df.groupby(['Филиал', 'Месяц'])['_V'].transform('sum')

    # Новый вес = V_i / Σ(V_i) = (Факт_i × Ползунок_i) / Σ(Факт × Ползунок)
    # Это эквивалентно: План_i = План × (V_i / Σ(V_i))
    df['Final_Weight'] = np.where(
        df['_sum_V'] > 0,
        df['_V'] / df['_sum_V'],
        df['Final_Weight']  # Сохраняем старый вес если сумма = 0
    )
    # Инициализация Базового веса (копия чистого веса до компрессии)
    if 'Base_Weight' not in df.columns:
        df['Base_Weight'] = df['Final_Weight'].copy()

    direction_counts = df.groupby(['Филиал', 'Месяц'])['_plan_direction'].first().value_counts()


    non_one = (df['_slider'] != 1.0).sum()


    # Убираем временные колонки
    df = df.drop(columns=['_slider', '_V', '_sum_V', '_plan_direction', '_load_category'])

    return df










    # def set_coefficients(self, coeffs):
    #     """Устанавливает коэффициенты из словаря"""
    #     for fmt in coeffs:
    #         if fmt in self.sliders:
    #             for role in coeffs[fmt]:
    #                 if role in self.sliders[fmt]:
    #                     self.sliders[fmt][role].value = coeffs[fmt][role]

    # def print_coefficients(self):
    #     """Выводит текущие коэффициенты для копирования"""
    #     coeffs = self.get_coefficients()
    #     for fmt in coeffs:
    #         for role, val in coeffs[fmt].items():
    #             pass  # Вывод отключён

def parse_number(value, round_to=None):
    # Обработка пустых значений и NaN
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, str):
        v = value.strip().lower()
        if not v or v in ('nan', 'none', ''):
            return None
        # Специальные команды для удаления
        if v in ('x', 'd', 'del', 'delete', 'удалить', '-1'):
            return -1  # Специальное значение для удаления
    try:
        num = int(float(str(value).replace(' ', '').replace(',', '.')))
        if round_to and num > 0:
            num = int(round(num / round_to) * round_to)
        return num
    except:
        return None


def has_correction(df, mask=None):
    """Проверяет наличие корректировки (ручной или автоматической)"""
    check = df['Корр'].notna() | df['Корр_Дельта'].notna()
    # Также учитываем автоматические корректировки (например, плавный рост Дверей)
    if 'Авто_Корр' in df.columns:
        check = check | df['Авто_Корр'].notna()
    return check & mask if mask is not None else check


def calc_growth_pct(plan, fact):
    if isinstance(plan, pd.Series):
        return np.where(fact > 0, ((plan / fact - 1) * 100).round(1), 0.0)
    return round((plan / fact - 1) * 100, 1) if fact > 0 else 0.0


def recalc_row_metrics(df, mask, cols_available):
    plan = df.loc[mask, 'План_Скорр']
    rev25 = df.loc[mask, 'Выручка_2025']
    df.loc[mask, 'Прирост_%'] = np.where(rev25 > 0, ((plan / rev25 - 1) * 100).round(1), 0.0)
    if 'Выручка_2024' in cols_available:
        rev24 = df.loc[mask, 'Выручка_2024']
        df.loc[mask, 'Прирост_24_26_%'] = np.where(rev24 > 0, ((plan / rev24 - 1) * 100).round(1), 0.0)
    if 'Площадь_2026' in cols_available:
        area26 = df.loc[mask, 'Площадь_2026']
        df.loc[mask, 'Отдача_План'] = np.where(area26 > 0, (plan / area26).round(0), 0.0)
        if 'Отдача_2025' in cols_available:
            otd_plan = df.loc[mask, 'Отдача_План']
            otd_25 = df.loc[mask, 'Отдача_2025']
            df.loc[mask, 'Δ_Отдача_%'] = np.where((otd_25 > 0) & (otd_plan > 0), ((otd_plan / otd_25 - 1) * 100).round(1), 0.0)


def create_bokeh_chart(x_range, height=200, title=None):
    p = figure(x_range=x_range, height=height, sizing_mode='stretch_width', toolbar_location=None, tools='', title=title)
    p.xaxis.major_label_text_font_size = '10px'
    p.yaxis.major_label_text_font_size = '9px'
    p.xgrid.grid_line_color = None
    p.outline_line_color = None
    # Минимальные отступы
    p.min_border_left = 35
    p.min_border_right = 5
    p.min_border_top = 5
    p.min_border_bottom = 20
    if title:
        p.title.text_font_size = '11px'
    return p


def add_line_with_scatter(p, source, x_field, y_field, color, line_width=2, scatter_size=5, line_dash='solid'):
    line = p.line(x_field, y_field, source=source, line_width=line_width, color=color, line_dash=line_dash)
    p.scatter(x_field, y_field, source=source, size=scatter_size, color=color)
    return line


def create_filter_widget(name, options, inline=False, widget_type='choice'):
    """Создаёт виджет фильтра.
    widget_type options: 'choice' (MultiChoice), 'check' (CheckBoxGroup)
    """
    if widget_type == 'check':
        # Для чекбоксов value=[] обычно значит ничего не выбрано, но у нас логика "пусто = все"
        # Чтобы не путать пользователя, сделаем кнопку "Все" которая очищает выбор
        select = pn.widgets.CheckBoxGroup(
            name=name,
            options=list(options),
            value=[],
            inline=False,
            sizing_mode='stretch_width'
        )
    else:
        select = pn.widgets.MultiChoice(
            name=name,
            options=list(options),
            value=[],
            solid=False,
            sizing_mode='stretch_width'
        )

    # Кнопка сброса
    reset_btn = pn.widgets.Button(name='✕', width=25, height=25, button_type='light', align='center')

    def _reset_filter(event):
        select.value = []
    reset_btn.on_click(_reset_filter)

    indicator = pn.pane.HTML("", sizing_mode='stretch_width')
    return select, reset_btn, indicator

    def _reset_filter(event):
        select.value = []
    reset_btn.on_click(_reset_filter)

    indicator = pn.pane.HTML("", sizing_mode='stretch_width')
    return select, reset_btn, indicator


def format_indicator(values, max_show=3):
    if not values:
        return "<span style='color:#888;font-size:11px;'>все</span>"
    tags = " ".join([f"<span style='background:#e3f2fd;padding:1px 4px;border-radius:3px;font-size:10px;'>{str(v)[:8]}</span>" for v in values[:max_show]])
    if len(values) > max_show:
        tags += f" <span style='background:#bbdefb;padding:1px 4px;border-radius:3px;font-size:10px;'>+{len(values)-max_show}</span>"
    return f"<div style='display:flex;flex-wrap:wrap;gap:2px;'>{tags}</div>"


def get_cell_style(val):
    """Возвращает стиль ячейки с фоновым цветом - кэшируемая версия"""
    if val > 0:
        intensity = min(abs(val) / 30, 1)
        r = int(255 - intensity * 80)
        g = int(255 - intensity * 20)
        b = int(255 - intensity * 80)
        return f'rgb({r},{g},{b})', str(int(val))
    elif val < 0:
        intensity = min(abs(val) / 30, 1)
        r = int(255 - intensity * 20)
        g = int(255 - intensity * 80)
        b = int(255 - intensity * 80)
        return f'rgb({r},{g},{b})', str(int(val))
    else:
        return 'white', '0'


def get_table_formatters():
    templates = {
        'month': "<div style='text-align:center;'><%= {1:'янв',2:'фев',3:'мар',4:'апр',5:'май',6:'июн',7:'июл',8:'авг',9:'сен',10:'окт',11:'ноя',12:'дек'}[value] || value %></div>",
        'delta': "<div style='background:<%= value<=-20?\"#d73027\":value<=-10?\"#f46d43\":value<=-5?\"#fdae61\":value<0?\"#fee08b\":value<5?\"#d9ef8b\":value<10?\"#a6d96a\":value<20?\"#66bd63\":\"#1a9850\" %>;color:<%= (value<=-10||value>=20)?\"white\":\"black\" %>;font-weight:bold;padding:2px 6px;text-align:right;border-radius:3px;'><%= (value||0).toFixed(1) %>%</div>",
        'number': "<div style='text-align:right;padding:2px 6px;'><%= (value !== null && value !== undefined && value !== '') ? Math.round(value).toLocaleString('ru-RU') : '' %></div>",
        'corr': "<div style='text-align:right;padding:2px 6px;background:<%= value===0?\"#fff3cd\":\"transparent\" %>;'><%= (value !== null && value !== undefined && value !== '') ? value.toLocaleString('ru-RU') : '' %></div>",
        'corr_delta': "<div style='background:<%= !value||value===0?\"transparent\":value>0?\"#c6efce\":\"#ffc7ce\" %>;color:<%= !value||value===0?\"black\":value>0?\"#006100\":\"#9c0006\" %>;font-weight:<%= value?\"bold\":\"normal\" %>;text-align:right;padding:2px 6px;'><%= value ? (value>0?'+':'')+value.toLocaleString('ru-RU') : '' %></div>",
        'season': "<div style='text-align:right;padding:2px 6px;color:#555;'><%= value ? value.toFixed(1)+'%' : '' %></div>",
        'weight': "<div style='text-align:right;padding:2px 6px;color:#555;'><%= value ? (value*100).toFixed(2)+'%' : '' %></div>",
        'bool': "<div style='text-align:center;'><%= value ? '✓' : '' %></div>",
    }
    return {
        'Месяц': HTMLTemplateFormatter(template=templates['month']),
        'Прирост_%': HTMLTemplateFormatter(template=templates['delta']),
        'Прирост_24_26_%': HTMLTemplateFormatter(template=templates['delta']),
        'Δ_Отдача_%': HTMLTemplateFormatter(template=templates['delta']),
        'Δ_Площадь_%': HTMLTemplateFormatter(template=templates['delta']),
        'Корр': HTMLTemplateFormatter(template=templates['corr']),
        'Корр_Дельта': HTMLTemplateFormatter(template=templates['corr_delta']),
        'Расч_План': HTMLTemplateFormatter(template=templates['number']),
        'План_Скорр': HTMLTemplateFormatter(template=templates['number']),
        'Рекоменд': HTMLTemplateFormatter(template=templates['number']),
        'Выручка_2025': HTMLTemplateFormatter(template=templates['number']),
        'Выручка_2024': HTMLTemplateFormatter(template=templates['number']),
        'Выручка_2025_Норм': HTMLTemplateFormatter(template=templates['number']),
        'Площадь_2025': HTMLTemplateFormatter(template=templates['number']),
        'Площадь_2026': HTMLTemplateFormatter(template=templates['number']),
        'Отдача_План': HTMLTemplateFormatter(template=templates['number']),
        'Отдача_2025': HTMLTemplateFormatter(template=templates['number']),
        'Сезонность_Факт': HTMLTemplateFormatter(template=templates['season']),
        'Сезонность_План': HTMLTemplateFormatter(template=templates['season']),
        # Новые колонки
        'План': HTMLTemplateFormatter(template=templates['number']),
        'План_Расч': HTMLTemplateFormatter(template=templates['number']),
        '_План_Расч_Исх': HTMLTemplateFormatter(template=templates['number']),
        'Авто_Корр': HTMLTemplateFormatter(template=templates['number']),
        'Final_Weight': HTMLTemplateFormatter(template=templates['weight']),
        'is_network_format': HTMLTemplateFormatter(template=templates['bool']),
    }


# ============================================================================
# РАСПРЕДЕЛЕНИЕ ПЛАНА
# ============================================================================

def distribute_plan_for_group(group_df, target, fixed_mask=None):
    """Распределение по весам с учётом ручных корректировок

    Логика:
    1. Считаем "теоретический" план для ВСЕХ по весам (включая "Не считаем план")
    2. "Не считаем план" без корректировки получает план = 0
    3. Фиксированные (с корректировкой) получают свой ручной план
    4. Высвободившаяся разница перераспределяется на активных

    fixed_mask: отделы с ручными корректировками (Корр/Корр_Дельта)
    """
    g = group_df.copy()
    weights = g['Final_Weight'].copy() if 'Final_Weight' in g.columns else pd.Series(1/len(g), index=g.index)
    no_plan_mask = g['Правило'] == 'Не считаем план' if 'Правило' in g.columns else pd.Series(False, index=g.index)

    branch = g['Филиал'].iloc[0] if 'Филиал' in g.columns else ''
    month = g['Месяц'].iloc[0] if 'Месяц' in g.columns else ''

    if fixed_mask is None:
        fixed_mask = pd.Series(False, index=g.index)

    # "Не считаем план" БЕЗ корректировки — получают план 0, но их доля перераспределяется
    no_plan_without_corr = no_plan_mask & ~fixed_mask
    # "Не считаем план" С корректировкой — получают фиксированный план
    no_plan_with_corr = no_plan_mask & fixed_mask

    # Активные = все без "Не считаем план" и без корректировок
    active_mask = ~no_plan_mask & ~fixed_mask

    if 'План_Расч' not in g.columns:
        g['План_Расч'] = 0.0

    # НЕ обнуляем веса — они нужны для расчёта теоретического плана!
    # Нормализуем веса по всем отделам с весом > 0
    total_weight = weights.sum()
    if total_weight <= 0:
        return g

    # ШАГ 1: Теоретический план для ВСЕХ по весам
    g['_theoretical'] = target * (weights / total_weight)

    # ШАГ 2: "Не считаем план" без корректировки получает план = 0
    g.loc[no_plan_without_corr, 'План_Расч'] = 0

    # ШАГ 3: Фиксированные (с корректировкой) получают свой ручной план
    # ВАЖНО: берём значение из Корр/Корр_Дельта, а не из План_Скорр
    if fixed_mask.any():
        for idx in g.index[fixed_mask]:
            corr = g.loc[idx, 'Корр'] if 'Корр' in g.columns else np.nan
            delta = g.loc[idx, 'Корр_Дельта'] if 'Корр_Дельта' in g.columns else np.nan
            base = g.loc[idx, '_theoretical']  # Теоретический план по весу

            if pd.notna(corr):
                # Корр = 0 означает план = 0 (явное обнуление)
                # Корр > 0 означает план = Корр + дельта
                if corr == 0:
                    final = 0
                else:
                    final = corr + (delta if pd.notna(delta) else 0)
            elif pd.notna(delta):
                # Только дельта — добавляем к теоретическому плану
                final = base + delta
            else:
                # Нет корректировки — используем План_Скорр если есть
                final = g.loc[idx, 'План_Скорр'] if 'План_Скорр' in g.columns else base

            g.loc[idx, 'План_Расч'] = max(0, final)

    # ШАГ 4: Считаем высвободившийся остаток
    # ШАГ 4: Считаем высвободившийся остаток
    # ИЗМЕНЕНИЕ (2025-01-30): "Не считаем план" (без корр) НЕ перераспределяем.
    # Их теоретическая доля просто сгорает (общий план будет меньше цели).
    # Учитываем (перераспределяем) разницу ТОЛЬКО по фиксированным отделам.

    theoretical_fixed = g.loc[fixed_mask, '_theoretical'].sum() if fixed_mask.any() else 0
    actual_fixed = g.loc[fixed_mask, 'План_Расч'].sum() if fixed_mask.any() else 0

    freed_amount = theoretical_fixed - actual_fixed  # Положительное = высвободилось

    # ШАГ 4: Распределяем остаток на активных (С учетом Инфляционного ограничителя)
    if active_mask.any():
        weights_active = weights.loc[active_mask].copy() # Копия для модификации

        remaining_target = target - actual_fixed

        # --- ЛОГИКА ИНФЛЯЦИОННОГО ЛИМИТА (Inflation Cap) ---
        # Правило: Сопутствующий отдел не может расти больше чем на 6% к 2024 году.
        # Излишек отдаем СТРАТЕГИЧЕСКИМ отделам.

        INFLATION_CAP_PCT = 6
        has_fact_24 = 'Выручка_2024' in g.columns

        if has_fact_24 and remaining_target > 0 and weights_active.sum() > 0:
            # Идентифицируем Сопутствующие, которые превышают лимит
            capped_indices = []
            excess_weight_total = 0

            # Предварительная сумма весов
            current_sum_active = weights_active.sum()

            for idx in weights_active.index:
                role = g.loc[idx, 'Роль'] if 'Роль' in g.columns else 'Сопутствующий'
                if role != 'Сопутствующий':
                    continue

                # base_rev = g.loc[idx, 'Выручка_2024'] # БЫЛО 2024
                # ИЗМЕНЕНИЕ: Пользователь попросил базу 2025
                base_rev = g.loc[idx, 'Rev_2025_Norm'] if 'Rev_2025_Norm' in g.columns else g.loc[idx, 'Выручка_2025']

                if pd.isna(base_rev) or base_rev <= 0:
                    continue

                max_plan = base_rev * (1 + INFLATION_CAP_PCT / 100)

                # Текущий план по весу: Plan = Target * (Weight / Sum)
                current_weight = weights_active.loc[idx]
                implied_plan = remaining_target * (current_weight / current_sum_active)

                if implied_plan > max_plan:
                    # Корректируем вес, чтобы план стал равен max_plan
                    # New_Weight = (Max_Plan / Target) * Sum
                    target_weight = (max_plan / remaining_target) * current_sum_active

                    # Разница весов, которую надо забрать
                    weight_diff = current_weight - target_weight

                    if weight_diff > 0:
                        weights_active.loc[idx] = target_weight
                        excess_weight_total += weight_diff
                        capped_indices.append(idx)

            # Перераспределяем отобранный вес на Стратегические
            if excess_weight_total > 0:
                strat_mask_local = (g.loc[active_mask, 'Роль'] == 'Стратегический')
                # Индексы стратегических внутри active_mask !!!
                # weights_active индексирован так же, как active_mask

                # Нужно найти индексы стратегических, которые есть в active
                strat_indices = [idx for idx in weights_active.index if g.loc[idx, 'Роль'] == 'Стратегический']

                if strat_indices:
                    strat_weights = weights_active.loc[strat_indices]
                    strat_sum = strat_weights.sum()
                    if strat_sum > 0:
                        # Добавляем вес пропорционально
                        boost = excess_weight_total * (strat_weights / strat_sum)
                        weights_active.loc[strat_indices] += boost
                        print(f"      ⚖️ Capped {len(capped_indices)} Supporting depts (Inflation +{INFLATION_CAP_PCT}%). Redistributed {excess_weight_total:.4f} weight to {len(strat_indices)} Strategic.")
                else:
                    # Нет стратегических? Размазываем обратно на всех (возвращаем в котел)
                    # Или просто оставляем как есть, тогда сумма весов уменьшится, и при делении на неё
                    # план вырастет у ВСЕХ оставшихся (включая другие сопутствующие).
                    # Это тоже приемлемо.
                    pass

        # Итоговая сумма весов (могла измениться незначительно из-за float, или если не было стратегов)
        weights_active_sum = weights_active.sum()

        if weights_active_sum > 0:
            # Финальное распределение остатка
            g.loc[active_mask, 'План_Расч'] = remaining_target * (weights_active / weights_active_sum)
        else:
            g.loc[active_mask, 'План_Расч'] = 0

    # Удаляем временную колонку
    g = g.drop(columns=['_theoretical'])

    # Обнуление малых планов и перераспределение
    small_mask = (g['План_Расч'] > 0) & (g['План_Расч'] < BUSINESS_RULES['MIN_PLAN_THRESHOLD']) & active_mask
    if small_mask.any():
        freed = g.loc[small_mask, 'План_Расч'].sum()
        g.loc[small_mask, 'План_Расч'] = 0
        remaining_active = active_mask & ~small_mask & (g['План_Расч'] > 0)
        if remaining_active.any() and freed > 0:
            w = weights.loc[remaining_active]
            w_sum = w.sum()
            if w_sum > 0:
                g.loc[remaining_active, 'План_Расч'] += freed * (w / w_sum)

    # ИЗМЕНЕНИЕ (2025-01-30): Умное округление (Largest Remainder Method)
    # Вместо сброса всего остатка на лидера, распределяем по 10к тем, кто больше всех "пострадал" от округления.

    # 1. Сохраняем точные значения до округления
    g.loc[active_mask, 'raw_plan'] = g.loc[active_mask, 'План_Расч']

    # 2. Первичное округление до шага
    step = CONFIG['rounding_step']
    g.loc[active_mask, 'План_Расч'] = (g.loc[active_mask, 'raw_plan'] / step).round(0).astype(int) * step

    # 3. Считаем ошибку округления
    # Цель для активных = (Общая цель - Планы особых отделов)
    # Но проще: Diff = Общая Цель - Сумма всех текущих планов (особые + округленные активные)
    current_total = g['План_Расч'].sum()
    diff = target - current_total

    # 4. Распределяем по 10к (шагами)
    # Количество шагов, которые нужно добавить (или убавить)
    steps_needed = int(diff // step)
    remainder_final = diff % step # Некратный остаток (если цель не кратна 10к)

    if steps_needed != 0:
        # Считаем "остатки" (разницу между точным и округленным)
        # Если steps_needed > 0 (надо добавить): приоритет тем, у кого raw > rounded (кого обидели)
        # diff_val = raw - rounded. Чем больше, тем сильнее округлили вниз.
        g.loc[active_mask, 'diff_val'] = g.loc[active_mask, 'raw_plan'] - g.loc[active_mask, 'План_Расч']

        # Сортируем:
        # Если добавляем (+): по убыванию diff_val (сначала те, у кого срезали больше всего)
        # Если убавляем (-): по возрастанию diff_val (сначала те, кому накинули больше всего, т.е. diff_val отрицательный)
        ascending = (steps_needed < 0)

        # Выбираем топ N отделов
        # ВАЖНО: сортируем только активные
        sorted_indices = g[active_mask].sort_values('diff_val', ascending=ascending).index

        # Берем первые N
        indices_to_adjust = sorted_indices[:abs(steps_needed)]

        # Применяем корректировку
        adjustment = step if steps_needed > 0 else -step
        g.loc[indices_to_adjust, 'План_Расч'] += adjustment

    # 5. Финальный сброс некратного остатка (копейки, если цель не 10000-кратная)
    # Скидываем на максимальный отдел
    current_total_after_steps = g['План_Расч'].sum()
    final_diff = target - current_total_after_steps

    if final_diff != 0:
        # Ищем среди активных (если есть), иначе среди всех
        candidate_mask = active_mask if active_mask.any() else pd.Series(True, index=g.index)
        # Ищем отдел с макс планом
        if candidate_mask.any():
            max_idx = g.loc[candidate_mask, 'План_Расч'].idxmax()
            g.loc[max_idx, 'План_Расч'] += final_diff

    # Чистим временные колонки
    if 'raw_plan' in g.columns: g.drop(columns=['raw_plan'], inplace=True)
    if 'diff_val' in g.columns: g.drop(columns=['diff_val'], inplace=True)

    final_sum = g['План_Расч'].sum()

    return g


def apply_business_rules(df, df_roles):
    """Добавляет роли и распределяет план с учётом корректировок (EXPLICIT LOOP VERSION V2)"""
    print(f"... apply_business_rules called with {len(df)} rows")

    if 'Роль' in df.columns:
        df = df.drop(columns=['Роль'])
    df = pd.merge(df, df_roles[['Отдел', 'Роль']], on='Отдел', how='left')
    df['Роль'] = df['Роль'].fillna('Сопутствующий')

    if 'Final_Weight' not in df.columns:
        weight_basis = df['Rev_2025_Norm'] if 'Rev_2025_Norm' in df.columns else df['Выручка_2025']
        df['Final_Weight'] = df.groupby(['Филиал', 'Месяц'])['Выручка_2025'].transform(lambda x: x / x.sum() if x.sum() > 0 else 0)
        if 'Rev_2025_Norm' in df.columns:
             df['Final_Weight'] = df.groupby(['Филиал', 'Месяц'])['Rev_2025_Norm'].transform(lambda x: x / x.sum() if x.sum() > 0 else 0)

    if 'Base_Weight' not in df.columns:
        df['Base_Weight'] = df['Final_Weight'].copy()

    if 'Корр' not in df.columns: df['Корр'] = np.nan
    if 'Корр_Дельта' not in df.columns: df['Корр_Дельта'] = np.nan

    # ========== СЕЗОННОСТЬ СЕТИ ==========
    network_by_month = df.groupby('Месяц')['Выручка_2025'].sum()
    network_total = network_by_month.sum()
    if network_total > 0:
        network_seasonality = {m: network_by_month.get(m, 0) / network_total for m in range(1, 13)}
    else:
        network_seasonality = {m: 1/12 for m in range(1, 13)}

    def process_group(g):
        # Simple function logic, no complex safeguards needed if called from explicit loop
        try:
            if len(g) == 0: return g

            if 'План' not in g.columns: return g
            plan_val = g['План'].iloc[0]
            if pd.isna(plan_val): return g

            target = int(round(plan_val))
            fixed_mask = has_correction(g)
            return distribute_plan_for_group(g, target, fixed_mask=fixed_mask)
        except Exception as e:
            print(f"  ❌ Oшибка в process_group: {e}")
            # Fallback to returning original group
            return g

    # Apply logic - EXPLICIT LOOP
    print("... executing explicit groupby loop")
    results = []

    # Check dtypes just in case
    if 'Филиал' not in df.columns or 'Месяц' not in df.columns:
         print(f"❌ CRITICAL: Missing columns before loop. Columns: {df.columns.tolist()}")
         # Try reset index if needed
         df = df.reset_index()

    # FIX V2: as_index=False IS REQUIRED HERE too
    for name, group in df.groupby(['Филиал', 'Месяц'], as_index=False):
        # Columns 'Филиал' and 'Месяц' SHOULD be present now.
        processed = process_group(group)
        results.append(processed)

    if results:
        result = pd.concat(results, ignore_index=True)
    else:
        result = df.iloc[0:0]

    print(f"... loop finished. Result columns: {len(result.columns)}")
    return result
    def process_group(g):
        # Simple function logic, no complex safeguards needed if called from explicit loop
        try:
            if len(g) == 0: return g

            if 'План' not in g.columns: return g
            plan_val = g['План'].iloc[0]
            if pd.isna(plan_val): return g

            target = int(round(plan_val))
            fixed_mask = has_correction(g)
            return distribute_plan_for_group(g, target, fixed_mask=fixed_mask)
        except Exception as e:
            print(f"  ❌ Oшибка в process_group: {e}")
            # Fallback to returning original group
            return g

    # Apply logic - EXPLICIT LOOP
    print("... executing explicit groupby loop")
    results = []

    # Check dtypes just in case
    if 'Филиал' not in df.columns or 'Месяц' not in df.columns:
         print(f"❌ CRITICAL: Missing columns before loop. Columns: {df.columns.tolist()}")
         # Try reset index if needed
         df = df.reset_index()

    for name, group in df.groupby(['Филиал', 'Месяц']):
        # group is a DataFrame slice. Indices are preserved.
        # Columns 'Филиал' и 'Месяц' должны присутствовать.
        processed = process_group(group)
        results.append(processed)

    if results:
        result = pd.concat(results, ignore_index=True)
    else:
        result = df.iloc[0:0]

    print(f"... loop finished. Result columns: {len(result.columns)}")
    return result
    def process_group(g):
        try:
            plan_val = g['План'].iloc[0]
            branch = g['Филиал'].iloc[0]
            month = g['Месяц'].iloc[0]

            if pd.isna(plan_val):
                return g
            target = int(round(plan_val))
            month_name = MONTH_MAP_REV.get(month, str(month))

            # Определяем фиксированные строки (с ручными корректировками)
            fixed_mask = has_correction(g)

            return distribute_plan_for_group(g, target, fixed_mask=fixed_mask)
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            return g

    result = df.groupby(['Филиал', 'Месяц'], group_keys=False).apply(process_group)
    result.index = range(len(result))
    return result


# ============================================================================
# ПОДГОТОВКА ДАННЫХ
# ============================================================================

# MAPPING for Months
MONTH_MAP = {
    'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6,
    'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12
}
MONTH_MAP_REV = {v: k for k, v in MONTH_MAP.items()}

def prepare_baseline(df_sales, df_area):
    df_s = df_sales.copy()
    df_s['Month_Num'] = df_s['Месяц'].map(MONTH_MAP)
    df_s['Date'] = pd.to_datetime(df_s['Год'].astype(str) + '-' + df_s['Month_Num'].astype(str) + '-01')

    df_py = df_s[['Филиал', 'Отдел', 'Год', 'Month_Num', 'Выручка']].copy()
    df_py['Год'] = df_py['Год'] + 1
    df_py.columns = ['Филиал', 'Отдел', 'Год', 'Month_Num', 'Выручка_PY']

    df_merged = pd.merge(df_s, df_py, on=['Филиал', 'Отдел', 'Год', 'Month_Num'], how='left')

    network_sales = df_s.groupby(['Год', 'Month_Num'])['Выручка'].sum().reset_index()
    network_sales_py = network_sales.copy()
    network_sales_py['Год'] += 1
    network_sales_py.columns = ['Год', 'Month_Num', 'Выручка_PY_Network']

    df_trend = pd.merge(network_sales, network_sales_py, on=['Год', 'Month_Num'], how='left')
    df_trend['Trend_Network'] = (df_trend['Выручка'] / df_trend['Выручка_PY_Network']).fillna(1.0)
    df_merged = pd.merge(df_merged, df_trend[['Год', 'Month_Num', 'Trend_Network']], on=['Год', 'Month_Num'], how='left')

    df_a = df_area.copy()
    df_a['Month_Num'] = df_a['Месяц'].map(MONTH_MAP)
    df_a = df_a.sort_values(['Филиал', 'Отдел', 'Год', 'Month_Num'])
    df_a['Date'] = pd.to_datetime(df_a['Год'].astype(str) + '-' + df_a['Month_Num'].astype(str) + '-01')
    df_a['Prev_Area'] = df_a.groupby(['Филиал', 'Отдел'])['Площадь'].shift(1)

    area_changes = df_a[(df_a['Площадь'] != df_a['Prev_Area']) & (df_a['Prev_Area'].notna()) & (df_a['Prev_Area'] > 0)].copy()

    for _, row in area_changes.iterrows():
        branch, dept, change_date = row['Филиал'], row['Отдел'], row['Date']
        check_start = change_date - pd.DateOffset(months=3)
        mask = (df_merged['Филиал'] == branch) & (df_merged['Отдел'] == dept) & (df_merged['Date'] >= check_start) & (df_merged['Date'] < change_date)
        for idx in df_merged[mask].index:
            act, py = df_merged.loc[idx, 'Выручка'], df_merged.loc[idx, 'Выручка_PY']
            if pd.notna(py) and py > 0 and (act - py) / py < -0.30:
                df_merged.loc[idx, 'Выручка'] = int(py * df_merged.loc[idx, 'Trend_Network'])

    return df_merged[['Филиал', 'Отдел', 'Месяц', 'Год', 'Выручка', 'Чеки']]


def calculate_planning_weights(df_sales, df_rules, df_formats):
    """Распределение долей через нормализованную базу

    Логика:
    - "Только 2025": База = Выручка 2025
    - "2024-2025": База = 0.5 × Выручка_2024 + 0.5 × Выручка_2025 (взвешенное среднее)
    - "Формат": База = Годовая выручка отдела × Сезонность по сети
    - "Не считаем план": Исключается из расчёта (база = 0, не участвует в сумме)

    Все базы приводятся к единому знаменателю, затем считается доля каждого отдела.
    """
    # Веса для взвешенного среднего
    WEIGHT_2024 = 0.5
    WEIGHT_2025 = 0.5

    df_rules_melted = df_rules.melt(id_vars=['Отдел'], var_name='Филиал', value_name='Правило')
    df_rules_melted['Филиал'] = df_rules_melted['Филиал'].astype(str).str.strip()
    df_rules_melted['Отдел'] = df_rules_melted['Отдел'].astype(str).str.strip()

    df_s = df_sales.copy()
    df_s['Месяц'] = df_s['Месяц'].astype(str).str.strip().str.lower()
    df_s['Филиал'] = df_s['Филиал'].astype(str).str.strip()
    df_s['Отдел'] = df_s['Отдел'].astype(str).str.strip()

    df_formats = df_formats.copy()
    df_formats['Филиал'] = df_formats['Филиал'].astype(str).str.strip()

    months = list(df_s['Месяц'].unique())

    # Объединяем с правилами
    df_s = pd.merge(df_s, df_rules_melted[['Филиал', 'Отдел', 'Правило']], on=['Филиал', 'Отдел'], how='left')

    # Определяем типы правил
    rule_lower = df_s['Правило'].fillna('').str.strip().str.lower()
    df_s['_is_no_plan'] = df_s['Правило'].fillna('').str.strip() == 'Не считаем план'
    df_s['_is_only_2025'] = rule_lower.str.contains('только 2025', na=False)
    df_s['_is_2024_2025'] = rule_lower.str.contains('2024-2025', na=False)
    df_s['_is_format'] = rule_lower.str.contains('формат', na=False)

    # ========== ШАГ 1: Подготовка выручки по годам (помесячно) ==========
    df_2024 = df_s[df_s['Год'] == 2024].groupby(['Филиал', 'Отдел', 'Месяц'])['Выручка'].sum().reset_index()
    df_2024.columns = ['Филиал', 'Отдел', 'Месяц', 'Rev_2024']

    df_2025 = df_s[df_s['Год'] == 2025].groupby(['Филиал', 'Отдел', 'Месяц'])['Выручка'].sum().reset_index()
    df_2025.columns = ['Филиал', 'Отдел', 'Месяц', 'Rev_2025']

    # ========== ШАГ 2: Годовая выручка для "Формат" отделов ==========
    df_2025_year = df_s[df_s['Год'] == 2025].groupby(['Филиал', 'Отдел'])['Выручка'].sum().reset_index()
    df_2025_year.columns = ['Филиал', 'Отдел', 'Rev_2025_Year']

    # ========== ШАГ 3: Создаём мастер-таблицу ==========
    df_master = df_rules_melted.loc[df_rules_melted.index.repeat(len(months))].reset_index(drop=True)
    df_master['Месяц'] = np.tile(months, len(df_rules_melted))

    # Добавляем помесячную выручку
    df_master = pd.merge(df_master, df_2024, on=['Филиал', 'Отдел', 'Месяц'], how='left')
    df_master = pd.merge(df_master, df_2025, on=['Филиал', 'Отдел', 'Месяц'], how='left')
    df_master['Rev_2024'] = df_master['Rev_2024'].fillna(0)
    df_master['Rev_2025'] = df_master['Rev_2025'].fillna(0)

    # Добавляем годовую выручку
    df_master = pd.merge(df_master, df_2025_year, on=['Филиал', 'Отдел'], how='left')
    df_master['Rev_2025_Year'] = df_master['Rev_2025_Year'].fillna(0)

    # ========== DEBUG: Проверка отделов в правилах vs в продажах для Владимира ==========
    vlad_rules = df_master[(df_master['Филиал'] == 'Владимир Розница') & (df_master['Месяц'] == 'янв')]
    vlad_sales = df_2025[(df_2025['Филиал'] == 'Владимир Розница') & (df_2025['Месяц'] == 'янв')]

    rules_depts = set(vlad_rules['Отдел'].unique())
    sales_depts = set(vlad_sales['Отдел'].unique())

    extra_in_rules = rules_depts - sales_depts
    missing_in_rules = sales_depts - rules_depts

    print(f"\n{'='*70}")
    print(f"🔍 DEBUG: Владимир Розница - отделы в правилах vs продажах")
    print(f"{'='*70}")
    print(f"   Отделов в правилах: {len(rules_depts)}")
    print(f"   Отделов в продажах 2025: {len(sales_depts)}")
    print(f"   Отделов ТОЛЬКО в правилах (нет продаж): {len(extra_in_rules)}")
    if extra_in_rules:
        for d in sorted(extra_in_rules)[:10]:
            print(f"      - {d}")
        if len(extra_in_rules) > 10:
            print(f"      ... и ещё {len(extra_in_rules) - 10}")
    print(f"   Отделов ТОЛЬКО в продажах (нет в правилах): {len(missing_in_rules)}")
    if missing_in_rules:
        for d in sorted(missing_in_rules)[:10]:
            print(f"      - {d}")

    # ========== ШАГ 3.1: Нормализация выручки для филиалов на ремонте ==========
    # Рыбинск и Владимир Розница с сентября 2025 на ремонте — выручка упала
    # Нормализуем: берём среднее падение янв-авг и применяем к 2024 для сен-дек
    RENOVATION_BRANCHES = ['Рыбинск', 'Владимир Розница']
    RENOVATION_START_MONTH = 9  # сентябрь

    # Преобразуем месяц в число для сравнения
    month_to_num = {'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6,
                    'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12}
    df_master['_month_num'] = df_master['Месяц'].map(month_to_num)

    # Создаём колонку для нормализованной выручки (изначально = Rev_2025)
    df_master['Rev_2025_Norm'] = df_master['Rev_2025'].copy()

    # Для филиалов на ремонте
    for branch in RENOVATION_BRANCHES:
        branch_mask = df_master['Филиал'] == branch
        if not branch_mask.any():
            continue

        # Данные янв-авг для расчёта среднего коэффициента
        jan_aug_mask = branch_mask & (df_master['_month_num'] < RENOVATION_START_MONTH)
        jan_aug_data = df_master[jan_aug_mask].copy()

        # Считаем средний коэффициент 2025/2024 по каждому отделу за янв-авг
        # (где есть данные 2024 > 0)
        valid_data = jan_aug_data[jan_aug_data['Rev_2024'] > 0].copy()
        if len(valid_data) == 0:
            continue

        valid_data['_ratio'] = valid_data['Rev_2025'] / valid_data['Rev_2024']
        avg_ratio_by_dept = valid_data.groupby('Отдел')['_ratio'].mean()

        # Общий средний коэффициент по филиалу (если нет данных по отделу)
        overall_avg_ratio = valid_data['_ratio'].mean() if len(valid_data) > 0 else 1.0

        print(f"📊 Нормализация {branch}: avg_ratio янв-авг = {overall_avg_ratio:.2%}")

        # DEBUG: Показать avg_ratio для 7. Инструменты
        if '7. Инструменты' in avg_ratio_by_dept.index:
            dept_ratio = avg_ratio_by_dept['7. Инструменты']
            print(f"   → 7. Инструменты: avg_ratio = {dept_ratio:.2%} (янв-авг)")

        # Применяем к месяцам сен-дек
        sep_dec_mask = branch_mask & (df_master['_month_num'] >= RENOVATION_START_MONTH)

        for idx in df_master[sep_dec_mask].index:
            dept = df_master.loc[idx, 'Отдел']
            rev_2024 = df_master.loc[idx, 'Rev_2024']

            # Берём коэффициент по отделу, или общий если нет
            ratio = avg_ratio_by_dept.get(dept, overall_avg_ratio)

            # Нормализованная выручка = Rev_2024 × avg_ratio
            if rev_2024 > 0:
                df_master.loc[idx, 'Rev_2025_Norm'] = rev_2024 * ratio

    # Также создаём нормализованную годовую выручку
    df_master['Rev_2025_Year_Norm'] = df_master.groupby(['Филиал', 'Отдел'])['Rev_2025_Norm'].transform('sum')

    print(f"✅ Нормализация выручки завершена для {RENOVATION_BRANCHES}")

    # ========== DEBUG: Проверка нормализации для 7. Инструменты ==========
    DEBUG_DEPT = '7. Инструменты'
    DEBUG_MONTHS = ['сен', 'окт', 'ноя', 'дек']
    for branch in RENOVATION_BRANCHES:
        debug_mask = (df_master['Филиал'] == branch) & (df_master['Отдел'] == DEBUG_DEPT) & (df_master['Месяц'].isin(DEBUG_MONTHS))
        if debug_mask.any():
            print(f"\n{'='*70}")
            print(f"🔍 DEBUG НОРМАЛИЗАЦИЯ: {branch} / {DEBUG_DEPT}")
            print(f"{'='*70}")
            for _, row in df_master[debug_mask].iterrows():
                diff = row['Rev_2025_Norm'] - row['Rev_2025']
                diff_pct = (row['Rev_2025_Norm'] / row['Rev_2025'] - 1) * 100 if row['Rev_2025'] > 0 else 0
                print(f"   {row['Месяц']}:")
                print(f"      Rev_2024        = {row['Rev_2024']:>12,.0f}")
                print(f"      Rev_2025 (факт) = {row['Rev_2025']:>12,.0f}")
                print(f"      Rev_2025_Norm   = {row['Rev_2025_Norm']:>12,.0f}  (Δ = {diff:+,.0f}, {diff_pct:+.1f}%)")

    # Определяем типы правил
    rule_lower = df_master['Правило'].fillna('').str.strip().str.lower()
    df_master['_is_no_plan'] = df_master['Правило'].fillna('').str.strip() == 'Не считаем план'
    df_master['_is_only_2025'] = rule_lower.str.contains('только 2025', na=False)
    df_master['_is_2024_2025'] = rule_lower.str.contains('2024-2025', na=False)
    df_master['_is_format'] = rule_lower.str.contains('формат', na=False)
    df_master['_is_format_only'] = rule_lower.str.contains('структура только формата', na=False)

    # ========== ШАГ 4: Сезонность по СЕТИ для "Формат" отделов ==========
    # Сезонность считается по ВСЕМ продажам сети (без фильтра по правилам!)
    # Правила влияют только на конкретный филиал, не на общую сезонность
    #
    # ВАЖНО: Используем НОРМАЛИЗОВАННУЮ выручку для расчёта сезонности!
    # Это корректирует искажение от ремонтов в Рыбинске и Владимире
    df_s_2025_all = df_s[df_s['Год'] == 2025].copy()

    # DEBUG: Проверяем данные для 9А. Материалы отделочные в df_s_2025_all
    debug_dept = '9А. Материалы отделочные'
    debug_s = df_s_2025_all[df_s_2025_all['Отдел'] == debug_dept]
    if len(debug_s) > 0:
        print(f"\n{'='*70}")
        print(f"🔍 DEBUG df_s_2025_all: {debug_dept}")
        print(f"{'='*70}")
        for m in sorted(debug_s['Месяц'].unique()):
            m_data = debug_s[debug_s['Месяц'] == m]
            total_rev = m_data['Выручка'].sum()
            branches = m_data['Филиал'].unique().tolist()
            print(f"   Месяц '{m}': Выручка={total_rev:,.0f}, Филиалы: {branches[:3]}{'...' if len(branches) > 3 else ''}")
    else:
        print(f"\n❌ DEBUG: Отдел '{debug_dept}' не найден в df_s_2025_all!")
        print(f"   Уникальные месяцы в df_s_2025_all: {df_s_2025_all['Месяц'].unique()}")
        print(f"   Количество записей: {len(df_s_2025_all)}")

    # Применяем нормализацию к df_s_2025_all для филиалов на ремонте
    # Используем уже рассчитанные данные из df_master
    norm_data = df_master[['Филиал', 'Отдел', 'Месяц', 'Rev_2025', 'Rev_2025_Norm']].copy()
    norm_data['_norm_ratio'] = np.where(
        norm_data['Rev_2025'] > 0,
        norm_data['Rev_2025_Norm'] / norm_data['Rev_2025'],
        1.0
    )

    # Присоединяем коэффициент нормализации к df_s_2025_all
    df_s_2025_all = pd.merge(
        df_s_2025_all,
        norm_data[['Филиал', 'Отдел', 'Месяц', '_norm_ratio']],
        on=['Филиал', 'Отдел', 'Месяц'],
        how='left'
    )
    df_s_2025_all['_norm_ratio'] = df_s_2025_all['_norm_ratio'].fillna(1.0)
    df_s_2025_all['Выручка_Norm'] = df_s_2025_all['Выручка'] * df_s_2025_all['_norm_ratio']

    # DEBUG: Проверяем нормализацию в df_s_2025_all
    for branch in RENOVATION_BRANCHES:
        debug_s = df_s_2025_all[(df_s_2025_all['Филиал'] == branch) & (df_s_2025_all['Отдел'] == DEBUG_DEPT) & (df_s_2025_all['Месяц'].isin(DEBUG_MONTHS))]
        if len(debug_s) > 0:
            print(f"\n🔍 DEBUG СЕЗОННОСТЬ СЕТИ: нормализация {branch} / {DEBUG_DEPT}")
            for month in DEBUG_MONTHS:
                m_data = debug_s[debug_s['Месяц'] == month]
                if len(m_data) > 0:
                    orig = m_data['Выручка'].sum()
                    norm = m_data['Выручка_Norm'].sum()
                    print(f"   {month}: Выручка={orig:,.0f} → Выручка_Norm={norm:,.0f} (ratio={norm/orig:.2%})" if orig > 0 else f"   {month}: нет данных")

    # Сетевая выручка отделов по месяцам (используем НОРМАЛИЗОВАННУЮ выручку)
    network_format_month = df_s_2025_all.groupby(['Отдел', 'Месяц'])['Выручка_Norm'].sum().reset_index()
    network_format_month.columns = ['Отдел', 'Месяц', 'Network_Month']

    # Сетевая выручка отделов за год (НОРМАЛИЗОВАННАЯ)
    network_format_year = df_s_2025_all.groupby('Отдел')['Выручка_Norm'].sum().reset_index()
    network_format_year.columns = ['Отдел', 'Network_Year']

    # Сезонность = (Выручка месяца / Выручка года) — доля месяца в году
    seasonality = pd.merge(network_format_month, network_format_year, on='Отдел', how='left')
    seasonality['Seasonality_Share'] = np.where(
        seasonality['Network_Year'] > 0,
        seasonality['Network_Month'] / seasonality['Network_Year'],
        1.0 / 12  # Равномерно, если нет данных
    )

    # DEBUG: Проверяем сезонность для 9А. Материалы отделочные
    debug_dept = '9А. Материалы отделочные'
    debug_seas = seasonality[seasonality['Отдел'] == debug_dept]
    if len(debug_seas) > 0:
        print(f"\n{'='*70}")
        print(f"🔍 DEBUG СЕЗОННОСТЬ: {debug_dept}")
        print(f"{'='*70}")
        for _, r in debug_seas.iterrows():
            print(f"   Месяц {r['Месяц']}: Network_Month={r['Network_Month']:,.0f}, Network_Year={r['Network_Year']:,.0f}, Seasonality={r['Seasonality_Share']:.4f}")
    else:
        print(f"\n❌ DEBUG: Отдел '{debug_dept}' не найден в seasonality!")
        print(f"   Доступные отделы: {seasonality['Отдел'].unique()[:10]}...")

    # DEBUG: Сравнение сезонности с/без нормализации для 7. Инструменты
    # Считаем сезонность БЕЗ нормализации для сравнения
    network_month_raw = df_s_2025_all.groupby(['Отдел', 'Месяц'])['Выручка'].sum().reset_index()
    network_month_raw.columns = ['Отдел', 'Месяц', 'Network_Month_Raw']
    network_year_raw = df_s_2025_all.groupby('Отдел')['Выручка'].sum().reset_index()
    network_year_raw.columns = ['Отдел', 'Network_Year_Raw']
    seasonality_raw = pd.merge(network_month_raw, network_year_raw, on='Отдел', how='left')
    seasonality_raw['Seasonality_Raw'] = np.where(
        seasonality_raw['Network_Year_Raw'] > 0,
        seasonality_raw['Network_Month_Raw'] / seasonality_raw['Network_Year_Raw'],
        1.0 / 12
    )

    # Сравниваем
    compare = pd.merge(
        seasonality[seasonality['Отдел'] == DEBUG_DEPT][['Месяц', 'Seasonality_Share', 'Network_Month']],
        seasonality_raw[seasonality_raw['Отдел'] == DEBUG_DEPT][['Месяц', 'Seasonality_Raw', 'Network_Month_Raw']],
        on='Месяц', how='left'
    )
    if len(compare) > 0 and DEBUG_MONTHS:
        print(f"\n{'='*70}")
        print(f"🔍 DEBUG СЕЗОННОСТЬ СЕТИ: {DEBUG_DEPT}")
        print(f"{'='*70}")
        for month in DEBUG_MONTHS:
            row = compare[compare['Месяц'] == month]
            if len(row) > 0:
                r = row.iloc[0]
                diff = (r['Seasonality_Share'] - r['Seasonality_Raw']) * 100
                print(f"   {month}:")
                print(f"      Network_Month: {r['Network_Month_Raw']:,.0f} → {r['Network_Month']:,.0f} (норм)")
                print(f"      Сезонность:    {r['Seasonality_Raw']:.4f} → {r['Seasonality_Share']:.4f} (Δ = {diff:+.4f}%)")

    # ШАГ 4.0.1: Помесячная доля отдела в сети (для Network_Dept_Share)
    network_total_by_month = seasonality.groupby('Месяц')['Network_Month'].sum().reset_index()
    network_total_by_month.columns = ['Месяц', 'Network_Total_Month']
    seasonality = pd.merge(seasonality, network_total_by_month, on='Месяц', how='left')
    seasonality['Network_Dept_Share'] = np.where(
        seasonality['Network_Total_Month'] > 0,
        seasonality['Network_Month'] / seasonality['Network_Total_Month'],
        0.0
    )

    # ШАГ 4.0.2: ГОДОВАЯ доля отдела в сети (для Мини/Микро/Интернет)
    # Это СТАБИЛЬНАЯ доля отдела, не зависит от колебаний конкретного месяца
    network_total_year = network_format_year['Network_Year'].sum()
    network_format_year['All_Network_Year_Share'] = np.where(
        network_total_year > 0,
        network_format_year['Network_Year'] / network_total_year,
        0.0
    )

    df_master = pd.merge(df_master, seasonality[['Отдел', 'Месяц', 'Seasonality_Share', 'Network_Dept_Share']],
                         on=['Отдел', 'Месяц'], how='left')
    df_master['Seasonality_Share'] = df_master['Seasonality_Share'].fillna(1.0 / 12)
    df_master['Network_Dept_Share'] = df_master['Network_Dept_Share'].fillna(0)

    # Добавляем ГОДОВУЮ долю отдела в сети (стабильная, не зависит от месяца)
    df_master = pd.merge(df_master, network_format_year[['Отдел', 'All_Network_Year_Share']],
                         on='Отдел', how='left')
    df_master['All_Network_Year_Share'] = df_master['All_Network_Year_Share'].fillna(0)

    share_check = df_master[['Отдел', 'All_Network_Year_Share']].drop_duplicates().sort_values('All_Network_Year_Share', ascending=False)
    for _, row in share_check.head(5).iterrows():
        print(f"   {row['Отдел']}: {row['All_Network_Year_Share']:.4f}")

    # ========== ШАГ 4.1: Сетевая выручка формата для "Структура только формата" ==========
    # Для филиалов без собственных продаж берём выручку СЕТИ по формату
    df_master = pd.merge(df_master, seasonality[['Отдел', 'Месяц', 'Network_Month']].rename(
        columns={'Network_Month': 'Format_Network_Month'}),
        on=['Отдел', 'Месяц'], how='left')
    df_master['Format_Network_Month'] = df_master['Format_Network_Month'].fillna(0)

    # ========== ШАГ 4.2: Добавляем формат филиала ==========
    df_master = pd.merge(df_master, df_formats[['Филиал', 'Формат']], on='Филиал', how='left')
    df_master['Формат'] = df_master['Формат'].fillna('').astype(str).str.strip()

    moscow_check = df_master[df_master['Филиал'].str.contains('Москва', na=False)]['Формат'].unique()

    # Форматы, для которых используем сетевую структуру
    NETWORK_STRUCTURE_FORMATS = ['Мини', 'Микро', 'Интернет', 'Интернет магазин']

    # ========== ШАГ 5: Расчёт нормализованной базы ==========
    # ВАЖНО: "Не считаем план" тоже получает базу для расчёта теоретического плана
    # Это нужно чтобы при ручной корректировке высвободившийся остаток
    # правильно перераспределялся на другие отделы
    #
    # ВАЖНО: Используем Rev_2025_Norm вместо Rev_2025 для расчёта весов!
    # Это нормализованная выручка, которая учитывает ремонты (Рыбинск, Владимир Розница)
    def calc_base(row):
        # Используем нормализованные значения для расчёта весов
        rev_2025 = row['Rev_2025_Norm']
        rev_2025_year = row['Rev_2025_Year_Norm']
        fmt = row.get('Формат', '')

        if row['_is_no_plan']:
            # "Не считаем план" — база по факту 2025 (для расчёта теоретического веса)
            return rev_2025 if rev_2025 > 0 else 0.0
        elif row['_is_format_only']:
            # "Структура только формата" — используем СЕТЕВУЮ выручку формата
            # Это для филиалов без собственных продаж
            return row['Format_Network_Month'] if row['Format_Network_Month'] > 0 else 0.0
        elif row['_is_only_2025']:
            # "Только 2025" — РАЗНАЯ логика для разных форматов:
            # - Для Интернет: Годовая выручка × Сезонность сети (как "Формат")
            # - Для остальных: помесячные продажи 2025
            if fmt == 'Интернет':
                # Интернет использует сезонность сети
                return rev_2025_year * row['Seasonality_Share'] if rev_2025_year > 0 else 0.0
            else:
                return rev_2025
        elif row['_is_2024_2025']:
            # Взвешенное среднее: 50% от 2024 + 50% от 2025
            # ВАЖНО: Для филиалов на ремонте (Рыбинск, Владимир Розница)
            # если Rev_2024 аномально низкий относительно Rev_2025_Norm,
            # используем только Rev_2025_Norm
            branch = row.get('Филиал', '')
            is_renovation = branch in ['Рыбинск', 'Владимир Розница']

            if is_renovation:
                # Для филиалов на ремонте: если Rev_2024 < 50% от Rev_2025_Norm,
                # считаем что данные 2024 ненадёжны и используем только 2025
                if row['Rev_2024'] < rev_2025 * 0.5:
                    return rev_2025  # Используем только нормализованные данные 2025

            return WEIGHT_2024 * row['Rev_2024'] + WEIGHT_2025 * rev_2025
        elif row['_is_format']:
            # Формат: Годовая выручка × Сезонность по сети
            # Для ВСЕХ форматов используем сетевую сезонность
            return rev_2025_year * row['Seasonality_Share']
        else:
            # Не задано правило — по умолчанию как "Только 2025"
            # Для Интернет — сезонность сети
            if fmt == 'Интернет':
                return rev_2025_year * row['Seasonality_Share'] if rev_2025_year > 0 else 0.0
            return rev_2025

    df_master['_base'] = df_master.apply(calc_base, axis=1)

    # ========== ШАГ 6: Расчёт долей (Final_Weight) ==========
    # Сумма баз по филиалу и месяцу (включая "Не считаем план")
    df_master['_total_base'] = df_master.groupby(['Филиал', 'Месяц'])['_base'].transform('sum')

    # Доля = База / Сумма баз (для ВСЕХ отделов с базой > 0)
    df_master['Final_Weight'] = np.where(
        df_master['_total_base'] > 0,
        df_master['_base'] / df_master['_total_base'],
        0.0
    )

    # ========== DEBUG: Проверка _base и Final_Weight для 7. Инструменты ==========
    for branch in RENOVATION_BRANCHES:
        # Выводим ВСЕ месяцы для понимания проблемы
        debug_mask = (df_master['Филиал'] == branch) & (df_master['Отдел'] == DEBUG_DEPT)
        if debug_mask.any():
            print(f"\n{'='*70}")
            print(f"🔍 DEBUG БАЗА И ВЕС: {branch} / {DEBUG_DEPT}")
            print(f"{'='*70}")
            for _, row in df_master[debug_mask].sort_values('_month_num').iterrows():
                rule = row['Правило'] if pd.notna(row['Правило']) else 'не задано'
                # Определяем какая формула использовалась
                if row['_is_no_plan']:
                    formula = "Rev_2025_Norm (Не считаем план)"
                elif row['_is_format_only']:
                    formula = "Format_Network_Month"
                elif row['_is_only_2025']:
                    formula = f"Rev_2025_Norm = {row['Rev_2025_Norm']:,.0f} (Только 2025)"
                elif row['_is_2024_2025']:
                    # Проверяем применилось ли исключение для ремонта
                    is_renovation_exception = row['Rev_2024'] < row['Rev_2025_Norm'] * 0.5
                    if is_renovation_exception:
                        formula = f"Rev_2025_Norm = {row['Rev_2025_Norm']:,.0f} (РЕМОНТ: Rev_2024 < 50% Rev_2025)"
                    else:
                        formula = f"0.5×{row['Rev_2024']:,.0f} + 0.5×{row['Rev_2025_Norm']:,.0f}"
                elif row['_is_format']:
                    formula = f"Rev_2025_Year_Norm × Seasonality = {row['Rev_2025_Year_Norm']:,.0f} × {row['Seasonality_Share']:.4f}"
                else:
                    formula = f"Rev_2025_Norm = {row['Rev_2025_Norm']:,.0f} (по умолчанию)"

                print(f"   {row['Месяц']}: Rev_2024={row['Rev_2024']:>12,.0f}, Rev_2025={row['Rev_2025']:>12,.0f}, Rev_2025_Norm={row['Rev_2025_Norm']:>12,.0f}")
                print(f"      Правило: {rule}, _base={row['_base']:,.0f}, Weight={row['Final_Weight']*100:.2f}%")
                if row['_is_2024_2025']:
                    print(f"      Формула: {formula}")

    # ========== ШАГ 6.1: Для Мини/Микро/Интернет — веса по правилам, сезонность по сети ==========
    # Веса уже рассчитаны в _base согласно правилам (Продажи только 2025, Не считаем план и т.д.)
    # Для этих форматов НЕ переопределяем веса на сетевую структуру
    # Сезонность сети уже учтена в правиле "Формат" (Rev_2025_Year * Seasonality_Share)

    # ========== DEBUG ==========
    debug_mask = (df_master['Филиал'].str.contains('Фрунзе', na=False)) & (df_master['Месяц'] == 'фев')
    if debug_mask.any():
        debug_cols = ['Отдел', 'Правило', 'Rev_2024', 'Rev_2025', 'Rev_2025_Year', 'Seasonality_Share', '_base', 'Final_Weight']
        debug_df = df_master.loc[debug_mask, debug_cols].sort_values('Final_Weight', ascending=False)

        total_base = df_master.loc[debug_mask & ~df_master['_is_no_plan'], '_base'].sum()
        total_weight = df_master.loc[debug_mask & ~df_master['_is_no_plan'], 'Final_Weight'].sum()

    # Убираем NaN и пустые строки
    df_master = df_master[
        df_master['Отдел'].notna() &
        df_master['Филиал'].notna() &
        (df_master['Отдел'].astype(str).str.lower() != 'nan') &
        (df_master['Филиал'].astype(str).str.lower() != 'nan')
    ]

    # Добавляем флаг сетевой структуры для использования в dashboard
    df_master['is_network_format'] = df_master['Формат'].isin(NETWORK_STRUCTURE_FORMATS)

    # DEBUG: Проверяем Москва Хаб / 9А. Материалы отделочные / ноябрь
    debug_mask = (df_master['Филиал'] == 'Москва Хаб') & (df_master['Отдел'] == '9А. Материалы отделочные')
    if debug_mask.any():
        print(f"\n{'='*70}")
        print(f"🔍 DEBUG: Москва Хаб / 9А. Материалы отделочные")
        print(f"{'='*70}")
        for _, row in df_master[debug_mask].iterrows():
            m = row['Месяц']
            weight = row['Final_Weight']
            base = row.get('_base', 'N/A')
            total_base = row.get('_total_base', 'N/A')
            seas = row.get('Seasonality_Share', 'N/A')
            rev_year = row.get('Rev_2025_Year_Norm', 'N/A')
            is_only_2025 = row.get('_is_only_2025', 'N/A')
            fmt = row.get('Формат', 'N/A')
            rule = row.get('Правило', 'N/A')

            if weight == 0 or (isinstance(base, (int, float)) and base == 0):
                print(f"   ❌ {m}: Weight={weight:.6f}, _base={base}, Seas={seas}, Rev_Year={rev_year}")
                print(f"      Правило: {rule}, Формат: {fmt}, _is_only_2025: {is_only_2025}")

    return df_master[['Филиал', 'Отдел', 'Месяц', 'Правило', 'Final_Weight', 'is_network_format', 'Rev_2025_Norm', 'Rev_2024', 'Rev_2025']]


# DEBUG: Функция для диагностики нулевого плана
def debug_zero_plan(df_master, branch, dept, month):
    """Выводит диагностику почему план может быть 0"""
    mask = (df_master['Филиал'] == branch) & (df_master['Отдел'] == dept) & (df_master['Месяц'] == month)
    if not mask.any():
        print(f"❌ DEBUG: Не найдена комбинация {branch} / {dept} / {month}")
        return

    row = df_master[mask].iloc[0]
    print(f"\n{'='*70}")
    print(f"🔍 DEBUG НУЛЕВОЙ ПЛАН: {branch} / {dept} / месяц {month}")
    print(f"{'='*70}")
    print(f"   Правило: {row.get('Правило', 'N/A')}")
    print(f"   Final_Weight: {row.get('Final_Weight', 'N/A'):.6f}")
    print(f"   Rev_2025_Norm: {row.get('Rev_2025_Norm', 'N/A'):,.0f}")
    print(f"   Формат: {row.get('Формат', 'N/A')}")
    print(f"   is_network_format: {row.get('is_network_format', 'N/A')}")

    if '_base' in row:
        print(f"   _base: {row['_base']:,.0f}")
    if 'Seasonality_Share' in row:
        print(f"   Seasonality_Share: {row['Seasonality_Share']:.6f}")
    if 'Rev_2025_Year_Norm' in row:
        print(f"   Rev_2025_Year_Norm: {row['Rev_2025_Year_Norm']:,.0f}")
    if '_is_only_2025' in row:
        print(f"   _is_only_2025: {row['_is_only_2025']}")
    if '_total_base' in row:
        print(f"   _total_base: {row['_total_base']:,.0f}")


# ============================================================================

# ============================================================================
# КАЛЬКУЛЯТОР ПЛАНОВ (Separation of Concerns)
# ============================================================================

class PlanCalculator:
    """
    Класс для математических расчётов планов.
    Отделён от UI для чистой архитектуры - можно использовать в скриптах без UI.
    """

    def __init__(self, config=None):
        self.config = config or CONFIG
        self.rounding_step = self.config.get('rounding_step', 10000)

    @staticmethod
    def recalc_metrics(df, mask, cols_available):
        """Пересчитывает метрики для указанных строк"""
        recalc_row_metrics(df, mask, cols_available)

    def redistribute_group(self, df, branch, month, verbose=False):
        """Перераспределяет план для группы (филиал, месяц)."""
        gm = (df['Филиал'] == branch) & (df['Месяц'] == month)
        if gm.sum() == 0:
            return 0

        target = int(round(df.loc[gm, 'План'].iloc[0]))
        corr_mask = has_correction(df, gm)

        if verbose:
            corrected_depts = df.loc[gm & corr_mask, 'Отдел'].tolist() if corr_mask.any() else []
            if corrected_depts:
                print(f"   📌 {branch}/{month}: фиксированные отделы ({len(corrected_depts)})")

        group_df = df.loc[gm].copy().reset_index(drop=True)
        fixed_mask_local = corr_mask[gm].reset_index(drop=True)
        result = distribute_plan_for_group(group_df, target, fixed_mask=fixed_mask_local)

        result_values = result['План_Расч'].values
        active_idx = df[gm].index[~corr_mask[df[gm].index]]

        changes = 0
        if len(active_idx) > 0:
            active_positions = [list(df[gm].index).index(idx) for idx in active_idx]
            active_values = [result_values[i] for i in active_positions]
            df.loc[active_idx, 'План_Скорр'] = active_values
            df.loc[active_idx, 'План_Расч'] = active_values
            if 'Рекоменд' in df.columns:
                df.loc[active_idx, 'Рекоменд'] = active_values
            changes = len(active_idx)
        return changes

    def apply_smooth_growth(self, df, dept_name, quarter_progress, verbose=False):
        """Универсальная логика плавного роста для отдела."""
        INFLATION = 1.06

        def get_quarter_end(month):
            return ((month - 1) // 3 + 1) * 3

        def get_quarter_start(month):
            return ((month - 1) // 3) * 3 + 1

        if 'Корр' not in df.columns:
            return set()
        if 'Авто_Корр' not in df.columns:
            df['Авто_Корр'] = np.nan

        dec_mask = (df['Отдел'] == dept_name) & (df['Месяц'] == 12) & (df['Корр'].notna())
        if not dec_mask.any():
            return set()

        dept_network = df[df['Отдел'] == dept_name].groupby('Месяц')['Выручка_2025'].sum()
        total_network = dept_network.sum()
        seasonality = {m: dept_network.get(m, 0) / total_network if total_network > 0 else 1/12 for m in range(1, 13)}

        branches_with_dec_target = df.loc[dec_mask, 'Филиал'].unique()
        affected_groups = set()

        for branch in branches_with_dec_target:
            dept_mask = (df['Филиал'] == branch) & (df['Отдел'] == dept_name)
            if not dept_mask.any():
                continue

            month_data = {}
            for month in range(1, 13):
                month_mask = dept_mask & (df['Месяц'] == month)
                if not month_mask.any():
                    continue
                idx = df.index[month_mask][0]
                fact_2025 = df.loc[idx, 'Выручка_2025'] if 'Выручка_2025' in df.columns else 0
                fact_2024 = df.loc[idx, 'Выручка_2024'] if 'Выручка_2024' in df.columns else 0
                fact_2025 = fact_2025 if pd.notna(fact_2025) else 0
                fact_2024 = fact_2024 if pd.notna(fact_2024) else 0
                floor_val = max(fact_2024, fact_2025 * INFLATION)
                corr = df.loc[idx, 'Корр'] if pd.notna(df.loc[idx, 'Корр']) else None
                delta = df.loc[idx, 'Корр_Дельта'] if 'Корр_Дельта' in df.columns and pd.notna(df.loc[idx, 'Корр_Дельта']) else None
                month_data[month] = {'idx': idx, 'floor': floor_val, 'corr': corr, 'delta': delta, 'seasonality': seasonality.get(month, 1/12)}

            if 12 not in month_data or month_data[12]['corr'] is None:
                continue

            start_level = month_data[1]['floor'] if 1 in month_data else 0
            target_dec = month_data[12]['corr'] + (month_data[12]['delta'] or 0)
            total_growth = target_dec - start_level
            if total_growth == 0:
                continue
            is_decline = total_growth < 0

            def calc_progress(month):
                if month < 1:
                    return 0.0
                q_end = get_quarter_end(month)
                q_start = get_quarter_start(month)
                prev_q_end = q_start - 1 if q_start > 1 else 0
                prev_progress = quarter_progress.get(prev_q_end, 0.0)
                curr_q_progress = quarter_progress[q_end]
                q_growth_share = curr_q_progress - prev_progress
                q_months = [q_start, q_start + 1, q_start + 2]
                q_seasonality = [month_data.get(m, {}).get('seasonality', 1/12) for m in q_months]
                q_total_season = sum(q_seasonality)
                if q_total_season <= 0:
                    ratio = (month - q_start + 1) / 3
                else:
                    cumsum = sum(q_seasonality[i] for i, m in enumerate(q_months) if m <= month)
                    ratio = cumsum / q_total_season
                return prev_progress + q_growth_share * ratio

            for month in sorted(month_data.keys()):
                md = month_data[month]
                idx = md['idx']
                if md['corr'] is not None and month != 12:
                    manual_plan = max(0, md['corr'] + (md['delta'] or 0))
                    df.loc[idx, 'План_Скорр'] = manual_plan
                    df.loc[idx, 'План_Расч'] = manual_plan
                    affected_groups.add((branch, month))
                    continue
                progress = calc_progress(month)
                smooth_plan = start_level + total_growth * progress
                final_plan = smooth_plan if is_decline else max(smooth_plan, md['floor'])
                if md['delta'] and md['corr'] is None:
                    final_plan += md['delta']
                final_plan = int(round(max(0, final_plan) / self.rounding_step) * self.rounding_step)
                df.loc[idx, 'План_Скорр'] = final_plan
                df.loc[idx, 'Авто_Корр'] = final_plan
                affected_groups.add((branch, month))

        if verbose:
            print(f"🔧 {dept_name}: затронуто {len(affected_groups)} групп")
        return affected_groups

    def apply_doors_smooth_growth(self, df, verbose=False):
        return self.apply_smooth_growth(df, '9. Двери, фурнитура дверная', {3: 0.15, 6: 0.30, 9: 0.60, 12: 1.00}, verbose)

    def apply_kitchen_smooth_growth(self, df, verbose=True):
        return self.apply_smooth_growth(df, 'Мебель для кухни', {3: 0.15, 6: 0.30, 9: 0.60, 12: 1.00}, verbose)

    def rebalance_to_target(self, df, verbose=False):
        """Перебалансировка планов отделов к плану филиала."""
        rebalanced_count = 0
        force_adjusted_count = 0

        for (branch, month), group in df.groupby(['Филиал', 'Месяц']):
            plan_branch = group['План'].iloc[0]
            sum_plan = group['План_Скорр'].sum()
            diff = plan_branch - sum_plan
            if abs(diff) <= 1000:
                continue

            self.redistribute_group(df, branch, month, verbose=verbose)
            rebalanced_count += 1

            gm = (df['Филиал'] == branch) & (df['Месяц'] == month)
            new_sum = df.loc[gm, 'План_Скорр'].sum()
            remaining_diff = plan_branch - new_sum

            if abs(remaining_diff) > 1000:
                flexible_mask = gm & df['Корр'].isna()
                if 'Корр_Дельта' in df.columns:
                    flexible_mask &= df['Корр_Дельта'].isna()
                if 'Авто_Корр' in df.columns:
                    flexible_mask &= df['Авто_Корр'].isna()
                if 'Правило' in df.columns:
                    flexible_mask &= (df['Правило'] != 'Не считаем план')

                if flexible_mask.any():
                    max_idx = df.loc[flexible_mask, 'План_Скорр'].idxmax()
                    old_plan = df.at[max_idx, 'План_Скорр']
                    new_plan = int(round(max(0, old_plan + remaining_diff) / self.rounding_step) * self.rounding_step)
                    df.at[max_idx, 'План_Скорр'] = new_plan
                    df.at[max_idx, 'План_Расч'] = new_plan
                    if verbose:
                        print(f"   🔧 {branch}/{month}: корректировка {remaining_diff:+,.0f}")
                    force_adjusted_count += 1

        return rebalanced_count, force_adjusted_count


# Глобальный экземпляр калькулятора
plan_calculator = PlanCalculator()

# ============================================================================
# ДАШБОРД
# ============================================================================

# Optional columns list
OPTIONAL_COLS = [
    'Выручка_2025', 'Выручка_2024', 'Выручка_2025_Норм', 'Прирост_%', 'Прирост_24_26_%',
    'Сезонность_Факт', 'Сезонность_План', 'Площадь_2025', 'Площадь_2026',
    'Δ_Площадь_%', 'Отдача_План', 'Отдача_2025', 'Δ_Отдача_%',
    'Формат', 'Роль', 'Правило',
    'План', 'План_Расч', '_План_Расч_Исх', 'Авто_Корр',
    'Final_Weight', 'is_network_format'
]

class PlanDashboard:
    def __init__(self, df, df_roles=None, gc_client=None):
        self.df = df.copy(deep=True).reset_index(drop=True)
        self.df_roles = df_roles
        self.gc = gc_client
        self.show_only_corrections = False
        self._updating = False
        self._cached_filtered_df = None

        # Конвертация месяцев
        if self.df['Месяц'].dtype == 'object' or self.df['Месяц'].iloc[0] in MONTH_MAP:
            self.df['_Месяц_текст'] = self.df['Месяц'].copy()
            self.df['Месяц'] = self.df['Месяц'].map(MONTH_MAP)
        else:
            self.df['_Месяц_текст'] = self.df['Месяц'].map(MONTH_MAP_REV)

        self.cols_available = set(col for col in OPTIONAL_COLS if col in self.df.columns)

        # Списки для фильтров
        self.all_branches = sorted([x for x in self.df['Филиал'].unique().tolist() if pd.notna(x) and str(x).lower() != 'nan'])
        self.all_depts = sorted([x for x in self.df['Отдел'].unique().tolist() if pd.notna(x) and str(x).lower() != 'nan'])
        self.all_formats = sorted([x for x in self.df['Формат'].unique().tolist() if pd.notna(x) and str(x).lower() != 'nan']) if 'Формат' in self.cols_available else []
        self.all_roles = sorted([x for x in self.df['Роль'].unique().tolist() if pd.notna(x) and str(x).lower() != 'nan']) if 'Роль' in self.cols_available else []
        self.all_rules = sorted([x for x in self.df['Правило'].unique().tolist() if pd.notna(x) and str(x).lower() != 'nan']) if 'Правило' in self.cols_available else []

        self._save_pending = False

        for col, default in [('Корр', np.nan), ('Корр_Дельта', np.nan), ('Рекоменд', None)]:
            if col not in self.df.columns:
                self.df[col] = self.df['План_Скорр'].copy() if col == 'Рекоменд' else default

        self.df['_План_Расч_Исх'] = self.df['План_Расч'].copy() if 'План_Расч' in self.df.columns else self.df['План_Скорр'].copy()

        if 'Прирост_24_26_%' not in self.df.columns:
            self.df['Прирост_24_26_%'] = 0.0

        recalc_row_metrics(self.df, self.df.index, self.cols_available)

        self._calc_seasonality()

        # Диагностика Москва Хаб ДО _load_corrections
        _hub_jan_before = self.df[(self.df['Филиал'].str.contains('Хаб', na=False)) & (self.df['Месяц'] == 'янв')]
        if len(_hub_jan_before) > 0:
            _sant_hub = _hub_jan_before[_hub_jan_before['Отдел'].str.contains('Сантехника', na=False) & ~_hub_jan_before['Отдел'].str.contains('инженерная', na=False, case=False)]
            if len(_sant_hub) > 0:
                print(f"🔍 Москва Хаб/Сантехника янв ДО _load_corrections: План_Скорр={_sant_hub['План_Скорр'].values[0]:.0f}")

        _moscow_aug_before_corr = self.df[(self.df['Филиал'].str.contains('Москва', na=False)) & (self.df['Месяц'] == 'авг')]
        if len(_moscow_aug_before_corr) > 0:
            _sant_before_corr = _moscow_aug_before_corr[_moscow_aug_before_corr['Отдел'].str.contains('Сантехника', na=False) & ~_moscow_aug_before_corr['Отдел'].str.contains('инженерная', na=False, case=False)]
            if len(_sant_before_corr) > 0:
                print(f"   План_Скорр={_sant_before_corr['План_Скорр'].values[0]:.0f}")

        self._load_corrections()

        # Диагностика Москва Хаб ПОСЛЕ _load_corrections
        _hub_jan_after = self.df[(self.df['Филиал'].str.contains('Хаб', na=False)) & (self.df['Месяц'] == 'янв')]
        if len(_hub_jan_after) > 0:
            _sant_hub_after = _hub_jan_after[_hub_jan_after['Отдел'].str.contains('Сантехника', na=False) & ~_hub_jan_after['Отдел'].str.contains('инженерная', na=False, case=False)]
            if len(_sant_hub_after) > 0:
                print(f"🔍 Москва Хаб/Сантехника янв ПОСЛЕ _load_corrections: План_Скорр={_sant_hub_after['План_Скорр'].values[0]:.0f}")

        _moscow_aug_dash = self.df[(self.df['Филиал'].str.contains('Москва', na=False)) & (self.df['Месяц'] == 'авг')]
        if len(_moscow_aug_dash) > 0:
            _sant_dash = _moscow_aug_dash[_moscow_aug_dash['Отдел'].str.contains('Сантехника', na=False) & ~_moscow_aug_dash['Отдел'].str.contains('инженерная', na=False, case=False)]
            if len(_sant_dash) > 0:
                print(f"   План_Скорр={_sant_dash['План_Скорр'].values[0]:.0f}")

        self._calc_recommendation()

        # ВАЖНО: df_original создаём ПОСЛЕ загрузки корректировок!
        # Теперь df_original содержит правильное распределение с учётом всех корректировок

        # Применяем минимальный план для сетевых форматов (Мини/Микро/Интернет)
        self._apply_min_plan_network()

        # ВАЖНО: Повторно применяем лимиты роста ПОСЛЕ загрузки корректировок
        # только для отделов БЕЗ ручных корректировок
        print("🔄 Повторное применение лимитов после загрузки корректировок...")
        limits_dict = {}
        try:
            limits_dict = load_limits_local()
        except:
            pass

        if limits_dict:
            no_corr_mask = ~has_correction(self.df)
            reapplied = 0
            for idx in self.df.index:
                if not no_corr_mask.loc[idx]:
                    continue  # Пропускаем строки с корректировками

                branch = self.df.loc[idx, 'Филиал']
                dept = self.df.loc[idx, 'Отдел']
                key = f"{branch}|||{dept}"

                if key not in limits_dict:
                    continue  # Нет лимита для этого отдела

                max_growth = limits_dict[key]
                fact = self.df.loc[idx, 'Выручка_2025']
                if fact <= 0:
                    continue

                max_plan = fact * (1 + max_growth / 100)
                current_plan = self.df.loc[idx, 'План_Скорр']

                # ВАЖНО: Для отделов с лимитами без ручных корректировок
                # план должен быть РАВЕН max_plan (не выше и не ниже)
                if abs(current_plan - max_plan) > 1:  # Допуск на округление
                    self.df.loc[idx, 'План_Расч'] = max_plan
                    self.df.loc[idx, 'План_Скорр'] = max_plan
                    reapplied += 1

            if reapplied > 0:
                print(f"   ↩️ Повторно применено лимитов: {reapplied}")

        # DEBUG: проверка состояния df ПЕРЕД созданием df_original
        mh_mebel_check = (self.df['Филиал'].str.contains('Хаб', na=False)) & (self.df['Отдел'].str.contains('Мебель для дома', na=False)) & (self.df['Месяц'] == 11)
        if mh_mebel_check.any():
            val = self.df.loc[mh_mebel_check, 'План_Скорр'].values[0]
            print(f"🔍 ПЕРЕД df_original: МХ/Мебель/ноя План_Скорр={val:,.0f}")

        # DEBUG: Вологда ТЦ Мебель для кухни декабрь
        vol_kitchen_dec = (self.df['Филиал'] == 'Вологда ТЦ') & (self.df['Отдел'] == 'Мебель для кухни') & (self.df['Месяц'] == 12)
        if vol_kitchen_dec.any():
            row = self.df.loc[vol_kitchen_dec].iloc[0]
            print(f"🍳 ВОЛОГДА КУХНЯ ДЕКАБРЬ ПЕРЕД df_original:")
            print(f"   Корр = {row.get('Корр', 'N/A')}")
            print(f"   Авто_Корр = {row.get('Авто_Корр', 'N/A')}")
            print(f"   План_Скорр = {row.get('План_Скорр', 'N/A'):,.0f}")
            print(f"   Рекоменд = {row.get('Рекоменд', 'N/A'):,.0f}")

        self.df_original = self.df.copy(deep=True)

        # Проверка для Москва Хаб после создания df_original
        mh_mebel_mask = (self.df['Филиал'].str.contains('Хаб', na=False)) & (self.df['Отдел'].str.contains('Мебель для дома', na=False))
        if mh_mebel_mask.any():
            for m in [1, 11, 12]:
                m_mask = mh_mebel_mask & (self.df['Месяц'] == m)
                if m_mask.any():
                    plan_df = self.df.loc[m_mask, 'План_Скорр'].values[0]
                    plan_orig = self.df_original.loc[m_mask, 'План_Скорр'].values[0]
                    print(f"🔍 df_original МХ/Мебель/{m}: df={plan_df:,.0f}, orig={plan_orig:,.0f}")

        # Проверка для Вологда ТЦ после создания df_original
        vologda_jan_mask = (self.df['Филиал'] == 'Вологда ТЦ') & (self.df['Отдел'] == 'Мебель для кухни') & (self.df['Месяц'] == 1)
        if vologda_jan_mask.any():
            plan_df = self.df.loc[vologda_jan_mask, 'План_Скорр'].values[0]
            plan_orig = self.df_original.loc[vologda_jan_mask, 'План_Скорр'].values[0]
            print(f"🔍 После df_original: Вологда ТЦ янв Мебель План_Скорр={plan_df:,.0f}, df_original={plan_orig:,.0f}")

        # Инициализируем словарь лимитов
        self._branch_dept_limits = {}
        self._accompanying_depts = []
        self._branches_by_format = {}

        self._setup_widgets()
        self._setup_table()

        # DEBUG: Проверка равенства Корр и План_Скорр при старте
        self._debug_check_corr_vs_plan()

    # ========== Сезонность ==========

    def _calc_seasonality(self):
        """Векторизованный расчёт сезонности факта"""
        if 'Правило' in self.cols_available:
            dept_rules = self.df.groupby('Отдел')['Правило'].first().fillna('').str.lower()
            self.df['_rule_lower'] = self.df['Отдел'].map(dept_rules)
            use_only_2025 = self.df['_rule_lower'].str.contains('только 2025|формат', regex=True)
        else:
            use_only_2025 = pd.Series(False, index=self.df.index)

        if 'Выручка_2024' in self.cols_available:
            rev_avg = (self.df['Выручка_2024'].fillna(0) + self.df['Выручка_2025'].fillna(0)) / 2
        else:
            rev_avg = self.df['Выручка_2025'].fillna(0)

        self.df['_rev_for_season'] = np.where(use_only_2025, self.df['Выручка_2025'], rev_avg)

        self.df['_month_rev'] = self.df.groupby(['Отдел', 'Месяц'])['_rev_for_season'].transform('sum')
        self.df['_year_rev'] = self.df.groupby('Отдел')['_rev_for_season'].transform('sum')

        self.df['Сезонность_Факт'] = np.where(
            self.df['_year_rev'] > 0,
            (self.df['_month_rev'] / self.df['_year_rev'] * 100).round(1),
            0.0
        )

        cols_to_drop = ['_rev_for_season', '_month_rev', '_year_rev']
        if '_rule_lower' in self.df.columns:
            cols_to_drop.append('_rule_lower')
        self.df.drop(columns=cols_to_drop, inplace=True)

        self._update_seasonality_plan()

    def _update_seasonality_plan(self):
        """Векторизованный расчёт сезонности плана"""
        self.df['_month_plan'] = self.df.groupby(['Отдел', 'Месяц'])['План_Скорр'].transform('sum')
        self.df['_year_plan'] = self.df.groupby('Отдел')['План_Скорр'].transform('sum')

        self.df['Сезонность_План'] = np.where(
            self.df['_year_plan'] > 0,
            (self.df['_month_plan'] / self.df['_year_plan'] * 100).round(1),
            0.0
        )

        self.df.drop(columns=['_month_plan', '_year_plan'], inplace=True)

    def _calc_recommendation(self):
        """Векторизованный расчёт рекомендаций"""
        self.df['Рекоменд'] = self.df['План_Скорр'].copy()

        corr_mask = has_correction(self.df)
        if not corr_mask.any():
            return

        self.df['_implied_year'] = np.where(
            corr_mask & (self.df['Сезонность_Факт'] > 0) & (self.df['План_Скорр'] > 0),
            self.df['План_Скорр'] / (self.df['Сезонность_Факт'] / 100),
            np.nan
        )

        self.df['_avg_implied_year'] = self.df.groupby(['Филиал', 'Отдел'])['_implied_year'].transform('mean')

        has_avg = self.df['_avg_implied_year'].notna() & (self.df['Сезонность_Факт'] > 0)
        self.df.loc[has_avg, 'Рекоменд'] = (
            (self.df.loc[has_avg, '_avg_implied_year'] * self.df.loc[has_avg, 'Сезонность_Факт'] / 100 / 10000)
            .round(0) * 10000
        ).astype(int)

        self.df.drop(columns=['_implied_year', '_avg_implied_year'], inplace=True)

    def _apply_min_plan_network(self, silent=False):
        """
        Применяет правило минимального плана для Мини/Микро/Интернет форматов.

        Правило: План_Скорр >= Выручка_2025 × 1.06, с округлением до 10,000 если < 70,000

        Сходимость гарантируется: добавленное к отделам ниже минимума
        снимается с других отделов пропорционально их текущему плану.

        ВАЖНО: Отделы с лимитами роста исключаются из "доноров", чтобы не нарушать лимиты.
        """
        NETWORK_FORMATS = ['Мини', 'Микро', 'Интернет', 'Интернет магазин']
        MIN_GROWTH = 1.06  # +6%
        ROUND_THRESHOLD = 70000
        ROUND_STEP = 10000

        # Загружаем лимиты для исключения из доноров
        limits_dict = {}
        try:
            limits_dict = load_limits_local()
        except:
            pass

        if 'Формат' not in self.df.columns:
            if not silent:
                print("⚠️ _apply_min_plan_network: нет колонки Формат")
            return

        network_mask = self.df['Формат'].isin(NETWORK_FORMATS)
        if not network_mask.any():
            if not silent:
                print("⚠️ _apply_min_plan_network: нет строк с сетевыми форматами")
            return

        if not silent:
            print(f"\n🔧 _apply_min_plan_network: {network_mask.sum()} строк с сетевыми форматами")

            # Debug: Владимир Розница формат
            vr_mask = self.df['Филиал'] == 'Владимир Розница'
            if vr_mask.any():
                vr_format = self.df.loc[vr_mask, 'Формат'].iloc[0]
                vr_in_network = vr_format in NETWORK_FORMATS
                vr_network_rows = (vr_mask & network_mask).sum()
                print(f"   📍 Владимир Розница: формат='{vr_format}', в сетевых={vr_in_network}, строк в network_mask={vr_network_rows}")

            # Debug: Владимир Лента до обработки
            vl_mask = (self.df['Филиал'] == 'Владимир Лента') & (self.df['Отдел'] == '10. Товары для дома')
            if vl_mask.any():
                vl_data = self.df[vl_mask].head(3)
                print(f"   Владимир Лента / 10. Товары для дома ДО:")
                for _, row in vl_data.iterrows():
                    print(f"      {row['Месяц']}: План_Скорр={row['План_Скорр']:.0f}, Выр25={row['Выручка_2025']:.0f}")

        def ceil_step(val):
            """
            Округляет значение до ROUND_STEP:
            - Сначала округляем (ceil если < 70000, round иначе)
            - Если результат < 20,000 → 0 (не считаем план)
            """
            MIN_PLAN_THRESHOLD = 20000
            if val <= 0:
                return 0

            # Сначала округляем
            if val < ROUND_THRESHOLD:
                rounded = np.ceil(val / ROUND_STEP) * ROUND_STEP
            else:
                rounded = round(val / ROUND_STEP) * ROUND_STEP

            # Если план < 20000 — не считаем
            if rounded < MIN_PLAN_THRESHOLD:
                return 0

            return rounded

        adjustments_made = 0

        # Обрабатываем по группам Филиал + Месяц
        for (branch, month), group_idx in self.df[network_mask].groupby(['Филиал', 'Месяц']).groups.items():
            indices = list(group_idx)

            rev_2025 = self.df.loc[indices, 'Выручка_2025'].fillna(0)
            plan_skorr = self.df.loc[indices, 'План_Скорр'].fillna(0)

            # Минимум = Выручка × 1.06, округлённый (или 0 если < 20000)
            min_plan = (rev_2025 * MIN_GROWTH).apply(ceil_step)

            # Обнуляем планы < 20,000 для отделов с маленькой выручкой
            # НО только если нет ручной корректировки
            MIN_PLAN_THRESHOLD = 20000
            for idx in indices:
                has_manual_corr = pd.notna(self.df.loc[idx, 'Корр']) or pd.notna(self.df.loc[idx, 'Корр_Дельта'])
                if not has_manual_corr and 0 < self.df.loc[idx, 'План_Скорр'] < MIN_PLAN_THRESHOLD:
                    self.df.loc[idx, 'План_Скорр'] = 0
                    self.df.loc[idx, 'Рекоменд'] = 0

            # Пересчитываем plan_skorr после обнуления
            plan_skorr = self.df.loc[indices, 'План_Скорр'].fillna(0)

            # Отделы ниже минимума (с выручкой > 0 И минимум > 0)
            below_min_mask = (plan_skorr < min_plan) & (rev_2025 > 0) & (min_plan > 0)

            # Исключаем строки с ручными корректировками
            has_corr = self.df.loc[indices, 'Корр'].notna() | self.df.loc[indices, 'Корр_Дельта'].notna()
            below_min_mask = below_min_mask & ~has_corr

            # DEBUG: Владимир Розница / 2. Стройматериалы
            if 'Владимир Розница' in branch and str(month) in ['1', 'янв']:
                print(f"\n   🔍 DEBUG: Владимир Розница / {month} - проверка всех отделов:")
                print(f"      Всего отделов в группе: {len(indices)}")
                print(f"      Отделов ниже минимума (before has_corr filter): {((plan_skorr < min_plan) & (rev_2025 > 0) & (min_plan > 0)).sum()}")
                print(f"      Отделов с корректировкой (has_corr): {has_corr.sum()}")
                print(f"      Отделов ниже минимума (after has_corr filter): {below_min_mask.sum()}")

                # Показываем топ-5 по выручке
                top_rev = sorted([(self.df.loc[idx, 'Отдел'], rev_2025.loc[idx], plan_skorr.loc[idx], min_plan.loc[idx])
                                  for idx in indices], key=lambda x: -x[1])[:5]
                print(f"      Топ-5 по выручке:")
                for dept, r25, ps, mp in top_rev:
                    status = "✗ НИЖЕ" if ps < mp and r25 > 0 else "✓ OK"
                    print(f"         {dept[:30]}: Выр25={r25:,.0f}, План={ps:,.0f}, Мин={mp:,.0f} {status}")

                stroy_mask = self.df.loc[indices, 'Отдел'] == '2. Стройматериалы'
                if stroy_mask.any():
                    stroy_idx = [idx for idx, is_stroy in zip(indices, stroy_mask) if is_stroy]
                    if stroy_idx:
                        idx = stroy_idx[0]
                        print(f"\n      📊 2. Стройматериалы детально:")
                        print(f"         Выручка_2025 = {rev_2025.loc[idx]:,.0f}")
                        print(f"         План_Скорр = {plan_skorr.loc[idx]:,.0f}")
                        print(f"         min_plan (×1.06) = {min_plan.loc[idx]:,.0f}")
                        print(f"         plan_skorr < min_plan? {plan_skorr.loc[idx] < min_plan.loc[idx]}")
                        print(f"         rev_2025 > 0? {rev_2025.loc[idx] > 0}")
                        print(f"         min_plan > 0? {min_plan.loc[idx] > 0}")
                        print(f"         has_corr? {has_corr.loc[idx]}")
                        print(f"         below_min_mask? {below_min_mask.loc[idx]}")

            below_indices = [idx for idx, is_below in zip(indices, below_min_mask) if is_below]

            if not below_indices:
                continue

            # Считаем дефицит
            deficit = sum(min_plan.loc[idx] - plan_skorr.loc[idx] for idx in below_indices)
            if deficit <= 0:
                continue

            # Debug для Владимир Розница
            if 'Владимир Розница' in branch:
                print(f"\n      📈 Дефицит для покрытия: {deficit:,.0f}")
                print(f"      Отделов ниже минимума: {len(below_indices)}")

            # Debug для Владимира Лента
            if not silent and 'Владимир Лента' in branch and month in [1, 12]:
                print(f"\n   📊 {branch} / месяц {month}:")
                print(f"      Дефицит: {deficit:,.0f}")
                print(f"      Отделов ниже минимума: {len(below_indices)}")

            # Поднимаем отделы до минимума
            for idx in below_indices:
                old_val = self.df.loc[idx, 'План_Скорр']
                new_val = min_plan.loc[idx]
                self.df.loc[idx, 'План_Скорр'] = new_val
                self.df.loc[idx, 'Рекоменд'] = new_val
                adjustments_made += 1

                # Debug для Владимир Розница
                if 'Владимир Розница' in branch:
                    print(f"      ↑ {self.df.loc[idx, 'Отдел']}: {old_val:,.0f} → {new_val:,.0f}")

                # Debug
                if not silent and 'Владимир Лента' in branch and self.df.loc[idx, 'Отдел'] == '10. Товары для дома':
                    print(f"      ↑ 10. Товары для дома: {old_val:.0f} → {new_val:.0f}")

            # Снимаем дефицит с других отделов пропорционально их плану
            # Исключаем: 1) строки с ручными корректировками, 2) отделы с лимитами роста
            other_indices = [idx for idx in indices if idx not in below_indices]
            # Фильтруем доноров - не снимаем с тех, у кого есть корректировка
            other_indices = [idx for idx in other_indices
                           if not (pd.notna(self.df.loc[idx, 'Корр']) or pd.notna(self.df.loc[idx, 'Корр_Дельта']))]

            # Debug для Владимир Розница
            if 'Владимир Розница' in branch:
                print(f"      Потенциальных доноров: {len(other_indices)}")
                if other_indices:
                    total_donor_plan = sum(self.df.loc[idx, 'План_Скорр'] for idx in other_indices)
                    print(f"      Сумма планов доноров: {total_donor_plan:,.0f}")

            # ВАЖНО: Также исключаем отделы с лимитами роста - их план нельзя снижать!
            if limits_dict:
                excluded_count = 0
                excluded_examples = []
                new_other_indices = []
                for idx in other_indices:
                    key = f"{self.df.loc[idx, 'Филиал']}|||{self.df.loc[idx, 'Отдел']}"
                    if key in limits_dict:
                        excluded_count += 1
                        if excluded_count <= 3:
                            excluded_examples.append(f"{self.df.loc[idx, 'Отдел']}")
                    else:
                        new_other_indices.append(idx)
                if excluded_count > 0 and not silent and 'Москва Хаб' in branch:
                    print(f"      🚫 Исключено из доноров (лимиты): {excluded_count} отд. ({', '.join(excluded_examples)})")
                other_indices = new_other_indices
            if not other_indices:
                # Debug для Владимир Розница
                if 'Владимир Розница' in branch:
                    print(f"      ⚠️ НЕТ ДОНОРОВ! Но планы УЖЕ подняты до минимума.")
                    print(f"      ⚠️ Сходимость нарушена - сумма планов > план филиала!")
                continue

            other_plans = self.df.loc[other_indices, 'План_Скорр']
            total_other = other_plans.sum()

            if total_other <= 0:
                # Debug для Владимир Розница
                if 'Владимир Розница' in branch:
                    print(f"      ⚠️ Сумма планов доноров = 0! Сходимость нарушена.")
                continue

            # Снимаем пропорционально, с округлением
            rounding_step = CONFIG.get('rounding_step', 10000)
            total_reduction = 0
            for idx in other_indices:
                share = self.df.loc[idx, 'План_Скорр'] / total_other
                reduction = deficit * share
                new_plan = max(0, self.df.loc[idx, 'План_Скорр'] - reduction)
                # Округляем математически до 10000
                new_plan = round(new_plan / rounding_step) * rounding_step
                actual_reduction = self.df.loc[idx, 'План_Скорр'] - new_plan
                total_reduction += actual_reduction
                self.df.loc[idx, 'План_Скорр'] = new_plan
                self.df.loc[idx, 'Рекоменд'] = new_plan

            # Корректировка ошибки округления для сходимости
            # deficit = сколько добавили, total_reduction = сколько сняли
            rounding_error = deficit - total_reduction
            if abs(rounding_error) >= rounding_step and other_indices:
                # Корректируем на самом большом доноре
                max_idx = max(other_indices, key=lambda i: self.df.loc[i, 'План_Скорр'])
                self.df.loc[max_idx, 'План_Скорр'] -= rounding_error
                self.df.loc[max_idx, 'Рекоменд'] = self.df.loc[max_idx, 'План_Скорр']

        # Debug: Владимир Лента после обработки
        if not silent:
            vl_mask = (self.df['Филиал'] == 'Владимир Лента') & (self.df['Отдел'] == '10. Товары для дома')
            if vl_mask.any():
                vl_data = self.df[vl_mask].head(3)
                print(f"\n   Владимир Лента / 10. Товары для дома ПОСЛЕ:")
                for _, row in vl_data.iterrows():
                    print(f"      {row['Месяц']}: План_Скорр={row['План_Скорр']:.0f}")

            if adjustments_made > 0:
                print(f"\n✅ Минимальный план +6% для Мини/Микро/Интернет: {adjustments_made} корректировок")

        # Пересчитываем метрики (Δ% к 2025 и др.) после изменения План_Скорр
        if adjustments_made > 0:
            recalc_row_metrics(self.df, self.df.index, self.cols_available)

    # ========== Загрузка корректировок ==========

    def _get_filters_filepath(self):
        """Путь к локальному файлу с фильтрами (fallback)"""
        import os
        return os.path.join(os.getcwd(), 'filters.json')

    def _load_filters(self):
        """Загружает состояние фильтров (Local)"""
        try:
            return load_filters_local()
        except Exception as e:
            print(f"⚠️ Grid load err: {e}")
            return {}
    def _save_filters(self):
        """Сохраняет состояние фильтров (Local)"""
        try:
            filters_data = {}
            if hasattr(self, 'filters'):
                for key, f in self.filters.items():
                    val = f['select'].value
                    if val is None:
                        filters_data[key] = []
                    elif isinstance(val, (list, tuple)):
                        filters_data[key] = list(val)
                    else:
                        filters_data[key] = [val]

            filters_data['show_corrections'] = getattr(self, 'show_only_corrections', False)

            save_filters_local(filters_data)

        except Exception as e:
            print(f"⚠️ Save filters err: {e}")
    def _get_corrections_filepath(self):
        """Путь к локальному файлу с корректировками (fallback)"""
        import os
        return os.path.join(os.getcwd(), 'corrections.json')

    def _load_corrections(self):
        """Загружает корректировки из локального JSON"""
        import json
        import os

        # Загружаем корректировки из локального файла
        corrections = load_corrections_local()

        if not corrections:
            print("ℹ️ Нет корректировок для загрузки")
            return

        print(f"📥 Начинаю применять {len(corrections)} корректировок...")

        try:
            # ШАГ 1: Применяем все корректировки к df БЕЗ пересчёта
            applied_idx = []
            affected_groups = set()
            not_found = []

            # Получаем уникальные филиалы и отделы из df для сравнения
            df_branches = set(self.df['Филиал'].unique())
            df_depts = set(self.df['Отдел'].unique())

            for corr in corrections:
                branch = corr.get('branch', '')
                dept = corr.get('dept', '')
                month = corr.get('month', 0)
                corr_val = corr.get('corr')
                delta_val = corr.get('delta')

                # Находим строку в df
                mask = (self.df['Филиал'] == branch) & (self.df['Отдел'] == dept) & (self.df['Месяц'] == month)
                if mask.sum() == 0:
                    # Определяем причину
                    reason = []
                    if branch not in df_branches:
                        reason.append(f"филиал '{branch}' не найден")
                    if dept not in df_depts:
                        reason.append(f"отдел '{dept}' не найден")
                    not_found.append(f"{branch} / {dept} / мес={month}: {', '.join(reason) if reason else 'комбинация не найдена'}")
                    continue

                idx = self.df.index[mask][0]

                # Применяем корректировки ко ВСЕМ форматам (включая сетевые)
                if corr_val is not None:
                    self.df.loc[idx, 'Корр'] = corr_val
                if delta_val is not None:
                    self.df.loc[idx, 'Корр_Дельта'] = delta_val

                # DEBUG: отслеживаем корректировки для Москва Хаб / Мебель
                if 'Хаб' in branch and 'Мебель для дома' in dept:
                    print(f"⚠️ ЗАГРУЗКА КОРР: {branch}/{dept}/{month} - Корр={corr_val}, Дельта={delta_val}")

                applied_idx.append(idx)
                affected_groups.add((branch, month))

            # ШАГ 2: Пересчитываем планы БАТЧЕМ
            if applied_idx:
                for idx in applied_idx:
                    self._recalc_plan(self.df.index == idx)

            # ШАГ 3: НЕ пересчитываем здесь - это сделает _apply_elasticity
            print(f"✅ Применено корректировок: {len(applied_idx)}")
            if not_found:
                print(f"⚠️ Не найдено: {len(not_found)}")

            # ШАГ 4: Применяем специальную логику плавного роста
            self._apply_doors_smooth_growth()
            self._apply_kitchen_smooth_growth()

        except Exception as e:
            print(f"❌ Ошибка загрузки корректировок: {e}")

    def _apply_doors_smooth_growth(self):
        """Плавный рост для Дверей - делегирует в plan_calculator"""
        affected = plan_calculator.apply_doors_smooth_growth(self.df, verbose=False)
        if affected and hasattr(self, 'df_original') and self.df_original is not None:
            for branch, month in affected:
                mask = (self.df['Филиал'] == branch) & (self.df['Месяц'] == month)
                self.df_original.loc[mask, 'План_Скорр'] = self.df.loc[mask, 'План_Скорр']
                if 'Авто_Корр' in self.df.columns:
                    self.df_original.loc[mask, 'Авто_Корр'] = self.df.loc[mask, 'Авто_Корр']

    def _apply_kitchen_smooth_growth(self):
        """Плавный рост для Мебели для кухни - делегирует в plan_calculator"""
        affected = plan_calculator.apply_kitchen_smooth_growth(self.df, verbose=True)
        if affected and hasattr(self, 'df_original') and self.df_original is not None:
            for branch, month in affected:
                mask = (self.df['Филиал'] == branch) & (self.df['Месяц'] == month)
                self.df_original.loc[mask, 'План_Скорр'] = self.df.loc[mask, 'План_Скорр']
                if 'Авто_Корр' in self.df.columns:
                    self.df_original.loc[mask, 'Авто_Корр'] = self.df.loc[mask, 'Авто_Корр']

    # ========== Виджеты ==========

    def _setup_widgets(self):
        # Загружаем сохранённые фильтры
        saved_filters = self._load_filters()

        # Config: (key, name, options, widget_type)
        filter_configs = [
            ('branch', 'Филиалы', self.all_branches, 'choice'),
            ('dept', 'Отделы', self.all_depts, 'choice'),
            ('format', 'Формат', self.all_formats, 'check'),
            ('month', 'Месяцы', list(MONTH_MAP.keys()), 'check'),
            ('role', 'Роль', self.all_roles, 'check'),
            ('rule', 'Правило', self.all_rules, 'check'),
        ]

        self.filters = {}
        for key, name, options, w_type in filter_configs:
            select, reset, indicator = create_filter_widget(name, options, widget_type=w_type)
            # Применяем сохранённые значения если есть
            if key in saved_filters:
                saved_vals = [v for v in saved_filters[key] if v in options]
                if saved_vals:
                    select.value = saved_vals

            self.filters[key] = {'select': select, 'reset': reset, 'indicator': indicator}
            select.param.watch(self._on_filter_change, 'value')

        self.all_optional_cols = [
            'Выручка_2025', 'Выручка_2024', 'Выручка_2025_Норм', 'Прирост_%', 'Прирост_24_26_%',
            'Сезонность_Факт', 'Сезонность_План', 'Площадь_2025', 'Площадь_2026',
            'Δ_Площадь_%', 'Отдача_План', 'Отдача_2025', 'Δ_Отдача_%',
            'Формат', 'Роль', 'Правило',
            'План', 'План_Расч', '_План_Расч_Исх', 'Авто_Корр',
            'Final_Weight', 'is_network_format'
        ]
        self.all_optional_cols = [c for c in self.all_optional_cols if c in self.df.columns]

        self.default_cols = [
            'Выручка_2025', 'Выручка_2024', 'Прирост_%', 'Прирост_24_26_%',
            'Сезонность_Факт', 'Сезонность_План', 'Площадь_2025', 'Площадь_2026',
            'Δ_Площадь_%', 'Отдача_План', 'Отдача_2025', 'Δ_Отдача_%',
            'Формат', 'Роль', 'Правило'
        ]
        self.default_cols = [c for c in self.default_cols if c in self.df.columns]

        col_select, col_reset, col_indicator = create_filter_widget('Столбцы', self.all_optional_cols, widget_type='choice')
        if 'columns' in saved_filters:
            saved_cols = [c for c in saved_filters['columns'] if c in self.all_optional_cols]
            col_select.value = saved_cols if saved_cols else self.default_cols
        else:
            col_select.value = self.default_cols
        col_reset.on_click(lambda e: setattr(col_select, 'value', self.default_cols))
        col_select.param.watch(self._on_filter_change, 'value')
        self.filters['columns'] = {'select': col_select, 'reset': col_reset, 'indicator': col_indicator}

        # RESTORED: Toggle for corrections
        self.corr_btn = pn.widgets.Toggle(name='Только корр.', value=False, button_type='default', width=100)
        def _on_corr_toggle(e):
             self.show_only_corrections = e.new
             self._cached_filtered_df = None
             self._update()
             self._save_filters()
        self.corr_btn.param.watch(_on_corr_toggle, 'value')



        self.corr_history, self.corr_history_idx = [], -1
        self.undo_btn = pn.widgets.Button(name='↩', width=28, height=24, button_type='light')
        self.undo_btn.on_click(self._undo_correction)
        self.redo_btn = pn.widgets.Button(name='↪', width=28, height=24, button_type='light')
        self.redo_btn.on_click(self._redo_correction)

        # Кнопка обновления графиков
        self.refresh_btn = pn.widgets.Button(name='🔄', width=28, height=24, button_type='primary')
        self.refresh_btn.on_click(self._refresh_charts)

        # Кнопка экспорта CSV
        self.export_btn = pn.widgets.FileDownload(
            callback=self._get_csv_data,
            filename='plan_export.csv',
            button_type='success',
            label='📥 CSV',
            width=65,
            height=24
        )

        self.status = pn.pane.HTML("", width=100, height=24)
        self.stats = pn.pane.HTML("", height=20, sizing_mode='stretch_width')
        self.chart_pane = pn.pane.Bokeh(sizing_mode='stretch_width', height=175)
        self.chart_branches_pane = pn.pane.HTML("", sizing_mode='stretch_width', height=200)
        self.chart_seasonality_pane = pn.pane.Bokeh(sizing_mode='stretch_width', height=175)

        # Сводная таблица приростов
        self.pivot_pane = pn.pane.HTML("", sizing_mode='stretch_width', height=200)

        self._pending_edits = []
        self._save_pending = False

        # Компактная статистика (всегда видна)
        self.compact_stats = pn.pane.HTML("", height=24, sizing_mode='stretch_width')

    def _update_compact_stats(self):
        """Компактная статистика для верхней строки - оптимизированно"""
        try:
            df = self._get_filtered_df()
        except:
            self.compact_stats.object = ""
            return
        if df.empty:
            self.compact_stats.object = "<div style='color:#888;font-size:11px;'>Нет данных</div>"
            return

        # Используем numpy для скорости
        sel_br = df['Филиал'].unique()
        sel_mo = df['Месяц'].unique()
        n_br, n_mo = len(sel_br), len(sel_mo)

        # Быстрый расчёт через numpy маски
        mask = np.isin(self.df['Филиал'].values, sel_br) & np.isin(self.df['Месяц'].values, sel_mo)
        total = int(self.df.loc[mask, 'План_Скорр'].sum())

        # target - только уникальные филиал-месяц
        if 'План' in self.df.columns:
            conv = self.df.loc[mask]
            target = int(round(conv.drop_duplicates(['Филиал', 'Месяц'])['План'].sum()))
        else:
            target = 0

        diff = total - target
        rev25 = df['Выручка_2025'].sum()
        g25 = ((total/rev25-1)*100) if rev25 > 0 else 0

        diff_color = '#1a9850' if diff == 0 else '#d73027'
        g25_color = '#1a9850' if g25 > 0 else '#d73027'

        # Кэшируем счётчики (редко меняются)
        growth_cnt = len(getattr(self, '_growth_branches', []))
        decline_cnt = len(getattr(self, '_decline_branches', []))

        # Счётчик изменённых слайдеров - кэшируем
        if not hasattr(self, '_changed_sliders_cache'):
            self._changed_sliders_cache = 0
        changed = self._changed_sliders_cache

        self.compact_stats.object = f"""<div style='display:flex;gap:10px;font-size:11px;align-items:center;white-space:nowrap;'>
            <b>План:</b> {total/1e6:.0f}М <b>Цель:</b> {target/1e6:.0f}М
            <b>Δ:</b> <span style='color:{diff_color};font-weight:bold;'>{diff/1e6:+.1f}М</span>
            <b>к25:</b> <span style='color:{g25_color};'>{g25:+.0f}%</span>
            <span style='color:#aaa;'>│</span>
            <span style='color:#1a9850;'>▲{growth_cnt}</span><span style='color:#d73027;'>▼{decline_cnt}</span>
            <span style='color:#aaa;'>│</span> {n_br}×{n_mo}
            {f"<span style='color:#ff9800;'>│ K≠1:{changed}</span>" if changed else ""}
        </div>"""

    def get_sidebar(self):
        """Возвращает панель фильтров для сайдбара"""

        def make_filter_block(key, title):
            f = self.filters[key]
            # Заголовок с кнопкой сброса
            header = pn.Row(
                pn.pane.Markdown(f"**{title}**", sizing_mode='stretch_width'),
                f['reset'],
                sizing_mode='stretch_width'
            )
            return pn.Column(
                header,
                f['select'],
                f['indicator'],
                pn.layout.Divider(),
                sizing_mode='stretch_width'
            )

        sidebar = pn.Column(
            pn.pane.Markdown("### Фильтры", sizing_mode='stretch_width'),
            make_filter_block('branch', 'Филиалы'),
            make_filter_block('dept', 'Отделы'),
            make_filter_block('format', 'Форматы'),
            make_filter_block('month', 'Месяцы'),
            make_filter_block('role', 'Роли'),
            make_filter_block('rule', 'Правила'),
            make_filter_block('columns', 'Столбцы'),
            sizing_mode='stretch_width',
            css_classes=['sidebar-scroll'] # Custom CSS class if needed
        )
        return sidebar
    def _on_filter_change(self, event=None):
        """Обработчик изменения фильтров - синхронный"""
        print(f"🔄 DEBUG: Filter change detected! Event: {event}") # DEBUG PRINT
        # Сбрасываем кэши
        self._cached_filtered_df = None
        self._cached_agg = None

        # Обновляем _last_table_df (для корректного отслеживания удалений)
        self._last_table_df = None

        # Обновляем UI сразу
        try:
            self._update_indicators()
            self.table.value = self._get_display_df()
            self._last_table_df = self.table.value.copy() if self.table.value is not None else None
            self._update_compact_stats()
            self._update_charts()
            print("✅ UI updated after filter change") # DEBUG PRINT
        except Exception as e:
            print(f"Filter error: {e}")
            import traceback
            traceback.print_exc()

        # Сохранение - отложенно через pn.state
        try:
            if hasattr(self, '_save_callback') and self._save_callback is not None:
                try:
                    self._save_callback.stop()
                except:
                    pass
            self._save_callback = pn.state.add_periodic_callback(
                self._save_filters_once, period=1500, count=1
            )
        except:
            pass

    def _save_filters_once(self):
        """Сохраняет фильтры один раз"""
        self._save_filters()
        if hasattr(self, '_save_callback') and self._save_callback is not None:
            try:
                self._save_callback.stop()
            except:
                pass
            self._save_callback = None

    def _get_cached_agg(self):
        """Кэшированные агрегаты для графиков - оптимизированно"""
        if hasattr(self, '_cached_agg') and self._cached_agg is not None:
            return self._cached_agg

        df = self._get_filtered_df()
        if df.empty:
            self._cached_agg = {}
            return self._cached_agg

        # Определяем колонки для агрегации
        agg_cols = ['План_Скорр', 'Выручка_2025']
        if 'Выручка_2024' in df.columns:
            agg_cols.append('Выручка_2024')

        # Предвычисляем нужные колонки как numpy массивы для скорости
        plan_arr = df['План_Скорр'].values
        plan_calc_arr = df['_План_Расч_Исх'].values if '_План_Расч_Исх' in df.columns else plan_arr
        rev25_arr = df['Выручка_2025'].values
        rev24_arr = df['Выручка_2024'].values if 'Выручка_2024' in df.columns else None
        month_arr = df['Месяц'].values
        branch_arr = df['Филиал'].values
        dept_arr = df['Отдел'].values
        role_arr = df['Роль'].values if 'Роль' in df.columns else None
        season_arr = df['Сезонность_Факт'].values if 'Сезонность_Факт' in df.columns else None

        # by_month - самый частый запрос
        by_month_data = {'Месяц': [], 'План_Скорр': [], 'План_Расч': [], 'Выручка_2025': []}
        if rev24_arr is not None:
            by_month_data['Выручка_2024'] = []

        for m in sorted(set(month_arr)):
            mask = month_arr == m
            by_month_data['Месяц'].append(m)
            by_month_data['План_Скорр'].append(plan_arr[mask].sum())
            by_month_data['План_Расч'].append(plan_calc_arr[mask].sum())
            by_month_data['Выручка_2025'].append(rev25_arr[mask].sum())
            if rev24_arr is not None:
                by_month_data['Выручка_2024'].append(rev24_arr[mask].sum())

        # Остальные агрегаты - через pandas (реже используются)
        agg_dict = {'План_Скорр': 'sum', 'Выручка_2025': 'sum'}
        if 'Выручка_2024' in df.columns:
            agg_dict['Выручка_2024'] = 'sum'

        self._cached_agg = {
            'by_month': pd.DataFrame(by_month_data),
            'by_branch_month': df.groupby(['Филиал', 'Месяц'], sort=False).agg(agg_dict).reset_index(),
            'by_dept_role_month': df.groupby(['Отдел', 'Роль', 'Месяц'], sort=False).agg(agg_dict).reset_index(),
            'seasonality': df.groupby('Месяц', sort=False)['Сезонность_Факт'].mean() if season_arr is not None else None,
        }
        return self._cached_agg

    def _do_update(self):
        try:
            self.table.value = self._get_display_df()
            self._update_stats()
            self._update_charts()
        except:
            pass

    def _update_indicators(self):
        """Обновляет индикаторы фильтров - только если изменились"""
        for key, f in self.filters.items():
            if key == 'columns':
                is_all = len(f['select'].value) == len(self.all_optional_cols)
                new_html = "<span style='color:#888;font-size:11px;'>все</span>" if is_all else format_indicator(f['select'].value)
            else:
                new_html = format_indicator(f['select'].value)

            # Обновляем только если изменилось
            if f['indicator'].object != new_html:
                f['indicator'].object = new_html

    # ========== История и Undo/Redo ==========

    def _add_to_history(self, branch, dept, month, old_val, new_val):
        if self.corr_history_idx < len(self.corr_history) - 1:
            self.corr_history = self.corr_history[:self.corr_history_idx + 1]
        self.corr_history.append({'branch': branch, 'dept': dept, 'month': month, 'old_val': old_val, 'new_val': new_val})
        self.corr_history_idx = len(self.corr_history) - 1
        if len(self.corr_history) > 50:
            self.corr_history = self.corr_history[-50:]
            self.corr_history_idx = len(self.corr_history) - 1

    def _apply_history_item(self, item, use_old=True):
        """Восстанавливает корректировки и пересчитывает группу.

        При undo: восстанавливаем Корр/Дельта → redistribute → apply_elasticity
        Все отделы группы пересчитываются согласно слайдерам.
        """
        mask = (self.df['Филиал'] == item['branch']) & (self.df['Отдел'] == item['dept']) & (self.df['Месяц'] == item['month'])
        if mask.sum() == 0:
            return

        vals = item['old_val'] if use_old else item['new_val']
        idx = self.df.index[mask][0]

        # Восстанавливаем ТОЛЬКО корректировки (Корр и Корр_Дельта)
        if isinstance(vals, dict):
            corr_val = vals.get('корр')
            delta_val = vals.get('дельта')

            self.df.at[idx, 'Корр'] = corr_val if pd.notna(corr_val) else np.nan
            self.df.at[idx, 'Корр_Дельта'] = delta_val if pd.notna(delta_val) else np.nan

            # Если корректировки удалены — сбрасываем Авто_Корр
            if pd.isna(corr_val) and pd.isna(delta_val) and 'Авто_Корр' in self.df.columns:
                self.df.at[idx, 'Авто_Корр'] = np.nan
        else:
            self.df.at[idx, 'Корр'] = vals if pd.notna(vals) else np.nan
            self.df.at[idx, 'Корр_Дельта'] = np.nan

            if pd.isna(vals) and 'Авто_Корр' in self.df.columns:
                self.df.at[idx, 'Авто_Корр'] = np.nan

        # Пересчитываем план этой строки
        self._recalc_plan(mask)

        # Перераспределяем всю группу (филиал+месяц)
        self._redistribute_group(item['branch'], item['month'])


    def _undo_correction(self, event=None):
        if self.corr_history_idx < 0:
            return
        self._apply_history_item(self.corr_history[self.corr_history_idx], use_old=True)
        self.corr_history_idx -= 1
        self._cached_filtered_df = None
        # Применяем слайдеры — пересчитываем все группы согласно текущим K↑/K↓
        self._apply_elasticity()
        self._after_correction_change()
        self.status.object = "↩️ Отмена"

    def _redo_correction(self, event=None):
        if self.corr_history_idx >= len(self.corr_history) - 1:
            return
        self.corr_history_idx += 1
        self._apply_history_item(self.corr_history[self.corr_history_idx], use_old=False)
        self._cached_filtered_df = None
        # Применяем слайдеры — пересчитываем все группы согласно текущим K↑/K↓
        self._apply_elasticity()
        self._after_correction_change()
        self.status.object = "↪️ Повтор"

    def _after_correction_change(self):
        # Сбрасываем кэши СРАЗУ
        self._cached_filtered_df = None
        self._cached_agg = None

        # НЕ вызываем _apply_special_rules здесь!
        # Это приводит к перезаписи ручных корректировок.
        # Специальные правила применяются только при изменении декабрьской корректировки.

        # Быстрые операции - сразу
        self._update_seasonality_plan()
        self._calc_recommendation()

        # Обновляем таблицу и статистику
        self._updating_table = True
        self.table.value = self._get_display_df()
        self._last_table_df = self.table.value.copy() if self.table.value is not None else None
        self._updating_table = False

        self._update_stats()
        self._update_compact_stats()

        # Графики - ПОВТОРНО сбрасываем кэш перед обновлением
        self._cached_filtered_df = None
        self._cached_agg = None
        self._update_charts()

        # Сохранение - в конце
        self._save_pending = True
        self._do_save()

    def _apply_special_rules(self):
        """Применяет специальные правила расчёта для Дверей и Мебели для кухни"""
        # Проверяем есть ли корректировки на декабрь для этих отделов
        if 'Корр' not in self.df.columns:
            return

        # Двери
        doors_dec_corr = (
            (self.df['Отдел'] == '9. Двери, фурнитура дверная') &
            (self.df['Месяц'] == 12) &
            (self.df['Корр'].notna())
        )
        if doors_dec_corr.any():
            self._apply_doors_smooth_growth()

        # Мебель для кухни
        kitchen_dec_corr = (
            (self.df['Отдел'] == 'Мебель для кухни') &
            (self.df['Месяц'] == 12) &
            (self.df['Корр'].notna())
        )
        if kitchen_dec_corr.any():
            self._apply_kitchen_smooth_growth()

    # ========== Расчёт плана ==========

    def _recalc_row(self, mask):
        recalc_row_metrics(self.df, mask, self.cols_available)

    def _recalc_plan(self, mask):
        corr = self.df.loc[mask, 'Корр'].values[0]
        delta = self.df.loc[mask, 'Корр_Дельта'].values[0]
        base = self.df.loc[mask, '_План_Расч_Исх'].values[0]

        # Корр = 0 означает план = 0 (явное обнуление)
        # Корр > 0 означает план = Корр + дельта
        # Корр = NaN означает план = base + дельта
        if pd.notna(corr):
            if corr == 0:
                final = 0  # Явное обнуление
            else:
                final = corr + (delta if pd.notna(delta) else 0)
        else:
            final = base + (delta if pd.notna(delta) else 0)

        final = max(0, final)
        self.df.loc[mask, 'План_Скорр'] = final
        self.df.loc[mask, 'План_Расч'] = final

        # ВАЖНО: Обновляем df_original чтобы эластичность не перезаписала
        # (только если df_original уже создан)
        if hasattr(self, 'df_original') and self.df_original is not None:
            self.df_original.loc[mask, 'План_Скорр'] = final
            self.df_original.loc[mask, 'План_Расч'] = final

        self._recalc_row(mask)

    def _redistribute_group(self, branch, month):
        """Перераспределяет план для группы (филиал, месяц) - оптимизированно"""
        gm = (self.df['Филиал'] == branch) & (self.df['Месяц'] == month)
        if gm.sum() == 0:
            return

        target = int(round(self.df.loc[gm, 'План'].iloc[0]))
        corr_mask = has_correction(self.df, gm)

        # DEBUG: Показываем какие отделы имеют корректировки
        corrected_depts = self.df.loc[gm & corr_mask, 'Отдел'].tolist() if corr_mask.any() else []
        if corrected_depts:
            print(f"   📌 {branch}/{month}: фиксированные отделы ({len(corrected_depts)}): {corrected_depts[:3]}...")

        group_df = self.df.loc[gm].copy().reset_index(drop=True)
        fixed_mask_local = corr_mask[gm].reset_index(drop=True)

        result = distribute_plan_for_group(group_df, target, fixed_mask=fixed_mask_local)

        # Применяем результат векторно
        result_values = result['План_Расч'].values
        active_idx = self.df[gm].index[~corr_mask[self.df[gm].index]]

        if len(active_idx) > 0:
            active_positions = [list(self.df[gm].index).index(idx) for idx in active_idx]
            active_values = [result_values[i] for i in active_positions]

            self.df.loc[active_idx, 'План_Скорр'] = active_values
            self.df.loc[active_idx, 'План_Расч'] = active_values
            self.df.loc[active_idx, 'Рекоменд'] = active_values  # ВАЖНО: обновляем и Рекоменд!
            # ВАЖНО: обновляем df_original чтобы _apply_elasticity не перезаписала!
            if hasattr(self, 'df_original') and self.df_original is not None:
                self.df_original.loc[active_idx, 'План_Скорр'] = active_values
                self.df_original.loc[active_idx, 'План_Расч'] = active_values
                self.df_original.loc[active_idx, 'Рекоменд'] = active_values

        # Пересчитываем метрики для ВСЕЙ группы (чтобы обновить Прирост_%)
        recalc_row_metrics(self.df, gm, self.cols_available)


    # ========== Таблица ==========

    def _setup_table(self):
        formatters = get_table_formatters()
        editors = {
            'Корр': {'type': 'number', 'step': 10000, 'min': 0},
            'Корр_Дельта': {'type': 'number', 'step': 10000}
        }

        readonly_cols = ['Филиал', 'Отдел', 'Месяц', 'План_Скорр', 'Рекоменд', 'Выручка_2025', 'Выручка_2024',
                        'Выручка_2025_Норм', 'Прирост_%', 'Прирост_24_26_%', 'Сезонность_Факт', 'Сезонность_План', 'Площадь_2025',
                        'Площадь_2026', 'Δ_Площадь_%', 'Отдача_План', 'Отдача_2025', 'Δ_Отдача_%',
                        'Формат', 'Роль', 'Правило',
                        'План', 'План_Расч', '_План_Расч_Исх', 'Авто_Корр', 'Final_Weight', 'is_network_format']
        for c in readonly_cols:
            editors[c] = None

        titles = {
            'План_Скорр': 'План 2026', 'Рекоменд': 'Рекоменд', 'Корр_Дельта': '✏️ +/-', 'Корр': '✏️ Корр',
            'Выручка_2025': 'Выр.2025', 'Выручка_2024': 'Выр.2024', 'Выручка_2025_Норм': 'Выр.25(Н)',
            'Прирост_%': 'Δ% к 2025', 'Прирост_24_26_%': 'Δ% к 2024',
            'Сезонность_Факт': 'Сез.Факт', 'Сезонность_План': 'Сез.План',
            # Новые колонки
            'План': 'Цель', 'План_Расч': 'План_Расч', '_План_Расч_Исх': 'Исх.План',
            'Авто_Корр': 'Авто', 'Final_Weight': 'Вес', 'is_network_format': 'Сеть'
        }

        self.table = pn.widgets.Tabulator(
            self._get_display_df(), formatters=formatters, editors=editors, titles=titles,
            pagination=None, height=600, sizing_mode='stretch_width', show_index=False,
            frozen_columns=['Филиал', 'Отдел', 'Месяц'], widths={'Филиал': 140, 'Отдел': 160, 'Месяц': 55},
            theme='simple', header_filters=False
        )
        self.table.on_edit(self._on_edit)

        # Дополнительный watcher для отслеживания удалений (Tabulator не всегда вызывает on_edit при очистке)
        self._last_table_df = self.table.value.copy() if self.table.value is not None else None
        self.table.param.watch(self._on_table_value_change, 'value')

    def _get_filtered_df(self):
        """Возвращает отфильтрованный DF (Robust Version)"""
        # CACHE DISABLED FOR DEBUG
        # if hasattr(self, '_cached_filtered_df') and self._cached_filtered_df is not None:
        #     return self._cached_filtered_df

        df = self.df
        mask = np.ones(len(df), dtype=bool)

        filter_map = {
            'branch': 'Филиал',
            'dept': 'Отдел',
            'format': 'Формат',
            'role': 'Роль',
            'rule': 'Правило',
        }

        print(f"\n🔍 FILTER CHECK (DF Rows: {len(df)})")

        for key, col in filter_map.items():
            if key not in self.filters: continue

            # Получаем значения и приводим к строке для надежности
            vals = self.filters[key]['select'].value

            if vals and col in df.columns:
                # Normalize values: string and strip
                vals_clean = [str(v).strip() for v in vals]

                # Normalize DF column for comparison
                # We use astype(str) to be safe
                col_values_clean = df[col].astype(str).str.strip()

                matches = col_values_clean.isin(vals_clean)
                n_match = matches.sum()

                print(f"   Filter '{key}': selected {len(vals_clean)} -> matches {n_match}")
                if n_match == 0 and len(vals_clean) > 0:
                     print(f"   ⚠️ MISMATCH! Selected example: '{vals_clean[0]}', DF example: '{col_values_clean.iloc[0] if len(df)>0 else 'empty'}'")

                mask &= matches.values

        month_vals = self.filters['month']['select'].value
        if month_vals:
            # Months are tricky (int vs str)
            # Try to match both names and integers
            month_nums = set()
            for m in month_vals:
                month_nums.add(MONTH_MAP.get(m, m)) # Name -> Int
                try:
                    month_nums.add(int(m)) # String int -> Int
                except: pass

            mask &= df['Месяц'].isin(list(month_nums))

        if getattr(self, 'show_only_corrections', False):
            mask &= has_correction(df).values

        self._cached_filtered_df = df.loc[mask]
        return self._cached_filtered_df

    def _get_display_df(self):
        df = self._get_filtered_df()

        base_cols = ['Филиал', 'Отдел', 'Месяц', 'Корр_Дельта', 'Корр', 'Рекоменд', 'План_Скорр']
        opt_cols = [c for c in self.all_optional_cols if c in self.filters['columns']['select'].value]
        cols = [c for c in base_cols + opt_cols if c in df.columns]
        # Возвращаем срез без копирования, fillna только для отображения
        result = df[cols]
        # fillna делаем только если есть NaN (проверка быстрее чем fillna)
        if result['Корр'].isna().any() or result['Корр_Дельта'].isna().any():
            result = result.fillna({'Корр': '', 'Корр_Дельта': ''})
        return result

    def _get_csv_data(self):
        """Генерирует CSV из текущих отфильтрованных данных для скачивания"""
        import io
        from datetime import datetime

        df = self._get_filtered_df()

        # Выбираем колонки для экспорта
        export_cols = ['Филиал', 'Отдел', 'Месяц', 'План_Скорр', 'Рекоменд', 'Корр', 'Корр_Дельта']

        # Добавляем дополнительные колонки если они есть
        extra_cols = ['Выручка_2025', 'Выручка_2024', 'Прирост_%', 'Формат', 'Роль', 'Правило']
        for col in extra_cols:
            if col in df.columns:
                export_cols.append(col)

        # Фильтруем только существующие колонки
        export_cols = [c for c in export_cols if c in df.columns]

        export_df = df[export_cols].copy()

        # Заменяем NaN на пустые строки для Корр и Корр_Дельта
        if 'Корр' in export_df.columns:
            export_df['Корр'] = export_df['Корр'].fillna('')
        if 'Корр_Дельта' in export_df.columns:
            export_df['Корр_Дельта'] = export_df['Корр_Дельта'].fillna('')

        # Генерируем CSV в память
        buffer = io.StringIO()
        export_df.to_csv(buffer, index=False, encoding='utf-8-sig')  # utf-8-sig для корректного отображения в Excel
        buffer.seek(0)

        # Обновляем имя файла с датой
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        self.export_btn.filename = f'plan_export_{timestamp}.csv'

        print(f"📥 Экспорт CSV: {len(export_df)} строк, {len(export_cols)} колонок")

        return buffer

    def _update(self, event=None):
        if not self._updating:
            self._do_update()

    # ========== Статистика и Графики ==========

    def _update_stats(self):
        df = self._get_filtered_df()
        if df.empty:
            self.stats.object = "<div style='color:#888;'>Нет данных</div>"
            return

        sel_br, sel_mo = df['Филиал'].unique(), df['Месяц'].unique()
        conv = self.df[(self.df['Филиал'].isin(sel_br)) & (self.df['Месяц'].isin(sel_mo))]

        total = int(conv['План_Скорр'].sum())
        target = int(round(conv.drop_duplicates(['Филиал', 'Месяц'])['План'].sum())) if 'План' in conv.columns else 0
        diff = total - target

        rev25 = df['Выручка_2025'].sum()
        rev24 = df['Выручка_2024'].sum() if 'Выручка_2024' in df.columns else 0
        plan_sum = int(df['План_Скорр'].sum())

        g25 = ((plan_sum/rev25-1)*100) if rev25 else 0
        g24 = ((plan_sum/rev24-1)*100) if rev24 else 0

        diff_color = COLORS['positive'] if diff == 0 else COLORS['negative']
        g25_color = COLORS['positive'] if g25 > 0 else COLORS['negative']
        g24_color = COLORS['positive'] if g24 > 0 else COLORS['negative']

        self.stats.object = f"""<div style='display:flex;gap:15px;font-size:10px;align-items:center;'>
            <b>📊 План:</b> {total:,} | <b>Цель:</b> {target:,} |
            <b>Δ:</b> <span style='color:{diff_color};font-weight:bold;'>{diff:+,}</span> |
            <b>Δ к 2025:</b> <span style='color:{g25_color};'>{g25:+.0f}%</span> |
            <b>Δ к 2024:</b> <span style='color:{g24_color};'>{g24:+.0f}%</span> |
            {len(sel_br)} фил. × {len(sel_mo)} мес.
        </div>"""
        self._update_compact_stats()

    def _update_charts(self):
        """Обновление графиков - оптимизированно"""
        try:
            # Получаем агрегаты один раз (кэшируются)
            agg = self._get_cached_agg()
            if not agg:
                return

            # Обновляем все графики напрямую
            self._update_chart_main()
            self._update_pivot_table()
            self._update_chart_branches()
            self._update_chart_seasonality()

            # Принудительное обновление ВСЕХ pane (для bokeh)
            for pane_name in ['chart_pane', 'chart_branches_pane', 'chart_seasonality_pane', 'pivot_pane']:
                if hasattr(self, pane_name):
                    pane = getattr(self, pane_name)
                    if pane and hasattr(pane, 'param'):
                        pane.param.trigger('object')

        except Exception as e:
            print(f"❌ _update_charts ошибка: {e}")
            import traceback
            traceback.print_exc()

    def _update_pivot_table(self):
        """Сводная таблица: отделы × месяцы с приростами в %"""
        if not hasattr(self, 'pivot_pane'):
            return

        agg = self._get_cached_agg()
        if not agg or 'by_dept_role_month' not in agg:
            self.pivot_pane.object = "<div style='color:#888;font-size:10px;'>Нет данных</div>"
            return

        pivot_data = agg['by_dept_role_month']
        if len(pivot_data) == 0:
            self.pivot_pane.object = "<div style='color:#888;font-size:10px;'>Нет данных</div>"
            return

        # Вычисляем прирост
        pivot_data = pivot_data.copy()
        mask = pivot_data['Выручка_2025'] > 0
        pivot_data['Прирост_%'] = np.where(mask,
            ((pivot_data['План_Скорр'] / pivot_data['Выручка_2025'] - 1) * 100).round(0), 0)

        month_order = [m for m in range(1, 13) if m in pivot_data['Месяц'].unique()]
        month_names = [MONTH_MAP_REV.get(m, str(m)) for m in month_order]
        n_months = len(month_order)

        # Заголовок - компактный с фиксированной шириной для отдела
        header_cells = ''.join(f'<th style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:#f5f5f5;font-size:9px;">{m}</th>' for m in month_names)
        header = f'''<thead style="position:sticky;top:0;background:#f5f5f5;z-index:1;"><tr>
            <th style="border:1px solid #ccc;padding:1px 2px;text-align:left;background:#f5f5f5;font-size:9px;max-width:120px;">Отдел</th>
            {header_cells}
            <th style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:#e0e0e0;font-size:9px;">Σ</th>
        </tr></thead>'''

        rows = []

        for role in ['Стратегический', 'Сопутствующий']:
            role_data = pivot_data[pivot_data['Роль'] == role]
            if role_data.empty:
                continue

            # Pivot
            pivot = role_data.pivot(index='Отдел', columns='Месяц', values='Прирост_%').fillna(0)
            pivot_plan = role_data.pivot(index='Отдел', columns='Месяц', values='План_Скорр').fillna(0)
            pivot_fact = role_data.pivot(index='Отдел', columns='Месяц', values='Выручка_2025').fillna(0)

            # Итого по строке
            row_plan = pivot_plan.sum(axis=1)
            row_fact = pivot_fact.sum(axis=1)
            pivot['Σ'] = np.where(row_fact > 0, ((row_plan / row_fact - 1) * 100).round(0), 0)

            # Строки отделов - с обрезанием текста
            for dept in sorted(pivot.index):
                cells = [f'<td style="border:1px solid #ccc;padding:1px 2px;font-size:9px;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{dept}">{dept}</td>']

                for m in month_order:
                    val = pivot.loc[dept, m] if m in pivot.columns else 0
                    bg, text = get_cell_style(val)
                    cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')

                val = pivot.loc[dept, 'Σ']
                bg, text = get_cell_style(val)
                cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-weight:bold;font-size:9px;">{text}</td>')
                rows.append(f'<tr>{"".join(cells)}</tr>')

            # Итог по роли
            role_label = '📌 Стратег.' if role == 'Стратегический' else '📎 Сопутств.'
            role_cells = [f'<td style="border:1px solid #ccc;padding:1px 2px;font-size:9px;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{role_label}</td>']

            for m in month_order:
                m_plan = pivot_plan[m].sum() if m in pivot_plan.columns else 0
                m_fact = pivot_fact[m].sum() if m in pivot_fact.columns else 0
                val = int(((m_plan / m_fact - 1) * 100)) if m_fact > 0 else 0
                bg, text = get_cell_style(val)
                role_cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')

            role_total = int(((pivot_plan.sum().sum() / pivot_fact.sum().sum() - 1) * 100)) if pivot_fact.sum().sum() > 0 else 0
            bg, text = get_cell_style(role_total)
            role_cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')
            rows.append(f'<tr style="background:#e8e8e8;font-weight:bold;">{"".join(role_cells)}</tr>')

        # Общий итог
        total_cells = ['<td style="border:1px solid #ccc;padding:1px 2px;font-size:9px;max-width:120px;">ИТОГО</td>']
        for m in month_order:
            m_data = pivot_data[pivot_data['Месяц'] == m]
            m_plan, m_fact = m_data['План_Скорр'].sum(), m_data['Выручка_2025'].sum()
            val = int(((m_plan / m_fact - 1) * 100)) if m_fact > 0 else 0
            bg, text = get_cell_style(val)
            total_cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')

        total_pct = int(((pivot_data['План_Скорр'].sum() / pivot_data['Выручка_2025'].sum() - 1) * 100)) if pivot_data['Выручка_2025'].sum() > 0 else 0
        bg, text = get_cell_style(total_pct)
        total_cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')
        rows.append(f'<tr style="background:#d0d0d0;font-weight:bold;">{"".join(total_cells)}</tr>')

        self.pivot_pane.object = f'<div style="max-height:175px;overflow-y:auto;"><table style="border-collapse:collapse;font-size:9px;width:100%;table-layout:fixed;">{header}<tbody>{"".join(rows)}</tbody></table></div>'
        # Принудительно триггерим обновление
        self.pivot_pane.param.trigger('object')

    def _update_chart_main(self):
        try:
            agg = self._get_cached_agg()
            if not agg or 'by_month' not in agg:
                self.chart_pane.object = None
                return

            m = agg['by_month'].sort_values('Месяц')
            if len(m) == 0:
                self.chart_pane.object = None
                return

            m['Месяц_текст'] = m['Месяц'].map(MONTH_MAP_REV)

            # Δ% План к 2025
            m['Δ%_план'] = 0.0
            mask25 = m['Выручка_2025'] > 0
            m.loc[mask25, 'Δ%_план'] = ((m.loc[mask25, 'План_Скорр'] / m.loc[mask25, 'Выручка_2025'] - 1) * 100).round(1)

            # Δ% Выручка 2025 к 2024 (факт к факту)
            m['Δ%_25_24'] = 0.0
            if 'Выручка_2024' in m.columns:
                mask24 = m['Выручка_2024'] > 0
                m.loc[mask24, 'Δ%_25_24'] = ((m.loc[mask24, 'Выручка_2025'] / m.loc[mask24, 'Выручка_2024'] - 1) * 100).round(1)

            mt = m['Месяц_текст'].tolist()
            plan = (m['План_Скорр'].fillna(0)/1e6).tolist()
            plan_calc = (m['План_Расч'].fillna(0)/1e6).tolist() if 'План_Расч' in m.columns else plan
            r25 = (m['Выручка_2025'].fillna(0)/1e6).tolist()
            r24 = (m['Выручка_2024'].fillna(0)/1e6).tolist() if 'Выручка_2024' in m.columns else [0]*len(m)
            delta_plan = m['Δ%_план'].fillna(0).tolist()
            delta_25_24 = m['Δ%_25_24'].fillna(0).tolist()

            # Разница между планом и расчётным (для отображения)
            diff_corr = [p - c for p, c in zip(plan, plan_calc)]

            mx = max(max(plan), max(plan_calc), max(r25), max(r24)) if plan else 1
            mn = min(min(plan), min(plan_calc), min(r25), min(r24)) if plan else 0
            mn = max(0, mn * 0.9)

            p = create_bokeh_chart(mt)
            p.y_range.start = mn
            p.y_range.end = mx * 1.2

            src = ColumnDataSource(data={
                'month': mt, 'plan': plan, 'plan_calc': plan_calc,
                'rev25': r25, 'rev24': r24, 'delta_plan': delta_plan, 'delta_25_24': delta_25_24, 'diff': diff_corr
            })

            l24 = add_line_with_scatter(p, src, 'month', 'rev24', COLORS['muted'], line_width=1.5, scatter_size=4)
            l25 = add_line_with_scatter(p, src, 'month', 'rev25', COLORS['primary'])

            # Расчётный план - пунктирная линия
            l_calc = p.line('month', 'plan_calc', source=src, line_width=2,
                           line_color='#9E9E9E', line_dash='dashed', line_alpha=0.8)
            p.scatter('month', 'plan_calc', source=src, size=5,
                     fill_color='#9E9E9E', line_color='#9E9E9E', fill_alpha=0.6)

            # Финальный план - основная линия
            l26 = add_line_with_scatter(p, src, 'month', 'plan', COLORS['secondary'], line_width=2.5, scatter_size=6)

            hover_circles = p.circle('month', 'plan', source=src, size=15, fill_alpha=0, line_alpha=0)

            # Дельта плана к 2025 — над точками плана
            for t, v, d in zip(mt, plan, delta_plan):
                color = COLORS['negative'] if d < 0 else COLORS['positive']
                p.text(x=[t], y=[v+mx*0.05], text=[f"{d:+.0f}%"], text_font_size='10px',
                       text_color=color, text_align='center', text_font_style='bold')

            # Дельта 2025 к 2024 — над точками факта 2025
            for t, v, d in zip(mt, r25, delta_25_24):
                color = COLORS['negative'] if d < 0 else COLORS['positive']
                p.text(x=[t], y=[v+mx*0.03], text=[f"({d:+.0f}%)"], text_font_size='8px',
                       text_color=color, text_align='center', text_font_style='normal')

            p.add_layout(Legend(items=[
                ('План 26', [l26]),
                ('Расч.', [l_calc]),
                ('Факт 25', [l25]),
                ('Факт 24', [l24])
            ], location='center', orientation='vertical', label_text_font_size='7px', spacing=0, padding=1), 'right')

            hover = HoverTool(
                tooltips=[
                    ('Месяц', '@month'),
                    ('План', '@plan{0.0f} млн'),
                    ('Расчётный', '@plan_calc{0.0f} млн'),
                    ('Корр.', '@diff{+0.0f} млн'),
                    ('2025', '@rev25{0.0f} млн'),
                    ('2024', '@rev24{0.0f} млн'),
                    ('Δ% План/25', '@delta_plan{+0.0f}%'),
                    ('Δ% 25/24', '@delta_25_24{+0.0f}%')
                ],
                renderers=[hover_circles],
                mode='vline'
            )
            p.add_tools(hover)

            self.chart_pane.object = p
        except Exception as e:
            print(f"❌ _update_chart_main ошибка: {e}")

    def _update_chart_branches(self):
        """Сводная таблица: филиалы × месяцы с приростами в %"""
        agg = self._get_cached_agg()
        if not agg or 'by_branch_month' not in agg:
            self.chart_branches_pane.object = "<div style='color:#888;font-size:10px;'>Нет данных</div>"
            return

        pivot_data = agg['by_branch_month']
        if len(pivot_data) == 0:
            self.chart_branches_pane.object = "<div style='color:#888;font-size:10px;'>Нет данных</div>"
            return

        # Вычисляем прирост
        pivot_data = pivot_data.copy()
        mask = pivot_data['Выручка_2025'] > 0
        pivot_data['Прирост_%'] = np.where(mask,
            ((pivot_data['План_Скорр'] / pivot_data['Выручка_2025'] - 1) * 100).round(0), 0)

        month_order = [m for m in range(1, 13) if m in pivot_data['Месяц'].unique()]
        month_names = [MONTH_MAP_REV.get(m, str(m)) for m in month_order]

        # Заголовок - компактный с фиксированной шириной для филиала
        header_cells = ''.join(f'<th style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:#f5f5f5;font-size:9px;">{m}</th>' for m in month_names)
        header = f'''<thead style="position:sticky;top:0;background:#f5f5f5;z-index:1;"><tr>
            <th style="border:1px solid #ccc;padding:1px 2px;text-align:left;background:#f5f5f5;font-size:9px;max-width:100px;">Филиал</th>
            {header_cells}
            <th style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:#e0e0e0;font-size:9px;">Σ</th>
        </tr></thead>'''

        # Pivot
        pivot = pivot_data.pivot(index='Филиал', columns='Месяц', values='Прирост_%').fillna(0)
        pivot_plan = pivot_data.pivot(index='Филиал', columns='Месяц', values='План_Скорр').fillna(0)
        pivot_fact = pivot_data.pivot(index='Филиал', columns='Месяц', values='Выручка_2025').fillna(0)

        # Итого по строке
        row_plan = pivot_plan.sum(axis=1)
        row_fact = pivot_fact.sum(axis=1)
        pivot['Σ'] = np.where(row_fact > 0, ((row_plan / row_fact - 1) * 100).round(0), 0)

        rows = []
        for branch in sorted(pivot.index):
            cells = [f'<td style="border:1px solid #ccc;padding:1px 2px;font-size:9px;max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{branch}">{branch}</td>']

            for m in month_order:
                val = pivot.loc[branch, m] if m in pivot.columns else 0
                bg, text = get_cell_style(val)
                cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')

            val = pivot.loc[branch, 'Σ']
            bg, text = get_cell_style(val)
            cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-weight:bold;font-size:9px;">{text}</td>')
            rows.append(f'<tr>{"".join(cells)}</tr>')

        # Итого
        total_cells = ['<td style="border:1px solid #ccc;padding:1px 2px;font-size:9px;max-width:100px;">ИТОГО</td>']
        for m in month_order:
            m_data = pivot_data[pivot_data['Месяц'] == m]
            m_plan, m_fact = m_data['План_Скорр'].sum(), m_data['Выручка_2025'].sum()
            val = int(((m_plan / m_fact - 1) * 100)) if m_fact > 0 else 0
            bg, text = get_cell_style(val)
            total_cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')

        total_pct = int(((pivot_data['План_Скорр'].sum() / pivot_data['Выручка_2025'].sum() - 1) * 100)) if pivot_data['Выручка_2025'].sum() > 0 else 0
        bg, text = get_cell_style(total_pct)
        total_cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')
        rows.append(f'<tr style="background:#d0d0d0;font-weight:bold;">{"".join(total_cells)}</tr>')

        self.chart_branches_pane.object = f'<div style="max-height:200px;overflow-y:auto;"><table style="border-collapse:collapse;font-size:9px;width:100%;table-layout:fixed;">{header}<tbody>{"".join(rows)}</tbody></table></div>'
        # Принудительно триггерим обновление
        self.chart_branches_pane.param.trigger('object')

    def _update_chart_seasonality(self):
        agg = self._get_cached_agg()
        df = self._get_filtered_df()

        if len(df) == 0:
            self.chart_seasonality_pane.object = None
            return

        p = create_bokeh_chart(MONTHS, title='Сезонность %')

        items = []
        tooltip_data = {m: {'month': m} for m in MONTHS}

        # 1. ПУНКТИРНАЯ: Сезонность ФАКТА 2025 (для сравнения)
        fact_by_month = df.groupby('Месяц')['Выручка_2025'].sum()
        total_fact = fact_by_month.sum()
        if total_fact > 0:
            sf_fact = {m: round(fact_by_month.get(m, 0) / total_fact * 100, 1) for m in range(1, 13)}
        else:
            sf_fact = {m: 0 for m in range(1, 13)}

        fd_fact = [{'month': MONTH_MAP_REV.get(m, str(m)), 'val': sf_fact.get(m, 0)} for m in range(1, 13)]
        src_fact = ColumnDataSource(data={
            'month': [d['month'] for d in fd_fact],
            'val': [d['val'] for d in fd_fact],
            'label': ['Факт 2025']*12
        })

        l_fact = add_line_with_scatter(p, src_fact, 'month', 'val', '#9E9E9E', line_width=2, scatter_size=5, line_dash='dashed')
        items.append(('Факт 2025', [l_fact]))

        for m_num in range(1, 13):
            m_txt = MONTH_MAP_REV.get(m_num, str(m_num))
            tooltip_data[m_txt]['val_fact'] = round(sf_fact.get(m_num, 0), 1)

        # 2. СПЛОШНАЯ: Сезонность ИТОГОВОГО плана (План_Скорр - после корректировок)
        plan_by_month = df.groupby('Месяц')['План_Скорр'].sum()
        total_plan = plan_by_month.sum()
        if total_plan > 0:
            sf_final = {m: round(plan_by_month.get(m, 0) / total_plan * 100, 1) for m in range(1, 13)}
        else:
            sf_final = {m: 0 for m in range(1, 13)}

        fd_final = [{'month': MONTH_MAP_REV.get(m, str(m)), 'val': sf_final.get(m, 0)} for m in range(1, 13)]
        src_final = ColumnDataSource(data={
            'month': [d['month'] for d in fd_final],
            'val': [d['val'] for d in fd_final],
            'label': ['План 2026']*12
        })

        l_final = add_line_with_scatter(p, src_final, 'month', 'val', '#2196F3', line_width=3, scatter_size=8)
        items.append(('План 2026', [l_final]))

        for m_num in range(1, 13):
            m_txt = MONTH_MAP_REV.get(m_num, str(m_num))
            tooltip_data[m_txt]['val_final'] = round(sf_final.get(m_num, 0), 1)

        # 3. Линии по филиалам (если несколько)
        branches = df['Филиал'].unique().tolist()
        colors_list = Category10[max(3, min(len(branches), 10))] if branches else []

        # Показываем филиалы только если их больше 1
        if len(branches) > 1:
            for i, branch in enumerate(branches[:6]):
                bd = df[df['Филиал'] == branch]
                mp = bd.groupby('Месяц')['План_Скорр'].sum()
                yp = mp.sum()

                pd_data = [{'month': MONTH_MAP_REV.get(m, str(m)),
                           'val': round((mp.get(m, 0)/yp*100) if yp > 0 else 0, 1)} for m in range(1, 13)]

                src_p = ColumnDataSource(data={
                    'month': [d['month'] for d in pd_data],
                    'val': [d['val'] for d in pd_data],
                    'label': [branch]*12
                })

                lp = add_line_with_scatter(p, src_p, 'month', 'val', colors_list[i % len(colors_list)], line_width=1.5, scatter_size=4)
                label = branch[:10]+'..' if len(branch) > 10 else branch
                items.append((label, [lp]))

                for d in pd_data:
                    if d['month'] in tooltip_data:
                        tooltip_data[d['month']][f'val_{i}'] = d['val']

        if len(items) > 1:
            p.add_layout(Legend(items=items[:9], location='top_right', orientation='vertical',
                               label_text_font_size='6px', spacing=0, padding=1), 'right')

        hover_data = {
            'month': MONTHS,
            'val_fact': [tooltip_data.get(m, {}).get('val_fact', 0) for m in MONTHS],
            'val_final': [tooltip_data.get(m, {}).get('val_final', 0) for m in MONTHS]
        }
        tooltip_html_parts = [
            '<b>@month</b><br>',
            '<span style="color:#9E9E9E">Факт 2025</span>: @val_fact{0.0f}%<br>',
            '<span style="color:#2196F3"><b>План 2026</b></span>: @val_final{0.0f}%<br>'
        ]

        if len(branches) > 1:
            for i, branch in enumerate(branches[:6]):
                label = branch[:10]+'..' if len(branch) > 10 else branch
                col = f'val_{i}'
                hover_data[col] = [tooltip_data.get(m, {}).get(col, 0) for m in MONTHS]
                tooltip_html_parts.append(f'<span style="color:{colors_list[i % len(colors_list)]}">{label}</span>: @{col}{{0.0f}}%<br>')

        hover_src = ColumnDataSource(data=hover_data)
        hover_circles = p.circle('month', 'val_final', source=hover_src, size=20, fill_alpha=0, line_alpha=0)

        tooltip_html = ''.join(tooltip_html_parts)
        hover = HoverTool(tooltips=tooltip_html, renderers=[hover_circles], mode='vline')
        p.add_tools(hover)

        self.chart_seasonality_pane.object = p

    # ========== Обработка редактирования ==========

    def _on_table_value_change(self, event):
        """Обработчик изменения значения таблицы - ловит удаления корректировок"""
        if getattr(self, '_updating_table', False):
            return
        if getattr(self, '_processing_deletion', False):
            return

        old_df = getattr(self, '_last_table_df', None)
        new_df = event.new

        if old_df is None or new_df is None:
            self._last_table_df = new_df.copy() if new_df is not None else None
            return

        if len(old_df) != len(new_df):
            self._last_table_df = new_df.copy() if new_df is not None else None
            return

        # Ищем изменения в колонках Корр и Корр_Дельта
        try:
            for col in ['Корр', 'Корр_Дельта']:
                if col not in old_df.columns or col not in new_df.columns:
                    continue

                for idx in range(len(old_df)):
                    old_val = old_df.iloc[idx].get(col)
                    new_val = new_df.iloc[idx].get(col)

                    # Проверяем удаление (было значение, стало пусто/NaN/0)
                    def is_empty(v):
                        if pd.isna(v):
                            return True
                        if v is None:
                            return True
                        s = str(v).strip().lower()
                        return s in ['', 'nan', 'none', 'null']

                    def is_set(v):
                        if is_empty(v):
                            return False
                        try:
                            return float(v) >= 0  # Любое число >= 0 считается установленным
                        except:
                            return False

                    old_is_set = is_set(old_val)
                    new_is_empty = is_empty(new_val)

                    if old_is_set and new_is_empty:
                        # Удаление корректировки!
                        row = new_df.iloc[idx]
                        branch = row.get('Филиал')
                        dept = row.get('Отдел')
                        month = row.get('Месяц')

                        print(f"\n{'='*60}")
                        print(f"🗑️ УДАЛЕНИЕ через param.watch: {branch}/{dept}/{month}")
                        print(f"   {col}: {old_val} → пусто")

                        # Находим строку в основном df
                        mask = (self.df['Филиал'] == branch) & (self.df['Отдел'] == dept) & (self.df['Месяц'] == month)
                        if mask.any():
                            self._processing_deletion = True
                            try:
                                idx_df = self.df.index[mask][0]
                                old_plan = self.df.at[idx_df, 'План_Скорр']

                                # Сбрасываем корректировку
                                if col == 'Корр':
                                    self.df.at[idx_df, 'Корр'] = np.nan
                                    self.df_original.at[idx_df, 'Корр'] = np.nan
                                    self.df.at[idx_df, 'Корр_Дельта'] = np.nan
                                    self.df_original.at[idx_df, 'Корр_Дельта'] = np.nan
                                    if 'Авто_Корр' in self.df.columns:
                                        self.df.at[idx_df, 'Авто_Корр'] = np.nan
                                        self.df_original.at[idx_df, 'Авто_Корр'] = np.nan
                                else:
                                    self.df.at[idx_df, 'Корр_Дельта'] = np.nan
                                    self.df_original.at[idx_df, 'Корр_Дельта'] = np.nan

                                # Перераспределяем план для группы
                                self._redistribute_group(branch, month)

                                # ВАЖНО: Применяем специальные правила (Двери, Мебель для кухни)
                                self._apply_special_rules()

                                # Обновляем df_original для всей группы
                                group_mask = (self.df['Филиал'] == branch) & (self.df['Месяц'] == month)
                                for c in ['План_Скорр', 'План_Расч', 'Рекоменд', 'Корр', 'Корр_Дельта', 'Авто_Корр']:
                                    if c in self.df.columns:
                                        self.df_original.loc[group_mask, c] = self.df.loc[group_mask, c].values

                                new_plan = self.df.at[idx_df, 'План_Скорр']
                                print(f"   План: {old_plan:,.0f} → {new_plan:,.0f}")

                                # Обновляем UI
                                self._cached_filtered_df = None
                                self._cached_agg = None

                                # Обновляем таблицу
                                self._updating_table = True
                                self.table.value = self._get_display_df()
                                self._updating_table = False

                                self._update_stats()
                                self._update_compact_stats()
                                self._update_charts()

                                # Сохраняем
                                self._save_pending = True
                                self._do_save()

                                print(f"   ✅ Готово")
                            finally:
                                self._processing_deletion = False

                        # Обрабатываем только первое изменение
                        self._last_table_df = self.table.value.copy() if self.table.value is not None else None
                        return
        except Exception as e:
            print(f"⚠️ Ошибка в _on_table_value_change: {e}")
            import traceback
            traceback.print_exc()

        self._last_table_df = new_df.copy() if new_df is not None else None

    def _on_edit(self, e):
        if e.column not in ['Корр', 'Корр_Дельта']:
            return

        try:
            fd = self.table.value
            if e.row >= len(fd):
                return

            rd = fd.iloc[e.row]
            branch, dept, month = rd['Филиал'], rd['Отдел'], rd['Месяц']

            mask = (self.df['Филиал'] == branch) & (self.df['Отдел'] == dept) & (self.df['Месяц'] == month)
            if mask.sum() == 0:
                return

            idx = self.df.index[mask][0]

            old_c = self.df.at[idx, 'Корр']
            old_d = self.df.at[idx, 'Корр_Дельта']
            current_plan = self.df.at[idx, 'План_Скорр']

            # Детальный debug
            print(f"\n{'='*60}")
            print(f"📝 EDIT EVENT:")
            print(f"   e.value = '{e.value}' (type={type(e.value).__name__})")
            print(f"   e.column = '{e.column}'")
            print(f"   Ячейка в таблице: rd['{e.column}'] = '{rd.get(e.column, 'N/A')}'")
            print(f"   Текущее в df: Корр={old_c}, Корр_Дельта={old_d}")

            # Проверяем - если e.value это старое значение, значит пользователь хочет удалить
            cell_value = rd.get(e.column, '')
            if e.value == cell_value and cell_value != '':
                print(f"   ⚠️ e.value == cell_value, возможно Tabulator вернул старое значение")

            nv = parse_number(e.value, round_to=CONFIG['rounding_step'])

            print(f"   parsed = {nv}")

            if e.column == 'Корр':
                # Корр = 0 допустимо (план будет 0)
                # Корр = -1 — УДАЛЕНИЕ корректировки (специальное значение)
                # Корр = NaN/пусто — тоже удаление (но Tabulator может не вызвать on_edit)
                if nv is not None:
                    if nv == -1:
                        # Специальное значение для удаления
                        new_corr = np.nan
                        print(f"   🗑️ Удаление через -1")
                    elif nv >= 0:
                        new_corr = nv
                    else:
                        new_corr = np.nan
                else:
                    new_corr = np.nan

                print(f"   old_corr={old_c}, new_corr={new_corr}")

                old_plan = self.df.at[idx, 'План_Скорр']
                old_auto = self.df.at[idx, 'Авто_Корр'] if 'Авто_Корр' in self.df.columns else None
                base = self.df.at[idx, '_План_Расч_Исх']

                self.df.at[idx, 'Корр'] = new_corr

                # ВАЖНО: Сразу обновляем df_original чтобы следующее редактирование не затёрло
                self.df_original.at[idx, 'Корр'] = new_corr

                print(f"   ЗАПИСАНО: df.Корр={self.df.at[idx, 'Корр']}, df_original.Корр={self.df_original.at[idx, 'Корр']}")

                # Если корректировка удалена — сбрасываем Авто_Корр, Корр_Дельта
                # План будет пересчитан в _redistribute_group
                if pd.isna(new_corr):
                    if 'Авто_Корр' in self.df.columns:
                        self.df.at[idx, 'Авто_Корр'] = np.nan
                        self.df_original.at[idx, 'Авто_Корр'] = np.nan
                    self.df.at[idx, 'Корр_Дельта'] = np.nan
                    self.df_original.at[idx, 'Корр_Дельта'] = np.nan

                    # НЕ устанавливаем план здесь — он будет пересчитан в _redistribute_group
                    # по весам, как для обычного отдела без корректировки
                    print(f"   УДАЛЕНИЕ: Корр и Авто_Корр сброшены, план будет пересчитан")

                # Вызываем _recalc_plan только если НЕ удаление (для удаления — redistribute сделает всё)
                if pd.notna(new_corr):
                    self._recalc_plan(mask)
            else:
                new_delta = nv if nv and nv != 0 else np.nan
                self.df.at[idx, 'Корр_Дельта'] = new_delta

                # ВАЖНО: Сразу обновляем df_original
                self.df_original.at[idx, 'Корр_Дельта'] = new_delta

                corr = self.df.at[idx, 'Корр']

                if nv and nv != 0:
                    new_plan = current_plan + nv
                    self.df.at[idx, 'План_Скорр'] = max(0, new_plan)
                else:
                    base = self.df.at[idx, '_План_Расч_Исх']
                    # Корр = 0 означает план = 0
                    if pd.notna(corr):
                        self.df.at[idx, 'План_Скорр'] = corr
                    else:
                        self.df.at[idx, 'План_Скорр'] = base

                    # Если обе корректировки удалены — сбрасываем Авто_Корр
                    if pd.isna(corr) and pd.isna(new_delta) and 'Авто_Корр' in self.df.columns:
                        self.df.at[idx, 'Авто_Корр'] = np.nan

                self._recalc_row(mask)

            self._redistribute_group(branch, month)

            # ВАЖНО: Обновляем df_original для ВСЕЙ группы после redistribute
            # чтобы _apply_elasticity не затёр новые значения
            group_mask = (self.df['Филиал'] == branch) & (self.df['Месяц'] == month)
            for col in ['План_Скорр', 'План_Расч', 'Корр', 'Корр_Дельта', 'Авто_Корр']:
                if col in self.df.columns:
                    self.df_original.loc[group_mask, col] = self.df.loc[group_mask, col].values

            print(f"   ПОСЛЕ redistribute: df.Корр={self.df.at[idx, 'Корр']}, План={self.df.at[idx, 'План_Скорр']}")

            # Записываем в историю ПОСЛЕ redistribute — чтобы план был финальным
            self._add_to_history(
                branch, dept, month,
                {'корр': old_c, 'дельта': old_d, 'план': current_plan},
                {'корр': self.df.at[idx, 'Корр'], 'дельта': self.df.at[idx, 'Корр_Дельта'], 'план': self.df.at[idx, 'План_Скорр']}
            )

            # Если это отдел Дверей
            DOORS_DEPT = '9. Двери, фурнитура дверная'
            if dept == DOORS_DEPT:
                if month == 12:
                    # Изменение декабрьской цели — пересчитываем весь плавный рост
                    doors_mask = (self.df['Филиал'] == branch) & (self.df['Отдел'] == DOORS_DEPT)
                    if 'Авто_Корр' in self.df.columns:
                        # Сбрасываем Авто_Корр для всех месяцев БЕЗ ручной корректировки
                        no_manual = doors_mask & self.df['Корр'].isna() & self.df['Корр_Дельта'].isna()
                        self.df.loc[no_manual, 'Авто_Корр'] = np.nan
                    # Пересчитываем плавный рост
                    self._apply_doors_smooth_growth()
                else:
                    # Ручная корректировка для другого месяца — сбрасываем Авто_Корр для этой строки
                    # чтобы ручная корректировка имела приоритет
                    if 'Авто_Корр' in self.df.columns:
                        self.df.at[idx, 'Авто_Корр'] = np.nan

            # Если это отдел Кухни
            KITCHEN_DEPT = 'Мебель для кухни'
            if dept == KITCHEN_DEPT:
                if month == 12:
                    # Изменение декабрьской цели — пересчитываем весь плавный рост
                    kitchen_mask = (self.df['Филиал'] == branch) & (self.df['Отдел'] == KITCHEN_DEPT)
                    if 'Авто_Корр' in self.df.columns:
                        # Сбрасываем Авто_Корр для всех месяцев БЕЗ ручной корректировки
                        no_manual = kitchen_mask & self.df['Корр'].isna() & self.df['Корр_Дельта'].isna()
                        self.df.loc[no_manual, 'Авто_Корр'] = np.nan

                    # Пересчитываем плавный рост и получаем затронутые группы
                    affected = plan_calculator.apply_kitchen_smooth_growth(self.df, verbose=False)

                    # ПРИНУДИТЕЛЬНО пересчитываем затронутые месяцы
                    if affected:
                        for b, m in affected:
                            # Пропускаем текущий месяц (12), так как он уже обработан выше
                            if b == branch and m == month:
                                continue
                            self._redistribute_group(b, m)

                            # Синхронизируем с df_original
                            gm = (self.df['Филиал'] == b) & (self.df['Месяц'] == m)
                            if hasattr(self, 'df_original'):
                                for col in ['План_Скорр', 'План_Расч', 'Авто_Корр']:
                                    if col in self.df.columns:
                                        self.df_original.loc[gm, col] = self.df.loc[gm, col].values

                else:
                    # Ручная корректировка для другого месяца — сбрасываем Авто_Корр для этой строки
                    if 'Авто_Корр' in self.df.columns:
                        self.df.at[idx, 'Авто_Корр'] = np.nan

            # Добавляем также пересчет для Дверей (исправление существующего блока)
            if dept == DOORS_DEPT and month == 12:
                affected = plan_calculator.apply_doors_smooth_growth(self.df, verbose=False)
                if affected:
                    for b, m in affected:
                        if b == branch and m == month:
                            continue
                        self._redistribute_group(b, m)
                        gm = (self.df['Филиал'] == b) & (self.df['Месяц'] == m)
                        if hasattr(self, 'df_original'):
                            for col in ['План_Скорр', 'План_Расч', 'Авто_Корр']:
                                if col in self.df.columns:
                                    self.df_original.loc[gm, col] = self.df.loc[gm, col].values

            # Если это отдел Мебель для кухни
            KITCHEN_DEPT = 'Мебель для кухни'
            if dept == KITCHEN_DEPT:
                if month == 12:
                    # Изменение декабрьской цели — пересчитываем весь плавный рост
                    kitchen_mask = (self.df['Филиал'] == branch) & (self.df['Отдел'] == KITCHEN_DEPT)
                    if 'Авто_Корр' in self.df.columns:
                        no_manual = kitchen_mask & self.df['Корр'].isna() & self.df['Корр_Дельта'].isna()
                        self.df.loc[no_manual, 'Авто_Корр'] = np.nan
                    self._apply_kitchen_smooth_growth()
                else:
                    # Ручная корректировка для другого месяца — сбрасываем Авто_Корр для этой строки
                    # чтобы ручная корректировка имела приоритет
                    if 'Авто_Корр' in self.df.columns:
                        self.df.at[idx, 'Авто_Корр'] = np.nan
                        if hasattr(self, 'df_original') and self.df_original is not None:
                            self.df_original.at[idx, 'Авто_Корр'] = np.nan
                    print(f"   ✅ Ручная корректировка Мебель для кухни/{month}: Авто_Корр сброшен")

            self._cached_filtered_df = None

            # НЕ вызываем _apply_elasticity автоматически после редактирования!
            # Это приводит к сбросу введённых значений.
            # Эластичность применяется только при изменении слайдеров K.

            # Отменяем предыдущий таймер если есть
            if hasattr(self, '_edit_elasticity_timer') and self._edit_elasticity_timer is not None:
                try:
                    self._edit_elasticity_timer.cancel()
                except:
                    pass
                self._edit_elasticity_timer = None

            print(f"   ПЕРЕД _after_correction_change: df.Корр={self.df.at[idx, 'Корр']}, План={self.df.at[idx, 'План_Скорр']}")

            self._after_correction_change()

            # При удалении - дополнительно перезагружаем таблицу
            if is_deletion:
                self.table.value = self._get_display_df()
                print(f"   🔄 Таблица перезагружена после удаления")

            print(f"   ПОСЛЕ _after_correction_change: df.Корр={self.df.at[idx, 'Корр']}, План={self.df.at[idx, 'План_Скорр']}")

            # Финальная проверка
            final_corr = self.df.at[idx, 'Корр']
            final_plan = self.df.at[idx, 'План_Скорр']
            final_auto = self.df.at[idx, 'Авто_Корр'] if 'Авто_Корр' in self.df.columns else None

            self.status.object = f"✅ {int(self.df.at[idx, 'План_Скорр']):,}"

        except Exception as ex:
            self.status.object = f"❌ Ошибка"

    # ========== Сохранение ==========

    def _do_save(self):
        if not self._save_pending:
            return
        self._save_pending = False
        self._auto_save()

    def _auto_save(self):
        """Сохраняет РУЧНЫЕ корректировки в Google Sheets"""

        # Только РУЧНЫЕ корректировки (Корр или Корр_Дельта), НЕ Авто_Корр
        manual_mask = self.df['Корр'].notna() | self.df['Корр_Дельта'].notna()

        try:
            corrections = []

            if manual_mask.any():
                cols = ['Филиал', 'Отдел', 'Месяц', 'Корр', 'Корр_Дельта', 'План_Скорр', '_План_Расч_Исх']
                cols = [c for c in cols if c in self.df.columns]
                dc = self.df.loc[manual_mask, cols].copy()

                for _, row in dc.iterrows():
                    corr_entry = {
                        'branch': row['Филиал'],
                        'dept': row['Отдел'],
                        'month': int(row['Месяц']),
                    }

                    # Корректировка (Корр >= 0 допустимо, включая 0)
                    if pd.notna(row['Корр']):
                        corr_entry['corr'] = float(row['Корр'])

                    # Дельта напрямую из колонки
                    if 'Корр_Дельта' in row and pd.notna(row['Корр_Дельта']) and row['Корр_Дельта'] != 0:
                        corr_entry['delta'] = float(row['Корр_Дельта'])

                    corrections.append(corr_entry)

            # Сохраняем в локальный JSON
            if save_corrections_local(corrections):
                self.status.object = f"💾 Сохранено ({len(corrections)})"

        except Exception as e:
            self.status.object = "⚠️ Ошибка сохр."
            print(f"❌ Ошибка сохранения корректировок: {e}")


    # ========== Асимметричная эластичность ==========

    def _setup_elasticity_sliders(self):
        """Создаёт матрицу слайдеров: отделы × филиалы"""

        # Получаем филиалы (вместо форматов) и отделы
        self.elastic_branches = sorted(self.df['Филиал'].dropna().unique().tolist())

        # Отделы отсортированные по выручке
        dept_revenue = self.df.groupby('Отдел')['Выручка_2025'].sum().sort_values(ascending=False)
        self.elastic_depts = dept_revenue.index.tolist()

        # Определяем филиалы с ростом и падением (по годовым суммам)
        # План филиала = сумма План по всем месяцам (берём первую строку каждого месяца)
        # Факт филиала = сумма Выручка_2025 по всем строкам
        branch_plan = self.df.groupby(['Филиал', 'Месяц'])['План'].first().groupby('Филиал').sum()
        branch_fact = self.df.groupby('Филиал')['Выручка_2025'].sum()

        self._branch_direction = {}
        for branch in branch_plan.index:
            plan = branch_plan.get(branch, 0)
            fact = branch_fact.get(branch, 0)
            self._branch_direction[branch] = 'growth' if plan >= fact else 'decline'

        self._growth_branches = [b for b, d in self._branch_direction.items() if d == 'growth']
        self._decline_branches = [b for b, d in self._branch_direction.items() if d == 'decline']

        for branch, direction in self._branch_direction.items():
            plan = branch_plan.get(branch, 0)
            fact = branch_fact.get(branch, 0)
            pct = (plan / fact - 1) * 100 if fact > 0 else 0

        # Загружаем сохранённые коэффициенты
        saved_coeffs = self._load_elasticity_coefficients()

        # Слайдеры: {(отдел, филиал): {'k_up': slider, 'k_down': slider}}
        self.elasticity_sliders = {}

        applied_count = 0
        for dept in self.elastic_depts:
            for branch in self.elastic_branches:
                key = (dept, branch)
                saved = saved_coeffs.get(key, {})
                default_up = saved.get('k_up', 1.0)
                default_down = saved.get('k_down', 1.0)

                # Ограничиваем диапазоном слайдера
                default_up = max(0.0, min(2.0, float(default_up)))
                default_down = max(0.0, min(2.0, float(default_down)))

                # K_up: зелёный слайдер (с яркими контурами)
                k_up = pn.widgets.FloatSlider(
                    start=0.0, end=2.0, step=0.01, value=default_up,
                    show_value=False,
                    bar_color='#4CAF50',
                    sizing_mode='stretch_width',
                    height=14,
                    margin=0,
                    stylesheets=[':host .bk-slider-bar { border: 2px solid #2E7D32; }']
                )

                # K_down: красный слайдер (с яркими контурами)
                k_down = pn.widgets.FloatSlider(
                    start=0.0, end=2.0, step=0.01, value=default_down,
                    show_value=False,
                    bar_color='#f44336',
                    sizing_mode='stretch_width',
                    height=14,
                    margin=0,
                    stylesheets=[':host .bk-slider-bar { border: 2px solid #C62828; }']
                )

                # Подписываемся на изменения
                k_up.param.watch(lambda e, d=dept, b=branch: self._on_elasticity_change(e, d, b), 'value')
                k_down.param.watch(lambda e, d=dept, b=branch: self._on_elasticity_change(e, d, b), 'value')

                self.elasticity_sliders[key] = {
                    'k_up': k_up,
                    'k_down': k_down
                }

                # Считаем сколько значений применено из сохранённых
                if key in saved_coeffs:
                    applied_count += 1


        # ========== Макс. рост сопутствующих: Филиал × Отдел ==========
        # Определяем формат каждого филиала
        self._branch_format = {}
        if 'Формат' in self.df.columns:
            for branch in self.elastic_branches:
                branch_data = self.df[self.df['Филиал'] == branch]
                if len(branch_data) > 0:
                    fmt = branch_data['Формат'].iloc[0]
                    self._branch_format[branch] = fmt if pd.notna(fmt) else 'Другой'
                else:
                    self._branch_format[branch] = 'Другой'

        # Группируем филиалы по форматам
        self._branches_by_format = {'Флагман': [], 'Средний': [], 'Другой': []}
        for branch in self.elastic_branches:
            fmt = self._branch_format.get(branch, 'Другой')
            if fmt == 'Флагман':
                self._branches_by_format['Флагман'].append(branch)
            elif fmt == 'Средний':
                self._branches_by_format['Средний'].append(branch)
            else:
                self._branches_by_format['Другой'].append(branch)


        # Определяем отделы для компрессора (Сопутствующие + Обои)
        # Фильтруем только сопутствующие отделы
        if 'Роль' in self.df.columns:
            accomp_mask = self.df['Роль'].isin(['Сопутствующий', 'Обои'])
            self._accompanying_depts = sorted(self.df[accomp_mask]['Отдел'].unique().tolist())
        else:
            self._accompanying_depts = []
        print(f"📊 Сопутствующие отделы для компрессора: {len(self._accompanying_depts)}")

        # Кнопка сброса (компактная)
        self.reset_elastic_btn = pn.widgets.Button(name='⟲', button_type='warning', width=22, height=16)
        self.reset_elastic_btn.on_click(self._reset_elasticity)

        # Кнопка сохранения (компактная)
        self.save_elastic_btn = pn.widgets.Button(name='💾', button_type='success', width=22, height=16)
        self.save_elastic_btn.on_click(self._save_elasticity_click)

        # Статус
        self.elastic_status = pn.pane.HTML("", height=25)
        self._update_elastic_status()

        # Флаги
        self._updating_elasticity = False
        self._elasticity_changed = False
        self._elasticity_timer = None  # Для debounce
        self._edit_elasticity_timer = None  # Для debounce при быстром редактировании
        self._updating_limits = False  # Защита от рекурсии при редактировании лимитов

        # ВАЖНО: НЕ вызываем _apply_elasticity здесь!
        # Она будет вызвана в view() ПОСЛЕ применения компрессора и лимитов

        # Проверка для Вологда ТЦ
        vologda_jan_mask = (self.df['Филиал'] == 'Вологда ТЦ') & (self.df['Отдел'] == 'Мебель для кухни') & (self.df['Месяц'] == 1)
        if vologda_jan_mask.any():
            plan_after = self.df.loc[vologda_jan_mask, 'План_Скорр'].values[0]
            auto_corr = self.df.loc[vologda_jan_mask, 'Авто_Корр'].values[0] if 'Авто_Корр' in self.df.columns else 'N/A'
            print(f"🔍 ПОСЛЕ _setup_elasticity_sliders: Вологда ТЦ янв Мебель План_Скорр={plan_after:,.0f}, Авто_Корр={auto_corr}")

    def _save_elasticity_click(self, event=None):
        """Обработчик кнопки сохранения"""
        self._save_elasticity_coefficients()
        self._elasticity_changed = False
        self.elastic_status.object = self.elastic_status.object.replace('</div>', ' | 💾 Сохранено!</div>')

    def _get_elasticity_filepath(self):
        """Путь к локальному файлу с коэффициентами (fallback)"""
        import os
        return os.path.join(os.getcwd(), 'elasticity_coefficients.json')

    def _load_elasticity_coefficients(self):
        """Загружает коэффициенты эластичности из локального JSON"""
        import json
        import os
        filepath = self._get_elasticity_filepath()
        if not os.path.exists(filepath):
            return {}

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            coeffs = {}
            for key_str, values in data.get('coefficients', {}).items():
                parts = key_str.split('|||')
                if len(parts) == 2:
                    dept, fmt = parts
                    k_up = max(0.0, min(2.0, float(values.get('k_up', 1.0))))
                    k_down = max(0.0, min(2.0, float(values.get('k_down', 1.0))))
                    coeffs[(dept, fmt)] = {'k_up': k_up, 'k_down': k_down}
            print(f"📂 Эластичность загружена: {len(coeffs)} записей")
            return coeffs
        except Exception as e:
            print(f"❌ Ошибка загрузки эластичности: {e}")
            return {}

    def _save_elasticity_coefficients(self):
        """Сохраняет коэффициенты эластичности в Google Sheets"""
        try:
            # Собираем ВСЕ коэффициенты
            coefficients = {}

            for dept in self.elastic_depts:
                for branch in self.elastic_branches:
                    key = (dept, branch)
                    if key not in self.elasticity_sliders:
                        continue
                    k_up = self.elasticity_sliders[key]['k_up'].value
                    k_down = self.elasticity_sliders[key]['k_down'].value
                    coefficients[key] = {'k_up': round(k_up, 2), 'k_down': round(k_down, 2)}

            # Сохраняем в локальный JSON
            import json
            filepath = self._get_elasticity_filepath()
            # Преобразуем ключи для JSON
            json_coeffs = {f"{k[0]}|||{k[1]}": v for k, v in coefficients.items()}
            data = {'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'), 'coefficients': json_coeffs}
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"💾 Эластичность сохранена: {len(coefficients)} записей")

        except Exception as e:
            print(f"❌ Ошибка сохранения эластичности: {e}")

    def _get_city_limits_filepath(self):
        """Путь к файлу с лимитами роста (fallback)"""
        import os
        return os.path.join(os.getcwd(), 'branch_dept_max_growth.json')

    def _load_city_dept_limits(self):
        """Загружает лимиты макс. роста: Филиал × Отдел из локального JSON"""
        self._branch_dept_limits = {}

        # Загружаем из локального JSON
        limits = load_limits_local()
        if limits:
            # Конвертируем ключи из "branch|||dept" в (branch, dept)
            for key, val in limits.items():
                if '|||' in str(key):
                    parts = key.split('|||')
                    if len(parts) == 2:
                        self._branch_dept_limits[(parts[0], parts[1])] = val
                else:
                    self._branch_dept_limits[key] = val
            print(f"📂 Лимиты загружены: {len(self._branch_dept_limits)} записей")

    def _save_branch_dept_limits(self):
        """Сохраняет лимиты макс. роста: Филиал × Отдел в локальный JSON"""
        try:
            # Собираем лимиты
            limits_for_save = {}
            for (branch, dept), val in self._branch_dept_limits.items():
                if val is not None and val != '':
                    try:
                        limits_for_save[(branch, dept)] = int(val)
                    except (ValueError, TypeError):
                        pass

            # Сохраняем в локальный JSON
            if save_limits_local(limits_for_save):
                print(f"💾 Лимиты сохранены: {len(limits_for_save)} записей")

        except Exception as e:
            print(f"❌ Ошибка сохранения лимитов: {e}")

    def _apply_loaded_limits(self):
        """Применяет загруженные лимиты — пересчитывает все затронутые группы"""
        if not self._branch_dept_limits:
            return

        # Собираем уникальные филиалы с лимитами
        branches_with_limits = set(branch for branch, dept in self._branch_dept_limits.keys())
        print(f"📊 Применяю лимиты для {len(branches_with_limits)} филиалов...")

        for branch in branches_with_limits:
            months = self.df[self.df['Филиал'] == branch]['Месяц'].unique()
            for month in months:
                self._redistribute_group(branch, month)
                # ВАЖНО: применяем лимиты ПОСЛЕ распределения!
                self._apply_limits_for_group(branch, month)

        # Сбрасываем кеш
        self._cached_filtered_df = None
        self._cached_agg = None

        # Применяем специальные правила (Двери, Мебель для кухни)
        self._apply_special_rules()

        # ВАЖНО: Полностью синхронизируем df_original с df после лимитов
        if hasattr(self, 'df_original') and self.df_original is not None:
            for col in ['План_Скорр', 'План_Расч', 'Рекоменд']:
                if col in self.df.columns:
                    self.df_original[col] = self.df[col].values
            print(f"   📋 df_original синхронизирован с df после лимитов")

        print(f"✅ Лимиты применены")

    def _save_compressor(self):
        """Сохраняет настройки компрессора в локальный JSON"""
        try:
            if not hasattr(self, '_compressor_sliders') or not self._compressor_sliders:
                return

            # Собираем настройки из слайдеров
            compressor_dict = {}
            for (branch, dept), data in self._compressor_sliders.items():
                growth = data['slider_growth'].value if 'slider_growth' in data else 1.0
                decline = data['slider_decline'].value if 'slider_decline' in data else 1.0
                if growth != 1.0 or decline != 1.0:
                    compressor_dict[(branch, dept)] = {'growth': growth, 'decline': decline}

            # Сохраняем в локальный JSON
            if save_compressor_local(compressor_dict):
                print(f"💾 Компрессор сохранён: {len(compressor_dict)} записей")
                return True
            return False
        except Exception as e:
            print(f"❌ Ошибка сохранения компрессора: {e}")
            return False

    def _load_compressor(self):
        """Загружает настройки компрессора из локального JSON"""
        try:
            compressor = load_compressor_local()
            if compressor:
                print(f"📂 Загружено {len(compressor)} настроек компрессора")
            return compressor
        except Exception as e:
            print(f"⚠️ Ошибка загрузки компрессора: {e}")
            return {}

    def _apply_loaded_compressor(self, compressor_settings):
        """Применяет загруженные настройки компрессора к слайдерам"""
        if not compressor_settings:
            return

        print(f"🎚️ Применяю настройки компрессора: {len(compressor_settings)} отделов")

        for (branch, dept), vals in compressor_settings.items():
            key = (branch, dept)
            if key in self._compressor_sliders:
                growth = vals.get('growth', 1.0)
                decline = vals.get('decline', 1.0)

                if 'slider_growth' in self._compressor_sliders[key]:
                    self._compressor_sliders[key]['slider_growth'].value = growth
                if 'slider_decline' in self._compressor_sliders[key]:
                    self._compressor_sliders[key]['slider_decline'].value = decline

                print(f"   🎚️ {branch} / {dept}: growth={growth}, decline={decline}")

        print(f"✅ Настройки компрессора применены к слайдерам")

    def _apply_compressor_on_load(self):
        """Применяет загруженные настройки компрессора к данным при старте дашборда"""
        if not self._loaded_compressor_settings:
            return

        print(f"\n{'='*60}")
        print(f"🎚️ ПРИМЕНЕНИЕ КОМПРЕССОРА ПРИ ЗАГРУЗКЕ ({len(self._loaded_compressor_settings)} настроек)")
        print(f"{'='*60}")

        changes_count = 0
        MIN_GROWTH_BASE = 0.06  # Минимальная база прироста 6% для расчёта

        for idx in self.df.index:
            branch = self.df.at[idx, 'Филиал']
            dept = self.df.at[idx, 'Отдел']

            # Ищем настройки для этого филиала/отдела или для "Все"/отдел
            key = (branch, dept)
            key_all = ('Все', dept)

            mults = self._loaded_compressor_settings.get(key) or self._loaded_compressor_settings.get(key_all)
            if not mults:
                continue

            growth_mult = mults.get('growth', 1.0)
            decline_mult = mults.get('decline', 1.0)

            if growth_mult == 1.0 and decline_mult == 1.0:
                continue

            # Пропускаем строки с ручными корректировками
            corr = self.df.at[idx, 'Корр']
            delta = self.df.at[idx, 'Корр_Дельта']
            if pd.notna(corr) or pd.notna(delta):
                continue

            rev25 = self.df.at[idx, 'Выручка_2025']
            base_plan = self.df.at[idx, '_План_Расч_Исх']

            if rev25 <= 0 or base_plan <= 0:
                continue

            # Базовый прирост
            base_growth_pct = (base_plan / rev25 - 1)

            # Применяем множитель
            if base_growth_pct >= 0:
                # Для роста: если базовый прирост очень мал, используем минимум
                effective_growth = max(base_growth_pct, MIN_GROWTH_BASE) if growth_mult > 1.0 else base_growth_pct
                new_growth_pct = effective_growth * growth_mult
            else:
                new_growth_pct = base_growth_pct * decline_mult

            # Новый план
            new_plan = rev25 * (1 + new_growth_pct)
            new_plan = int(round(new_plan / CONFIG['rounding_step'])) * CONFIG['rounding_step']
            new_plan = max(0, new_plan)

            old_plan = self.df.at[idx, 'План_Скорр']

            if new_plan != old_plan:
                self.df.at[idx, 'План_Скорр'] = new_plan
                self.df.at[idx, 'План_Расч'] = new_plan
                self.df.at[idx, 'Рекоменд'] = new_plan
                self.df.at[idx, 'Авто_Корр'] = new_plan
                if hasattr(self, 'df_original'):
                    self.df_original.at[idx, 'План_Скорр'] = new_plan
                    self.df_original.at[idx, 'План_Расч'] = new_plan
                    self.df_original.at[idx, 'Рекоменд'] = new_plan
                changes_count += 1

        # Пересчитываем метрики
        if changes_count > 0:
            for (branch, month), _ in self.df.groupby(['Филиал', 'Месяц']):
                gm = (self.df['Филиал'] == branch) & (self.df['Месяц'] == month)
                recalc_row_metrics(self.df, gm, self.cols_available)

            self._cached_filtered_df = None
            self._cached_agg = None

            # Применяем специальные правила (Двери, Мебель для кухни)
            self._apply_special_rules()

            # ВАЖНО: Полностью синхронизируем df_original с df после компрессора
            # чтобы _apply_elasticity не восстановила старые значения
            if hasattr(self, 'df_original') and self.df_original is not None:
                for col in ['План_Скорр', 'План_Расч', 'Рекоменд', 'Авто_Корр']:
                    if col in self.df.columns:
                        self.df_original[col] = self.df[col].values
                print(f"   📋 df_original синхронизирован с df")

        print(f"   ✅ Изменено строк при загрузке: {changes_count}")

    def _apply_compressor(self):
        """
        Весовая Компрессия (2025-01-30):
        Модифицирует Final_Weight на основе множителей и перераспределяет план.
        Гарантирует сохранение общей суммы (Цели).
        """
        branch_filter = self._compressor_branch_select.value

        print(f"\n{'='*60}")
        print(f"🎚️ ПРИМЕНЕНИЕ КОМПРЕССОРА (ВЕСОВОЙ): филиал={branch_filter}")
        print(f"{'='*60}")

        if 'Base_Weight' not in self.df.columns:
            print("⚠️ Base_Weight не найден. Инициализирую копией Final_Weight.")
            self.df['Base_Weight'] = self.df['Final_Weight'].copy()

        # Сброс весов к базовым перед применением
        # Это важно, чтобы множители не накапливались при повторном нажатии
        if branch_filter == 'Все':
            self.df['Final_Weight'] = self.df['Base_Weight'].copy()
        else:
            # Сбрасываем только для выбранного филиала
            mask = self.df['Филиал'] == branch_filter
            self.df.loc[mask, 'Final_Weight'] = self.df.loc[mask, 'Base_Weight']

        changes_count = 0

        # Собираем множители
        multipliers = {}
        for key, data in self._compressor_sliders.items():
            growth = data['slider_growth'].value if 'slider_growth' in data else 1.0
            decline = data['slider_decline'].value if 'slider_decline' in data else 1.0
            if growth != 1.0 or decline != 1.0:
                multipliers[key] = {'growth': growth, 'decline': decline}

        if not multipliers:
            print("   Все множители = 1.0, сброс к базовым весам выполнен.")
            # Даже если множителей нет, нужно перераспределить (вдруг раньше было сжато)
            # Но если мы сбросили к базе, то redistrib вернет базовый план

        affected_groups = set()

        # Применяем множители к весам
        for idx in self.df.index:
            branch = self.df.at[idx, 'Филиал']
            dept = self.df.at[idx, 'Отдел']

            if branch_filter != 'Все' and branch != branch_filter:
                continue

            key = (branch_filter, dept) # Ключ слайдера (обычно (Филиал, Отдел) или (Все, Отдел))
            # Если фильтр 'Все', а слайдеры индивидуальные? 
            # В текущей реализации ключи слайдеров зависят от того, как они были созданы.
            # Обычно они создаются под текущий view.
            # Если выбрано "Все", то ключи могут быть ('Все', Отдел).
            # Если выбран "Владимир", ключи ('Владимир', Отдел).

            # Проверим наличие множителя
            mults = multipliers.get(key)
            # Если не нашли прямого совпадения, попробуем поискать ('Все', dept) если мы внутри филиала?
            # Или наоборот. Тут полагаемся на то, что self._compressor_sliders согласованы с current view.

            if not mults:
                continue

            # Определяем, растет отдел или падает (по базовому сценарию)
            # Рост = Theoretical_Plan > Forecast_2025
            # Theoretical_Plan = Target * Base_Weight
            # Но Target может быть сложным. Проще сравнить Base_Weight с естественной долей.
            # Или взять сохраненный тренд?

            # Используем простую эвристику: 
            # Если Rev_2025 > 0:
            #   Projected = Base_Weight * (Total_Target of Branch) -- сложно достать Total_Target здесь быстро.
            #   Попробуем использовать отношение Base_Weight к доле выручки 2025.

            # ВАРИАНТ ПРОЩЕ: Сравнить (Base_Weight) vs (Rev_2025 / Sum_Rev_2025 города)
            # Но Sum_Rev_2025 надо считать.

            # Давайте возьмем знак из План_Скорр (если он уже посчитан) vs Rev_2025?
            # Или просто: Growth Slider применяется если мы ХОТИМ увеличить/уменьшить РОСТ.
            # Если пользователь крутит Growth Slider, он подразумевает "для растущих".

            # Использование:
            # Если Base_Weight * Target > Rev2025 -> Growth.
            # Но у нас нет Target под рукой в цикле по строкам.

            # Workaround:
            # В `prepare_baseline` считался `base_growth_pct`. Можно было бы его сохранить.
            # Но давайте посчитаем локально, используя текущие значения План_Скорр (до компрессии они равны базовым если сбросили).
            # Но мы только что сбросили веса, но План_Скорр еще старый (или уже пересчитан?).

            # Лучший вариант: Считаем, что "Рост" это когда Base_Weight > (Rev2025 / TotRev25).
            # Или просто смотрим на Rev2025.

            # Для надежности возьмем логику: 
            # Если (План_Расч / Выручка_2025) > 1 -> Рост.
            # Но План_Расч сейчас может быть "сжат".
            # Возьмем данные из строки, надеясь что они актуальны (или из df_original?)

            rev25 = self.df.at[idx, 'Выручка_2025']
            # Используем _План_Расч_Исх как индикатор направления, если он есть
            indicator_plan = self.df.at[idx, '_План_Расч_Исх'] if '_План_Расч_Исх' in self.df.columns else self.df.at[idx, 'План_Расч']

            is_growing = (indicator_plan > rev25) if rev25 > 0 else True

            multiplier = mults['growth'] if is_growing else mults['decline']

            if multiplier != 1.0:
                old_weight = self.df.at[idx, 'Base_Weight']
                new_weight = old_weight * multiplier
                self.df.at[idx, 'Final_Weight'] = new_weight
                changes_count += 1
                affected_groups.add((branch, self.df.at[idx, 'Месяц']))

        # Перераспределяем планы в затронутых группах
        print(f"   🔄 Перерасчет {len(affected_groups)} групп...")
        for branch, month in affected_groups:
            self._redistribute_group(branch, month)

        print(f"   ✅ Веса обновлены у {changes_count} отделов. Планы пересчитаны.")

        # Обновляем UI
        self._cached_filtered_df = None
        self._cached_agg = None
        self._after_correction_change()

        # Сохраняем
        self._save_compressor()

        self._compressor_status.object = f"<span style='font-size:9px;color:#4CAF50;'>✅ Применено (W)</span>"

    def _on_elasticity_change(self, event, dept, fmt):
        """Обработчик изменения слайдера - пересчёт и сохранение сразу"""
        if self._updating_elasticity:
            return

        self._updating_elasticity = True
        try:
            # Пересчёт сразу
            self._apply_elasticity()

            # Сохраняем СРАЗУ (не откладываем)
            self._save_elasticity_coefficients()

        except Exception as e:
            print(f"Ошибка: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._updating_elasticity = False

    def _save_elasticity_once(self):
        """Сохраняет коэффициенты один раз (legacy, для совместимости)"""
        self._save_elasticity_coefficients()

    def _apply_elasticity_debounced(self):
        """Отложенный пересчёт эластичности (legacy, не используется)"""
        try:
            self._apply_elasticity()
        except Exception as e:
            print(f"Ошибка debounced: {e}")

    def _apply_elasticity(self, event=None):
        """Применяет асимметричную эластичность.

        Логика:
        1. Восстанавливаем План_Скорр из df_original только для СВОБОДНЫХ отделов
        2. Отделы с корректировками (Корр/Корр_Дельта) сохраняют свои значения
        3. Применяем эластичность - пересчитываем свободные отделы
        """
        try:
            if len(self.df) != len(self.df_original):
                print(f"❌ ОШИБКА: len(df)={len(self.df)} != len(df_original)={len(self.df_original)}")
                return

            # DEBUG: Вологда ТЦ Кухня декабрь В НАЧАЛЕ _apply_elasticity
            vol_kitchen_dec = (self.df['Филиал'] == 'Вологда ТЦ') & (self.df['Отдел'] == 'Мебель для кухни') & (self.df['Месяц'] == 12)
            if vol_kitchen_dec.any():
                idx = self.df.index[vol_kitchen_dec][0]
                df_korr = self.df.at[idx, 'Корр'] if 'Корр' in self.df.columns else None
                df_auto = self.df.at[idx, 'Авто_Корр'] if 'Авто_Корр' in self.df.columns else None
                df_plan = self.df.at[idx, 'План_Скорр']
                orig_korr = self.df_original.at[idx, 'Корр'] if 'Корр' in self.df_original.columns else None
                orig_auto = self.df_original.at[idx, 'Авто_Корр'] if 'Авто_Корр' in self.df_original.columns else None
                orig_plan = self.df_original.at[idx, 'План_Скорр']
                print(f"🍳 НАЧАЛО _apply_elasticity: Вологда/Кухня/дек")
                print(f"   df: Корр={df_korr}, Авто={df_auto}, План={df_plan:,.0f}")
                print(f"   orig: Корр={orig_korr}, Авто={orig_auto}, План={orig_plan:,.0f}")

            # ШАГ 1: Определяем отделы с корректировками (их НЕ перезаписываем)
            corr_mask = has_correction(self.df)

            # ВАЖНО: также не перезаписываем отделы с активными лимитами!
            limit_mask = pd.Series(False, index=self.df.index)
            limits_dict = getattr(self, '_branch_dept_limits', {})
            if limits_dict:
                for idx in self.df.index:
                    branch = self.df.loc[idx, 'Филиал']
                    dept = self.df.loc[idx, 'Отдел']
                    key = (branch, dept)
                    if key in limits_dict:
                        limit_mask.loc[idx] = True

            free_mask = ~(corr_mask | limit_mask)

            # DEBUG: проверка Москва Хаб / Мебель
            mh_mebel = self.df[(self.df['Филиал'].str.contains('Хаб', na=False)) &
                               (self.df['Отдел'].str.contains('Мебель для дома', na=False)) &
                               (self.df['Месяц'] == 11)]
            if not mh_mebel.empty:
                idx = mh_mebel.index[0]
                is_free = free_mask.loc[idx]
                is_limit = limit_mask.loc[idx]
                is_corr = corr_mask.loc[idx]
                orig_val = self.df_original.loc[idx, 'План_Скорр'] if idx in self.df_original.index else 0
                cur_val = self.df.loc[idx, 'План_Скорр']
                print(f"🔍 _apply_elasticity START: МХ/Мебель/ноя - cur={cur_val:,.0f}, orig={orig_val:,.0f}, free={is_free}, limit={is_limit}, corr={is_corr}")

            # Сохраняем текущие корректировки
            corr_plans = self.df.loc[corr_mask, 'План_Скорр'].copy() if corr_mask.any() else None
            corr_korr = self.df.loc[corr_mask, 'Корр'].copy() if corr_mask.any() else None
            corr_delta = self.df.loc[corr_mask, 'Корр_Дельта'].copy() if corr_mask.any() else None

            # ШАГ 2: Собираем коэффициенты эластичности
            coeffs = {}
            all_default = True
            changed_keys = []

            for dept in self.elastic_depts:
                for branch in self.elastic_branches:
                    key = (dept, branch)
                    k_up = self.elasticity_sliders[key]['k_up'].value
                    k_down = self.elasticity_sliders[key]['k_down'].value
                    coeffs[key] = {'k_up': k_up, 'k_down': k_down}

                    if abs(k_up - 1.0) > 0.01 or abs(k_down - 1.0) > 0.01:
                        all_default = False
                        changed_keys.append(key)

            # ШАГ 3: Применяем эластичность
            # Перераспределяем если:
            # - есть изменённые K (not all_default)
            # - ИЛИ есть ручные корректировки (corr_mask.any())
            # - ИЛИ есть активные лимиты роста
            has_limits = bool(getattr(self, '_branch_dept_limits', {}))
            need_redistribute = (not all_default) or corr_mask.any() or has_limits

            # ВАЖНО: Восстанавливаем из df_original ТОЛЬКО если нужно перераспределение
            # Иначе сохраняем текущие данные (например, от компрессора)
            if need_redistribute and free_mask.any():
                self.df.loc[free_mask, 'План_Расч'] = self.df_original.loc[free_mask, 'План_Расч'].values
                self.df.loc[free_mask, 'План_Скорр'] = self.df_original.loc[free_mask, 'План_Скорр'].values

            orig_sum = self.df_original['План_Скорр'].sum()
            current_sum = self.df['План_Скорр'].sum()
            corr_sum = self.df.loc[corr_mask, 'План_Скорр'].sum() if corr_mask.any() else 0

            if need_redistribute:
                reason = []
                if not all_default:
                    reason.append(f"K≠1.0: {len(changed_keys)}")
                if corr_mask.any():
                    reason.append(f"корр: {corr_mask.sum()}")
                if has_limits:
                    reason.append(f"лимиты: {len(self._branch_dept_limits)}")

                branch_direction = self._branch_direction
                groups = self.df.groupby(['Филиал', 'Месяц']).groups

                for (branch, month), group_idx in groups.items():
                    is_growth = branch_direction.get(branch, 'growth') == 'growth'
                    self._apply_elasticity_to_group_fast(branch, month, group_idx, coeffs, is_growth)

                # Проверка сходимости
                total_plan = self.df['План_Скорр'].sum()
                total_target = self.df.groupby(['Филиал', 'Месяц'])['План'].first().sum()
                global_diff = total_target - total_plan

            # ШАГ 4: Обновляем метрики и UI
            recalc_row_metrics(self.df, self.df.index, self.cols_available)
            self._update_seasonality_plan()
            self._calc_recommendation()

            # DEBUG: Проверка кухни ПОСЛЕ всех операций эластичности
            vol_kitchen_dec = (self.df['Филиал'] == 'Вологда ТЦ') & (self.df['Отдел'] == 'Мебель для кухни') & (self.df['Месяц'] == 12)
            if vol_kitchen_dec.any():
                row = self.df.loc[vol_kitchen_dec].iloc[0]
                print(f"🍳 ПОСЛЕ _apply_elasticity (ШАГ 4):")
                print(f"   Корр = {row.get('Корр', 'N/A')}, Авто_Корр = {row.get('Авто_Корр', 'N/A')}")
                print(f"   План_Скорр = {row.get('План_Скорр', 'N/A'):,.0f}")

            # ШАГ 5: Применяем минимальный план для сетевых форматов (финальный шаг)
            self._apply_min_plan_network(silent=True)

            self._cached_filtered_df = None
            self._cached_agg = None
            self._do_update()
            self._update_elastic_status()

        except Exception as e:
            print(f"Ошибка: {e}")
            import traceback
            traceback.print_exc()

    def _apply_elasticity_to_group(self, branch, month, group_idx, coeffs):
        """Применяет эластичность к группе филиал-месяц через ВИРТУАЛЬНЫЕ ВЕСА.

        Логика:
        1. V_i = Факт_i × K_i — виртуальный объём (K из слайдера)
        2. weight_i = V_i / Σ(V) — новый вес отдела
        3. План_i = remaining_target × weight_i — план пропорционально весу

        Это гарантирует:
        - K=0 → V=0 → вес=0 → план=0 (отдел не получает план)
        - K=2 → V удваивается → доля растёт
        - Сумма планов = target (сходимость)

        Фиксированные отделы (не участвуют в эластичности):
        - С ручными корректировками (Корр/Корр_Дельта)
        - "Не считаем план"

        is_growth определяется на уровне ФИЛИАЛА ЗА ГОД (не за месяц!)
        ВСЕ данные берутся из df_original для стабильности!
        """
        g = self.df.loc[group_idx]
        g_orig = self.df_original.loc[group_idx]  # Оригинальные данные

        target = g['План'].iloc[0]
        if pd.isna(target):
            return
        target = int(round(target))

        # Определяем рост/падение на уровне ФИЛИАЛА ЗА ГОД (из оригинала)
        branch_data = self.df_original[self.df_original['Филиал'] == branch]
        branch_plan_total = branch_data.groupby('Месяц')['План'].first().sum()
        branch_fact_total = branch_data['Выручка_2025'].sum()
        is_growth = branch_plan_total >= branch_fact_total

        fmt = g_orig['Формат'].iloc[0] if 'Формат' in g_orig.columns else 'Все'

        # Фиксированные = корректировки ИЛИ "Не считаем план" — проверяем в ТЕКУЩЕМ df!
        g = self.df.loc[group_idx]
        corr_mask = has_correction(g)
        no_plan_mask = g_orig['Правило'] == 'Не считаем план' if 'Правило' in g_orig.columns else pd.Series(False, index=g_orig.index)
        fixed_mask = corr_mask | no_plan_mask

        # ШАГ 1: Считаем фиксированную сумму из ТЕКУЩЕГО df (планы уже установлены через _recalc_plan)
        fixed_sum = self.df.loc[group_idx[fixed_mask.values], 'План_Скорр'].sum() if fixed_mask.any() else 0
        remaining_target = target - fixed_sum

        # ШАГ 2: Считаем виртуальные объёмы V_i = Факт × K для свободных отделов
        virtual_volumes = {}  # {idx: V_i}

        for idx in group_idx:
            if fixed_mask.loc[idx]:
                continue  # Пропускаем фиксированные

            dept = g_orig.loc[idx, 'Отдел']
            fact = g_orig.loc[idx, 'Выручка_2025']
            rule = g_orig.loc[idx, 'Правило'] if 'Правило' in g_orig.columns else ''

            # Для правила "Формат" или сетевых форматов используем План_Расч (учитывает сезонность сети)
            rule_lower = str(rule).lower() if pd.notna(rule) else ''
            is_format_rule = 'формат' in rule_lower

            # ВАЖНО: Для сетевых форматов (Мини/Микро/Интернет) всегда используем План_Расч
            is_network_fmt = g_orig.loc[idx, 'is_network_format'] if 'is_network_format' in g_orig.columns else False

            # Получаем K из слайдера
            key = (dept, fmt)
            k_coeffs = coeffs.get(key, {'k_up': 1.0, 'k_down': 1.0})
            k = k_coeffs['k_up'] if is_growth else k_coeffs['k_down']

            # Виртуальный объём
            # Для форматов и сетевых форматов — берём План_Расч (рассчитанный по сетевым весам)
            if is_format_rule or is_network_fmt or fact <= 0:
                base_plan = g_orig.loc[idx, 'План_Расч']
                v = base_plan * k
            else:
                v = fact * k

            virtual_volumes[idx] = max(0, v)

        # ШАГ 3: Сумма виртуальных объёмов
        sum_v = sum(virtual_volumes.values())

        # ШАГ 4: Распределяем remaining_target пропорционально виртуальным весам
        if sum_v > 0 and remaining_target > 0:
            for idx, v in virtual_volumes.items():
                weight = v / sum_v
                new_plan = remaining_target * weight
                new_plan = round(new_plan / CONFIG['rounding_step']) * CONFIG['rounding_step']

                self.df.loc[idx, 'План_Скорр'] = new_plan
                self.df.loc[idx, 'План_Расч'] = new_plan

        elif sum_v == 0 and remaining_target > 0:
            # Все K=0, но есть план — распределяем равномерно как fallback
            free_idx = [idx for idx in group_idx if not fixed_mask.loc[idx]]
            if free_idx:
                per_dept = remaining_target / len(free_idx)
                per_dept = round(per_dept / CONFIG['rounding_step']) * CONFIG['rounding_step']
                for idx in free_idx:
                    self.df.loc[idx, 'План_Скорр'] = per_dept
                    self.df.loc[idx, 'План_Расч'] = per_dept

        elif remaining_target <= 0:
            # Фиксированные забрали всё или больше
            for idx in virtual_volumes.keys():
                self.df.loc[idx, 'План_Скорр'] = 0
                self.df.loc[idx, 'План_Расч'] = 0

        # ШАГ 4.5: Обнуление малых планов и перераспределение
        min_threshold = BUSINESS_RULES['MIN_PLAN_THRESHOLD']
        free_idx_list = [idx for idx in group_idx if not fixed_mask.loc[idx]]
        small_plans = [idx for idx in free_idx_list if 0 < self.df.loc[idx, 'План_Скорр'] < min_threshold]

        if small_plans:
            freed = sum(self.df.loc[idx, 'План_Скорр'] for idx in small_plans)
            for idx in small_plans:
                self.df.loc[idx, 'План_Скорр'] = 0
                self.df.loc[idx, 'План_Расч'] = 0

            # Перераспределяем на оставшиеся свободные отделы
            remaining_free = [idx for idx in free_idx_list if idx not in small_plans and self.df.loc[idx, 'План_Скорр'] > 0]
            if remaining_free and freed > 0:
                total_weight = sum(virtual_volumes.get(idx, 0) for idx in remaining_free)
                if total_weight > 0:
                    for idx in remaining_free:
                        w = virtual_volumes.get(idx, 0) / total_weight
                        add = round(freed * w / CONFIG['rounding_step']) * CONFIG['rounding_step']
                        self.df.loc[idx, 'План_Скорр'] += add
                        self.df.loc[idx, 'План_Расч'] += add

        # ШАГ 5: Корректировка сходимости (из-за округления)
        current_sum = self.df.loc[group_idx, 'План_Скорр'].sum()
        diff = target - current_sum
        if abs(diff) > 0:
            # Добавляем разницу к самому большому свободному отделу
            free_idx = [i for i in group_idx if not fixed_mask.loc[i] and self.df.loc[i, 'План_Скорр'] > 0]
            if free_idx:
                if diff < 0:
                    # Уменьшаем - ищем отдел который можно уменьшить
                    can_decrease = [idx for idx in free_idx if self.df.loc[idx, 'План_Скорр'] > abs(diff)]
                    if can_decrease:
                        max_idx = max(can_decrease, key=lambda i: self.df.loc[i, 'План_Скорр'])
                        self.df.loc[max_idx, 'План_Скорр'] += diff
                        self.df.loc[max_idx, 'План_Расч'] += diff
                else:
                    # Увеличиваем - просто на самый большой
                    max_idx = max(free_idx, key=lambda i: self.df.loc[i, 'План_Скорр'])
                    self.df.loc[max_idx, 'План_Скорр'] += diff
                    self.df.loc[max_idx, 'План_Расч'] += diff

    def _apply_elasticity_to_group_fast(self, branch, month, group_idx, coeffs, is_growth):
        """МАРЖИНАЛЬНОЕ распределение: база (факт) + доля дельты.

        Логика:
        1. Фиксированные отделы (с корректировками) получают свой план
        2. Факт свободных = sum(Факт_i) для отделов без корректировок
        3. Дельта = remaining_target - Факт_свободных
        4. План_i = Факт_i + Дельта × (Факт_i × K_i) / Σ(Факт_j × K_j)

        При K=0.5 отдел получает половину своей доли дельты, но база (факт) сохраняется.
        """
        g = self.df.loc[group_idx]
        g_orig = self.df_original.loc[group_idx]

        target = g['План'].iloc[0]
        if pd.isna(target):
            return
        target = int(round(target))

        # Филиал группы - используем для ключа слайдеров
        # (branch уже передан как параметр функции)

        # Фиксированные отделы - проверяем в ТЕКУЩЕМ df
        corr_mask = has_correction(g)
        no_plan_mask = g['Правило'] == 'Не считаем план' if 'Правило' in g.columns else pd.Series(False, index=g.index)
        fixed_mask = corr_mask | no_plan_mask

        # DEBUG: Проверка кухни
        is_vologda_kitchen = (branch == 'Вологда ТЦ') and (month == 12) and ('Мебель для кухни' in g['Отдел'].values)
        if is_vologda_kitchen:
            kitchen_idx = g[g['Отдел'] == 'Мебель для кухни'].index
            if len(kitchen_idx) > 0:
                idx = kitchen_idx[0]
                korr = g.loc[idx, 'Корр'] if 'Корр' in g.columns else None
                auto = g.loc[idx, 'Авто_Корр'] if 'Авто_Корр' in g.columns else None
                plan = self.df.loc[idx, 'План_Скорр']
                is_fixed = fixed_mask.loc[idx]
                print(f"🍳 _apply_elasticity_to_group_fast: Вологда/Кухня/дек")
                print(f"   Корр={korr}, Авто_Корр={auto}, План_Скорр={plan:,.0f}, is_fixed={is_fixed}")

        debug_this = 'Фрунзе' in str(branch) and fixed_mask.any()

        if debug_this:

            # Информация о скорректированных отделах
            for idx in group_idx[fixed_mask.values]:
                dept = g.loc[idx, 'Отдел']
                fact = g_orig.loc[idx, 'Выручка_2025']
                plan = self.df.loc[idx, 'План_Скорр']
                corr_v = g.loc[idx, 'Корр'] if 'Корр' in g.columns else None
                delta_v = g.loc[idx, 'Корр_Дельта'] if 'Корр_Дельта' in g.columns else None
                pct = ((plan / fact - 1) * 100) if fact > 0 else 0

        # Сумма планов фиксированных (из ТЕКУЩЕГО df - планы уже установлены через _recalc_plan)
        if fixed_mask.any():
            fixed_plan = self.df.loc[group_idx[fixed_mask.values], 'План_Скорр'].sum()
        else:
            fixed_plan = 0

        # Свободные индексы
        free_mask = ~fixed_mask
        free_idx = group_idx[free_mask.values]
        if len(free_idx) == 0:
            return

        # Остаток для свободных отделов
        remaining_target = target - fixed_plan

        # Собираем факты и взвешенные факты свободных отделов
        free_facts = []
        free_facts_original = []  # Оригинальные Выручка_2025 для проверки лимитов
        weighted_facts = []

        for idx in free_idx:
            dept = g_orig.loc[idx, 'Отдел']
            fact = g_orig.loc[idx, 'Выручка_2025']
            fact_original = fact  # Сохраняем оригинал для лимитов
            role = g_orig.loc[idx, 'Роль'] if 'Роль' in g_orig.columns else 'Сопутствующий'
            rule = g_orig.loc[idx, 'Правило'] if 'Правило' in g_orig.columns else ''

            # Для правила "Формат" используем План_Расч (он учитывает сезонность сети)
            # вместо Выручка_2025 (которая отражает локальную структуру)
            rule_lower = str(rule).lower() if pd.notna(rule) else ''
            is_format_rule = 'формат' in rule_lower

            # ВАЖНО: Для сетевых форматов (Мини/Микро/Интернет) всегда используем План_Расч
            is_network_fmt = g_orig.loc[idx, 'is_network_format'] if 'is_network_format' in g_orig.columns else False

            if is_format_rule or is_network_fmt or fact <= 0:
                fact = g_orig.loc[idx, 'План_Расч']
            fact = max(0, fact)

            # Слайдеры K применяются ТОЛЬКО для стратегических
            if role == 'Стратегический':
                # Ищем коэффициенты: сначала точный ключ (отдел, филиал), потом fallback
                key = (dept, branch)
                if key in coeffs:
                    k_coeffs = coeffs[key]
                else:
                    # Fallback: ищем любой ключ с этим отделом
                    k_coeffs = None
                    for (d, b), c in coeffs.items():
                        if d == dept:
                            k_coeffs = c
                            break
                    if k_coeffs is None:
                        k_coeffs = {'k_up': 1.0, 'k_down': 1.0}

                k = k_coeffs['k_up'] if is_growth else k_coeffs['k_down']
            else:
                # Для сопутствующих K = 1.0 (без тонкой настройки)
                k = 1.0

            free_facts.append(fact)
            free_facts_original.append(max(0, fact_original))  # Сохраняем оригинал
            weighted_facts.append(fact * k)

        sum_free_facts = sum(free_facts)
        sum_weighted = sum(weighted_facts)

        # Теоретический план скорректированных (если бы они не были скорректированы)
        # = факт_скорр × (target / общий_факт)
        total_fact = sum_free_facts + g_orig.loc[fixed_mask, 'Выручка_2025'].sum() if fixed_mask.any() else sum_free_facts
        theoretical_fixed = 0
        if fixed_mask.any() and total_fact > 0:
            for idx in group_idx[fixed_mask.values]:
                fact_fixed = g_orig.loc[idx, 'Выручка_2025']
                theoretical_fixed += target * (fact_fixed / total_fact) if total_fact > 0 else 0

        # Высвобожденная разница
        freed = theoretical_fixed - fixed_plan

        # ДЕЛЬТА = сколько нужно добавить/убавить сверх фактов
        delta = remaining_target - sum_free_facts

        if debug_this:

            # Что получат свободные
            avg_free_change = ((remaining_target / sum_free_facts - 1) * 100) if sum_free_facts > 0 else 0

        # Распределяем: Факт + доля дельты
        rounding_step = CONFIG['rounding_step']
        limits_dict = getattr(self, '_branch_dept_limits', {})

        # ====== ШАГ 1: Рассчитываем план БЕЗ лимитов для всех ======
        preliminary_plans = []

        for i, idx in enumerate(free_idx):
            fact = free_facts[i]
            fact_original = free_facts_original[i]
            weighted = weighted_facts[i]
            dept = g_orig.loc[idx, 'Отдел']
            role = g_orig.loc[idx, 'Роль'] if 'Роль' in g_orig.columns else 'Сопутствующий'

            if sum_weighted > 0 and delta != 0:
                share = weighted / sum_weighted
                dept_delta = delta * share
            elif delta != 0 and len(free_idx) > 0:
                dept_delta = delta / len(free_idx)
            else:
                dept_delta = 0

            # План БЕЗ лимита
            prelim_plan = fact + dept_delta

            # Проверяем есть ли лимит для этого отдела
            key = (branch, dept)
            limit_val = limits_dict.get(key)
            # Отдел имеет лимит если он установлен в настройках (независимо от текущего роста)
            has_limit = limit_val is not None

            preliminary_plans.append({
                'idx': idx,
                'fact': fact,
                'fact_original': fact_original,
                'role': role,
                'dept': dept,
                'prelim': prelim_plan,
                'weighted': weighted,
                'has_limit': has_limit,
                'limit_val': limit_val
            })

        # ====== ШАГ 2: Применяем лимиты, собираем излишек ======
        total_excess = 0

        for p in preliminary_plans:
            if p['has_limit'] and p['fact_original'] > 0:
                try:
                    limit_pct = int(p['limit_val'])
                    max_plan = p['fact_original'] * (1 + limit_pct / 100)

                    # Лимит отрезает сверху
                    if p['prelim'] > max_plan:
                        excess = p['prelim'] - max_plan
                        total_excess += excess
                        print(f"      ⚠️ ЛИМИТ {p['dept']}: {p['prelim']:,.0f} → {max_plan:,.0f} (−{excess:,.0f})")
                        p['prelim'] = max_plan

                    # ЗАЩИТА: план не может быть меньше факта (лимит только ограничивает рост!)
                    if p['prelim'] < p['fact_original']:
                        p['prelim'] = p['fact_original']

                    p['is_capped'] = True  # Отмечаем как зафиксированный (не участвует в перераспределении)
                except (ValueError, TypeError):
                    p['is_capped'] = False
            else:
                p['is_capped'] = False

        # ====== ШАГ 3: Перераспределяем излишек на отделы БЕЗ лимитов ======
        if total_excess > 0:
            # Отделы без лимитов (или с лимитом но не достигшие его)
            recipients = [p for p in preliminary_plans if not p['is_capped'] and not p['has_limit']]

            if recipients:
                sum_weights = sum(p['weighted'] for p in recipients)
                if sum_weights > 0:
                    for p in recipients:
                        share = p['weighted'] / sum_weights
                        p['prelim'] += total_excess * share

        # ====== ШАГ 4: Округляем и записываем ======
        new_plans = []
        limited_indices = set()

        for p in preliminary_plans:
            final_plan = round(p['prelim'] / rounding_step) * rounding_step
            final_plan = max(0, final_plan)

            # Финальная проверка для отделов с лимитом
            if p['has_limit'] and p['fact_original'] > 0:
                limited_indices.add(p['idx'])
                try:
                    limit_pct = int(p['limit_val'])
                    max_plan = p['fact_original'] * (1 + limit_pct / 100)
                    max_plan = round(max_plan / rounding_step) * rounding_step

                    # Ограничиваем сверху
                    if final_plan > max_plan:
                        final_plan = max_plan

                    # ЗАЩИТА: не ниже факта (округлённого)
                    min_plan = round(p['fact_original'] / rounding_step) * rounding_step
                    if final_plan < min_plan:
                        final_plan = min_plan

                except (ValueError, TypeError):
                    pass

            # DEBUG: Москва Хаб / Мебель
            if 'Хаб' in str(branch) and 'Мебель для дома' in str(p['dept']):
                print(f"   🔍 DEBUG МХ: {p['dept']}/{month} - fact_orig={p['fact_original']:,.0f}, final={final_plan:,.0f}, has_limit={p['has_limit']}")

            new_plans.append((p['idx'], final_plan))

            if debug_this:
                dept = g_orig.loc[p['idx'], 'Отдел']
                pct = (final_plan / p['fact'] - 1) * 100 if p['fact'] > 0 else 0
                role_mark = "📈" if p['role'] == 'Стратегический' else "📊"

        # Записываем
        for idx, plan in new_plans:
            self.df.loc[idx, 'План_Скорр'] = plan
            self.df.loc[idx, 'План_Расч'] = plan
            # DEBUG: Проверяем запись для Москва Хаб / Мебель
            if 'Хаб' in str(branch):
                dept_check = self.df.loc[idx, 'Отдел']
                if 'Мебель для дома' in str(dept_check):
                    print(f"   ✏️ ЗАПИСЬ МХ: {dept_check}/{month} = {plan:,.0f}")

        # ИЗМЕНЕНО: Лимиты НЕ применяются к строкам с ручными корректировками (Корр/Корр_Дельта)
        # Если пользователь вручную установил корректировку - это его решение,
        # лимит не должен её перезаписывать

        # Обнуление малых планов и перераспределение
        min_threshold = BUSINESS_RULES['MIN_PLAN_THRESHOLD']
        small_plans = [idx for idx in free_idx if 0 < self.df.loc[idx, 'План_Скорр'] < min_threshold]

        if small_plans:
            freed = sum(self.df.loc[idx, 'План_Скорр'] for idx in small_plans)
            for idx in small_plans:
                self.df.loc[idx, 'План_Скорр'] = 0
                self.df.loc[idx, 'План_Расч'] = 0

            # Перераспределяем на оставшиеся свободные отделы БЕЗ лимитов
            remaining_free = [idx for idx in free_idx
                             if idx not in small_plans
                             and idx not in limited_indices  # Не на лимитированные!
                             and self.df.loc[idx, 'План_Скорр'] > 0]
            if remaining_free and freed > 0:
                # Используем текущие планы как веса
                total_plan = sum(self.df.loc[idx, 'План_Скорр'] for idx in remaining_free)
                if total_plan > 0:
                    for idx in remaining_free:
                        w = self.df.loc[idx, 'План_Скорр'] / total_plan
                        add = round(freed * w / rounding_step) * rounding_step
                        self.df.loc[idx, 'План_Скорр'] += add
                        self.df.loc[idx, 'План_Расч'] += add

        # Корректировка сходимости - распределяем умно
        current_sum = self.df.loc[group_idx, 'План_Скорр'].sum()
        diff = target - current_sum

        if abs(diff) > 0:
            # Исключаем отделы с активными лимитами
            eligible_idx = [i for i in free_idx if i not in limited_indices]

            if eligible_idx and diff != 0:
                # Вычисляем максимальную добавку для каждого отдела (0.1% от факта)
                max_additions = {}
                for idx in eligible_idx:
                    fact = self.df_original.loc[idx, 'Выручка_2025']
                    if fact > 0:
                        max_add = fact * 0.001
                        max_add = round(max_add / rounding_step) * rounding_step
                        max_additions[idx] = max(rounding_step, max_add)

                remaining_diff = diff
                sign = 1 if diff > 0 else -1

                # Первый проход: распределяем по чуть-чуть на все отделы
                for idx in eligible_idx:
                    if abs(remaining_diff) < rounding_step:
                        break

                    max_add = max_additions.get(idx, rounding_step)
                    add_amount = min(max_add, abs(remaining_diff)) * sign

                    new_plan = self.df.loc[idx, 'План_Скорр'] + add_amount
                    # ЗАЩИТА: план не может быть меньше факта
                    fact_original = self.df_original.loc[idx, 'Выручка_2025']
                    if new_plan >= max(0, fact_original):
                        self.df.loc[idx, 'План_Скорр'] = new_plan
                        self.df.loc[idx, 'План_Расч'] = new_plan
                        remaining_diff -= add_amount

                # Второй проход: остаток на самый большой отдел
                if abs(remaining_diff) >= rounding_step:
                    if remaining_diff < 0:
                        # ЗАЩИТА: не уменьшаем план ниже факта!
                        can_decrease = [i for i in eligible_idx
                                       if self.df.loc[i, 'План_Скорр'] > abs(remaining_diff)
                                       and self.df.loc[i, 'План_Скорр'] + remaining_diff >= self.df_original.loc[i, 'Выручка_2025']]
                        if can_decrease:
                            max_idx = max(can_decrease, key=lambda i: self.df.loc[i, 'План_Скорр'])
                            self.df.loc[max_idx, 'План_Скорр'] += remaining_diff
                            self.df.loc[max_idx, 'План_Расч'] += remaining_diff
                    else:
                        positive_eligible = [i for i in eligible_idx if self.df.loc[i, 'План_Скорр'] > 0]
                        if positive_eligible:
                            max_idx = max(positive_eligible, key=lambda i: self.df.loc[i, 'План_Скорр'])
                            self.df.loc[max_idx, 'План_Скорр'] += remaining_diff
                            self.df.loc[max_idx, 'План_Расч'] += remaining_diff

        # DEBUG: Финальная проверка для Москва Хаб / Мебель
        if 'Хаб' in str(branch):
            for idx in group_idx:
                dept_check = self.df.loc[idx, 'Отдел']
                if 'Мебель для дома' in str(dept_check):
                    final_val = self.df.loc[idx, 'План_Скорр']
                    in_limited = idx in limited_indices
                    print(f"   ✅ ИТОГ МХ: {dept_check}/{month} = {final_val:,.0f}, in_limited={in_limited}")

    def _reset_elasticity(self, event=None):
        """Сбрасывает все коэффициенты в 1.0"""
        self._updating_elasticity = True
        try:

            # Сбрасываем ВСЕ слайдеры из словаря
            count = 0
            for key, sliders in self.elasticity_sliders.items():
                sliders['k_up'].value = 1.0
                sliders['k_down'].value = 1.0
                count += 1


            # Сохраняем (лист очистится, т.к. все = 1.0)
            self._save_elasticity_coefficients()


        except Exception as e:
            print(f"❌ Ошибка сброса: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._updating_elasticity = False

        # Применяем эластичность (с K=1.0 это просто применит корректировки и перераспределение)
        self._apply_elasticity()

    def _update_elastic_status(self):
        """Обновляет статус"""
        total_plan = self.df['План_Скорр'].sum()
        total_fact = self.df['Выручка_2025'].sum()
        target = self.df.groupby(['Филиал', 'Месяц'])['План'].first().sum()
        diff = total_plan - target

        diff_color = '#1a9850' if abs(diff) < 100000 else '#d73027'
        growth = (total_plan / total_fact - 1) * 100 if total_fact > 0 else 0

        # Считаем изменённые
        changed = sum(1 for key in self.elasticity_sliders
                     if self.elasticity_sliders[key]['k_up'].value != 1.0
                     or self.elasticity_sliders[key]['k_down'].value != 1.0)

        self.elastic_status.object = f"""
        <div style='font-size:10px;'>
            <b>План:</b> {total_plan/1e6:.0f}М |
            <b>Цель:</b> {target/1e6:.0f}М |
            <b>Δ:</b> <span style='color:{diff_color};'>{diff/1e6:+.0f}М</span> |
            <span style='color:#1a9850;'>▲{len(self._growth_branches)}</span>
            <span style='color:#d73027;'>▼{len(self._decline_branches)}</span> |
            Изменено: {changed}
        </div>
        """

    def _build_city_dept_limits_panel(self):
        """Строит панель с вкладками: Лимиты роста + Компрессор"""

        # Панель лимитов роста
        limits_panel = self._build_limits_table_panel()

        # Панель компрессора (с множителями прироста/падения)
        compressor_panel = self._build_compressor_panel()

        # ВАЖНО: Применяем загруженные лимиты к планам
        if self._branch_dept_limits:
            print(f"📊 Применяю {len(self._branch_dept_limits)} загруженных лимитов...")
            self._apply_loaded_limits()

        # Вкладки
        tabs = pn.Tabs(
            ('📊 Макс.рост', limits_panel),
            ('🎚️ Компрессор', compressor_panel),
            sizing_mode='stretch_width',
            tabs_location='above',
            stylesheets=[':host .bk-tab { font-size: 10px !important; padding: 4px 8px !important; }']
        )

        return tabs

    def _build_limits_table_panel(self):
        """Строит панель с таблицей лимитов макс. роста (Отдел × Филиал)"""

        # Определяем отделы и филиалы
        if 'Роль' in self.df.columns:
            accomp_mask = self.df['Роль'].isin(['Сопутствующий', 'Обои'])
            self._accompanying_depts = sorted(self.df[accomp_mask]['Отдел'].unique().tolist())
        else:
            self._accompanying_depts = sorted(self.df['Отдел'].unique().tolist())

        self._ordered_branches = sorted(self.df['Филиал'].unique().tolist())

        # Загружаем сохранённые лимиты
        self._load_city_dept_limits()

        # Создаём DataFrame для таблицы
        data = []
        for dept in self._accompanying_depts:
            row = {'Отдел': dept}
            for branch in self._ordered_branches:
                val = self._branch_dept_limits.get((branch, dept), '')
                row[branch] = str(val) if val != '' else ''
            data.append(row)

        limits_df = pd.DataFrame(data)

        # Настраиваем редакторы и форматтеры
        editors = {'Отдел': None}  # Отдел не редактируется
        widths = {'Отдел': 120}
        for branch in self._ordered_branches:
            editors[branch] = {'type': 'input', 'attributes': {'type': 'number'}}
            widths[branch] = 55

        # Создаём таблицу
        self._limits_table = pn.widgets.Tabulator(
            limits_df,
            height=180,
            sizing_mode='stretch_width',
            show_index=False,
            selectable=False,
            disabled=False,
            frozen_columns=['Отдел'],
            editors=editors,
            widths=widths,
            text_align={col: 'center' for col in self._ordered_branches},
            configuration={
                'columnDefaults': {'headerSort': False},
            },
            stylesheets=[
                ':host .tabulator-cell { font-size: 9px !important; padding: 2px !important; }',
                ':host .tabulator-col-title { font-size: 8px !important; }'
            ]
        )

        # Обработчик редактирования
        self._limits_table.on_edit(self._on_table_edit)
        self._limits_table.param.watch(self._on_limits_value_change, 'value')
        self._last_limits_df = limits_df.copy()

        # Кнопки
        apply_btn = pn.widgets.Button(name='▶', width=30, height=26, button_type='primary')
        apply_btn.on_click(lambda e: self._force_apply_limits())

        save_btn = pn.widgets.Button(name='💾', width=30, height=26, button_type='success')
        save_btn.on_click(lambda e: self._save_and_apply_limits())

        reset_btn = pn.widgets.Button(name='↺', width=30, height=26, button_type='warning')
        reset_btn.on_click(self._reset_limits)

        self._limits_status = pn.pane.HTML("", width=200, height=20)

        header = pn.Row(
            pn.pane.HTML("<b style='font-size:10px;'>Макс. прирост % по отделам:</b>", width=180),
            apply_btn,
            save_btn,
            reset_btn,
            self._limits_status,
            sizing_mode='stretch_width',
            align='center'
        )

        legend = pn.pane.HTML("""
        <div style='font-size:9px;color:#666;padding:3px;'>
            Введите макс. % прироста | <b>▶</b> применить | <b>💾</b> сохранить+применить | <b>↺</b> сброс
        </div>
        """)

        return pn.Column(
            header,
            self._limits_table,
            legend,
            sizing_mode='stretch_width',
            styles={'background': '#fff3e0', 'padding': '8px', 'border-radius': '5px'}
        )

    def _save_and_apply_limits(self):
        """Сохраняет лимиты в Sheets и применяет их"""
        # Сначала синхронизируем из таблицы
        self._sync_limits_from_table()
        # Сохраняем
        self._save_branch_dept_limits()
        # Применяем
        self._force_apply_limits()

    def _sync_limits_from_table(self):
        """Синхронизирует лимиты из таблицы UI в словарь"""
        if not hasattr(self, '_limits_table'):
            return

        table_df = self._limits_table.value
        if table_df is None:
            return

        print(f"📋 Синхронизация лимитов из таблицы...")
        self._branch_dept_limits = {}

        for idx, row in table_df.iterrows():
            dept = row['Отдел']
            for col in table_df.columns:
                if col == 'Отдел':
                    continue
                val = row[col]
                if val and str(val).strip():
                    try:
                        self._branch_dept_limits[(col, dept)] = int(val)
                        print(f"   📌 {col} / {dept}: {val}%")
                    except (ValueError, TypeError):
                        pass

        print(f"✅ Синхронизировано {len(self._branch_dept_limits)} лимитов")

    def _force_apply_limits(self):
        """Принудительно применяет лимиты ко всем филиалам"""
        if not self._branch_dept_limits:
            # Синхронизируем из таблицы если словарь пуст
            self._sync_limits_from_table()

        if not self._branch_dept_limits:
            self._limits_status.object = "<span style='color:orange;font-size:9px;'>Нет лимитов</span>"
            return

        print(f"\n{'='*60}")
        print(f"🔒 ПРИНУДИТЕЛЬНОЕ ПРИМЕНЕНИЕ ЛИМИТОВ ({len(self._branch_dept_limits)})")
        print(f"{'='*60}")

        # Собираем уникальные филиалы с лимитами
        branches_with_limits = set(branch for branch, dept in self._branch_dept_limits.keys())
        changes_count = 0

        for branch in branches_with_limits:
            months = self.df[self.df['Филиал'] == branch]['Месяц'].unique()
            for month in months:
                # Применяем лимиты
                before_count = len([idx for idx in self.df[(self.df['Филиал'] == branch) & (self.df['Месяц'] == month)].index])
                self._apply_limits_for_group(branch, month)

        # Обновляем UI через _after_correction_change (включает специальные правила)
        self._cached_filtered_df = None
        self._cached_agg = None
        self._after_correction_change()

        self._limits_status.object = f"<span style='color:green;font-size:9px;'>✅ Лимиты применены</span>"
        print(f"✅ Лимиты применены")

    def _reset_limits(self, event):
        """Сбрасывает все лимиты и пересчитывает"""
        self._branch_dept_limits = {}
        self._update_limits_table()

        # Очищаем базу компрессора (она пересчитается при следующем изменении)
        if hasattr(self, '_compressor_row_base'):
            self._compressor_row_base = {}
        if hasattr(self, '_compressor_base'):
            self._compressor_base = {}

        # Пересчитываем все филиалы
        for branch in self.df['Филиал'].unique():
            for month in range(1, 13):
                self._redistribute_group(branch, month)

        self._cached_filtered_df = None
        self._cached_agg = None

        # Применяем специальные правила и обновляем UI
        self._after_correction_change()

        self._limits_status.object = "<span style='color:blue;font-size:9px;'>Лимиты сброшены</span>"

    def _build_compressor_panel(self):
        """Строит панель компрессора планов с множителями прироста и падения"""

        # Загружаем сохранённые настройки компрессора
        self._loaded_compressor_settings = self._load_compressor()

        # Селектор филиала
        branches = sorted(self.df['Филиал'].unique().tolist())
        self._compressor_branch_select = pn.widgets.Select(
            name='', options=['Все'] + branches, value='Все',
            width=150, height=28
        )

        # Словарь слайдеров: {(branch, dept): {'growth': slider, 'decline': slider}}
        self._compressor_sliders = {}

        # Статус
        self._compressor_status = pn.pane.HTML("", width=300, height=20)

        # Контейнер для слайдеров
        self._compressor_content = pn.Column(sizing_mode='stretch_width')

        # Обновляем при смене филиала
        self._compressor_branch_select.param.watch(self._rebuild_compressor_sliders, 'value')

        # Кнопка сброса
        reset_btn = pn.widgets.Button(name='↺ Сброс', width=60, height=28, button_type='warning')
        reset_btn.on_click(self._reset_compressor)

        # Кнопка сохранения
        save_btn = pn.widgets.Button(name='💾', width=30, height=28, button_type='success')
        save_btn.on_click(lambda e: self._save_compressor())

        # Кнопка применения
        apply_btn = pn.widgets.Button(name='▶', width=30, height=28, button_type='primary')
        apply_btn.on_click(lambda e: self._apply_compressor())

        header = pn.Row(
            pn.pane.HTML("<b style='font-size:10px;'>🎚️ Множители:</b>", width=80),
            self._compressor_branch_select,
            apply_btn,
            reset_btn,
            save_btn,
            self._compressor_status,
            sizing_mode='stretch_width',
            align='center'
        )

        legend = pn.pane.HTML("""
        <div style='font-size:9px;color:#666;padding:3px;'>
            <span style='color:#4CAF50'>📈 Прирост</span>: ×1.5 → +20% станет +30% |
            <span style='color:#f44336'>📉 Падение</span>: ×0.5 → -20% станет -10%
        </div>
        """)

        # Инициализируем слайдеры
        self._rebuild_compressor_sliders(None)

        # Применяем загруженные настройки после создания слайдеров
        if self._loaded_compressor_settings:
            self._apply_loaded_compressor(self._loaded_compressor_settings)
            # ВАЖНО: Применяем настройки к данным при загрузке дашборда
            self._apply_compressor_on_load()

        return pn.Column(
            header,
            pn.Column(self._compressor_content, scroll=True, height=300, sizing_mode='stretch_width',
                     styles={'border': '1px solid #ccc', 'border-radius': '3px'}),
            legend,
            sizing_mode='stretch_width',
            styles={'background': '#e8f5e9', 'padding': '8px', 'border-radius': '5px'}
        )

    def _rebuild_compressor_sliders(self, event):
        """Перестраивает слайдеры компрессора - два слайдера (прирост/падение) для каждого отдела"""
        branch = self._compressor_branch_select.value

        # Фильтруем данные
        if branch == 'Все':
            df = self.df.copy()
        else:
            df = self.df[self.df['Филиал'] == branch].copy()

        if len(df) == 0:
            self._compressor_content[:] = [pn.pane.HTML("<div>Нет данных</div>")]
            return

        # Группируем по отделам
        agg_dict = {
            'Выручка_2025': 'sum',
            'План_Скорр': 'sum',
        }

        yearly = df.groupby('Отдел').agg(agg_dict).reset_index()
        yearly = yearly.sort_values('Отдел', ascending=True)  # Сортировка по алфавиту

        rows = []
        self._compressor_sliders = {}

        for _, row in yearly.iterrows():
            dept = row['Отдел']
            fact = row['Выручка_2025']
            plan = row['План_Скорр']

            # Средний прирост по отделу
            avg_growth = ((plan / fact - 1) * 100) if fact > 0 else 0

            # Загруженные значения компрессора
            loaded_settings = getattr(self, '_loaded_compressor_settings', {})
            loaded_vals = loaded_settings.get((branch, dept), {})
            init_growth = loaded_vals.get('growth', 1.0)
            init_decline = loaded_vals.get('decline', 1.0)

            # Слайдер ПРИРОСТ — от 0.0 до 2.0
            slider_growth = pn.widgets.FloatSlider(
                name='',
                value=init_growth,
                start=0.0, end=2.0, step=0.01,
                width=150,
                bar_color='#4CAF50',
                format='0.00',
                stylesheets=[':host .bk-slider-title { display: none; }']
            )

            # Слайдер ПАДЕНИЕ — от 0.0 до 2.0
            slider_decline = pn.widgets.FloatSlider(
                name='',
                value=init_decline,
                start=0.0, end=2.0, step=0.01,
                width=150,
                bar_color='#f44336',
                format='0.00',
                stylesheets=[':host .bk-slider-title { display: none; }']
            )

            # Сохраняем метаданные
            key = (branch, dept)
            self._compressor_sliders[key] = {
                'slider_growth': slider_growth,
                'slider_decline': slider_decline,
                'avg_growth': avg_growth,
                'dept': dept,
                'branch': branch
            }

            # Короткое имя отдела
            short_dept = dept[:20] + '..' if len(dept) > 20 else dept

            # Метки
            dept_label = pn.pane.HTML(
                f"<div style='font-size:9px;width:150px;overflow:hidden;text-overflow:ellipsis;' title='{dept}'>{short_dept}</div>",
                width=155
            )

            growth_color = '#4CAF50' if avg_growth >= 0 else '#F44336'
            avg_label = pn.pane.HTML(
                f"<div style='font-size:9px;text-align:right;color:{growth_color};'>{avg_growth:+.0f}%</div>",
                width=35
            )

            # Метки значений слайдеров
            growth_val_label = pn.pane.HTML(
                f"<div style='font-size:9px;color:#4CAF50;font-weight:bold;'>×{init_growth:.2f}</div>",
                width=35
            )
            decline_val_label = pn.pane.HTML(
                f"<div style='font-size:9px;color:#f44336;font-weight:bold;'>×{init_decline:.2f}</div>",
                width=35
            )

            self._compressor_sliders[key]['growth_label'] = growth_val_label
            self._compressor_sliders[key]['decline_label'] = decline_val_label

            # Обработчики изменения
            slider_growth.param.watch(
                lambda e, k=key: self._on_compressor_slider_change(e, k, 'growth'),
                'value_throttled'
            )
            slider_decline.param.watch(
                lambda e, k=key: self._on_compressor_slider_change(e, k, 'decline'),
                'value_throttled'
            )

            row_widget = pn.Row(
                dept_label, avg_label,
                pn.pane.HTML("<span style='font-size:8px;color:#4CAF50;'>📈</span>", width=15),
                slider_growth, growth_val_label,
                pn.pane.HTML("<span style='font-size:8px;color:#f44336;'>📉</span>", width=15),
                slider_decline, decline_val_label,
                sizing_mode='stretch_width',
                styles={'border-bottom': '1px solid #eee', 'padding': '2px 0'}
            )
            rows.append(row_widget)

        # Заголовок
        header_row = pn.Row(
            pn.pane.HTML("<div style='font-size:8px;font-weight:bold;'>Отдел</div>", width=125),
            pn.pane.HTML("<div style='font-size:8px;text-align:right;'>Δ%</div>", width=35),
            pn.pane.HTML("<div style='font-size:8px;text-align:center;color:#4CAF50;'>← Прирост ×</div>", width=130),
            pn.pane.HTML("<div style='font-size:8px;text-align:center;color:#f44336;'>← Падение ×</div>", width=130),
            sizing_mode='stretch_width',
            styles={'border-bottom': '2px solid #999', 'background': '#f5f5f5', 'padding': '2px'}
        )

        self._compressor_content[:] = [header_row] + rows
        self._update_compressor_status()

    def _on_compressor_slider_change(self, event, key, slider_type):
        """Обработчик изменения слайдера компрессора"""
        if key not in self._compressor_sliders:
            return

        val = event.new

        # Обновляем метку
        if slider_type == 'growth':
            self._compressor_sliders[key]['growth_label'].object = f"<div style='font-size:9px;color:#4CAF50;font-weight:bold;'>×{val:.2f}</div>"
        else:
            self._compressor_sliders[key]['decline_label'].object = f"<div style='font-size:9px;color:#f44336;font-weight:bold;'>×{val:.2f}</div>"

        self._update_compressor_status()

    def _reset_compressor(self, event):
        """Сбрасывает все слайдеры компрессора на 1.0"""
        if getattr(self, '_updating_compressor', False):
            return

        try:
            self._updating_compressor = True
            branch = self._compressor_branch_select.value

            for key, data in self._compressor_sliders.items():
                if key[0] == branch or branch == 'Все':
                    # Сбрасываем слайдеры на 1.0
                    if 'slider_growth' in data:
                        data['slider_growth'].value = 1.0
                    if 'slider_decline' in data:
                        data['slider_decline'].value = 1.0
                    if 'growth_label' in data:
                        data['growth_label'].object = "<div style='font-size:9px;color:#4CAF50;font-weight:bold;'>×1.00</div>"
                    if 'decline_label' in data:
                        data['decline_label'].object = "<div style='font-size:9px;color:#f44336;font-weight:bold;'>×1.00</div>"

            self._compressor_status.object = "<span style='color:blue;font-size:9px;'>Сброшено на ×1.0</span>"
        finally:
            self._updating_compressor = False

    def _update_compressor_status(self):
        """Обновляет общий статус компрессора"""
        # Считаем отклонения от 1.0
        changed_growth = 0
        changed_decline = 0
        for key, data in self._compressor_sliders.items():
            if 'slider_growth' in data and data['slider_growth'].value != 1.0:
                changed_growth += 1
            if 'slider_decline' in data and data['slider_decline'].value != 1.0:
                changed_decline += 1

        if changed_growth > 0 or changed_decline > 0:
            self._compressor_status.object = f"<span style='font-size:9px;'><span style='color:#4CAF50;'>📈{changed_growth}</span> <span style='color:#f44336;'>📉{changed_decline}</span></span>"
        else:
            self._compressor_status.object = ""

    def _on_limits_value_change(self, event):
        """Альтернативный обработчик изменений таблицы лимитов через param.watch"""
        if getattr(self, '_updating_limits', False):
            return
        if not hasattr(self, '_last_limits_df'):
            self._last_limits_df = event.old.copy() if event.old is not None else None
            return

        old_df = self._last_limits_df
        new_df = event.new

        if old_df is None or new_df is None:
            self._last_limits_df = new_df.copy() if new_df is not None else None
            return

        # Ищем ВСЕ изменения (не только первое!)
        changes = []
        try:
            for col in new_df.columns:
                if col == 'Отдел':
                    continue
                for idx in new_df.index:
                    old_val = old_df.loc[idx, col] if idx in old_df.index else ''
                    new_val = new_df.loc[idx, col]
                    if str(old_val) != str(new_val):
                        dept = new_df.loc[idx, 'Отдел']
                        changes.append((idx, col, new_val, dept))

            # Обрабатываем все изменения
            if changes:
                print(f"🔔 param.watch: найдено {len(changes)} изменений")
                for idx, col, new_val, dept in changes:
                    print(f"   📌 {col} / {dept}: {new_val}")

                    # Обновляем словарь напрямую (без вызова _on_table_edit чтобы избежать дублирования)
                    key = (col, dept)
                    if new_val and str(new_val).strip():
                        try:
                            self._branch_dept_limits[key] = int(new_val)
                        except (ValueError, TypeError):
                            pass
                    else:
                        if key in self._branch_dept_limits:
                            del self._branch_dept_limits[key]

                    # Добавляем филиал в очередь на пересчёт
                    if not hasattr(self, '_pending_recalc_branches'):
                        self._pending_recalc_branches = set()
                    self._pending_recalc_branches.add(col)

                # Запускаем один отложенный пересчёт для всех изменений
                if hasattr(self, '_recalc_timer') and self._recalc_timer:
                    self._recalc_timer.cancel()

                import threading
                self._recalc_timer = threading.Timer(0.5, self._do_deferred_recalc)
                self._recalc_timer.start()

        except Exception as e:
            print(f"⚠️ Ошибка в param.watch: {e}")
            import traceback
            traceback.print_exc()

        self._last_limits_df = new_df.copy()

    def _on_table_edit(self, event):
        """Обработчик редактирования таблицы лимитов - с debounce"""
        print(f"🔔 _on_table_edit ВЫЗВАН! event={event}")

        # Защита от рекурсии
        if getattr(self, '_updating_limits', False):
            print(f"   ⚠️ Пропуск: _updating_limits=True")
            return

        try:
            row_idx = event.row
            branch = event.column
            new_val = event.value

            print(f"   📌 row={row_idx}, column={branch}, value={new_val}")

            # Пропускаем редактирование колонки "Отдел"
            if branch == 'Отдел':
                print(f"   ⚠️ Пропуск: колонка Отдел")
                return

            # Получаем полное имя отдела
            table_df = self._limits_table.value
            if row_idx >= len(table_df):
                return

            dept_full = table_df.iloc[row_idx]['Отдел']

            # Обновляем словарь лимитов (быстро, без пересчёта)
            key = (branch, dept_full)
            old_val = self._branch_dept_limits.get(key)

            print(f"📝 Редактирование лимита: {branch} / {dept_full} = {new_val} (было: {old_val})")

            if new_val and str(new_val).strip():
                try:
                    int_val = int(new_val)
                    if old_val == int_val:
                        return
                    self._branch_dept_limits[key] = int_val
                except ValueError:
                    return
            else:
                if key not in self._branch_dept_limits:
                    return
                del self._branch_dept_limits[key]

            # Добавляем филиал в очередь на пересчёт
            if not hasattr(self, '_pending_recalc_branches'):
                self._pending_recalc_branches = set()
            self._pending_recalc_branches.add(branch)

            # Отменяем предыдущий таймер если есть
            if hasattr(self, '_recalc_timer') and self._recalc_timer:
                self._recalc_timer.cancel()

            # Запускаем отложенный пересчёт через 500ms
            import threading
            self._recalc_timer = threading.Timer(0.5, self._do_deferred_recalc)
            self._recalc_timer.start()
            print(f"   ⏱️ Таймер пересчёта запущен (0.5с)")

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()

    def _do_deferred_recalc(self):
        """Отложенный пересчёт после debounce"""
        if getattr(self, '_updating_limits', False):
            return

        try:
            self._updating_limits = True

            branches = getattr(self, '_pending_recalc_branches', set())
            if not branches:
                return

            print(f"🔄 Пересчёт: {len(branches)} филиал(ов)...")

            # Очищаем базу компрессора (она пересчитается при следующем изменении)
            if hasattr(self, '_compressor_row_base'):
                self._compressor_row_base = {}
            if hasattr(self, '_compressor_base'):
                self._compressor_base = {}

            # Сохраняем в Google Sheets (один раз)
            try:
                self._save_branch_dept_limits()
            except:
                pass

            # Пересчитываем только нужные филиалы
            for branch in branches:
                # Только выбранные месяцы
                selected_months = self.filters['month']['select'].value if 'month' in self.filters else []
                print(f"   📅 {branch}: selected_months={selected_months}")
                if selected_months:
                    month_nums = [MONTH_MAP.get(m, m) for m in selected_months]
                    months = [m for m in self.df[self.df['Филиал'] == branch]['Месяц'].unique()
                             if m in month_nums]
                else:
                    months = list(self.df[self.df['Филиал'] == branch]['Месяц'].unique())

                print(f"   📅 Месяцы для пересчёта: {months}")

                for month in months:
                    self._redistribute_group(branch, month)

                    # ВАЖНО: Применяем лимиты ПОСЛЕ распределения
                    self._apply_limits_for_group(branch, month)

            # Применяем специальные правила (Двери, Мебель для кухни)
            self._apply_special_rules()

            # Очищаем очередь
            self._pending_recalc_branches = set()

            # Сбрасываем кеш
            self._cached_filtered_df = None
            self._cached_agg = None

            # Обновляем UI (через pn.io для thread-safety)
            try:
                import panel as pn
                print(f"   📊 Обновляю UI...")
                # Пробуем разные способы обновления
                if hasattr(pn.state, 'curdoc') and pn.state.curdoc:
                    pn.state.curdoc.add_next_tick_callback(self._update_ui_after_recalc)
                elif hasattr(pn, 'io') and hasattr(pn.io, 'unlocked'):
                    with pn.io.unlocked():
                        self._update_ui_after_recalc()
                else:
                    self._update_ui_after_recalc()
                print(f"   ✅ UI обновлён")
            except Exception as ui_err:
                print(f"   ⚠️ Ошибка обновления UI: {ui_err}")
                # Пробуем напрямую
                try:
                    self._update_ui_after_recalc()
                except:
                    pass

        except Exception as e:
            print(f"❌ Ошибка пересчёта: {e}")
        finally:
            self._updating_limits = False

    def _apply_limits_for_group(self, branch, month):
        """Применяет лимиты роста для конкретной группы (филиал, месяц)"""
        if not self._branch_dept_limits:
            print(f"   ⚠️ _apply_limits_for_group: нет лимитов")
            return

        gm = (self.df['Филиал'] == branch) & (self.df['Месяц'] == month)
        if not gm.any():
            return

        print(f"   🔧 Применяю лимиты для {branch} / месяц {month}")
        print(f"   📋 Доступные лимиты ({len(self._branch_dept_limits)}): {list(self._branch_dept_limits.keys())[:5]}...")

        rounding_step = CONFIG.get('rounding_step', 10000)
        total_excess = 0
        limited_indices = []

        # Шаг 1: Применяем лимиты и считаем излишек
        for idx in self.df[gm].index:
            dept = self.df.loc[idx, 'Отдел']
            key = (branch, dept)

            # DEBUG: показываем какие ключи проверяем
            if key in self._branch_dept_limits:
                print(f"      ✓ Ключ найден: {key}")

            if key not in self._branch_dept_limits:
                continue

            # Пропускаем строки с ручными корректировками
            has_corr = pd.notna(self.df.loc[idx, 'Корр']) or pd.notna(self.df.loc[idx, 'Корр_Дельта'])
            if has_corr:
                print(f"      ⏭️ Пропуск {dept}: есть ручная корректировка")
                continue

            max_growth = self._branch_dept_limits[key]
            fact = self.df.loc[idx, 'Выручка_2025']
            if fact <= 0:
                continue

            max_plan = fact * (1 + max_growth / 100)
            current_plan = self.df.loc[idx, 'План_Скорр']
            current_growth = ((current_plan / fact) - 1) * 100 if fact > 0 else 0

            print(f"      📊 {dept}: факт={fact:,.0f}, план={current_plan:,.0f} ({current_growth:+.1f}%), лимит={max_growth}%, макс_план={max_plan:,.0f}")

            if current_plan > max_plan:
                excess = current_plan - max_plan
                total_excess += excess

                # Округляем max_plan
                max_plan_rounded = round(max_plan / rounding_step) * rounding_step

                self.df.loc[idx, 'План_Скорр'] = max_plan_rounded
                self.df.loc[idx, 'План_Расч'] = max_plan_rounded
                self.df.loc[idx, 'Рекоменд'] = max_plan_rounded
                # ВАЖНО: обновляем df_original чтобы _apply_elasticity не перезаписала!
                if hasattr(self, 'df_original') and self.df_original is not None:
                    self.df_original.loc[idx, 'План_Скорр'] = max_plan_rounded
                    self.df_original.loc[idx, 'План_Расч'] = max_plan_rounded
                    self.df_original.loc[idx, 'Рекоменд'] = max_plan_rounded
                limited_indices.append(idx)
                print(f"      🔒 ЛИМИТ ПРИМЕНЁН: {current_plan:,.0f} → {max_plan_rounded:,.0f} (−{excess:,.0f})")

        # Шаг 2: Перераспределяем излишек на стратегические отделы БЕЗ лимитов
        if total_excess > 0:
            strategic_mask = gm & (self.df['Роль'] == 'Стратегический') & (self.df['Правило'] != 'Не считаем план')
            # Исключаем отделы с лимитами и с корректировками
            for idx in self.df[strategic_mask].index:
                dept = self.df.loc[idx, 'Отдел']
                key = (branch, dept)
                has_corr = pd.notna(self.df.loc[idx, 'Корр']) or pd.notna(self.df.loc[idx, 'Корр_Дельта'])
                if key in self._branch_dept_limits or has_corr:
                    strategic_mask.loc[idx] = False

            if strategic_mask.any():
                weights = self.df.loc[strategic_mask, 'Final_Weight']
                weights_sum = weights.sum()
                if weights_sum > 0:
                    for idx in self.df[strategic_mask].index:
                        share = self.df.loc[idx, 'Final_Weight'] / weights_sum
                        add_amount = total_excess * share
                        # Округляем
                        new_plan = self.df.loc[idx, 'План_Скорр'] + add_amount
                        new_plan = round(new_plan / rounding_step) * rounding_step
                        self.df.loc[idx, 'План_Скорр'] = new_plan
                        self.df.loc[idx, 'План_Расч'] = new_plan
                        self.df.loc[idx, 'Рекоменд'] = new_plan  # ВАЖНО: обновляем и Рекоменд!
                        # ВАЖНО: обновляем df_original чтобы _apply_elasticity не перезаписала!
                        if hasattr(self, 'df_original') and self.df_original is not None:
                            self.df_original.loc[idx, 'План_Скорр'] = new_plan
                            self.df_original.loc[idx, 'План_Расч'] = new_plan
                            self.df_original.loc[idx, 'Рекоменд'] = new_plan

        # Пересчитываем метрики для ВСЕЙ группы (не только ограниченных)
        if limited_indices or total_excess > 0:
            recalc_row_metrics(self.df, gm, self.cols_available)
            if hasattr(self, 'df_original') and self.df_original is not None:
                recalc_row_metrics(self.df_original, gm, self.cols_available)

    def _update_ui_after_recalc(self):
        """Обновление UI после пересчёта"""
        try:
            # Принудительно сбрасываем кеш
            self._cached_filtered_df = None
            self._cached_agg = None

            # DEBUG: Проверка равенства Корр и План_Скорр
            self._debug_check_corr_vs_plan()

            new_df = self._get_display_df()
            print(f"   📊 Обновляю таблицу: {len(new_df)} строк")
            self.table.value = new_df
            self._update_indicators()
            # Графики НЕ обновляем автоматически - слишком медленно
        except Exception as e:
            print(f"⚠️ Ошибка обновления UI: {e}")
            import traceback
            traceback.print_exc()

    def _debug_check_corr_vs_plan(self):
        """Проверяет что План_Скорр == Корр (+ Дельта) для строк с корректировками"""
        print(f"\n{'='*60}")
        print(f"🔍 DEBUG: Проверка Корр vs План_Скорр")
        print(f"{'='*60}")

        # Находим строки с корректировками
        has_corr = self.df['Корр'].notna()
        corr_rows = self.df[has_corr]

        if corr_rows.empty:
            print("   Нет строк с корректировками")
            return

        mismatches = []
        for idx in corr_rows.index:
            branch = self.df.loc[idx, 'Филиал']
            dept = self.df.loc[idx, 'Отдел']
            month = self.df.loc[idx, 'Месяц']
            corr = self.df.loc[idx, 'Корр']
            delta = self.df.loc[idx, 'Корр_Дельта']
            plan = self.df.loc[idx, 'План_Скорр']

            # Ожидаемый план = Корр + Дельта (если дельта есть)
            expected = corr + (delta if pd.notna(delta) else 0)
            expected = max(0, expected)

            # Проверяем совпадение (с погрешностью 1 рубль)
            if abs(plan - expected) > 1:
                mismatches.append({
                    'branch': branch,
                    'dept': dept,
                    'month': month,
                    'corr': corr,
                    'delta': delta,
                    'expected': expected,
                    'actual': plan,
                    'diff': plan - expected
                })

        if mismatches:
            print(f"   ❌ НАЙДЕНО РАСХОЖДЕНИЙ: {len(mismatches)}")
            for m in mismatches[:10]:  # Показываем первые 10
                delta_str = f"+{m['delta']:,.0f}" if pd.notna(m['delta']) else ""
                print(f"      {m['branch']} / {m['dept']} / мес.{m['month']}:")
                print(f"         Корр={m['corr']:,.0f}{delta_str} → ожидали {m['expected']:,.0f}, получили {m['actual']:,.0f} (Δ={m['diff']:+,.0f})")
            if len(mismatches) > 10:
                print(f"      ... и ещё {len(mismatches) - 10} расхождений")
        else:
            print(f"   ✅ Все {len(corr_rows)} строк с корректировками совпадают!")

        print(f"{'='*60}\n")

    def _refresh_charts(self, event=None):
        """Ручное обновление графиков"""
        try:
            self._update_charts()
            self._update_compact_stats()
            print("✅ Графики обновлены")
        except Exception as e:
            print(f"⚠️ Ошибка обновления графиков: {e}")

    def _update_limits_table(self):
        """Обновляет DataFrame в таблице лимитов"""
        if not hasattr(self, '_limits_table') or not hasattr(self, '_ordered_branches'):
            return

        try:
            # Пересоздаём DataFrame с актуальными значениями
            data = []
            for dept in self._accompanying_depts:
                row = {'Отдел': dept}
                for branch in self._ordered_branches:
                    val = self._branch_dept_limits.get((branch, dept), '')
                    row[branch] = str(val) if val != '' else ''
                data.append(row)

            new_df = pd.DataFrame(data)
            self._limits_table.value = new_df
        except Exception as e:
            print(f"⚠️ Ошибка обновления таблицы лимитов: {e}")

    def _build_elasticity_panel(self):
        """Строит компактную матрицу слайдеров: строки=отделы, столбцы=филиалы"""

        # Заголовок: филиалы (фиксированный при прокрутке)
        header_cells = [pn.pane.HTML(
            "<div style='font-size:8px;font-weight:bold;padding:1px;background:#fafafa;'></div>",
            width=90, sizing_mode='fixed'
        )]
        for branch in self.elastic_branches:
            # Сокращаем длинные названия филиалов
            short_branch = branch[:10] + '..' if len(branch) > 10 else branch
            header_cells.append(pn.pane.HTML(
                f"<div style='text-align:center;padding:1px;font-size:7px;background:#fafafa;'>"
                f"<b>{short_branch}</b></div>",
                sizing_mode='stretch_width',
                min_width=50,
                margin=(0, 2)
            ))
        header_row = pn.Row(*header_cells, sizing_mode='stretch_width',
                           styles={'border-bottom': '2px solid #999', 'background': '#fafafa'})

        # Строки по отделам
        data_rows = []
        for i, dept in enumerate(self.elastic_depts):
            short_name = dept[:12] + '..' if len(dept) > 12 else dept
            bg_color = '#fff' if i % 2 == 0 else '#f8f8f8'

            row_cells = [pn.pane.HTML(
                f"<div style='font-size:8px;padding:1px;background:{bg_color};"
                f"border-bottom:1px solid #eee;height:30px;display:flex;align-items:center;'>{short_name}</div>",
                width=90, sizing_mode='fixed'
            )]

            for branch in self.elastic_branches:
                key = (dept, branch)
                slider_up = self.elasticity_sliders[key]['k_up']
                slider_down = self.elasticity_sliders[key]['k_down']

                cell = pn.Column(
                    slider_up,
                    slider_down,
                    sizing_mode='stretch_width',
                    margin=(0, 2),  # Отступ 2px слева и справа (компактнее)
                    styles={'background': bg_color, 'border-bottom': '1px solid #eee', 'padding': '1px'}
                )
                row_cells.append(cell)

            data_rows.append(pn.Row(*row_cells, sizing_mode='stretch_width'))

        # Легенда
        legend = pn.pane.HTML("""
        <div style='font-size:8px;color:#666;padding:2px;background:#f5f5f5;'>
            0=только факт, 1=норма, 2=×2 доля | 🟢рост 🔴падение
        </div>
        """, sizing_mode='stretch_width')

        # Кнопки управления эластичностью
        elastic_controls = pn.Row(
            self.reset_elastic_btn,
            self.save_elastic_btn,
            pn.Spacer(width=10),
            self.elastic_status,
            sizing_mode='stretch_width',
            align='center',
            height=22
        )

        return pn.Column(
            elastic_controls,
            pn.pane.HTML("<div style='font-size:10px;font-weight:bold;margin-bottom:5px;'>📈 Тонкая настройка стратегических отделов</div>"),
            header_row,
            pn.Column(*data_rows, scroll=True, height=90, sizing_mode='stretch_width',
                      styles={'border': '1px solid #ccc', 'border-radius': '2px'}),
            legend,
            sizing_mode='stretch_width',
            styles={'padding': '3px', 'background': '#fafafa'}
        )

    # ========== View ==========

    def view(self):
        """Главный метод отображения дашборда"""
        # CSS стили для дашборда
        filter_css = pn.pane.HTML("""
        <style>
        .bk-root .bk-input-group { margin-bottom: 10px; }
        .bk-root .bk-btn { font-size: 13px; }
        .sidebar_box { background: #f9f9f9; padding: 10px; border-radius: 5px; border: 1px solid #eee; }
        </style>
        """, width=0, height=0, margin=0, sizing_mode='fixed')

        # Подсказка для фильтров
        filter_hint = pn.pane.HTML("<div style='color: #666; font-size: 12px; margin-bottom: 10px;'>*Используйте фильтры в панели ниже для обновления данных*</div>")

        # ВАЖНО: Сначала инициализируем панели
        self._update()
        self._update_indicators()
        self._update_compact_stats()

        url = f"https://docs.google.com/spreadsheets/d/{CONFIG['corrections_sheet_id']}/edit#gid={CONFIG['corrections_gid']}"

        def make_filter_col(key):
            f = self.filters[key]
            return pn.Column(
                pn.Row(f['select'], f['reset'], align='start', sizing_mode='stretch_width'),
                f['indicator'],
                sizing_mode='stretch_width',
                margin=(0, 5)
            )

        def on_debug(e):
            """Кнопка отладки: показывает текущие значения фильтров"""
            vals = {}
            for k, f in self.filters.items():
                vals[k] = f['select'].value
            import json
            msg = json.dumps(vals, ensure_ascii=False, indent=2)
            self.status.object = f"<pre style='font-size:9px;max-height:200px;overflow:auto;'>{msg}</pre>"
            print(f"\n🐞 DEBUG FILTER VALUES:\n{msg}")

        debug_btn = pn.widgets.Button(name='🐞 Debug', width=60, button_type='light')
        debug_btn.on_click(on_debug)

        # Фильтры в GridBox
        filters_grid = pn.GridBox(
            make_filter_col('branch'),
            make_filter_col('dept'),
            make_filter_col('format'),
            make_filter_col('month'),
            make_filter_col('role'),
            make_filter_col('rule'),
            ncols=3,
            sizing_mode='stretch_width'
        )

        filters_block = pn.Column(
            filter_hint,
            filters_grid,
            sizing_mode='stretch_width',
            styles={'padding': '5px', 'background': '#fafafa', 'border': '1px solid #eee', 'border-radius': '5px'}
        )

        # Графики
        charts_row = pn.Row(
            pn.Column(
                pn.pane.HTML("<b style='font-size:11px;'>📈 Сезонность</b>", height=15),
                self.chart_pane,
                sizing_mode='stretch_width'
            ),
            pn.Column(
                pn.pane.HTML("<b style='font-size:11px;'>📊 Отделы</b>", height=15),
                self.chart_depts_pane,
                sizing_mode='stretch_width'
            ),
            pn.Column(
                pn.pane.HTML("<b style='font-size:11px;'>🏢 Филиалы</b>", height=15),
                self.chart_branches_pane,
                sizing_mode='stretch_width'
            ),
            sizing_mode='stretch_width'
        )

        # Слайдеры (если есть)
        def toggle_sliders(event):
            self._sliders_container.visible = not self._sliders_container.visible
            self._sliders_btn.name = '📉 Скрыть K' if self._sliders_container.visible else '📈 K-коэфф'

        self._sliders_btn = pn.widgets.Button(name='📈 K-коэфф', width=80, button_type='light')
        self._sliders_btn.on_click(toggle_sliders)

        sliders_content = self._get_elasticity_panel() if hasattr(self, '_get_elasticity_panel') else pn.pane.HTML("")
        self._sliders_container = pn.Column(sliders_content, visible=False, sizing_mode='stretch_width')

        # Заголовок
        header_row = pn.Row(
            pn.pane.HTML("<b style='font-size: 14px;'>📊 План 2026</b>", width=120),
            self.status,
            self.compact_stats,
            debug_btn,
            pn.Spacer(width=10),
            self.export_btn,
            pn.Spacer(width=5),
            pn.pane.HTML(f'<a href="{url}" target="_blank" style="font-size:10px;">📋</a>', width=25),
            pn.Spacer(width=10),
            self._sliders_btn,
            sizing_mode='stretch_width',
            align='center',
            height=30,
            styles={'background': '#f5f5f5', 'border-bottom': '1px solid #ddd', 'padding': '2px 8px'}
        )

        # Увеличиваем высоту статуса
        self.status.height = 30
        self.status.sizing_mode = 'stretch_width'

        return pn.Column(
            filter_css,
            header_row,
            self._sliders_container,
            filters_block,
            charts_row,
            self.table,
            sizing_mode='stretch_width'
        )


# ============================================================================
# ЗАПУСК (ИСПОЛНЯЕМЫЙ КОД)
# ============================================================================

# Загрузка ролей отделов
df_roles = pd.read_csv('https://docs.google.com/spreadsheets/d/1yPANhEDRwf_CKMLLz5Wdov4Tx8HCgfS0ckyW7jv1ugQ/export?format=csv&gid=93699808')

# Загрузка правил структуры (ВСЕГДА свежие данные!)
import time
cache_buster = int(time.time())
df_rules_structure = pd.read_csv(f'https://docs.google.com/spreadsheets/d/1yPANhEDRwf_CKMLLz5Wdov4Tx8HCgfS0ckyW7jv1ugQ/export?format=csv&gid=2130598218&_={cache_buster}')

# Преобразование плана 2026 из wide в long формат
if 'Месяц' not in df_plan_2026.columns:
    df_plan_2026 = df_plan_2026.melt(
        id_vars=['Филиал'],
        var_name='Месяц',
        value_name='План'
    )

# Нормализация
df_plan_2026['Месяц'] = df_plan_2026['Месяц'].astype(str).str.strip().str.lower()
df_plan_2026['Филиал'] = df_plan_2026['Филиал'].astype(str).str.strip()

# Подготовка данных
df_clean = prepare_baseline(df_sales_2023_2025, df_area)

df_weights = calculate_planning_weights(df_clean, df_rules_structure, df_formats)

# Нормализация
df_weights['Месяц'] = df_weights['Месяц'].astype(str).str.strip().str.lower()
df_weights['Филиал'] = df_weights['Филиал'].astype(str).str.strip()

# Объединение
df_calc = pd.merge(df_weights, df_plan_2026, on=['Филиал', 'Месяц'], how='left')
df_calc['План_Расч'] = (df_calc['План'] * df_calc['Final_Weight']).fillna(0)

# ========== DEBUG: Владимир Лента ==========
_vl = df_calc[df_calc['Филиал'] == 'Владимир Лента']
if len(_vl) > 0:
    print(f"\n{'='*70}")
    print(f"🔍 DEBUG: Владимир Лента")
    print(f"{'='*70}")
    print(f"   Всего строк: {len(_vl)}")
    print(f"   План филиала (уникальные): {_vl['План'].unique()}")
    print(f"   План филиала NaN: {_vl['План'].isna().sum()}")
    _vl_dept = _vl[_vl['Отдел'] == '10. Товары для дома']
    if len(_vl_dept) > 0:
        print(f"\n   10. Товары для дома:")
        for _, row in _vl_dept.head(3).iterrows():
            print(f"      {row['Месяц']}: План_фил={row['План']}, Weight={row['Final_Weight']:.4f}, Rev_2025_Norm={row['Rev_2025_Norm']:.0f}, План_Расч={row['План_Расч']:.0f}")
else:
    print(f"\n⚠️ Владимир Лента НЕ НАЙДЕН в df_calc!")

# Проверяем есть ли в плане 2026
_vl_plan = df_plan_2026[df_plan_2026['Филиал'].str.contains('Владимир', na=False)]
print(f"\n   Филиалы с 'Владимир' в df_plan_2026: {_vl_plan['Филиал'].unique().tolist()}")

# Проверяем форматы
_vl_fmt = df_formats[df_formats['Филиал'].str.contains('Владимир', na=False)]
print(f"   Филиалы с 'Владимир' в df_formats: {list(zip(_vl_fmt['Филиал'].tolist(), _vl_fmt['Формат'].tolist()))}")

# ========== DEBUG: Итоговый План_Расч для 7. Инструменты ==========
DEBUG_DEPT = '7. Инструменты'
DEBUG_MONTHS = ['сен', 'окт', 'ноя', 'дек']
RENOVATION_BRANCHES = ['Рыбинск', 'Владимир Розница']

# ========== АНАЛИЗ СТРУКТУРЫ ВЕСОВ ВЛАДИМИР РОЗНИЦА ==========
vlad_all = df_calc[df_calc['Филиал'] == 'Владимир Розница']
if len(vlad_all) > 0:
    print(f"\n{'='*70}")
    print(f"🔍 СТРУКТУРА ВЕСОВ: Владимир Розница (январь)")
    print(f"{'='*70}")

    vlad_jan = vlad_all[vlad_all['Месяц'] == 'янв'].sort_values('Final_Weight', ascending=False)
    total_weight = vlad_jan['Final_Weight'].sum()
    total_plan_rsch = vlad_jan['План_Расч'].sum()
    plan_branch = vlad_jan['План'].iloc[0] if len(vlad_jan) > 0 else 0

    print(f"   План филиала: {plan_branch:,.0f}")
    print(f"   Σ Final_Weight: {total_weight:.4f}")
    print(f"   Σ План_Расч: {total_plan_rsch:,.0f}")
    print(f"   Кол-во отделов: {len(vlad_jan)}")

    # Проверяем отделы с нулевой выручкой но ненулевым весом
    zero_rev_nonzero_weight = vlad_jan[(vlad_jan['Rev_2025'] == 0) & (vlad_jan['Final_Weight'] > 0)]
    if len(zero_rev_nonzero_weight) > 0:
        print(f"\n   ⚠️ ОТДЕЛЫ БЕЗ ПРОДАЖ 2025 НО С ВЕСОМ ({len(zero_rev_nonzero_weight)}):")
        for _, row in zero_rev_nonzero_weight.iterrows():
            r24 = row.get('Rev_2024', 0)
            r25 = row.get('Rev_2025', 0)
            w = row['Final_Weight']
            p = row['План_Расч']
            rule = row.get('Правило', 'N/A')
            print(f"      {row['Отдел']}: R24={r24:,.0f}, R25={r25:,.0f}, W={w:.4f}, План={p:,.0f}, Правило={rule}")

    # Проверяем отделы с очень маленькой выручкой но большим весом
    print(f"\n   {'Отдел':<40} {'Rev_2024':>12} {'Rev_2025':>12} {'Weight':>10} {'План_Расч':>12}")
    print(f"   {'-'*40} {'-'*12} {'-'*12} {'-'*10} {'-'*12}")

    # Топ-20 по весу
    for i, (_, row) in enumerate(vlad_jan.head(20).iterrows()):
        dept = row['Отдел'][:38] if len(row['Отдел']) > 38 else row['Отдел']
        r24 = row.get('Rev_2024', 0)
        r25 = row.get('Rev_2025', 0)
        w = row['Final_Weight']
        p = row['План_Расч']
        print(f"   {dept:<40} {r24:>12,.0f} {r25:>12,.0f} {w:>10.4f} {p:>12,.0f}")

    # Итого вес топ-20
    top20_weight = vlad_jan.head(20)['Final_Weight'].sum()
    print(f"\n   Σ вес топ-20: {top20_weight:.4f} ({top20_weight*100:.1f}%)")

    # Проверяем 2. Стройматериалы конкретно
    stroy = vlad_jan[vlad_jan['Отдел'] == '2. Стройматериалы']
    if len(stroy) > 0:
        row = stroy.iloc[0]
        r24 = row.get('Rev_2024', 0)
        r25 = row.get('Rev_2025', 0)
        print(f"\n   📊 2. Стройматериалы:")
        print(f"      Rev_2024 = {r24:,.0f}")
        print(f"      Rev_2025 = {r25:,.0f}")
        print(f"      Final_Weight = {row['Final_Weight']:.4f} ({row['Final_Weight']*100:.2f}%)")
        print(f"      План_Расч = {row['План_Расч']:,.0f}")
        print(f"      Правило = {row.get('Правило', 'N/A')}")
        if r24 > 0 and r25 > 0:
            base = 0.5 * r24 + 0.5 * r25
            print(f"      База (0.5×R24 + 0.5×R25) = {base:,.0f}")

# Показываем ВСЕ месяцы для Владимир Розница / 7. Инструменты
vlad_instr = df_calc[(df_calc['Филиал'] == 'Владимир Розница') & (df_calc['Отдел'] == DEBUG_DEPT)]
if len(vlad_instr) > 0:
    print(f"\n{'='*70}")
    print(f"🔧 ПОЛНЫЙ DEBUG: Владимир Розница / {DEBUG_DEPT}")
    print(f"{'='*70}")
    print(f"   {'Мес':<4} {'Rev_2024':>12} {'Rev_2025':>12} {'Rev_2025_Norm':>12} {'Final_Weight':>12} {'План_Расч':>12}")
    print(f"   {'-'*4} {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")
    for _, row in vlad_instr.sort_values('Месяц').iterrows():
        m = row['Месяц'][:3]
        r24 = row.get('Rev_2024', 0) if 'Rev_2024' in row else 0
        r25 = row.get('Rev_2025', 0) if 'Rev_2025' in row else 0
        r25n = row.get('Rev_2025_Norm', r25)
        w = row['Final_Weight']
        p = row['План_Расч']
        print(f"   {m:<4} {r24:>12,.0f} {r25:>12,.0f} {r25n:>12,.0f} {w:>12.4f} {p:>12,.0f}")

    # Проверяем формулу для янв
    jan_row = vlad_instr[vlad_instr['Месяц'] == 'янв']
    if len(jan_row) > 0:
        jan = jan_row.iloc[0]
        r24 = jan.get('Rev_2024', 0) if 'Rev_2024' in jan else 0
        r25n = jan.get('Rev_2025_Norm', jan.get('Rev_2025', 0))
        base_calc = 0.5 * r24 + 0.5 * r25n
        print(f"\n   📐 Формула для янв (правило '2024-2025'):")
        print(f"      База = 0.5×Rev_2024 + 0.5×Rev_2025_Norm")
        print(f"      База = 0.5×{r24:,.0f} + 0.5×{r25n:,.0f} = {base_calc:,.0f}")
        print(f"      Это объясняет низкий вес, если Rev_2024 был маленьким!")

for branch in RENOVATION_BRANCHES:
    debug_mask = (df_calc['Филиал'] == branch) & (df_calc['Отдел'] == DEBUG_DEPT) & (df_calc['Месяц'].isin(DEBUG_MONTHS))
    if debug_mask.any():
        print(f"\n{'='*70}")
        print(f"🔍 DEBUG ИТОГОВЫЙ ПЛАН: {branch} / {DEBUG_DEPT}")
        print(f"{'='*70}")
        for _, row in df_calc[debug_mask].iterrows():
            plan_rsch = row['План_Расч']
            print(f"   {row['Месяц']}:")
            print(f"      План филиала   = {row['План']:>12,.0f}")
            print(f"      Final_Weight   = {row['Final_Weight']:.4f} ({row['Final_Weight']*100:.2f}%)")
            print(f"      План_Расч      = {plan_rsch:>12,.0f}")
            print(f"      (Rev_2025_Norm = {row['Rev_2025_Norm']:>12,.0f} использовалась в расчёте веса)")

# ========== ДИАГНОСТИКА СХОДИМОСТИ для Москва Хаб ==========
_hub = df_calc[df_calc['Филиал'].str.contains('Хаб', na=False)]
if len(_hub) > 0:
    print(f"\n{'='*70}")
    print(f"🔍 СХОДИМОСТЬ Москва Хаб (все месяцы)")
    print(f"{'='*70}")
    _hub_errors = []
    for month in _hub['Месяц'].unique():
        _month_data = _hub[_hub['Месяц'] == month]
        if len(_month_data) > 0:
            plan_branch = _month_data['План'].iloc[0]
            sum_plan_rsch = _month_data['План_Расч'].sum()
            sum_weights = _month_data['Final_Weight'].sum()
            diff = plan_branch - sum_plan_rsch
            if abs(diff) > 100:
                _hub_errors.append(f"   ❌ {month}: План={plan_branch:,.0f}, Σ План_Расч={sum_plan_rsch:,.0f}, diff={diff:,.0f}, Σ весов={sum_weights:.4f}")
    if _hub_errors:
        for e in _hub_errors:
            print(e)
    else:
        print("   ✅ Все месяцы сходятся!")

    # Структура Москва Хаб для января
    _jan = _hub[_hub['Месяц'] == 'янв'].sort_values('Final_Weight', ascending=False)
    print(f"\n   📊 Структура Москва Хаб (янв):")
    for _, row in _jan.head(5).iterrows():
        print(f"      {row['Отдел']}: вес={row['Final_Weight']:.4f} ({row['Final_Weight']*100:.1f}%), План_Расч={row['План_Расч']:,.0f}")

_moscow_aug = df_calc[(df_calc['Филиал'].str.contains('Москва', na=False)) & (df_calc['Месяц'] == 'авг')]
if len(_moscow_aug) > 0:
    _sant = _moscow_aug[_moscow_aug['Отдел'].str.contains('Сантехника', na=False) & ~_moscow_aug['Отдел'].str.contains('инженерная', na=False, case=False)]
    if len(_sant) > 0:
        print(f"   План={_sant['План'].values[0]}, Final_Weight={_sant['Final_Weight'].values[0]:.4f}, План_Расч={_sant['План_Расч'].values[0]:.0f}")

# Подготовка справочников
df_fact_25 = df_sales_2023_2025[df_sales_2023_2025['Год']==2025].groupby(['Филиал', 'Отдел', 'Месяц'])['Выручка'].sum().reset_index().rename(columns={'Выручка': 'Выручка_2025'})
df_fact_24 = df_sales_2023_2025[df_sales_2023_2025['Год']==2024].groupby(['Филиал', 'Отдел', 'Месяц'])['Выручка'].sum().reset_index().rename(columns={'Выручка': 'Выручка_2024'})
df_area_25 = df_area[df_area['Год']==2025].groupby(['Филиал', 'Отдел', 'Месяц'])['Площадь'].max().reset_index().rename(columns={'Площадь': 'Площадь_2025'})
df_area_26 = df_area[df_area['Год']==2026].groupby(['Филиал', 'Отдел', 'Месяц'])['Площадь'].max().reset_index().rename(columns={'Площадь': 'Площадь_2026'})

# Объединение всех справочников
merge_keys = ['Филиал', 'Отдел', 'Месяц']
df_facts_areas = (
    df_fact_25
    .merge(df_fact_24, on=merge_keys, how='outer')
    .merge(df_area_25, on=merge_keys, how='outer')
    .merge(df_area_26, on=merge_keys, how='outer')
)

df_result = (
    df_calc
    .merge(df_facts_areas, on=merge_keys, how='left')
    .merge(df_formats, on='Филиал', how='left')
)
df_result[['Выручка_2025', 'Выручка_2024', 'Площадь_2025', 'Площадь_2026']] = df_result[['Выручка_2025', 'Выручка_2024', 'Площадь_2025', 'Площадь_2026']].fillna(0)

# Переименовываем нормализованную выручку для отображения
if 'Rev_2025_Norm' in df_result.columns:
    df_result['Выручка_2025_Норм'] = df_result['Rev_2025_Norm']
    df_result.drop(columns=['Rev_2025_Norm'], inplace=True)

# ФИЛЬТРАЦИЯ НЕВАЛИДНЫХ СТРОК ДО ПРИМЕНЕНИЯ БИЗНЕС-ПРАВИЛ
# Это критично! NaN-филиалы создают группы в groupby, но не обрабатываются в цикле проверки
invalid_before = len(df_result)
df_result = df_result[
    df_result['Филиал'].notna() &
    df_result['Отдел'].notna() &
    (df_result['Филиал'].astype(str).str.strip() != '') &
    (df_result['Отдел'].astype(str).str.strip() != '') &
    (df_result['Филиал'].astype(str).str.lower() != 'nan') &
    (df_result['Отдел'].astype(str).str.lower() != 'nan')
].reset_index(drop=True)
invalid_after = len(df_result)

# ========== КОЭФФИЦИЕНТЫ НАГРУЗКИ (ОТКЛЮЧЕНО) ==========
# Добавляем Роль до применения бизнес-правил
df_result = pd.merge(df_result, df_roles[['Отдел', 'Роль']], on='Отдел', how='left')
df_result['Роль'] = df_result['Роль'].fillna('Сопутствующий')

# Коэффициенты нагрузки временно отключены
# saved_growth, saved_decline, saved_limits = load_coefficients_from_sheets(gc)
# df_result = apply_load_coefficients(df_result, coeffs_growth, coeffs_decline)

# Пересчитываем План_Расч с весами (без коэффициентов)
df_result['План_Расч'] = (df_result['План'] * df_result['Final_Weight']).fillna(0)

# ========== DEBUG: Москва Хаб / 1. Сантехника ==========
_hub_sant = df_result[(df_result['Филиал'].str.contains('Хаб', na=False)) & (df_result['Отдел'] == '1. Сантехника')]
if len(_hub_sant) > 0:
    print(f"\n{'='*70}")
    print(f"🔍 DEBUG: Москва Хаб / 1. Сантехника (до apply_business_rules)")
    print(f"{'='*70}")
    for _, row in _hub_sant.iterrows():
        m = row['Месяц']
        print(f"   {m}: План_фил={row['План']:,.0f}, Weight={row['Final_Weight']:.6f}, Выр25={row['Выручка_2025']:,.0f}, План_Расч={row['План_Расч']:,.0f}")

_moscow_aug_before = df_result[(df_result['Филиал'].str.contains('Москва', na=False)) & (df_result['Месяц'] == 'авг')]
if len(_moscow_aug_before) > 0:
    _sant_before = _moscow_aug_before[_moscow_aug_before['Отдел'].str.contains('Сантехника', na=False) & ~_moscow_aug_before['Отдел'].str.contains('инженерная', na=False, case=False)]
    if len(_sant_before) > 0:
        print(f"   План={_sant_before['План'].values[0]}, Final_Weight={_sant_before['Final_Weight'].values[0]:.4f}")
        print(f"   План_Расч={_sant_before['План_Расч'].values[0]:.0f}")

# Применяем ограничения роста (лимиты из таблицы Google Sheets)
# _limits_from_sheets = load_limits_from_sheets(gc)
# ГЛАВНОЕ: Применение бизнес-правил
df_result = apply_business_rules(df_result, df_roles)

# ВАЖНО: Применяем лимиты ПОСЛЕ бизнес-правил (иначе бизнес-правила перезапишут)
# df_result = apply_plan_limits(df_result, None, _limits_from_sheets) # REMOVED: Redundant and breaks rounding

# DEBUG: Проверяем Москва Хаб / Мебель СРАЗУ после apply_plan_limits
_hub_mebel_debug = df_result[(df_result['Филиал'].str.contains('Хаб', na=False)) &
                              (df_result['Отдел'].str.contains('Мебель для дома', na=False))]
if len(_hub_mebel_debug) > 0:
    print(f"\n🔍 DEBUG: Москва Хаб / Мебель для дома ПОСЛЕ apply_plan_limits:")
    for _, row in _hub_mebel_debug.iterrows():
        fact = row.get('Выручка_2025', 0)
        plan = row.get('План_Расч', 0)
        growth = (plan / fact - 1) * 100 if fact > 0 else 0
        print(f"   {row['Месяц']}: fact={fact:,.0f}, План_Расч={plan:,.0f}, рост={growth:.1f}%")

# ========== DEBUG: Москва Хаб / 1. Сантехника ПОСЛЕ apply_business_rules ==========
_hub_sant_after = df_result[(df_result['Филиал'].str.contains('Хаб', na=False)) & (df_result['Отдел'] == '1. Сантехника')]
if len(_hub_sant_after) > 0:
    print(f"\n🔍 DEBUG: Москва Хаб / 1. Сантехника ПОСЛЕ apply_business_rules")
    for _, row in _hub_sant_after.iterrows():
        m = row['Месяц']
        print(f"   {m}: План_Расч={row['План_Расч']:,.0f}")

# Минимальный план для Мини/Микро/Интернет теперь применяется внутри дашборда
# после загрузки корректировок (метод _apply_min_plan_network)

# ========== ДИАГНОСТИКА СХОДИМОСТИ после apply_business_rules ==========
_hub = df_result[df_result['Филиал'].str.contains('Хаб', na=False)]
if len(_hub) > 0:
    print(f"\n{'='*70}")
    print(f"🔍 СХОДИМОСТЬ после apply_business_rules - Москва Хаб")
    print(f"{'='*70}")
    for month in [1, 2, 3]:
        _month_data = _hub[_hub['Месяц'] == month]
        if len(_month_data) > 0:
            plan_branch = _month_data['План'].iloc[0]
            sum_plan_rsch = _month_data['План_Расч'].sum()
            diff = plan_branch - sum_plan_rsch
            month_name = {1:'янв', 2:'фев', 3:'мар'}[month]
            status = "✅" if abs(diff) < 1000 else "❌"
            print(f"   {status} {month_name}: План={plan_branch:,.0f}, Σ План_Расч={sum_plan_rsch:,.0f}, diff={diff:,.0f}")

_moscow_aug_after = df_result[(df_result['Филиал'].str.contains('Москва', na=False)) & (df_result['Месяц'] == 'авг')]
if len(_moscow_aug_after) > 0:
    _sant_after = _moscow_aug_after[_moscow_aug_after['Отдел'].str.contains('Сантехника', na=False) & ~_moscow_aug_after['Отдел'].str.contains('инженерная', na=False, case=False)]
    if len(_sant_after) > 0:
        print(f"   План_Расч={_sant_after['План_Расч'].values[0]:.0f}, Final_Weight={_sant_after['Final_Weight'].values[0]:.4f}")

# Убираем строки с NaN (на всякий случай - основная фильтрация уже прошла выше)
df_result = df_result[
    df_result['Филиал'].notna() &
    df_result['Отдел'].notna() &
    (df_result['Филиал'].astype(str).str.lower() != 'nan') &
    (df_result['Отдел'].astype(str).str.lower() != 'nan')
].reset_index(drop=True)

# Инициализация
df_result['Расч_План'] = df_result['План_Расч'].copy()
df_result['План_Скорр'] = df_result['План_Расч'].copy()
df_result['Корр'] = np.nan

# DEBUG: Проверяем Москва Хаб / Мебель ПОСЛЕ План_Скорр = План_Расч.copy()
_hub_mebel_debug2 = df_result[(df_result['Филиал'].str.contains('Хаб', na=False)) &
                               (df_result['Отдел'].str.contains('Мебель для дома', na=False))]
if len(_hub_mebel_debug2) > 0:
    print(f"\n🔍 DEBUG: Москва Хаб / Мебель для дома ПОСЛЕ копирования План_Скорр:")
    for _, row in _hub_mebel_debug2.iterrows():
        fact = row.get('Выручка_2025', 0)
        plan = row.get('План_Скорр', 0)
        growth = (plan / fact - 1) * 100 if fact > 0 else 0
        print(f"   {row['Месяц']}: fact={fact:,.0f}, План_Скорр={plan:,.0f}, рост={growth:.1f}%")

_moscow_aug_final = df_result[(df_result['Филиал'].str.contains('Москва', na=False)) & (df_result['Месяц'] == 'авг')]
if len(_moscow_aug_final) > 0:
    _sant_final = _moscow_aug_final[_moscow_aug_final['Отдел'].str.contains('Сантехника', na=False) & ~_moscow_aug_final['Отдел'].str.contains('инженерная', na=False, case=False)]
    if len(_sant_final) > 0:
        print(f"   План_Расч={_sant_final['План_Расч'].values[0]:.0f}, План_Скорр={_sant_final['План_Скорр'].values[0]:.0f}")

# Расчёт метрик
df_result['Прирост_%'] = calc_growth_pct(df_result['План_Расч'], df_result['Выручка_2025'])
df_result['Отдача_План'] = np.where(df_result['Площадь_2026'] > 0, (df_result['План_Скорр'] / df_result['Площадь_2026']).round(0), 0)
df_result['Отдача_2025'] = np.where(df_result['Площадь_2025'] > 0, (df_result['Выручка_2025'] / df_result['Площадь_2025']).round(0), 0)
df_result['Δ_Отдача_%'] = np.where((df_result['Отдача_2025'] > 0) & (df_result['Отдача_План'] > 0), calc_growth_pct(df_result['Отдача_План'], df_result['Отдача_2025']), 0)
df_result['Δ_Площадь_%'] = np.where((df_result['Площадь_2025'] > 0) & (df_result['Площадь_2026'] > 0), calc_growth_pct(df_result['Площадь_2026'], df_result['Площадь_2025']), 0)

# ========== ФИНАЛЬНАЯ ПРОВЕРКА СХОДИМОСТИ ==========
print(f"\n{'='*70}")
print(f"📊 ФИНАЛЬНАЯ ПРОВЕРКА СХОДИМОСТИ")
print(f"{'='*70}")
_convergence_issues = []
for (branch, month), group in df_result.groupby(['Филиал', 'Месяц']):
    plan_branch = group['План'].iloc[0]
    sum_plan = group['План_Скорр'].sum()
    diff = plan_branch - sum_plan
    if abs(diff) > 1000:  # Допуск 1000 руб
        _convergence_issues.append({
            'Филиал': branch,
            'Месяц': month,
            'План': plan_branch,
            'Σ_План_Скорр': sum_plan,
            'Diff': diff
        })
if _convergence_issues:
    print(f"❌ Найдено {len(_convergence_issues)} проблем сходимости:")
    for issue in _convergence_issues[:15]:
        print(f"   {issue['Филиал']} {issue['Месяц']}: План={issue['План']:,.0f}, Σ={issue['Σ_План_Скорр']:,.0f}, diff={issue['Diff']:,.0f}")
    if len(_convergence_issues) > 15:
        print(f"   ... и ещё {len(_convergence_issues) - 15}")
else:
    print(f"✅ Все {df_result.groupby(['Филиал', 'Месяц']).ngroups} групп сходятся!")

# Запуск дашборда

# === ВНЕДРЕННАЯ ЛОГИКА КОНЕЦ ===

# === ЗАПУСК ДАШБОРДА ===
print('✅ Логика загружена. Запуск дашборда...')
try:
    if 'dashboard' in locals(): del dashboard # Очистка старой переменной
    if 'gc' not in locals(): gc = None

    # Пытаемся запустить
    # df_result и df_roles должны быть определены в логике выше
    if 'df_result' in locals():
        # Если df_roles не определен, попробуем None
        roles_arg = df_roles if 'df_roles' in locals() else None

        # dashboard = PlanDashboard(df_result, gc_client=gc, df_roles=roles_arg)
        display(dashboard.view())
    else:
        print('❌ Ошибка: df_result не определен после выполнения логики.')
except Exception as e:
    print(f'❌ Ошибка запуска дашборда: {e}')
    import traceback
    traceback.print_exc()

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


    def _update_chart_main(self):
        try:
            agg = self._get_cached_agg()
            if not agg or 'by_month' not in agg:
                self.chart_pane.object = None
                return

            m = agg['by_month'].sort_values('Месяц')
            if len(m) == 0:
                self.chart_pane.object = None
                return

            m['Месяц_текст'] = m['Месяц'].map(MONTH_MAP_REV)

            # Δ% План к 2025
            m['Δ%_план'] = 0.0
            mask25 = m['Выручка_2025'] > 0
            m.loc[mask25, 'Δ%_план'] = ((m.loc[mask25, 'План_Скорр'] / m.loc[mask25, 'Выручка_2025'] - 1) * 100).round(1)

            # Δ% Выручка 2025 к 2024 (факт к факту)
            m['Δ%_25_24'] = 0.0
            if 'Выручка_2024' in m.columns:
                mask24 = m['Выручка_2024'] > 0
                m.loc[mask24, 'Δ%_25_24'] = ((m.loc[mask24, 'Выручка_2025'] / m.loc[mask24, 'Выручка_2024'] - 1) * 100).round(1)

            mt = m['Месяц_текст'].tolist()
            plan = (m['План_Скорр'].fillna(0)/1e6).tolist()
            plan_calc = (m['План_Расч'].fillna(0)/1e6).tolist() if 'План_Расч' in m.columns else plan
            r25 = (m['Выручка_2025'].fillna(0)/1e6).tolist()
            r24 = (m['Выручка_2024'].fillna(0)/1e6).tolist() if 'Выручка_2024' in m.columns else [0]*len(m)
            delta_plan = m['Δ%_план'].fillna(0).tolist()
            delta_25_24 = m['Δ%_25_24'].fillna(0).tolist()

            # Разница между планом и расчётным (для отображения)
            diff_corr = [p - c for p, c in zip(plan, plan_calc)]

            mx = max(max(plan), max(plan_calc), max(r25), max(r24)) if plan else 1
            mn = min(min(plan), min(plan_calc), min(r25), min(r24)) if plan else 0
            mn = max(0, mn * 0.9)

            p = create_bokeh_chart(mt)
            p.y_range.start = mn
            p.y_range.end = mx * 1.2

            src = ColumnDataSource(data={
                'month': mt, 'plan': plan, 'plan_calc': plan_calc,
                'rev25': r25, 'rev24': r24, 'delta_plan': delta_plan, 'delta_25_24': delta_25_24, 'diff': diff_corr
            })

            l24 = add_line_with_scatter(p, src, 'month', 'rev24', COLORS['muted'], line_width=1.5, scatter_size=4)
            l25 = add_line_with_scatter(p, src, 'month', 'rev25', COLORS['primary'])

            # Расчётный план - пунктирная линия
            l_calc = p.line('month', 'plan_calc', source=src, line_width=2,
                           line_color='#9E9E9E', line_dash='dashed', line_alpha=0.8)
            p.scatter('month', 'plan_calc', source=src, size=5,
                     fill_color='#9E9E9E', line_color='#9E9E9E', fill_alpha=0.6)

            # Финальный план - основная линия
            l26 = add_line_with_scatter(p, src, 'month', 'plan', COLORS['secondary'], line_width=2.5, scatter_size=6)

            hover_circles = p.circle('month', 'plan', source=src, size=15, fill_alpha=0, line_alpha=0)

            # Дельта плана к 2025 — над точками плана
            for t, v, d in zip(mt, plan, delta_plan):
                color = COLORS['negative'] if d < 0 else COLORS['positive']
                p.text(x=[t], y=[v+mx*0.05], text=[f"{d:+.0f}%"], text_font_size='10px',
                       text_color=color, text_align='center', text_font_style='bold')

            # Дельта 2025 к 2024 — над точками факта 2025
            for t, v, d in zip(mt, r25, delta_25_24):
                color = COLORS['negative'] if d < 0 else COLORS['positive']
                p.text(x=[t], y=[v+mx*0.03], text=[f"({d:+.0f}%)"], text_font_size='8px',
                       text_color=color, text_align='center', text_font_style='normal')

            p.add_layout(Legend(items=[
                ('План 26', [l26]),
                ('Расч.', [l_calc]),
                ('Факт 25', [l25]),
                ('Факт 24', [l24])
            ], location='center', orientation='vertical', label_text_font_size='7px', spacing=0, padding=1), 'right')

            hover = HoverTool(
                tooltips=[
                    ('Месяц', '@month'),
                    ('План', '@plan{0.0f} млн'),
                    ('Расчётный', '@plan_calc{0.0f} млн'),
                    ('Корр.', '@diff{+0.0f} млн'),
                    ('2025', '@rev25{0.0f} млн'),
                    ('2024', '@rev24{0.0f} млн'),
                    ('Δ% План/25', '@delta_plan{+0.0f}%'),
                    ('Δ% 25/24', '@delta_25_24{+0.0f}%')
                ],
                renderers=[hover_circles],
                mode='vline'
            )
            p.add_tools(hover)

            self.chart_pane.object = p
        except Exception as e:
            print(f"❌ _update_chart_main ошибка: {e}")



    def _update_chart_branches(self):
        """Сводная таблица: филиалы × месяцы с приростами в %"""
        agg = self._get_cached_agg()
        if not agg or 'by_branch_month' not in agg:
            self.chart_branches_pane.object = "<div style='color:#888;font-size:10px;'>Нет данных</div>"
            return

        pivot_data = agg['by_branch_month']
        if len(pivot_data) == 0:
            self.chart_branches_pane.object = "<div style='color:#888;font-size:10px;'>Нет данных</div>"
            return

        # Вычисляем прирост
        pivot_data = pivot_data.copy()
        mask = pivot_data['Выручка_2025'] > 0
        pivot_data['Прирост_%'] = np.where(mask,
            ((pivot_data['План_Скорр'] / pivot_data['Выручка_2025'] - 1) * 100).round(0), 0)

        month_order = [m for m in range(1, 13) if m in pivot_data['Месяц'].unique()]
        month_names = [MONTH_MAP_REV.get(m, str(m)) for m in month_order]

        # Заголовок - компактный с фиксированной шириной для филиала
        header_cells = ''.join(f'<th style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:#f5f5f5;font-size:9px;">{m}</th>' for m in month_names)
        header = f'''<thead style="position:sticky;top:0;background:#f5f5f5;z-index:1;"><tr>
            <th style="border:1px solid #ccc;padding:1px 2px;text-align:left;background:#f5f5f5;font-size:9px;max-width:100px;">Филиал</th>
            {header_cells}
            <th style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:#e0e0e0;font-size:9px;">Σ</th>
        </tr></thead>'''

        # Pivot
        pivot = pivot_data.pivot(index='Филиал', columns='Месяц', values='Прирост_%').fillna(0)
        pivot_plan = pivot_data.pivot(index='Филиал', columns='Месяц', values='План_Скорр').fillna(0)
        pivot_fact = pivot_data.pivot(index='Филиал', columns='Месяц', values='Выручка_2025').fillna(0)

        # Итого по строке
        row_plan = pivot_plan.sum(axis=1)
        row_fact = pivot_fact.sum(axis=1)
        pivot['Σ'] = np.where(row_fact > 0, ((row_plan / row_fact - 1) * 100).round(0), 0)

        rows = []
        for branch in sorted(pivot.index):
            cells = [f'<td style="border:1px solid #ccc;padding:1px 2px;font-size:9px;max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{branch}">{branch}</td>']

            for m in month_order:
                val = pivot.loc[branch, m] if m in pivot.columns else 0
                bg, text = get_cell_style(val)
                cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')

            val = pivot.loc[branch, 'Σ']
            bg, text = get_cell_style(val)
            cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-weight:bold;font-size:9px;">{text}</td>')
            rows.append(f'<tr>{"".join(cells)}</tr>')

        # Итого
        total_cells = ['<td style="border:1px solid #ccc;padding:1px 2px;font-size:9px;max-width:100px;">ИТОГО</td>']
        for m in month_order:
            m_data = pivot_data[pivot_data['Месяц'] == m]
            m_plan, m_fact = m_data['План_Скорр'].sum(), m_data['Выручка_2025'].sum()
            val = int(((m_plan / m_fact - 1) * 100)) if m_fact > 0 else 0
            bg, text = get_cell_style(val)
            total_cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')

        total_pct = int(((pivot_data['План_Скорр'].sum() / pivot_data['Выручка_2025'].sum() - 1) * 100)) if pivot_data['Выручка_2025'].sum() > 0 else 0
        bg, text = get_cell_style(total_pct)
        total_cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')
        rows.append(f'<tr style="background:#d0d0d0;font-weight:bold;">{"".join(total_cells)}</tr>')

        self.chart_branches_pane.object = f'<div style="max-height:200px;overflow-y:auto;"><table style="border-collapse:collapse;font-size:9px;width:100%;table-layout:fixed;">{header}<tbody>{"".join(rows)}</tbody></table></div>'
        # Принудительно триггерим обновление
        self.chart_branches_pane.param.trigger('object')



    def _update_chart_seasonality(self):
        agg = self._get_cached_agg()
        df = self._get_filtered_df()

        if len(df) == 0:
            self.chart_seasonality_pane.object = None
            return

        p = create_bokeh_chart(MONTHS, title='Сезонность %')

        items = []
        tooltip_data = {m: {'month': m} for m in MONTHS}

        # 1. ПУНКТИРНАЯ: Сезонность ФАКТА 2025 (для сравнения)
        fact_by_month = df.groupby('Месяц')['Выручка_2025'].sum()
        total_fact = fact_by_month.sum()
        if total_fact > 0:
            sf_fact = {m: round(fact_by_month.get(m, 0) / total_fact * 100, 1) for m in range(1, 13)}
        else:
            sf_fact = {m: 0 for m in range(1, 13)}

        fd_fact = [{'month': MONTH_MAP_REV.get(m, str(m)), 'val': sf_fact.get(m, 0)} for m in range(1, 13)]
        src_fact = ColumnDataSource(data={
            'month': [d['month'] for d in fd_fact],
            'val': [d['val'] for d in fd_fact],
            'label': ['Факт 2025']*12
        })

        l_fact = add_line_with_scatter(p, src_fact, 'month', 'val', '#9E9E9E', line_width=2, scatter_size=5, line_dash='dashed')
        items.append(('Факт 2025', [l_fact]))

        for m_num in range(1, 13):
            m_txt = MONTH_MAP_REV.get(m_num, str(m_num))
            tooltip_data[m_txt]['val_fact'] = round(sf_fact.get(m_num, 0), 1)

        # 2. СПЛОШНАЯ: Сезонность ИТОГОВОГО плана (План_Скорр - после корректировок)
        plan_by_month = df.groupby('Месяц')['План_Скорр'].sum()
        total_plan = plan_by_month.sum()
        if total_plan > 0:
            sf_final = {m: round(plan_by_month.get(m, 0) / total_plan * 100, 1) for m in range(1, 13)}
        else:
            sf_final = {m: 0 for m in range(1, 13)}

        fd_final = [{'month': MONTH_MAP_REV.get(m, str(m)), 'val': sf_final.get(m, 0)} for m in range(1, 13)]
        src_final = ColumnDataSource(data={
            'month': [d['month'] for d in fd_final],
            'val': [d['val'] for d in fd_final],
            'label': ['План 2026']*12
        })

        l_final = add_line_with_scatter(p, src_final, 'month', 'val', '#2196F3', line_width=3, scatter_size=8)
        items.append(('План 2026', [l_final]))

        for m_num in range(1, 13):
            m_txt = MONTH_MAP_REV.get(m_num, str(m_num))
            tooltip_data[m_txt]['val_final'] = round(sf_final.get(m_num, 0), 1)

        # 3. Линии по филиалам (если несколько)
        branches = df['Филиал'].unique().tolist()
        colors_list = Category10[max(3, min(len(branches), 10))] if branches else []

        # Показываем филиалы только если их больше 1
        if len(branches) > 1:
            for i, branch in enumerate(branches[:6]):
                bd = df[df['Филиал'] == branch]
                mp = bd.groupby('Месяц')['План_Скорр'].sum()
                yp = mp.sum()

                pd_data = [{'month': MONTH_MAP_REV.get(m, str(m)),
                           'val': round((mp.get(m, 0)/yp*100) if yp > 0 else 0, 1)} for m in range(1, 13)]

                src_p = ColumnDataSource(data={
                    'month': [d['month'] for d in pd_data],
                    'val': [d['val'] for d in pd_data],
                    'label': [branch]*12
                })

                lp = add_line_with_scatter(p, src_p, 'month', 'val', colors_list[i % len(colors_list)], line_width=1.5, scatter_size=4)
                label = branch[:10]+'..' if len(branch) > 10 else branch
                items.append((label, [lp]))

                for d in pd_data:
                    if d['month'] in tooltip_data:
                        tooltip_data[d['month']][f'val_{i}'] = d['val']

        if len(items) > 1:
            p.add_layout(Legend(items=items[:9], location='top_right', orientation='vertical',
                               label_text_font_size='6px', spacing=0, padding=1), 'right')

        hover_data = {
            'month': MONTHS,
            'val_fact': [tooltip_data.get(m, {}).get('val_fact', 0) for m in MONTHS],
            'val_final': [tooltip_data.get(m, {}).get('val_final', 0) for m in MONTHS]
        }
        tooltip_html_parts = [
            '<b>@month</b><br>',
            '<span style="color:#9E9E9E">Факт 2025</span>: @val_fact{0.0f}%<br>',
            '<span style="color:#2196F3"><b>План 2026</b></span>: @val_final{0.0f}%<br>'
        ]

        if len(branches) > 1:
            for i, branch in enumerate(branches[:6]):
                label = branch[:10]+'..' if len(branch) > 10 else branch
                col = f'val_{i}'
                hover_data[col] = [tooltip_data.get(m, {}).get(col, 0) for m in MONTHS]
                tooltip_html_parts.append(f'<span style="color:{colors_list[i % len(colors_list)]}">{label}</span>: @{col}{{0.0f}}%<br>')

        hover_src = ColumnDataSource(data=hover_data)
        hover_circles = p.circle('month', 'val_final', source=hover_src, size=20, fill_alpha=0, line_alpha=0)

        tooltip_html = ''.join(tooltip_html_parts)
        hover = HoverTool(tooltips=tooltip_html, renderers=[hover_circles], mode='vline')
        p.add_tools(hover)

        self.chart_seasonality_pane.object = p



    def _update_pivot_table(self):
        """Сводная таблица: отделы × месяцы с приростами в %"""
        if not hasattr(self, 'pivot_pane'):
            return

        agg = self._get_cached_agg()
        if not agg or 'by_dept_role_month' not in agg:
            self.pivot_pane.object = "<div style='color:#888;font-size:10px;'>Нет данных</div>"
            return

        pivot_data = agg['by_dept_role_month']
        if len(pivot_data) == 0:
            self.pivot_pane.object = "<div style='color:#888;font-size:10px;'>Нет данных</div>"
            return

        # Вычисляем прирост
        pivot_data = pivot_data.copy()
        mask = pivot_data['Выручка_2025'] > 0
        pivot_data['Прирост_%'] = np.where(mask,
            ((pivot_data['План_Скорр'] / pivot_data['Выручка_2025'] - 1) * 100).round(0), 0)

        month_order = [m for m in range(1, 13) if m in pivot_data['Месяц'].unique()]
        month_names = [MONTH_MAP_REV.get(m, str(m)) for m in month_order]
        n_months = len(month_order)

        # Заголовок - компактный с фиксированной шириной для отдела
        header_cells = ''.join(f'<th style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:#f5f5f5;font-size:9px;">{m}</th>' for m in month_names)
        header = f'''<thead style="position:sticky;top:0;background:#f5f5f5;z-index:1;"><tr>
            <th style="border:1px solid #ccc;padding:1px 2px;text-align:left;background:#f5f5f5;font-size:9px;max-width:120px;">Отдел</th>
            {header_cells}
            <th style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:#e0e0e0;font-size:9px;">Σ</th>
        </tr></thead>'''

        rows = []

        for role in ['Стратегический', 'Сопутствующий']:
            role_data = pivot_data[pivot_data['Роль'] == role]
            if role_data.empty:
                continue

            # Pivot
            pivot = role_data.pivot(index='Отдел', columns='Месяц', values='Прирост_%').fillna(0)
            pivot_plan = role_data.pivot(index='Отдел', columns='Месяц', values='План_Скорр').fillna(0)
            pivot_fact = role_data.pivot(index='Отдел', columns='Месяц', values='Выручка_2025').fillna(0)

            # Итого по строке
            row_plan = pivot_plan.sum(axis=1)
            row_fact = pivot_fact.sum(axis=1)
            pivot['Σ'] = np.where(row_fact > 0, ((row_plan / row_fact - 1) * 100).round(0), 0)

            # Строки отделов - с обрезанием текста
            for dept in sorted(pivot.index):
                cells = [f'<td style="border:1px solid #ccc;padding:1px 2px;font-size:9px;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{dept}">{dept}</td>']

                for m in month_order:
                    val = pivot.loc[dept, m] if m in pivot.columns else 0
                    bg, text = get_cell_style(val)
                    cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')

                val = pivot.loc[dept, 'Σ']
                bg, text = get_cell_style(val)
                cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-weight:bold;font-size:9px;">{text}</td>')
                rows.append(f'<tr>{"".join(cells)}</tr>')

            # Итог по роли
            role_label = '📌 Стратег.' if role == 'Стратегический' else '📎 Сопутств.'
            role_cells = [f'<td style="border:1px solid #ccc;padding:1px 2px;font-size:9px;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{role_label}</td>']

            for m in month_order:
                m_plan = pivot_plan[m].sum() if m in pivot_plan.columns else 0
                m_fact = pivot_fact[m].sum() if m in pivot_fact.columns else 0
                val = int(((m_plan / m_fact - 1) * 100)) if m_fact > 0 else 0
                bg, text = get_cell_style(val)
                role_cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')

            role_total = int(((pivot_plan.sum().sum() / pivot_fact.sum().sum() - 1) * 100)) if pivot_fact.sum().sum() > 0 else 0
            bg, text = get_cell_style(role_total)
            role_cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')
            rows.append(f'<tr style="background:#e8e8e8;font-weight:bold;">{"".join(role_cells)}</tr>')

        # Общий итог
        total_cells = ['<td style="border:1px solid #ccc;padding:1px 2px;font-size:9px;max-width:120px;">ИТОГО</td>']
        for m in month_order:
            m_data = pivot_data[pivot_data['Месяц'] == m]
            m_plan, m_fact = m_data['План_Скорр'].sum(), m_data['Выручка_2025'].sum()
            val = int(((m_plan / m_fact - 1) * 100)) if m_fact > 0 else 0
            bg, text = get_cell_style(val)
            total_cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')

        total_pct = int(((pivot_data['План_Скорр'].sum() / pivot_data['Выручка_2025'].sum() - 1) * 100)) if pivot_data['Выручка_2025'].sum() > 0 else 0
        bg, text = get_cell_style(total_pct)
        total_cells.append(f'<td style="border:1px solid #ccc;padding:1px 2px;text-align:center;background:{bg};font-size:9px;">{text}</td>')
        rows.append(f'<tr style="background:#d0d0d0;font-weight:bold;">{"".join(total_cells)}</tr>')

        self.pivot_pane.object = f'<div style="max-height:175px;overflow-y:auto;"><table style="border-collapse:collapse;font-size:9px;width:100%;table-layout:fixed;">{header}<tbody>{"".join(rows)}</tbody></table></div>'
        # Принудительно триггерим обновление
        self.pivot_pane.param.trigger('object')



    def view(self):
        """Главный метод отображения дашборда"""
        # CSS стили для дашборда
        filter_css = pn.pane.HTML("""
        <style>
        .bk-root .bk-input-group { margin-bottom: 10px; }
        .bk-root .bk-btn { font-size: 13px; }
        .sidebar_box { background: #f9f9f9; padding: 10px; border-radius: 5px; border: 1px solid #eee; }
        </style>
        """, width=0, height=0, margin=0, sizing_mode='fixed')

        # Подсказка для фильтров
        filter_hint = pn.pane.HTML("<div style='color: #666; font-size: 12px; margin-bottom: 10px;'>*Используйте фильтры в панели ниже для обновления данных*</div>")

        # ВАЖНО: Сначала инициализируем панели
        self._update()
        self._update_indicators()
        self._update_compact_stats()

        url = f"https://docs.google.com/spreadsheets/d/{CONFIG['corrections_sheet_id']}/edit#gid={CONFIG['corrections_gid']}"

        def make_filter_col(key):
            f = self.filters[key]
            return pn.Column(
                pn.Row(f['select'], f['reset'], align='start', sizing_mode='stretch_width'),
                f['indicator'],
                sizing_mode='stretch_width',
                margin=(0, 5)
            )

        def on_debug(e):
            """Кнопка отладки: показывает текущие значения фильтров"""
            vals = {}
            for k, f in self.filters.items():
                vals[k] = f['select'].value
            import json
            msg = json.dumps(vals, ensure_ascii=False, indent=2)
            self.status.object = f"<pre style='font-size:9px;max-height:200px;overflow:auto;'>{msg}</pre>"
            print(f"\n🐞 DEBUG FILTER VALUES:\n{msg}")

        debug_btn = pn.widgets.Button(name='🐞 Debug', width=60, button_type='light')
        debug_btn.on_click(on_debug)

        # Фильтры в GridBox
        filters_grid = pn.GridBox(
            make_filter_col('branch'),
            make_filter_col('dept'),
            make_filter_col('format'),
            make_filter_col('month'),
            make_filter_col('role'),
            make_filter_col('rule'),
            ncols=3,
            sizing_mode='stretch_width'
        )

        filters_block = pn.Column(
            filter_hint,
            filters_grid,
            sizing_mode='stretch_width',
            styles={'padding': '5px', 'background': '#fafafa', 'border': '1px solid #eee', 'border-radius': '5px'}
        )

        # Графики
        charts_row = pn.Row(
            pn.Column(
                pn.pane.HTML("<b style='font-size:11px;'>📈 Сезонность</b>", height=15),
                self.chart_pane,
                sizing_mode='stretch_width'
            ),
            pn.Column(
                pn.pane.HTML("<b style='font-size:11px;'>📊 Отделы</b>", height=15),
                self.chart_depts_pane,
                sizing_mode='stretch_width'
            ),
            pn.Column(
                pn.pane.HTML("<b style='font-size:11px;'>🏢 Филиалы</b>", height=15),
                self.chart_branches_pane,
                sizing_mode='stretch_width'
            ),
            sizing_mode='stretch_width'
        )

        # Слайдеры (если есть)
        def toggle_sliders(event):
            self._sliders_container.visible = not self._sliders_container.visible
            self._sliders_btn.name = '📉 Скрыть K' if self._sliders_container.visible else '📈 K-коэфф'

        self._sliders_btn = pn.widgets.Button(name='📈 K-коэфф', width=80, button_type='light')
        self._sliders_btn.on_click(toggle_sliders)

        sliders_content = self._get_elasticity_panel() if hasattr(self, '_get_elasticity_panel') else pn.pane.HTML("")
        self._sliders_container = pn.Column(sliders_content, visible=False, sizing_mode='stretch_width')

        # Заголовок
        header_row = pn.Row(
            pn.pane.HTML("<b style='font-size: 14px;'>📊 План 2026</b>", width=120),
            self.status,
            self.compact_stats,
            debug_btn,
            pn.Spacer(width=10),
            self.export_btn,
            pn.Spacer(width=5),
            pn.pane.HTML(f'<a href="{url}" target="_blank" style="font-size:10px;">📋</a>', width=25),
            pn.Spacer(width=10),
            self._sliders_btn,
            sizing_mode='stretch_width',
            align='center',
            height=30,
            styles={'background': '#f5f5f5', 'border-bottom': '1px solid #ddd', 'padding': '2px 8px'}
        )

        # Увеличиваем высоту статуса
        self.status.height = 30
        self.status.sizing_mode = 'stretch_width'

        return pn.Column(
            filter_css,
            header_row,
            self._sliders_container,
            filters_block,
            charts_row,
            self.table,
            sizing_mode='stretch_width'
        )


# ============================================================================
# ЗАПУСК (ИСПОЛНЯЕМЫЙ КОД)
# ============================================================================

# Загрузка ролей отделов


    def _update_chart_depts(self):
        """Топ-10 отделов по выручке (Bokeh)"""
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


    def _update_charts(self):
        """Безопасное обновление всех графиков"""
        for method_name in ['_update_chart_main', '_update_chart_branches', '_update_chart_seasonality', '_update_pivot_table', '_update_chart_depts']:
             if hasattr(self, method_name):
                try:
                    getattr(self, method_name)()
                except Exception as e:
                    print(f"❌ Error in {method_name}: {e}")



# In[15]:


# 💾 EXPORT DATA FOR WEB APP
import pickle
import os

DATA_FILE = '/home/eveselove/PLAN/dashboard_data.pkl'

# Check if required dataframes exist
if 'df_result' in locals() and 'df_roles' in locals():
    print(f"✅ Found data ({len(df_result)} rows)")

    with open(DATA_FILE, 'wb') as f:
        pickle.dump({'df': df_result, 'df_roles': df_roles}, f)
    print(f"✅ Data saved to {DATA_FILE}")
    print("🚀 Now you can run the web app: 'panel serve app.py'")
else:
    print("❌ df_result or df_roles not found.")
    print("⚠️ Please run the logic cells above (cells 1-13) first!")


# In[16]:


# Запуск отображения
dashboard.view()


# In[ ]:


# SAFETY EXPORT TO CSV
try:
    print("Saving to CSV...")
    df_export = dashboard.df.copy()
    # Convert list/array columns to string if needed to avoid csv issues, but standard csv handles it ok mostly
    df_export.to_csv('/home/eveselove/PLAN/dashboard_data.csv', index=False)
    print("✅ Saved dashboard_data.csv")

    if hasattr(dashboard, 'df_roles') and dashboard.df_roles is not None:
         dashboard.df_roles.to_csv('/home/eveselove/PLAN/dashboard_roles.csv', index=False)
except Exception as e:
    print(f"❌ Error saving CSV: {e}")


print("Script finished. Exporting...")
try:
    if 'df_result' in locals():
        print(f"Columns: {df_result.columns}")
        df_result.to_csv('dashboard_full.csv', index=False)
        print("SUCCESS: dashboard_full.csv created")
    else:
        print("df_result not found")
except Exception as e:
    print(f"Error: {e}")
