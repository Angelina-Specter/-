// 侧边栏导航：高亮当前页面、悬停样式通过 CSS，点击跳转默认行为
(function(){
  const current = document.body.getAttribute('data-page') || '';
  const links = document.querySelectorAll('.nav-link');
  const LS_KEY_PREFIX = 'navGroup:';

  const setGroupState = (key, isOpen) => {
    try { localStorage.setItem(LS_KEY_PREFIX + key, isOpen ? 'open' : 'closed'); } catch {}
  };
  const getGroupState = (key) => {
    try {
      const v = localStorage.getItem(LS_KEY_PREFIX + key);
      if (v === 'open') return true;
      if (v === 'closed') return false;
    } catch {}
    return null; // 未记忆
  };

  // 高亮当前链接，并设置标题
  links.forEach(a => {
    if (a.dataset.page === current) {
      a.classList.add('active');
      let text = a.querySelector('.text')?.textContent || '';
      // 若为分组子项，则展示为“分组名/子项名”
      const sublist = a.closest('.nav-sublist');
      if (sublist) {
        const groupKey = sublist.getAttribute('data-parent');
        const groupBtn = document.querySelector(`.nav-group[data-group="${groupKey}"]`);
        const groupText = groupBtn?.querySelector('.text')?.textContent || '';
        if (groupText) text = `${groupText}/${text}`;
      }
      const h1 = document.querySelector('.page-header h1');
      if (h1 && text) h1.textContent = text;
    }
  });

  // 折叠组逻辑：默认关闭；当当前页面属于该组子项时自动展开
  const groups = document.querySelectorAll('.nav-group');
  groups.forEach(btn => {
    const key = btn.dataset.group;
    const sub = document.querySelector(`.nav-sublist[data-parent="${key}"]`);
    if(!sub) return;

    // 判断是否应展开：当前页面是否在子列表中
    const isChildPage = Array.from(sub.querySelectorAll('a.nav-link')).some(a => a.dataset.page === current);

    // 规则：
    // - 若在子页面或为组页面，则强制展开（不覆盖记忆，仅展示层面）
    // - 否则按记忆状态展示；无记忆则默认收起
    if (isChildPage || current === key) {
      sub.classList.add('open');
      btn.classList.add('active');
    } else {
      const remembered = getGroupState(key);
      const open = remembered === true; // null 或 false 均视为收起
      sub.classList.toggle('open', open);
      btn.classList.toggle('active', open);
    }

    // 点击切换展开/收起（点击不跳转）
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const isOpen = sub.classList.toggle('open');
      btn.classList.toggle('active', isOpen);
      setGroupState(key, isOpen);
    });
  });
})();
