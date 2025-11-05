(function(){
  const canvas = document.getElementById('extGrid');
  const ctx = canvas.getContext('2d');
  const runBtn = document.getElementById('runBtn');
  const clearBtn = document.getElementById('clearBtn');
  const exportBtn = document.getElementById('exportBtn');

  let grid = null; let start=null; let end=null; let size=20;
  let path = null; 
  let gridTs = null;

  function loadFromSession(){
    try{
      let raw = sessionStorage.getItem('process.grid');
      if(!raw) raw = localStorage.getItem('process.grid');
      if(!raw) return false;
      const obj = JSON.parse(raw);
      if(!obj || !obj.grid) return false;
      const prevSize = size;
      grid = obj.grid; size = obj.size || grid.length; start = obj.start || null; end = obj.end || null; gridTs = obj.ts || null;
      if(prevSize !== size){ path = null; }
      draw();
      return true;
    }catch{ return false; }
  }

  window.addEventListener('storage', (e)=>{ if(e.key==='process.grid'){ loadFromSession(); } });

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
    ctx.beginPath(); ctx.rect(0.5,0.5,canvas.width-1,canvas.height-1); ctx.stroke();

    if(start){ ctx.strokeStyle='#22c55e'; ctx.lineWidth=2; ctx.strokeRect(start.c*cell+1,start.r*cell+1,cell-2,cell-2); }
    if(end){ ctx.strokeStyle='#ef4444'; ctx.lineWidth=2; ctx.strokeRect(end.c*cell+1,end.r*cell+1,cell-2,cell-2); }

    if(path && path.length>1){
      ctx.strokeStyle = '#10b981';
      ctx.lineWidth = 3; ctx.lineJoin='round'; ctx.lineCap='round';
      ctx.beginPath();
      path.forEach((pt,i)=>{ const x=(pt.c+0.5)*cell; const y=(pt.r+0.5)*cell; if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y); });
      ctx.stroke();
    }
  }

  async function solveExtended(){
    const payload={
      grid,
      start: { r:start.r, c:start.c },
      end: { r:end.r, c:end.c },
      radius: 2
    };
    try{
      const resp = await fetch('/api/solve-extended', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      const data = await resp.json();
      if(!data?.ok || !Array.isArray(data.triplets)) return null;
      // Decode triplets to path
      const DIRS_24 = [];
      for (let dr = -2; dr <= 2; dr++) {
        for (let dc = -2; dc <= 2; dc++) {
          if (dr === 0 && dc === 0) continue;
          DIRS_24.push([dr, dc]);
        }
      }
      const dirMap = {};
      for (let i = 0; i < DIRS_24.length; i++) {
        dirMap[i+1] = DIRS_24[i];
      }
      const trips = data.triplets; if(trips.length===0) return null;
      // Build node list from triplets — do NOT expand into unit steps; draw straight segments between nodes.
      const nodes = [];
      let curR = trips[0][0], curC = trips[0][1];
      nodes.push({r: curR, c: curC});
      for(const t of trips){
        const d = t[2]|0; const delta = dirMap[d]; if(!delta) continue;
        const targetR = curR + delta[0]; const targetC = curC + delta[1];
        nodes.push({r: targetR, c: targetC});
        curR = targetR; curC = targetC;
      }
      return nodes;
    }catch(e){ console.warn('solve-extended failed', e); return null; }
  }

  runBtn?.addEventListener('click', async ()=>{
    if(!grid){ alert('未读取到栅格'); return; }
    if(!start||!end){ alert('请设置起点和终点'); return; }
    path = await solveExtended();
    draw();
  });

  clearBtn?.addEventListener('click', ()=>{ path=null; draw(); });

  exportBtn?.addEventListener('click', ()=>{
    const a=document.createElement('a'); a.href=canvas.toDataURL('image/png'); a.download='extended-path.png'; a.click();
  });

  // 初始
  if(!loadFromSession()){ loadFromSession(); }
  draw();
})();
