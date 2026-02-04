# === STREAMLIT PLAN DASHBOARD ===
# Полная логика расчёта из ноутбука PLANB.ipynb

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import warnings
from datetime import datetime
import sys

# === ПАРОЛЬ ДЛЯ РЕДАКТИРОВАНИЯ ===
# Измените этот пароль на свой. Только пользователи, знающие пароль, смогут редактировать данные.
EDIT_PASSWORD = "292929"  # <-- ЗАМЕНИТЕ НА СВОЙ ПАРОЛЬ

# Импорт нового оптимизатора распределения
try:
    from plan_optimizer import distribute_plan_qp, FIXED_DEPARTMENTS, LIMITED_GROWTH_DEPARTMENTS, clear_optimization_cache
    USE_QP_OPTIMIZER = True
except ImportError:
    USE_QP_OPTIMIZER = False
    def clear_optimization_cache(): pass  # Заглушка

warnings.filterwarnings('ignore')

st.set_page_config(page_title="План 2026", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

# Убираем лишние отступы Streamlit и фиксируем масштабирование колонок
st.markdown("""
<style>
    .block-container {
        padding-top: 0.5rem; 
        padding-bottom: 0rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
    div[data-testid="stVerticalBlock"] > div {gap: 0.3rem;}
    
    /* Фиксируем 4 колонки графиков */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        overflow-x: auto;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        min-width: 200px;
        flex: 1 1 25%;
    }
    
    /* Уменьшаем размер шрифта в таблицах */
    div[data-testid="stDataFrame"] {
        font-size: 11px !important;
    }
    div[data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] th {
        padding: 2px 4px !important;
        font-size: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

# Относительные пути для совместимости с Streamlit Cloud
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DATA_FILE = os.path.join(os.path.dirname(__file__), 'dashboard_data.csv')

# ============================================================================
# GOOGLE SHEETS ID (ИЗ НОУТБУКА)
# ============================================================================

# ЦЕЛЕВЫЕ ПЛАНЫ ФИЛИАЛОВ 2026 (Месяц, Филиал, План)
PLAN_SHEET_ID = '1q_hU5hQJ2aQXadGKJak2BY2DWltGTrhpi_7UyRVbXVM'

# Основные данные о продажах
SALES_SHEET_ID = '1Uh_5wP8MFJUgaHm_JLJkwQvzKWTyWqQW5LOr3p29h_o'
# Корректировки продаж Владимир (тот же sheet, другой gid)
SALES_CORRECTIONS_GID = '129997454'

# Справочники (Площади, Правила, Роли)
REFS_SHEET_ID = '1yPANhEDRwf_CKMLLz5Wdov4Tx8HCgfS0ckyW7jv1ugQ'
AREA_GID = None  # Первый лист (без gid) - площади магазинов
RULES_GID = '2130598218'  # Правила расчёта
ROLES_GID = '93699808'     # Роли отделов



# Создаём директорию данных, если её нет (с exist_ok для Streamlit Cloud)
os.makedirs(DATA_DIR, exist_ok=True)


CONFIG = {
    'rounding_step': 10000,
}

MONTH_MAP = {
    'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6,
    'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12
}
MONTH_MAP_REV = {v: k for k, v in MONTH_MAP.items()}

BUSINESS_RULES = {
    'MIN_PLAN_THRESHOLD': 0,  # Отключено по запросу
}

WEIGHT_2024 = 0.5
WEIGHT_2025 = 0.5

# ============================================================================
# ЛОКАЛЬНОЕ ХРАНИЛИЩЕ
# ============================================================================

def save_corrections_local(corrections_list):
    try:
        filepath = os.path.join(DATA_DIR, 'corrections.json')
        backup_dir = os.path.join(DATA_DIR, 'backups')
        
        # Создаём папку для бэкапов
        os.makedirs(backup_dir, exist_ok=True)
        
        # Создаём backup с датой и временем
        if os.path.exists(filepath):
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f'corrections_{timestamp}.json')
            import shutil
            shutil.copy2(filepath, backup_path)
            
            # Храним только последние 50 бэкапов
            backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('corrections_')])
            if len(backups) > 50:
                for old_backup in backups[:-50]:
                    os.remove(os.path.join(backup_dir, old_backup))
        
        # Сохраняем новую версию
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(corrections_list, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Ошибка сохранения: {e}")
        return False

def load_corrections_local():
    try:
        filepath = os.path.join(DATA_DIR, 'corrections.json')
        if not os.path.exists(filepath):
            return []
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_limits_local(limits_dict):
    try:
        filepath = os.path.join(DATA_DIR, 'limits.json')
        limits_json = {}
        for k, v in limits_dict.items():
            if isinstance(k, tuple):
                key = f"{k[0]}|||{k[1]}"
            else:
                key = k
            if v is not None and v != '':
                limits_json[key] = int(v)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({'limits': limits_json}, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def load_limits_local():
    """Загружает лимиты макс. роста. Возвращает dict с ключами-кортежами (Branch, Dept)."""
    try:
        filepath = os.path.join(DATA_DIR, 'limits.json')
        if not os.path.exists(filepath):
            return {}
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        raw = data.get('limits', {})
        limits = {}
        for k, v in raw.items():
            if isinstance(k, str) and '|||' in k:
                parts = k.split('|||')
                if len(parts) >= 2:
                    limits[(parts[0], parts[1])] = v
            else:
                # На случай, если ключи уже хранятся иначе или это legacy
                limits[k] = v
        return limits
    except Exception as e:
        print(f"Error loading limits: {e}")
        return {}

def load_growth_rates_local():
    """Загружает годовые приросты для сопутствующих отделов. Возвращает dict с ключами-кортежами (Branch, Dept)."""
    try:
        filepath = os.path.join(DATA_DIR, 'growth_rates.json')
        if not os.path.exists(filepath):
            return {}
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        growth = {}
        for item in data:
            branch = item.get('branch', '')
            dept = item.get('dept', '')
            rate = item.get('rate', 0)
            if branch and dept:
                growth[(branch, dept)] = rate
        return growth
    except Exception as e:
        print(f"Error loading growth rates: {e}")
        return {}

def load_strategic_growth_rates():
    """Загружает годовые приросты для стратегических отделов. Возвращает dict с ключами-кортежами (Branch, Dept)."""
    try:
        filepath = os.path.join(DATA_DIR, 'strategic_growth_rates.json')
        if not os.path.exists(filepath):
            return {}
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        growth = {}
        for item in data:
            branch = item.get('branch', '')
            dept = item.get('dept', '')
            rate = item.get('rate', 0)
            if branch and dept:
                growth[(branch, dept)] = rate
        return growth
    except Exception as e:
        print(f"Error loading strategic growth rates: {e}")
        return {}

def save_strategic_growth_rates(rates_dict):
    """Сохраняет годовые приросты для стратегических отделов."""
    try:
        filepath = os.path.join(DATA_DIR, 'strategic_growth_rates.json')
        data = []
        for (branch, dept), rate in rates_dict.items():
            data.append({'branch': branch, 'dept': dept, 'rate': rate})
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving strategic growth rates: {e}")
        return False

# ============================================================================
# ФУНКЦИИ РАСЧЁТА (ИЗ НОУТБУКА)
# ============================================================================

def parse_month(val):
    if val is None or val == '':
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    val_str = str(val).strip().lower()
    if val_str.isdigit():
        return int(val_str)
    return MONTH_MAP.get(val_str[:3], 0)

def has_correction(df, mask=None):
    """Проверяет наличие АБСОЛЮТНОЙ корректировки (Корр). 
    Корр_Дельта НЕ защищает отдел от перебалансировки до финального применения."""
    check = df['Корр'].notna()
    if 'Авто_Корр' in df.columns:
        check = check | df['Авто_Корр'].notna()
    return check & mask if mask is not None else check

def has_any_correction(df, mask=None):
    """Проверяет наличие любой корректировки (включая Корр_Дельта) — для финальной защиты."""
    check = df['Корр'].notna() | df['Корр_Дельта'].notna()
    if 'Авто_Корр' in df.columns:
        check = check | df['Авто_Корр'].notna()
    return check & mask if mask is not None else check

def calc_growth_pct(plan, fact):
    if isinstance(plan, pd.Series):
        return np.where(fact > 0, ((plan / fact - 1) * 100).round(1), 0.0)
    return round((plan / fact - 1) * 100, 1) if fact > 0 else 0.0


# ============================================================================
# СПЕЦИАЛЬНЫЙ РАСЧЁТ ДЛЯ ОТДЕЛА "ДОСТАВКА"
# ============================================================================

DELIVERY_TOTAL_PLAN = 73_000_000  # Жёсткий лимит плана Доставки

# Маппинг филиалов для расчёта долей Доставки
DELIVERY_BRANCH_GROUPS = {
    # Воронеж Московский Проспект берёт долю от Воронеж
    'Воронеж Московский Проспект': 'Воронеж',
    # Владимир филиалы объединяются для расчёта общей доли
    'Владимир Лента': 'Владимир_Объединённый',
    'Владимир Розница': 'Владимир_Объединённый',
}

def calculate_delivery_plan(df_sales, branch_plans):
    """
    Рассчитывает план для отдела Доставка по специальной логике:
    1. Общий план = 73,000,000
    2. Распределяется по долям Доставки в выручке филиала/месяца
    3. Специальные правила для некоторых филиалов
    
    Args:
        df_sales: DataFrame с продажами (Филиал, Отдел, Месяц, Год, Выручка)
        branch_plans: DataFrame с планами филиалов (Филиал, Месяц, План)
    
    Returns:
        DataFrame с планами Доставки по филиалам/месяцам
    """
    # Фильтруем только 2025 год и Доставку
    df_2025 = df_sales[(df_sales['Год'] == 2025)].copy()
    
    if df_2025.empty:
        return pd.DataFrame()
    
    # Создаём группу для расчёта доли
    df_2025['Группа_Для_Доли'] = df_2025['Филиал'].map(
        lambda x: DELIVERY_BRANCH_GROUPS.get(x, x)
    )
    
    # Считаем выручку Доставки по группам
    delivery_by_group = df_2025[df_2025['Отдел'] == 'Доставка.'].groupby(
        ['Группа_Для_Доли', 'Месяц']
    )['Выручка'].sum().reset_index()
    delivery_by_group.columns = ['Группа_Для_Доли', 'Месяц', 'Выручка_Доставка']
    
    # Считаем общую выручку по группам
    total_by_group = df_2025.groupby(
        ['Группа_Для_Доли', 'Месяц']
    )['Выручка'].sum().reset_index()
    total_by_group.columns = ['Группа_Для_Доли', 'Месяц', 'Выручка_Всего']
    
    # Объединяем для расчёта доли
    shares = delivery_by_group.merge(total_by_group, on=['Группа_Для_Доли', 'Месяц'], how='left')
    shares['Доля_Доставки'] = shares['Выручка_Доставка'] / shares['Выручка_Всего']
    shares['Доля_Доставки'] = shares['Доля_Доставки'].fillna(0)
    
    # Получаем планы филиалов и добавляем группу
    if branch_plans is None or branch_plans.empty:
        return pd.DataFrame()
    
    bp = branch_plans.copy()
    bp['Группа_Для_Доли'] = bp['Филиал'].map(
        lambda x: DELIVERY_BRANCH_GROUPS.get(x, x)
    )
    
    # Объединяем с долями
    bp = bp.merge(shares[['Группа_Для_Доли', 'Месяц', 'Доля_Доставки']], 
                  on=['Группа_Для_Доли', 'Месяц'], how='left')
    bp['Доля_Доставки'] = bp['Доля_Доставки'].fillna(0)
    
    # Рассчитываем "сырой" план Доставки (как долю от плана филиала)
    bp['План_Доставки_Сырой'] = bp['План'] * bp['Доля_Доставки']
    
    # Нормируем к общему лимиту 73 млн
    total_raw = bp['План_Доставки_Сырой'].sum()
    if total_raw > 0:
        bp['План_Доставки'] = (bp['План_Доставки_Сырой'] / total_raw) * DELIVERY_TOTAL_PLAN
    else:
        bp['План_Доставки'] = 0
    
    # Округляем до 10000
    bp['План_Доставки'] = (bp['План_Доставки'] / 10000).round() * 10000
    
    # Корректируем чтобы сумма была ровно 73 млн
    diff = DELIVERY_TOTAL_PLAN - bp['План_Доставки'].sum()
    if diff != 0:
        # Добавляем разницу к самому большому значению
        max_idx = bp['План_Доставки'].idxmax()
        bp.loc[max_idx, 'План_Доставки'] += diff
    
    # Формируем результат
    result = bp[['Филиал', 'Месяц', 'План_Доставки', 'Доля_Доставки']].copy()
    result.columns = ['Филиал', 'Месяц', 'План_Скорр', 'Доля_Факт']
    result['Отдел'] = 'Доставка.'
    
    return result


# ============================================================================
# ПОЛНАЯ ЛОГИКА РАСЧЁТА (ИЗ НОУТБУКА PLANB.ipynb)
# ============================================================================

# Справочник форматов филиалов (из ноутбука)
BRANCH_FORMATS = {
    'Вологда ТЦ': 'Флагман',
    'Иваново': 'Флагман',
    'Ярославль': 'Средний',
    'Кострома Стройка': 'Средний',
    'ЯрославльФрунзе': 'Средний',
    'Череповец ТЦ': 'Средний',
    'Рыбинск': 'Средний',
    'Тамбов': 'Средний',
    'Владимир Розница': 'Мини',
    'Владимир Лента': 'Мини',
    'Воронеж': 'Микро',
    'Воронеж Московский Проспект': 'Микро',
    'Москва Хаб': 'Интернет'
}

# Форматы с сетевой структурой
NETWORK_STRUCTURE_FORMATS = ['Мини', 'Микро', 'Интернет', 'Интернет магазин']

# Филиалы на ремонте
RENOVATION_BRANCHES = ['Рыбинск', 'Владимир Розница']
RENOVATION_START_MONTH = 9

# Инфляционный лимит для сопутствующих отделов (%)
INFLATION_CAP_PCT = 6

# Минимальный порог плана (меньше - обнуляем)
MIN_PLAN_THRESHOLD = 30000  # Минимальный план для отдела

# Шаг округления
ROUNDING_STEP = 10000  # Шаг округления

# Квартальная прогрессия роста для Дверей и Кухни
QUARTER_PROGRESS_DOORS = {3: 0.20, 6: 0.40, 9: 0.60, 12: 1.00}
QUARTER_PROGRESS_KITCHEN = {3: 0.20, 6: 0.40, 9: 0.60, 12: 1.00}


def save_filters_local(filters_dict):
    """Сохраняет фильтры в data/filters.json"""
    try:
        filepath = os.path.join(DATA_DIR, 'filters.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(filters_dict, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.warning(f"Ошибка сохранения фильтров: {e}")
        return False


def load_filters_local():
    """Загружает фильтры из data/filters.json"""
    try:
        filepath = os.path.join(DATA_DIR, 'filters.json')
        if not os.path.exists(filepath):
            return {}
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {}


def save_compressor_local(compressor_dict):
    """Сохраняет настройки компрессора в data/compressor.json"""
    try:
        filepath = os.path.join(DATA_DIR, 'compressor.json')
        compressor_json = {}
        for k, v in compressor_dict.items():
            if isinstance(k, tuple):
                key = f"{k[0]}|||{k[1]}"
            else:
                key = k
            growth = v.get('growth', 1.0)
            decline = v.get('decline', 1.0)
            if growth != 1.0 or decline != 1.0:
                compressor_json[key] = {'growth': growth, 'decline': decline}
        
        data = {
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'compressor': compressor_json
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.warning(f"Ошибка сохранения компрессора: {e}")
        return False


def load_compressor_local():
    """Загружает настройки компрессора из data/compressor.json"""
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
        return compressor
    except Exception as e:
        return {}


def calc_seasonality(df):
    """Рассчитывает сезонность факта и плана"""
    # Сезонность факта
    if 'Выручка_2024' in df.columns:
        rev_avg = (df['Выручка_2024'].fillna(0) + df['Выручка_2025'].fillna(0)) / 2
    else:
        rev_avg = df['Выручка_2025'].fillna(0)
    
    df['_month_rev'] = df.groupby(['Отдел', 'Месяц'])['Выручка_2025'].transform('sum')
    df['_year_rev'] = df.groupby('Отдел')['Выручка_2025'].transform('sum')
    
    df['Сезонность_Факт'] = np.where(
        df['_year_rev'] > 0,
        (df['_month_rev'] / df['_year_rev'] * 100).round(1),
        0.0
    )
    
    # Сезонность плана
    df['_month_plan'] = df.groupby(['Отдел', 'Месяц'])['План_Скорр'].transform('sum')
    df['_year_plan'] = df.groupby('Отдел')['План_Скорр'].transform('sum')
    
    df['Сезонность_План'] = np.where(
        df['_year_plan'] > 0,
        (df['_month_plan'] / df['_year_plan'] * 100).round(1),
        0.0
    )
    
    # Удаляем временные колонки
    df.drop(columns=['_month_rev', '_year_rev', '_month_plan', '_year_plan'], inplace=True, errors='ignore')
    
    return df


def apply_smooth_growth(df, dept_name, quarter_progress):
    """
    Универсальная логика плавного роста для отдела.
    
    Если для декабря задана корректировка (Корр), план плавно растёт
    от текущего уровня к декабрьской цели по квартальной прогрессии.
    """
    INFLATION = 1.06
    
    def get_quarter_end(month):
        return ((month - 1) // 3 + 1) * 3
    
    def get_quarter_start(month):
        return ((month - 1) // 3) * 3 + 1
    
    if 'Корр' not in df.columns:
        return set()
    if 'Авто_Корр' not in df.columns:
        df['Авто_Корр'] = np.nan
    
    # Находим филиалы с декабрьской корректировкой
    dec_mask = (df['Отдел'] == dept_name) & (df['Месяц'] == 12) & (df['Корр'].notna())
    if not dec_mask.any():
        return set()
    
    # Сезонность по отделу (используем Rev_2025, так как Выручка_2025 появляется позже)
    col_rev = 'Rev_2025' if 'Rev_2025' in df.columns else 'Выручка_2025'
    
    dept_network = df[df['Отдел'] == dept_name].groupby('Месяц')[col_rev].sum()
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
            # Пытаемся взять данные из разных вариантов названия колонок
            val_2025 = df.loc[idx, 'Выручка_2025'] if 'Выручка_2025' in df.columns else df.loc[idx, 'Rev_2025'] if 'Rev_2025' in df.columns else 0
            val_2024 = df.loc[idx, 'Выручка_2024'] if 'Выручка_2024' in df.columns else df.loc[idx, 'Rev_2024'] if 'Rev_2024' in df.columns else 0
            
            fact_2025 = val_2025 if pd.notna(val_2025) else 0
            fact_2024 = val_2024 if pd.notna(val_2024) else 0
            floor_val = max(fact_2024, fact_2025 * INFLATION)
            corr = df.loc[idx, 'Корр'] if pd.notna(df.loc[idx, 'Корр']) else None
            delta = df.loc[idx, 'Корр_Дельта'] if 'Корр_Дельта' in df.columns and pd.notna(df.loc[idx, 'Корр_Дельта']) else None
            month_data[month] = {
                'idx': idx, 'floor': floor_val, 'corr': corr, 'delta': delta, 
                'seasonality': seasonality.get(month, 1/12)
            }
        
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
            
            # Если есть ручная корректировка (не декабрь) - пропускаем
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
            
            final_plan = int(round(max(0, final_plan) / ROUNDING_STEP) * ROUNDING_STEP)
            df.loc[idx, 'План_Скорр'] = final_plan
            df.loc[idx, 'Авто_Корр'] = final_plan
            affected_groups.add((branch, month))
    
    return affected_groups


def apply_doors_smooth_growth(df):
    """Применяет плавный рост для отдела '9. Двери, фурнитура дверная'"""
    return apply_smooth_growth(df, '9. Двери, фурнитура дверная', QUARTER_PROGRESS_DOORS)


def apply_kitchen_smooth_growth(df):
    """Применяет плавный рост для отдела 'Мебель для кухни'"""
    return apply_smooth_growth(df, 'Мебель для кухни', QUARTER_PROGRESS_KITCHEN)


def apply_min_plan_network(df):
    """
    Применяет минимальный план для Мини/Микро/Интернет форматов.
    MIN_GROWTH = 1.0 означает: план не ниже факта (без принудительного роста).
    Если прирост задан отдельно — он уже применён в calculate_plan.
    """
    MIN_GROWTH = 1.0  # FIX: Убрали принудительный рост 6%
    
    if 'Формат' not in df.columns:
        return df
    
    network_mask = df['Формат'].isin(NETWORK_STRUCTURE_FORMATS)
    if not network_mask.any():
        return df
    
    def ceil_step(val):
        if val <= 0:
            return 0
        if val < 70000:
            rounded = np.ceil(val / ROUNDING_STEP) * ROUNDING_STEP
        else:
            rounded = round(val / ROUNDING_STEP) * ROUNDING_STEP
        if rounded < MIN_PLAN_THRESHOLD:
            return 0
        return rounded
    
    adjustments_made = 0
    limits_dict = load_limits_local()
    
    for (branch, month), group_idx in df[network_mask].groupby(['Филиал', 'Месяц']).groups.items():
        indices = list(group_idx)
        
        col_rev = 'Rev_2025' if 'Rev_2025' in df.columns else 'Выручка_2025'
        rev_2025 = df.loc[indices, col_rev].fillna(0)
        plan_skorr = df.loc[indices, 'План_Скорр'].fillna(0)
        
        min_plan = (rev_2025 * MIN_GROWTH).apply(ceil_step)
        
        # Отделы ниже минимума
        below_min_mask = (plan_skorr < min_plan) & (rev_2025 > 0) & (min_plan > 0)
        # Защищаем только отделы с Корр (абсолютной), НЕ Корр_Дельта
        has_corr = df.loc[indices, 'Корр'].notna()
        below_min_mask = below_min_mask & ~has_corr
        
        below_indices = [idx for idx, is_below in zip(indices, below_min_mask) if is_below]
        
        if not below_indices:
            continue
        
        deficit = sum(min_plan.loc[idx] - plan_skorr.loc[idx] for idx in below_indices)
        if deficit <= 0:
            continue
        
        # Поднимаем до минимума
        for idx in below_indices:
            df.loc[idx, 'План_Скорр'] = min_plan.loc[idx]
            adjustments_made += 1
        
        # Снимаем с других отделов пропорционально
        other_indices = [idx for idx in indices if idx not in below_indices]
        # Защищаем только отделы с Корр (абсолютной), НЕ Корр_Дельта
        other_indices = [idx for idx in other_indices
                       if not pd.notna(df.loc[idx, 'Корр'])]
        
        # Исключаем отделы с лимитами
        if limits_dict:
            other_indices = [idx for idx in other_indices 
                           if f"{df.loc[idx, 'Филиал']}|||{df.loc[idx, 'Отдел']}" not in limits_dict]
        
        if not other_indices:
            continue
        
        other_plans = df.loc[other_indices, 'План_Скорр']
        total_other = other_plans.sum()
        
        if total_other <= 0:
            continue
        
        for idx in other_indices:
            share = df.loc[idx, 'План_Скорр'] / total_other
            reduction = deficit * share
            new_plan = max(0, df.loc[idx, 'План_Скорр'] - reduction)
            new_plan = round(new_plan / ROUNDING_STEP) * ROUNDING_STEP
            df.loc[idx, 'План_Скорр'] = new_plan
    
    return df


def apply_load_coefficients(df, role_coefficients):
    """
    Применяет коэффициенты нагрузки (компрессор) по ролям отделов.
    
    Логика:
    1. Для каждой роли (Краски, Обои, Стратегический, Сопутствующий) задаётся коэффициент
    2. Коэффициент > 1 = больше нагрузки (план увеличивается)
    3. Коэффициент < 1 = меньше нагрузки (план уменьшается)
    4. После применения планы нормализуются к цели филиала
    
    Args:
        df: DataFrame с планами (должен содержать 'Роль', 'План_Скорр', 'Филиал', 'Месяц')
        role_coefficients: dict {роль: коэффициент}, например {'Краски': 1.2, 'Сопутствующий': 0.8}
    
    Returns:
        DataFrame с пересчитанными планами
    """
    if not role_coefficients:
        return df
    
    if 'Роль' not in df.columns:
        return df
    
    result = df.copy()
    
    # Получаем отделы с АБСОЛЮТНЫМИ корректировками (их не трогаем)
    # Корр_Дельта НЕ защищает - она применяется в самом конце
    has_corr = result['Корр'].notna()
    if 'Авто_Корр' in result.columns:
        has_corr = has_corr | result['Авто_Корр'].notna()
    
    adjustments = 0
    
    for (branch, month), group_idx in result.groupby(['Филиал', 'Месяц']).groups.items():
        indices = list(group_idx)
        
        # Цель филиала на месяц (сумма План_Скорр)
        target = result.loc[indices, 'План_Скорр'].sum()
        if target <= 0:
            continue
        
        # Отделы без корректировок (можем перераспределять)
        adjustable_indices = [idx for idx in indices if not has_corr.loc[idx]]
        
        # Исключаем отделы с strategic_rate
        strategic_growth_rates = load_strategic_growth_rates()
        if strategic_growth_rates:
            adjustable_indices = [idx for idx in adjustable_indices 
                                  if strategic_growth_rates.get((result.loc[idx, 'Филиал'], result.loc[idx, 'Отдел'])) is None]
        
        if not adjustable_indices:
            continue
        
        # Применяем коэффициенты
        weighted_plans = {}
        total_weighted = 0
        
        for idx in adjustable_indices:
            role = result.loc[idx, 'Роль']
            plan = result.loc[idx, 'План_Скорр']
            coef = role_coefficients.get(role, 1.0)
            weighted = plan * coef
            weighted_plans[idx] = weighted
            total_weighted += weighted
        
        if total_weighted <= 0:
            continue
        
        # Сумма фиксированных (с корректировками)
        fixed_indices = [idx for idx in indices if has_corr.loc[idx]]
        fixed_sum = result.loc[fixed_indices, 'План_Скорр'].sum() if fixed_indices else 0
        
        # Доступный бюджет для перераспределения
        available = target - fixed_sum
        if available <= 0:
            continue
        
        # Нормализуем к доступному бюджету
        for idx in adjustable_indices:
            share = weighted_plans[idx] / total_weighted
            new_plan = available * share
            new_plan = round(new_plan / ROUNDING_STEP) * ROUNDING_STEP
            new_plan = max(0, new_plan)
            
            if new_plan != result.loc[idx, 'План_Скорр']:
                adjustments += 1
            
            result.loc[idx, 'План_Скорр'] = new_plan
    
    if adjustments > 0:
        st.info(f"⚖️ Компрессор: перераспределено {adjustments} отделов")
    
    return result


def calculate_plan(df_sales, corrections=None, role_coefficients=None, limits=None):
    """
    Полный расчёт плана с учетом лимитов роста.
    """
    # ... (код функции) ...

    # ========== ПОДГОТОВКА ДАННЫХ ==========
    df_s = df_sales.copy()
    df_s['Месяц'] = df_s['Месяц'].apply(parse_month) if df_s['Месяц'].dtype == 'object' else df_s['Месяц']
    df_s['Филиал'] = df_s['Филиал'].astype(str).str.strip()
    df_s['Отдел'] = df_s['Отдел'].astype(str).str.strip()
    df_s['Выручка'] = pd.to_numeric(df_s['Выручка'], errors='coerce').fillna(0)
    
    months = list(range(1, 13))
    
    # ========== ЗАГРУЗКА СПРАВОЧНИКОВ (из session_state если есть) ==========
    if 'rules' in st.session_state:
        df_rules = st.session_state['rules']
    else:
        df_rules = load_rules()
    
    if 'roles' in st.session_state:
        df_roles = st.session_state['roles']
    else:
        df_roles = load_roles()
    
    # ========== ШАГ 1: Выручка по годам ==========

    df_2024 = df_s[df_s['Год'] == 2024].groupby(['Филиал', 'Отдел', 'Месяц'])['Выручка'].sum().reset_index()
    df_2024.columns = ['Филиал', 'Отдел', 'Месяц', 'Rev_2024']

    df_2025 = df_s[df_s['Год'] == 2025].groupby(['Филиал', 'Отдел', 'Месяц'])['Выручка'].sum().reset_index()
    df_2025.columns = ['Филиал', 'Отдел', 'Месяц', 'Rev_2025']

    # Годовая выручка
    df_2025_year = df_s[df_s['Год'] == 2025].groupby(['Филиал', 'Отдел'])['Выручка'].sum().reset_index()
    df_2025_year.columns = ['Филиал', 'Отдел', 'Rev_2025_Year']

    # ========== ШАГ 2: Мастер-таблица ==========
    if df_rules is not None:
        # Убираем дубликаты правил (один отдел - одно правило)
        df_rules = df_rules.drop_duplicates(subset=['Филиал', 'Отдел'])
        
        # Используем правила как основу
        df_master = df_rules.loc[df_rules.index.repeat(len(months))].reset_index(drop=True)
        df_master['Месяц'] = np.tile(months, len(df_rules))
    else:
        # Без правил - используем уникальные комбинации из данных
        all_combos = df_s[['Филиал', 'Отдел']].drop_duplicates()
        df_master = all_combos.loc[all_combos.index.repeat(len(months))].reset_index(drop=True)
        df_master['Месяц'] = np.tile(months, len(all_combos))
        df_master['Правило'] = 'Продажи 2024-2025'  # По умолчанию

    # Добавляем помесячную выручку
    df_master = pd.merge(df_master, df_2024, on=['Филиал', 'Отдел', 'Месяц'], how='left')
    df_master = pd.merge(df_master, df_2025, on=['Филиал', 'Отдел', 'Месяц'], how='left')
    df_master = pd.merge(df_master, df_2025_year, on=['Филиал', 'Отдел'], how='left')
    
    df_master['Rev_2024'] = df_master['Rev_2024'].fillna(0)
    df_master['Rev_2025'] = df_master['Rev_2025'].fillna(0)
    df_master['Rev_2025_Year'] = df_master['Rev_2025_Year'].fillna(0)

    # ========== ШАГ 3: Нормализация для филиалов на ремонте ==========
    df_master['Rev_2025_Norm'] = df_master['Rev_2025'].copy()

    for branch in RENOVATION_BRANCHES:
        branch_mask = df_master['Филиал'] == branch
        if not branch_mask.any():
            continue

        jan_aug_mask = branch_mask & (df_master['Месяц'] < RENOVATION_START_MONTH)
        jan_aug_data = df_master[jan_aug_mask].copy()

        valid_data = jan_aug_data[jan_aug_data['Rev_2024'] > 0].copy()
        if len(valid_data) == 0:
            continue

        valid_data['_ratio'] = valid_data['Rev_2025'] / valid_data['Rev_2024']
        avg_ratio_by_dept = valid_data.groupby('Отдел')['_ratio'].mean()
        overall_avg_ratio = valid_data['_ratio'].mean()

        sep_dec_mask = branch_mask & (df_master['Месяц'] >= RENOVATION_START_MONTH)
        for idx in df_master[sep_dec_mask].index:
            dept = df_master.loc[idx, 'Отдел']
            rev_2024 = df_master.loc[idx, 'Rev_2024']
            ratio = avg_ratio_by_dept.get(dept, overall_avg_ratio)
            if rev_2024 > 0:
                df_master.loc[idx, 'Rev_2025_Norm'] = rev_2024 * ratio

    # Годовая нормализованная выручка
    df_master['Rev_2025_Year_Norm'] = df_master.groupby(['Филиал', 'Отдел'])['Rev_2025_Norm'].transform('sum')

    # ========== ШАГ 4: Сезонность по НОРМАЛИЗОВАННОЙ выручке сети ==========
    df_s_2025 = df_s[df_s['Год'] == 2025].copy()
    
    # Применяем нормализацию к данным продаж для расчёта сезонности
    norm_ratios = df_master[['Филиал', 'Отдел', 'Месяц', 'Rev_2025', 'Rev_2025_Norm']].copy()
    norm_ratios['_norm_ratio'] = np.where(
        norm_ratios['Rev_2025'] > 0,
        norm_ratios['Rev_2025_Norm'] / norm_ratios['Rev_2025'],
        1.0
    )
    
    df_s_2025 = pd.merge(df_s_2025, norm_ratios[['Филиал', 'Отдел', 'Месяц', '_norm_ratio']],
                         on=['Филиал', 'Отдел', 'Месяц'], how='left')
    df_s_2025['_norm_ratio'] = df_s_2025['_norm_ratio'].fillna(1.0)
    df_s_2025['Выручка_Norm'] = df_s_2025['Выручка'] * df_s_2025['_norm_ratio']
    
    # Сетевая выручка по НОРМАЛИЗОВАННЫМ данным (сумма по всем филиалам отдела, с учётом нормализации провалов)
    # Используем Выручка_Norm, чтобы исключить влияние ремонтов и провалов на профиль сезонности
    network_month = df_s_2025.groupby(['Отдел', 'Месяц'])['Выручка_Norm'].sum().reset_index()
    network_month.columns = ['Отдел', 'Месяц', 'Network_Month']
    
    network_year = df_s_2025.groupby('Отдел')['Выручка_Norm'].sum().reset_index()
    network_year.columns = ['Отдел', 'Network_Year']
    
    # Сезонность = доля месяца в году (по всем филиалам сети)
    seasonality = pd.merge(network_month, network_year, on='Отдел', how='left')
    seasonality['Seasonality_Share'] = np.where(
        seasonality['Network_Year'] > 0,
        seasonality['Network_Month'] / seasonality['Network_Year'],
        1.0 / 12
    )
    
    # Приведение типов перед merge
    seasonality['Месяц'] = seasonality['Месяц'].astype(int)
    df_master['Месяц'] = df_master['Месяц'].astype(int)
    seasonality['Отдел'] = seasonality['Отдел'].astype(str).str.strip()
    df_master['Отдел'] = df_master['Отдел'].astype(str).str.strip()
    
    df_master = pd.merge(df_master, seasonality[['Отдел', 'Месяц', 'Seasonality_Share', 'Network_Month']], 
                         on=['Отдел', 'Месяц'], how='left')
    df_master['Seasonality_Share'] = df_master['Seasonality_Share'].fillna(1.0 / 12)
    df_master['Format_Network_Month'] = df_master['Network_Month'].fillna(0)
    
    # ========== ШАГ 5: Добавляем формат филиала ==========
    df_master['Формат'] = df_master['Филиал'].map(BRANCH_FORMATS).fillna('')
    df_master['is_network_format'] = df_master['Формат'].isin(NETWORK_STRUCTURE_FORMATS)

    # ========== ШАГ 6: Определяем типы правил ==========
    if 'Правило' not in df_master.columns:
        df_master['Правило'] = ''
    df_master['Правило'] = df_master['Правило'].fillna('').astype(str).str.strip()
    
    rule_lower = df_master['Правило'].str.lower()
    df_master['_is_no_plan'] = df_master['Правило'] == 'Не считаем план'
    df_master['_is_only_2025'] = rule_lower.str.contains('только 2025', na=False)
    df_master['_is_2024_2025'] = rule_lower.str.contains('2024-2025', na=False)
    df_master['_is_format'] = rule_lower.str.contains('формат', na=False) & ~rule_lower.str.contains('структура', na=False)
    df_master['_is_format_only'] = rule_lower.str.contains('структура только формата', na=False)

    # ========== ШАГ 7: Расчёт базы по правилам ==========
    def calc_base(row):
        rev_2025 = row['Rev_2025_Norm']
        rev_2025_year = row['Rev_2025_Year_Norm']
        fmt = row.get('Формат', '')
        
        if row['_is_no_plan']:
            # "Не считаем план" — база по факту 2025 (для расчёта теоретического веса)
            return rev_2025 if rev_2025 > 0 else 0.0
        elif row['_is_format_only']:
            # "Структура только формата" — используем СЕТЕВУЮ выручку формата
            return row['Format_Network_Month'] if row['Format_Network_Month'] > 0 else 0.0
        elif row['_is_only_2025']:
            # "Только 2025" — ЕДИНАЯ логика для сетевых форматов (Мини/Микро/Интернет):
            # Годовая выручка × Сезонность сети
            if fmt in ['Мини', 'Микро', 'Интернет', 'Интернет магазин']:
                return rev_2025_year * row['Seasonality_Share'] if rev_2025_year > 0 else 0.0
            return rev_2025
        elif row['_is_2024_2025']:
            # Взвешенное среднее 50/50
            # Для филиалов на ремонте: если Rev_2024 < 50% от Rev_2025, используем только 2025
            if row['Филиал'] in RENOVATION_BRANCHES:
                if row['Rev_2024'] < rev_2025 * 0.5:
                    return rev_2025
            return WEIGHT_2024 * row['Rev_2024'] + WEIGHT_2025 * rev_2025
        elif row['_is_format']:
            # "Формат" — годовая выручка × сезонность сети
            return rev_2025_year * row['Seasonality_Share']
        else:
            # По умолчанию — как "Только 2025"
            # Для сетевых форматов — сезонность сети
            if fmt in ['Мини', 'Микро', 'Интернет', 'Интернет магазин']:
                return rev_2025_year * row['Seasonality_Share'] if rev_2025_year > 0 else 0.0
            return rev_2025

    df_master['_base'] = df_master.apply(calc_base, axis=1)

    # ========== ШАГ 8: Расчёт весов ==========
    df_master['_total_base'] = df_master.groupby(['Филиал', 'Месяц'])['_base'].transform('sum')
    df_master['Final_Weight'] = np.where(
        df_master['_total_base'] > 0,
        df_master['_base'] / df_master['_total_base'],
        0.0
    )

    # ========== ШАГ 9: Добавляем роли отделов ==========
    if df_roles is not None:
        df_master = pd.merge(df_master, df_roles[['Отдел', 'Роль']], on='Отдел', how='left')
        df_master['Роль'] = df_master['Роль'].fillna('Сопутствующий')
    else:
        df_master['Роль'] = 'Сопутствующий'

    # ========== ШАГ 10: ЗАГРУЗКА ЦЕЛЕВЫХ ПЛАНОВ ФИЛИАЛОВ ==========
    # План спущен сверху — берём из session_state или загружаем
    if 'branch_plans' in st.session_state:
        df_branch_plans = st.session_state['branch_plans']
    else:
        df_branch_plans = load_branch_plans()
    
    if df_branch_plans is None or df_branch_plans.empty:
        st.error("❌ Целевые планы филиалов не загружены! Проверьте Google Sheets.")
        return pd.DataFrame()
    
    # Мержим целевые планы
    # ПРИНУДИТЕЛЬНОЕ ПРИВЕДЕНИЕ ТИПОВ ДЛЯ МЕРЖА
    df_master['Месяц'] = df_master['Месяц'].astype(int)
    df_branch_plans['Месяц'] = df_branch_plans['Месяц'].astype(int)
    df_master['Филиал'] = df_master['Филиал'].astype(str).str.strip()
    df_branch_plans['Филиал'] = df_branch_plans['Филиал'].astype(str).str.strip()

    df_master = pd.merge(df_master, df_branch_plans[['Филиал', 'Месяц', 'План']], 
                         on=['Филиал', 'Месяц'], how='left')
    
    # ДИАГНОСТИКА
    if df_master['План'].sum() == 0:
        with st.expander("🔴 ОШИБКА: План = 0. Нажмите для диагностики", expanded=True):
            st.error("Целевые планы филиалов не сопоставились с данными!")
            st.write("Uniq Branches Master:", df_master['Филиал'].unique())
            st.write("Uniq Branches Plans:", df_branch_plans['Филиал'].unique())
            st.write("Sample Master Keys:", df_master[['Филиал', 'Месяц']].head())
            st.write("Sample Plan Keys:", df_branch_plans[['Филиал', 'Месяц']].head())


    # ========== ШАГ 11: Инициализация колонок ==========
    df_master['Корр'] = np.nan
    df_master['Корр_Дельта'] = np.nan
    df_master['План_Расч'] = 0.0

    df_master['План_Скорр'] = 0.0

    # ========== ШАГ 11: Применение корректировок ==========
    if corrections:
        for corr in corrections:
            branch = corr.get('branch', '')
            dept = corr.get('dept', '')
            month = corr.get('month', 0)
            corr_val = corr.get('corr')
            delta_val = corr.get('delta')

            mask = (df_master['Филиал'] == branch) & (df_master['Отдел'] == dept) & (df_master['Месяц'] == month)
            if mask.sum() == 0:
                continue

            idx = df_master.index[mask][0]
            if corr_val is not None:
                df_master.loc[idx, 'Корр'] = corr_val
            if delta_val is not None:
                df_master.loc[idx, 'Корр_Дельта'] = delta_val

    # ========== ПРЕДВАРИТЕЛЬНЫЙ РАСЧЁТ ДЛЯ СПЕЦ-ФОРМАТОВ (Идеальная Сезонность) ==========
    # Для форматов: Мини, Микро, Интернет, Интернет магазин
    # Логика: 
    # - Для Сопутствующих отделов: План = Факт 2025 × (1 + Заданный Прирост%) × Сезонность
    # - Для Стратегических: План = Прогноз × Глобальный Коэфф. роста
    
    # ВАЖНО: Добавляем колонку Роль в df_master для использования в Step 9 и Step 13
    # Создаем dict {Отдел: Роль} для быстрого lookup
    if df_roles is not None and not df_roles.empty:
        role_map = df_roles.set_index('Отдел')['Роль'].to_dict()
    else:
        role_map = {}
    
    df_master['Роль'] = df_master['Отдел'].map(role_map).fillna('Стратегический')
    
    # ========== ШАГ 9: Расчёт для спец-форматов (Мини, Микро, Интернет) ==========
    # Логика:
    # 1. Сопутствующие: План = Факт_Год * Сезонность * (1 + Ручной_Прирост)
    # 2. Стратегические: План = (Цель_Филиала - Сумма_Сопутствующих) * Доля_Внутри_Стратегических
    #    Доля = (Факт_Год * Сезонность) / Сумма(Факт_Год * Сезонность) по стратегическим
    
    precalc_plans = {}
    
    # 1. Загружаем цели филиалов
    if 'branch_plans' in st.session_state:
        df_plans = st.session_state['branch_plans']
    else:
        df_plans = load_branch_plans()
    
    # Создаем маппинг целей: (Филиал, Месяц) -> План
    target_map = df_plans.groupby(['Филиал', 'Месяц'])['План'].sum().to_dict()
    
    # Спец-форматы для правила +6% (только для них применяется минимальный рост)
    SPECIAL_FORMATS = ['Мини', 'Микро', 'Интернет', 'Интернет магазин']
    
    # 2. ЛОГИКА ДЛЯ ВСЕХ ФОРМАТОВ: Сначала сопутствующие, потом стратегические
    # (Раньше было только для спец-форматов, теперь для ВСЕХ)
    growth_rates = load_growth_rates_local()
    
    # Получаем ВСЕ данные (не только спец-форматы)
    df_all = df_master.copy()
    
    # Роль уже определена в df_master выше (через role_map)
    
    # Определяем спец-форматы (Мини/Микро/Интернет) - для них используем сетевую сезонность
    is_special_format = df_all['Формат'].isin(SPECIAL_FORMATS)
    
    # --- РАСЧЁТ СОПУТСТВУЮЩИХ ---
    # Функция получения прироста (дефолт 0% если не указано)
    def get_growth(row):
        if row['Роль'] != 'Сопутствующий':
            return 0
        return growth_rates.get((row['Филиал'], row['Отдел']), 0) / 100.0

    df_all['Growth_Rate'] = df_all.apply(get_growth, axis=1)
    
    # Предварительный расчёт "Теоретического плана" (база для распределения)
    # Для СПЕЦ-ФОРМАТОВ: Base = Факт_Год × Сезонность_Сети  
    # Для ОСТАЛЬНЫХ: Base = Rev_2025_Norm (нормализованные продажи месяца)
    df_all['Base_Plan'] = np.where(
        is_special_format,
        df_all['Rev_2025_Year'] * df_all['Seasonality_Share'],  # Мини/Микро/Интернет - сетевая сезонность
        df_all['Rev_2025_Norm']  # Остальные - факт 2025 нормализованный
    )
    
    # План Сопутствующих (фиксированный)
    # Для СПЕЦ-ФОРМАТОВ: Calc_Plan = Base_Plan × (1 + Прирост) — помесячно
    # Для ОСТАЛЬНЫХ: growth_rate применяется к ГОДУ, затем распределяется по месяцам
    #   Годовой_План = Rev_2025_Year × (1 + growth_rate)
    #   Месячный_План = Годовой_План × (Rev_2025_Norm / Rev_2025_Year)
    #   Это эквивалентно: Rev_2025_Norm × (1 + growth_rate)
    df_all['Calc_Plan'] = 0.0
    acc_mask = df_all['Роль'] == 'Сопутствующий'
    
    # Для спец-форматов: помесячный расчёт
    acc_special = acc_mask & is_special_format
    df_all.loc[acc_special, 'Calc_Plan'] = df_all.loc[acc_special, 'Base_Plan'] * (1 + df_all.loc[acc_special, 'Growth_Rate'])
    
    # Для остальных форматов: годовой прирост × месячная доля
    # Calc_Plan = Rev_2025_Year × (1 + growth_rate) × (Rev_2025_Norm / Rev_2025_Year)
    # Упрощается до: Rev_2025_Norm × (1 + growth_rate)
    # НО! Важно: при балансировке в месяцы падения план сжимается.
    # Поэтому нужно компенсировать в месяцы роста.
    # Для этого рассчитаем "идеальный" план на год и распределим по структуре
    acc_other = acc_mask & ~is_special_format
    df_all.loc[acc_other, 'Calc_Plan'] = df_all.loc[acc_other, 'Rev_2025_Norm'] * (1 + df_all.loc[acc_other, 'Growth_Rate'])
    
    # --- РАСЧЁТ СТРАТЕГИЧЕСКИХ (С остатка) ---
    # Группируем по Филиал-Месяц
    strat_mask = df_all['Роль'] != 'Сопутствующий'
    
    # Предрасчёт: сумма нормализованной выручки 2025 по филиалу-месяцу
    fact_2025_by_branch_month = df_all.groupby(['Филиал', 'Месяц'])['Rev_2025_Norm'].sum().to_dict()
    
    # Предрасчёт: сумма базы сопутствующих и стратегических по филиалу-месяцу
    acc_base_sums = df_all[acc_mask].groupby(['Филиал', 'Месяц'])['Base_Plan'].sum().to_dict()
    strat_base_sums = df_all[strat_mask].groupby(['Филиал', 'Месяц'])['Base_Plan'].sum().to_dict()
    
    # Предрасчёт: сумма планов сопутствующих (с приростом) по филиалу-месяцу  
    acc_calc_sums = df_all[acc_mask].groupby(['Филиал', 'Месяц'])['Calc_Plan'].sum().to_dict()
    
    # DEBUG: для отслеживания расчётов
    debug_list = []
    
    # 3. Распределяем план в зависимости от роста/падения филиала
    def calc_plan_by_format(row):
        branch, month = row['Филиал'], row['Месяц']
        target = target_map.get((branch, month), 0)
        fact_2025 = fact_2025_by_branch_month.get((branch, month), 0)
        is_special = row['Формат'] in SPECIAL_FORMATS
        
        # Если таргета нет, фаллбэк на базу
        if target <= 0:
            return row['Base_Plan']
        
        # ========== СПЕЦ-ФОРМАТЫ (Мини/Микро/Интернет) ==========
        # Логика: Сначала сопутствующие (фиксированные), потом стратегические (остаток)
        if is_special:
            if row['Роль'] == 'Сопутствующий':
                return row['Calc_Plan']
            else:
                # Стратегические получают остаток
                acc_sum = acc_calc_sums.get((branch, month), 0)
                residual = max(0, target - acc_sum)
                strat_total = strat_base_sums.get((branch, month), 0)
                if strat_total > 0:
                    share = row['Base_Plan'] / strat_total
                    return residual * share
                return 0
        
        # ========== ОСТАЛЬНЫЕ ФОРМАТЫ ==========
        # Определяем прирост/падение филиала
        if fact_2025 > 0:
            branch_growth = (target / fact_2025) - 1  # Например: -0.05 = падение 5%
        else:
            branch_growth = 0
        
        # ПАДЕНИЕ филиала:
        # 1. Стратегические = уровень 2025 (не падают)
        # 2. Сопутствующие = Таргет - Σ Стратегических (терпят убыток в этом месяце)
        if branch_growth < 0:
            if row['Роль'] != 'Сопутствующий':
                # Стратегические: уровень 2025
                return row['Base_Plan']
            else:
                # Сопутствующие: получают остаток (Таргет - Σ Стратегических)
                strat_total = strat_base_sums.get((branch, month), 0)
                residual = max(0, target - strat_total)
                
                # Распределяем остаток пропорционально Base_Plan сопутствующих
                acc_base_total = acc_base_sums.get((branch, month), 0)
                if acc_base_total > 0:
                    share = row['Base_Plan'] / acc_base_total
                    return residual * share
                return 0
        
        # РОСТ филиала:
        # 1. Сопутствующие = Calc_Plan (с growth_rate) - будет скорректировано позже
        # 2. Стратегические = Таргет - Σ Сопутствующих
        else:
            if row['Роль'] == 'Сопутствующий':
                return row['Calc_Plan']
            else:
                # Стратегические получают остаток
                acc_sum = acc_calc_sums.get((branch, month), 0)
                residual = max(0, target - acc_sum)
                strat_total = strat_base_sums.get((branch, month), 0)
                if strat_total > 0:
                    share = row['Base_Plan'] / strat_total
                    return residual * share
                return 0
    
    # Применяем расчёт (Фаза 1)
    df_all['Final_Plan'] = df_all.apply(calc_plan_by_format, axis=1)
    
    # ========== ФАЗА 2: Корректировка сопутствующих для достижения годового growth_rate ==========
    # Для каждого сопутствующего отдела в НЕ спец-формате:
    # 1. Посчитать годовой итог Final_Plan
    # 2. Сравнить с целевым: Rev_2025_Year × (1 + growth_rate)
    # 3. Разницу распределить по месяцам РОСТА пропорционально их Base_Plan
    
    acc_other_mask = (df_all['Роль'] == 'Сопутствующий') & (~df_all['Формат'].isin(SPECIAL_FORMATS))
    
    if acc_other_mask.any():
        # Группируем по Филиал-Отдел
        for (branch, dept), group in df_all[acc_other_mask].groupby(['Филиал', 'Отдел']):
            # Годовой итог текущий
            current_year_sum = group['Final_Plan'].sum()
            
            # Целевой годовой план = Rev_2025_Year × (1 + growth_rate)
            rev_2025_year = group['Rev_2025_Year'].iloc[0] if 'Rev_2025_Year' in group.columns else group['Rev_2025_Norm'].sum()
            growth_rate = group['Growth_Rate'].iloc[0] if 'Growth_Rate' in group.columns else 0
            target_year_sum = rev_2025_year * (1 + growth_rate)
            
            # Разница (сколько нужно добавить)
            diff = target_year_sum - current_year_sum
            
            if abs(diff) > 10000:  # Корректируем только если разница значительная
                # Находим месяцы РОСТА филиала
                for idx, row in group.iterrows():
                    month = row['Месяц']
                    fact_2025_m = fact_2025_by_branch_month.get((branch, month), 0)
                    target_m = target_map.get((branch, month), 0)
                    
                    if fact_2025_m > 0:
                        br_growth = (target_m / fact_2025_m) - 1
                    else:
                        br_growth = 0
                    
                    df_all.loc[idx, '_is_growth_month'] = (br_growth >= 0)
                
                # Сумма Base_Plan в месяцы роста
                growth_months_mask = df_all.index.isin(group[df_all.loc[group.index, '_is_growth_month'] == True].index)
                growth_base_sum = df_all.loc[growth_months_mask, 'Base_Plan'].sum()
                
                if growth_base_sum > 0:
                    # Распределяем diff пропорционально Base_Plan в месяцы роста
                    for idx in group.index:
                        if df_all.loc[idx, '_is_growth_month']:
                            share = df_all.loc[idx, 'Base_Plan'] / growth_base_sum
                            adjustment = diff * share
                            df_all.loc[idx, 'Final_Plan'] += adjustment
    
    # Убираем временную колонку
    if '_is_growth_month' in df_all.columns:
        df_all.drop('_is_growth_month', axis=1, inplace=True)
    
    # ========== ФАЗА 3: Пересчёт стратегических после корректировки сопутствующих ==========
    # В месяцы РОСТА: стратегические = Таргет - Σ Сопутствующих (после корректировки)
    strat_other_mask = (df_all['Роль'] != 'Сопутствующий') & (~df_all['Формат'].isin(SPECIAL_FORMATS))
    
    if strat_other_mask.any():
        # Пересчитываем суммы сопутствующих после корректировки
        acc_final_sums = df_all[acc_mask].groupby(['Филиал', 'Месяц'])['Final_Plan'].sum().to_dict()
        
        for idx in df_all[strat_other_mask].index:
            row = df_all.loc[idx]
            branch, month = row['Филиал'], row['Месяц']
            target = target_map.get((branch, month), 0)
            fact_2025 = fact_2025_by_branch_month.get((branch, month), 0)
            
            if fact_2025 > 0:
                br_growth = (target / fact_2025) - 1
            else:
                br_growth = 0
            
            # Только в месяцы РОСТА пересчитываем
            if br_growth >= 0:
                acc_sum = acc_final_sums.get((branch, month), 0)
                residual = max(0, target - acc_sum)
                strat_total = strat_base_sums.get((branch, month), 0)
                
                if strat_total > 0:
                    share = row['Base_Plan'] / strat_total
                    df_all.loc[idx, 'Final_Plan'] = residual * share
    
    # Логика: strategic_growth_rates задаёт АБСОЛЮТНЫЙ годовой прирост для стратегических
    # Годовой План = Факт_2025_Year × (1 + rate%)
    # Распределяется по месяцам пропорционально Base_Plan
    # Остальные стратегические получают остаток
    
    strategic_growth_rates = load_strategic_growth_rates()
    
    if strategic_growth_rates:
        # Отделы, которые не участвуют в перераспределении
        excluded_strat_depts = ['9. Двери, фурнитура дверная', 'Мебель для кухни']
        
        # Группируем по Филиал-Отдел для расчёта годового плана
        strat_mask = (df_all['Роль'] != 'Сопутствующий') & (~df_all['Отдел'].isin(excluded_strat_depts))
        
        # Для каждого отдела с заданным rate: рассчитываем годовой план
        debug_phase4 = []
        for (branch, dept), dept_group in df_all[strat_mask].groupby(['Филиал', 'Отдел']):
            rate = strategic_growth_rates.get((branch, dept))
            
            if rate is None:
                continue  # Этот отдел не имеет заданного rate
            
            # Годовой план = Факт_2025_Year × (1 + rate%)
            rev_2025_year = dept_group['Rev_2025_Year'].iloc[0] if 'Rev_2025_Year' in dept_group.columns else dept_group['Base_Plan'].sum()
            target_year = rev_2025_year * (1 + rate / 100.0)
            
            # Общий Base_Plan для распределения по месяцам
            total_base = dept_group['Base_Plan'].sum()
            
            debug_phase4.append({
                'branch': str(branch),
                'dept': str(dept),
                'rate': float(rate),
                'rev_2025_year': float(rev_2025_year),
                'target_year': float(target_year),
                'total_base': float(total_base),
                'months': len(dept_group)
            })
            
            if total_base > 0:
                # Распределяем годовой план по месяцам пропорционально Base_Plan
                for idx, row in dept_group.iterrows():
                    monthly_share = row['Base_Plan'] / total_base
                    df_all.loc[idx, 'Final_Plan'] = target_year * monthly_share
        
        # Сохраняем debug
        if debug_phase4:
            import json
            with open('/tmp/debug_phase4_new.json', 'w') as f:
                json.dump(debug_phase4, f, ensure_ascii=False, indent=2)
        
        # Теперь для каждого Филиал-Месяц: пересчитываем остальных стратегических
        # Они получают остаток (Таргет - Σ Сопутствующих - Σ Стратегических_с_rate)
        for (branch, month), group in df_all.groupby(['Филиал', 'Месяц']):
            target = target_map.get((branch, month), 0)
            if target <= 0:
                continue
            
            # Сумма сопутствующих
            acc_sum = group[group['Роль'] == 'Сопутствующий']['Final_Plan'].sum()
            
            # Сумма стратегических С rate (исключая Двери/Кухни)
            strat_with_rate_mask = (
                (group['Роль'] != 'Сопутствующий') & 
                (~group['Отдел'].isin(excluded_strat_depts)) &
                group.apply(lambda r: strategic_growth_rates.get((branch, r['Отдел'])) is not None, axis=1)
            )
            strat_with_rate_sum = group.loc[strat_with_rate_mask, 'Final_Plan'].sum()
            
            # Сумма Двери + Кухни (фиксированные)
            doors_kitchens = group[group['Отдел'].isin(excluded_strat_depts)]['Final_Plan'].sum()
            
            # Остаток для стратегических БЕЗ rate
            residual = max(0, target - acc_sum - strat_with_rate_sum - doors_kitchens)
            
            # Стратегические БЕЗ rate
            strat_without_rate_mask = (
                (group['Роль'] != 'Сопутствующий') & 
                (~group['Отдел'].isin(excluded_strat_depts)) &
                group.apply(lambda r: strategic_growth_rates.get((branch, r['Отдел'])) is None, axis=1)
            )
            
            strat_without_rate = group[strat_without_rate_mask]
            if len(strat_without_rate) > 0 and residual > 0:
                total_base = strat_without_rate['Base_Plan'].sum()
                for idx in strat_without_rate.index:
                    if total_base > 0:
                        share = group.loc[idx, 'Base_Plan'] / total_base
                        df_all.loc[idx, 'Final_Plan'] = residual * share
                    else:
                        df_all.loc[idx, 'Final_Plan'] = 0
    
    # DEBUG: 1А. Сантехника инженерная
    import json
    if debug_list:
        with open('/tmp/debug_santeh_inj.json', 'w', encoding='utf-8') as f:
            json.dump(debug_list, f, ensure_ascii=False, indent=2)
    
    # DEBUG: Вологда
    import json
    vologda_debug = df_all[df_all['Филиал'].str.contains('Вологда', na=False) & (df_all['Месяц'] == 1)][
        ['Филиал', 'Отдел', 'Месяц', 'Роль', 'Формат', 'Rev_2025_Norm', 'Base_Plan', 'Final_Plan']
    ].head(20).to_dict('records')
    
    # Также добавим таргет и факт для Вологды
    vologda_targets = {k: v for k, v in target_map.items() if 'Вологда' in k[0] and k[1] == 1}
    vologda_facts = {k: v for k, v in fact_2025_by_branch_month.items() if 'Вологда' in k[0] and k[1] == 1}
    
    with open('/tmp/debug_vologda.json', 'w', encoding='utf-8') as f:
        json.dump({
            'target_map': {f"{k[0]}|{k[1]}": v for k, v in vologda_targets.items()},
            'fact_2025': {f"{k[0]}|{k[1]}": v for k, v in vologda_facts.items()},
            'departments': vologda_debug
        }, f, ensure_ascii=False, indent=2)
    
    # ========== ОКРУГЛЕНИЕ И МИНИМУМ ДЛЯ ВСЕХ ФОРМАТОВ ==========
    # Округляем все планы до ROUNDING_STEP
    df_all['Final_Plan'] = (df_all['Final_Plan'] / ROUNDING_STEP).round(0) * ROUNDING_STEP
    
    # Применяем минимум: план < MIN_PLAN_THRESHOLD → 0
    below_min_mask = (df_all['Final_Plan'] > 0) & (df_all['Final_Plan'] < MIN_PLAN_THRESHOLD)
    
    # Сохраняем освобождённые суммы по филиал-месяц
    freed_by_group = {}
    for (branch, month), grp in df_all[below_min_mask].groupby(['Филиал', 'Месяц']):
        freed_by_group[(branch, month)] = grp['Final_Plan'].sum()
    
    # Обнуляем маленькие планы
    df_all.loc[below_min_mask, 'Final_Plan'] = 0
    
    # Перераспределяем освобождённое
    for (branch, month), freed_amount in freed_by_group.items():
        if freed_amount > 0:
            # Определяем формат филиала
            branch_mask = (df_all['Филиал'] == branch) & (df_all['Месяц'] == month)
            format_val = df_all.loc[branch_mask, 'Формат'].iloc[0] if branch_mask.any() else None
            is_special = format_val in SPECIAL_FORMATS
            
            # Для остальных форматов с падением: перераспределяем на сопутствующих
            rev_sum = df_all.loc[branch_mask, 'Rev_2025_Norm'].sum()
            target_val = target_map.get((branch, month), 0)
            branch_growth = (target_val / rev_sum - 1) if rev_sum > 0 else 0
            
            if (not is_special) and (branch_growth < 0):
                # На сопутствующих
                acc_in_group = branch_mask & (df_all['Роль'] == 'Сопутствующий') & (df_all['Final_Plan'] >= MIN_PLAN_THRESHOLD)
            else:
                # На стратегических
                acc_in_group = branch_mask & (df_all['Роль'] == 'Стратегический') & (df_all['Final_Plan'] >= MIN_PLAN_THRESHOLD)
            
            if acc_in_group.any():
                max_idx = df_all.loc[acc_in_group, 'Final_Plan'].idxmax()
                df_all.loc[max_idx, 'Final_Plan'] += freed_amount
    
    # Заносим в precalc_plans
    for idx, row in df_all.iterrows():
        precalc_plans[(row['Филиал'], row['Отдел'], row['Месяц'])] = row['Final_Plan']

    # DEBUG: Записываем precalc_plans и детали для 2В. Металлопрокат
    import json
    debug_data = {
        'total_entries': len(precalc_plans),
        'metalloprokkt': [],
        'santeh_inj': [],
        'pokrytiya': [],
        'oboi': []
    }
    for key, val in precalc_plans.items():
        if '2В. Металлопрокат' in str(key[1]) and 'Владимир' in str(key[0]):
            debug_data['metalloprokkt'].append({
                'branch': key[0],
                'dept': key[1],
                'month': key[2],
                'plan': val
            })
        if '1А. Сантехника' in str(key[1]) and 'Вологда' in str(key[0]):
            debug_data['santeh_inj'].append({
                'branch': key[0],
                'dept': key[1],
                'month': key[2],
                'plan': val
            })
        if '5. Покрытия' in str(key[1]) and 'Владимир Лента' in str(key[0]):
            debug_data['pokrytiya'].append({
                'branch': key[0],
                'dept': key[1],
                'month': key[2],
                'plan': val
            })
        if '4. Обои' in str(key[1]) and 'Владимир Лента' in str(key[0]):
            debug_data['oboi'].append({
                'branch': key[0],
                'dept': key[1],
                'month': key[2],
                'plan': val
            })
    with open('/tmp/debug_metalloprokkat.json', 'w') as f:
        json.dump(debug_data, f, ensure_ascii=False, indent=2)

    # ========== ШАГ 12: Распределение плана по отделам ==========
    
    # Предрасчёт: максимальная месячная выручка за год для каждого (Филиал, Отдел)
    # Используется для исключения в правиле +6%
    max_rev_2025_by_branch_dept = {}
    if 'Rev_2025' in df_master.columns:
        for (branch, dept), grp in df_master.groupby(['Филиал', 'Отдел']):
            max_val = grp['Rev_2025'].max()
            if pd.notna(max_val):
                max_rev_2025_by_branch_dept[(branch, dept)] = max_val
    
    # Загружаем прирост для спец-форматов (используется в fallback расчёте)
    growth_rates_special = load_growth_rates_local()
    
    results = []
    for (branch, month), group in df_master.groupby(['Филиал', 'Месяц']):
        target = group['План'].iloc[0]
        if pd.isna(target):
            # Логируем пропущенные группы для диагностики
            with open('/tmp/missing_targets.txt', 'a') as f:
                f.write(f"Missing target: {branch}, Month {month}\n")
            results.append(group)
            continue
        target = int(round(target))
        
        g = group.copy()
        
        # DEBUG: trace 2В. Металлопрокат in Владимир Лента
        metalloprokkat_rows = g[g['Отдел'].str.contains('2В. Металлопрокат', na=False)]
        if 'Владимир Лента' in branch and len(metalloprokkat_rows) > 0:
            with open('/tmp/step12_metal_debug.txt', 'a') as df:
                for idx, row in metalloprokkat_rows.iterrows():
                    precalc_key = (row['Филиал'], row['Отдел'], row['Месяц'])
                    precalc_val = precalc_plans.get(precalc_key, 'NOT_FOUND')
                    df.write(f"Month={month}, Dept={row['Отдел']}, precalc={precalc_val}, Formат={row.get('Формат', 'N/A')}, Роль={row.get('Роль', 'N/A')}\n")
        
        weights = g['Final_Weight'].copy()
        manual_fixed_mask = has_correction(g) # Только ручные
        no_plan_mask = g['_is_no_plan']
        
        # Определяем, кто является спец-форматом (для правила +6%)
        is_special = g['Формат'].isin(SPECIAL_FORMATS)
        
        # Логика для ВСЕХ форматов:
        # 1. Сопутствующие -> ФИКСИРОВАННЫЕ (берем из precalc)
        # 2. Стратегические -> АКТИВНЫЕ (участвуют в балансировке под таргет)
        roles = g['Роль'] if 'Роль' in g.columns else pd.Series('Стратегический', index=g.index)
        
        # Сопутствующие ВСЕХ форматов теперь фиксированные
        is_accomp = (roles == 'Сопутствующий') & ~no_plan_mask
        is_strat = (roles != 'Сопутствующий') & ~no_plan_mask
        
        # Стратегические с заданным strategic_growth_rate тоже фиксируются (из precalc Фаза 4)
        strategic_growth_rates = load_strategic_growth_rates()
        has_strat_rate = pd.Series(False, index=g.index)
        for idx, row in g.iterrows():
            if strategic_growth_rates.get((row['Филиал'], row['Отдел'])) is not None:
                has_strat_rate[idx] = True
        
        # ВАЖНО: Веса для Стратегических НЕ переопределяем!
        # Используем оригинальные Final_Weight (из Step 8), основанные на правилах/продажах.
        # Это позволяет балансировке распределить МЕСЯЧНЫЙ таргет пропорционально,
        # сохраняя сезонность таргета (а не сетевую сезонность).
        # precalc используется только для Сопутствующих (fixed).

        # Общая маска фиксации: Ручные ИЛИ Сопутствующие ИЛИ Стратегические с rate (любого формата)
        fixed_mask = manual_fixed_mask | is_accomp | has_strat_rate
        
        # DEBUG: Покрытия во Владимир Лента
        if 'Владимир Лента' in branch and month == 1:
            pok_rows = g[g['Отдел'].str.contains('Покрытия', na=False)]
            if len(pok_rows) > 0:
                import json
                debug_step12_pok = []
                for idx, row in pok_rows.iterrows():
                    pk = (row['Филиал'], row['Отдел'], row['Месяц'])
                    debug_step12_pok.append({
                        'dept': str(row['Отдел']),
                        'has_strat_rate': bool(has_strat_rate[idx]) if idx in has_strat_rate.index else False,
                        'fixed_mask': bool(fixed_mask[idx]) if idx in fixed_mask.index else False,
                        'precalc_key': str(pk),
                        'precalc_value': float(precalc_plans.get(pk, -1)),
                        'strategic_rate': strategic_growth_rates.get((row['Филиал'], row['Отдел']))
                    })
                with open('/tmp/debug_step12_pokrytiya.json', 'w') as f:
                    json.dump(debug_step12_pok, f, ensure_ascii=False, indent=2)
        
        # DEBUG: Обои во Владимир Лента
        if 'Владимир Лента' in branch and month == 1:
            oboi_rows = g[g['Отдел'].str.contains('Обои', na=False)]
            if len(oboi_rows) > 0:
                import json
                debug_step12_oboi = []
                for idx, row in oboi_rows.iterrows():
                    pk = (row['Филиал'], row['Отдел'], row['Месяц'])
                    debug_step12_oboi.append({
                        'dept': str(row['Отдел']),
                        'has_strat_rate': bool(has_strat_rate[idx]) if idx in has_strat_rate.index else False,
                        'fixed_mask': bool(fixed_mask[idx]) if idx in fixed_mask.index else False,
                        'precalc_key': str(pk),
                        'precalc_value': float(precalc_plans.get(pk, -1)),
                        'strategic_rate': strategic_growth_rates.get((row['Филиал'], row['Отдел']))
                    })
                with open('/tmp/debug_step12_oboi.json', 'w') as f:
                    json.dump(debug_step12_oboi, f, ensure_ascii=False, indent=2)
        
        # Для остальных форматов с ПАДЕНИЕМ: ВСЕ фиксированы из precalc
        # (Стратегические = уровень 2025, Сопутствующие = с приростом)
        format_val = g['Формат'].iloc[0] if 'Формат' in g.columns else None
        is_special_format = format_val in SPECIAL_FORMATS
        
        # Рассчитываем рост/падение филиала
        rev_2025_sum = g['Rev_2025_Norm'].sum() if 'Rev_2025_Norm' in g.columns else 0
        branch_growth_pct = (target / rev_2025_sum - 1) if rev_2025_sum > 0 else 0
        
        # При ПАДЕНИИ в остальных форматах: ВСЕ фиксированы из precalc
        if (not is_special_format) and (branch_growth_pct < 0):
            # Все = FIXED (из precalc, который уже рассчитан в calc_plan_by_format)
            fixed_mask = ~no_plan_mask  # Все кроме "не считаем план"
            active_mask = pd.Series(False, index=g.index)  # Никто не балансирует
        else:
            active_mask = ~fixed_mask & ~no_plan_mask

        # Теоретический план (для всего, нужно для fallback)
        total_weight = weights.sum()
        if total_weight > 0:
            g['_theoretical'] = target * (weights / total_weight)
        else:
            g['_theoretical'] = 0

        # "Не считаем план" без корректировки = 0
        no_plan_without_corr = no_plan_mask & ~manual_fixed_mask
        g.loc[no_plan_without_corr, 'План_Расч'] = 0

        # Фиксированные (Ручные + Спец)
        if fixed_mask.any():
            for idx in g.index[fixed_mask]:
                corr = g.loc[idx, 'Корр']
                delta = g.loc[idx, 'Корр_Дельта']
                
                # Базовое значение:
                # 1. Если это Спец-Формат -> берем Precalc (Идеальная сезонность)
                # 2. Иначе -> берем Theoretical (Доля от месячного бюджета)
                
                # Ключ для Precalc
                precalc_key = (g.loc[idx, 'Филиал'], g.loc[idx, 'Отдел'], g.loc[idx, 'Месяц'])
                
                if precalc_key in precalc_plans:
                    base = precalc_plans[precalc_key]
                    is_precalc = True
                else:
                    base = g.loc[idx, '_theoretical']
                    is_precalc = False

                # Применяем ТОЛЬКО абсолютную корректировку (Корр)
                # Корр_Дельта применяется В САМОМ КОНЦЕ (после всех балансировок)
                if pd.notna(corr):
                    # Explicit 0 from user forces 0
                    if corr == 0:
                        final = 0
                    else:
                        # Абсолютная корректировка - используем как есть
                        final = corr
                else:
                    # Нет абсолютной корректировки - используем base
                    # Корр_Дельта будет применена позже в ШАГ 14
                    final = base
                
                # Apply Rounding and Threshold rules (Standardized)
                # Если исходное значение < 10000 — обнуляем (не округляем вверх)
                if final < ROUNDING_STEP:
                    final_rounded = 0
                else:
                    # Округляем до ближайших 10000 (стандартное математическое)
                    final_rounded = round(final / ROUNDING_STEP) * ROUNDING_STEP
                
                # Apply minimum threshold: план < 30000 → обнуляем
                if final_rounded > 0 and final_rounded < MIN_PLAN_THRESHOLD:
                    final_rounded = 0
                
                # DEBUG: trace for 2В. Металлопрокат
                if '2В. Металлопрокат' in str(g.loc[idx, 'Отдел']) and 'Владимир Лента' in str(g.loc[idx, 'Филиал']):
                    with open('/tmp/step12_debug.txt', 'a') as df:
                        df.write(f"Month={g.loc[idx, 'Месяц']}, precalc_key={precalc_key}, is_precalc={is_precalc}, base={base}, final={final}, final_rounded={final_rounded}\n")
                
                # DEBUG: trace for 1А. Сантехника
                if '1А. Сантехника' in str(g.loc[idx, 'Отдел']) and 'Вологда' in str(g.loc[idx, 'Филиал']):
                    with open('/tmp/step12_santeh.json', 'a') as df:
                        import json as j
                        j.dump({'month': int(g.loc[idx, 'Месяц']), 'is_precalc': is_precalc, 'base': float(base), 
                                'final': float(final), 'final_rounded': float(final_rounded), 'fixed': bool(fixed_mask.loc[idx])}, df)
                        df.write('\n')
                
                # DEBUG: trace for 4. Обои
                if '4. Обои' in str(g.loc[idx, 'Отдел']) and 'Владимир Лента' in str(g.loc[idx, 'Филиал']):
                    with open('/tmp/step12_oboi_fixed.json', 'a') as df:
                        import json as j
                        j.dump({'month': int(g.loc[idx, 'Месяц']), 'is_precalc': is_precalc, 'base': float(base), 
                                'final': float(final), 'final_rounded': float(final_rounded)}, df)
                        df.write('\n')
                
                g.loc[idx, 'План_Расч'] = final_rounded

        # Остаток на активных
        actual_fixed = g.loc[fixed_mask, 'План_Расч'].sum() if fixed_mask.any() else 0
        actual_no_plan = g.loc[no_plan_without_corr, 'План_Расч'].sum() if no_plan_without_corr.any() else 0
        remaining_target = target - actual_fixed - actual_no_plan

        # DEBUG: балансировка
        if is_special.any() and 'Владимир' in str(branch):
            with open('/tmp/balance_debug.txt', 'a') as f:
                f.write(f"\n=== {branch}, Месяц {month} ===\n")
                f.write(f"Target: {target}\n")
                f.write(f"Fixed (Сопутствующие): {actual_fixed}\n")
                f.write(f"Remaining for Стратегических: {remaining_target}\n")
                f.write(f"Fixed count: {fixed_mask.sum()}, Active count: {active_mask.sum()}\n")

        if active_mask.any() and remaining_target > 0:
            weights_active = weights.loc[active_mask].copy()
            weights_active_sum = weights_active.sum()

            # ========== ИНФЛЯЦИОННЫЙ ЛИМИТ ==========
            # Сопутствующие отделы не могут расти больше чем на INFLATION_CAP_PCT к 2025
            if weights_active_sum > 0:
                capped_indices = []
                excess_weight_total = 0
                current_sum_active = weights_active_sum
                
                for idx in weights_active.index:
                    role = g.loc[idx, 'Роль'] if 'Роль' in g.columns else 'Сопутствующий'
                    if role != 'Сопутствующий':
                        continue
                    
                    # База = нормализованная выручка 2025
                    base_rev = g.loc[idx, 'Rev_2025_Norm'] if 'Rev_2025_Norm' in g.columns else 0
                    if pd.isna(base_rev) or base_rev <= 0:
                        continue
                    
                    max_plan = base_rev * (1 + INFLATION_CAP_PCT / 100)
                    current_weight = weights_active.loc[idx]
                    implied_plan = remaining_target * (current_weight / current_sum_active)
                    
                    if implied_plan > max_plan:
                        # Корректируем вес
                        target_weight = (max_plan / remaining_target) * current_sum_active
                        weight_diff = current_weight - target_weight
                        
                        if weight_diff > 0:
                            weights_active.loc[idx] = target_weight
                            excess_weight_total += weight_diff
                            capped_indices.append(idx)
                
                # Перераспределяем на Стратегические
                if excess_weight_total > 0:
                    strat_indices = [idx for idx in weights_active.index 
                                     if g.loc[idx, 'Роль'] == 'Стратегический']
                    if strat_indices:
                        strat_weights = weights_active.loc[strat_indices]
                        strat_sum = strat_weights.sum()
                        if strat_sum > 0:
                            boost = excess_weight_total * (strat_weights / strat_sum)
                            weights_active.loc[strat_indices] += boost
                
                weights_active_sum = weights_active.sum()

            if weights_active_sum > 0:
                g.loc[active_mask, 'План_Расч'] = remaining_target * (weights_active / weights_active_sum)
            else:
                g.loc[active_mask, 'План_Расч'] = 0

        # Обнуление малых планов
        step = CONFIG['rounding_step']
        min_threshold = BUSINESS_RULES['MIN_PLAN_THRESHOLD']
        small_mask = (g['План_Расч'] > 0) & (g['План_Расч'] < min_threshold) & active_mask
        if small_mask.any():
            freed = g.loc[small_mask, 'План_Расч'].sum()
            g.loc[small_mask, 'План_Расч'] = 0
            remaining_active = active_mask & ~small_mask & (g['План_Расч'] > 0)
            if remaining_active.any() and freed > 0:
                w = weights.loc[remaining_active]
                w_sum = w.sum()
                if w_sum > 0:
                    g.loc[remaining_active, 'План_Расч'] += freed * (w / w_sum)

        # ========== УМНОЕ ОКРУГЛЕНИЕ (Largest Remainder Method) ==========
        # Сохраняем точные значения
        g.loc[active_mask, 'raw_plan'] = g.loc[active_mask, 'План_Расч']
        
        # Первичное округление
        g.loc[active_mask, 'План_Расч'] = (g.loc[active_mask, 'raw_plan'] / step).round(0).astype(int) * step
        
        # Считаем ошибку округления
        current_total = int(g['План_Расч'].sum())
        diff = target - current_total
        
        # Сколько ПОЛНЫХ шагов нужно добавить/убрать
        steps_needed = int(diff // step)
        
        if steps_needed != 0 and active_mask.any():
            # Считаем остатки (насколько мы "недодали" каждому отделу при округлении)
            g.loc[active_mask, 'diff_val'] = g.loc[active_mask, 'raw_plan'] - g.loc[active_mask, 'План_Расч']
            
            # Если нужно добавить (steps > 0): берем тех, у кого остаток наибольший (они "потеряли" при округлении)
            # Если нужно убрать (steps < 0): берем тех, у кого остаток наименьший (они "получили" лишнее)
            ascending = (steps_needed < 0)
            sorted_indices = g[active_mask].sort_values('diff_val', ascending=ascending).index
            
            # Берем top N, где N = количество шагов
            indices_to_adjust = sorted_indices[:abs(steps_needed)]
            adjustment = step if steps_needed > 0 else -step
            g.loc[indices_to_adjust, 'План_Расч'] += adjustment
        
        # Финальная проверка: после всех корректировок sum должен равняться target
        final_total = int(g['План_Расч'].sum())
        final_diff = target - final_total
        
        # Если остаток не равен 0 (из-за того что target не кратен step, или ошибки на границе),
        # добавляем его к самому большому плану (чтобы минимизировать относительное искажение)
        if final_diff != 0 and active_mask.any():
            # Находим отдел с максимальным планом среди активных
            active_plans = g.loc[active_mask, 'План_Расч']
            if not active_plans.empty and active_plans.max() > 0:
                max_idx = active_plans.idxmax()
                g.loc[max_idx, 'План_Расч'] += final_diff
        
        # DEBUG: После Smart Rounding
        if is_special.any() and 'Владимир' in str(branch) and month == 1:
            with open('/tmp/balance_debug.txt', 'a') as f:
                total_after_rounding = g['План_Расч'].sum()
                f.write(f"\nПосле Smart Rounding: {total_after_rounding} (Target: {target}, Diff: {target - total_after_rounding})\n")
        
        # ========== ПРАВИЛО: Минимум +6% для спец-форматов ==========
        # Для Мини, Микро, Интернет: План не может быть меньше Факт_2025 * 1.06
        # ИСКЛЮЧЕНИЕ: если месяц был максимальным по продажам за год — правило не применяется
        MIN_GROWTH_SPECIAL = 0.06  # +6%
        if is_special.any():
            for idx in g.index[is_special]:
                rev_2025 = g.loc[idx, 'Rev_2025'] if 'Rev_2025' in g.columns else 0
                dept = g.loc[idx, 'Отдел']
                branch_name = g.loc[idx, 'Филиал']
                
                if pd.notna(rev_2025) and rev_2025 > 0:
                    # Получаем максимум за год для этого (Филиал, Отдел)
                    max_rev_year = max_rev_2025_by_branch_dept.get((branch_name, dept), 0)
                    
                    # Проверяем: является ли этот месяц максимальным по продажам
                    is_max_month = (rev_2025 >= max_rev_year * 0.999)  # 0.1% погрешность для float
                    
                    if is_max_month:
                        # Для максимального месяца НЕ применяем +6%
                        # НО если расчётный план = 0 (ошибка данных), пересчитываем
                        if g.loc[idx, 'План_Расч'] <= 0:
                            # Используем: Факт_Год × Сезонность × (1 + Прирост)
                            rev_year = g.loc[idx, 'Rev_2025_Year'] if 'Rev_2025_Year' in g.columns else 0
                            seas = g.loc[idx, 'Seasonality_Share'] if 'Seasonality_Share' in g.columns else 0
                            
                            # Если сезонность = 0 или NaN, используем равномерную (1/12)
                            if pd.isna(seas) or seas <= 0:
                                seas = 1.0 / 12
                            
                            # Прирост из настроек (загружен перед циклом)
                            growth_key = (branch_name, dept)
                            growth_rate = growth_rates_special.get(growth_key, 0) / 100.0
                            
                            # Расчёт
                            if rev_year > 0:
                                fallback_plan = rev_year * seas * (1 + growth_rate)
                            else:
                                fallback_plan = rev_2025  # Крайний fallback
                            
                            g.loc[idx, 'План_Расч'] = round(fallback_plan / step) * step
                        continue
                    
                    min_plan = rev_2025 * (1 + MIN_GROWTH_SPECIAL)
                    # Округляем минимум до step
                    min_plan_rounded = round(min_plan / step) * step
                    if g.loc[idx, 'План_Расч'] < min_plan_rounded:
                        g.loc[idx, 'План_Расч'] = min_plan_rounded
        
        # ========== ПЕРЕБАЛАНСИРОВКА ПОСЛЕ +6% ==========
        # Если правило +6% создало избыток, уменьшаем Стратегических
        current_sum = g['План_Расч'].sum()
        excess = current_sum - target
        
        if excess > 0 and is_special.any():
            # Находим Стратегических в спец-форматах
            strat_special = is_special & (roles == 'Стратегический')
            
            if strat_special.any():
                strat_plans = g.loc[strat_special, 'План_Расч'].sum()
                
                if strat_plans > excess:
                    # Уменьшаем пропорционально, НО исключаем отделы с strategic_rate
                    strategic_growth_rates_inner = load_strategic_growth_rates()
                    reduction_ratio = (strat_plans - excess) / strat_plans
                    for idx in g.index[strat_special]:
                        dept = g.loc[idx, 'Отдел']
                        branch_name = g.loc[idx, 'Филиал']
                        # Пропускаем отделы с strategic_rate
                        if strategic_growth_rates_inner.get((branch_name, dept)) is not None:
                            continue
                        new_plan = g.loc[idx, 'План_Расч'] * reduction_ratio
                        # Округляем
                        g.loc[idx, 'План_Расч'] = round(new_plan / step) * step
                    
                    # Финальная корректировка остатка к максимальному плану
                    final_sum = g['План_Расч'].sum()
                    final_diff = target - final_sum
                    if final_diff != 0:
                        strat_plans_after = g.loc[strat_special, 'План_Расч']
                        if not strat_plans_after.empty and strat_plans_after.max() > 0:
                            max_idx = strat_plans_after.idxmax()
                            g.loc[max_idx, 'План_Расч'] += final_diff
        
        # DEBUG: Полный JSON для Владимир Лента
        if is_special.any() and 'Владимир Лента' in str(branch):
            import json
            debug_data = {
                'branch': str(branch),
                'month': int(month),
                'target': int(target),
                'fixed_sum': float(g.loc[fixed_mask, 'План_Расч'].sum()) if fixed_mask.any() else 0,
                'active_sum': float(g.loc[active_mask, 'План_Расч'].sum()) if active_mask.any() else 0,
                'total_sum': float(g['План_Расч'].sum()),
                'diff': float(target - g['План_Расч'].sum()),
                'fixed_count': int(fixed_mask.sum()),
                'active_count': int(active_mask.sum()),
                'departments': []
            }
            for idx in g.index:
                dept_info = {
                    'dept': str(g.loc[idx, 'Отдел']),
                    'role': str(g.loc[idx, 'Роль']) if 'Роль' in g.columns else 'N/A',
                    'plan': float(g.loc[idx, 'План_Расч']),
                    'rev_2025': float(g.loc[idx, 'Rev_2025']) if 'Rev_2025' in g.columns else 0,
                    'is_fixed': bool(fixed_mask.loc[idx]) if idx in fixed_mask.index else False,
                    'is_active': bool(active_mask.loc[idx]) if idx in active_mask.index else False
                }
                debug_data['departments'].append(dept_info)
            
            with open('/tmp/balance_full_debug.json', 'a') as f:
                f.write(json.dumps(debug_data, ensure_ascii=False) + '\n')
        
        # Чистим временные колонки
        for col in ['_theoretical', 'raw_plan', 'diff_val']:
            if col in g.columns:
                g = g.drop(columns=[col])

        # DEBUG: Все филиалы с расхождением
        final_diff_check = target - g['План_Расч'].sum()
        if abs(final_diff_check) > 1000:  # Расхождение > 1000 руб
            import json
            with open('/tmp/divergence_debug.json', 'a') as f:
                debug_info = {
                    'branch': str(branch),
                    'month': int(month),
                    'target': int(target),
                    'actual': float(g['План_Расч'].sum()),
                    'diff': float(final_diff_check),
                    'is_special': bool(is_special.any())
                }
                f.write(json.dumps(debug_info, ensure_ascii=False) + '\n')

        results.append(g)


    if results:
        result = pd.concat(results, ignore_index=True)
    else:
        result = df_master

    # ========== ШАГ 12.5: Промежуточные правила (Минимумы, Плавный рост) ==========
    # Для работы apply функций нужна колонка План_Скорр (они работают с ней)
    result['План_Скорр'] = result['План_Расч'].copy()
    
    # Сохраняем План_Расч для отделов с strategic_rate из precalc_plans (Фаза 4)
    # НЕ из result, т.к. Step 12 перебалансировка уже могла изменить значения
    strategic_growth_rates_preserve = load_strategic_growth_rates()
    preserved_plans = {}
    if strategic_growth_rates_preserve:
        for (branch, dept), rate in strategic_growth_rates_preserve.items():
            for m in range(1, 13):  # Все 12 месяцев
                key = (branch, dept, m)
                if key in precalc_plans:
                    preserved_plans[key] = precalc_plans[key]
    
    # DEBUG: что сохраняется для Обои
    oboi_preserved = sum(v for k, v in preserved_plans.items() 
                          if 'Обои' in str(k[1]) and 'Владимир Лента' in str(k[0]))
    with open('/tmp/debug_oboi_preserved.txt', 'w') as f:
        f.write(f"Oboi preserved: {oboi_preserved:,.0f}\n")
    
    apply_doors_smooth_growth(result)
    apply_kitchen_smooth_growth(result)
    # result = apply_min_plan_network(result)  # Отключено по запросу — минимальный план не применяется
    
    # 4. Компрессор (перераспределение по ролям)
    if role_coefficients:
        result = apply_load_coefficients(result, role_coefficients)
    
    # Возвращаем изменения в переменную расчета для балансировки
    result['План_Расч'] = result['План_Скорр']
    
    # Восстанавливаем План_Расч для отделов с strategic_rate
    for (branch, dept, month_val), plan_val in preserved_plans.items():
        mask = (result['Филиал'] == branch) & (result['Отдел'] == dept) & (result['Месяц'] == month_val)
        result.loc[mask, 'План_Расч'] = plan_val

    # DEBUG: Oboi после восстановления, до Step 13
    oboi_before_step13 = result[(result['Филиал'] == 'Владимир Лента') & (result['Отдел'].str.contains('Обои', na=False))]['План_Расч'].sum()
    with open('/tmp/debug_oboi_before_step13.txt', 'w') as f:
        f.write(f"Oboi before Step 13: {oboi_before_step13:,.0f}\n")

    # ========== ШАГ 13: SMART BALANCING v2 (Для обычных форматов) ==========
    # Логика:
    # 1. Считаем "Пол" (Факт + 6%).
    # 2. Считаем Score для каждого отдела (на основе Доли рынка и Тренда).
    # 3. Если денег много (Delta > 0) -> Раздаем тем, у кого высокий Score (недобор доли + рост).
    # 4. Если денег мало (Delta < 0) -> Режем тех, у кого низкий Score (перегретая доля + падение).
    
    # === НАСТРОЙКИ ВЕСОВ ===
    SMART_WEIGHTS = {
        'penetration': 0.6,  # 60% - "Сколько еще места на рынке?"
        'momentum': 0.4      # 40% - "Как быстро бежим?"
    }
    INFLATION_FLOOR = 0.0  # Пол убран — базовый план = факт 2025
    ROUND_STEP = ROUNDING_STEP  # 10000
    
    # S-кривая для нормализации
    def sigmoid(x, k=1, x0=0):
        return 1 / (1 + np.exp(-k * (x - x0)))
    
    def calculate_score_smart(group_data, network_share_map):
        """Рассчитывает Score без использования площади."""
        # 1. МОМЕНТУМ (ТЯГА)
        prev_rev = group_data['Rev_2024'].replace(0, 1) if 'Rev_2024' in group_data.columns else pd.Series(1, index=group_data.index)
        rev_col = 'Rev_2025_Norm' if 'Rev_2025_Norm' in group_data.columns else 'Rev_2025'
        momentum_raw = np.log1p(group_data[rev_col] / prev_rev)
        score_momentum = sigmoid(momentum_raw, k=2, x0=0.7)
        
        # 2. ПРОНИКНОВЕНИЕ (ПОТЕНЦИАЛ)
        total_rev = group_data[rev_col].sum()
        if total_rev == 0: total_rev = 1
        local_shares = group_data[rev_col] / total_rev
        
        # Целевая доля по формату сети
        fmt = group_data['Формат'].iloc[0] if 'Формат' in group_data.columns else 'Средний'
        target_shares = group_data['Отдел'].apply(lambda x: network_share_map.get((fmt, x), 0.05))
        
        # Gap = Цель / Факт
        penetration_gap = (target_shares / local_shares).replace([np.inf, -np.inf], 1.0).fillna(1.0)
        score_penetration = sigmoid(penetration_gap, k=2, x0=1.0)
        
        # ИТОГОВЫЙ СКОР
        final_score = (
            score_momentum * SMART_WEIGHTS['momentum'] +
            score_penetration * SMART_WEIGHTS['penetration']
        )
        
        # БОНУСЫ ЗА РОЛЬ
        role_multiplier = group_data['Роль'].map({
            'Стратегический': 1.1,  # +10% приоритета
            'Сопутствующий': 0.9    # -10% приоритета
        }).fillna(1.0) if 'Роль' in group_data.columns else pd.Series(1.0, index=group_data.index)
        
        return final_score * role_multiplier
    
    # --- ПРЕДРАСЧЕТ ДОЛЕЙ СЕТИ ---
    rev_col = 'Rev_2025_Norm' if 'Rev_2025_Norm' in result.columns else 'Rev_2025'
    if rev_col in result.columns and 'Формат' in result.columns:
        net_stats = result.groupby(['Формат', 'Отдел'])[rev_col].sum().reset_index()
        fmt_totals = result.groupby(['Формат'])[rev_col].sum().reset_index().rename(columns={rev_col: 'Total'})
        net_stats = pd.merge(net_stats, fmt_totals, on='Формат')
        net_stats['Share'] = net_stats[rev_col] / net_stats['Total']
        NETWORK_SHARE_MAP = net_stats.set_index(['Формат', 'Отдел'])['Share'].to_dict()
    else:
        NETWORK_SHARE_MAP = {}
    
    # --- ПРЕДРАСЧЕТ СЕЗОННОСТИ ПО ОТДЕЛАМ СЕТИ ---
    # Для сезонных отделов (Краски, Стройматериалы, 2В, 10А)
    # Сезонность = доля месяца в годовой выручке отдела по всей сети
    SEASONAL_DEPTS = ['Краски', 'Стройматериалы', '2В', '2в', '10А', '10а']
    DEPT_SEASONALITY_MAP = {}  # {(Отдел, Месяц): сезонность}
    DEPT_YEAR_TOTAL = {}  # {Отдел: годовая сумма}
    
    for dept in result['Отдел'].unique():
        if any(s in str(dept) for s in SEASONAL_DEPTS):
            dept_data = result[result['Отдел'] == dept]
            year_total = dept_data[rev_col].sum()
            DEPT_YEAR_TOTAL[dept] = year_total
            
            for m in range(1, 13):
                month_total = dept_data[dept_data['Месяц'] == m][rev_col].sum()
                seasonality = month_total / year_total if year_total > 0 else 1/12
                DEPT_SEASONALITY_MAP[(dept, m)] = seasonality
    
    # --- ГЛАВНЫЙ ЦИКЛ ПО ФИЛИАЛАМ ---
    for (branch, month), group in result.groupby(['Филиал', 'Месяц']):
        idx = group.index
        
        # 1. ЦЕЛЬ ФИЛИАЛА
        target = result.loc[idx, 'План'].iloc[0]
        if pd.isna(target) or target <= 0: 
            continue
        target = int(round(target))
        
        # Определяем формат
        group_slice = result.loc[idx]
        branch_format = group_slice['Формат'].iloc[0] if 'Формат' in group_slice.columns else 'Средний'
        is_special_branch = branch_format in SPECIAL_FORMATS
        
        # ДЛЯ СПЕЦ-ФОРМАТОВ (Мини/Микро/Интернет) — используем СТАРУЮ логику
        if is_special_branch:
            # Старая логика: водопадное распределение с лимитами
            fixed_mask = has_correction(group_slice)
            strategic_growth_rates = load_strategic_growth_rates()
            if strategic_growth_rates:
                for i, row in group_slice.iterrows():
                    if strategic_growth_rates.get((row['Филиал'], row['Отдел'])) is not None:
                        fixed_mask.loc[i] = True
            
            active_mask = (group_slice['План_Расч'] > 0) & (~fixed_mask)
            active_idx = idx[active_mask]
            
            if len(active_idx) == 0:
                continue
            
            current_sum = result.loc[idx, 'План_Расч'].sum()
            diff = target - current_sum
            
            if diff == 0:
                continue
            
            # Водопадное распределение
            weights = result.loc[active_idx, 'Final_Weight'] if 'Final_Weight' in result.columns else result.loc[active_idx, 'План_Расч']
            w_sum = weights.sum()
            if w_sum > 0:
                shares = weights / w_sum
                result.loc[active_idx, 'План_Расч'] += diff * shares
            
            # Округление
            result.loc[active_idx, 'План_Расч'] = (result.loc[active_idx, 'План_Расч'] / ROUND_STEP).round(0) * ROUND_STEP
            result.loc[active_idx, 'План_Расч'] = result.loc[active_idx, 'План_Расч'].clip(lower=0)
            result.loc[active_idx, 'План_Расч'] = np.where(
                result.loc[active_idx, 'План_Расч'] < MIN_PLAN_THRESHOLD, 
                0, 
                result.loc[active_idx, 'План_Расч']
            )
            
            # Финальная сходимость
            final_sum = result.loc[idx, 'План_Расч'].sum()
            final_residual = target - final_sum
            if final_residual != 0:
                all_plans = result.loc[idx, 'План_Расч']
                if all_plans.max() > 0:
                    max_idx = all_plans.idxmax()
                    result.loc[max_idx, 'План_Расч'] += final_residual
            continue
        
        # ========== КВАДРАТИЧНОЕ ПРОГРАММИРОВАНИЕ (НОВЫЙ ОПТИМИЗАТОР) ==========
        if USE_QP_OPTIMIZER:
            # Собираем фиксированные планы:
            # 1. Двери, Кухни и др. из FIXED_DEPARTMENTS
            # 2. Ручные корректировки (Корр)
            fixed_plans = {}
            for i in idx:
                dept = result.loc[i, 'Отдел']
                
                # Фиксированные отделы (Двери, Кухни, etc.)
                if any(fix in str(dept) for fix in FIXED_DEPARTMENTS):
                    if pd.notna(result.loc[i, 'План_Расч']) and result.loc[i, 'План_Расч'] > 0:
                        fixed_plans[dept] = result.loc[i, 'План_Расч']
                
                # Ручные корректировки (Корр)
                if 'Корр' in result.columns and pd.notna(result.loc[i, 'Корр']):
                    corr_val = result.loc[i, 'Корр']
                    if 'Корр_Дельта' in result.columns and pd.notna(result.loc[i, 'Корр_Дельта']):
                        corr_val += result.loc[i, 'Корр_Дельта']
                    fixed_plans[dept] = corr_val
            
            # Вызываем QP оптимизатор
            branch_data = result.loc[idx].copy()
            optimized = distribute_plan_qp(branch_data, target, fixed_plans)
            
            # Обновляем результаты
            result.loc[idx, 'План_Расч'] = optimized['План_Расч'].values
            continue
        
        # ========== SMART BALANCING v2 ДЛЯ ОБЫЧНЫХ ФОРМАТОВ (LEGACY) ==========
        
        # 2. ФИКСИРОВАННЫЕ (Неприкасаемые)
        is_manual = has_correction(group_slice)
        
        # Спец. ставки из json
        has_rate = pd.Series(False, index=idx)
        strategic_growth_rates = load_strategic_growth_rates()
        acc_growth_rates = load_growth_rates_local()
        
        for i in idx:
            d = result.loc[i, 'Отдел']
            b = result.loc[i, 'Филиал']
            if strategic_growth_rates.get((b, d)) is not None: 
                has_rate.loc[i] = True
            if acc_growth_rates.get((b, d), 0) != 0: 
                has_rate.loc[i] = True
        
        # Двери и Кухни
        is_special_dept = group_slice['Отдел'].str.contains('Двери|Мебель для к', case=False, na=False)
        
        fixed_mask = is_manual | has_rate | is_special_dept
        fixed_sum = result.loc[idx[fixed_mask], 'План_Расч'].sum()
        
        # 3. АКТИВНЫЕ
        rev_col_active = 'Rev_2025_Norm' if 'Rev_2025_Norm' in result.columns else 'Rev_2025'
        active_mask = (~fixed_mask) & (result.loc[idx, rev_col_active] > 0)
        active_idx = idx[active_mask]
        
        residual_target = target - fixed_sum
        
        if len(active_idx) == 0 or residual_target <= 0:
            if len(active_idx) > 0: 
                result.loc[active_idx, 'План_Расч'] = 0
            continue
        
        # 4. ПОЛ (BASE FLOOR)
        rev_25 = result.loc[active_idx, rev_col_active]
        rev_24 = result.loc[active_idx, 'Rev_2024'].replace(0, 1) if 'Rev_2024' in result.columns else pd.Series(1, index=active_idx)
        mom = rev_25 / rev_24
        
        floor_multipliers = pd.Series(1 + INFLATION_FLOOR, index=active_idx)
        
        # Ослабление пола для падающих сопутствующих
        if 'Роль' in result.columns:
            weak_acc = (result.loc[active_idx, 'Роль'] == 'Сопутствующий') & (mom < 0.95)
            floor_multipliers.loc[weak_acc] = 0.95
        
        # БОНУС ДЛЯ СОПУТСТВУЮЩИХ: на каждые 3% прироста стратегических — +1%
        if 'Роль' in result.columns:
            # Считаем средний прирост стратегических в этом филиале/месяце
            strat_mask = result.loc[idx, 'Роль'] == 'Стратегический'
            if strat_mask.any():
                strat_rev_25 = result.loc[idx[strat_mask], rev_col_active].sum()
                strat_rev_24 = result.loc[idx[strat_mask], 'Rev_2024'].sum() if 'Rev_2024' in result.columns else strat_rev_25
                if strat_rev_24 > 0:
                    strat_growth = (strat_rev_25 / strat_rev_24) - 1  # Например 0.09 = +9%
                    if strat_growth > 0:
                        # Бонус = strat_growth / 3 (на каждые 3% прироста -> +1%)
                        acc_bonus = strat_growth / 3
                        # Применяем к сопутствующим
                        acc_mask_active = result.loc[active_idx, 'Роль'] == 'Сопутствующий'
                        floor_multipliers.loc[acc_mask_active] += acc_bonus
        
        base_floor = rev_25 * floor_multipliers
        total_floor = base_floor.sum()
        
        # 5. ДЕЛЬТА И СКОРИНГ
        delta = residual_target - total_floor
        scores = calculate_score_smart(result.loc[active_idx], NETWORK_SHARE_MAP)
        
        # 6. РАСПРЕДЕЛЕНИЕ
        if delta > 0:
            # === ИЗБЫТОК (GROWTH) ===
            dist_weights = result.loc[active_idx, rev_col_active] * (scores ** 2)
            
            if dist_weights.sum() > 0:
                share = dist_weights / dist_weights.sum()
                final_plans = base_floor + (delta * share)
            else:
                final_plans = base_floor
        else:
            # === ДЕФИЦИТ (CUT) — РЕЖЕМ ТОЛЬКО СОПУТСТВУЮЩИХ ===
            # Стратегические сохраняют свой пол
            
            if 'Роль' in result.columns:
                # Разделяем на стратегических и сопутствующих
                strat_active = active_idx[result.loc[active_idx, 'Роль'] != 'Сопутствующий']
                acc_active = active_idx[result.loc[active_idx, 'Роль'] == 'Сопутствующий']
                
                # Стратегические получают свой пол (base_floor)
                final_plans = base_floor.copy()
                
                # Пересчитываем дельту только для сопутствующих
                strat_floor_sum = base_floor.loc[strat_active].sum() if len(strat_active) > 0 else 0
                acc_target = residual_target - strat_floor_sum
                acc_floor_sum = base_floor.loc[acc_active].sum() if len(acc_active) > 0 else 0
                
                if len(acc_active) > 0 and acc_floor_sum > 0:
                    # Режем только сопутствующих пропорционально
                    if acc_target >= acc_floor_sum:
                        # Хватает денег — даём пол
                        pass  # final_plans уже = base_floor
                    else:
                        # Дефицит — режем сопутствующих пропорционально
                        acc_ratio = acc_target / acc_floor_sum if acc_floor_sum > 0 else 0
                        final_plans.loc[acc_active] = base_floor.loc[acc_active] * max(0, acc_ratio)
            else:
                # Нет колонки Роль — старая логика
                max_score = scores.max() + 0.1
                weakness = max_score - scores
                cut_weights = result.loc[active_idx, rev_col_active] * (weakness ** 2)
                if cut_weights.sum() > 0:
                    share = cut_weights / cut_weights.sum()
                    final_plans = base_floor + (delta * share)
                else:
                    ratio = residual_target / total_floor if total_floor > 0 else 0
                    final_plans = base_floor * ratio
        
        # ОГРАНИЧЕНИЕ: Обои — не более +8% прироста и не ниже 0%
        MAX_GROWTH_LIMITED = 0.08
        MIN_GROWTH_LIMITED = 0.0  # Не ниже факта 2025
        for i in active_idx:
            dept_name = result.loc[i, 'Отдел']
            if 'Обои' in str(dept_name):
                fact_val = result.loc[i, rev_col_active]
                max_plan = fact_val * (1 + MAX_GROWTH_LIMITED)
                min_plan = fact_val * (1 + MIN_GROWTH_LIMITED)  # = факт
                final_plans.loc[i] = max(min(final_plans.loc[i], max_plan), min_plan)
        
        # ОГРАНИЧЕНИЕ: 9А — только максимум +8% (без минимального пола)
        for i in active_idx:
            dept_name = result.loc[i, 'Отдел']
            if '9А' in str(dept_name) or '9а' in str(dept_name):
                fact_val = result.loc[i, rev_col_active]
                max_plan = fact_val * (1 + MAX_GROWTH_LIMITED)
                final_plans.loc[i] = min(final_plans.loc[i], max_plan)
        
        # СЕЗОННЫЕ ОТДЕЛЫ: Краски, Стройматериалы, 2В, 10А — план по сезонности сети
        for i in active_idx:
            dept_name = result.loc[i, 'Отдел']
            if any(s in str(dept_name) for s in SEASONAL_DEPTS):
                # Годовой факт филиала для этого отдела
                branch_dept_mask = (result['Филиал'] == branch) & (result['Отдел'] == dept_name)
                branch_year_fact = result.loc[branch_dept_mask, rev_col_active].sum()
                
                # Сезонность по сети для этого отдела и месяца
                seasonality = DEPT_SEASONALITY_MAP.get((dept_name, month), 1/12)
                
                # План = Годовой_Факт_Филиала × Сезонность_Сети
                seasonal_plan = branch_year_fact * seasonality
                
                # ОГРАНИЧЕНИЕ: 2. Стройматериалы, 2Б, 2В — максимум +6% прироста (2А исключён)
                if '2. Стройматериалы' in str(dept_name) or 'Стройматериалы' in str(dept_name) or '2Б' in str(dept_name) or '2В' in str(dept_name) or '2б' in str(dept_name) or '2в' in str(dept_name):
                    fact_month = result.loc[i, rev_col_active]
                    max_plan = fact_month * 1.06
                    seasonal_plan = min(seasonal_plan, max_plan)
                
                final_plans.loc[i] = seasonal_plan
        
        # 7. ОКРУГЛЕНИЕ
        result.loc[active_idx, 'План_Расч'] = final_plans
        result.loc[active_idx, 'План_Расч'] = (result.loc[active_idx, 'План_Расч'] / ROUND_STEP).round(0) * ROUND_STEP
        
        # Минимальный порог
        result.loc[active_idx, 'План_Расч'] = np.where(
            result.loc[active_idx, 'План_Расч'] < MIN_PLAN_THRESHOLD,
            0,
            result.loc[active_idx, 'План_Расч']
        )
        
        # 8. 100% СХОДИМОСТЬ
        current_total = result.loc[idx, 'План_Расч'].sum()
        diff_final = target - current_total
        
        if diff_final != 0:
            # Большой остаток — на крупнейший активный
            if abs(diff_final) >= ROUND_STEP and len(active_idx) > 0:
                best_candidate = result.loc[active_idx, 'План_Расч'].idxmax()
                result.loc[best_candidate, 'План_Расч'] += diff_final
            # Маленький остаток — на любой крупнейший
            elif abs(diff_final) < ROUND_STEP:
                all_plans = result.loc[idx, 'План_Расч']
                if all_plans.max() > 0:
                    max_idx = all_plans.idxmax()
                    result.loc[max_idx, 'План_Расч'] += diff_final

    # ========== ШАГ 13.5: ПРАВИЛО +6% ДЛЯ СОПУТСТВУЮЩИХ (после балансировки) ==========
    # Для спец-форматов: Сопутствующие должны иметь минимум +6% к Факту_2025
    # ИСКЛЮЧЕНИЕ: максимальный месяц по продажам
    # ИСКЛЮЧЕНИЕ 2: если в таблице приростов указано значение < 0
    MIN_GROWTH_FINAL = 0.06  # +6%
    
    # Загружаем таблицу приростов для проверки отрицательных значений
    growth_rates_for_rule = {}
    growth_file = os.path.join(DATA_DIR, 'growth_rates.json')
    if os.path.exists(growth_file):
        try:
            with open(growth_file, 'r', encoding='utf-8') as f:
                growth_data = json.load(f)
                for item in growth_data:
                    growth_rates_for_rule[(item['branch'], item['dept'])] = item['rate']
        except:
            pass
    
    for (branch, month), group in result.groupby(['Филиал', 'Месяц']):
        grp_idx = group.index
        
        # Только для спец-форматов
        branch_format = result.loc[grp_idx, 'Формат'].iloc[0] if 'Формат' in result.columns else None
        if branch_format not in SPECIAL_FORMATS:
            continue
        
        target = result.loc[grp_idx, 'План'].iloc[0]
        if pd.isna(target):
            continue
        target = int(round(target))
        
        total_increase = 0  # Сколько добавили Сопутствующим
        
        for idx in grp_idx:
            role = result.loc[idx, 'Роль'] if 'Роль' in result.columns else 'Стратегический'
            if role != 'Сопутствующий':
                continue
            
            # Используем нормализованную выручку если есть (для филиалов на ремонте)
            rev_2025_norm = result.loc[idx, 'Rev_2025_Norm'] if 'Rev_2025_Norm' in result.columns else None
            rev_2025 = result.loc[idx, 'Rev_2025'] if 'Rev_2025' in result.columns else 0
            
            # Для расчёта используем нормализованную выручку (учитывает ремонт)
            base_rev = rev_2025_norm if (pd.notna(rev_2025_norm) and rev_2025_norm > 0) else rev_2025
            
            if pd.isna(base_rev) or base_rev <= 0:
                continue
            
            dept = result.loc[idx, 'Отдел']
            branch_name = result.loc[idx, 'Филиал']
            
            # Получаем кастомный прирост из таблицы
            custom_growth = growth_rates_for_rule.get((branch_name, dept))
            
            # Если прирост отрицательный — применяем его (уменьшаем план)
            if custom_growth is not None and custom_growth < 0:
                # Например: -20 означает план = База * 0.80 (используем нормализованную выручку)
                target_plan = base_rev * (1 + custom_growth / 100)  # custom_growth уже в процентах
                target_plan_rounded = int(round(target_plan / ROUNDING_STEP)) * ROUNDING_STEP
                
                # Обнуляем если < 30000
                if target_plan_rounded < MIN_PLAN_THRESHOLD:
                    target_plan_rounded = 0
                
                current_plan = result.loc[idx, 'План_Расч']
                
                if current_plan > target_plan_rounded:
                    # Уменьшаем план — освобождаем сумму для стратегических
                    freed = current_plan - target_plan_rounded
                    result.loc[idx, 'План_Расч'] = target_plan_rounded
                    total_increase -= freed  # Отрицательное — значит освободили
                continue
            
            # Проверяем: максимальный месяц? (используем фактическую выручку для сравнения)
            max_rev_year = max_rev_2025_by_branch_dept.get((branch_name, dept), 0)
            is_max_month = (rev_2025 >= max_rev_year * 0.999)
            
            if is_max_month:
                continue  # Для max месяца +6% не применяем
            
            # Используем нормализованную выручку для расчёта +6%
            min_plan = base_rev * (1 + MIN_GROWTH_FINAL)
            min_plan_rounded = int(round(min_plan / ROUNDING_STEP)) * ROUNDING_STEP
            
            # Обнуляем если < 30000
            if min_plan_rounded < MIN_PLAN_THRESHOLD:
                min_plan_rounded = 0
            
            current_plan = result.loc[idx, 'План_Расч']
            
            if current_plan < min_plan_rounded:
                increase = min_plan_rounded - current_plan
                result.loc[idx, 'План_Расч'] = min_plan_rounded
                total_increase += increase
        
        # Перераспределяем: + = уменьшаем стратегических, - = увеличиваем стратегических
        if total_increase != 0:
            strat_mask = (result.loc[grp_idx, 'Роль'] == 'Стратегический') & (result.loc[grp_idx, 'План_Расч'] > 0)
            strat_idx = grp_idx[strat_mask]
            
            if len(strat_idx) > 0:
                # Исключаем отделы с strategic_rate
                strategic_growth_rates_inner = load_strategic_growth_rates()
                adjustable_strat = []
                for idx in strat_idx:
                    dept = result.loc[idx, 'Отдел']
                    branch_name = result.loc[idx, 'Филиал']
                    if strategic_growth_rates_inner.get((branch_name, dept)) is None:
                        adjustable_strat.append(idx)
                
                strat_idx = pd.Index(adjustable_strat)
                
                if len(strat_idx) == 0:
                    continue  # Все стратегические фиксированы по rate
                
                # Изменяем пропорционально весам
                strat_plans = result.loc[strat_idx, 'План_Расч']
                total_strat = strat_plans.sum()
                
                if total_strat > 0:
                    shares = strat_plans / total_strat
                    # total_increase > 0 — уменьшаем стратегических
                    # total_increase < 0 — увеличиваем стратегических (освободили от сопутствующих)
                    delta = shares * total_increase
                    result.loc[strat_idx, 'План_Расч'] -= delta
                    
                    # Стандартное округление Стратегических
                    result.loc[strat_idx, 'План_Расч'] = (result.loc[strat_idx, 'План_Расч'] / ROUNDING_STEP).round(0) * ROUNDING_STEP
                    
                    # Обнуляем те, что меньше порога (< 30000) и перераспределяем
                    below_min = result.loc[strat_idx, 'План_Расч'] < MIN_PLAN_THRESHOLD
                    below_min_idx = strat_idx[below_min]
                    if len(below_min_idx) > 0:
                        freed_amount = result.loc[below_min_idx, 'План_Расч'].sum()
                        result.loc[below_min_idx, 'План_Расч'] = 0
                        # Добавляем освободившуюся сумму к крупнейшему
                        remaining_strat = strat_idx[~below_min]
                        if len(remaining_strat) > 0:
                            max_strat_idx = result.loc[remaining_strat, 'План_Расч'].idxmax()
                            result.loc[max_strat_idx, 'План_Расч'] += freed_amount
                    
                    # Корректируем остаток на крупнейшем
                    new_sum = result.loc[grp_idx, 'План_Расч'].sum()
                    residual = target - new_sum
                    if residual != 0:
                        # Находим крупнейший отдел (любой роли) с планом > 0
                        active_plans = result.loc[grp_idx, 'План_Расч']
                        active_nonzero = active_plans[active_plans >= MIN_PLAN_THRESHOLD]
                        if len(active_nonzero) > 0:
                            max_idx = active_nonzero.idxmax()
                            result.loc[max_idx, 'План_Расч'] += residual

    # ========== ШАГ 14: Финализация ==========
    result['План_Скорр'] = result['План_Расч'].copy()
    
    # ПРИМЕНЕНИЕ РУЧНЫХ КОРРЕКТИРОВОК
    # Корр — абсолютное значение плана (включая 0)
    if 'Корр' in result.columns:
        # Применяем если Корр указан (не NaN), включая значение 0
        corr_mask = result['Корр'].notna()
        if corr_mask.any():
            result.loc[corr_mask, 'План_Скорр'] = result.loc[corr_mask, 'Корр']
    
    # Корр_Дельта — дельта к скорректированному плану (применяется если нет абсолютной корректировки)
    if 'Корр_Дельта' in result.columns:
        delta_mask = result['Корр_Дельта'].notna() & (result['Корр_Дельта'] != 0)
        # Применяем дельту только если нет абсолютной корректировки
        if 'Корр' in result.columns:
            delta_mask = delta_mask & result['Корр'].isna()
        if delta_mask.any():
            # Применяем к План_Скорр (после балансировки), не к План_Расч!
            result.loc[delta_mask, 'План_Скорр'] = result.loc[delta_mask, 'План_Скорр'] + result.loc[delta_mask, 'Корр_Дельта']
    
    # Убедимся что План_Скорр >= 0
    result['План_Скорр'] = result['План_Скорр'].clip(lower=0)
    
    # ПЕРЕБАЛАНСИРОВКА после корректировок для сохранения сходимости
    # Для каждого филиала/месяца: если сумма изменилась из-за корректировок, 
    # перераспределяем разницу на некорректированные отделы
    for (branch, month), group in result.groupby(['Филиал', 'Месяц']):
        grp_idx = group.index
        
        target = result.loc[grp_idx, 'План'].iloc[0]
        if pd.isna(target) or target <= 0:
            continue
        target = int(round(target))
        
        current_sum = result.loc[grp_idx, 'План_Скорр'].sum()
        diff = target - current_sum
        
        if abs(diff) < 1000:  # Мелкие расхождения игнорируем
            continue
        
        # Определяем отделы с ручными корректировками (их не трогаем)
        # Корр указан (включая 0) = корректировка есть
        has_corr = result.loc[grp_idx, 'Корр'].notna() if 'Корр' in result.columns else pd.Series(False, index=grp_idx)
        has_delta = (result.loc[grp_idx, 'Корр_Дельта'].notna() & (result.loc[grp_idx, 'Корр_Дельта'] != 0)) if 'Корр_Дельта' in result.columns else pd.Series(False, index=grp_idx)
        is_corrected = has_corr | has_delta
        
        # Некорректированные отделы с планом > MIN_PLAN_THRESHOLD
        adjustable_mask = ~is_corrected & (result.loc[grp_idx, 'План_Скорр'] >= MIN_PLAN_THRESHOLD)
        adjustable_idx = grp_idx[adjustable_mask]
        
        if len(adjustable_idx) == 0:
            # Нет некорректированных отделов, но маленький остаток всё равно нужно обработать
            if abs(diff) < ROUNDING_STEP and diff != 0:
                all_plans = result.loc[grp_idx, 'План_Скорр']
                if all_plans.max() > 0:
                    max_idx_any = all_plans.idxmax()
                    result.loc[max_idx_any, 'План_Скорр'] += diff
            continue
        
        # Перераспределяем разницу пропорционально весам
        adjustable_plans = result.loc[adjustable_idx, 'План_Скорр']
        total_adjustable = adjustable_plans.sum()
        
        if total_adjustable > 0:
            shares = adjustable_plans / total_adjustable
            adjustment = shares * diff
            result.loc[adjustable_idx, 'План_Скорр'] += adjustment
            
            # Округляем
            result.loc[adjustable_idx, 'План_Скорр'] = (result.loc[adjustable_idx, 'План_Скорр'] / ROUNDING_STEP).round(0) * ROUNDING_STEP
            
            # Финальная корректировка остатка на крупнейшем
            new_sum = result.loc[grp_idx, 'План_Скорр'].sum()
            final_residual = target - new_sum
            
            # Большой остаток (>= 10000) — добавляем к некорректированному
            if abs(final_residual) >= ROUNDING_STEP and len(adjustable_idx) > 0:
                max_idx = result.loc[adjustable_idx, 'План_Скорр'].idxmax()
                result.loc[max_idx, 'План_Скорр'] += final_residual
            # Маленький остаток (< 10000) — добавляем к ЛЮБОМУ крупнейшему для сходимости
            elif final_residual != 0 and abs(final_residual) < ROUNDING_STEP:
                all_plans = result.loc[grp_idx, 'План_Скорр']
                if all_plans.max() > 0:
                    max_idx_any = all_plans.idxmax()
                    result.loc[max_idx_any, 'План_Скорр'] += final_residual
    
    # DEBUG: Кострома Стройка - сходимость
    kostroma_debug = result[result['Филиал'].str.contains('Кострома Стройка', na=False)]
    with open('/tmp/debug_kostroma.txt', 'w') as df:
        for month in [2, 12]:
            m_data = kostroma_debug[kostroma_debug['Месяц'] == month]
            if len(m_data) > 0:
                target = m_data['План'].iloc[0]
                total = m_data['План_Скорр'].sum()
                df.write(f"Month={month}: Target={target}, Total={total}, Diff={target-total}\n")
    
    # DEBUG: Рыбинск Покрытия
    ryb_debug = result[(result['Отдел'].str.contains('Покрытия напольные', na=False)) & 
                       (result['Филиал'].str.contains('Рыбинск', na=False))]
    with open('/tmp/debug_rybinsk_pokrytia.txt', 'w') as df:
        for _, row in ryb_debug.iterrows():
            df.write(f"Month={row['Месяц']}, План_Скорр={row['План_Скорр']}, План_Расч={row['План_Расч']}, Корр={row.get('Корр')}, Корр_Дельта={row.get('Корр_Дельта')}\n")
    
    # DEBUG: Final values for 2В. Металлопрокат
    metal_final = result[(result['Отдел'].str.contains('2В. Металлопрокат', na=False)) & 
                         (result['Филиал'].str.contains('Владимир Лента', na=False))]
    with open('/tmp/final_metal_debug.txt', 'w') as df:
        for _, row in metal_final.iterrows():
            df.write(f"Month={row['Месяц']}, План_Скорр={row['План_Скорр']}, План_Расч={row['План_Расч']}\n")
    
    # DEBUG: Вологда финальные значения
    import json
    vologda_final = result[(result['Филиал'].str.contains('Вологда', na=False)) & (result['Месяц'] == 1)][
        ['Филиал', 'Отдел', 'Роль', 'Rev_2025', 'План_Скорр', 'План_Расч']
    ].copy()
    vologda_final['Прирост_%'] = ((vologda_final['План_Скорр'] / vologda_final['Rev_2025']) - 1) * 100
    vologda_final = vologda_final.round(1).to_dict('records')
    
    with open('/tmp/debug_vologda_final.json', 'w', encoding='utf-8') as f:
        json.dump(vologda_final, f, ensure_ascii=False, indent=2)
    
    # DEBUG: Владимир Лента отделы с rate
    vlad_oboi = result[(result['Филиал'] == 'Владимир Лента') & (result['Отдел'].str.contains('Обои', na=False))].copy()
    vlad_oboi_sum = vlad_oboi['План_Расч'].sum()
    vlad_oboi_rev = vlad_oboi['Rev_2025'].sum() if 'Rev_2025' in vlad_oboi.columns else 0
    with open('/tmp/debug_vlad_oboi.json', 'w') as f:
        json.dump({
            'year_plan': float(vlad_oboi_sum),
            'year_rev_2025': float(vlad_oboi_rev),
            'growth_pct': float((vlad_oboi_sum / vlad_oboi_rev - 1) * 100) if vlad_oboi_rev > 0 else 0,
            'months': len(vlad_oboi),
            'precalc_target': 13070000  # from precalc
        }, f, indent=2)

    # DEBUG: Проверяем финальные значения
    debug_df = result[(result['Филиал'] == 'Владимир Лента') & (result['Отдел'] == '1А. Сантехника инженерная')]
    with open('/tmp/final_debug.txt', 'w') as f:
        f.write("=== ФИНАЛЬНЫЕ ЗНАЧЕНИЯ 1А ===\n")
        for _, row in debug_df.sort_values('Месяц').iterrows():
            m = row['Месяц']
            plan = row['План_Скорр']
            seas = row['Seasonality_Share']
            f.write(f"Месяц {m}: План={plan:,.0f}, Seas_Сеть={seas:.4f} ({seas*100:.2f}%)\n")
        f.write(f"\nСумма плана: {debug_df['План_Скорр'].sum():,.0f}\n")
        f.write(f"Сумма сезонности: {debug_df['Seasonality_Share'].sum():.6f}\n")

    # ========== ШАГ 14: Расчёт дополнительных колонок ==========
    
    # Прирост к 2025
    result['Прирост_%'] = calc_growth_pct(result['План_Скорр'], result['Rev_2025'])
    
    # Прирост к 2024
    result['Прирост_24_26_%'] = calc_growth_pct(result['План_Скорр'], result['Rev_2024'])
    
    # Переименовываем колонки для совместимости
    result['Выручка_2024'] = result['Rev_2024']
    result['Выручка_2025'] = result['Rev_2025']
    result['Выручка_2025_Норм'] = result['Rev_2025_Norm']
    
    # Сезонность факт (доля месяца в году по выручке 2025)
    year_2025_by_dept = result.groupby(['Филиал', 'Отдел'])['Rev_2025'].transform('sum')
    result['Сезонность_Факт'] = np.where(
        year_2025_by_dept > 0,
        (result['Rev_2025'] / year_2025_by_dept) * 100,
        0.0
    )
    
    # Сезонность план (доля месяца в году по плану)
    year_plan_by_dept = result.groupby(['Филиал', 'Отдел'])['План_Скорр'].transform('sum')
    result['Сезонность_План'] = np.where(
        year_plan_by_dept > 0,
        (result['План_Скорр'] / year_plan_by_dept) * 100,
        0.0
    )
    
    # Годовой прирост отдела (План_Год / Факт_2025_Год - 1) × 100
    # Одинаковое значение для всех месяцев в рамках (Филиал, Отдел)
    year_fact_by_dept = result.groupby(['Филиал', 'Отдел'])['Rev_2025'].transform('sum')
    result['Прирост_Год_%'] = np.where(
        year_fact_by_dept > 0,
        ((year_plan_by_dept / year_fact_by_dept) - 1) * 100,
        0.0
    )
    result['Прирост_Год_%'] = result['Прирост_Год_%'].round(1)
    
    # DEBUG: Проверка колонки Прирост_Год_%
    import json
    debug_growth_year = {
        'column_exists': 'Прирост_Год_%' in result.columns,
        'all_columns': list(result.columns),
        'sample_values': result[['Филиал', 'Отдел', 'Месяц', 'Прирост_Год_%']].head(20).to_dict('records') if 'Прирост_Год_%' in result.columns else []
    }
    with open('/tmp/debug_growth_year.json', 'w', encoding='utf-8') as f:
        json.dump(debug_growth_year, f, ensure_ascii=False, indent=2)
    
    # Рекомендуемый план (План_Расч до корректировок) 
    result['Рекоменд'] = result['План_Расч'].copy()

    # Удаляем служебные колонки
    cols_to_drop = ['_is_no_plan', '_is_only_2025', '_is_2024_2025', '_is_format', '_is_format_only', 
                    '_base', '_total_base', 'Network_Month', 'Format_Network_Month']
    result = result.drop(columns=[c for c in cols_to_drop if c in result.columns], errors='ignore')

    # ========== ШАГ 15: Площади и Отдача ==========
    
    # Загружаем площади
    try:
        df_area_full = load_areas()
    except:
        df_area_full = None
    
    if df_area_full is not None and not df_area_full.empty:
        # Площадь 2025
        area_2025 = df_area_full[df_area_full['Год'] == 2025][['Филиал', 'Отдел', 'Месяц', 'Площадь']]
        area_2025.columns = ['Филиал', 'Отдел', 'Месяц', 'Площадь_2025']
        
        # Площадь 2026 (пока берем как 2025, если нет данных, или если есть - используем 2026)
        # Если в ref файле есть 2026, используем его
        area_2026 = df_area_full[df_area_full['Год'] == 2026][['Филиал', 'Отдел', 'Месяц', 'Площадь']]
        if area_2026.empty:
             area_2026 = area_2025.copy()
             area_2026.columns = ['Филиал', 'Отдел', 'Месяц', 'Площадь_2026']
        else:
             area_2026.columns = ['Филиал', 'Отдел', 'Месяц', 'Площадь_2026']

        result = pd.merge(result, area_2025, on=['Филиал', 'Отдел', 'Месяц'], how='left')
        result = pd.merge(result, area_2026, on=['Филиал', 'Отдел', 'Месяц'], how='left')
        
    else:
        result['Площадь_2025'] = 0
        result['Площадь_2026'] = 0

    result['Площадь_2025'] = result['Площадь_2025'].fillna(0)
    result['Площадь_2026'] = result['Площадь_2026'].fillna(0)
    
    # Delta Area
    result['Δ_Площадь_%'] = np.where(
        result['Площадь_2025'] > 0,
        ((result['Площадь_2026'] - result['Площадь_2025']) / result['Площадь_2025']) * 100,
        0
    )

    # Отдача (Выручка / Площадь)
    # Отдача 2025
    result['Отдача_2025'] = np.where(
        result['Площадь_2025'] > 0,
        result['Rev_2025'] / result['Площадь_2025'],
        0
    )
    result['Отдача_2025'] = result['Отдача_2025'].round(0).astype(int)

    # Отдача План (2026)
    result['Отдача_План'] = np.where(
        result['Площадь_2026'] > 0,
        result['План_Скорр'] / result['Площадь_2026'],
        0
    )
    result['Отдача_План'] = result['Отдача_План'].round(0).astype(int)

    # Delta Efficiency
    result['Δ_Отдача_%'] = np.where(
        result['Отдача_2025'] > 0,
        ((result['Отдача_План'] - result['Отдача_2025']) / result['Отдача_2025']) * 100,
        0
    )

    # Restore/Enable requested columns
    # _План_Расч_Исх (Original/Base)
    if '_theoretical' in result.columns:
        result['_План_Расч_Исх'] = result['_theoretical'].fillna(0)
    elif 'Рекоменд' in result.columns:
        result['_План_Расч_Исх'] = result['Рекоменд']
    else:
        result['_План_Расч_Исх'] = result['План_Расч']

    # Авто_Корр
    if 'Авто_Корр' not in result.columns:
        result['Авто_Корр'] = 0 
        
    return result



@st.cache_data(ttl=300, show_spinner=False)
def load_raw_data():
    """
    Загружает данные продаж из Google Sheets (полная логика из ноутбука)
    
    1. Основные продажи из Google Sheets
    2. Корректировки продаж Владимир (вычеты/добавления)
    3. Агрегация и очистка данных
    """
    
    try:
        # ========== 1. ОСНОВНЫЕ ПРОДАЖИ ==========
        sales_url = f'https://docs.google.com/spreadsheets/d/{SALES_SHEET_ID}/export?format=csv'
        df_sales = pd.read_csv(sales_url)
        
        # Очистка данных
        df_sales['Выручка'] = df_sales['Выручка'].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
        df_sales['Выручка'] = pd.to_numeric(df_sales['Выручка'], errors='coerce').fillna(0)
        df_sales['Филиал'] = df_sales['Филиал'].astype(str).str.strip()
        df_sales['Отдел'] = df_sales['Отдел'].astype(str).str.strip()
        df_sales['Месяц'] = df_sales['Месяц'].astype(str).str.strip()
        
        # Удаление дубликатов
        df_sales.drop_duplicates(subset=['Филиал', 'Отдел', 'Год', 'Месяц', 'Выручка'], inplace=True)
        
        # Агрегация
        agg_cols = {'Выручка': 'sum'}
        if 'Чеки' in df_sales.columns:
            agg_cols['Чеки'] = 'sum'
        df_sales = df_sales.groupby(['Филиал', 'Отдел', 'Год', 'Месяц'], as_index=False).agg(agg_cols)
        
        # ========== 2. КОРРЕКТИРОВКИ ПРОДАЖ ВЛАДИМИР ==========
        try:
            corr_url = f'https://docs.google.com/spreadsheets/d/{SALES_SHEET_ID}/export?format=csv&gid={SALES_CORRECTIONS_GID}'
            df_corr = pd.read_csv(corr_url)
            
            # Melt: месяцы из колонок в строки
            id_vars = [c for c in ['Филиал', 'Отдел', 'Код эксперта', 'Филиал Корр'] if c in df_corr.columns]
            month_cols = [c for c in df_corr.columns if c not in id_vars]
            
            if 'Филиал Корр' in id_vars and month_cols:
                df_corr = df_corr.melt(id_vars=id_vars, var_name='Месяц', value_name='Выручка')
                df_corr['Выручка'] = df_corr['Выручка'].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
                df_corr['Выручка'] = pd.to_numeric(df_corr['Выручка'], errors='coerce')
                df_corr = df_corr.dropna(subset=['Выручка'])
                df_corr['Год'] = 2025
                
                # Сводная таблица корректировок
                df_summary = df_corr.groupby(['Филиал', 'Отдел', 'Филиал Корр', 'Месяц'], as_index=False)['Выручка'].sum()
                
                # Вычеты (из исходного филиала)
                deductions = df_summary.groupby(['Филиал', 'Отдел', 'Месяц'])['Выручка'].sum().reset_index()
                deductions.columns = ['Филиал', 'Отдел', 'Месяц', 'Deduction']
                deductions['Год'] = 2025
                
                # Добавления (в целевой филиал)
                additions_temp = df_summary[['Филиал Корр', 'Отдел', 'Месяц', 'Выручка']].rename(columns={'Филиал Корр': 'Филиал'})
                additions = additions_temp.groupby(['Филиал', 'Отдел', 'Месяц'])['Выручка'].sum().reset_index()
                additions.columns = ['Филиал', 'Отдел', 'Месяц', 'Addition']
                additions['Год'] = 2025
                
                # Применяем вычеты
                df_sales = pd.merge(df_sales, deductions, on=['Филиал', 'Отдел', 'Месяц', 'Год'], how='left')
                df_sales['Выручка'] = df_sales['Выручка'] - df_sales['Deduction'].fillna(0)
                df_sales.drop(columns=['Deduction'], inplace=True)
                
                # Применяем добавления
                df_sales = pd.merge(df_sales, additions, on=['Филиал', 'Отдел', 'Месяц', 'Год'], how='left')
                df_sales['Выручка'] = df_sales['Выручка'] + df_sales['Addition'].fillna(0)
                df_sales.drop(columns=['Addition'], inplace=True)
                
        except Exception as e:
            st.warning(f"Корректировки Владимир не загружены: {e}")
        
        # ========== 3. ФИНАЛЬНАЯ ОБРАБОТКА ==========
        df_sales['Выручка'] = df_sales['Выручка'].fillna(0).round(0).astype(int)
        df_sales['Месяц'] = df_sales['Месяц'].apply(parse_month)
        df_sales['Год'] = pd.to_numeric(df_sales['Год'], errors='coerce').fillna(0).astype(int)
        
        return df_sales
        
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_rules():
    """Загружает правила расчёта из Google Sheets"""
    try:
        url = f'https://docs.google.com/spreadsheets/d/{REFS_SHEET_ID}/export?format=csv&gid={RULES_GID}'
        df_rules = pd.read_csv(url)
        # Преобразуем wide в long формат
        df_rules_melted = df_rules.melt(id_vars=['Отдел'], var_name='Филиал', value_name='Правило')
        df_rules_melted['Филиал'] = df_rules_melted['Филиал'].astype(str).str.strip()
        df_rules_melted['Отдел'] = df_rules_melted['Отдел'].astype(str).str.strip()
        return df_rules_melted
    except Exception as e:
        st.warning(f"Правила не загружены: {e}")
        return None


@st.cache_data(ttl=300)
def load_roles():
    """Загружает роли отделов из Google Sheets"""
    try:
        url = f'https://docs.google.com/spreadsheets/d/{REFS_SHEET_ID}/export?format=csv&gid={ROLES_GID}'
        df_roles = pd.read_csv(url)
        df_roles['Отдел'] = df_roles['Отдел'].astype(str).str.strip()
        df_roles['Роль'] = df_roles['Роль'].astype(str).str.strip()
        return df_roles
    except Exception as e:
        st.warning(f"Роли не загружены: {e}")
        return None


@st.cache_data(ttl=300)
def load_branch_plans():
    """
    Загружает ЦЕЛЕВЫЕ ПЛАНЫ ФИЛИАЛОВ 2026 из Google Sheets
    Формат: Филиал | янв | фев | ... | дек
    Возвращает: DataFrame с колонками [Филиал, Месяц, План]
    """
    try:
        url = f'https://docs.google.com/spreadsheets/d/{PLAN_SHEET_ID}/export?format=csv'
        df = pd.read_csv(url)
        
        # Преобразуем wide в long формат (месяцы из колонок в строки)
        df_plan = df.melt(id_vars=['Филиал'], var_name='Месяц', value_name='План')
        
        # Нормализация
        df_plan['Филиал'] = df_plan['Филиал'].astype(str).str.strip()
        df_plan['Месяц'] = df_plan['Месяц'].astype(str).str.strip().str.lower()
        df_plan['Месяц'] = df_plan['Месяц'].apply(parse_month)
        df_plan['План'] = pd.to_numeric(df_plan['План'], errors='coerce').fillna(0)
        
        return df_plan
        
    except Exception as e:
        st.warning(f"Целевые планы не загружены: {e}")
        return None


@st.cache_data(ttl=300)
def load_areas():
    """
    Загружает ПЛОЩАДИ МАГАЗИНОВ из Google Sheets (как в ноутбуке)
    Формат: Год | Месяц | Отдел | Филиал1 | Филиал2 | ...
    Возвращает: DataFrame с колонками [Филиал, Отдел, Месяц, Год, Площадь]
    """
    try:
        url = f'https://docs.google.com/spreadsheets/d/{REFS_SHEET_ID}/export?format=csv'
        df_area = pd.read_csv(url)
        
        # Преобразование (unpivot): филиалы из колонок в строки
        df_area = df_area.melt(id_vars=['Год', 'Месяц', 'Отдел'], var_name='Филиал', value_name='Площадь')
        
        # Создание полной сетки (Grid) для всех комбинаций
        months_order = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
        month_map_local = {m: i+1 for i, m in enumerate(months_order)}
        
        branches = df_area['Филиал'].unique()
        departments = df_area['Отдел'].unique()
        years = [2023, 2024, 2025, 2026]
        
        index = pd.MultiIndex.from_product([branches, departments, years, months_order], 
                                           names=['Филиал', 'Отдел', 'Год', 'Месяц'])
        df_full = pd.DataFrame(index=index).reset_index()
        df_full['Month_Num'] = df_full['Месяц'].map(month_map_local)
        
        # Объединяем с исходными данными
        df_merged = pd.merge(df_full, df_area, on=['Филиал', 'Отдел', 'Год', 'Месяц'], how='left')
        df_merged = df_merged.sort_values(by=['Филиал', 'Отдел', 'Год', 'Month_Num'])
        
        # Forward fill для заполнения пропусков
        df_merged['Площадь'] = df_merged.groupby(['Филиал', 'Отдел'])['Площадь'].ffill()
        
        # Фильтрация: только 2024+
        df_merged = df_merged[df_merged['Год'] >= 2024]
        
        # Возвращаем числовой месяц!
        df_merged = df_merged.drop(columns=['Месяц']).rename(columns={'Month_Num': 'Месяц'})
        
        return df_merged[['Филиал', 'Отдел', 'Месяц', 'Год', 'Площадь']]
        
    except Exception as e:
        st.warning(f"Площади не загружены: {e}")
        return None


def prepare_baseline(df_sales, df_area):
    """
    Корректировка выручки при изменении площадей (как в ноутбуке)
    
    Если площадь отдела изменилась, выручка за 3 месяца до изменения 
    корректируется по тренду сети (чтобы избежать искажения базы)
    """
    if df_area is None or df_area.empty:
        return df_sales
    
    df_s = df_sales.copy()
    df_s['Month_Num'] = df_s['Месяц'].apply(parse_month) if df_s['Месяц'].dtype == 'object' else df_s['Месяц']
    df_s['Date'] = pd.to_datetime(df_s['Год'].astype(str) + '-' + df_s['Month_Num'].astype(str) + '-01')
    
    # Выручка прошлого года
    df_py = df_s[['Филиал', 'Отдел', 'Год', 'Month_Num', 'Выручка']].copy()
    df_py['Год'] = df_py['Год'] + 1
    df_py.columns = ['Филиал', 'Отдел', 'Год', 'Month_Num', 'Выручка_PY']
    
    df_merged = pd.merge(df_s, df_py, on=['Филиал', 'Отдел', 'Год', 'Month_Num'], how='left')
    
    # Тренд сети
    network_sales = df_s.groupby(['Год', 'Month_Num'])['Выручка'].sum().reset_index()
    network_sales_py = network_sales.copy()
    network_sales_py['Год'] += 1
    network_sales_py.columns = ['Год', 'Month_Num', 'Выручка_PY_Network']
    
    df_trend = pd.merge(network_sales, network_sales_py, on=['Год', 'Month_Num'], how='left')
    df_trend['Trend_Network'] = (df_trend['Выручка'] / df_trend['Выручка_PY_Network']).fillna(1.0)
    df_merged = pd.merge(df_merged, df_trend[['Год', 'Month_Num', 'Trend_Network']], on=['Год', 'Month_Num'], how='left')
    
    # Обработка площадей
    df_a = df_area.copy()
    df_a['Month_Num'] = df_a['Месяц'].apply(parse_month) if df_a['Месяц'].dtype == 'object' else df_a['Месяц']
    df_a = df_a.sort_values(['Филиал', 'Отдел', 'Год', 'Month_Num'])
    df_a['Date'] = pd.to_datetime(df_a['Год'].astype(str) + '-' + df_a['Month_Num'].astype(str) + '-01')
    df_a['Prev_Area'] = df_a.groupby(['Филиал', 'Отдел'])['Площадь'].shift(1)
    
    # Находим изменения площади
    area_changes = df_a[(df_a['Площадь'] != df_a['Prev_Area']) & 
                        (df_a['Prev_Area'].notna()) & 
                        (df_a['Prev_Area'] > 0)].copy()
    
    # Корректируем выручку за 3 месяца до изменения
    for _, row in area_changes.iterrows():
        branch, dept, change_date = row['Филиал'], row['Отдел'], row['Date']
        check_start = change_date - pd.DateOffset(months=3)
        mask = ((df_merged['Филиал'] == branch) & 
                (df_merged['Отдел'] == dept) & 
                (df_merged['Date'] >= check_start) & 
                (df_merged['Date'] < change_date))
        for idx in df_merged[mask].index:
            act, py = df_merged.loc[idx, 'Выручка'], df_merged.loc[idx, 'Выручка_PY']
            if pd.notna(py) and py > 0 and (act - py) / py < -0.30:
                df_merged.loc[idx, 'Выручка'] = int(py * df_merged.loc[idx, 'Trend_Network'])
    
    return df_merged[['Филиал', 'Отдел', 'Месяц', 'Год', 'Выручка']]

def get_plan_data(role_coefficients=None):
    """Загружает данные и рассчитывает план с учётом корректировок"""
    # Берём данные из session_state (загружены при старте)
    if 'raw_sales' in st.session_state:
        df_sales = st.session_state['raw_sales'].copy()
    else:
        df_sales = load_raw_data()
    
    if df_sales.empty:
        return pd.DataFrame()
    
    # Применяем корректировку по площадям
    if 'areas' in st.session_state:
        df_area = st.session_state['areas']
    else:
        df_area = load_areas()
    
    if df_area is not None:
        df_sales = prepare_baseline(df_sales, df_area)
    
    corrections = load_corrections_local()
    limits = load_limits_local()
    
    # Исключаем Доставку из основного расчёта (считается отдельно)
    df_sales_no_delivery = df_sales[df_sales['Отдел'] != 'Доставка.'].copy()
    
    # Полный цикл расчета для всех отделов кроме Доставки
    result = calculate_plan(df_sales_no_delivery, corrections=corrections, role_coefficients=role_coefficients, limits=limits)
    
    # Добавляем план Доставки по специальной логике
    if 'branch_plans' in st.session_state:
        branch_plans = st.session_state['branch_plans']
    else:
        branch_plans = load_branch_plans()
    
    if branch_plans is not None and not branch_plans.empty:
        delivery_plan = calculate_delivery_plan(df_sales, branch_plans)
        
        if not delivery_plan.empty:
            # Добавляем недостающие колонки для Доставки
            delivery_full = df_sales[df_sales['Отдел'] == 'Доставка.'].copy()
            if not delivery_full.empty:
                # Берём данные 2025 года для расчёта прироста
                rev_2025 = delivery_full[delivery_full['Год'] == 2025].groupby(['Филиал', 'Месяц'])['Выручка'].sum().reset_index()
                rev_2025.columns = ['Филиал', 'Месяц', 'Rev_2025']
                
                rev_2024 = delivery_full[delivery_full['Год'] == 2024].groupby(['Филиал', 'Месяц'])['Выручка'].sum().reset_index()
                rev_2024.columns = ['Филиал', 'Месяц', 'Rev_2024']
                
                delivery_plan = delivery_plan.merge(rev_2025, on=['Филиал', 'Месяц'], how='left')
                delivery_plan = delivery_plan.merge(rev_2024, on=['Филиал', 'Месяц'], how='left')
                delivery_plan['Rev_2025'] = delivery_plan['Rev_2025'].fillna(0)
                delivery_plan['Rev_2024'] = delivery_plan['Rev_2024'].fillna(0)
                delivery_plan['Выручка_2025'] = delivery_plan['Rev_2025']
                delivery_plan['Выручка_2024'] = delivery_plan['Rev_2024']
                
                # Прирост
                delivery_plan['Прирост_%'] = calc_growth_pct(delivery_plan['План_Скорр'], delivery_plan['Rev_2025'])
                delivery_plan['Прирост_24_26_%'] = calc_growth_pct(delivery_plan['План_Скорр'], delivery_plan['Rev_2024'])
                
                # Роль
                delivery_plan['Роль'] = 'Сопутствующий'
                delivery_plan['Формат'] = delivery_plan['Филиал'].map(BRANCH_FORMATS).fillna('N/A')
                
                # Удаляем любые существующие строки Доставки из основного результата
                result = result[result['Отдел'] != 'Доставка.'].copy()
                
                # Добавляем к основному результату
                result = pd.concat([result, delivery_plan], ignore_index=True)
    
    return result


# ============================================================================
# STREAMLIT UI
# ============================================================================

# CSS для компактного сайдбара и синих тегов
st.markdown('''
<style>
    /* Ограничение ширины контента для больших экранов */
    .main .block-container {
        max-width: 1800px !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* Компактные таблицы — уменьшенный шрифт и строки */
    [data-testid="stDataFrame"] table {
        font-size: 11px !important;
    }
    [data-testid="stDataFrame"] th,
    [data-testid="stDataFrame"] td {
        padding: 2px 4px !important;
        line-height: 1.1 !important;
    }
    [data-testid="stDataFrame"] th {
        font-size: 10px !important;
    }
    
    /* Компактный сайдбар - минимальные отступы, заголовок в самом верху */
    [data-testid="stSidebar"] {
        padding-top: 0rem !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0rem !important;
        padding-left: 0.3rem !important;
        padding-right: 0.3rem !important;
    }
    [data-testid="stSidebar"] > div > div:first-child {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    [data-testid="stSidebar"] .block-container {
        padding: 0rem !important;
    }
    [data-testid="stSidebar"] h2 {
        font-size: 0.85rem !important;
        margin-bottom: 0.1rem !important;
        margin-top: 0rem !important;
        padding-top: 0.2rem !important;
    }
    [data-testid="stSidebar"] .stMultiSelect {
        margin-bottom: 0rem !important;
    }
    [data-testid="stSidebar"] label {
        font-size: 0.65rem !important;
        margin-bottom: 0rem !important;
    }
    [data-testid="stSidebar"] .stExpander {
        margin-bottom: 0rem !important;
        margin-top: 0rem !important;
    }
    
    /* Уменьшенные multiselect и input */
    [data-testid="stSidebar"] .stMultiSelect > div > div {
        min-height: 28px !important;
        padding: 0 4px !important;
    }
    [data-testid="stSidebar"] .stMultiSelect input {
        font-size: 0.7rem !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] {
        font-size: 0.7rem !important;
    }
    [data-testid="stSidebar"] [data-baseweb="tag"] {
        font-size: 0.6rem !important;
        padding: 1px 4px !important;
        margin: 1px !important;
        height: 18px !important;
    }
    
    /* Кнопки меньше */
    [data-testid="stSidebar"] button {
        font-size: 0.7rem !important;
        padding: 0.15rem 0.4rem !important;
        min-height: 24px !important;
    }
    
    /* Слайдеры компактнее */
    [data-testid="stSidebar"] .stSlider {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
    }
    [data-testid="stSidebar"] .stSlider > div {
        margin-bottom: 0.1rem !important;
    }
    
    /* Синие теги и слайдеры вместо красных */
    span[data-baseweb="tag"] {
        background-color: #3498db !important;
        border-color: #2980b9 !important;
    }
    span[data-baseweb="tag"] span {
        color: white !important;
    }
    
    /* Синие слайдеры */
    [data-testid="stSlider"] > div > div > div > div {
        background-color: #3498db !important;
    }
    [data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
        background-color: #3498db !important;
    }
    
    /* Синяя primary кнопка вместо красной */
    [data-testid="stSidebar"] button[kind="primary"],
    [data-testid="stSidebar"] .stButton button[kind="primary"] {
        background-color: #3498db !important;
        border-color: #2980b9 !important;
    }
    button[kind="primary"] {
        background-color: #3498db !important;
        border-color: #2980b9 !important;
    }
    
    /* Компактные отступы между элементами */
    [data-testid="stSidebar"] > div > div > div {
        gap: 0.1rem !important;
    }
    
    /* Уменьшаем кнопку */
    [data-testid="stSidebar"] button {
        padding: 0.2rem 0.4rem !important;
        font-size: 0.75rem !important;
        margin: 0.1rem 0 !important;
    }
    
    /* Убираем лишние отступы везде */
    [data-testid="stSidebar"] .element-container {
        margin-bottom: 0.1rem !important;
        margin-top: 0rem !important;
    }
    [data-testid="stSidebar"] .stMarkdown {
        margin-bottom: 0rem !important;
    }
    [data-testid="stSidebar"] hr {
        margin: 0.2rem 0 !important;
    }
    
    /* Компактный multiselect */
    [data-testid="stSidebar"] .stMultiSelect > div {
        margin-bottom: 0rem !important;
    }
    
    /* Синяя рамка вместо красной для мультиселекта */
    .stMultiSelect > div > div {
        border-color: #3498db !important;
    }
    .stMultiSelect > div > div:focus-within {
        border-color: #3498db !important;
        box-shadow: 0 0 0 1px #3498db !important;
    }
    
    /* КНОПКА ОТКРЫТИЯ САЙДБАРА — ВСЕГДА ВИДНА */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stExpandSidebarButton"],
    button[aria-label="Expand sidebar"],
    [data-testid="collapsedControl"] {
        visibility: visible !important;
        opacity: 1 !important;
        display: flex !important;
        background: linear-gradient(135deg, #3498db, #2980b9) !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(52, 152, 219, 0.4) !important;
        border: none !important;
        z-index: 999999 !important;
    }
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="stExpandSidebarButton"] svg,
    button[aria-label="Expand sidebar"] svg,
    [data-testid="collapsedControl"] svg,
    [data-testid="stSidebarCollapseButton"] svg path,
    [data-testid="stExpandSidebarButton"] svg path,
    [data-testid="collapsedControl"] svg path {
        color: white !important;
        fill: white !important;
        stroke: white !important;
    }
    [data-testid="stSidebarCollapseButton"]:hover,
    [data-testid="stExpandSidebarButton"]:hover,
    button[aria-label="Expand sidebar"]:hover,
    [data-testid="collapsedControl"]:hover {
        background: linear-gradient(135deg, #2980b9, #1a5276) !important;
        box-shadow: 0 4px 12px rgba(52, 152, 219, 0.6) !important;
        transform: scale(1.05);
    }
    
    /* Полноэкранный режим таблицы */
    [data-testid="stDataFrame"]:fullscreen,
    [data-testid="stDataFrame"]:-webkit-full-screen {
        height: 100vh !important;
        width: 100vw !important;
    }
    [data-testid="stDataFrame"]:fullscreen iframe,
    [data-testid="stDataFrame"]:-webkit-full-screen iframe {
        height: 100% !important;
        width: 100% !important;
    }
    [data-testid="stDataFrame"]:fullscreen > div,
    [data-testid="stDataFrame"]:-webkit-full-screen > div {
        height: 100% !important;
    }
    
    /* Выравнивание числовых колонок по правому краю */
    [data-testid="stDataEditor"] td,
    [data-testid="stDataFrame"] td {
        text-align: right !important;
    }
    [data-testid="stDataEditor"] td:first-child,
    [data-testid="stDataEditor"] td:nth-child(2),
    [data-testid="stDataEditor"] td:nth-child(3),
    [data-testid="stDataEditor"] td:nth-child(4),
    [data-testid="stDataFrame"] td:first-child,
    [data-testid="stDataFrame"] td:nth-child(2),
    [data-testid="stDataFrame"] td:nth-child(3),
    [data-testid="stDataFrame"] td:nth-child(4) {
        text-align: left !important;
    }
    
    /* Синяя рамка для активной ячейки в data_editor */
    [data-testid="stDataEditor"] input:focus,
    [data-testid="stDataEditor"] [contenteditable="true"]:focus,
    [data-testid="stDataEditor"] *:focus {
        outline: 2px solid #3498db !important;
        border-color: #3498db !important;
        box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.3) !important;
    }
    [data-testid="stDataEditor"] td.selected,
    [data-testid="stDataEditor"] td[aria-selected="true"] {
        outline: 2px solid #3498db !important;
        border-color: #3498db !important;
    }
</style>
''', unsafe_allow_html=True)

# ========== ЗАГРУЗКА ДАННЫХ ПРИ СТАРТЕ СЕССИИ (КАК В COLAB) ==========
# Данные загружаются ОДИН РАЗ при входе и используются всю сессию
# При перезагрузке страницы (F5) — данные загружаются заново

# Показываем заставку ТОЛЬКО при первом визите в сессию
if 'splash_shown' not in st.session_state:
    import time
    
    # Полноэкранный белый фон с центрированием
    splash = st.empty()
    
    with splash.container():
        st.markdown("""
        <style>
            .stApp { background: white !important; }
            .stApp > header, .stSidebar, footer, div[data-testid="stSidebarNav"] { 
                visibility: hidden !important; 
                display: none !important;
            }
            div[data-testid="stVerticalBlock"] {
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }
            @keyframes zoomIn {
                0% { opacity: 0; transform: scale(0.3); }
                50% { opacity: 1; transform: scale(1.05); }
                100% { opacity: 1; transform: scale(1); }
            }
            div[data-testid="stImage"] img {
                animation: zoomIn 0.6s ease-out;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Задержка перед появлением лошадки
        time.sleep(1.0)
        
        # Сначала лошадка — крупно по центру с плавным исчезновением
        horse_placeholder = st.empty()
        horse_placeholder.image(os.path.join(os.path.dirname(__file__), "horse_icon.png"), width=400)
        time.sleep(2.0)  # Показываем дольше
        
        # Плавное исчезновение лошадки
        fade_style = st.empty()
        fade_style.markdown("""
        <style>
            div[data-testid="stImage"] img {
                animation: fadeOut 0.8s ease-out forwards !important;
            }
            @keyframes fadeOut {
                0% { opacity: 1; transform: scale(1); }
                100% { opacity: 0; transform: scale(0.95); }
            }
        </style>
        """, unsafe_allow_html=True)
        time.sleep(0.8)
        horse_placeholder.empty()
        fade_style.empty()
        
        # Потом АКСОН — крупно по центру, дольше с плавным исчезновением
        akson_placeholder = st.empty()
        akson_placeholder.image(os.path.join(os.path.dirname(__file__), "logo_akson.png"), width=400)
        time.sleep(2.5)
        
        # Плавное исчезновение АКСОН
        fade_style2 = st.empty()
        fade_style2.markdown("""
        <style>
            div[data-testid="stImage"] img {
                animation: fadeOut 0.8s ease-out forwards !important;
            }
            @keyframes fadeOut {
                0% { opacity: 1; transform: scale(1); }
                100% { opacity: 0; transform: scale(0.95); }
            }
        </style>
        """, unsafe_allow_html=True)
        time.sleep(0.8)
        akson_placeholder.empty()
        fade_style2.empty()
    
    splash.empty()
    st.session_state['splash_shown'] = True

if 'data_loaded' not in st.session_state:
    # Загрузка данных без видимого spinner
    st.session_state['raw_sales'] = load_raw_data()
    st.session_state['rules'] = load_rules()
    st.session_state['roles'] = load_roles()
    st.session_state['branch_plans'] = load_branch_plans()
    st.session_state['areas'] = load_areas()
    st.session_state['data_loaded'] = True
    st.session_state['load_time'] = pd.Timestamp.now().strftime('%H:%M:%S')



# Сайдбар - Кнопка обновления
if st.sidebar.button("🔄 Обновить данные", type="primary", use_container_width=True):
    # Полная очистка всех кэшей
    st.cache_data.clear()
    clear_optimization_cache()  # Очищаем кэш ML оптимизатора
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ========== КОМПРЕССОР ОТКЛЮЧЁН — ML ОПТИМИЗАТОР УПРАВЛЯЕТ АВТОМАТИЧЕСКИ ==========
role_coefficients = None

# Определяем, запущено ли приложение на Streamlit Cloud
IS_STREAMLIT_CLOUD = '/mount/src/' in os.path.abspath(__file__)

# Файл для публикации на Streamlit Cloud (только для чтения там)
PUBLISHED_FILE = os.path.join(DATA_DIR, 'plan_published.csv')

if IS_STREAMLIT_CLOUD:
    # На Streamlit Cloud — загружаем из готового CSV (без пересчёта)
    if os.path.exists(PUBLISHED_FILE):
        df_base = pd.read_csv(PUBLISHED_FILE)
        for col in ['План_Скорр', 'Rev_2025', 'Rev_2024', 'Выручка_2025', 'Выручка_2024']:
            if col in df_base.columns:
                df_base[col] = pd.to_numeric(df_base[col], errors='coerce').fillna(0)
    else:
        st.error("⚠️ Файл данных не найден. Обратитесь к администратору.")
        df_base = pd.DataFrame()
else:
    # Локально — динамический расчёт с корректировками
    df_base = get_plan_data(role_coefficients=role_coefficients)
    
    # Автоматически сохраняем в файл для публикации
    if not df_base.empty:
        df_base.to_csv(PUBLISHED_FILE, index=False)

# Сайдбар - Кнопка скачивания плана
def prepare_plan_csv(dataframe):
    """Подготовка CSV с планом"""
    export_df = dataframe[['Филиал', 'Отдел', 'Месяц', 'План_Скорр']].copy()
    export_df = export_df.rename(columns={'План_Скорр': 'План'})
    export_df['Месяц'] = export_df['Месяц'].map(MONTH_MAP_REV)
    return export_df.to_csv(index=False).encode('utf-8')

if not df_base.empty:
    st.sidebar.download_button(
        label="📥 Скачать план CSV",
        data=prepare_plan_csv(df_base),
        file_name="plan_2026.csv",
        mime="text/csv",
        use_container_width=True
    )


# CSS для центрирования заголовка сайдбара и замены кнопки на лошадку
horse_b64 = "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAIAAADYYG7QAAAH2UlEQVR42u1Za2xU1xGeOefevfvwrtcLNjWhEK8L5pESg4RDaHg5SRPilkdLmqo/kCpRoVakaSkB4qL0YZS0KqWUKqKq3RaEf0SRQgIhtFVxCFgJIANxCLJTHjYYr42d2Hh37fXu3ntm+mPXi2N71zatUioxv+7OeX1nzjcz58wiEQFCUhjSfsPYmlKtKT0Pa4WRhyf7JgAlNINah44b+D147tTqnBiLQ0HdgXAK0J2N/++LGHHf/2NAd5XcA/R/CojvNkB3kZdpY4piPGBCxM8DUOZFmAhFkmqsFEo5GnQa2KK4gw2MwiFmRiEsov6uLkqhYR6pJwEpQASUICSgvDNzahk4xESA2HJgf0dVZW8wJDyeSWufLtr4LCbT4ODcpRAlIFC0h29d5lgQbW70TEXXJEQxUgYeBVBa+yCijji5+YrMy4t1dV57sTzW2fHgjpeYCFOAmAGlCl1XJyuw6Sj2tgMDK7B89/G8DXrxBunMhYQKEWAAH4pxA0JEQHQGWkIup8OwG5o2d2bRxQP7u57+lu+BL1M8jkIAMCCaF/bz4fUaATgANA0U86RZ2tpD0uvngfXxNgIEAFZxlLbxBEYiECJ26eP+117VNd3q7jLNOAgxTWL47FmUUthsqGmo6YB9OrXZHv4uZXtAAQqBSrHuwKx81fGh+Y9nzX0LrOol5vEXrJYTFG5XnRei72ymWGhE+iIRIY50wEqBlN3bfmLt+4ucv0Bbs8Y89AYHAkKp3kWP0OJlqJQEnjh5cr/bffO9c+7pX8pfVMCvr5adH4NNgqlU1gSI9YiIAg2AgQlAA3L5INgND6yyffNNYAUox0xqRACwP1kW0+3urdu0LPenx9/h5mbp8QSPHbv26muaEDZEe56vT8o204pea+7csLn4paPqj/OEGUZNykgXCGCXBswMCEIiogh3k9MtH/1duvCX3kJD7BUMdq9dCZ98IgwjQnwlHDGJv+AwprgcdKvb/rNfNp58r23v3jmVBwrn31Bvlgu3DqQAmBMLI6JFFAfKmSzWVGtTlwPTiLweJXWwaXI0Cszm1ct8sx0dDhWJuMLByWa/pzc4xYwQKUVEH9YX/nCj7vPEWpupYCU7dCYrAQYBAZBNsibM4KXb5PpzGdCM5vYAqOug66yU2XCR43EOh+TsOfoTT+VPK5jYGxbn6qy/vS11PX6h3pM36Svvn8kumhk/sQXjJjgkMAECIIJJvOIVbf4PBuJ9WjQZATEDYlNVpXvGjNwlS83z57AvrK3/vuenL0p9wF1Xf6N/5erwjzdS01XRcyu7aOa/fvPr/K99J2va37n1I9AFAAEgM4DQoL0u2vKubf5Godkz5E+RIWkAQOijC6dXPNFc9SduaLAteyzn5zuk1DgWpXicYjGORh0LHvL8aqduWbeOvPX+2lVXX36ZHRPB5gSCxHuEmYWhi7c2WH8u0SbOFrojgXLcFkKBwFz8+z9k+f2N5S84I70Fz2919vTYvF407IPfVdHsnBaH++aW512LH1ty8ZLj2m515Yxw2jjp6BZHTHJm4dertMIyYBru6uPxMmZADDY0NL2yp+PIUSkxa9ZsR0GhbYKPzXi0NRBuaOi/ft1RVHT/9zZMeXIuntjMH9SgC4CSMY+cTi4sE4u3a7lzgRQIOQpraXBWGungyLKkrgNA7/Xrn9ae6Dl9Jt5ywwwFWQhbXp57zpwJy5b5FszHznfNk7+F8E3hyiEUaHiF1w+T5sGUR8SE6QgAlglCCiH+I0BjfW8yoYqC5hz2qB33TFrmsZZlNTU1EVHiNiIAZhTNQKkFAoFQsAcBSSnDbi+cPv1Wr9XR3oiIAExEHrf7vi9OBVaXLl2mZL5iIWRhoV/KDLEGgYiYiYeJUoqZA4HAkPxfUVFRX1/vdrtTSl3XDx8+tG/fXwf3zMrKqq+vr6ioGGx+KWVnZyczE42wYkLS5rLEYefm5n5QX68sS0oZj8dKSx+tqanx+XzhcLhix45FDy8KBFrXrVt38OAbu3fvPn16liY1qcmTtbU/eu65U6dO1dTU2AxbzbEam81QyjIMw+fLSV5sxuv2iTiklHr7yJGzdXXRWFQp6uvrc7lcTpcTER8qKSktXd7W1oaIdrs9FApVVVW1trYm7MrMLpfL5XKZcXPTpk0AYLfbS0pKiop+4XDIDJhE+usQIWJdXd327duvNjffX1Dg9/vLy8v37t1rxk1E1DQJAJqmAYDb7d6zZ09VVZU3x+v3+5cuXbpr165nvv1MV1eXYRgrVqxYtWoVM+/cufP8+fOImCBlBgulJXU8HgeAeQ8Wlz1VppSyLOvGjRuRSISIDr5+sLn5WkdHBzNHo9EEstLlpfn5+URkWVagNWCaplJq4cKFDoejqamptrY2Go1m9jJIxy/Lspj5+PHjnmyPYRipEV99/PHGxsaCggJN0wBBSpmXl3fsn8e2btnq8XgGh5nq6urKykqv15vifnFxcXt7OxGlJzWNEodM0+zp6ZFSpvpIKT0eT39/fyQSkVISkZQyOzs7FArFYrGEnRLidDoNw+ju7k4whkh5vTlSSmbOsOJYL2hD6DUk4A7XpNNnRjOmSM3JZ+FtniEif/atOFyToefnkTrulWPuVdDusiPje0c2aiWf71lotKJnskqHqZiMn2H64ArY7e9BfTj5jwmnuzpkuGAny0fJuf4NMqw59jfnfSoAAAAASUVORK5CYII="

st.sidebar.markdown(f"""
<style>
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] .stCaption {{
        text-align: center !important;
    }}
    
</style>
""", unsafe_allow_html=True)


# Заголовок и дата — ФИЛЬТРЫ ВВЕРХУ
st.sidebar.header("📊 Фильтры")
st.sidebar.caption(f"📅 Данные: {st.session_state.get('load_time', 'N/A')}")
st.sidebar.caption(f"🐍 Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

# === АВТОРИЗАЦИЯ ДЛЯ РЕДАКТИРОВАНИЯ ===
if 'edit_authorized' not in st.session_state:
    st.session_state.edit_authorized = False

# Показываем форму авторизации или статус
if not st.session_state.edit_authorized:
    with st.sidebar.expander("🔐 Режим редактирования", expanded=False):
        password_input = st.text_input("Введите пароль:", type="password", key="edit_password_input")
        if st.button("Войти", key="login_btn", use_container_width=True):
            if password_input == EDIT_PASSWORD:
                st.session_state.edit_authorized = True
                st.rerun()
            else:
                st.error("❌ Неверный пароль")
else:
    st.sidebar.success("✅ Режим редактирования")
    if st.sidebar.button("🚪 Выход из редактирования", key="logout_btn", use_container_width=True):
        st.session_state.edit_authorized = False
        st.rerun()

st.sidebar.divider()

if df_base.empty:
    st.error("Нет данных для отображения")
    st.stop()

# Получаем все уникальные значения
all_branches = sorted(df_base['Филиал'].unique())
all_depts = sorted(df_base['Отдел'].unique())
all_months = list(range(1, 13))

# Загружаем сохранённые фильтры
saved_filters = load_filters_local()

# Основные фильтры (с учётом сохранённых, по умолчанию пустые = все данные)
default_branches = saved_filters.get('branches', [])
default_depts = saved_filters.get('depts', [])
default_months = saved_filters.get('months', [])

# Валидация (если сохранённые значения устарели - оставляем только валидные)
default_branches = [b for b in default_branches if b in all_branches]
default_depts = [d for d in default_depts if d in all_depts]
default_months = [m for m in default_months if m in all_months]

sel_branches = st.sidebar.multiselect("Филиал", all_branches, default=default_branches, placeholder="Все филиалы")
sel_depts = st.sidebar.multiselect("Отдел", all_depts, default=default_depts, placeholder="Все отделы")
sel_months = st.sidebar.multiselect("Месяц", all_months, default=default_months, format_func=lambda x: MONTH_MAP_REV[x], placeholder="Все месяцы")

# Кнопка сохранения фильтров


st.sidebar.divider()


# Выбор колонок для таблицы
st.sidebar.header("📋 Колонки таблицы")

# Обязательные колонки (всегда видны, порядок фиксирован в начале)
MANDATORY_COLS = ['Филиал', 'Отдел', 'Мес', 'Корр', 'Корр±', 'План_Скорр', 'Выручка_2025']

# Полный список всех возможных
all_columns_full = ['Филиал', 'Отдел', 'Мес', 'Роль', 'Формат', 'Правило', 
               'Корр', 'Корр±', 'Авто_Корр',
               'План_Скорр', 'План_Расч', 'План', '_План_Расч_Исх', 'Рекоменд',
               'Выручка_2025', 'Выручка_2024', 'Выручка_2025_Норм',
               'Прирост_%', 'Прирост_24_26_%', 'Прирост_Год_%',
               'Сезонность_Факт', 'Сезонность_План',
               'Площадь_2025', 'Площадь_2026', 'Δ_Площадь_%',
               'Отдача_План', 'Отдача_2025', 'Δ_Отдача_%',
               'Final_Weight', 'is_network_format', 'Месяц']

# Опциональные (те что можно скрывать) = Все минус Обязательные
optional_columns = [c for c in all_columns_full if c not in MANDATORY_COLS]

# Настройки по умолчанию для опциональных (убрали 'План' чтобы не путать с План_Скорр)
default_optional_init = ['Выручка_2024', 'Прирост_%', 'Прирост_24_26_%', 
                         'Площадь_2025', 'Площадь_2026', 'Отдача_План', 'Отдача_2025']

# Пытаемся взять из сохранений
# Сначала пробуем новый ключ 'optional_columns', потом старый 'columns'
saved_optional_cols = saved_filters.get('optional_columns', [])
if not saved_optional_cols:
    # Fallback: старый формат - берём из 'columns' только опциональные
    saved_all_cols = saved_filters.get('columns', [])
    saved_optional_cols = [c for c in saved_all_cols if c in optional_columns]

if saved_optional_cols:
    # Фильтруем только валидные опциональные колонки
    default_optional = [c for c in saved_optional_cols if c in optional_columns]
else:
    default_optional = default_optional_init

st.sidebar.caption("🔒 Основные колонки (Филиал, Отдел, Мес, Корр..., Выручка, План) закреплены.")
sel_optional = st.sidebar.multiselect("Дополнительные колонки", optional_columns, default=default_optional)

# Итоговый список колонок для отображения: Обязательные + Выбранные опциональные
# Сохраняем порядок: Сначала обязательные (в определенном порядке?), или перемешиваем?
# Лучше держать Обязательные в начале, или хотя бы Филиал/Отдел/Мес
# Давайте соберем в порядке appearance в all_columns_full для консистентности
sel_columns = [c for c in all_columns_full if c in MANDATORY_COLS or c in sel_optional]



# Обновляем кнопку сохранения, чтобы сохранять и колонки
if st.sidebar.button("💾 Сохранить настройки", use_container_width=True):
    # Сохраняем только опциональные колонки (не обязательные)
    filters_to_save = {
        'branches': sel_branches,
        'depts': sel_depts,
        'months': sel_months,
        'optional_columns': sel_optional  # <- Сохраняем только опциональные
    }
    if save_filters_local(filters_to_save):
        st.sidebar.success("Настройки (фильтры и столбцы) сохранены!")


# Все линии на графиках всегда показываем
show_2024 = True
show_2025 = True
show_plan = True

# Фильтрация
df = df_base.copy()
if sel_branches:
    df = df[df['Филиал'].isin(sel_branches)]
if sel_depts:
    df = df[df['Отдел'].isin(sel_depts)]
if sel_months:
    df = df[df['Месяц'].isin(sel_months)]

if sel_months:
    df = df[df['Месяц'].isin(sel_months)]


# Убираем отступы вверху страницы
st.markdown("""
<style>
    .block-container {
        padding-top: 0.3rem !important; 
        padding-bottom: 0 !important; 
        margin-top: 0 !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    header {visibility: hidden; height: 0 !important;}
    .stApp > header {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Минимальные отступы между элементами */
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.1rem !important;
    }
    
    /* Выравнивание колонок заголовка по центру */
    div[data-testid="stHorizontalBlock"] {
        align-items: center !important;
        gap: 0 !important;
    }
    
    /* Убираем скругление у всех изображений */
    div[data-testid="stImage"] img {
        border-radius: 0 !important;
    }
    
    /* Центрирование заголовков над графиками */
    .stCaption p {
        text-align: center !important;
        font-weight: 600 !important;
    }
    
    /* Уменьшение отступов между панелью и графиками */
    div[data-testid="stExpander"] {
        margin-bottom: 0.2rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Компактный заголовок в одну линию — АКСОН и План
col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.image("logo_akson.png", width=140)
with col_title:
    st.markdown("<p style='margin: 0; padding: 10px 0; font-size: 32px; font-weight: 600; color: #333;'>План</p>", unsafe_allow_html=True)

# KPI (компактная строка)
total_plan = df['План_Скорр'].sum()
total_fact = df['Rev_2025'].sum()
total_fact_24 = df['Rev_2024'].sum()

# ========== ПРОВЕРКА СХОДИМОСТИ ==========
# Сходимость рассчитывается по ВСЕМ данным выбранных филиалов
# Если фильтр пустой — показываем общую сходимость по ВСЕМ филиалам

convergence_ok = True
convergence_msg = ""
convergence_details = {}

if 'План' in df_base.columns:
    # Если филиалы не выбраны — используем ВСЕ данные
    if len(sel_branches) > 0:
        df_convergence = df_base[df_base['Филиал'].isin(sel_branches)].copy()
    else:
        df_convergence = df_base.copy()  # Все данные
    
    # Целевой план — уникальные значения по филиалу/месяцу
    target_by_group = df_convergence.groupby(['Филиал', 'Месяц'])['План'].first()
    target_total = target_by_group.sum()
    
    # Распределённый план (сумма по отделам)
    distributed_total = df_convergence['План_Скорр'].sum()
    
    # Отклонение
    deviation = distributed_total - target_total
    deviation_pct = (deviation / target_total * 100) if target_total > 0 else 0
    
    # Проверка по каждому филиалу-месяцу
    for (branch, month), grp in df_convergence.groupby(['Филиал', 'Месяц']):
        dept_sum = grp['План_Скорр'].sum()
        target_val = grp['План'].iloc[0]
        if pd.notna(target_val):
            diff = dept_sum - target_val
            if abs(diff) > 100:  # Погрешность более 100 руб
                convergence_details[(branch, month)] = {
                    'target': target_val,
                    'distributed': dept_sum,
                    'diff': diff
                }
    
    convergence_ok = abs(deviation) < 1000  # Допустимое отклонение < 1000 руб
    
    if convergence_ok:
        convergence_msg = f"✅ Сходимость: {deviation:+,.0f} руб ({deviation_pct:+.2f}%)".replace(',', ' ')
        convergence_color = "#27ae60"
    else:
        convergence_msg = f"⚠️ Расхождение: {deviation:+,.0f} руб ({deviation_pct:+.2f}%)".replace(',', ' ')
        convergence_color = "#e74c3c"
else:
    convergence_msg = "⚠️ Целевые планы не загружены"
    convergence_color = "#f39c12"
    target_total = 0

st.markdown(f"""
<div style="display:flex; gap:15px; padding:5px 10px; background:#f8f9fa; border-radius:6px; font-size:13px;">
    <div><b>План:</b> {total_plan/1e6:,.1f}M</div>
    <div><b>Факт'25:</b> {total_fact/1e6:,.1f}M</div>
    <div><b>Δ:</b> <span style="color:{'green' if total_plan > total_fact else 'red'}">{(total_plan/total_fact-1)*100:+.1f}%</span></div>
    <div><b>Факт'24:</b> {total_fact_24/1e6:,.1f}M</div>
    <div><b>Рост 24→26:</b> <span style="color:{'green' if total_plan > total_fact_24 else 'red'}">{(total_plan/total_fact_24-1)*100:+.1f}%</span></div>
    <div style="margin-left:auto;"><span style="color:{convergence_color}; font-weight:bold;">{convergence_msg}</span></div>
</div>
""", unsafe_allow_html=True)

# Показываем детали расхождений если есть
if convergence_details:
    with st.expander(f"⚠️ Расхождения по {len(convergence_details)} группам"):
        conv_data = []
        for (branch, month), vals in convergence_details.items():
            conv_data.append({
                'Филиал': branch,
                'Месяц': MONTH_MAP_REV.get(month, month),
                'Цель': f"{vals['target']:,.0f}".replace(',', ' '),
                'Распред.': f"{vals['distributed']:,.0f}".replace(',', ' '),
                'Δ': f"{vals['diff']:+,.0f}".replace(',', ' ')
            })
        st.dataframe(pd.DataFrame(conv_data), hide_index=True, use_container_width=True)

# === 4 ГРАФИКА В ОДИН РЯД ===
# Пропорции: Динамика(1), Отделы(1.5), Филиалы(1.5), Сезонность(1)
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])


# 1. График динамики
with col1:
    st.caption("📈 Динамика")
    # DEBUG: Проверка данных
    aggregated_sum = df['План_Скорр'].sum()
    # st.info(f"Сумма плана (фильтр): {aggregated_sum:,.0f} | Строк: {len(df)}")
    all_months_df = pd.DataFrame({'Месяц': range(1, 13)})
    agg_dict = {
        'План_Скорр': 'sum',
        'План_Расч': 'sum',
        'Корр_Дельта': 'sum',
        'Rev_2025': 'sum',
        'Rev_2024': 'sum'
    }
    # Добавляем сезонность если есть (для одного отдела это одинаковое значение)
    if 'Seasonality_Share' in df.columns:
        agg_dict['Seasonality_Share'] = 'first'
    m_agg = df.groupby('Месяц').agg(agg_dict).reset_index()
    m_full = pd.merge(all_months_df, m_agg, on='Месяц', how='left').fillna(0)
    m_full['M'] = m_full['Месяц'].map(MONTH_MAP_REV)
    
    # Расчёт процентов
    m_full['Δ_План_25'] = np.where(m_full['Rev_2025'] > 0, 
        (m_full['План_Скорр'] / m_full['Rev_2025'] - 1) * 100, 0)
    m_full['Δ_25_24'] = np.where(m_full['Rev_2024'] > 0, 
        (m_full['Rev_2025'] / m_full['Rev_2024'] - 1) * 100, 0)
    
    # Форматирование для hover с пробелами (млн)
    def fmt_mln(val):
        return f"{val/1e6:.1f} млн".replace(',', ' ')
    
    def fmt_sign_mln(val):
        sign = '+' if val >= 0 else ''
        return f"{sign}{val/1e6:.1f} млн".replace(',', ' ')
    
    def fmt_pct_color(val):
        sign = '+' if val >= 0 else ''
        color = '#27ae60' if val >= 0 else '#e74c3c'
        return f"<span style='color:{color}'>{sign}{val:.1f}%</span>"
    
    def fmt_corr_color(val):
        sign = '+' if val >= 0 else ''
        color = '#27ae60' if val >= 0 else '#e74c3c'
        return f"<span style='color:{color}'>{sign}{val/1e6:.1f} млн</span>"
    
    fig1 = go.Figure()
    
    # Сначала добавляем столбцы Плана (на заднем плане)
    if show_plan:
        fig1.add_trace(go.Bar(
            x=m_full['M'], y=m_full['План_Скорр'], name='План 26',
            marker=dict(color='rgba(52, 152, 219, 0.3)', line=dict(color='#3498db', width=1)),
            hoverinfo='skip'
        ))
    
    # Затем линии поверх столбцов
    if show_2024:
        fig1.add_trace(go.Scatter(
            x=m_full['M'], y=m_full['Rev_2024'], name='Факт 24', 
            line=dict(color='#bdc3c7', width=1.5, dash='dot'), 
            mode='lines+markers', marker=dict(size=5, color='#bdc3c7'),
            hoverinfo='skip'
        ))
    if show_2025:
        fig1.add_trace(go.Scatter(
            x=m_full['M'], y=m_full['Rev_2025'], name='Факт 25', 
            line=dict(color='#2ecc71', width=2.5), 
            mode='lines+markers', marker=dict(size=6, color='#2ecc71'),
            hoverinfo='skip'
        ))
    
    # Невидимая линия для общего hover
    hover_texts = []
    for _, row in m_full.iterrows():
        text = (
            f"<b>Месяц: {row['M']}</b><br>"
            f"<span style='color:#3498db; font-weight:bold'>План: {fmt_mln(row['План_Скорр'])}</span><br>"
            f"<span style='color:#2ecc71; font-weight:bold'>2025: {fmt_mln(row['Rev_2025'])}</span><br>"
            f"<span style='color:#95a5a6'>2024: {fmt_mln(row['Rev_2024'])}</span><br>"
            f"Δ% План/25: {fmt_pct_color(row['Δ_План_25'])}<br>"
            f"Δ% 25/24: {fmt_pct_color(row['Δ_25_24'])}"
        )
        hover_texts.append(text)
    
    fig1.add_trace(go.Scatter(
        x=m_full['M'], y=m_full['План_Скорр'],
        mode='markers', marker=dict(size=15, opacity=0),
        hovertext=hover_texts,
        hoverinfo='text',
        showlegend=False
    ))
    
    # Аннотации с процентами в середине столбцов
    if show_plan:
        annotations = []
        for _, row in m_full.iterrows():
            val = row['Δ_План_25']
            y_pos = row['План_Скорр'] * 0.5  # Середина столбца
            color = '#27ae60' if val >= 0 else '#e74c3c'
            annotations.append(dict(
                x=row['M'], y=y_pos,
                text=f"<b>{val:+.0f}%</b>",
                showarrow=False,
                font=dict(size=10, color=color),
                bgcolor='rgba(255,255,255,0.85)',
                borderpad=1
            ))
        fig1.update_layout(annotations=annotations)
    
    fig1.update_layout(
        margin=dict(l=0,r=0,t=10,b=20), height=280, 
        showlegend=True, 
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, font=dict(size=10)),
        hoverlabel=dict(bgcolor='white', font_size=12),
        hovermode='x'
    )
    fig1.update_xaxes(tickfont=dict(size=8), tickangle=0)
    fig1.update_yaxes(tickfont=dict(size=8), showticklabels=False)
    st.plotly_chart(fig1, use_container_width=True)

# 2. Таблица по отделам (числа прироста)
with col2:
    st.caption("🔥 Отделы %")
    # Агрегация данных по отделам и месяцам
    p = df.groupby(['Отдел', 'Месяц']).agg({
        'План_Скорр': 'sum', 'Rev_2025': 'sum', 'Rev_2024': 'sum'
    }).reset_index()
    p['G'] = np.where(p['Rev_2025'] > 0, ((p['План_Скорр'] / p['Rev_2025']) - 1) * 100, 0)
    p['Δ_25_24'] = np.where(p['Rev_2024'] > 0, ((p['Rev_2025'] / p['Rev_2024']) - 1) * 100, 0)
    
    pivot = p.pivot(index='Отдел', columns='Месяц', values='G')
    pivot_plan = p.pivot(index='Отдел', columns='Месяц', values='План_Скорр')
    pivot_25 = p.pivot(index='Отдел', columns='Месяц', values='Rev_2025')
    pivot_24 = p.pivot(index='Отдел', columns='Месяц', values='Rev_2024')
    pivot_d25_24 = p.pivot(index='Отдел', columns='Месяц', values='Δ_25_24')
    
    for i in range(1, 13):
        if i not in pivot.columns: pivot[i] = 0
        if i not in pivot_plan.columns: pivot_plan[i] = 0
        if i not in pivot_25.columns: pivot_25[i] = 0
        if i not in pivot_24.columns: pivot_24[i] = 0
        if i not in pivot_d25_24.columns: pivot_d25_24[i] = 0
    
    # Сортировка по алфавиту (А->Я)
    pivot = pivot[range(1, 13)].fillna(0).sort_index(ascending=True)
    pivot_plan = pivot_plan[range(1, 13)].fillna(0).sort_index(ascending=True)
    pivot_25 = pivot_25[range(1, 13)].fillna(0).sort_index(ascending=True)
    pivot_24 = pivot_24[range(1, 13)].fillna(0).sort_index(ascending=True)
    pivot_d25_24 = pivot_d25_24[range(1, 13)].fillna(0).sort_index(ascending=True)
    
    # Добавляем колонку Итого по отделам
    pivot_total = df.groupby('Отдел').agg({'План_Скорр': 'sum', 'Rev_2025': 'sum', 'Rev_2024': 'sum'})
    pivot_total['Σ'] = np.where(pivot_total['Rev_2025'] > 0, 
        ((pivot_total['План_Скорр'] / pivot_total['Rev_2025']) - 1) * 100, 0)
    pivot['Σ'] = pivot_total['Σ']
    
    # Добавляем строку ИТОГО внизу только если больше 1 строки
    is_single_row = len(pivot) <= 1
    
    if not is_single_row:
        total_row_plan = pivot_plan.sum()
        total_row_25 = pivot_25.sum()
        total_row_24 = pivot_24.sum()
        total_row_g = pd.Series({m: ((total_row_plan[m] / total_row_25[m]) - 1) * 100 if total_row_25[m] > 0 else 0 for m in range(1, 13)})
        total_row_d25_24 = pd.Series({m: ((total_row_25[m] / total_row_24[m]) - 1) * 100 if total_row_24[m] > 0 else 0 for m in range(1, 13)})
        
        # Итого за год
        year_plan = total_row_plan.sum()
        year_25 = total_row_25.sum()
        total_sigma = ((year_plan / year_25) - 1) * 100 if year_25 > 0 else 0
        
        pivot.loc['ИТОГО'] = list(total_row_g.values) + [total_sigma]
        pivot_plan.loc['ИТОГО'] = total_row_plan.values
        pivot_25.loc['ИТОГО'] = total_row_25.values
        pivot_24.loc['ИТОГО'] = total_row_24.values
        pivot_d25_24.loc['ИТОГО'] = total_row_d25_24.values
    
    # Создаём кастомный hover текст
    month_labels = [MONTH_MAP_REV[i] for i in range(1, 13)] + ['Σ']
    hover_texts = []
    for dept in pivot.index:
        row_texts = []
        for m in range(1, 13):
            plan_val = pivot_plan.loc[dept, m] / 1e6
            f25_val = pivot_25.loc[dept, m] / 1e6
            f24_val = pivot_24.loc[dept, m] / 1e6
            g_val = pivot.loc[dept, m]
            d25_24 = pivot_d25_24.loc[dept, m]
            
            g_color = '#27ae60' if g_val >= 0 else '#e74c3c'
            d_color = '#27ae60' if d25_24 >= 0 else '#e74c3c'
            g_sign = '+' if g_val >= 0 else ''
            d_sign = '+' if d25_24 >= 0 else ''
            
            text = (
                f"<b>{dept[:20]}</b><br>"
                f"<b>{MONTH_MAP_REV[m]}</b><br>"
                f"<span style='color:#3498db'>План: {plan_val:.1f} млн</span><br>"
                f"<span style='color:#2ecc71'>2025: {f25_val:.1f} млн</span><br>"
                f"<span style='color:#95a5a6'>2024: {f24_val:.1f} млн</span><br>"
                f"<span style='color:{g_color}'>Δ% П/25: {g_sign}{g_val:.0f}%</span><br>"
                f"<span style='color:{d_color}'>Δ% 25/24: {d_sign}{d25_24:.0f}%</span>"
            )
            row_texts.append(text)
        
        # Итого колонка - полная информация как для месяцев
        year_plan = pivot_plan.loc[dept].sum() / 1e6
        year_25 = pivot_25.loc[dept].sum() / 1e6
        year_24 = pivot_24.loc[dept].sum() / 1e6
        year_g = pivot.loc[dept, 'Σ']
        year_d25_24 = ((pivot_25.loc[dept].sum() / pivot_24.loc[dept].sum()) - 1) * 100 if pivot_24.loc[dept].sum() > 0 else 0
        
        g_color = '#27ae60' if year_g >= 0 else '#e74c3c'
        d_color = '#27ae60' if year_d25_24 >= 0 else '#e74c3c'
        g_sign = '+' if year_g >= 0 else ''
        d_sign = '+' if year_d25_24 >= 0 else ''
        
        row_texts.append(
            f"<b>{dept[:20]}</b><br>"
            f"<b>ИТОГО</b><br>"
            f"<span style='color:#3498db'>План: {year_plan:.1f} млн</span><br>"
            f"<span style='color:#2ecc71'>2025: {year_25:.1f} млн</span><br>"
            f"<span style='color:#95a5a6'>2024: {year_24:.1f} млн</span><br>"
            f"<span style='color:{g_color}'>Δ% П/25: {g_sign}{year_g:.0f}%</span><br>"
            f"<span style='color:{d_color}'>Δ% 25/24: {d_sign}{year_d25_24:.0f}%</span>"
        )
        hover_texts.append(row_texts)
    
    # Plotly heatmap
    fig_h1 = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=month_labels,
        y=[d[:12] for d in pivot.index.tolist()],
        colorscale=[[0, '#e74c3c'], [0.3, '#f5b7b1'], [0.5, '#ffffff'], [0.7, '#abebc6'], [1, '#27ae60']],
        zmin=-20, zmax=20,
        text=pivot.values.round(0).astype(int),
        texttemplate="%{text}",
        textfont={"size": 9},
        showscale=False,
        hovertext=hover_texts,
        hoverinfo='text'
    ))
    # Динамическая высота (не более 280px)
    row_height = 25
    min_height = 100
    calc_height = min(280, max(min_height, len(pivot) * row_height + 40))
    
    fig_h1.update_layout(margin=dict(l=0,r=0,t=10,b=20), height=calc_height, hoverlabel=dict(bgcolor='white', font_size=12))
    fig_h1.update_xaxes(tickfont=dict(size=9), side='bottom', tickangle=0)
    fig_h1.update_yaxes(tickfont=dict(size=8), autorange='reversed')
    st.plotly_chart(fig_h1, use_container_width=True)

# 3. Таблица по филиалам (числа прироста)
with col3:
    st.caption("🏪 Филиалы %")
    p_br = df.groupby(['Филиал', 'Месяц']).agg({'План_Скорр': 'sum', 'Rev_2025': 'sum', 'Rev_2024': 'sum'}).reset_index()
    p_br['G'] = np.where(p_br['Rev_2025'] > 0, ((p_br['План_Скорр'] / p_br['Rev_2025']) - 1) * 100, 0)
    p_br['Δ_25_24'] = np.where(p_br['Rev_2024'] > 0, ((p_br['Rev_2025'] / p_br['Rev_2024']) - 1) * 100, 0)
    
    pivot_br = p_br.pivot(index='Филиал', columns='Месяц', values='G')
    pivot_br_plan = p_br.pivot(index='Филиал', columns='Месяц', values='План_Скорр')
    pivot_br_25 = p_br.pivot(index='Филиал', columns='Месяц', values='Rev_2025')
    pivot_br_24 = p_br.pivot(index='Филиал', columns='Месяц', values='Rev_2024')
    pivot_br_d25_24 = p_br.pivot(index='Филиал', columns='Месяц', values='Δ_25_24')
    
    for i in range(1, 13):
        if i not in pivot_br.columns: pivot_br[i] = 0
        if i not in pivot_br_plan.columns: pivot_br_plan[i] = 0
        if i not in pivot_br_25.columns: pivot_br_25[i] = 0
        if i not in pivot_br_24.columns: pivot_br_24[i] = 0
        if i not in pivot_br_d25_24.columns: pivot_br_d25_24[i] = 0
    
    pivot_br = pivot_br[range(1, 13)].fillna(0).sort_index(ascending=False)
    pivot_br_plan = pivot_br_plan[range(1, 13)].fillna(0).sort_index(ascending=False)
    pivot_br_25 = pivot_br_25[range(1, 13)].fillna(0).sort_index(ascending=False)
    pivot_br_24 = pivot_br_24[range(1, 13)].fillna(0).sort_index(ascending=False)
    pivot_br_d25_24 = pivot_br_d25_24[range(1, 13)].fillna(0).sort_index(ascending=False)
    
    # Добавляем колонку Итого
    pivot_br_total = df.groupby('Филиал').agg({'План_Скорр': 'sum', 'Rev_2025': 'sum'})
    pivot_br_total['Σ'] = np.where(pivot_br_total['Rev_2025'] > 0, 
        ((pivot_br_total['План_Скорр'] / pivot_br_total['Rev_2025']) - 1) * 100, 0)
    pivot_br['Σ'] = pivot_br_total['Σ']
    
    # Добавляем строку ИТОГО внизу только если больше 1 строки
    is_single_row_br = len(pivot_br) <= 1
    
    if not is_single_row_br:
        total_row_br_plan = pivot_br_plan.sum()
        total_row_br_25 = pivot_br_25.sum()
        total_row_br_24 = pivot_br_24.sum()
        total_row_br_g = pd.Series({m: ((total_row_br_plan[m] / total_row_br_25[m]) - 1) * 100 if total_row_br_25[m] > 0 else 0 for m in range(1, 13)})
        total_row_br_d25_24 = pd.Series({m: ((total_row_br_25[m] / total_row_br_24[m]) - 1) * 100 if total_row_br_24[m] > 0 else 0 for m in range(1, 13)})
        
        year_br_plan = total_row_br_plan.sum()
        year_br_25 = total_row_br_25.sum()
        total_br_sigma = ((year_br_plan / year_br_25) - 1) * 100 if year_br_25 > 0 else 0
        
        pivot_br.loc['ИТОГО'] = list(total_row_br_g.values) + [total_br_sigma]
        pivot_br_plan.loc['ИТОГО'] = total_row_br_plan.values
        pivot_br_25.loc['ИТОГО'] = total_row_br_25.values
        pivot_br_24.loc['ИТОГО'] = total_row_br_24.values
        pivot_br_d25_24.loc['ИТОГО'] = total_row_br_d25_24.values
    
    # Создаём кастомный hover текст
    month_labels_br = [MONTH_MAP_REV[i] for i in range(1, 13)] + ['Σ']
    hover_texts_br = []
    for branch in pivot_br.index:
        row_texts = []
        for m in range(1, 13):
            plan_val = pivot_br_plan.loc[branch, m] / 1e6
            f25_val = pivot_br_25.loc[branch, m] / 1e6
            f24_val = pivot_br_24.loc[branch, m] / 1e6
            g_val = pivot_br.loc[branch, m]
            d25_24 = pivot_br_d25_24.loc[branch, m]
            
            g_color = '#27ae60' if g_val >= 0 else '#e74c3c'
            d_color = '#27ae60' if d25_24 >= 0 else '#e74c3c'
            g_sign = '+' if g_val >= 0 else ''
            d_sign = '+' if d25_24 >= 0 else ''
            
            text = (
                f"<b>{branch[:15]}</b><br>"
                f"<b>{MONTH_MAP_REV[m]}</b><br>"
                f"<span style='color:#3498db'>План: {plan_val:.1f} млн</span><br>"
                f"<span style='color:#2ecc71'>2025: {f25_val:.1f} млн</span><br>"
                f"<span style='color:#95a5a6'>2024: {f24_val:.1f} млн</span><br>"
                f"<span style='color:{g_color}'>Δ% П/25: {g_sign}{g_val:.0f}%</span><br>"
                f"<span style='color:{d_color}'>Δ% 25/24: {d_sign}{d25_24:.0f}%</span>"
            )
            row_texts.append(text)
        
        # Итого колонка - полная информация как для месяцев
        year_plan = pivot_br_plan.loc[branch].sum() / 1e6
        year_25 = pivot_br_25.loc[branch].sum() / 1e6
        year_24 = pivot_br_24.loc[branch].sum() / 1e6
        year_g = pivot_br.loc[branch, 'Σ']
        year_d25_24 = ((pivot_br_25.loc[branch].sum() / pivot_br_24.loc[branch].sum()) - 1) * 100 if pivot_br_24.loc[branch].sum() > 0 else 0
        
        g_color = '#27ae60' if year_g >= 0 else '#e74c3c'
        d_color = '#27ae60' if year_d25_24 >= 0 else '#e74c3c'
        g_sign = '+' if year_g >= 0 else ''
        d_sign = '+' if year_d25_24 >= 0 else ''
        
        row_texts.append(
            f"<b>{branch[:15]}</b><br>"
            f"<b>ИТОГО</b><br>"
            f"<span style='color:#3498db'>План: {year_plan:.1f} млн</span><br>"
            f"<span style='color:#2ecc71'>2025: {year_25:.1f} млн</span><br>"
            f"<span style='color:#95a5a6'>2024: {year_24:.1f} млн</span><br>"
            f"<span style='color:{g_color}'>Δ% П/25: {g_sign}{year_g:.0f}%</span><br>"
            f"<span style='color:{d_color}'>Δ% 25/24: {d_sign}{year_d25_24:.0f}%</span>"
        )
        hover_texts_br.append(row_texts)
    
    # Plotly heatmap
    fig_h2 = go.Figure(data=go.Heatmap(
        z=pivot_br.values,
        x=month_labels_br,
        y=[f[:12] for f in pivot_br.index.tolist()],
        colorscale=[[0, '#e74c3c'], [0.3, '#f5b7b1'], [0.5, '#ffffff'], [0.7, '#abebc6'], [1, '#27ae60']],
        zmin=-20, zmax=20,
        text=pivot_br.values.round(0).astype(int),
        texttemplate="%{text}",
        textfont={"size": 9},
        showscale=False,
        hovertext=hover_texts_br,
        hovertemplate='%{hovertext}<extra></extra>'
    ))
    
    # Динамическая высота для филиалов (не более 280px)
    calc_height_br = min(280, max(100, len(pivot_br) * 25 + 40))
    
    fig_h2.update_layout(margin=dict(l=0,r=0,t=10,b=20), height=calc_height_br, hoverlabel=dict(bgcolor='white', font_size=12))
    fig_h2.update_xaxes(tickfont=dict(size=9), side='bottom', tickangle=0)
    fig_h2.update_yaxes(tickfont=dict(size=8), autorange='reversed')
    st.plotly_chart(fig_h2, use_container_width=True)

# 4. График сезонности
with col4:
    st.caption("📊 Сезонность %")
    total_25 = m_full['Rev_2025'].sum()
    total_plan = m_full['План_Скорр'].sum()
    total_24 = m_full['Rev_2024'].sum()
    
    m_full['Сез_25'] = m_full['Rev_2025'] / total_25 * 100 if total_25 > 0 else 0
    m_full['Сез_План'] = m_full['План_Скорр'] / total_plan * 100 if total_plan > 0 else 0
    m_full['Сез_24'] = m_full['Rev_2024'] / total_24 * 100 if total_24 > 0 else 0
    m_full['Δ_Сез'] = m_full['Сез_План'] - m_full['Сез_25']  # В процентных пунктах
    
    # --- ЭТАЛОННАЯ СЕЗОННОСТЬ СЕТИ (правильный расчёт) ---
    # --- ЭТАЛОННАЯ СЕЗОННОСТЬ СЕТИ (правильный расчёт) ---
    
    # DEBUG: Проверка наличия колонок (скрыто в экспандер)
    # with st.expander("DEBUG: Columns"):
    #     st.write(df.columns.tolist())
    
    # 1. Основной метод: через Network_Month (сумма продаж сети)
    if 'Network_Month' in df.columns:
        unique_net = df.drop_duplicates(subset=['Отдел', 'Месяц'])
        net_agg = unique_net.groupby('Месяц')['Network_Month'].sum().reset_index()
        net_total = net_agg['Network_Month'].sum()
        
        net_agg['Сез_Сеть'] = np.where(net_total > 0, (net_agg['Network_Month'] / net_total) * 100, 0)
        
        # Обновляем m_full
        m_full = pd.merge(m_full, net_agg[['Месяц', 'Сез_Сеть']], on='Месяц', how='left').fillna(0)
        
    elif 'Seasonality_Share' in df.columns:
        # Fallback 1: через Seasonality_Share (корректно для одного отдела)
        # Берем среднее по месяцу (так как для одного отдела значения одинаковые)
        seas_agg = df.groupby('Месяц')['Seasonality_Share'].mean().reset_index()
        seas_agg['Сез_Сеть'] = seas_agg['Seasonality_Share'] * 100
        m_full = pd.merge(m_full, seas_agg[['Месяц', 'Сез_Сеть']], on='Месяц', how='left').fillna(0)
        
    else:
        # Fallback 2: Равномерная
        m_full['Сез_Сеть'] = 100 / 12

    fig4 = go.Figure()

    # Сеть - Фиолетовая эталонная (на заднем плане, но яркая)
    fig4.add_trace(go.Scatter(
        x=m_full['M'], y=m_full['Сез_Сеть'], name='Сеть', 
        line=dict(color='#9b59b6', width=2, dash='dot'), mode='lines',
        hoverinfo='skip'
    ))
    
    # 2024 - серая пунктирная
    fig4.add_trace(go.Scatter(
        x=m_full['M'], y=m_full['Сез_24'], name='2024', 
        line=dict(color='#bdc3c7', width=1.5, dash='dot'), mode='lines+markers',
        marker=dict(size=4, color='#bdc3c7'),
        hoverinfo='skip'
    ))
    
    # 2025 - зелёная
    fig4.add_trace(go.Scatter(
        x=m_full['M'], y=m_full['Сез_25'], name='2025', 
        line=dict(color='#2ecc71', width=2), mode='lines+markers',
        marker=dict(size=6, color='#2ecc71'),
        hoverinfo='skip'
    ))
    
    # План - синяя пунктирная
    fig4.add_trace(go.Scatter(
        x=m_full['M'], y=m_full['Сез_План'], name='План', 
        line=dict(color='#3498db', width=2, dash='dash'), mode='lines+markers',
        marker=dict(size=6, color='#3498db', symbol='square'),
        hoverinfo='skip'
    ))
    
    # Единый hover
    hover_texts_sez = []
    for _, row in m_full.iterrows():
        delta = row['Δ_Сез']
        d_color = '#27ae60' if delta >= 0 else '#e74c3c'
        d_sign = '+' if delta >= 0 else ''
        hover_texts_sez.append(
            f"<b>{row['M']}</b><br>"
            f"<span style='color:#9b59b6'>Сеть: {row['Сез_Сеть']:.1f}%</span><br>"
            f"<span style='color:#2ecc71'>2025: {row['Сез_25']:.1f}%</span><br>"
            f"<span style='color:#3498db'>План: {row['Сез_План']:.1f}%</span><br>"
            f"<span style='color:#95a5a6'>2024: {row['Сез_24']:.1f}%</span><br>"
            f"<span style='color:{d_color}'>Δ п.п.: {d_sign}{delta:.1f}</span>"
        )
    
    fig4.add_trace(go.Scatter(
        x=m_full['M'], y=m_full['Сез_План'],
        mode='markers', marker=dict(size=15, opacity=0),
        hovertext=hover_texts_sez, hoverinfo='text', showlegend=False
    ))
    
    fig4.update_layout(
        margin=dict(l=0,r=0,t=10,b=20), height=280, 
        showlegend=True, 
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=8)),
        hoverlabel=dict(bgcolor='white', font_size=10),
        hovermode='x'
    )
    fig4.update_xaxes(tickfont=dict(size=8), tickangle=0)
    fig4.update_yaxes(tickfont=dict(size=8), ticksuffix="%")
    st.plotly_chart(fig4, use_container_width=True)


# Подготовка таблицы - используем уже рассчитанные колонки из calculate_plan
# Убеждаемся что Роль есть
if 'Роль' not in df.columns:
    df['Роль'] = 'Сопутствующий'

edit_df = df[['Филиал', 'Отдел', 'Месяц', 
              'Выручка_2024', 'Выручка_2025', 'Выручка_2025_Норм',
              'План_Скорр', 'План_Расч', 'План', 'Рекоменд',
              'Прирост_%', 'Прирост_24_26_%', 'Прирост_Год_%',
              'Сезонность_Факт', 'Сезонность_План',
              'Площадь_2025', 'Площадь_2026', 'Δ_Площадь_%',
              'Отдача_План', 'Отдача_2025', 'Δ_Отдача_%',
              'Формат', 'is_network_format', '_План_Расч_Исх', 'Авто_Корр',
              'Корр', 'Корр_Дельта', 'Final_Weight', 'Правило', 'Роль']].copy()

# Сортировка по месяцам хронологически
edit_df = edit_df.sort_values(by=['Филиал', 'Отдел', 'Месяц'])


# Колонка месяца с числовым префиксом (01 янв) для корректной строковой сортировки ("02" < "10")
def fmt_month_display(m):
    return f"{m:02d} {MONTH_MAP_REV[m]}"

edit_df['Мес'] = edit_df['Месяц'].apply(fmt_month_display)
edit_df['Корр±'] = edit_df['Корр_Дельта']

# Сортировка по числовому месяцу
edit_df = edit_df.sort_values(by=['Филиал', 'Отдел', 'Мес'])

# Отключаем переименование, чтобы вернуть полные названия колонок
# edit_df = edit_df.rename(columns={
#     'Выручка_2024': 'Выр.2024',
#     'Выручка_2025': 'Выр.2025',
#     'Выручка_2025_Норм': 'Выр.25(Н)',
#     'План_Скорр': 'План 2026',
#     'План_Расч': 'Расчёт',
#     'План': 'Цель',
#     'Прирост_%': 'Δ%_25',
#     'Прирост_24_26_%': 'Δ%_24',
#     'Сезонность_Факт': 'Сез.Факт',
#     'Сезонность_План': 'Сез.План',
#     'Final_Weight': 'Вес'
# })

# Удаляем старую колонку дельты (оставляем только Корр и Корр± для отображения/редактирования)
# Но нам нужны Корр и Корр_Дельта для логики сохранения! 
# Поэтому не удаляем их из edit_df, просто не включаем в default view если не надо.

# Порядок колонок
all_columns = ['Филиал', 'Отдел', 'Мес', 'Роль', 'Формат', 'Правило', 
               'Корр', 'Корр±', 'Авто_Корр',
               'План_Скорр', 'План_Расч', 'План', '_План_Расч_Исх', 'Рекоменд',
               'Выручка_2025', 'Выручка_2024', 'Выручка_2025_Норм',
               'Прирост_%', 'Прирост_24_26_%', 'Прирост_Год_%',
               'Сезонность_Факт', 'Сезонность_План',
               'Площадь_2025', 'Площадь_2026', 'Δ_Площадь_%',
               'Отдача_План', 'Отдача_2025', 'Δ_Отдача_%',
               'Final_Weight', 'is_network_format', 'Месяц']

# Фильтруем только те что есть (на случай если что-то не расчиталось)
all_columns = [c for c in all_columns if c in edit_df.columns]

# Применяем выбор колонок из sidebar (sel_columns)
column_order = [c for c in all_columns if c in sel_columns]
edit_df = edit_df[column_order]



# Функция для цветовой подсветки
def color_percent(val):
    if pd.isna(val):
        return ''
    if val > 10:
        return 'background-color: #27ae60; color: white'
    elif val > 0:
        return 'background-color: #a9dfbf'
    elif val > -10:
        return 'background-color: #f5b7b1'
    else:
        return 'background-color: #e74c3c; color: white'

# Применяем стили к копии для отображения
styled_df = edit_df.copy()

# Редактируемая таблица с автосохранением
def save_on_change():
    pass

# Применяем стили к дельтам для цветной подсветки
def style_dataframe(df):
    # Создаём стили для каждой ячейки
    styles = pd.DataFrame('', index=df.index, columns=df.columns)
    
    # Подсветка Прирост_% (ex Δ%_25)
    col_name_growth_25 = 'Прирост_%' 
    # Fallback to old name if not found (just in case)
    if col_name_growth_25 not in df.columns and 'Δ%_25' in df.columns:
        col_name_growth_25 = 'Δ%_25'

    if col_name_growth_25 in df.columns:
        styles[col_name_growth_25] = df[col_name_growth_25].apply(lambda x: 
            'background-color: #27ae60; color: white' if pd.notna(x) and x > 10 else
            'background-color: #a9dfbf' if pd.notna(x) and x > 0 else
            'background-color: #f5b7b1' if pd.notna(x) and x > -10 else
            'background-color: #e74c3c; color: white' if pd.notna(x) else ''
        )
    
    # Подсветка Прирост_24_26_% (ex Δ%_24)
    col_name_growth_24 = 'Прирост_24_26_%'
    if col_name_growth_24 not in df.columns and 'Δ%_24' in df.columns:
         col_name_growth_24 = 'Δ%_24'
         
    if col_name_growth_24 in df.columns:
        styles[col_name_growth_24] = df[col_name_growth_24].apply(lambda x: 
            'background-color: #27ae60; color: white' if pd.notna(x) and x > 10 else
            'background-color: #a9dfbf' if pd.notna(x) and x > 0 else
            'background-color: #f5b7b1' if pd.notna(x) and x > -10 else
            'background-color: #e74c3c; color: white' if pd.notna(x) else ''
        )
    
    return styles

# Функция форматирования чисел с пробелом
def fmt_num(x):
    if pd.isna(x):
        return ''
    return f'{x:,.0f}'.replace(',', ' ')

def fmt_num_sign(x):
    if pd.isna(x):
        return ''
    return f'{x:+,.0f}'.replace(',', ' ')

# ========== ПОДГОТОВКА ДАННЫХ ДЛЯ ОТОБРАЖЕНИЯ ==========
# Создаем отдельный DataFrame для отображения (display_df), 
# в котором числа превращются в красивые строки (1 000 000) и добавляется подсветка (цветом текста)

display_df = edit_df.copy()

# 1. Форматирование больших чисел (с пробелами)
static_num_cols = ['Выручка_2024', 'Выручка_2025', 'Выручка_2025_Norm', 
                  'План_Скорр', 'План_Расч', '_План_Расч_Исх', 'Рекоменд', 'План',
                  'Отдача_План', 'Отдача_2025']

def fmt_right(x):
    if pd.isna(x): return ""
    try:
        s = f"{float(x):,.0f}".replace(",", " ")
        return s.rjust(12, '\u2007')
    except:
        return str(x)

for col in static_num_cols:
    if col in display_df.columns:
        display_df[col] = display_df[col].apply(fmt_right)

# ========== ЕДИНАЯ РЕДАКТИРУЕМАЯ ТАБЛИЦА ==========
# Подготовка данных (как раньше, с эмодзи)
display_df = edit_df.copy()

# Форматирование для редактора
ignore_cols = ['Филиал', 'Отдел', 'Мес', 'Месяц', 'Роль', 'Формат', 'Правило', 'is_network_format', 'Final_Weight']
editable_cols = ['Корр', 'Корр±']

def fmt_abs_editor(x):
    if pd.isna(x): return ""
    try: return f"{float(x):,.0f}".replace(",", " ").rjust(12, '\u2007')
    except: return str(x)

def fmt_pct_editor(x):
    if pd.isna(x): return ""
    try:
        val = float(x)
        s = f"{val:,.1f}".replace(",", " ")
        # Градиентная шкала: 🟢 → 🟡 → ⚪ → 🟠 → 🔴
        if val >= 10:
            icon = "🟢"  # Ярко-зеленый (сильный рост)
        elif val >= 5:
            icon = "🟡"  # Желтый (умеренный рост)
        elif val > 0:
            icon = "⚪"  # Белый (слабый рост)
        elif val == 0:
            return s     # Без иконки
        elif val > -10:
            icon = "🟠"  # Оранжевый (небольшое падение)
        else:
            icon = "🔴"  # Красный (значительное падение, < -10%)
        
        sign = "+" if val > 0 else ""
        return f"{icon} {sign}{s}"
    except: return str(x)

for col in display_df.columns:
    if col in editable_cols or col in ignore_cols: continue
    is_pct = '%' in col or 'Сезонность' in col or 'Прирост' in col or 'Δ' in col
    if is_pct:
        display_df[col] = display_df[col].apply(fmt_pct_editor)
    elif pd.api.types.is_numeric_dtype(edit_df[col]):
        display_df[col] = display_df[col].apply(fmt_abs_editor)

# Конфиг колонок
disabled_cols = [c for c in edit_df.columns if c not in ['Корр', 'Корр±']]
col_config_dynamic = {}
for col in display_df.columns:
    if col in editable_cols:
        if col == 'Корр': col_config_dynamic[col] = st.column_config.NumberColumn("Корр", format="%.0f", min_value=-100000000)
        else: col_config_dynamic[col] = st.column_config.NumberColumn("Корр±", format="%+d", min_value=-100000000)
    elif col in ignore_cols: pass
    else: col_config_dynamic[col] = st.column_config.TextColumn(col)

# Условное отображение: редактирование только для авторизованных
if st.session_state.get('edit_authorized', False):
    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        height=600,
        hide_index=True,
        disabled=disabled_cols,
        column_config=col_config_dynamic,
        key="main_data_editor"
    )
else:
    # Только просмотр (без редактирования)
    st.dataframe(
        display_df,
        use_container_width=True,
        height=600,
        hide_index=True,
        column_config=col_config_dynamic
    )
    edited_df = display_df.copy()  # Пустышка для совместимости с остальным кодом

# --- НАСТРОЙКА (Прирост) --- ML оптимизатор управляет лимитами автоматически
# Только для авторизованных пользователей
if st.session_state.get('edit_authorized', False):
    with st.expander("⚙️ Настройка", expanded=False):
        tab_growth, tab_strat_growth = st.tabs(["📈 Прирост на год", "🎯 Прирост стратегических"])
        
        # === ВКЛАДКА 1: ПРИРОСТ НА ГОД ===
        with tab_growth:
            st.caption("Годовой прирост для Сопутствующих отделов. План = Факт 2025 × (1 + Прирост%) × Сезонность. Правило +6% минимум применяется только к Мини/Микро/Интернет.")
            
            # Используем df_base (полный датасет), чтобы настройки не зависели от фильтров
            target_df = df_base if 'df_base' in locals() and not df_base.empty else df
            
            if not target_df.empty:
                # Показываем ВСЕ филиалы (не только спец-форматы)
                all_branches_growth = sorted(target_df['Филиал'].unique())
                
                # Только Сопутствующие отделы
                if 'Роль' in target_df.columns:
                    accomp_depts = sorted(target_df[target_df['Роль'] == 'Сопутствующий']['Отдел'].unique())
                else:
                    accomp_depts = sorted(target_df['Отдел'].unique())
                    
                if len(accomp_depts) > 0:
                    # Загружаем сохраненные приросты
                    growth_file = os.path.join(DATA_DIR, 'growth_rates.json')
                    saved_growth = {}
                    if os.path.exists(growth_file):
                        try:
                            with open(growth_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                for item in data:
                                    saved_growth[(item['branch'], item['dept'])] = item['rate']
                        except:
                            pass
                    
                    # Строим DataFrame для редактора
                    df_growth_ui = pd.DataFrame(index=accomp_depts, columns=all_branches_growth)
                    
                    # Заполняем сохраненные значения
                    for (br, dp), val in saved_growth.items():
                        if br in all_branches_growth and dp in accomp_depts:
                            df_growth_ui.at[dp, br] = val
                    
                    # Функция автосохранения при изменении
                    def save_growth_auto():
                        """Автосохранение приростов при изменении"""
                        if 'growth_editor_matrix' in st.session_state:
                            edited_data = st.session_state['growth_editor_matrix']
                            current_df = df_growth_ui.copy()
                            
                            if 'edited_rows' in edited_data:
                                for row_idx, changes in edited_data['edited_rows'].items():
                                    row_label = current_df.index[int(row_idx)]
                                    for col, val in changes.items():
                                        current_df.at[row_label, col] = val
                            
                            new_growth_list = []
                            for dp in current_df.index:
                                for br in current_df.columns:
                                    val = current_df.at[dp, br]
                                    if pd.notna(val) and str(val).strip() != '':
                                        try:
                                            f_val = float(val)
                                            new_growth_list.append({'branch': br, 'dept': dp, 'rate': f_val})
                                        except:
                                            pass
                            
                            try:
                                with open(growth_file, 'w', encoding='utf-8') as f:
                                    json.dump(new_growth_list, f, ensure_ascii=False, indent=2)
                            except:
                                pass
                    
                    # Редактор прироста с автосохранением
                    edited_growth_df = st.data_editor(
                        df_growth_ui,
                        key='growth_editor_matrix',
                        use_container_width=True,
                        height=400,
                        on_change=save_growth_auto
                    )
                    
                    st.caption("💡 Изменения сохраняются автоматически")
                else:
                    st.info("Нет сопутствующих отделов")
        
        # === ВКЛАДКА 2: ПРИРОСТ СТРАТЕГИЧЕСКИХ ===
        with tab_strat_growth:
            st.caption("Годовой прирост для Стратегических отделов. Увеличение прироста одного отдела уменьшает другие пропорционально. Не влияет на ручные корректировки и методику Дверей/Кухонь.")
            
            target_df2 = df_base if 'df_base' in locals() and not df_base.empty else df
            
            if not target_df2.empty:
                all_branches_strat = sorted(target_df2['Филиал'].unique())
                
                excluded_depts = ['9. Двери, фурнитура дверная', 'Мебель для кухни']
                if 'Роль' in target_df2.columns:
                    strat_depts = sorted([d for d in target_df2[target_df2['Роль'] != 'Сопутствующий']['Отдел'].unique() 
                                         if d not in excluded_depts])
                else:
                    strat_depts = sorted([d for d in target_df2['Отдел'].unique() if d not in excluded_depts])
                    
                if len(strat_depts) > 0:
                    strat_growth_file = os.path.join(DATA_DIR, 'strategic_growth_rates.json')
                    saved_strat_growth = {}
                    if os.path.exists(strat_growth_file):
                        try:
                            with open(strat_growth_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                for item in data:
                                    saved_strat_growth[(item['branch'], item['dept'])] = item['rate']
                        except:
                            pass
                    
                    df_strat_growth_ui = pd.DataFrame(index=strat_depts, columns=all_branches_strat)
                    
                    for (br, dp), val in saved_strat_growth.items():
                        if br in all_branches_strat and dp in strat_depts:
                            df_strat_growth_ui.at[dp, br] = val
                    
                    def save_strat_growth_auto():
                        """Автосохранение приростов стратегических при изменении"""
                        if 'strat_growth_editor_matrix' in st.session_state:
                            edited_data = st.session_state['strat_growth_editor_matrix']
                            current_df = df_strat_growth_ui.copy()
                            
                            if 'edited_rows' in edited_data:
                                for row_idx, changes in edited_data['edited_rows'].items():
                                    row_label = current_df.index[int(row_idx)]
                                    for col, val in changes.items():
                                        current_df.at[row_label, col] = val
                            
                            new_strat_growth_list = []
                            for dp in current_df.index:
                                for br in current_df.columns:
                                    val = current_df.at[dp, br]
                                    if pd.notna(val) and str(val).strip() != '':
                                        try:
                                            f_val = float(val)
                                            new_strat_growth_list.append({'branch': br, 'dept': dp, 'rate': f_val})
                                        except:
                                            pass
                            
                            try:
                                with open(strat_growth_file, 'w', encoding='utf-8') as f:
                                    json.dump(new_strat_growth_list, f, ensure_ascii=False, indent=2)
                            except:
                                pass
                    
                    edited_strat_growth_df = st.data_editor(
                        df_strat_growth_ui,
                        key='strat_growth_editor_matrix',
                        use_container_width=True,
                        height=400,
                        on_change=save_strat_growth_auto
                    )
                    
                    st.caption("💡 Изменения сохраняются автоматически. Прирост перераспределяется только между стратегическими отделами.")
                else:
                    st.info("Нет стратегических отделов")
    
# Для логики сохранения нам нужно добавить в edited_df недостающие колонки (месяц числом), 
# чтобы логика внизу (iterrows) работала корректно.
# edited_df сейчас содержит только ['Филиал', 'Отдел', 'Мес', 'Корр', 'Корр±']
# Но логике сохранения нужны 'Месяц' (число) или умение парсить 'Мес'.
# Код ниже ("for _, row in edited_df.iterrows()") уже умеет парсить 'Мес', так что всё ок.


# Автосохранение корректировок из редактируемой таблицы
# Умное сохранение корректировок (Merge изменений)
saved_corrections = load_corrections_local()
# Превращаем список в словарь для быстрого поиска по ключу (Филиал, Отдел, Месяц)
# month преобразуем к int для надежности
corrections_map = {}
for item in saved_corrections:
    key = (item['branch'], item['dept'], int(item['month']))
    corrections_map[key] = item

changes_detected = False

# Проходим по текущей (возможно отфильтрованной) таблице
for _, row in edited_df.iterrows():
    # Определяем месяц (числом)
    m_val = row.get('Месяц')
    if pd.isna(m_val) or m_val == '':
        # Извлекаем число из формата 'N мес' (например '1 янв' -> 1)
        mes_str = str(row.get('Мес', '1'))
        m_val = int(mes_str.split()[0]) if mes_str and mes_str[0].isdigit() else 1
    
    try:
        month = int(m_val)
    except:
        continue

    branch = row['Филиал']
    dept = row['Отдел']
    key = (branch, dept, month)
    
    # Получаем существующую запись (если есть)
    old_item = corrections_map.get(key)
    old_corr = old_item.get('corr') if old_item else None
    old_delta = old_item.get('delta') if old_item else None
    
    current_corr = old_corr
    current_delta = old_delta

    # Обработка Корр
    if 'Корр' in edited_df.columns:
        # Колонка видна - принимаем значение из редактора (число или очистка)
        raw_val = row.get('Корр')
        if pd.notna(raw_val):
            try:
                val = float(raw_val)
                rounded_val = round(val / 10000) * 10000
                if val != 0 and rounded_val == 0:
                    current_corr = None # Явное удаление (например ввели 0)
                else:
                    current_corr = int(rounded_val)
            except:
                current_corr = None
        else:
            # Колонка есть, но значение пустое -> пользователь очистил
            current_corr = None
            
    # Обработка Корр±
    if 'Корр±' in edited_df.columns:
        # Колонка видна
        raw_val = row.get('Корр±')
        if pd.notna(raw_val):
            try:
                val = float(raw_val)
                rounded_val = round(val / 10000) * 10000
                if val != 0 and rounded_val == 0:
                    current_delta = None
                else:
                    current_delta = int(rounded_val)
            except:
                current_delta = None
        else:
            # Колонка есть, но значение пустое -> пользователь очистил
            current_delta = None
            
    # Проверяем, изменилось ли что-то
    if current_corr != old_corr or current_delta != old_delta:
        # Если оба значения пустые -> удаляем запись
        if current_corr is None and current_delta is None:
            if key in corrections_map:
                del corrections_map[key]
                changes_detected = True
        else:
            # Обновляем запись (сохраняя то что могло быть скрыто но перенесено через current_*)
            new_item = {
                'branch': branch,
                'dept': dept,
                'month': month,
                'corr': current_corr,
                'delta': current_delta
            }
            corrections_map[key] = new_item
            changes_detected = True

if changes_detected:
    new_corrections_list = list(corrections_map.values())
    save_corrections_local(new_corrections_list)
    
    # Показываем что сохранено и обновляем
    st.toast("✅ Корректировка сохранена!")
    st.cache_data.clear()
    st.rerun()

# Статистика корректировок (компактно)
corr_count = (edited_df['Корр'].notna().sum() if 'Корр' in edited_df.columns else 0) + \
             (edited_df['Корр±'].notna().sum() if 'Корр±' in edited_df.columns else 0)
if corr_count > 0:
    st.caption(f"✏️ Корректировок: {corr_count}")

