// 地图处理模块：左侧操作区 + 右侧方形栅格
(function(){
  const sizeSel = document.getElementById('gridSizeSel');
  const strategySel = document.getElementById('obstacleStrategy');
  const confirmSizeBtn = document.getElementById('confirmSize');
  const applyBtn = document.getElementById('applyStrategy');
  const toggleEditBtn = document.getElementById('toggleEdit');
  const pickStartBtn = document.getElementById('pickStart');
  const pickEndBtn = document.getElementById('pickEnd');
  const resetBtn = document.getElementById('resetAll');
  const canvas = document.getElementById('gridStage');
  const ctx = canvas.getContext('2d');

  let size = parseInt(sizeSel?.value||'20');
  let grid = null;
  let editMode = false;
  let picking = null;
  let start = null, end = null;

  // 生成栅格
  function makeGrid(n, fill=0){ return Array.from({length:n},()=>Array(n).fill(fill)); }

  function persist(){
    try{
      const payload = { size: grid.length, grid, start, end, ts: Date.now() };
      const s = JSON.stringify(payload);
      sessionStorage.setItem('process.grid', s);
      localStorage.setItem('process.grid', s);
    }catch{}
  }

  //栅格绘制
  function draw(){
    const n = grid.length;
    ctx.clearRect(0,0,canvas.width,canvas.height);
    const cell = canvas.width / n;
    for(let r=0;r<n;r++){
      for(let c=0;c<n;c++){
        ctx.fillStyle = grid[r][c]===1 ? '#1f2937' : '#ffffff';
        ctx.fillRect(c*cell, r*cell, cell, cell);
      }
    }
    ctx.strokeStyle = '#1f2937';
    ctx.lineWidth = 1;
    for(let i=0;i<=n;i++){
      const p = Math.round(i*cell)+0.5;
      ctx.beginPath(); ctx.moveTo(0,p); ctx.lineTo(canvas.width,p); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(p,0); ctx.lineTo(p,canvas.height); ctx.stroke();
    }
    ctx.beginPath();
    ctx.rect(0.5, 0.5, canvas.width - 1, canvas.height - 1);
    ctx.stroke();
    if(start){ ctx.strokeStyle='#00fa5cff'; ctx.lineWidth=2; ctx.strokeRect(start.c*cell+1, start.r*cell+1, cell-2, cell-2); }
    if(end){ ctx.strokeStyle='#ef4444'; ctx.lineWidth=2; ctx.strokeRect(end.c*cell+1, end.r*cell+1, cell-2, cell-2); }
  }

  // 从存储恢复栅格
  (function restore(){
    try{
      let raw = sessionStorage.getItem('process.grid');
      if(!raw) raw = localStorage.getItem('process.grid');
      if(raw){
        const data = JSON.parse(raw);
        if(data?.grid && Array.isArray(data.grid)){
          grid = data.grid; start = data.start||null; end = data.end||null; size = data.size||grid.length;
          if(sizeSel) sizeSel.value = String(size);
          draw();
          return;
        }
      }
    }catch{}
    grid = makeGrid(size,0); start=end=null; draw(); persist();
  })();

  // 应用选中策略生成栅格
  function applyStrategy(){
    size = parseInt(sizeSel.value);
    const n = size;
    const s = strategySel.value;
    if(s==='random'){
      grid = makeGrid(n, 0);
      const params = { size: n };
      fetch('/api/simulate-collapse', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(params) })
        .then(r=>r.json())
        .then(data=>{
          if(data && data.ok && Array.isArray(data.grid)){
            grid = data.grid; start=end=null; draw(); persist();
          }else{alert('坍塌模拟失败：'+(data?.error||'未知错误'));}
        })
        .catch(err=>{ alert('坍塌模拟请求失败：'+err); });
      return;
    } else if(s==='map'){
      grid = makeGrid(n, 0);
      try{
        let raw = sessionStorage.getItem('mapSelect.last');
        if(!raw) raw = localStorage.getItem('mapSelect.last');
        const info = raw ? JSON.parse(raw) : null;
        if(!info || !info.selection){ alert('未找到有效的选区，请先在“地图选取”框选并确认'); draw(); return; }
        const payload = {
          center: info.center,
          zoom: info.zoom,
          canvasWidth: info.canvasWidth,
          canvasHeight: info.canvasHeight,
          selection: info.selection,
          selCenter: info.selCenter || null,
          selSizePx: info.selSizePx || (info.selection? { w: info.selection.w, h: info.selection.h } : null),
          size: n
        };
        fetch('/api/rasterize', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) })
          .then(r=>r.json())
          .then(data=>{
            if(data && data.ok && Array.isArray(data.grid)){
              grid = data.grid; start=end=null; draw(); persist();
            }else{
              alert('栅格化失败：'+(data?.error||'未知错误'));
            }
          })
          .catch(err=>{ alert('栅格化请求失败：'+err); });
        return;
      }catch(err){ console.warn('map rasterize error', err); }
    } else if(s==='import'){
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.json,application/json';
      input.onchange = (e)=>{
        const file = e.target.files && e.target.files[0];
        if(!file){ return; }
        const reader = new FileReader();
        reader.onload = ()=>{
          try{
            const txt = String(reader.result||'');
            const arr = JSON.parse(txt);
            if(!Array.isArray(arr)) throw new Error('not array');
            // 按文件行列自动确定尺寸：n = max(rows, cols)
            const rows = arr.length;
            let cols = 0; for(const r of arr){ if(Array.isArray(r)) cols = Math.max(cols, r.length); }
            const n = Math.max(rows, cols);
            // 生成 n×n，默认黑色(1)填充，再将文件内容覆写到对应位置（超出裁剪，不足保留黑色）
            const g = Array.from({length:n},()=>Array(n).fill(1));
            for(let r=0;r<n;r++){
              const row = Array.isArray(arr[r]) ? arr[r] : null;
              if(!row) continue;
              for(let c=0;c<n;c++){
                const v = row[c];
                if(v===0 || v===1){ g[r][c] = v; }
                else if(v===false){ g[r][c] = 0; }
                else if(v===true){ g[r][c] = 1; }
              }
            }
            // 同步下拉 size（若无该选项则临时追加）
            if(sizeSel){
              const nv = String(n);
              const has = Array.from(sizeSel.options||[]).some(o=>o.value===nv);
              if(!has){ const opt = document.createElement('option'); opt.value = nv; opt.textContent = nv; sizeSel.appendChild(opt); }
              sizeSel.value = nv;
            }
            grid = g; start = null; end = null; draw(); persist();
          }catch(err){ alert('导入失败：JSON 无法解析或格式不正确'); }
        };
        reader.onerror = ()=>{ alert('读取文件失败'); };
        reader.readAsText(file, 'utf-8');
      };
      input.click();
      return;
    }
    start=null; end=null;
    draw();
    persist();
  }

  function canvasToCell(x,y){
    const n = grid.length; const cell = canvas.width / n;
    const c = Math.floor(x / cell); const r = Math.floor(y / cell);
    if(r<0||c<0||r>=n||c>=n) return null;
    return {r,c};
  }

  canvas.addEventListener('click', (e)=>{
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left, y = e.clientY - rect.top;
    const cell = canvasToCell(x,y); if(!cell) return;
    if(editMode){
      grid[cell.r][cell.c] = grid[cell.r][cell.c] ? 0 : 1; draw(); persist(); return;
    }
    if(picking==='start'){
      if(grid[cell.r][cell.c]!==0){ alert('起点不合法'); return; }
      start = cell; picking=null; draw(); persist(); return;
    }
    if(picking==='end'){
      if(grid[cell.r][cell.c]!==0){ alert('终点不合法'); return; }
      end = cell; picking=null; draw(); persist(); return;
    }
  });

  // 事件绑定
  applyBtn?.addEventListener('click', applyStrategy);
  confirmSizeBtn?.addEventListener('click', ()=>{ grid = makeGrid(parseInt(sizeSel.value||'20'),0); start=end=null; draw(); persist(); });
  sizeSel?.addEventListener('change', ()=>{ /* 同步 size 但不立即重建，等确认 */ });
  toggleEditBtn?.addEventListener('click', ()=>{ editMode = !editMode; toggleEditBtn.classList.toggle('active', editMode); toggleEditBtn.textContent = editMode? '编辑障碍(开启)' : '编辑障碍'; });
  pickStartBtn?.addEventListener('click', ()=>{ picking = 'start'; });
  pickEndBtn?.addEventListener('click', ()=>{ picking = 'end'; });
  resetBtn?.addEventListener('click', ()=>{ grid = makeGrid(parseInt(sizeSel.value||'20'),0); start=end=null; draw(); persist(); });
})();