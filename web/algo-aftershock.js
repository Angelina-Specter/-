// 余震模拟前端：调用 /api/dynamic-step 按 tick 演进 + 重规划 + 迈一步
(function(){
  const canvas = document.getElementById('simGrid');
  const ctx = canvas?.getContext('2d');
  const API_BASE = (typeof location !== 'undefined' && /^https?:/i.test(location.origin)) ? '' : 'http://localhost:9999';
  const intervalTicksInput = document.getElementById('intervalTicks');
  const intervalTicksVal = document.getElementById('intervalTicksVal');
  const severityInput = document.getElementById('severity');
  const severityVal = document.getElementById('severityVal');
  const stepDelayInput = document.getElementById('stepDelay');
  const stepDelayVal = document.getElementById('stepDelayVal');
  const startBtn = document.getElementById('startBtn');
  const pauseBtn = document.getElementById('pauseBtn');
  const resetBtn = document.getElementById('resetBtn');
  const statusLine = document.getElementById('statusLine');

  // 仓库：读取地图处理页给的 grid/start/end
  function loadFromProcess(){
    try{
      let raw = sessionStorage.getItem('process.grid');
      if(!raw) raw = localStorage.getItem('process.grid');
      if(!raw) return null;
      const obj = JSON.parse(raw);
      if(!obj || !obj.grid || !Array.isArray(obj.grid)) return null;
      return obj; // {grid,start,end,size}
    }catch{ return null; }
  }

  // 运行状态
  let base = loadFromProcess();
  let grid = base?.grid || null;
  let start = base?.start || null;
  let goal = base?.end || null;
  if(!grid){
    // 初始化默认网格，避免空白
    grid = Array.from({length:20},()=>Array(20).fill(0));
  }
  if(!start) start = { r: 0, c: 0 };
  if(!goal) goal = { r: grid.length-1, c: grid[0].length-1 };

  let agent = { r: start.r, c: start.c };
  let trail = [ { r: start.r, c: start.c } ]; // 从起点到当前点的实时轨迹
  let aftershockState = null; // 后端返回的 state
  let timer = null; // 主循环计时器
  let running = false;
  let inflight = null; // 当前在飞中的请求
  let aborter = null;  // AbortController

  // 绘制
  function draw(){
    if(!ctx || !grid){ return; }
    const n = grid.length; const m = grid[0].length; const cell = canvas.width / n;
    ctx.clearRect(0,0,canvas.width,canvas.height);
    // 背景
    ctx.fillStyle = '#ffffff'; ctx.fillRect(0,0,canvas.width,canvas.height);
    // 障碍
    for(let r=0;r<n;r++){
      for(let c=0;c<m;c++){
        if(grid[r][c]===1){
          ctx.fillStyle = '#1f2937';
          ctx.fillRect(c*cell, r*cell, cell, cell);
        }
      }
    }
    // 网格线
    ctx.strokeStyle = '#1f2937'; ctx.lineWidth = 1;
    for(let i=0;i<=n;i++){
      const p = Math.round(i*cell)+0.5;
      ctx.beginPath(); ctx.moveTo(0,p); ctx.lineTo(canvas.width,p); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(p,0); ctx.lineTo(p,canvas.height); ctx.stroke();
    }
    ctx.beginPath(); ctx.rect(0.5,0.5,canvas.width-1,canvas.height-1); ctx.stroke();

    // 起终点
    if(start){ ctx.strokeStyle='#22c55e'; ctx.lineWidth=2; ctx.strokeRect(start.c*cell+1,start.r*cell+1,cell-2,cell-2); }
    if(goal){ ctx.strokeStyle='#ef4444'; ctx.lineWidth=2; ctx.strokeRect(goal.c*cell+1,goal.r*cell+1,cell-2,cell-2); }

    // 轨迹：从起点到当前点
    if(trail && trail.length > 1){
      ctx.strokeStyle = '#06b6d4';
      ctx.lineWidth = 3; ctx.lineJoin='round'; ctx.lineCap='round';
      ctx.beginPath();
      trail.forEach((pt,i)=>{
        const x = (pt.c + 0.5) * cell; const y = (pt.r + 0.5) * cell;
        if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
      });
      ctx.stroke();
    }

    // 代理(小圆点)
    if(agent){
      ctx.fillStyle = '#05b1f0ff';
      ctx.beginPath(); ctx.arc((agent.c+0.5)*cell, (agent.r+0.5)*cell, Math.max(3, cell*0.25), 0, Math.PI*2); ctx.fill();
    }
  }

  function setStatus(text){ if(statusLine) statusLine.textContent = '状态：' + text; }

  function getParams(){
    // 前端滑动条表达：每 10 tick 生成 N 次（N=1..5）
    const N = parseInt(intervalTicksInput?.value||'2');
    // 转换为后端 intervalTicks（平均间隔 ~ 10/N）
    const intervalTicks = Math.max(1, Math.round(10 / Math.max(1, Math.min(5, N))));
    const severity = Math.max(0, Math.min(1, (parseInt(severityInput?.value||'20')||0)/100));
    const delay = parseInt(stepDelayInput?.value||'200');
    const algo = 'astar';
    return { intervalTicks, severity, delay, algo, N };
  }

  function syncIndicators(){
    const { N, severity, delay } = getParams();
    // 显示为“每10tick生成 N 次”中的 N
    if(intervalTicksVal) intervalTicksVal.textContent = String(N);
    if(severityVal) severityVal.textContent = severity.toFixed(2);
    if(stepDelayVal) stepDelayVal.textContent = String(delay);
  }

  // 一步
  async function stepOnce(){
    const { intervalTicks, severity, algo, N } = getParams();
    try{
      const payload = {
        grid,
        start,
        goal,
        agent,
        intervalTicks,
        // 新语义参数，后端优先使用 freqPer10
        freqPer10: N,
        severity,
        algo,
        aftershockState,
        returnDelta: true
      };
      // 单飞中请求：如果上一个未完成，取消它
      if (aborter) { aborter.abort(); }
      aborter = new AbortController();
      inflight = fetch(`${API_BASE}/api/dynamic-step`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload), signal: aborter.signal });
      const resp = await inflight;
      const data = await resp.json();
      if(!data?.ok){ setStatus('后端返回错误'); return { done: true }; }
      if (data.changed && Array.isArray(data.changed)){
        // 增量更新本地网格
        for (const ch of data.changed){
          const r = ch.r|0, c = ch.c|0, v = ch.val|0;
          if (grid[r] && typeof grid[r][c] !== 'undefined') grid[r][c] = v;
        }
      } else if (data.grid) {
        // 兼容：服务端未开启增量时仍支持
        grid = data.grid;
      }
  aftershockState = data.aftershockState || aftershockState;
      if(data.start) start = data.start;
      if(data.goal) goal = data.goal;
      if(data.agent){
        const prev = agent; agent = data.agent;
        const last = trail[trail.length-1];
        if(!last || last.r !== agent.r || last.c !== agent.c){
          trail.push({ r: agent.r, c: agent.c });
        }
      }
      draw();
      if(data.done){ setStatus('到达终点'); return { done: true }; }
      if(data.reason){ setStatus('继续（'+data.reason+'）'); } else { setStatus('运行中'); }
      return { done: false };
    }catch(e){ console.error('dynamic-step request failed', e); setStatus('请求失败：'+(e?.message||e)); return { done: true }; }
  }

  function loop(){
    if(!running) return;
    const { delay } = getParams();
    stepOnce().then(({done})=>{
      if(!running) return;
      if(done){ running=false; timer=null; return; }
      timer = setTimeout(loop, delay);
    });
  }

  function reset(){
    const src = loadFromProcess();
    if(src && src.grid){ grid = src.grid; start = src.start||{r:0,c:0}; goal = src.end||{r:grid.length-1,c:grid[0].length-1}; }
    agent = { r: start.r, c: start.c };
    trail = [ { r: start.r, c: start.c } ];
    aftershockState = null;
    draw(); setStatus('已重置');
  }

  // 事件
  intervalTicksInput?.addEventListener('input', syncIndicators);
  severityInput?.addEventListener('input', syncIndicators);
  stepDelayInput?.addEventListener('input', syncIndicators);

  startBtn?.addEventListener('click', ()=>{
    if(running) return; running = true; setStatus('运行中'); loop();
  });
  pauseBtn?.addEventListener('click', ()=>{
    running = false; if(timer){ clearTimeout(timer); timer=null; } setStatus('已暂停');
    if (aborter) { try { aborter.abort(); } catch{} finally { aborter = null; inflight = null; } }
  });
  resetBtn?.addEventListener('click', ()=>{ running=false; if(timer){ clearTimeout(timer); timer=null; } reset(); });

  // 首次初始化
  syncIndicators();
  draw();
})();
