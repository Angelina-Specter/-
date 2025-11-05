import heapq
from typing import List, Tuple, Dict, Any
from collections import deque

# 东南西北
DIRS = [(0,1),(1,0),(0,-1),(-1,0)]  
DIR_CODE = {(0,1):1,(1,0):2,(0,-1):3,(-1,0):4}

def find_all_paths(grid, start, end):
    """
    递归形式的算法，求得楼内部所有可能的通路
    """
    n = len(grid)
    m = len(grid[0]) if n > 0 else 0
    all_paths = []
    
    def dfs(current, path, visited):
        r, c = current
        
        # 到达终点，保存路径
        if current == end:
            all_paths.append(path.copy())
            return
        
        # 四个方向：东、南、西、北
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            next_pos = (nr, nc)
            
            # 检查新位置是否有效且未被访问
            if (0 <= nr < n and 0 <= nc < m and 
                grid[nr][nc] == 0 and next_pos not in visited):
                
                visited.add(next_pos)
                path.append(next_pos)
                
                # 递归搜索
                dfs(next_pos, path, visited)
                
                # 回溯
                path.pop()
                visited.remove(next_pos)
    
    # 初始化搜索
    visited = set()
    visited.add(start)
    dfs(start, [start], visited)
    return all_paths
def path_to_triplets(path):
    trips = []
    for k in range(len(path)-1):
        r,c = path[k]
        nr,nc = path[k+1]
        d = DIR_CODE.get((nr-r, nc-c), 0)
        trips.append((r,c,d))
    return trips
def format_all_paths_as_triplets(all_paths):
    """
    将所有路径转换为三元组形式
    """
    all_triplets = []
    for path in all_paths:
        triplets = path_to_triplets(path)
        all_triplets.append(triplets)
    return all_triplets

def format_all_paths_as_matrices(grid, all_paths):
    """
    将所有路径以方阵形式输出
    """
    matrices = []
    n, m = len(grid), len(grid[0]) if grid else 0
    dir_arrows = {
        (0, 1): "→",   # 右
        (1, 0): "↓",   # 下
        (0, -1): "←",  # 左
        (-1, 0): "↑"   # 上
    }
    for path in all_paths:
        # 复制原始网格
        mat = [row[:] for row in grid]
        
        # 标记路径方向
        for i in range(len(path) - 1):
            r, c = path[i]
            nr, nc = path[i + 1]
            dr, dc = nr - r, nc - c
            
            # 检查坐标是否有效且是可通过区域
            if 0 <= r < n and 0 <= c < m and mat[r][c] == 0:
                mat[r][c] = dir_arrows.get((dr, dc), "*")
        
        matrices.append(mat)
    
    return matrices
def dijkstra(grid, start, end):
    n = len(grid)
    m = len(grid[0]) if n>0 else 0
    sr, sc = start
    er, ec = end
    dist = [[float('inf')]*m for _ in range(n)]
    prev = [[None]*m for _ in range(n)]
    dist[sr][sc] = 0.0
    pq = [(0.0, sr, sc)]

    def step():
        if not pq:
            return
        d, r, c = heapq.heappop(pq)
        # 过期条目跳过
        if d != dist[r][c]:
            return step()
        # 提前终止条件
        if (r, c) == (er, ec):
            return
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < m and grid[nr][nc] == 0:
                nd = d + 1.0
                if nd < dist[nr][nc]:
                    dist[nr][nc] = nd
                    prev[nr][nc] = (r, c)
                    heapq.heappush(pq, (nd, nr, nc))
        # 递归处理下一个队列元素
        return step()
    step()

    if dist[er][ec] == float('inf'):
        return None, None
    path = []
    cur = (er, ec)
    while cur:
        path.append(cur)
        pr = prev[cur[0]][cur[1]]
        cur = pr
    path.reverse()
    return path_to_triplets(path), dist[er][ec]

