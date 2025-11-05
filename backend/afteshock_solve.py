from typing import List, Tuple
from backend.aftershock_generate import aftershock_step
from backend.pathfinder import a_star_jps, _compute_safety_cost
    
def dynamic_step_service(data):
    grid = data.get('grid')
    start = data.get('start')
    goal = data.get('goal')
    agent = data.get('agent') or start
    interval_ticks = data.get('intervalTicks')
    severity = data.get('severity')
    after_state = data.get('aftershockState')

    if not isinstance(grid, list) or not grid or not isinstance(grid[0], list):
        raise ValueError('invalid grid')

    n = len(grid); m = len(grid[0])

    def _pt(p):
        if isinstance(p, dict):
            return int(p.get('r')), int(p.get('c'))
        return int(p[0]), int(p[1])

    sr, sc = _pt(start); gr, gc = _pt(goal); ar, ac = _pt(agent)
    if not (0<=sr<n and 0<=sc<m and 0<=gr<n and 0<=gc<m and 0<=ar<n and 0<=ac<m):
        raise ValueError('points out of range')

    # 归一化为 0/1，并复制一份用于计算变化
    norm = [[1 if int(x) != 0 else 0 for x in row] for row in grid]
    before = [row[:] for row in norm]

    # 1) 余震步进（tick-only）
    ares = aftershock_step(norm, interval_ticks, severity, after_state)
    grid_now = ares['grid']
    after_state_out = ares['state']

    # 保证起点/终点不被坍塌
    grid_now[sr][sc] = 0
    grid_now[gr][gc] = 0

    # 变化单元格（供后端规划器使用，做增量或全图重算判断）
    changed: List[Tuple[int,int]] = []
    for r in range(n):
        br = before[r]; cr = grid_now[r]
        for c in range(m):
            if br[c] != cr[c]:
                changed.append((r,c))

    # 2) 规划/重规划（使用 A* 全图重算，每步调用以保证行为简单）
    costs = _compute_safety_cost(grid_now)
    # a_star_jps 返回 (triplets, cost) 或 (None, None)
    res = a_star_jps(grid_now, (ar,ac), (gr,gc), costs=costs)
    if isinstance(res, tuple) and len(res) == 2:
        trips, trip_cost = res
    else:
        trips = res
        trip_cost = None

    path_nodes: List[Tuple[int,int]] = []
    if trips is None:
        path = []
        agent_next = {'r': ar, 'c': ac}
        done = False
        reason = 'no path'
    else:
        # 从 triplets 还原节点路径（triplets 长度 = 节点数 - 1）
        dir_map = {1: (0,1), 2: (1,0), 3: (0,-1), 4: (-1,0)}
        # trips 是 List[Tuple[r,c,d]]，第一个元素包含起点坐标
        if len(trips) == 0:
            # 起点即终点的特殊情况
            path_nodes = [(ar, ac)]
        else:
            cur_r, cur_c = int(trips[0][0]), int(trips[0][1])
            path_nodes = [(cur_r, cur_c)]
            for (_, _, d) in trips:
                delta = dir_map.get(int(d))
                if not delta:
                    break
                cur_r += delta[0]; cur_c += delta[1]
                path_nodes.append((cur_r, cur_c))

        path = [ {'r': r, 'c': c} for (r,c) in path_nodes ]
        # 下一步为路径的第二个节点（如果存在）
        if len(path_nodes) >= 2:
            ns = path_nodes[1]
            agent_next = {'r': ns[0], 'c': ns[1]}
            reason = None
        else:
            agent_next = {'r': ar, 'c': ac}
            reason = None
        done = (agent_next['r'] == gr and agent_next['c'] == gc)

    return {
        'grid': grid_now,
        'aftershockState': after_state_out,
        'path': path,
        'agent': agent_next,
        'start': { 'r': sr, 'c': sc },
        'goal':  { 'r': gr, 'c': gc },
        'done': done,
        'reason': reason
    }