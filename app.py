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

warnings.filterwarnings('ignore')

st.set_page_config(page_title="План 2026", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# Убираем лишние отступы Streamlit
st.markdown("""
<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    div[data-testid="stVerticalBlock"] > div {gap: 0.3rem;}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

DATA_DIR = '/home/eveselove/PLANB/data'
DATA_FILE = '/home/eveselove/PLAN/dashboard_data.csv'

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



if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


CONFIG = {
    'rounding_step': 10000,
}

MONTH_MAP = {
    'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6,
    'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12
}
MONTH_MAP_REV = {v: k for k, v in MONTH_MAP.items()}

BUSINESS_RULES = {
    'MIN_PLAN_THRESHOLD': 20000,
}

WEIGHT_2024 = 0.5
WEIGHT_2025 = 0.5

# ============================================================================
# ЛОКАЛЬНОЕ ХРАНИЛИЩЕ
# ============================================================================

def save_corrections_local(corrections_list):
    try:
        filepath = os.path.join(DATA_DIR, 'corrections.json')
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
    """Проверяет наличие корректировки"""
    check = df['Корр'].notna() | df['Корр_Дельта'].notna()
    if 'Авто_Корр' in df.columns:
        check = check | df['Авто_Корр'].notna()
    return check & mask if mask is not None else check

def calc_growth_pct(plan, fact):
    if isinstance(plan, pd.Series):
        return np.where(fact > 0, ((plan / fact - 1) * 100).round(1), 0.0)
    return round((plan / fact - 1) * 100, 1) if fact > 0 else 0.0


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
MIN_PLAN_THRESHOLD = 20000

# Шаг округления
ROUNDING_STEP = 10000

# Квартальная прогрессия роста для Дверей и Кухни
QUARTER_PROGRESS_DOORS = {3: 0.15, 6: 0.30, 9: 0.60, 12: 1.00}
QUARTER_PROGRESS_KITCHEN = {3: 0.15, 6: 0.30, 9: 0.60, 12: 1.00}


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
            fact_2025 = df.loc[idx, 'Выручка_2025'] if 'Выручка_2025' in df.columns else 0
            fact_2024 = df.loc[idx, 'Выручка_2024'] if 'Выручка_2024' in df.columns else 0
            fact_2025 = fact_2025 if pd.notna(fact_2025) else 0
            fact_2024 = fact_2024 if pd.notna(fact_2024) else 0
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
    План ≥ Выручка_2025 × 1.06
    """
    MIN_GROWTH = 1.06
    
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
        has_corr = df.loc[indices, 'Корр'].notna() | df.loc[indices, 'Корр_Дельта'].notna()
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
        other_indices = [idx for idx in other_indices
                       if not (pd.notna(df.loc[idx, 'Корр']) or pd.notna(df.loc[idx, 'Корр_Дельта']))]
        
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
    
    # Получаем отделы с ручными корректировками (их не трогаем)
    has_corr = result['Корр'].notna() | result['Корр_Дельта'].notna()
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
    
    # Сетевая выручка по нормализованным данным
    network_month = df_s_2025.groupby(['Отдел', 'Месяц'])['Выручка_Norm'].sum().reset_index()
    network_month.columns = ['Отдел', 'Месяц', 'Network_Month']
    
    network_year = df_s_2025.groupby('Отдел')['Выручка_Norm'].sum().reset_index()
    network_year.columns = ['Отдел', 'Network_Year']
    
    # Сезонность = доля месяца в году
    seasonality = pd.merge(network_month, network_year, on='Отдел', how='left')
    seasonality['Seasonality_Share'] = np.where(
        seasonality['Network_Year'] > 0,
        seasonality['Network_Month'] / seasonality['Network_Year'],
        1.0 / 12
    )
    
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
            # "Только 2025" — для Интернет используем сезонность
            if fmt == 'Интернет':
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
            if fmt == 'Интернет':
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
    df_master = pd.merge(df_master, df_branch_plans[['Филиал', 'Месяц', 'План']], 
                         on=['Филиал', 'Месяц'], how='left')


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

    # ========== ШАГ 12: Распределение плана по отделам ==========
    results = []
    for (branch, month), group in df_master.groupby(['Филиал', 'Месяц']):
        target = group['План'].iloc[0]
        if pd.isna(target):
            results.append(group)
            continue
        target = int(round(target))
        
        g = group.copy()
        weights = g['Final_Weight'].copy()
        fixed_mask = has_correction(g)
        no_plan_mask = g['_is_no_plan']
        active_mask = ~fixed_mask & ~no_plan_mask

        # Теоретический план
        total_weight = weights.sum()
        if total_weight > 0:
            g['_theoretical'] = target * (weights / total_weight)
        else:
            g['_theoretical'] = 0

        # "Не считаем план" без корректировки = 0
        no_plan_without_corr = no_plan_mask & ~fixed_mask
        g.loc[no_plan_without_corr, 'План_Расч'] = 0

        # Фиксированные (с корректировками)
        if fixed_mask.any():
            for idx in g.index[fixed_mask]:
                corr = g.loc[idx, 'Корр']
                delta = g.loc[idx, 'Корр_Дельта']
                base = g.loc[idx, '_theoretical']

                if pd.notna(corr):
                    final = corr + (delta if pd.notna(delta) else 0)
                elif pd.notna(delta):
                    final = base + delta
                else:
                    final = base

                g.loc[idx, 'План_Расч'] = max(0, final)

        # Остаток на активных
        actual_fixed = g.loc[fixed_mask, 'План_Расч'].sum() if fixed_mask.any() else 0
        actual_no_plan = g.loc[no_plan_without_corr, 'План_Расч'].sum() if no_plan_without_corr.any() else 0
        remaining_target = target - actual_fixed - actual_no_plan

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
        current_total = g['План_Расч'].sum()
        diff = target - current_total
        steps_needed = int(diff // step)
        
        if steps_needed != 0:
            # Считаем остатки
            g.loc[active_mask, 'diff_val'] = g.loc[active_mask, 'raw_plan'] - g.loc[active_mask, 'План_Расч']
            ascending = (steps_needed < 0)
            sorted_indices = g[active_mask].sort_values('diff_val', ascending=ascending).index
            indices_to_adjust = sorted_indices[:abs(steps_needed)]
            adjustment = step if steps_needed > 0 else -step
            g.loc[indices_to_adjust, 'План_Расч'] += adjustment
        
        # Финальное распределение остатка пропорционально весам
        current_total_after = g['План_Расч'].sum()
        final_diff = target - current_total_after
        if final_diff != 0:
            # Распределяем остаток пропорционально весам активных отделов
            distribute_mask = active_mask & (g['План_Расч'] > 0)
            if distribute_mask.any():
                w = weights.loc[distribute_mask]
                w_sum = w.sum()
                if w_sum > 0:
                    # Распределяем пропорционально
                    distribution = final_diff * (w / w_sum)
                    g.loc[distribute_mask, 'План_Расч'] += distribution
                    # Финальное округление до step
                    g.loc[distribute_mask, 'План_Расч'] = (g.loc[distribute_mask, 'План_Расч'] / step).round(0).astype(int) * step
                    
                    # Если остался микроостаток — на максимальный
                    micro_diff = target - g['План_Расч'].sum()
                    if micro_diff != 0:
                        max_idx = g.loc[distribute_mask, 'План_Расч'].idxmax()
                        g.loc[max_idx, 'План_Расч'] += micro_diff
        
        # Чистим временные колонки
        for col in ['_theoretical', 'raw_plan', 'diff_val']:
            if col in g.columns:
                g = g.drop(columns=[col])

        results.append(g)


    if results:
        result = pd.concat(results, ignore_index=True)
    else:
        result = df_master

    # ========== ШАГ 12.5: Промежуточные правила (Минимумы, Плавный рост) ==========
    # Для работы apply функций нужна колонка План_Скорр (они работают с ней)
    result['План_Скорр'] = result['План_Расч'].copy()
    
    apply_doors_smooth_growth(result)
    apply_kitchen_smooth_growth(result)
    result = apply_min_plan_network(result)
    
    # 4. Компрессор (перераспределение по ролям)
    if role_coefficients:
        result = apply_load_coefficients(result, role_coefficients)
    
    # Возвращаем изменения в переменную расчета для балансировки
    result['План_Расч'] = result['План_Скорр']

    # ========== ШАГ 13: ФИНАЛЬНАЯ БАЛАНСИРОВКА ==========
    # Проверяем сходимость по каждому филиалу/месяцу и перераспределяем остаток
    
    for (branch, month), group in result.groupby(['Филиал', 'Месяц']):
        idx = group.index
        
        target = result.loc[idx, 'План'].iloc[0]
        if pd.isna(target):
            continue
        target = int(round(target))
        
        current_sum = result.loc[idx, 'План_Расч'].sum()
        diff = target - current_sum
        
        if diff == 0:
            continue
        
        # Находим активные отделы
        # ИСКЛЮЧАЯ те, которые имеют ручные корректировки (мы должны сохранить их значения)
        group_slice = result.loc[idx]
        fixed_mask = has_correction(group_slice)
        
        active_mask = (group_slice['План_Расч'] > 0) & (~fixed_mask)
        active_idx = idx[active_mask]
        
        if len(active_idx) == 0:
            active_idx = idx 
        
        # === ИТЕРАТИВНОЕ РАСПРЕДЕЛЕНИЕ С УЧЕТОМ ЛИМИТОВ (WATER FILLING) ===
        
        # Получаем данные 2025 года для расчета лимитов
        rev_col = 'Rev_2025' if 'Rev_2025' in result.columns else 'Выручка_2025'
        
        active_candidates = result.loc[active_idx].copy()
        
        # Функция определения лимита для конкретной строки
        def get_max_plan(row):
            # Если лимиты не переданы - нет ограничений
            if not limits:
                return float('inf')
            
            branch_name = row['Филиал']
            dept_name = row['Отдел']
            
            # Ключ может быть кортежем (Branch, Dept) или строкой
            # Пробуем форматы хранения
            limit_val = limits.get((branch_name, dept_name))
            
            # Если в таблице пусто (None) -> нет лимита
            if limit_val is None or limit_val == '':
                return float('inf')
                
            try:
                pct = float(limit_val)
            except (ValueError, TypeError):
                return float('inf')
            
            base_rev = row.get(rev_col, 0)
            if base_rev <= 0:
                return float('inf') 
            
            return base_rev * (1 + pct / 100.0)

        current_limits_series = active_candidates.apply(get_max_plan, axis=1)
        
        # Начальное состояние
        participants = list(active_idx)
        remaining_diff = diff
        
        while abs(remaining_diff) > 1 and participants:
            # Текущие веса участников
            current_parts = result.loc[participants]
            weights = current_parts.get('Final_Weight', pd.Series(1, index=participants))
            
            w_sum = weights.sum()
            if w_sum == 0:
                weights = current_parts['План_Расч']
                w_sum = weights.sum()
            
            shares = (weights / w_sum) if w_sum > 0 else pd.Series(1.0 / len(participants), index=participants)
            
            # Попытка распределить
            to_distribute = shares * remaining_diff
            
            overflow_indices = []
            
            if remaining_diff > 0:
                predicted_plan = result.loc[participants, 'План_Расч'] + to_distribute
                
                # Сравниваем с лимитом
                subset_limits = current_limits_series.loc[participants]
                overshoot = predicted_plan > subset_limits
                
                if overshoot.any():
                    overflow_indices = overshoot[overshoot].index.tolist()
                    for o_idx in overflow_indices:
                        limit_val = subset_limits.loc[o_idx]
                        current_val = result.loc[o_idx, 'План_Расч']
                        added = max(0, limit_val - current_val)
                        result.loc[o_idx, 'План_Расч'] = limit_val
                        remaining_diff -= added
            
            if not overflow_indices:
                result.loc[participants, 'План_Расч'] += to_distribute
                remaining_diff = 0
                break
            else:
                for o_idx in overflow_indices:
                    participants.remove(o_idx)
        
        # Если цикл завершился (все переполнились), а remain_diff остался
        if abs(remaining_diff) > 1 and not participants:
             # Все переполнились. Принудительно размазываем остаток
             all_active = active_idx
             weights = result.loc[all_active, 'Final_Weight']
             w_sum = weights.sum()
             dist_weights = (weights / w_sum) if w_sum > 0 else pd.Series(1, index=all_active)
             result.loc[all_active, 'План_Расч'] += remaining_diff * dist_weights

        # Округление (Largest Remainder Method)
        # Применяем ко всем активным, так как после итераций у нас могут быть дроби
        current_vals = result.loc[active_idx, 'План_Расч']
        rounded_vals = current_vals.round(0).astype(int)
        result.loc[active_idx, 'План_Расч'] = rounded_vals
        
        # Остаток от округления - на макс вес (среди незафиксированных лимитом, если возможно, или просто макс вес)
        # Упрощаем: кидаем на макс вес из всех активных
        new_diff = target - result.loc[idx, 'План_Расч'].sum()
        if new_diff != 0:
            candidates_w = result.loc[active_idx, 'Final_Weight']
            if candidates_w.sum() == 0:
                 candidates_w = result.loc[active_idx, 'План_Расч']
            
            max_w_idx = candidates_w.idxmax()
            result.loc[max_w_idx, 'План_Расч'] += new_diff

    # ========== ШАГ 14: Финализация ==========
    result['План_Скорр'] = result['План_Расч'].copy()

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
    
    # Рекомендуемый план (План_Расч до корректировок) 
    result['Рекоменд'] = result['План_Расч'].copy()

    # Удаляем служебные колонки
    cols_to_drop = ['_is_no_plan', '_is_only_2025', '_is_2024_2025', '_is_format', '_is_format_only', 
                    '_base', '_total_base', 'Network_Month', 'Format_Network_Month']
    result = result.drop(columns=[c for c in cols_to_drop if c in result.columns], errors='ignore')

    return result



@st.cache_data(ttl=300, show_spinner="📊 Загрузка данных...")
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
    
    # Полный цикл расчета теперь внутри calculate_plan
    result = calculate_plan(df_sales, corrections=corrections, role_coefficients=role_coefficients, limits=limits)
    
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

if 'data_loaded' not in st.session_state:
    with st.spinner("📊 Загрузка данных из Google Sheets..."):
        st.session_state['raw_sales'] = load_raw_data()
        st.session_state['rules'] = load_rules()
        st.session_state['roles'] = load_roles()
        st.session_state['branch_plans'] = load_branch_plans()
        st.session_state['areas'] = load_areas()
        st.session_state['data_loaded'] = True
        st.session_state['load_time'] = pd.Timestamp.now().strftime('%H:%M:%S')

# Сайдбар - Кнопка обновления вверху
if st.sidebar.button("🔄 Обновить", type="primary"):
    for key in ['data_loaded', 'raw_sales', 'rules', 'roles', 'branch_plans', 'areas']:
        if key in st.session_state:
            del st.session_state[key]
    st.cache_data.clear()
    st.rerun()

# Редактор лимитов перенесен в основную часть страницы (под графики)
pass

# Заголовок и дата
st.sidebar.header("📊 Фильтры")
st.sidebar.caption(f"📅 Данные: {st.session_state.get('load_time', 'N/A')}")

# ========== КОМПРЕССОР (Коэффициенты нагрузки) ==========
with st.sidebar.expander("⚖️ Компрессор (K нагрузки)", expanded=False):
    st.caption("Коэффициенты перераспределения нагрузки по ролям")
    st.caption("1.0 = без изменений, >1 = больше, <1 = меньше")
    
    # Загружаем сохранённые настройки компрессора
    saved_compressor = load_compressor_local()
    
    # Роли и их дефолтные коэффициенты
    ROLE_DEFAULTS = {
        'Краски': 1.0,
        'Обои': 1.0,
        'Стратегический': 1.0,
        'Сопутствующий': 1.0
    }
    
    role_coefficients = {}
    for role, default_val in ROLE_DEFAULTS.items():
        # Ищем сохранённое значение по роли
        saved_val = 1.0
        for key, vals in saved_compressor.items():
            if key == role or (isinstance(key, tuple) and key[1] == role):
                saved_val = vals.get('growth', 1.0)
                break
        
        coef = st.slider(
            f"K: {role}", 
            min_value=0.5, 
            max_value=1.5, 
            value=saved_val, 
            step=0.05,
            key=f"comp_{role}"
        )
        if coef != 1.0:
            role_coefficients[role] = coef
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Сохранить", key="save_comp"):
            # Сохраняем коэффициенты
            comp_to_save = {role: {'growth': role_coefficients.get(role, 1.0), 'decline': 1.0} 
                          for role in ROLE_DEFAULTS.keys()}
            if save_compressor_local(comp_to_save):
                st.success("✓")
    with col2:
        if st.button("🔄 Сброс", key="reset_comp"):
            # Удаляем файл компрессора
            import os
            filepath = os.path.join(DATA_DIR, 'compressor.json')
            if os.path.exists(filepath):
                os.remove(filepath)
                st.rerun()

# Загрузка данных с учётом корректировок и расчётом плана
df_base = get_plan_data(role_coefficients=role_coefficients if role_coefficients else None)


if df_base.empty:
    st.error("Нет данных для отображения")
    st.stop()

# Получаем все уникальные значения
all_branches = sorted(df_base['Филиал'].unique())
all_depts = sorted(df_base['Отдел'].unique())
all_months = list(range(1, 13))

# Загружаем сохранённые фильтры
saved_filters = load_filters_local()

st.sidebar.divider()

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
if st.sidebar.button("💾 Сохранить фильтры"):
    filters_to_save = {
        'branches': sel_branches,
        'depts': sel_depts,
        'months': sel_months
    }
    if save_filters_local(filters_to_save):
        st.sidebar.success("Фильтры сохранены!")

st.sidebar.divider()


# Выбор колонок для таблицы
st.sidebar.header("📋 Колонки таблицы")
all_columns = ['Филиал', 'Отдел', 'Мес', 'Роль', 'Корр±', 'Корр', 'Рекоменд', 'План 2026', 
               'Выр.2025', 'Выр.2024', 'Выр.25(Н)', 'Δ%_25', 'Δ%_24', 
               'Сез.Факт', 'Сез.План', 'Вес', 'Цель', 'Расчёт', 'Правило']
default_columns = ['Филиал', 'Отдел', 'Мес', 'Роль', 'Корр±', 'Корр', 'Рекоменд', 'План 2026', 
                   'Выр.2025', 'Выр.2024', 'Δ%_25', 'Δ%_24', 'Сез.Факт', 'Сез.План']
sel_columns = st.sidebar.multiselect("Показать колонки", all_columns, default=default_columns)



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



# Убираем отступы вверху страницы
st.markdown("""
<style>
    .block-container {padding-top: 1rem !important; padding-bottom: 0 !important;}
    header {visibility: hidden;}
    .stApp > header {display: none;}
</style>
""", unsafe_allow_html=True)

# KPI (компактная строка)
total_plan = df['План_Скорр'].sum()
total_fact = df['Rev_2025'].sum()
total_fact_24 = df['Rev_2024'].sum()

# ========== ПРОВЕРКА СХОДИМОСТИ ==========
# Используем План из df (уже содержит целевые планы из calculate_plan)

convergence_ok = True
convergence_msg = ""
convergence_details = {}

if 'План' in df.columns:
    # Целевой план — уникальные значения по филиалу/месяцу
    target_by_group = df.groupby(['Филиал', 'Месяц'])['План'].first()
    target_total = target_by_group.sum()
    
    # Распределённый план (сумма по отделам)
    distributed_total = df['План_Скорр'].sum()
    
    # Отклонение
    deviation = distributed_total - target_total
    deviation_pct = (deviation / target_total * 100) if target_total > 0 else 0
    
    # Проверка по каждому филиалу-месяцу
    for (branch, month), grp in df.groupby(['Филиал', 'Месяц']):
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
col1, col2, col3, col4 = st.columns([1, 1.5, 1.5, 1])


# 1. График динамики
with col1:
    st.caption("📈 Динамика")
    # DEBUG: Проверка данных
    aggregated_sum = df['План_Скорр'].sum()
    # st.info(f"Сумма плана (фильтр): {aggregated_sum:,.0f} | Строк: {len(df)}")
    all_months_df = pd.DataFrame({'Месяц': range(1, 13)})
    m_agg = df.groupby('Месяц').agg({
        'План_Скорр': 'sum',
        'План_Расч': 'sum',
        'Корр_Дельта': 'sum',
        'Rev_2025': 'sum',
        'Rev_2024': 'sum'
    }).reset_index()
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
    
    # Аннотации с процентами у основания столбцов
    if show_plan:
        y_min = m_full['План_Скорр'].min() * 0.02
        annotations = []
        for _, row in m_full.iterrows():
            val = row['Δ_План_25']
            color = '#27ae60' if val >= 0 else '#e74c3c'
            annotations.append(dict(
                x=row['M'], y=y_min,
                text=f"<b>{val:+.0f}%</b>",
                showarrow=False,
                font=dict(size=14, color=color),
                bgcolor='rgba(255,255,255,0.85)',
                borderpad=2
            ))
        fig1.update_layout(annotations=annotations)
    
    fig1.update_layout(
        margin=dict(l=0,r=0,t=10,b=30), height=320, 
        showlegend=True, 
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, font=dict(size=14)),
        hoverlabel=dict(bgcolor='white', font_size=16),
        hovermode='x'
    )
    fig1.update_xaxes(tickfont=dict(size=14), tickangle=0)
    fig1.update_yaxes(tickfont=dict(size=14), showticklabels=False)
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
    # Динамическая высота (не более 320px)
    row_height = 30
    min_height = 100
    calc_height = min(320, max(min_height, len(pivot) * row_height + 50))
    
    fig_h1.update_layout(margin=dict(l=0,r=0,t=10,b=30), height=calc_height, hoverlabel=dict(bgcolor='white', font_size=16))
    fig_h1.update_xaxes(tickfont=dict(size=14), side='bottom')
    fig_h1.update_yaxes(tickfont=dict(size=10), autorange='reversed')
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
    
    # Динамическая высота для филиалов (не более 320px)
    calc_height_br = min(320, max(100, len(pivot_br) * 30 + 50))
    
    fig_h2.update_layout(margin=dict(l=0,r=0,t=10,b=30), height=calc_height_br, hoverlabel=dict(bgcolor='white', font_size=16))
    fig_h2.update_xaxes(tickfont=dict(size=14), side='bottom')
    fig_h2.update_yaxes(tickfont=dict(size=10), autorange='reversed')
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
    
    fig4 = go.Figure()
    
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
        margin=dict(l=0,r=0,t=10,b=30), height=320, 
        showlegend=True, 
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=16)),
        hoverlabel=dict(bgcolor='white', font_size=16),
        hovermode='x'
    )
    fig4.update_xaxes(tickfont=dict(size=14), tickangle=0)
    fig4.update_yaxes(tickfont=dict(size=14), ticksuffix="%")
    st.plotly_chart(fig4, use_container_width=True)

