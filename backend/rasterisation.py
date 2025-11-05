import os
from urllib.parse import urlencode
from io import BytesIO
from datetime import datetime
from typing import Dict, Any
from PIL import Image
import requests

def rasterize_from_baidu(data: Dict[str, Any], ak: str, workspace_root: str) -> Dict[str, Any]:
    center = data.get('center') or {}
    zoom = int(data.get('zoom') or 19)
    canvas_w = int(data.get('canvasWidth') or 640)
    canvas_h = int(data.get('canvasHeight') or 640)
    sel = data.get('selection') or {}
    size = int(data.get('size') or 20)
    sel_center = data.get('selCenter') or None
    sel_size_px = data.get('selSizePx') or None
    lng = center.get('lng'); lat = center.get('lat')
    if lng is None or lat is None or not sel:
        return {'ok': False, 'error': 'missing center or selection'}

    # 拉取静态图
    try:
        # 优先直接按选区中心与大小请求静态图，避免再裁剪带来的像素对齐偏差
        use_direct = False
        req_center_lng = lng
        req_center_lat = lat
        req_w = canvas_w
        req_h = canvas_h
        if sel_center and sel_size_px and 'w' in sel_size_px and 'h' in sel_size_px:
            try:
                req_center_lng = float(sel_center.get('lng', lng))
                req_center_lat = float(sel_center.get('lat', lat))
                req_w = int(sel_size_px['w'])
                req_h = int(sel_size_px['h'])
                use_direct = (req_w > 0 and req_h > 0)
            except Exception:
                use_direct = False

        # 获取静态图
        base = "https://api.map.baidu.com/staticimage/v2"
        max_wh = 1024
        min_wh = 50
        ww = max(min_wh, min(req_w, max_wh))
        hh = max(min_wh, min(req_h, max_wh))
        qs = urlencode({'ak': ak,'zoom': int(zoom),'width': ww,'height': hh,'copyright': '1'})
        url = f"{base}?center={req_center_lng},{req_center_lat}&{qs}"

        r = requests.get(url, timeout=10)
        r.raise_for_status()
        ctype = r.headers.get('Content-Type','')
        if 'image' not in ctype.lower():
            text_snippet = r.text[:200]
            return {'ok': False, 'error': f'static image not image: {ctype}', 'body': text_snippet, 'url': url}
        img = Image.open(BytesIO(r.content)).convert('RGB')
    except Exception as e:
        return {'ok': False, 'error': f'static image fetch failed: {e}'}

    # 若直接按选区大小获取了静态图，则无需裁剪；否则按 selection 像素裁剪
    if use_direct and ww == req_w and hh == req_h:
        crop = img
    else:
        try:
            kx = (ww / canvas_w) if canvas_w else 1.0
            ky = (hh / canvas_h) if canvas_h else 1.0
            x = int(round(sel['x'] * kx))
            y = int(round(sel['y'] * ky))
            w = int(round(sel['w'] * kx))
            h = int(round(sel['h'] * ky))
            x = max(0, min(x, img.width-1)); y = max(0, min(y, img.height-1))
            w = max(1, min(w, img.width - x)); h = max(1, min(h, img.height - y))
            crop = img.crop((x, y, x+w, y+h))
        except Exception as e:
            return {'ok': False, 'error': f'crop failed: {e}'}

    # 保存裁切后的原始图到 Project/MapImage，文件名为日期+时间
    project_dir = os.path.dirname(__file__)
    project_dir = os.path.abspath(os.path.join(project_dir, '..'))
    out_dir = os.path.join(project_dir, 'MapImage')
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    crop_file = os.path.join(out_dir, f"{ts}.png")
    crop.save(crop_file, format='PNG')

    # 栅格化
    WATER_RGB = (0x91, 0xDF, 0xFA)  # 水域#91dffa
    BUILDING_RGB = (0xF9, 0xF7, 0xF4)  # 建筑#f9f7f4
    ROAD_RGB = (0xFF, 0xFF, 0xFF)  # 道路#ffffff
    rgb_full = crop.convert('RGB')
    px = rgb_full.load()
    rw = max(1.0, crop.width / float(size))
    rh = max(1.0, crop.height / float(size))

    # 判定
    try:
        _th = (data.get('thresholds') or {}) if isinstance(data.get('thresholds'), dict) else {}
        area_ratio = float(data.get('areaRatio', _th.get('area_ratio', 0.20)))
    except Exception:
        area_ratio = 0.20
    try:
        _th = (data.get('thresholds') or {}) if isinstance(data.get('thresholds'), dict) else {}
        road_ratio = float(data.get('roadRatio', _th.get('road_ratio', 0.25)))
    except Exception:
        road_ratio = 0.25

    grid = []
    for r in range(size):
        row = []
        y0 = int(r * rh)
        y1 = int((r + 1) * rh) - 1
        if y0 < 0: y0 = 0
        if y1 >= crop.height: y1 = crop.height - 1
        if y1 < y0: y1 = y0
        for c in range(size):
            x0 = int(c * rw)
            x1 = int((c + 1) * rw) - 1
            if x0 < 0: x0 = 0
            if x1 >= crop.width: x1 = crop.width - 1
            if x1 < x0: x1 = x0

            total = max(1, (x1 - x0 + 1) * (y1 - y0 + 1))
            obs_count = 0
            road_count = 0
            for yy in range(y0, y1 + 1):
                for xx in range(x0, x1 + 1):
                    r0, g0, b0 = px[xx, yy]
                    if (r0, g0, b0) == ROAD_RGB:
                        road_count += 1
                    elif (r0, g0, b0) == WATER_RGB or (r0, g0, b0) == BUILDING_RGB:
                        obs_count += 1

            if road_count > total * road_ratio:
                row.append(0)
            else:
                # 否则按障碍比例判定（严格大于阈值才为障碍）
                row.append(1 if (obs_count > total * area_ratio) else 0)
        grid.append(row)

    return {'ok': True, 'size': size, 'grid': grid, 'cropFile': crop_file}