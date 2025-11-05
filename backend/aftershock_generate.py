import random
from typing import Dict, Tuple
from backend.earthquake import neighbors

def _clamp01(x):    # 约束在 [0,1]
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

def _rand_jitter(a, b):  # 在 [a,b] 范围内均匀扰动
    return a + (b - a) * random.random()

# 激活单元格
def _activate_cell(grid, r, c, until_tick, active_map):
    n = len(grid)
    if r < 0 or r >= n or c < 0 or c >= n:
        return
    key = (r,c)
    prev = grid[r][c]
    if key in active_map:
        if until_tick > active_map[key]['until']:
            active_map[key]['until'] = until_tick
        grid[r][c] = 1
    else:
        active_map[key] = {'r': r, 'c': c, 'until': until_tick, 'prev': int(prev)}
        grid[r][c] = 1

# 到期恢复
def _expire_cells(grid, current_tick, active_map):
    expired = []
    for key, rec in active_map.items():
        if rec['until'] <= current_tick:
            expired.append(key)
    for key in expired:
        r, c = key
        prev = active_map[key].get('prev', 0)
        if prev == 0:
            grid[r][c] = 0
        del active_map[key]
    return len(expired)

# 区域生长
def _region_grow(grid, seed_r, seed_c, target, until_tick, active_map, bias=0.6):
    n = len(grid)
    if seed_r < 0 or seed_r >= n or seed_c < 0 or seed_c >= n:
        return 0
    added = 0
    frontier = [(seed_r, seed_c)]
    visited = set()
    while frontier and target > 0:
        r, c = frontier.pop()
        if (r,c) in visited:
            continue
        visited.add((r,c))
        if grid[r][c] == 0 or (r,c) in active_map:
            _activate_cell(grid, r, c, until_tick, active_map)
            added += 1
            target -= 1
        for nr, nc in neighbors(n, r, c):
            if random.random() < bias:
                frontier.append((nr, nc))
    return added

def aftershock_step(grid, interval_ticks, severity, state=None):
    """
    逐步余震更新（纯 tick 驱动）：
    - 不做任何真实时间映射，所有时间单位均为 tick；
    - interval_ticks 控制“生成/扩张”的步长间隔；
    - 动态障碍有寿命（以 tick 为单位），到期恢复原值（原本为 0 才恢复）；
    - 达到生成时刻：
        * 让部分现有动态障碍向邻近扩张；
        * 生成若干新簇（规模与 n² 与 severity 成正比）。
    - 返回 grid、state（含 active 列表）和统计。
    """ 
    n = len(grid)
    severity = _clamp01(float(severity) if severity is not None else 0.0)
    try:
        interval_ticks = int(interval_ticks)
    except Exception:
        interval_ticks = 5
    interval_ticks = max(1, interval_ticks)

    base_life_ticks = int(interval_ticks * (1.5 + 1.0 * severity))

    s = state or {}
    tick = int(s.get('tick') or 0)
    last_spawn_tick = int(s.get('lastSpawnTick') or -10**9)
    active_list = s.get('active') or []
    active_map: Dict[Tuple[int,int], Dict[str,int]] = {}
    for rec in active_list:
        try:
            r = int(rec.get('r')); c = int(rec.get('c'))
            until = int(rec.get('untilTick') if rec.get('untilTick') is not None else rec.get('until') or 0)
            prev = int(rec.get('prev', 0))
            active_map[(r,c)] = {'r': r, 'c': c, 'until': until, 'prev': prev}
        except Exception:
            continue

    expired = _expire_cells(grid, tick, active_map) # 恢复到期（tick）
    spawned = 0 # 新增
    grown = 0   # 扩张

    if tick - last_spawn_tick >= interval_ticks:
        if active_map:
            tries = max(1, int(3 + 7 * severity))
            keys = list(active_map.keys())
            random.shuffle(keys)
            keys = keys[:min(len(keys), tries)]
            for (r,c) in keys:
                grow_k = max(1, int(1 + 2 * severity))
                for nr, nc in neighbors(n, r, c):
                    if grow_k <= 0:
                        break
                    if grid[nr][nc] == 0:
                        life = int(base_life_ticks * _rand_jitter(0.8, 1.2))
                        _activate_cell(grid, nr, nc, tick + life, active_map)
                        grown += 1
                        grow_k -= 1

        target_area = max(1, int(severity * 0.003 * n * n))
        clusters = max(1, int(1 + severity * 2))
        per_cluster = max(1, target_area // clusters)
        for _ in range(clusters):
            sr = random.randrange(n); sc = random.randrange(n)
            life = int(base_life_ticks * _rand_jitter(0.8, 1.2))
            spawned += _region_grow(grid, sr, sc, per_cluster, tick + life, active_map, bias=0.55 + 0.3*severity)
        last_spawn_tick = tick

    # tick 前进一格
    tick += 1

    new_state = {
        'tick': tick,
        'lastSpawnTick': last_spawn_tick,
        'intervalTicks': interval_ticks,
        'active': [ {'r': rec['r'], 'c': rec['c'], 'untilTick': rec['until'], 'prev': rec.get('prev',0)} for rec in active_map.values() ]
    }

    return {
        'grid': grid,
        'state': new_state,
        'stats': {'expired': expired, 'spawned': spawned, 'grown': grown}
    }