# 飞途FlyWay — 无人机路径规划 & 余震仿真平台

简要说明：本仓库实现了一个小型的前后端演示平台，用于演示无人机避障、扩展邻域搜索、余震/坍塌仿真等算法。前端为静态页面（HTML/CSS/JS），后端为一组 Python 模块并通过内置 HTTP 服务器提供简单的 API
## 使用须知
- **请把 `Project` 文件夹作为运行时的工作目录**（即在该目录下运行下述启动命令）
- 使用时请自行注册百度地图开放平台开发者，并自行配置serve.py中的`Baidu_AK_Server`和`Baidu_AK_Client`为服务器端AK和客户端AK

## 项目结构（概览）
- backend/: 后端 Python 模块
    - `pathfinder.py`：路径搜索的多种实现（Dijkstra、A*、带权/带安全代价、JPS 变体、递归版 Dijkstra 等）
    - `extended_neighbors.py`：扩展邻域 A* 实现（用于前端扩展邻域示例页）
    - `afteshock_solve.py` / `aftershock_generate.py`：余震仿真相关逻辑
    - `earthquake.py`：用于生成简化的坍塌场景
    - `rasterisation.py`：将地图选区栅格化为 0/1 网格
- web/: 前端静态文件（HTML/CSS/JS）
    - `map-process.html` / `map-process.js`：地图选取与栅格处理 UI（生成/导入/导出等）
    - `algo-uav.html` / `algo-uav.js`：无人机避障演示页面
    - `algo-extended.html` / `algo-extended.js`：扩展邻域演示页面
    - 其它页面：`index.html`, `map-select.html`, `algo-aftershock.html` 等
- TEST/: 示例栅格 JSON（如 `1.json`）
- `serve.py`: 简单的单文件 HTTP 服务器，提供对 `web/` 静态页面和后端 API 的路由

## 依赖与环境
- Python 3.8+
- 在 Windows 下建议使用 PowerShell 作为示例命令行

## 启动服务器（开发/演示）
在项目根目录（包含 `serve.py`）执行：

```powershell
python .\serve.py
```

成功启动后会在控制台打印可访问地址，例如：`http://localhost:9999`,打开浏览器访问即可。

## 常用页面与快速演示
- 首页：`index.html`（功能入口）
- 地图处理：`map-process.html`（生成/导入/导出栅格、设置起点终点）
- 无人机避障：`algo-uav.html`（选择算法并运行；若无通路会弹窗提示）
- 扩展邻域：`algo-extended.html`（调用后端扩展邻域接口并绘制直线段路径）
- 余震模拟：`algo-aftershock.html`

## API 简要说明
- `POST /api/rasterize`：将地图选区栅格化为 `grid`（POST JSON）
- `POST /api/simulate-collapse`：随机/模拟坍塌生成栅格（POST JSON）
- `POST /api/solve`：通用寻路接口，接收 { algo, grid, start, end, safe }，返回 { ok, triplets, cost }
- `POST /api/solve-extended`：扩展邻域求解（返回 triplets）
- `POST /api/dynamic-step`：余震步进仿真接口

## 调试提示
- 若遇到 `ModuleNotFoundError: No module named 'backend'`，请确认当前工作目录为项目根，并使用 `python .\serve.py` 启动或在运行脚本前暂时把项目根加入 `PYTHONPATH`。
- 前端页面若没有响应，请在浏览器开发者工具（Console）检查是否有脚本错误或 404 资源未加载。

## 后续改进建议
- 为后端增加单元测试（可使用 pytest）以保证算法一致性
- 将前端的 alert 提示替换为非阻塞 toast，提高 UX
- 若需生产部署，建议用真正的 WSGI 服务器并把 API 与静态文件分离
