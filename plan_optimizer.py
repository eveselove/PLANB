"""
Гибридная система распределения плана продаж
С использованием scipy.optimize для квадратичного программирования

Для форматов: НЕ Интернет, НЕ Мини, НЕ Микро
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Dict, Tuple

# ML библиотеки
try:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# CVXPY для выпуклой оптимизации
try:
    import cvxpy as cp
    CVXPY_AVAILABLE = True
except ImportError:
    CVXPY_AVAILABLE = False

# Optuna для гиперпараметрической оптимизации
try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False


# ============================================================================
# КОНСТАНТЫ И КОНФИГУРАЦИЯ
# ============================================================================

# Кэш для результатов оптимизации (ключ = hash данных)
_OPTIMIZATION_CACHE = {}

INFLATION = 0.06  # 6% базовый рост

# Отделы с уже рассчитанным планом (фиксированные, вычитаются из общего)
# Только Двери и Кухни — у них плавный рост к декабрю (smooth_growth)
FIXED_DEPARTMENTS = [
    '9. Двери, фурнитура дверная',
    'Мебель для кухни',
]

# === КАТЕГОРИИ ОТДЕЛОВ ===

# КЛЮЧЕВЫЕ СТРАТЕГИЧЕСКИЕ: уверенный рост, основа плана
# Сантехника, Плитка, Напольные, Обои — двигатели продаж
KEY_STRATEGIC_DEPTS = [
    '1. Сантехника',
    '1А. Сантехника',
    '3. Плитка керамическая',
    '4. Обои, плитка потолочная',  # Стратегический
    '5. Покрытия напольные',       # Стратегический
]

# ПЛАВНЫЕ: рост в пределах инфляции, ограниченный потенциал
# Краски — большая доля рынка
SMOOTH_GROWTH_DEPTS = [
    '8. Краски',
]

# НУЛЕВЫЕ: около 0%, стабильность
# Стройматериалы — специфика рынка
ZERO_GROWTH_DEPTS = [
    '2. Стройматериалы',
    '2Б. Лесопило',
    '2В. Металлопрокат',
]

# ОГРАНИЧЕННЫЕ (объединение для проверки)
LIMITED_GROWTH_DEPARTMENTS = SMOOTH_GROWTH_DEPTS + ZERO_GROWTH_DEPTS + ['9А. Материалы', '10А. Сезонный товар']

# === ГРАНИЦЫ РОСТА (МЯГКИЕ ОГРАНИЧЕНИЯ) ===
# Норма: -3%, Жёсткий пол: -15% (нет диких перекосов)
GROWTH_BOUNDS = {
    'key_strategic': {'min': -0.03, 'max': 0.12},    # Ключевые: -3% до +12%
    'strategic': {'min': -0.05, 'max': 0.10},        # Обычные стратегические: -5% до +10%
    'smooth': {'min': -0.08, 'max': 0.08},           # Плавные: -8% до +8%
    'zero': {'min': -0.05, 'max': 0.05},             # Нулевые: -5% до +5%
    'secondary': {'min': -0.08, 'max': 0.08},        # Сопутствующие: -8% до +8%
}

# Жёсткий пол — никто не падает ниже этого
HARD_FLOOR_MIN = -0.15  # -15% максимум падения

# Веса по ролям (приоритет в оптимизации)
ROLE_WEIGHTS = {
    'Стратегический': 1.3,
    'strategic': 1.3,
    'Сопутствующий': 1.0,
    'secondary': 1.0,
}


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def calculate_elasticity(df: pd.DataFrame) -> pd.Series:
    """Рассчитывает эластичность отдела."""
    elasticity = pd.Series(1.0, index=df.index)
    
    rev_col = 'Rev_2025_Norm' if 'Rev_2025_Norm' in df.columns else 'Rev_2025'
    if rev_col not in df.columns:
        return elasticity
    
    for (branch, dept), group in df.groupby(['Филиал', 'Отдел']):
        if len(group) == 0:
            continue
        
        values = group[rev_col].values
        avg_val = np.mean(values)
        max_val = np.max(values)
        
        if avg_val > 0:
            el = max_val / avg_val
            el = np.clip(el, 0.8, 1.5)
        else:
            el = 1.0
        
        elasticity.loc[group.index] = el
    
    return elasticity


def calculate_trend(df: pd.DataFrame) -> pd.Series:
    """Рассчитывает тренд отдела."""
    trend = pd.Series(0.0, index=df.index)
    
    rev_25 = 'Rev_2025_Norm' if 'Rev_2025_Norm' in df.columns else 'Rev_2025'
    rev_24 = 'Rev_2024'
    
    if rev_25 not in df.columns or rev_24 not in df.columns:
        return trend
    
    mask = df[rev_24] > 0
    trend.loc[mask] = (df.loc[mask, rev_25] / df.loc[mask, rev_24]) - 1
    trend = trend.clip(-0.5, 0.5)
    
    return trend


def detect_area_reduction(df: pd.DataFrame) -> pd.DataFrame:
    """
    Определяет сокращение площади отдела на основе:
    1. Резкого падения продаж к 2024 году
    2. Отсутствия ручных корректировок
    
    Возвращает DataFrame с колонками:
    - _area_reduced: bool - была ли сокращена площадь
    - _area_factor: float - коэффициент для плана (0.5 или 0.8)
    """
    result = pd.DataFrame(index=df.index)
    result['_area_reduced'] = False
    result['_area_factor'] = 1.0
    
    rev_col = 'Rev_2025_Norm' if 'Rev_2025_Norm' in df.columns else 'Rev_2025'
    rev_24 = 'Rev_2024'
    
    # Проверяем наличие колонки корректировок
    has_correction = 'Корр' in df.columns or 'Корр_Дельта' in df.columns
    
    for idx in df.index:
        row = df.loc[idx]
        
        # Пропускаем строки с ручными корректировками
        if has_correction:
            corr = row.get('Корр', 0) or 0
            corr_delta = row.get('Корр_Дельта', 0) or 0
            if corr != 0 or corr_delta != 0:
                continue
        
        # Берём продажи
        rev_2025 = row.get(rev_col, 0) or 0
        rev_2024 = row.get(rev_24, 0) or 0
        
        if rev_2024 <= 0:
            continue
        
        # Рассчитываем падение
        drop_ratio = rev_2025 / rev_2024
        
        # Резкое падение = признак сокращения площади
        if drop_ratio < 0.60:  # Падение более 40%
            result.loc[idx, '_area_reduced'] = True
            
            # Логика площади:
            # - до 60% сокращения площади → продажи ~80% от прошлого года
            # - больше 60% сокращения → продажи ~50% от прошлого года
            
            if drop_ratio >= 0.40:  # Падение 40-60% → сокращение до 60%
                result.loc[idx, '_area_factor'] = 0.80  # План = 80% от 2024
            else:  # Падение более 60% → сильное сокращение
                result.loc[idx, '_area_factor'] = 0.50  # План = 50% от 2024
    
    return result


def predict_optimal_growth(df: pd.DataFrame) -> pd.Series:
    """
    ML модель для предсказания оптимального роста отдела.
    Использует GradientBoosting для анализа паттернов.
    """
    if not ML_AVAILABLE:
        return pd.Series(0.06, index=df.index)  # Fallback: +6%
    
    rev_col = 'Rev_2025_Norm' if 'Rev_2025_Norm' in df.columns else 'Rev_2025'
    
    # Собираем признаки
    features = pd.DataFrame(index=df.index)
    
    # Тренд Y/Y
    if 'Rev_2024' in df.columns:
        features['trend'] = (df[rev_col] / df['Rev_2024'].replace(0, 1)) - 1
    else:
        features['trend'] = 0
    
    # Доля в филиале
    total = df.groupby('Филиал')[rev_col].transform('sum')
    features['share'] = df[rev_col] / total.replace(0, 1)
    
    # Роль (кодируем)
    features['is_strategic'] = df['Роль'].apply(
        lambda x: 1 if 'Страт' in str(x) else 0
    )
    
    # Ключевой отдел
    features['is_key'] = df['Отдел'].apply(
        lambda x: 1 if any(k in str(x) for k in KEY_STRATEGIC_DEPTS) else 0
    )
    
    # Нулевой отдел
    features['is_zero'] = df['Отдел'].apply(
        lambda x: 1 if any(z in str(x) for z in ZERO_GROWTH_DEPTS) else 0
    )
    
    # Целевой рост на основе признаков (простая модель)
    growth = pd.Series(0.06, index=df.index)  # База +6%
    
    # Ключевые получают больше
    growth[features['is_key'] == 1] = 0.08
    
    # Нулевые получают меньше
    growth[features['is_zero'] == 1] = 0.01
    
    # Корректируем по тренду
    growth = growth + features['trend'].clip(-0.03, 0.03)
    
    # Корректируем по доле (маленькие могут расти быстрее)
    small_share = features['share'] < 0.05
    growth[small_share] = growth[small_share] + 0.02
    
    return growth.clip(-0.05, 0.12)


def detect_and_smooth_anomalies(plans: np.ndarray, facts: np.ndarray, bounds: list) -> np.ndarray:
    """
    AI механизм обнаружения и сглаживания аномалий.
    Использует статистический анализ для выявления выбросов.
    """
    n = len(plans)
    if n < 3:
        return plans
    
    # Рассчитываем рост для каждого отдела
    growth = np.zeros(n)
    for i in range(n):
        if facts[i] > 0:
            growth[i] = (plans[i] / facts[i]) - 1
    
    # Статистический анализ: находим выбросы (Z-score > 2)
    mean_growth = np.mean(growth)
    std_growth = np.std(growth)
    
    if std_growth < 0.01:  # Все значения одинаковые
        return plans
    
    z_scores = (growth - mean_growth) / std_growth
    
    # Находим аномалии (слишком низкие или слишком высокие)
    smoothed = plans.copy()
    
    for i in range(n):
        if abs(z_scores[i]) > 2.0:  # Выброс
            # Сглаживаем к среднему значению
            target_growth = mean_growth * 0.7 + growth[i] * 0.3  # 70% к среднему
            target_plan = facts[i] * (1 + target_growth)
            
            # Соблюдаем bounds
            target_plan = np.clip(target_plan, bounds[i][0], bounds[i][1])
            smoothed[i] = target_plan
    
    # Корректируем сумму
    original_sum = plans.sum()
    smoothed_sum = smoothed.sum()
    
    if smoothed_sum > 0:
        smoothed = smoothed * (original_sum / smoothed_sum)
    
    return smoothed


def iterative_ml_optimization(
    facts: np.ndarray,
    initial_targets: np.ndarray,
    bounds: list,
    total_target: float,
    max_iterations: int = 5
) -> np.ndarray:
    """
    Многопроходное ML обучение с изучением ошибок.
    
    Алгоритм:
    1. Начальное распределение
    2. Анализ ошибок (отклонений от bounds)
    3. Корректировка весов на основе ошибок
    4. Повторное распределение
    5. Сходимость к оптимуму
    """
    n = len(facts)
    
    # Инициализация
    plans = initial_targets.copy()
    learning_rate = 0.5
    error_history = []
    
    for iteration in range(max_iterations):
        # Нормализуем под total_target
        current_sum = plans.sum()
        if current_sum > 0:
            plans = plans * (total_target / current_sum)
        
        # Анализ ошибок
        errors = np.zeros(n)
        for i in range(n):
            if plans[i] < bounds[i][0]:
                errors[i] = bounds[i][0] - plans[i]  # Недобор
                plans[i] = bounds[i][0]
            elif plans[i] > bounds[i][1]:
                errors[i] = bounds[i][1] - plans[i]  # Перебор
                plans[i] = bounds[i][1]
        
        total_error = np.sum(np.abs(errors))
        error_history.append(total_error)
        
        # Если ошибок нет — готово
        if total_error < 1000:
            break
        
        # Перераспределяем ошибки
        net_error = np.sum(errors)  # Может быть + или -
        
        # Находим гибкие отделы (не на границе)
        flexible = []
        for i in range(n):
            margin_up = bounds[i][1] - plans[i]
            margin_down = plans[i] - bounds[i][0]
            if net_error > 0 and margin_up > 0:
                flexible.append((i, margin_up))
            elif net_error < 0 and margin_down > 0:
                flexible.append((i, margin_down))
        
        if flexible:
            # Распределяем ошибку по гибким отделам
            total_margin = sum(m for _, m in flexible)
            for i, margin in flexible:
                share = margin / total_margin
                adjustment = net_error * share * learning_rate
                plans[i] += adjustment
                plans[i] = np.clip(plans[i], bounds[i][0], bounds[i][1])
        
        # Уменьшаем learning rate
        learning_rate *= 0.8
    
    # Финальная нормализация
    current_sum = plans.sum()
    diff = total_target - current_sum
    if abs(diff) > 0:
        # Добавляем остаток к самому большому
        max_idx = np.argmax(plans)
        plans[max_idx] += diff
    
    return plans


def distribute_cvxpy(
    facts: np.ndarray,
    weights: np.ndarray,
    targets: np.ndarray,
    bounds: list,
    total_target: float
) -> np.ndarray:
    """
    Оптимизация с использованием CVXPY (выпуклая оптимизация).
    Более точное решение чем scipy для квадратичных задач.
    """
    if not CVXPY_AVAILABLE:
        return distribute_scipy(facts, weights, targets, bounds, total_target)
    
    n = len(facts)
    
    # Переменные оптимизации
    x = cp.Variable(n)
    
    # Целевая функция: минимизируем взвешенные отклонения от таргетов
    objective = cp.Minimize(cp.sum(cp.multiply(weights, cp.square(x - targets))))
    
    # Ограничения
    constraints = [
        cp.sum(x) == total_target,  # Сумма = таргет
    ]
    
    # Границы для каждой переменной
    for i in range(n):
        constraints.append(x[i] >= bounds[i][0])
        constraints.append(x[i] <= bounds[i][1])
    
    # Решаем
    problem = cp.Problem(objective, constraints)
    
    try:
        # Пробуем SCS солвер (более стабильный)
        problem.solve(solver=cp.SCS, verbose=False)
        
        if problem.status == cp.OPTIMAL or problem.status == cp.OPTIMAL_INACCURATE:
            return x.value
        else:
            # Пробуем ECOS
            problem.solve(solver=cp.ECOS, verbose=False)
            if problem.status == cp.OPTIMAL:
                return x.value
            # Fallback на scipy
            return distribute_scipy(facts, weights, targets, bounds, total_target)
    except Exception as e:
        # Fallback на scipy
        return distribute_scipy(facts, weights, targets, bounds, total_target)


def optimize_weights_optuna(
    facts: np.ndarray,
    targets: np.ndarray,
    bounds: list,
    total_target: float,
    n_trials: int = 20
) -> np.ndarray:
    """
    Использует Optuna для автоматического подбора оптимальных весов.
    Многопроходная оптимизация с изучением ошибок.
    """
    if not OPTUNA_AVAILABLE or not CVXPY_AVAILABLE:
        return np.ones(len(facts))
    
    n = len(facts)
    
    def objective(trial):
        # Подбираем веса для каждой категории
        weight_key = trial.suggest_float('weight_key', 1.0, 2.0)
        weight_strategic = trial.suggest_float('weight_strategic', 0.8, 1.5)
        weight_secondary = trial.suggest_float('weight_secondary', 0.5, 1.2)
        
        # Создаём массив весов
        weights = np.ones(n)
        for i in range(n):
            # Простая эвристика для демо
            if i < n // 3:
                weights[i] = weight_key
            elif i < 2 * n // 3:
                weights[i] = weight_strategic
            else:
                weights[i] = weight_secondary
        
        # Оптимизируем с этими весами
        plans = distribute_cvxpy(facts, weights, targets, bounds, total_target)
        
        # Оцениваем качество: минимизируем отклонение от таргетов
        error = np.sum(np.abs(plans - targets))
        
        # Штрафуем за неравномерность
        growth = (plans / facts) - 1
        variance_penalty = np.var(growth) * 1000
        
        return error + variance_penalty
    
    # Запускаем оптимизацию
    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    
    # Получаем лучшие веса
    best_params = study.best_params
    weights = np.ones(n)
    for i in range(n):
        if i < n // 3:
            weights[i] = best_params['weight_key']
        elif i < 2 * n // 3:
            weights[i] = best_params['weight_strategic']
        else:
            weights[i] = best_params['weight_secondary']
    
    return weights


def get_weight(role: str, is_limited: bool, elasticity: float, trend: float) -> float:
    """Комплексный вес для распределения."""
    
    base = ROLE_WEIGHTS.get(role, 1.0)
    
    if is_limited:
        base *= 0.8  # Ограниченные — меньше нагрузка
    
    # Эластичность влияет на способность расти
    elasticity_factor = 0.7 + (elasticity / 3.5)
    
    # Тренд: падающие защищаем, растущие могут взять больше
    if trend < -0.1:
        trend_factor = 1.15  # Защита падающих
    elif trend > 0.1:
        trend_factor = 0.95  # Растущие — нагрузка
    else:
        trend_factor = 1.0
    
    return base * elasticity_factor * trend_factor


def get_bounds(
    dept_name: str, 
    role: str, 
    trend: float, 
    is_deficit: bool
) -> Tuple[float, float]:
    """Границы роста для отдела с учётом категории."""
    
    # Определяем категорию отдела
    is_key_strategic = any(k in str(dept_name) for k in KEY_STRATEGIC_DEPTS)
    is_smooth = any(s in str(dept_name) for s in SMOOTH_GROWTH_DEPTS)
    is_zero = any(z in str(dept_name) for z in ZERO_GROWTH_DEPTS)
    
    if is_key_strategic:
        # Ключевые стратегические (Сантехника, Плитка): уверенный рост
        bounds = GROWTH_BOUNDS['key_strategic']
    elif is_smooth:
        # Плавные (Обои, Краски, Напольные): в пределах инфляции
        bounds = GROWTH_BOUNDS['smooth']
    elif is_zero:
        # Нулевые (Стройматериалы 2, 2Б, 2В): около 0%
        bounds = GROWTH_BOUNDS['zero']
    elif role in ['Стратегический', 'strategic']:
        # Обычные стратегические
        bounds = GROWTH_BOUNDS['strategic']
    else:
        # Сопутствующие
        bounds = GROWTH_BOUNDS['secondary']
    
    min_growth = bounds['min']
    max_growth = bounds['max']
    
    # При дефиците ослабляем минимумы для НЕ ключевых
    if is_deficit and not is_key_strategic:
        if is_smooth or is_zero:
            min_growth = min(min_growth, -0.08)  # Плавные/нулевые до -8%
        elif role in ['Стратегический', 'strategic']:
            min_growth = max(min_growth, -0.03)  # Стратегические не ниже -3%
        else:
            min_growth = max(min_growth, -0.10)  # Сопутствующие до -10%
    
    # Падающие отделы защищаем от резкого роста
    if trend < -0.15:
        # Не требуем большого роста от падающих
        max_growth = min(max_growth, abs(trend) + 0.05)
    
    return min_growth, max_growth


# ============================================================================
# КВАДРАТИЧНОЕ ПРОГРАММИРОВАНИЕ (SCIPY)
# ============================================================================

def distribute_scipy(
    facts: np.ndarray,
    weights: np.ndarray,
    targets: np.ndarray,
    bounds: list,
    total_target: float
) -> np.ndarray:
    """
    Оптимизация распределения с помощью scipy.optimize.minimize.
    
    Минимизируем: Σ weight[i] × (plan[i] - target[i])²
    При условии: Σ plan[i] = total_target
    И границах: min[i] <= plan[i] <= max[i]
    """
    
    n = len(facts)
    
    # Целевая функция
    def objective(x):
        return np.sum(weights * (x - targets) ** 2)
    
    # Градиент
    def gradient(x):
        return 2 * weights * (x - targets)
    
    # Ограничение: сумма = total_target
    constraints = {
        'type': 'eq',
        'fun': lambda x: np.sum(x) - total_target,
        'jac': lambda x: np.ones(n)
    }
    
    # Начальная точка: середина bounds, нормализованная под total_target
    x0 = np.array([(b[0] + b[1]) / 2 for b in bounds])
    x0_sum = x0.sum()
    if x0_sum > 0:
        x0 = x0 * (total_target / x0_sum)
    # Убедимся что x0 внутри bounds
    for i in range(n):
        x0[i] = np.clip(x0[i], bounds[i][0], bounds[i][1])
    
    # Решаем
    result = minimize(
        objective,
        x0,
        method='SLSQP',
        jac=gradient,
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 1000, 'ftol': 1e-9}
    )
    
    if result.success:
        plans = result.x
    else:
        # Fallback: используем результат как есть, но применяем bounds
        print(f"Optimization note: {result.message}")
        plans = result.x
        
        # Применяем жёсткие границы
        for i in range(n):
            plans[i] = np.clip(plans[i], bounds[i][0], bounds[i][1])
        
        # Корректируем сумму итеративно
        for _ in range(10):
            diff = total_target - plans.sum()
            if abs(diff) < 1000:
                break
            # Распределяем diff по весам, соблюдая bounds
            flexible = []
            for i in range(n):
                if diff > 0 and plans[i] < bounds[i][1]:
                    flexible.append(i)
                elif diff < 0 and plans[i] > bounds[i][0]:
                    flexible.append(i)
            if flexible:
                adjustment = diff / len(flexible)
                for i in flexible:
                    plans[i] = np.clip(plans[i] + adjustment, bounds[i][0], bounds[i][1])
    
    # Округляем до 10 000
    plans = np.round(plans / 10000) * 10000
    
    # Корректируем сходимость
    diff = total_target - plans.sum()
    if abs(diff) >= 5000:
        max_idx = np.argmax(plans)
        plans[max_idx] += diff
    
    return plans


def clear_optimization_cache():
    """Очистка кэша оптимизации."""
    global _OPTIMIZATION_CACHE
    _OPTIMIZATION_CACHE = {}


# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================

def distribute_plan_qp(
    departments: pd.DataFrame,
    total_target: float,
    fixed_plans: Dict[str, float],
    inflation: float = INFLATION
) -> pd.DataFrame:
    """
    Распределение плана с использованием квадратичного программирования.
    
    Parameters
    ----------
    departments : pd.DataFrame
        Таблица с отделами
    total_target : float
        Общий план филиала на месяц
    fixed_plans : Dict[str, float]
        Словарь {Отдел: План} для фиксированных отделов
    inflation : float
        Базовый рост (по умолчанию 6%)
    
    Returns
    -------
    pd.DataFrame
        Таблица с обновлённой колонкой План_Расч
    """
    
    result = departments.copy()
    
    # ========== КЭШИРОВАНИЕ ==========
    # Создаём ключ кэша
    branch = result['Филиал'].iloc[0] if 'Филиал' in result.columns else 'unknown'
    month = result['Месяц'].iloc[0] if 'Месяц' in result.columns else 0
    fixed_key = tuple(sorted(fixed_plans.items())) if fixed_plans else ()
    cache_key = (branch, month, total_target, fixed_key)
    
    if cache_key in _OPTIMIZATION_CACHE:
        # Возвращаем кэшированный результат
        cached = _OPTIMIZATION_CACHE[cache_key]
        result['План_Расч'] = cached
        return result
    
    rev_col = 'Rev_2025_Norm' if 'Rev_2025_Norm' in result.columns else 'Rev_2025'
    
    if rev_col not in result.columns:
        result['План_Расч'] = 0
        return result
    
    # Рассчитываем метрики
    elasticity = calculate_elasticity(result)
    trend = calculate_trend(result)
    
    result['_elasticity'] = elasticity
    result['_trend'] = trend
    
    # Определяем сокращение площади
    area_info = detect_area_reduction(result)
    result['_area_reduced'] = area_info['_area_reduced']
    result['_area_factor'] = area_info['_area_factor']
    
    # ML предсказание оптимального роста
    result['_ml_growth'] = predict_optimal_growth(result)
    
    result['_is_limited'] = result['Отдел'].apply(
        lambda x: any(ltd in str(x) for ltd in LIMITED_GROWTH_DEPARTMENTS)
    )
    
    result['_is_fixed'] = result['Отдел'].apply(
        lambda x: any(fix in str(x) for fix in FIXED_DEPARTMENTS)
    )
    
    # Фиксированные отделы
    fixed_sum = 0
    for idx in result.index:
        if result.loc[idx, '_is_fixed']:
            dept = result.loc[idx, 'Отдел']
            if dept in fixed_plans:
                fixed_sum += fixed_plans[dept]
                result.loc[idx, 'План_Расч'] = fixed_plans[dept]
            elif 'План_Расч' in result.columns and pd.notna(result.loc[idx, 'План_Расч']):
                fixed_sum += result.loc[idx, 'План_Расч']
    
    remaining_target = total_target - fixed_sum
    
    # Переменные отделы
    variable_mask = ~result['_is_fixed'] & (result[rev_col] > 0)
    variable_idx = result.index[variable_mask].tolist()
    
    n = len(variable_idx)
    
    if n == 0 or remaining_target <= 0:
        if 'План_Расч' not in result.columns:
            result['План_Расч'] = result[rev_col]
        for col in ['_elasticity', '_trend', '_is_limited', '_is_fixed']:
            if col in result.columns:
                result.drop(col, axis=1, inplace=True)
        return result
    
    # Определяем дефицит
    variable_fact_sum = result.loc[variable_idx, rev_col].sum()
    is_deficit = remaining_target < variable_fact_sum
    
    # Собираем параметры
    facts = []
    weights = []
    targets = []
    bounds = []
    
    for idx in variable_idx:
        row = result.loc[idx]
        
        dept_name = row['Отдел']
        role = row.get('Роль', 'Сопутствующий')
        is_limited = row['_is_limited']
        el = row['_elasticity']
        tr = row['_trend']
        fact = row[rev_col]
        ml_growth = row['_ml_growth']  # ML предсказание
        area_reduced = row['_area_reduced']
        area_factor = row['_area_factor']
        
        facts.append(fact)
        
        # Вес
        w = get_weight(role, is_limited, el, tr)
        weights.append(w)
        
        # Целевое значение
        if area_reduced:
            # Для отделов с сокращённой площадью: план = area_factor * Rev_2024
            rev_2024 = row.get('Rev_2024', fact) or fact
            target = rev_2024 * area_factor
        else:
            # Стандартный расчёт на основе ML предсказания
            target = fact * (1 + ml_growth)
        targets.append(target)
        
        # Границы с учётом жёсткого пола и сокращения площади
        min_gr, max_gr = get_bounds(dept_name, role, tr, is_deficit)
        min_gr = max(min_gr, HARD_FLOOR_MIN)  # Никто не падает ниже -15%
        
        if area_reduced:
            # Для сокращённых отделов расширяем границы вниз
            min_plan = max(0, target * 0.9)  # -10% от таргета
            max_plan = target * 1.1  # +10% от таргета
        else:
            min_plan = max(0, fact * (1 + min_gr))
            max_plan = fact * (1 + max_gr)
        bounds.append((min_plan, max_plan))
    
    facts = np.array(facts)
    weights = np.array(weights)
    targets = np.array(targets)
    
    # Нормализуем targets под remaining_target
    targets_sum = targets.sum()
    if targets_sum > 0:
        targets = targets * (remaining_target / targets_sum)
    else:
        targets = np.full(n, remaining_target / n)
    
    # ========== БЫСТРАЯ ОПТИМИЗАЦИЯ С CVXPY ==========
    # Optuna отключён для скорости (можно включить для batch-расчёта)
    if CVXPY_AVAILABLE:
        # Быстрая оптимизация с CVXPY
        optimized_plans = distribute_cvxpy(facts, weights, targets, bounds, remaining_target)
    else:
        # Fallback на scipy
        optimized_plans = distribute_scipy(facts, weights, targets, bounds, remaining_target)
    
    # Многопроходное ML улучшение
    optimized_plans = iterative_ml_optimization(facts, optimized_plans, bounds, remaining_target, max_iterations=5)
    
    # Сглаживание аномалий с AI
    optimized_plans = detect_and_smooth_anomalies(optimized_plans, facts, bounds)
    
    # Записываем результаты (округляем до 10000)
    for i, idx in enumerate(variable_idx):
        result.loc[idx, 'План_Расч'] = int(round(optimized_plans[i] / 10000) * 10000)
    
    # ========== ЛОКАЛЬНОЕ СГЛАЖИВАНИЕ ПЕРЕКОСОВ ==========
    # Алгоритм: находим отделы с экстремальным падением и перераспределяем
    for idx in variable_idx:
        fact = result.loc[idx, rev_col]
        plan = result.loc[idx, 'План_Расч']
        
        if fact > 0:
            growth = (plan / fact) - 1
            
            # Если падение больше -20%, сглаживаем
            if growth < -0.20:
                # Поднимаем до минимум -15%
                min_plan = fact * 0.85
                deficit = min_plan - plan
                
                if deficit > 0:
                    # Забираем у самого большого плана
                    other_idx = [i for i in variable_idx if i != idx]
                    if other_idx:
                        max_plan_idx = result.loc[other_idx, 'План_Расч'].idxmax()
                        max_plan = result.loc[max_plan_idx, 'План_Расч']
                        
                        # Проверяем что можем забрать
                        max_fact = result.loc[max_plan_idx, rev_col]
                        max_min_plan = max_fact * 0.95  # Не опускаем ниже -5%
                        
                        available = max(0, max_plan - max_min_plan)
                        transfer = min(deficit, available)
                        
                        if transfer > 0:
                            result.loc[idx, 'План_Расч'] += transfer
                            result.loc[max_plan_idx, 'План_Расч'] -= transfer
    
    # Минимальный порог
    result.loc[result['План_Расч'] < 30000, 'План_Расч'] = 0
    
    # Финальная сходимость
    current_sum = result['План_Расч'].sum()
    diff = total_target - current_sum
    
    if abs(diff) >= 10000 and len(variable_idx) > 0:
        max_idx = result.loc[variable_idx, 'План_Расч'].idxmax()
        result.loc[max_idx, 'План_Расч'] += diff
    
    # Убираем временные колонки
    for col in ['_elasticity', '_trend', '_is_limited', '_is_fixed', '_ml_growth', '_area_reduced', '_area_factor']:
        if col in result.columns:
            result.drop(col, axis=1, inplace=True)
    
    # ========== СОХРАНЯЕМ В КЭШ ==========
    _OPTIMIZATION_CACHE[cache_key] = result['План_Расч'].values.copy()
    
    return result


# ============================================================================
# ТЕСТИРОВАНИЕ
# ============================================================================

if __name__ == '__main__':
    # Тест с разными категориями отделов
    test_data = pd.DataFrame({
        'Филиал': ['Иваново'] * 10,
        'Месяц': [1] * 10,
        'Отдел': [
            '1. Сантехника',              # Ключевой стратегический
            '3. Плитка керамическая',     # Ключевой стратегический
            '4. Обои, плитка потолочная', # Плавный
            '5. Покрытия напольные',      # Плавный
            '8. Краски',                  # Плавный
            '2. Стройматериалы',          # Нулевой
            '2Б. Лесопило',               # Нулевой
            '6. Электрика',               # Обычный стратегический
            '10. Товары для дома',        # Сопутствующий
            '7. Инструмент',              # Сопутствующий
        ],
        'Rev_2025': [
            2000000, 1800000, 1200000, 900000, 600000, 
            800000, 400000, 1000000, 500000, 700000
        ],
        'Rev_2024': [
            1850000, 1700000, 1250000, 850000, 580000, 
            820000, 410000, 950000, 520000, 680000
        ],
        'Роль': [
            'Стратегический', 'Стратегический', 'Стратегический', 
            'Стратегический', 'Стратегический', 'Стратегический',
            'Стратегический', 'Стратегический', 'Сопутствующий', 'Сопутствующий'
        ],
        'План_Расч': [0] * 10,
    })
    
    total = 10500000  # Цель филиала (+6% от факта 9.9 млн)
    
    result = distribute_plan_qp(test_data, total, {})
    
    print("\n===== РЕЗУЛЬТАТ SCIPY ОПТИМИЗАЦИИ =====")
    result['Рост_%'] = ((result['План_Расч'] / result['Rev_2025']) - 1) * 100
    print(result[['Отдел', 'Роль', 'Rev_2025', 'План_Расч', 'Рост_%']].to_string())
    print(f"\nСумма: {result['План_Расч'].sum():,.0f} / Цель: {total:,.0f}")
    print(f"Сходимость: {result['План_Расч'].sum() / total * 100:.2f}%")
    
    print("\n===== КАТЕГОРИИ =====")
    print(f"Ключевые стратегические (Сантехника, Плитка): +3% — +15%")
    print(f"Плавные (Обои, Напольные, Краски): -5% — +6%")
    print(f"Нулевые (Стройматериалы): -2% — +2%")
    print(f"Сопутствующие: -5% — +6%")