# --- РЕДАКТОР ЛИМИТОВ РОСТА (Под графиками) ---
with st.expander("⚙️ Настройка лимитов роста (%)", expanded=False):
    st.caption("Оставьте ячейку пустой для снятия лимита (по умолчанию рост не ограничен для Мини форматиов, 6% для остальных). Введенное значение (например 5) означает лимит +5% к 2025 году. Изменения сохраняются автоматически.")
    
    # Загружаем текущие сохраненные лимиты
    current_limits = load_limits_local()
    
    if 'raw_sales' in st.session_state:
        df_raw = st.session_state['raw_sales']
        if not df_raw.empty:
            all_branches = sorted(df_raw['Филиал'].unique())
            all_depts = sorted(df_raw['Отдел'].unique())
            
            # Строим исходный DF для отображения
            df_lim_ui = pd.DataFrame(index=all_depts, columns=all_branches)
            
            # Заполняем
            for (br, dp), val in current_limits.items():
                if br in all_branches and dp in all_depts:
                    df_lim_ui.at[dp, br] = val
            
            # Редактор
            edited_limits_df = st.data_editor(
                df_lim_ui,
                key='limits_editor_matrix_main',
                use_container_width=True,
                height=400
            )
            
            # АВТОСОХРАНЕНИЕ ОТКЛЮЧЕНО (вызывало циклическое обновление)
            # Возвращаем кнопку сохранения
            if st.button("💾 Сохранить изменения лимитов", type="primary"):
                new_limits_dict = {}
                for dp in edited_limits_df.index:
                    for br in edited_limits_df.columns:
                        val = edited_limits_df.at[dp, br]
                        if pd.notna(val) and str(val).strip() != '':
                            try:
                                f_val = float(val)
                                new_limits_dict[(br, dp)] = f_val
                            except:
                                pass
                
                if save_limits_local(new_limits_dict):
                    st.toast("Лимиты сохранены! Обновляем...", icon="✅")
                    st.rerun()
    else:
        st.info("Загрузка данных...")