def a_star(grid, start, end):
    n = len(grid)
    m = len(grid[0]) if n > 0 else 0
    sr, sc = start
    er, ec = end

    def h(r, c):
        return abs(r - er) + abs(c - ec)

    INF = float('inf')
    g = [[INF] * m for _ in range(n)]
    f = [[INF] * m for _ in range(n)]
    prev = [[None] * m for _ in range(n)]

    open_set = []  # 优先队列
    open_dict = {}  # Open 表，用于快速查找
    close_set = set()  # Close 表

    g[sr][sc] = 0.0
    f[sr][sc] = h(sr, sc)
    heapq.heappush(open_set, (f[sr][sc], sr, sc))
    open_dict[(sr, sc)] = f[sr][sc]

    while open_set:
        _, r, c = heapq.heappop(open_set)
        open_dict.pop((r, c), None)

        if (r, c) == (er, ec):
            break

        if (r, c) in close_set:
            continue
        close_set.add((r, c))

        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < m and grid[nr][nc] == 0:
                tentative_g = g[r][c] + 1.0
                if tentative_g < g[nr][nc]:
                    g[nr][nc] = tentative_g
                    f[nr][nc] = tentative_g + h(nr, nc)
                    prev[nr][nc] = (r, c)
                    if (nr, nc) not in close_set and (nr, nc) not in open_dict:
                        heapq.heappush(open_set, (f[nr][nc], nr, nc))
                        open_dict[(nr, nc)] = f[nr][nc]

    if g[er][ec] == INF:
        return None, None
    path = []
    cur = (er, ec)
    while cur:
        path.append(cur)
        cur = prev[cur[0]][cur[1]]
    path.reverse()
    return path_to_triplets(path), g[er][ec]

# ---------------------------------------------------------------------------------------------------------------------------------------------

def _compute_safety_cost(grid):
    radius = 3   # 安全半径
    alpha = 1.25 # 安全权重
    n = len(grid); m = len(grid[0]) if n>0 else 0
    INF = float('inf')
    dist = [[INF]*m for _ in range(n)]
    q = deque()
    # 多源 BFS：障碍为源，距离=0
    for r in range(n):
        for c in range(m):
            if grid[r][c] == 1:
                dist[r][c] = 0
                q.append((r,c))
    while q:
        r,c = q.popleft()
        d0 = dist[r][c]
        for dr,dc in DIRS:
            nr, nc = r+dr, c+dc
            if 0<=nr<n and 0<=nc<m and dist[nr][nc] == INF:
                if grid[nr][nc] == 0:
                    dist[nr][nc] = d0 + 1
                    q.append((nr,nc))
    # 生成代价
    costs: List[List[float]] = [[INF]*m for _ in range(n)]
    for r in range(n):
        for c in range(m):
            if grid[r][c] == 1:
                costs[r][c] = INF
            else:
                d = dist[r][c]
                if d == INF:
                    penalty = 0.0
                else:
                    penalty = max(0.0, (radius - float(d)) / max(1.0, float(radius)))
                costs[r][c] = 1.0 + alpha * penalty
    return costs

def dijkstra_weighted(grid, costs, start, end):
    n = len(grid); m = len(grid[0]) if n>0 else 0
    sr, sc = start; er, ec = end
    INF = float('inf')
    if grid[sr][sc]==1 or grid[er][ec]==1:
        return None, None
    dist = [[INF]*m for _ in range(n)]
    prev = [[None]*m for _ in range(n)]
    dist[sr][sc] = 0.0
    pq = [(0.0, sr, sc)]
    while pq:
        d, r, c = heapq.heappop(pq)
        if d!=dist[r][c]:
            continue
        if (r,c)==(er,ec):
            break
        for dr,dc in DIRS:
            nr, nc = r+dr, c+dc
            if 0<=nr<n and 0<=nc<m and grid[nr][nc]==0:
                step = costs[nr][nc]
                if step == INF:
                    continue
                nd = d + step
                if nd < dist[nr][nc]:
                    dist[nr][nc] = nd
                    prev[nr][nc] = (r,c)
                    heapq.heappush(pq, (nd, nr, nc))
    if dist[er][ec] == INF:
        return None, None
    path = []
    cur = (er,ec)
    while cur:
        path.append(cur)
        pr = prev[cur[0]][cur[1]]
        cur = pr
    path.reverse()
    return path_to_triplets(path), dist[er][ec]

