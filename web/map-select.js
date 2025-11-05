// 地图选取模块脚本
(function(){
  // 简易契约
  // 输入控件：#placeInput, #btnSearch, #btnRandom, #btnSelectArea, #btnConfirm, #btnCancel
  // 地图容器：#bmap ； 框选层：#selLayer
  // 成果：记录 center（lng,lat）、bounds（像素选区换算成地理范围暂不导出，仅保存像素矩形），并在确认时打印到控制台（后续可对接地图处理页）

  const placeInput = document.getElementById('placeInput');
  const btnSearch = document.getElementById('btnSearch');
  const btnSelectArea = document.getElementById('btnSelectArea');
  const btnConfirm = document.getElementById('btnConfirm');
  const btnCancel = document.getElementById('btnCancel');
  const mapDiv = document.getElementById('bmap');
  const selCanvas = document.getElementById('selLayer');

  let map = null;
  let marker = null;
  let drawing = false;
  let anchor = null; // {x,y}
  let selection = null; // {x,y,w,h}
  let selecting = false;
  let mapDraggingEnabled = true;
  let locked = false;
  let hasSavedSelection = false;

  function updateConfirmState(){
    try{
      if(btnConfirm){
        const ok = !!(selection && selection.w>0 && selection.h>0);
        btnConfirm.disabled = !ok;
      }
    }catch{}
  }

  function initMap(){
    if(!window.BMapGL){ console.warn('BMapGL 未加载'); return; }
  map = new BMapGL.Map('bmap');
  const initPt = new BMapGL.Point(116.404, 39.915);
  map.centerAndZoom(initPt, 18);
  try{ map.disableScrollWheelZoom(); }catch{}
    // 强制 2D 视图
    try{
      map.setHeading?.(0);
      map.setTilt?.(0);
      map.disableRotate?.();
      map.disableTilt?.();
    }catch{}

    // 添加定位控件（停靠右上角），并尝试自动定位到当前位置（zoom=18）
    try{
      if(BMapGL.LocationControl){
        const lc = new BMapGL.LocationControl({ anchor: window.BMAP_ANCHOR_TOP_RIGHT });

        try{
          lc.addEventListener?.('locationSuccess', function(e){
            try{ if(e?.point){ setCenter(e.point, 18); } }catch{}
          });
        }catch{}
        map.addControl(lc);
      }
    }catch{}
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // 自定义滚轮整级缩放：每次滚轮事件仅变更 1 级，锁定或选择中不响应
    mapDiv.addEventListener('wheel', (e)=>{
      try{
        if(!map) return; 
        // 锁定或正在框选时禁用缩放
        if(locked || selecting){ e.preventDefault(); return; }
    const current = map.getZoom?.() || 18;
        const step = (e.deltaY < 0) ? 1 : -1; // 向上滚=放大，向下=缩小
  const target = Math.min(19, Math.max(18, current + step));
        if(target !== current){ map.setZoom?.(target); }
        e.preventDefault();
      }catch{}
    }, { passive:false });

    // 恢复上次选取
    try{
      let raw = localStorage.getItem('mapSelect.last');
      if(!raw) raw = sessionStorage.getItem('mapSelect.last');
      if(raw){
        const info = JSON.parse(raw);
        if(info?.center){
          const pt = new BMapGL.Point(info.center.lng, info.center.lat);
          // 若有保存的 zoom，使用其 zoom（至少 18，最多 19）
          const z = Math.min(19, Math.max(18, info.zoom||19));
          map.centerAndZoom(pt, z);
          placeMarker(pt);
        }
        if(info?.selection){
          // 依据当前画布尺寸按比例还原
          const s = info.selection; const cw = selCanvas.width||1; const ch = selCanvas.height||1;
          // 存储时也保存了当时的画布宽高（兼容处理，如无则以当前尺寸直接使用）
          const sw = info.canvasWidth||cw; const sh = info.canvasHeight||ch;
          const kx = cw / sw; const ky = ch / sh;
          selection = { x: Math.round(s.x * kx), y: Math.round(s.y * ky), w: Math.round(s.w * kx), h: Math.round(s.h * ky) };
          redrawSelection();
          // 若存在选区，默认锁定地图，防止拖动缩放
          lockMap();
          selCanvas.classList.add('sel-locked');
          hasSavedSelection = true;
        }
      }
    }catch{}
    // 初始化后更新确认按钮状态
    updateConfirmState();
  }

  function resizeCanvas(){
    const rect = mapDiv.getBoundingClientRect();
    selCanvas.width = Math.max(200, Math.floor(rect.width));
    selCanvas.height = Math.max(200, Math.floor(rect.height));
    redrawSelection();
    updateConfirmState();
  }

  function setCenter(pt, forceZoom){
    if(!map) return;
    // 若指定强制缩放，则使用之；否则以当前缩放为基准 +1
    const current = map.getZoom?.() || 18;
  const targetZoom = typeof forceZoom==='number' ? Math.min(19, Math.max(18, forceZoom)) : Math.min(19, Math.max(18, current + 1));
    map.centerAndZoom(pt, targetZoom);
    placeMarker(pt);
    // 重新定位视图时，解除锁定状态（用户主动搜索/随机会调用 setCenter）
    unlockMap();
  }

  function placeMarker(pt){
    if(marker) map.removeOverlay(marker);
    marker = new BMapGL.Marker(pt);
    map.addOverlay(marker);
  }

  // 搜索：使用 BMapGL.LocalSearch
  function doSearch(){
    const kw = (placeInput.value||'').trim();
    if(!kw){ placeInput.focus(); return; }
    try{
      const ls = new BMapGL.LocalSearch(map, {
        onSearchComplete: (res)=>{
          try {
            if(res && res.getPoi && typeof res.getPoi === 'function'){
              const poi = res.getPoi(0);
              if(poi && poi.point){ setCenter(poi.point, 19); return; }
            }
          } catch{}
        }
      });
      ls.search(kw);
    }catch(err){
      console.warn('LocalSearch失败', err);
    }
  }


  // 框选：强制正方形（像素空间）
  function startSelect(){
    selecting = true; selection = null; redrawSelection();
    // 允许覆盖层拦截事件与十字光标
    selCanvas.classList.add('sel-active');
    // 暂时禁用地图拖动
    try{ if(map && mapDraggingEnabled){ map.disableDragging(); mapDraggingEnabled=false; } }catch{}
    updateConfirmState();
  }

  function cancelSelect(){
    // 重置：清空选区与标记，恢复初始视图，并写入记忆点
    selecting = false; selection = null; redrawSelection();
    selCanvas.classList.remove('sel-active');
    selCanvas.classList.remove('sel-locked');
    // 恢复交互
    unlockMap();
    // 移除地图上的 marker
    try{ if(marker && map){ map.removeOverlay(marker); marker=null; } }catch{}
    // 恢复默认中心与缩放
    if(map){
      const initPt = new BMapGL.Point(116.404, 39.915);
      map.centerAndZoom(initPt, 18);
    }
    // 写入初始状态为记忆点（覆盖原有选择），确保重开页面也回到初始
    try{
  const info = { center: { lng: 116.404, lat: 39.915 }, zoom: 18, selection: null, canvasWidth: selCanvas.width, canvasHeight: selCanvas.height };
      const s = JSON.stringify(info);
      sessionStorage.setItem('mapSelect.last', s);
      localStorage.setItem('mapSelect.last', s);
    }catch{}
    updateConfirmState();
  }

  function redrawSelection(){
    const ctx = selCanvas.getContext('2d');
    ctx.clearRect(0,0,selCanvas.width,selCanvas.height);
    if(!selection) return;
    ctx.strokeStyle = '#1d4ed8';
    ctx.lineWidth = 2;
    ctx.strokeRect(selection.x+0.5, selection.y+0.5, selection.w, selection.h);
    ctx.fillStyle = 'rgba(37,99,235,0.12)';
    ctx.fillRect(selection.x, selection.y, selection.w, selection.h);
  }

  selCanvas.addEventListener('mousedown', (e)=>{
    if(!selecting) return;
    drawing = true;
    const r = selCanvas.getBoundingClientRect();
    anchor = { x: e.clientX - r.left, y: e.clientY - r.top };
    selection = { x: anchor.x, y: anchor.y, w: 0, h: 0 };
  });
  selCanvas.addEventListener('mousemove', (e)=>{
    if(!drawing) return;
    const r = selCanvas.getBoundingClientRect();
    const cx = e.clientX - r.left;
    const cy = e.clientY - r.top;
    let w = Math.abs(cx - anchor.x);
    let h = Math.abs(cy - anchor.y);
    const m = Math.max(w,h); w=h=m; // 强制正方形
    let x = anchor.x, y = anchor.y;
    if(cx < anchor.x) x = anchor.x - m;
    if(cy < anchor.y) y = anchor.y - m;
    // 边界裁剪
    x = Math.max(0, Math.min(x, selCanvas.width - m));
    y = Math.max(0, Math.min(y, selCanvas.height - m));
    selection = { x, y, w: m, h: m };
    redrawSelection();
    updateConfirmState();
  });
  selCanvas.addEventListener('mouseup', ()=>{
    drawing=false; /* 保留selection，结束选择模式 */ selecting=false;
    selCanvas.classList.remove('sel-active');
    // 选择结束，锁定地图
    lockMap();
    // 让覆盖层继续拦截，防止地图操作
    selCanvas.classList.add('sel-locked');
    updateConfirmState();
  });
  selCanvas.addEventListener('mouseleave', ()=>{ drawing=false; });

  // 按钮事件
  btnSearch?.addEventListener('click', doSearch);
  placeInput?.addEventListener('keydown', (e)=>{ if(e.key==='Enter') doSearch(); });
  btnSelectArea?.addEventListener('click', startSelect);
  btnCancel?.addEventListener('click', cancelSelect);

  btnConfirm?.addEventListener('click', ()=>{
    if(!map){ return; }
    if(!(selection && selection.w>0 && selection.h>0)){ return; }
  const center = map.getCenter();
  // 确保用于后端静态图请求的缩放级别是整数，且不低于18且不超过19，避免与静态图视图不一致导致裁剪偏移
  const zoom = Math.max(18, Math.min(19, Math.round(map.getZoom?.() || 19)));
    // 计算选区中心与经纬度边界，便于后端据此获取静态图像
    let selCenter=null, bounds=null;
    try{
      const tl = map.pixelToPoint(new BMapGL.Pixel(selection.x, selection.y));
      const br = map.pixelToPoint(new BMapGL.Pixel(selection.x+selection.w, selection.y+selection.h));
      const cc = map.pixelToPoint(new BMapGL.Pixel(selection.x+selection.w/2, selection.y+selection.h/2));
      selCenter = { lng: cc.lng, lat: cc.lat };
      // 规范化边界（sw: minLat,minLng; ne:maxLat,maxLng）
      const sw = { lng: Math.min(tl.lng, br.lng), lat: Math.min(tl.lat, br.lat) };
      const ne = { lng: Math.max(tl.lng, br.lng), lat: Math.max(tl.lat, br.lat) };
      bounds = { sw, ne };
    }catch{}
    const info = {
      center: { lng: center.lng, lat: center.lat },
      zoom,
      selection,
      canvasWidth: selCanvas.width,
      canvasHeight: selCanvas.height,
      selCenter,
      selSizePx: selection ? { w: selection.w, h: selection.h } : null,
      bounds
    };
    console.log('[MapSelect] confirm =>', info);
    // 存入 sessionStorage 和 localStorage，确保刷新与跨页保留
    try{
      const s = JSON.stringify(info);
      sessionStorage.setItem('mapSelect.last', s);
      localStorage.setItem('mapSelect.last', s);
      // 回显保存的数据（可选复制到剪贴板）
      try{ navigator.clipboard?.writeText(s).catch(()=>{}); }catch{}
    }catch{}
    // 保持地图锁定
    lockMap();
    selCanvas.classList.add('sel-locked');
  });

  // 初始化地图
  (function wait(){ if(window.BMapGL){ initMap(); } else { setTimeout(wait, 200); } })();

  // 全面禁用地图交互
  function lockMap(){
    if(!map) return; locked = true;
    try{
      map.disableDragging(); mapDraggingEnabled=false;
      map.disableScrollWheelZoom();
      map.disableDoubleClickZoom();
      map.disableContinuousZoom?.();
      map.disablePinchToZoom?.();
      map.disableTilt?.();
      map.disableRotate?.();
      map.disableInertialDragging?.();
      map.disableKeyboard?.();
    }catch{}
  }
  function unlockMap(){
    if(!map) return; locked = false;
    try{
      map.enableDragging(); mapDraggingEnabled=true;
      // 滚轮整级缩放
      map.enableDoubleClickZoom();
      map.enableContinuousZoom?.();
      map.enablePinchToZoom?.();
      // 保持2D视图
      map.disableTilt?.();
      map.disableRotate?.();
      map.enableInertialDragging?.();
      map.enableKeyboard?.();
    }catch{}
    selCanvas.classList.remove('sel-locked');
  }
})();