# Подготовка таблицы - используем уже рассчитанные колонки из calculate_plan
# Убеждаемся что Роль есть
if 'Роль' not in df.columns:
    df['Роль'] = 'Сопутствующий'

edit_df = df[['Филиал', 'Отдел', 'Месяц', 
              'Выручка_2024', 'Выручка_2025', 'Выручка_2025_Норм',
              'План_Скорр', 'План_Расч', 'План', 'Рекоменд',
              'Прирост_%', 'Прирост_24_26_%',
              'Сезонность_Факт', 'Сезонность_План',
              'Корр', 'Корр_Дельта', 'Final_Weight', 'Правило', 'Роль']].copy()

# Сортировка по месяцам хронологически
edit_df = edit_df.sort_values(by=['Филиал', 'Отдел', 'Месяц'])


# Колонка месяца с числовым префиксом для правильной сортировки (1 янв, 2 фев...)
def fmt_month_display(m):
    return f"{m} {MONTH_MAP_REV[m]}"

edit_df['Мес'] = edit_df['Месяц'].apply(fmt_month_display)
edit_df['Корр±'] = edit_df['Корр_Дельта']

# Сортировка по числовому месяцу
edit_df = edit_df.sort_values(by=['Филиал', 'Отдел', 'Мес'])

# Переименовываем для отображения
edit_df = edit_df.rename(columns={
    'Выручка_2024': 'Выр.2024',
    'Выручка_2025': 'Выр.2025',
    'Выручка_2025_Норм': 'Выр.25(Н)',
    'План_Скорр': 'План 2026',
    'План_Расч': 'Расчёт',
    'План': 'Цель',
    'Прирост_%': 'Δ%_25',
    'Прирост_24_26_%': 'Δ%_24',
    'Сезонность_Факт': 'Сез.Факт',
    'Сезонность_План': 'Сез.План',
    'Final_Weight': 'Вес'
})