def a_star_weighted(grid, costs, start, end):
    n = len(grid); m = len(grid[0]) if n>0 else 0
    sr, sc = start; er, ec = end
    INF = float('inf')
    if grid[sr][sc]==1 or grid[er][ec]==1:
        return None, None

    def h(r:int,c:int)->float:
        # 下界启发：每步至少 1
        return abs(r-er) + abs(c-ec)

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
        for dr,dc in DIRS:
            nr, nc = r+dr, c+dc
            if 0<=nr<n and 0<=nc<m and grid[nr][nc]==0:
                step = costs[nr][nc]
                if step == INF:
                    continue
                tg = g[r][c] + step
                if tg < g[nr][nc]:
                    g[nr][nc] = tg
                    f[nr][nc] = tg + h(nr,nc)
                    prev[nr][nc] = (r,c)
                    heapq.heappush(pq, (f[nr][nc], nr, nc))
    if g[er][ec] == INF:
        return None, None
    path = []
    cur = (er,ec)
    while cur:
        path.append(cur)
        pr = prev[cur[0]][cur[1]]
        cur = pr
    path.reverse()
    return path_to_triplets(path), g[er][ec]


# ---------------------------------------------------------------------------------------------------------------------------------------------------

def a_star_jps(grid, start, end, costs):
    n = len(grid); m = len(grid[0]) if n>0 else 0
    sr, sc = start; er, ec = end
    # 边界/障碍检查
    if not (0 <= sr < n and 0 <= sc < m and 0 <= er < n and 0 <= ec < m):
        return None, None
    if grid[sr][sc] == 1 or grid[er][ec] == 1:
        return None, None

    def in_bounds(r,c):
        return 0<=r<n and 0<=c<m

    def is_free(r,c):
        if not in_bounds(r,c):
            return False
        if grid[r][c] != 0:
            return False
        if costs is not None:
            try:
                if costs[r][c] == float('inf'):
                    return False
            except Exception:
                pass
        return True

    # 选取跳点：起点、终点，和与障碍相邻的空格，以及自由度不是2的格（交叉或死胡同）
    jump_points = set()
    jump_points.add((sr,sc)); jump_points.add((er,ec))
    for r in range(n):
        for c in range(m):
            if not is_free(r,c):
                continue
            free_nei = 0
            nei_block = 0
            for dr,dc in DIRS:
                nr, nc = r+dr, c+dc
                if is_free(nr,nc):
                    free_nei += 1
                else:
                    nei_block += 1
            if nei_block > 0 or free_nei != 2:
                jump_points.add((r,c))

    # 若跳点集合过小（例如全空地图），退化回普通 A*
    if len(jump_points) < 3:
        return a_star(grid, start, end)

    # 为每个跳点按四方向建立可见性边（直到遇到障碍或下一个跳点或边界）
    # 边权：如果提供了 costs，则为沿直线所有单步 costs 之和；否则为步数(dist)
    # adj maps each jump-point to a list of (neighbor_jump_point, weight)
    adj = { jp: [] for jp in jump_points }
    for (r,c) in list(jump_points):
        for dr,dc in DIRS:
            nr, nc = r+dr, c+dc
            dist = 1
            weight_sum = 0.0
            while is_free(nr,nc):
                if costs is not None:
                    # 加上进入该格的代价（与 a_star_weighted 语义一致）
                    step_cost = costs[nr][nc]
                    if step_cost == float('inf'):
                        break
                    weight_sum += float(step_cost)
                if (nr,nc) in jump_points:
                    adj[(r,c)].append(((nr,nc), weight_sum if costs is not None else float(dist)))
                    break
                if (nr,nc) == (er,ec):
                    adj[(r,c)].append(((nr,nc), weight_sum if costs is not None else float(dist)))
                    break
                nr += dr; nc += dc; dist += 1

    # 在跳点图上运行 A*
    import math
    open_set = []
    heapq.heappush(open_set, (abs(sr-er)+abs(sc-ec), 0.0, (sr,sc)))
    gscore = { (sr,sc): 0.0 }
    prev = { }
    closed = set()

    while open_set:
        _, cur_g, cur = heapq.heappop(open_set)
        if cur in closed:
            continue
        if cur == (er,ec):
            break
        closed.add(cur)
        for nb, w in adj.get(cur, []):
            if nb in closed:
                continue
            tentative = gscore.get(cur, math.inf) + w
            if tentative < gscore.get(nb, math.inf):
                gscore[nb] = tentative
                prev[nb] = cur
                priority = tentative + abs(nb[0]-er)+abs(nb[1]-ec)
                heapq.heappush(open_set, (priority, tentative, nb))

    if (er,ec) not in prev and (er,ec) != (sr,sc):
        return None, None

    # 重建跳点序列
    seq = []
    cur = (er,ec)
    seq.append(cur)
    while cur != (sr,sc):
        cur = prev.get(cur)
        if cur is None:
            return a_star(grid, start, end)
        seq.append(cur)
    seq.reverse()

    # 将跳点序列展开为网格路径（直线段），并计算总代价
    full_path: List[Tuple[int,int]] = []
    total_cost = 0.0
    for i in range(len(seq)-1):
        r0,c0 = seq[i]; r1,c1 = seq[i+1]
        dr = 0 if r1==r0 else (1 if r1>r0 else -1)
        dc = 0 if c1==c0 else (1 if c1>c0 else -1)
        cr, cc = r0, c0
        full_path.append((cr,cc))
        while (cr,cc) != (r1,c1):
            cr += dr; cc += dc
            full_path.append((cr,cc))
            if costs is not None:
                total_cost += float(costs[cr][cc])
    if not full_path:
        full_path = [(sr,sc)]
    if costs is None:
        cost = float(len(full_path)-1)
    else:
        cost = total_cost
    return path_to_triplets(full_path), cost



