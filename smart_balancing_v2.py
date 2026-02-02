"""
SMART BALANCING v2.3

ПРАВИЛА РАСПРЕДЕЛЕНИЯ:

1. ФИКСИРОВАННЫЕ ОТДЕЛЫ (не участвуют в балансировке):
   - Ручные корректировки (Корр / Корр_Дельта)
   - Заданные ставки роста (strategic_growth_rates.json / growth_rates.json)
   - Двери и Мебель для кухни — свой алгоритм

2. ЗАЩИЩЁННЫЕ ОТДЕЛЫ (ограниченный диапазон):
   - КРАСКИ, СТРОЙМАТЕРИАЛЫ, 2В: от -3% до +6%
   - ОБОИ, 9А: от 0% до +7%

3. ДРАЙВЕРЫ РОСТА (приоритет на рост):
   - ПЛИТКА, САНТЕХНИКА, ПОКРЫТИЯ НАПОЛЬНЫЕ, МЕБЕЛЬ ДЛЯ ДОМА
   - Минимум +6%, максимум +30%

4. БУФЕРНЫЕ (все остальные):
   - Диапазон: от -10% до +12%
   - Сопутствующие получают БОНУС (формула 2:1)

5. БОНУС ДЛЯ СОПУТСТВУЮЩИХ:
   - На каждые 2% роста стратегических → +1% бонус к полу
   - Максимум +10% бонуса

6. СКОРИНГ:
   - Momentum (тренд 2025/2024): 70%
   - Проникновение (vs целевая доля): 30%
   - Множители: Стратегический ×1.4, Сопутствующий ×0.9

7. СЕЗОННОСТЬ:
   - Индивидуальная для каждого сезонного отдела
   - Влияет на распределение избытка

8. КОРРЕКТИРОВКА ПО ПЛОЩАДИ (гарантированное сокращение):
   - Площадь ↓ ≤50% + тренд ↓ → план ×0.80
   - Площадь ↓ >50% + тренд ↓ → план ×0.50

9. HARD LIMIT:
   - Минимум для всех: 80% от Факт_2025
   - Площадь обходит этот лимит
"""

import pandas as pd
import numpy as np
import json
import os
from typing import Dict, Callable