# Удаляем старую колонку
edit_df = edit_df.drop(columns=['Корр_Дельта'])

# Порядок колонок как в ноутбуке
all_columns = ['Филиал', 'Отдел', 'Мес', 'Роль', 'Корр±', 'Корр', 'Рекоменд', 'План 2026', 
                'Выр.2025', 'Выр.2024', 'Выр.25(Н)', 'Δ%_25', 'Δ%_24', 
                'Сез.Факт', 'Сез.План', 'Вес', 'Цель', 'Расчёт', 'Правило', 'Месяц']
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
    
    # Подсветка Δ%_25
    if 'Δ%_25' in df.columns:
        styles['Δ%_25'] = df['Δ%_25'].apply(lambda x: 
            'background-color: #27ae60; color: white' if pd.notna(x) and x > 10 else
            'background-color: #a9dfbf' if pd.notna(x) and x > 0 else
            'background-color: #f5b7b1' if pd.notna(x) and x > -10 else
            'background-color: #e74c3c; color: white' if pd.notna(x) else ''
        )
    
    # Подсветка Δ%_24
    if 'Δ%_24' in df.columns:
        styles['Δ%_24'] = df['Δ%_24'].apply(lambda x: 
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

# Показываем стилизованную таблицу
styled = edit_df.style.apply(lambda _: style_dataframe(edit_df), axis=None)
styled = styled.format({
    'Выр.2024': fmt_num,
    'Выр.2025': fmt_num,
    'Выр.25(Н)': fmt_num,
    'План 2026': fmt_num,
    'Рекоменд': fmt_num,
    'Расчёт': fmt_num,
    'Цель': fmt_num,
    'Δ%_25': '{:.1f}',
    'Δ%_24': '{:.1f}',
    'Сез.Факт': '{:.1f}',
    'Сез.План': '{:.1f}',
    'Вес': '{:.3f}',
    'Корр': fmt_num,
    'Корр±': fmt_num_sign,
}, na_rep='')

# Используем st.data_editor для редактирования Корр и Корр±
# Для красоты превращаем нередактируемые числа в текст с разделителями и псевдо-выравниванием
display_df = edit_df.copy()
static_num_cols = ['Выр.2024', 'Выр.2025', 'Выр.25(Н)', 'План 2026', 'Рекоменд', 'Расчёт', 'Цель']

def fmt_right(x):
    if pd.isna(x): return ""
    # Обычный пробел или узкий для разделителя
    s = f"{x:,.0f}".replace(",", " ")
    # U+2007 (Figure Space) имеет ширину цифры - используем для отступа слева
    # чтобы визуально выровнять по правому краю в текстовой колонке
    return s.rjust(12, '\u2007')

for col in static_num_cols:
    if col in display_df.columns:
        display_df[col] = display_df[col].apply(fmt_right)

# Определяем нередактируемые колонки (все кроме Корр и Корр±)
disabled_cols = [c for c in edit_df.columns if c not in ['Корр', 'Корр±']]

edited_df = st.data_editor(
    display_df,
    use_container_width=True,
    height=550,
    hide_index=True,
    disabled=disabled_cols,
    column_config={
        "Корр": st.column_config.NumberColumn(
            "Корр",
            help="Абсолютное значение плана. Пустое = нет корр.",
            format="%.0f",
            default=None
        ),
        "Корр±": st.column_config.NumberColumn(
            "Корр±",
            help="Добавка/вычет к плану. Пустое = нет корр.",
            format="%+d",
            default=None
        ),
        # Статические колонки показываем как текст
        "Выр.2024": st.column_config.TextColumn("Выр.2024", width="small"),
        "Выр.2025": st.column_config.TextColumn("Выр.2025", width="small"),
        "Выр.25(Н)": st.column_config.TextColumn("Выр.25(Н)", width="small"),
        "План 2026": st.column_config.TextColumn("План 2026", width="small"),
        "Рекоменд": st.column_config.TextColumn("Рекоменд", width="small"),
        "Расчёт": st.column_config.TextColumn("Расчёт", width="small"),
        "Цель": st.column_config.TextColumn("Цель", width="small"),
        
        "Δ%_25": st.column_config.NumberColumn("Δ%_25", format="%.1f"),
        "Δ%_24": st.column_config.NumberColumn("Δ%_24", format="%.1f"),
        "Сез.Факт": st.column_config.NumberColumn("Сез.Факт", format="%.1f"),
        "Сез.План": st.column_config.NumberColumn("Сез.План", format="%.1f"),
    },
    key="main_data_editor"
)

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
    
    # Текущие значения в редакторе
    corr_val = row.get('Корр')
    delta_val = row.get('Корр±')
    
    has_corr = pd.notna(corr_val) if 'Корр' in edited_df.columns else False
    has_delta = pd.notna(delta_val) if 'Корр±' in edited_df.columns else False
    
    if has_corr or has_delta:
        new_corr = int(corr_val) if has_corr else None
        new_delta = int(delta_val) if has_delta else None
        
        # Проверяем, изменилось ли что-то (сравниваем только значимые поля)
        old_item = corrections_map.get(key)
        old_corr = old_item.get('corr') if old_item else None
        old_delta = old_item.get('delta') if old_item else None
        
        if old_corr != new_corr or old_delta != new_delta:
            new_item = {
                'branch': branch,
                'dept': dept,
                'month': month,
                'corr': new_corr,
                'delta': new_delta
            }
            corrections_map[key] = new_item
            changes_detected = True
    else:
        # Если корректировки нет (пусто), но она БЫЛА в файле -> удаляем (пользователь стер)
        if key in corrections_map:
            del corrections_map[key]
            changes_detected = True

if changes_detected:
    new_corrections_list = list(corrections_map.values())
    save_corrections_local(new_corrections_list)
    st.cache_data.clear()
    st.rerun()

# Статистика корректировок (компактно)
corr_count = (edited_df['Корр'].notna().sum() if 'Корр' in edited_df.columns else 0) + \
             (edited_df['Корр±'].notna().sum() if 'Корр±' in edited_df.columns else 0)
if corr_count > 0:
    st.caption(f"✏️ Корректировок: {corr_count}")