def solve(payload):
    algo = payload.get('algo')
    grid = payload.get('grid')
    start = payload.get('start')
    end = payload.get('end')
    safe = bool(payload.get('safe') or False)

    if not isinstance(grid, list) or not grid or not isinstance(grid[0], list):
        return {'ok': False, 'error': 'invalid grid'}
    if len(start)!=2 or len(end)!=2:
        return {'ok': False, 'error': 'invalid start/end'}

    if safe:
        costs = _compute_safety_cost(grid)
        if algo=='astar':
            trips, cost = a_star_weighted(grid, costs, (start[0],start[1]), (end[0],end[1]))
        else:
            trips, cost = dijkstra_weighted(grid, costs, (start[0],start[1]), (end[0],end[1]))
    else:
        if algo=='astar':
            trips, cost = a_star(grid, (start[0],start[1]), (end[0],end[1]))
        else:
            trips, cost = dijkstra(grid, (start[0],start[1]), (end[0],end[1]))

    if trips is None:
        return {'ok': False, 'error': 'no path'}
    return {'ok': True, 'algo': algo, 'triplets': trips, 'cost': cost, 'safe': safe}

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

def handle_solve(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        grid = data.get('grid')
        start = _parse_point(data.get('start'))
        end = _parse_point(data.get('end'))
        algo = data.get('algo')
        safe = data.get('safe')
        safe_radius = data.get('safeRadius')
        safe_weight = data.get('safeWeight')

        if not isinstance(grid, list) or not grid or not isinstance(grid[0], list):
            return {'ok': False, 'error': 'invalid grid'}
        n = len(grid); m = len(grid[0])
        if not start or not end:
            return {'ok': False, 'error': 'invalid start/end'}
        sr, sc = start; er, ec = end
        if not (0 <= sr < n and 0 <= sc < m and 0 <= er < n and 0 <= ec < m):
            return {'ok': False, 'error': 'start/end out of range'}

        norm = [[1 if int(x) != 0 else 0 for x in row] for row in grid]
        payload = {'algo': algo, 'grid': norm, 'start': (sr, sc), 'end': (er, ec), 'safe': safe}
        if safe_radius is not None:
            payload['safeRadius'] = safe_radius
        if safe_weight is not None:
            payload['safeWeight'] = safe_weight
        res = solve(payload)
        return res
    except Exception as e:
        return {'ok': False, 'error': str(e)}