import heapq
from typing import List, Tuple, Optional, Dict, Any

# Full 5x5 neighborhood (all offsets within [-2,2] excluding (0,0)) — 24 directions
DIRS_24 = [(dr, dc) for dr in range(-2, 3) for dc in range(-2, 3) if not (dr == 0 and dc == 0)]

DIR_CODE: Dict[Tuple[int,int], int] = {d: i+1 for i, d in enumerate(DIRS_24)}

def path_to_triplets(path: List[Tuple[int,int]]):
    trips = []
    for k in range(len(path)-1):
        r,c = path[k]
        nr,nc = path[k+1]
        d = DIR_CODE.get((nr-r, nc-c), 0)
        trips.append((r,c,d))
    return trips

def extended_astar(grid, start, end):
    n = len(grid); m = len(grid[0]) if n>0 else 0
    sr, sc = start; er, ec = end
    if not (0<=sr<n and 0<=sc<m and 0<=er<n and 0<=ec<m):
        return None, None
    if grid[sr][sc]==1 or grid[er][ec]==1:
        return None, None

    def free(r,c):
        return 0<=r<n and 0<=c<m and grid[r][c]==0

    # 检查从 (r,c) 到 (nr,nc) 连线（格中心到格中心）是否穿过任何障碍格
    # 使用密采样近似 supercover：对线段做若干采样点并取所在格集合进行检查。
    def is_line_clear(r, c, nr, nc):
        # 使用 Amanatides & Woo 的栅格遍历（ray-grid traversal）精确列举
        # 从格心 (c+0.5, r+0.5) 到目标格心 (nc+0.5, nr+0.5) 的线段所经过的所有格子。
        # 返回 True 当且仅当经过的所有格子均为空（0）。这是一个精确的 supercover 判定，避免丢样本或角落穿越问题。
        import math
        x0 = c + 0.5; y0 = r + 0.5
        x1 = nc + 0.5; y1 = nr + 0.5

        # 起始/结束在网格外视为不可通行
        if not (0 <= r < n and 0 <= c < m and 0 <= nr < n and 0 <= nc < m):
            return False

        dx = x1 - x0
        dy = y1 - y0

        # 当前格坐标（整数格索引）
        ix = int(math.floor(x0))
        iy = int(math.floor(y0))
        tx = int(math.floor(x1))
        ty = int(math.floor(y1))

        # 检查起点所在格
        if grid[iy][ix] != 0:
            return False

        # 如果起终格相同，已检查起点即可
        if (ix, iy) == (tx, ty):
            return True

        # 计算步进和 tDelta
        if dx == 0.0:
            step_x = 0
            t_delta_x = float('inf')
        else:
            step_x = 1 if dx > 0 else -1
            t_delta_x = abs(1.0 / dx)

        if dy == 0.0:
            step_y = 0
            t_delta_y = float('inf')
        else:
            step_y = 1 if dy > 0 else -1
            t_delta_y = abs(1.0 / dy)

        # 计算初始 tMax：到下一个垂直/水平网格线的参数化距离
        if step_x != 0:
            if step_x > 0:
                t_max_x = ( (ix + 1) - x0 ) * t_delta_x
            else:
                t_max_x = ( x0 - ix ) * t_delta_x
        else:
            t_max_x = float('inf')

        if step_y != 0:
            if step_y > 0:
                t_max_y = ( (iy + 1) - y0 ) * t_delta_y
            else:
                t_max_y = ( y0 - iy ) * t_delta_y
        else:
            t_max_y = float('inf')

        # 沿着射线遍历格子，直到到达目标格
        # 在每次移动后立即检查新的格子是否为空
        while not (ix == tx and iy == ty):
            if t_max_x < t_max_y:
                ix += step_x
                t_max_x += t_delta_x
            else:
                iy += step_y
                t_max_y += t_delta_y

            if not (0 <= iy < n and 0 <= ix < m):
                return False
            if grid[iy][ix] != 0:
                return False

        return True

    # 对于使用 Euclidean 长跳权重，启发式使用欧氏距离以保持可采纳性
    def h(r,c):
        dx = r - er; dy = c - ec
        import math
        return math.sqrt(dx*dx + dy*dy)

    INF = float('inf')
    g = [[INF]*m for _ in range(n)]
    f = [[INF]*m for _ in range(n)]
    prev = [[None]*m for _ in range(n)]

    g[sr][sc] = 0.0
    f[sr][sc] = h(sr,sc)
    pq = [(f[sr][sc], sr, sc)]

    while pq:
        fv, r, c = heapq.heappop(pq)
        if fv!=f[r][c]:
            continue
        if (r,c)==(er,ec):
            break
        # 扩展 5x5 邻居（使用 Euclidean 长跳代价和 supercover 检查）
        for idx, (dr, dc) in enumerate(DIRS_24, start=1):
            nr, nc = r+dr, c+dc
            if not (0<=nr<n and 0<=nc<m):
                continue
            if not free(nr,nc):
                continue
            # 使用 supercover 风格的线段检查，确保连线（格中心到格中心）不穿过任何障碍格
            if not is_line_clear(r, c, nr, nc):
                continue

            # 使用 Euclidean 长跳代价
            import math
            step_cost = math.sqrt(dr*dr + dc*dc)
            tg = g[r][c] + step_cost
            if tg < g[nr][nc]:
                g[nr][nc] = tg
                f[nr][nc] = tg + h(nr,nc)
                prev[nr][nc] = (r,c)
                heapq.heappush(pq, (f[nr][nc], nr, nc))

    if g[er][ec] == INF:
        return None, None

    # 重建节点路径
    nodes = []
    cur = (er,ec)
    while cur:
        nodes.append(cur)
        pr = prev[cur[0]][cur[1]]
        cur = pr
    nodes.reverse()

    # 将节点序列直接转为 triplets：每一段 (nodes[i] -> nodes[i+1]) 对应一个方向码
    unit_path = []
    for i in range(len(nodes)-1):
        r0,c0 = nodes[i]; r1,c1 = nodes[i+1]
        if not unit_path:
            unit_path.append((r0,c0))
        # 直接将目标点加入，前端会按方向码展开为单位步用于渲染
        unit_path.append((r1,c1))

    if not unit_path:
        unit_path = [(sr,sc)]

    return path_to_triplets(unit_path), g[er][ec]


def _parse_point(pt):
    if isinstance(pt, dict):
        try:
            return int(pt.get('r', 0)), int(pt.get('c', 0))
        except Exception:
            return None
    if isinstance(pt, (list, tuple)) and len(pt) >= 2:
        try:
            return int(pt[0]), int(pt[1])
        except Exception:
            return None
    return None

def handle_solve_extended(data):
    try:
        grid = data.get('grid')
        start = _parse_point(data.get('start'))
        end = _parse_point(data.get('end'))

        if not isinstance(grid, list) or not grid or not isinstance(grid[0], list):
            return {'ok': False, 'error': 'invalid grid'}
        n = len(grid); m = len(grid[0])
        if not start or not end:
            return {'ok': False, 'error': 'invalid start/end'}
        sr, sc = start; er, ec = end
        if not (0 <= sr < n and 0 <= sc < m and 0 <= er < n and 0 <= ec < m):
            return {'ok': False, 'error': 'start/end out of range'}

        # 归一化
        norm = [[1 if int(x) != 0 else 0 for x in row] for row in grid]
        trips, cost = extended_astar(norm, (sr,sc), (er,ec))
        if trips is None:
            return {'ok': False, 'error': 'no path'}
        return {'ok': True, 'triplets': trips, 'cost': cost}
    except Exception as e:
        return {'ok': False, 'error': str(e)}