# === ЗАГРУЗКА ПАРАМЕТРОВ ===
def load_algo_params() -> dict:
    """Загрузить параметры алгоритма из файла"""
    params_file = os.path.join(os.path.dirname(__file__), 'data', 'algo_params.json')
    defaults = {
        'weight_momentum': 70,
        'weight_penetration': 30,
        'inflation_floor': 6,
        'hard_limit': 80,
        'driver_min': 6,
        'driver_max': 30,
        'buffer_min': -10,
        'buffer_max': 12,
        'role_mult_strategic': 1.4,
        'role_mult_accompanying': 0.9,
        'bonus_divisor': 2,
        'bonus_max': 10,
    }
    if os.path.exists(params_file):
        try:
            with open(params_file, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                defaults.update(saved)
        except:
            pass
    return defaults

# Загружаем параметры
ALGO_PARAMS = load_algo_params()

# === НАСТРОЙКИ (из параметров) ===
WEIGHTS = {
    'penetration': ALGO_PARAMS['weight_penetration'] / 100,
    'momentum': ALGO_PARAMS['weight_momentum'] / 100
}

INFLATION_FLOOR = ALGO_PARAMS['inflation_floor'] / 100
HARD_LIMIT = ALGO_PARAMS['hard_limit'] / 100
ROUND_STEP = 10000
SPECIAL_FORMATS = {'Мини Бизнес', 'Микро Бизнес', 'Интернет'}

# Сезонность ПО ОТДЕЛАМ: {паттерн отдела: {месяц: множитель}}
# Множитель > 1 = в сезон получает больше прироста
# Множитель < 1 = не в сезон получает меньше прироста
DEPT_SEASONALITY = {
    '8. Краски': {
        1: 0.5, 2: 0.6, 3: 0.9, 4: 1.3, 5: 1.4, 6: 1.4,
        7: 1.3, 8: 1.2, 9: 1.0, 10: 0.7, 11: 0.6, 12: 0.5
    },
    '10А. Сезонные': {
        1: 0.4, 2: 0.5, 3: 0.8, 4: 1.4, 5: 1.5, 6: 1.5,
        7: 1.4, 8: 1.2, 9: 0.9, 10: 0.6, 11: 0.5, 12: 0.4
    },
    '2. Стройматериалы': {
        1: 0.6, 2: 0.7, 3: 0.9, 4: 1.2, 5: 1.3, 6: 1.3,
        7: 1.2, 8: 1.1, 9: 1.0, 10: 0.8, 11: 0.7, 12: 0.6
    },
    '2В.': {  # Металлопрокат
        1: 0.6, 2: 0.7, 3: 0.9, 4: 1.2, 5: 1.3, 6: 1.3,
        7: 1.2, 8: 1.1, 9: 1.0, 10: 0.8, 11: 0.7, 12: 0.6
    },
    '2Б.': {  # Лесопиломатериалы
        1: 0.5, 2: 0.6, 3: 0.8, 4: 1.3, 5: 1.4, 6: 1.4,
        7: 1.3, 8: 1.2, 9: 1.0, 10: 0.7, 11: 0.6, 12: 0.5
    },
    '7. Инструменты': {
        1: 0.7, 2: 0.7, 3: 0.9, 4: 1.2, 5: 1.2, 6: 1.2,
        7: 1.1, 8: 1.1, 9: 1.0, 10: 0.8, 11: 0.8, 12: 0.7
    },
}

def get_dept_season_mult(dept_name: str, month: int) -> float:
    """Получить сезонный множитель для отдела и месяца"""
    for pattern, season_map in DEPT_SEASONALITY.items():
        if pattern in dept_name:
            return season_map.get(month, 1.0)
    return 1.0  # Несезонные отделы = без множителя

# === КАТЕГОРИИ ОТДЕЛОВ ===
# Защищённые: ограниченный диапазон роста/падения
PROTECTED_DEPTS = {
    '8. Краски': {'min_growth': -0.03, 'max_growth': 0.08},           # -3% до +8%
    '4. Обои': {'min_growth': -0.03, 'max_growth': 0.08},             # -3% до +8%
    '9А. Материалы': {'min_growth': -0.03, 'max_growth': 0.08},       # -3% до +8%
    '2. Стройматериалы': {'min_growth': 0.0, 'max_growth': 0.02},     # ~+1% за год
    '2В. Металлопрокат': {'min_growth': 0.0, 'max_growth': 0.02},     # ~+1% за год
}

# Драйверы: приоритет на рост (минимум +6%)
DRIVER_DEPTS = ['3. Плитка', '1. Сантехника', '5. Покрытия напольные', 'Мебель для дома']

# Фиксированные: свой алгоритм (исключены из балансировки)
FROZEN_DEPTS = ['9. Двери', 'Мебель для кухни']


def sigmoid(x, k=1, x0=0):
    """Вспомогательная функция S-кривой"""
    return 1 / (1 + np.exp(-k * (x - x0)))


def get_dept_category(dept_name: str) -> str:
    """Определить категорию отдела"""
    for key in PROTECTED_DEPTS:
        if key in dept_name:
            return 'protected'
    for key in DRIVER_DEPTS:
        if key in dept_name:
            return 'driver'
    for key in FROZEN_DEPTS:
        if key in dept_name:
            return 'frozen'
    return 'buffer'


def get_growth_limits(dept_name: str, role: str = None) -> tuple:
    """Получить лимиты роста для отдела"""
    for key, limits in PROTECTED_DEPTS.items():
        if key in dept_name:
            return limits['min_growth'], limits['max_growth']
    # Драйверы
    for key in DRIVER_DEPTS:
        if key in dept_name:
            driver_min = ALGO_PARAMS['driver_min'] / 100
            driver_max = ALGO_PARAMS['driver_max'] / 100
            return driver_min, driver_max
    # Буферные
    buffer_min = ALGO_PARAMS['buffer_min'] / 100
    buffer_max = ALGO_PARAMS['buffer_max'] / 100
    return buffer_min, buffer_max


def get_acc_bonus_growth(strategic_growth: float) -> float:
    """
    Бонус к росту для сопутствующих.
    
    Формула: рост стратегических / divisor
    
    Args:
        strategic_growth: средний рост стратегических отделов (например 0.20 = +20%)
    Returns:
        bonus_growth: бонус к росту для сопутствующих
    """
    divisor = ALGO_PARAMS['bonus_divisor'] / 100  # Переводим в доли (2 -> 0.02)
    bonus_max = ALGO_PARAMS['bonus_max'] / 100
    
    # Бонус = рост стратегических / divisor
    # Если divisor=2, то 20% рост -> 20/2 = 10% бонус
    bonus = strategic_growth / (ALGO_PARAMS['bonus_divisor'])
    
    # Ограничения: минимум 0%, максимум bonus_max
    bonus = max(0.0, min(bonus_max, bonus))
    
    return bonus


def get_area_adjustment(area_2025: float, area_2026: float, momentum: float) -> float:
    """
    Корректировка плана при сокращении площади.
    
    Логика:
    - Если площадь сократилась И тренд падает:
      - Сокращение <= 50% → план = 80% от расчётного
      - Сокращение > 50% → план = 50% от расчётного
    - Иначе: план = 100%
    
    Args:
        area_2025: Площадь 2025 (max за год)
        area_2026: Площадь 2026
        momentum: Тренд выручки (Rev_2025 / Rev_2024)
    
    Returns:
        Множитель плана (0.5, 0.8 или 1.0)
    """
    if area_2025 <= 0 or area_2026 <= 0:
        return 1.0
    
    # Процент сокращения площади
    area_change = (area_2026 - area_2025) / area_2025
    
    # Проверяем условия: площадь сократилась И тренд падает
    if area_change < 0 and momentum < 1.0:
        if area_change <= -0.50:
            # Сокращение больше 50% → план 50%
            return 0.50
        else:
            # Сокращение до 50% → план 80%
            return 0.80
    
    return 1.0


def calculate_score_no_area(group: pd.DataFrame, network_share_map: Dict) -> pd.Series:
    """Рассчитывает Score (без площади)"""
    # 1. МОМЕНТУМ
    prev_rev = group['Rev_2024'].replace(0, 1)
    momentum_raw = np.log1p(group['Rev_2025_Norm'] / prev_rev)
    score_momentum = sigmoid(momentum_raw, k=2, x0=0.7)

    # 2. ПРОНИКНОВЕНИЕ
    total_rev = group['Rev_2025_Norm'].sum()
    if total_rev == 0:
        total_rev = 1
    local_shares = group['Rev_2025_Norm'] / total_rev
    
    fmt = group['Формат'].iloc[0] if 'Формат' in group.columns else 'Средний'
    target_shares = group['Отдел'].apply(lambda x: network_share_map.get((fmt, x), 0.05))
    
    penetration_gap = (target_shares / local_shares).replace([np.inf, -np.inf], 1.0).fillna(1.0)
    score_penetration = sigmoid(penetration_gap, k=2, x0=1.0)

    final_score = (
        score_momentum * WEIGHTS['momentum'] +
        score_penetration * WEIGHTS['penetration']
    )
    
    # БОНУСЫ (из параметров)
    role_multiplier = group['Роль'].map({
        'Стратегический': ALGO_PARAMS['role_mult_strategic'],
        'Сопутствующий': ALGO_PARAMS['role_mult_accompanying']
    }).fillna(1.0)
    
    dept_multiplier = group['Отдел'].apply(
        lambda x: 1.0  # Бонус драйверов отключён
    )

    return final_score * role_multiplier * dept_multiplier


def apply_smart_balancing_v2(
    df: pd.DataFrame,
    has_correction_func: Callable,
    load_strategic_rates_func: Callable,
    load_acc_rates_func: Callable
) -> pd.DataFrame:
    """Применить Smart Balancing v2.3"""
    # Перезагружаем параметры при каждом вызове
    global ALGO_PARAMS, WEIGHTS, INFLATION_FLOOR, HARD_LIMIT
    ALGO_PARAMS = load_algo_params()
    WEIGHTS = {
        'penetration': ALGO_PARAMS['weight_penetration'] / 100,
        'momentum': ALGO_PARAMS['weight_momentum'] / 100
    }
    INFLATION_FLOOR = ALGO_PARAMS['inflation_floor'] / 100
    HARD_LIMIT = ALGO_PARAMS['hard_limit'] / 100
    
    result = df.copy()
    
    # Предрасчёт долей
    if 'Rev_2025_Norm' in result.columns and 'Формат' in result.columns:
        net_stats = result.groupby(['Формат', 'Отдел'])['Rev_2025_Norm'].sum().reset_index()
        fmt_totals = result.groupby(['Формат'])['Rev_2025_Norm'].sum().reset_index().rename(
            columns={'Rev_2025_Norm': 'Total'}
        )
        net_stats = pd.merge(net_stats, fmt_totals, on='Формат')
        net_stats['Share'] = net_stats['Rev_2025_Norm'] / net_stats['Total']
        network_share_map = net_stats.set_index(['Формат', 'Отдел'])['Share'].to_dict()
    else:
        network_share_map = {}
    
    strategic_growth_rates = load_strategic_rates_func()
    acc_growth_rates = load_acc_rates_func()
    
    debug_info = []
    
    for (branch, month), group in result.groupby(['Филиал', 'Месяц']):
        idx = group.index
        
        format_val = group['Формат'].iloc[0] if 'Формат' in group.columns else ''
        if format_val in SPECIAL_FORMATS:
            continue
        
        target = result.loc[idx, 'План'].iloc[0]
        if pd.isna(target) or target <= 0:
            continue
        target = int(round(target))

        # ФИКСИРОВАННЫЕ
        group_slice = result.loc[idx]
        is_manual = has_correction_func(group_slice)
        
        has_rate = pd.Series(False, index=idx)
        for i in idx:
            d = result.loc[i, 'Отдел']
            b = result.loc[i, 'Филиал']
            if strategic_growth_rates.get((b, d)) is not None:
                has_rate[i] = True
            if acc_growth_rates.get((b, d), 0) != 0:
                has_rate[i] = True
        
        is_frozen = group_slice['Отдел'].apply(lambda x: get_dept_category(x) == 'frozen')
        
        # Frozen отделы без плана (=0) получают Rev × INFLATION
        frozen_idx = idx[is_frozen]
        for i in frozen_idx:
            if result.loc[i, 'План_Расч'] <= 0:
                result.loc[i, 'План_Расч'] = result.loc[i, 'Rev_2025_Norm'] * (1 + INFLATION_FLOOR)
        
        fixed_mask = is_manual | has_rate | is_frozen
        fixed_sum = result.loc[idx[fixed_mask], 'План_Расч'].sum()
        
        # АКТИВНЫЕ
        active_mask = (~fixed_mask) & (result.loc[idx, 'Rev_2025_Norm'] > 0)
        active_idx = idx[active_mask]
        
        residual_target = target - fixed_sum
        
        if len(active_idx) == 0 or residual_target <= 0:
            if len(active_idx) > 0:
                result.loc[active_idx, 'План_Расч'] = 0
            continue

        # ПОЛ с учётом категорий
        rev_25 = result.loc[active_idx, 'Rev_2025_Norm']
        rev_24 = result.loc[active_idx, 'Rev_2024'].replace(0, 1)
        mom = rev_25 / rev_24
        
        # Сначала вычисляем рост СТРАТЕГИЧЕСКИХ в этом филиале/месяце
        strategic_mask_init = result.loc[active_idx, 'Роль'] == 'Стратегический'
        strategic_idx_init = active_idx[strategic_mask_init]
        
        if len(strategic_idx_init) > 0:
            strat_rev_25 = result.loc[strategic_idx_init, 'Rev_2025_Norm'].sum()
            strat_rev_24 = result.loc[strategic_idx_init, 'Rev_2024'].sum()
            # Рост стратегических = средний momentum
            strategic_growth = (strat_rev_25 / strat_rev_24 - 1) if strat_rev_24 > 0 else 0.06
            # Добавляем плановый рост (target vs fact)
            strat_share = strat_rev_25 / result.loc[idx, 'Rev_2025_Norm'].sum() if result.loc[idx, 'Rev_2025_Norm'].sum() > 0 else 0.5
            strat_target_share = target * strat_share
            strategic_growth_plan = (strat_target_share / strat_rev_25 - 1) if strat_rev_25 > 0 else 0.06
        else:
            strategic_growth_plan = 0.06
        
        # Рассчитываем бонус для сопутствующих (формула 3:1)
        acc_bonus = get_acc_bonus_growth(strategic_growth_plan)
        
        # === УМНОЕ ДИНАМИЧЕСКОЕ РАСПРЕДЕЛЕНИЕ ===
        # Принцип:
        # 1. Сопутствующие гарантированно получают инфляцию (6%)
        # 2. Стратегические растут с учётом penetration gap (потенциал)
        # 3. Избыток сначала покрывает сопутствующих, потом стратегических
        
        # Вычисляем penetration gap для каждого отдела
        total_rev = result.loc[active_idx, 'Rev_2025_Norm'].sum()
        local_shares = result.loc[active_idx, 'Rev_2025_Norm'] / total_rev if total_rev > 0 else pd.Series(1/len(active_idx), index=active_idx)
        
        fmt = result.loc[active_idx, 'Формат'].iloc[0] if 'Формат' in result.columns else 'Средний'
        target_shares = result.loc[active_idx, 'Отдел'].apply(lambda x: network_share_map.get((fmt, x), 0.05))
        
        # Penetration gap: насколько отдел отстаёт от целевой доли
        penetration_gap_raw = (target_shares / local_shares).replace([np.inf, -np.inf], 1.0).fillna(1.0)
        # Плавная "резинка" через сигмоиду вместо жёсткого clip
        # Центрируем на 1.0, сжимаем диапазон плавно
        penetration_gap = 0.5 + sigmoid(penetration_gap_raw - 1.0, k=2, x0=0) * 1.5
        
        # ШАГ 1: Гарантированный пол
        floor_multipliers = pd.Series(1.0, index=active_idx)
        
        for i in active_idx:
            dept = result.loc[i, 'Отдел']
            role = result.loc[i, 'Роль'] if 'Роль' in result.columns else None
            category = get_dept_category(dept)
            
            if category == 'protected':
                # Защищённые - свои лимиты
                min_g, _ = get_growth_limits(dept)
                floor_multipliers[i] = 1 + min_g
            elif role == 'Стратегический':
                # Стратегические - инфляция + бонус (выше пол)
                floor_multipliers[i] = 1 + INFLATION_FLOOR + 0.04  # +10% vs 6% для сопутствующих
            elif category == 'driver':
                # Драйверы - инфляция + бонус
                floor_multipliers[i] = 1 + INFLATION_FLOOR + 0.04
            else:
                # Сопутствующие - только инфляция (ниже пол)
                floor_multipliers[i] = 1 + INFLATION_FLOOR
        
        base_floor = rev_25 * floor_multipliers
        total_floor = base_floor.sum()
        
        # ШАГ 2: Вычисляем доступный избыток
        delta = residual_target - total_floor
        scores = calculate_score_no_area(result.loc[active_idx], network_share_map)
        
        # ШАГ 3: УМНОЕ РАСПРЕДЕЛЕНИЕ ИЗБЫТКА
        if delta > 0:
            # Есть избыток - распределяем с учётом penetration
            # Стратегические получают больше если penetration gap высокий
            
            season_boost = pd.Series(1.0, index=active_idx)
            for i in active_idx:
                dept = result.loc[i, 'Отдел']
                season_boost[i] = get_dept_season_mult(dept, int(month))
            
            # Веса: для стратегических - учитываем penetration gap
            # для сопутствующих - только Rev (они уже получили свой пол)
            weights = pd.Series(0.0, index=active_idx)
            
            for i in active_idx:
                role = result.loc[i, 'Роль'] if 'Роль' in result.columns else None
                rev = result.loc[i, 'Rev_2025_Norm']
                
                if role == 'Стратегический':
                    # Стратегические: Rev × Score × Penetration × Season
                    # Чем больше gap (отстаёт от целевой доли) - тем больше получает
                    weights[i] = rev * scores[i] * penetration_gap[i] * season_boost[i]
                else:
                    # Сопутствующие: минимальный вес (уже получили инфляцию)
                    weights[i] = rev * 0.15 * season_boost[i]  # 15% от базового - больше разрыв
            
            if weights.sum() > 0:
                share = weights / weights.sum()
                final_plans = base_floor + (delta * share)
            else:
                final_plans = base_floor
                
        else:
            # Дефицит — режем, но стратегические защищены
            max_score = scores.max() + 0.1
            weakness = max_score - scores
            
            # Защита по категориям и ролям
            for i in active_idx:
                dept = result.loc[i, 'Отдел']
                role = result.loc[i, 'Роль'] if 'Роль' in result.columns else None
                category = get_dept_category(dept)
                
                if category in ['protected', 'driver']:
                    weakness[i] = 0.05  # Почти не режем
                elif role == 'Стратегический':
                    weakness[i] = weakness[i] * 0.3  # Стратегические режутся в 3 раза меньше
                # Сопутствующие - полная слабость (режутся больше)
            
            cut_weights = result.loc[active_idx, 'Rev_2025_Norm'] * (weakness ** 2)
            
            if cut_weights.sum() > 0:
                share = cut_weights / cut_weights.sum()
                final_plans = base_floor + (delta * share)
            else:
                ratio = residual_target / total_floor if total_floor > 0 else 0
                final_plans = base_floor * ratio

        # ПРИМЕНЕНИЕ ЛИМИТОВ с учётом роста СТРАТЕГИЧЕСКИХ
        # Вычисляем рост стратегических отделов
        strategic_mask = result.loc[active_idx, 'Роль'] == 'Стратегический'
        strategic_idx = active_idx[strategic_mask]
        
        if len(strategic_idx) > 0:
            strategic_rev_25 = result.loc[strategic_idx, 'Rev_2025_Norm'].sum()
            strategic_plan = final_plans[strategic_idx].sum()
            strategic_growth = (strategic_plan / strategic_rev_25 - 1) if strategic_rev_25 > 0 else 0
        else:
            strategic_growth = 0.06  # Дефолт = инфляция
        
        for i in active_idx:
            dept = result.loc[i, 'Отдел']
            role = result.loc[i, 'Роль'] if 'Роль' in result.columns else None
            rev = rev_25[i]  # Rev_2025_Norm
            
            # Базовые лимиты по категории
            min_g, max_g = get_growth_limits(dept)
            
            # Для сопутствующих буферных — бонус к росту (формула 5:1)
            if role == 'Сопутствующий' and get_dept_category(dept) == 'buffer':
                bonus = get_acc_bonus_growth(strategic_growth)
                # Добавляем бонус к максимальному росту
                max_g = max_g + bonus
            
            min_plan = rev * (1 + min_g)
            max_plan = rev * (1 + max_g)
            
            # Плавное сжатие вместо жёсткого clip (резинка)
            current = final_plans[i]
            if current < min_plan:
                # Плавно притягиваем к min
                t = (min_plan - current) / (min_plan * 0.5 + 1)  # Нормализуем
                soft_factor = sigmoid(t, k=3, x0=0.5)
                final_plans[i] = current + (min_plan - current) * soft_factor
            elif current > max_plan:
                # Плавно притягиваем к max
                t = (current - max_plan) / (max_plan * 0.5 + 1)
                soft_factor = sigmoid(t, k=3, x0=0.5)
                final_plans[i] = current - (current - max_plan) * soft_factor
        
        # УМНЫЙ ПЕРЕНОС ИЗБЫТКА: от стратегических к сопутствующим
        # Если стратегический растёт > overflow_cap, излишек переносим на сопутствующих
        strategic_cap = ALGO_PARAMS.get('overflow_cap', 15) / 100  # Порог переноса
        overflow_pool = 0.0
        
        for i in active_idx:
            role = result.loc[i, 'Роль'] if 'Роль' in result.columns else None
            if role == 'Стратегический':
                rev = rev_25[i]
                current_growth = (final_plans[i] / rev - 1) if rev > 0 else 0
                
                if current_growth > strategic_cap:
                    # Обрезаем до cap и собираем излишек
                    capped_plan = rev * (1 + strategic_cap)
                    overflow = final_plans[i] - capped_plan
                    overflow_pool += overflow
                    final_plans[i] = capped_plan
        
        # Распределяем излишек на сопутствующих
        if overflow_pool > 0:
            acc_idx = [i for i in active_idx 
                      if result.loc[i, 'Роль'] == 'Сопутствующий' 
                      and get_dept_category(result.loc[i, 'Отдел']) == 'buffer']
            
            if acc_idx:
                acc_rev = result.loc[acc_idx, 'Rev_2025_Norm']
                total_acc_rev = acc_rev.sum()
                
                if total_acc_rev > 0:
                    shares = acc_rev / total_acc_rev
                    for i in acc_idx:
                        # Добавляем долю излишка
                        bonus_amount = overflow_pool * shares[i]
                        final_plans[i] += bonus_amount
                        
                        # Но не больше max роста для буфера + бонус
                        buf_max = ALGO_PARAMS['buffer_max'] / 100 + get_acc_bonus_growth(strategic_cap)
                        max_allowed = rev_25[i] * (1 + buf_max)
                        final_plans[i] = min(final_plans[i], max_allowed)
        
        # Hard stop: минимум из параметров (ДО корректировки по площади)
        final_plans = final_plans.clip(lower=result.loc[active_idx, 'Rev_2025_Norm'] * HARD_LIMIT)
        
        # КОРРЕКТИРОВКА ПО ПЛОЩАДИ (гарантированное сокращение, обходит 70% пол)
        # Если площадь сократилась и тренд падает → снижаем план
        if 'Площадь_2025' in result.columns and 'Площадь_2026' in result.columns:
            for i in active_idx:
                area_25 = result.loc[i, 'Площадь_2025'] if pd.notna(result.loc[i, 'Площадь_2025']) else 0
                area_26 = result.loc[i, 'Площадь_2026'] if pd.notna(result.loc[i, 'Площадь_2026']) else 0
                momentum_i = mom[i] if i in mom.index else 1.0
                
                area_mult = get_area_adjustment(area_25, area_26, momentum_i)
                if area_mult < 1.0:
                    # Гарантированное сокращение - обходит 70% пол
                    final_plans[i] = final_plans[i] * area_mult

        # ОКРУГЛЕНИЕ
        result.loc[active_idx, 'План_Расч'] = final_plans
        result.loc[active_idx, 'План_Расч'] = (
            result.loc[active_idx, 'План_Расч'] / ROUND_STEP
        ).round(0) * ROUND_STEP
        
        # СХОДИМОСТЬ (100% точность) - распределяем diff пропорционально
        current_total = result.loc[idx, 'План_Расч'].sum()
        diff = target - current_total
        
        if abs(diff) > 0 and len(active_idx) > 0:
            # Распределяем пропорционально нормализованной выручке (Rev_2025_Norm)
            active_rev = result.loc[active_idx, 'Rev_2025_Norm']
            total_rev = active_rev.sum()
            
            if total_rev > 0:
                shares = active_rev / total_rev
                adjustments = diff * shares
                
                # Применяем корректировки с учётом минимума
                for i in active_idx:
                    new_val = result.loc[i, 'План_Расч'] + adjustments[i]
                    min_allowed = result.loc[i, 'Rev_2025_Norm'] * HARD_LIMIT
                    result.loc[i, 'План_Расч'] = max(new_val, min_allowed)
                
                # Финальное округление
                result.loc[active_idx, 'План_Расч'] = (
                    result.loc[active_idx, 'План_Расч'] / ROUND_STEP
                ).round(0) * ROUND_STEP
            
            # Финальная подгонка на самый большой буферный отдел
            final_diff = int(round(target - result.loc[idx, 'План_Расч'].sum()))
            if final_diff != 0:
                buffer_idx = [i for i in active_idx if get_dept_category(result.loc[i, 'Отдел']) == 'buffer']
                if buffer_idx:
                    best = result.loc[buffer_idx, 'План_Расч'].idxmax()
                else:
                    best = result.loc[active_idx, 'План_Расч'].idxmax()
                result.loc[best, 'План_Расч'] += final_diff
        
        debug_info.append({
            'branch': branch,
            'month': int(month),
            'target': target,
            'delta': float(delta),
            'final_sum': float(result.loc[idx, 'План_Расч'].sum())
        })
    
    import json
    with open('/tmp/debug_smart_v2.json', 'w', encoding='utf-8') as f:
        json.dump(debug_info[:20], f, ensure_ascii=False, indent=2)
    
    return result


# === ЭКСПОРТ ПРАВИЛ ДЛЯ UI ===
def get_balancing_rules() -> dict:
    """Получить текущие правила для отображения в UI"""
    return {
        'weights': WEIGHTS,
        'inflation_floor': INFLATION_FLOOR,
        'protected_depts': PROTECTED_DEPTS,
        'driver_depts': DRIVER_DEPTS,
        'frozen_depts': FROZEN_DEPTS,
        'role_multipliers': {
            'Стратегический': 1.4,
            'Сопутствующий': 0.7
        },
        'driver_bonus': 1.2,
        'hard_floor': 0.8  # 80% минимум
    }
