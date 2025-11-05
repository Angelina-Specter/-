// 无人机避障：读取地图处理的栅格，执行算法并渲染路径
(function(){
  const canvas = document.getElementById('uavGrid');
  const ctx = canvas.getContext('2d');
  const runBtn = document.getElementById('runBtn');
  const clearBtn = document.getElementById('clearBtn');
  const exportBtn = document.getElementById('exportBtn');
  const algoChecks = document.querySelectorAll('.algoCheck');
  const enableSafe = document.getElementById('enableSafe');

  let grid = null; let start=null; let end=null; let size=20;
  let paths = {}; // {algo: [{r,c}...]}
  let gridTs = null; // 来源栅格的时间戳，用于判断是否要清空旧路径

  function loadFromSession(){
    try{
      let raw = sessionStorage.getItem('process.grid');
      if(!raw) raw = localStorage.getItem('process.grid');
      if(!raw) return false;
      const obj = JSON.parse(raw);
      if(!obj || !obj.grid) return false;
      const prevSize = size;
      grid = obj.grid; size = obj.size || grid.length; start = obj.start || null; end = obj.end || null; gridTs = obj.ts || null;
      // 当尺寸变化时，清空旧路径
      if(prevSize !== size){ paths = {}; }
      draw();
      return true;
    }catch{ return false; }
  }

  window.addEventListener('storage', (e)=>{
    if(e.key === 'process.grid'){ loadFromSession(); }
  });

  function draw(){
    if(!grid){ ctx.clearRect(0,0,canvas.width,canvas.height); return; }
    const n = grid.length; const cell = canvas.width / n;
    ctx.clearRect(0,0,canvas.width,canvas.height);
    for(let r=0;r<n;r++){
      for(let c=0;c<n;c++){
        ctx.fillStyle = grid[r][c]===1 ? '#1f2937' : '#ffffff';
        ctx.fillRect(c*cell, r*cell, cell, cell);
      }
    }
    ctx.strokeStyle='#1f2937'; ctx.lineWidth=1;
    for(let i=0;i<=n;i++){
      const p = Math.round(i*cell)+0.5;
      ctx.beginPath(); ctx.moveTo(0,p); ctx.lineTo(canvas.width,p); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(p,0); ctx.lineTo(p,canvas.height); ctx.stroke();
    }
    ctx.beginPath();
    ctx.rect(0.5, 0.5, canvas.width - 1, canvas.height - 1);
    ctx.stroke();
    // start/end
    if(start){ ctx.strokeStyle='#22c55e'; ctx.lineWidth=2; ctx.strokeRect(start.c*cell+1,start.r*cell+1,cell-2,cell-2); }
    if(end){ ctx.strokeStyle='#ef4444'; ctx.lineWidth=2; ctx.strokeRect(end.c*cell+1,end.r*cell+1,cell-2,cell-2); }
    // paths
  const colors = { dijkstra:'#2563eb', astar:'#ff7f0e' };
    Object.entries(paths).forEach(([algo, p])=>{
      if(!p||p.length===0) return; ctx.strokeStyle=colors[algo]||'#e2276fff'; ctx.lineWidth=3; ctx.lineJoin='round'; ctx.lineCap='round';
      ctx.beginPath(); p.forEach((pt,i)=>{ const x=(pt.c+0.5)*cell; const y=(pt.r+0.5)*cell; if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y); }); ctx.stroke();
    });
  }

  function persistConfig(){
    try{
      const config = {
        algo: [...algoChecks].map(cb=>({k:cb.value, on: cb.checked})),
        safe: !!(enableSafe && enableSafe.checked),
        
        paths,
        gridTs
      };
      const s = JSON.stringify(config);
      localStorage.setItem('algo.uav.config', s);
      sessionStorage.setItem('algo.uav.config', s);
    }catch{}
  }

  function restoreConfig(){
    try{
      let raw = localStorage.getItem('algo.uav.config');
      if(!raw) raw = sessionStorage.getItem('algo.uav.config');
      if(!raw) return;
      const cfg = JSON.parse(raw);
      if(cfg?.algo){
        const map = new Map(cfg.algo.map(x=>[x.k, x.on]));
        [...algoChecks].forEach(cb=>{ if(map.has(cb.value)) cb.checked = !!map.get(cb.value); });
      }
      if(enableSafe && typeof cfg.safe==='boolean') enableSafe.checked = cfg.safe;
      
      // 仅当 gridTs 一致时恢复路径
      if(cfg.paths && cfg.gridTs && gridTs && cfg.gridTs===gridTs){ paths = cfg.paths; }
      else { paths = {}; }
      draw();
    }catch{}
  }

  async function solveBackend(algo){
    const payload={
      algo,
      grid,
      start: { r:start.r, c:start.c },
      end: { r:end.r, c:end.c },
      safe: !!(enableSafe && enableSafe.checked)
    };
    try{
      const resp = await fetch('/api/solve', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      const data = await resp.json();
      if(!data?.ok || !Array.isArray(data.triplets)) return null;
      const dirMap = {1:[0,1], 2:[1,0], 3:[0,-1], 4:[-1,0]};
      const trips = data.triplets;
      if(trips.length===0) return null;
      const out=[];
      let curR = trips[0][0], curC = trips[0][1];
      out.push({r:curR, c:curC});
      for(const t of trips){
        const d = t[2];
        const delta = dirMap[d]; if(!delta) continue;
        curR += delta[0]; curC += delta[1];
        out.push({r:curR, c:curC});
      }
      return out;
    }catch(e){
      console.warn('solve backend failed', e);
      return null;
    }
  }

  function enforceSingleAlgo(changed){
    const checks = [...algoChecks];
    if (changed && changed.checked){
      // 打开一个时，关闭其他
      checks.forEach(cb=>{ if(cb!==changed) cb.checked = false; });
    } else {
      // 保证至少一个开启：如果全部关闭，则默认开启第一个
      if (!checks.some(cb=>cb.checked) && checks[0]) checks[0].checked = true;
    }
    persistConfig();
  }

  ;[...algoChecks].forEach(cb=>{
    cb.addEventListener('change', ()=> enforceSingleAlgo(cb));
  });

  runBtn?.addEventListener('click', async ()=>{
    if(!grid){ alert('未读取到栅格'); return; }
    if(!start||!end){ alert('请设置起点和终点'); return; }
    paths={};
    const selected=[...algoChecks].filter(cb=>cb.checked).map(cb=>cb.value);
    // 在互斥模式下 selected 最多一个，此处容错：若为空则自动启用第一个
    if(selected.length===0){
      const first=[...algoChecks][0]; if(first){ first.checked=true; selected.push(first.value); persistConfig(); }
      else { alert('未找到任何算法选项'); return; }
    }
    for(const algo of selected){
      if(algo==='dijkstra' || algo==='astar'){
        const p = await solveBackend(algo);
        if(p) paths[algo]=p;
      }
    }
    // 若所有选中的算法都未得到路径，则弹窗提示
    if(Object.keys(paths).length === 0){
      alert('未找到可行通路，请尝试调整起点或终点位置');
    }
    draw();
    persistConfig();
  });

  clearBtn?.addEventListener('click', ()=>{ paths={}; draw(); persistConfig(); });

  exportBtn?.addEventListener('click', ()=>{
    const a=document.createElement('a');
    a.href = canvas.toDataURL('image/png');
    a.download = 'uav-path.png';
    a.click();
  });

  // 初始加载
  if(!loadFromSession()){
    loadFromSession();
  }
  restoreConfig();

  // 监听配置变更
  ;[...algoChecks].forEach(cb=>cb.addEventListener('change', persistConfig));
  enableSafe?.addEventListener('change', persistConfig);
  
})();