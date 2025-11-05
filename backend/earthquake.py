import random
from typing import List
# - 结构化障碍：墙体/廊道/房间块的成片坍塌
# - 碎片化障碍：掉落碎块、堆积
# - 可控参数：强度、连通性、碎片比例、走廊保持概率
# 基本思路：
# 1) 生成基础房间布局（若未提供），构造走廊与房间栅格；
# 2) 在房间内部以连通簇方式坍塌（区域生长）；
# 3) 沿“承重线/墙体线”增加成带状坍塌；
# 4) 随机碎片撒落，形成非规则形状；

class CollapseParams:
    def __init__(
        self,
        intensity = 0.8,       # 总体坍塌强度
        corridor_keep = 0.6,   # 走廊保持概率
        cluster_bias = 0.3,    # 成片坍塌倾向
        debris_ratio = 0.02,   # 零散碎片比例
        wall_belt = 0.3,       # 沿墙/承重线成带坍塌概率 
    ):
        self.intensity = max(0.0, min(1.0, intensity))
        self.corridor_keep = max(0.0, min(1.0, corridor_keep))
        self.cluster_bias = max(0.0, min(1.0, cluster_bias))
        self.debris_ratio = max(0.0, min(1.0, debris_ratio))
        self.wall_belt = max(0.0, min(1.0, wall_belt))

DEFAULT_PARAMS = CollapseParams()

def gen_room_layout(n, room_size: int = 10):
    """初始化"""
    g = [[0 for _ in range(n)] for _ in range(n)]
    for i in range(0, n, room_size):
        for c in range(n):
            g[i][c] = 0
    for j in range(0, n, room_size):
        for r in range(n):
            g[r][j] = 0
    return g

def neighbors(n: int, r: int, c: int):
    for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
        nr, nc = r+dr, c+dc
        if 0 <= nr < n and 0 <= nc < n:
            yield nr, nc

def apply_corridor_keep(grid: List[List[int]], keep_prob: float):
    """提高走廊通行概率：对规则网格线（假定为走廊线）做稀疏清理。"""
    n = len(grid)
    for i in range(n):
        for j in range(n):
            if i % 10 == 0 or j % 10 == 0:
                if random.random() < keep_prob:
                    grid[i][j] = 0

def cluster_collapse(grid: List[List[int]], params: CollapseParams = DEFAULT_PARAMS):
    """成片坍塌：随机挑若干种子做区域生长，形成大块障碍。"""
    n = len(grid)
    seeds = max(1, int(params.intensity * 10))
    area_scale = int((n / 40) ** 0.5)
    base_target = params.intensity * (n // 3)
    scaled_target = int(max(3, min(n * n * 0.25, base_target * max(1.0, area_scale))))
    for _ in range(seeds):
        r = random.randrange(n); c = random.randrange(n)
        target = scaled_target
        frontier = [(r,c)]
        visited = set()
        while frontier and target>0:
            cr, cc = frontier.pop()
            if (cr,cc) in visited: continue
            visited.add((cr,cc))
            grid[cr][cc] = 1
            target -= 1
            for nr, nc in neighbors(n, cr, cc):
                if random.random() < (0.5 + 0.5*params.cluster_bias):
                    frontier.append((nr,nc))

def wall_belt_collapse(grid: List[List[int]], params: CollapseParams = DEFAULT_PARAMS):
    """沿墙/承重线进行带状坍塌：靠近边界或模拟承重墙线条。"""
    n = len(grid)
    # 四周墙体附近
    belt = max(1, n//20)
    for r in range(n):
        for c in range(n):
            near_wall = (r < belt) or (r >= n-belt) or (c < belt) or (c >= n-belt)
            if near_wall and random.random() < params.wall_belt*0.5:
                grid[r][c] = 1
    # 模拟承重墙：每隔 ~room_size 列/行加一条带状坍塌
    room = 10
    for i in range(room, n, room):
        for c in range(n):
            if random.random() < params.wall_belt*0.25:
                grid[i][c] = 1
    for j in range(room, n, room):
        for r in range(n):
            if random.random() < params.wall_belt*0.25:
                grid[r][j] = 1

def scatter_debris(grid: List[List[int]], params: CollapseParams = DEFAULT_PARAMS):
    """碎片化障碍：在通路上随机撒落碎片，形成不规则干扰。"""
    n = len(grid)
    total = n*n
    cnt = int(total * params.debris_ratio)
    for _ in range(cnt):
        r = random.randrange(n); c = random.randrange(n)
        if grid[r][c] == 0:
            grid[r][c] = 1
            # 以小概率再扩散一点点
            if random.random() < 0.3:
                for nr, nc in neighbors(n, r, c):
                    if random.random() < 0.2:
                        grid[nr][nc] = 1

def simulate_collapse(n: int) -> List[List[int]]:
    """生成 n×n 室内坍塌栅格（1=障碍，0=通路）。"""
    grid = gen_room_layout(n)
    # 步骤：成片坍塌 -> 墙带坍塌 -> 碎片 -> 走廊清理
    params = DEFAULT_PARAMS
    cluster_collapse(grid, params)
    wall_belt_collapse(grid, params)
    scatter_debris(grid, params)
    apply_corridor_keep(grid, params.corridor_keep)
    return grid