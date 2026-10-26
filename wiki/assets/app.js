const menu = document.querySelector('.menu-toggle');
menu.addEventListener('click', () => {
  const open = menu.getAttribute('aria-expanded') !== 'true';
  menu.setAttribute('aria-expanded', String(open));
  menu.setAttribute('aria-label', open ? '关闭目录' : '打开目录');
  document.body.classList.toggle('menu-open', open);
});
const dialog = document.querySelector('#search-dialog');
const input = document.querySelector('#search-input');
const results = document.querySelector('#search-results');
const hint = document.querySelector('.search-hint');
let indexPromise;
let index = [];
let searchReady = false;
const normalize = value => value.toLowerCase().replace(/wi[\s-]?fi/g, 'wifi').replace(/\s+/g, ' ').trim();
async function openSearch() {
  if (!dialog.open) dialog.showModal();
  input.focus();
  if (!indexPromise) indexPromise = fetch('/search-index.json').then(r => {
    if (!r.ok) throw Error('index');
    return r.json();
  }).catch(() => { indexPromise = null; throw Error('index'); });
  try {
    index = await indexPromise;
    searchReady = true;
    runSearch();
  } catch {
    hint.textContent = '搜索暂时无法加载，请从左侧目录查阅，或稍后重新打开搜索。';
  }
}
function runSearch() {
  results.replaceChildren();
  const query = normalize(input.value);
  if (!searchReady) return;
  if (!query) {
    hint.textContent = '输入关键词搜索全文，例如 Wi-Fi、5M、485、浏览器。';
    return;
  }
  const words = query.split(' ');
  const found = index.map(item => {
    const label = normalize(item.title + ' ' + item.heading);
    const all = label + ' ' + normalize(item.text);
    const score = words.every(w => all.includes(w)) ? words.reduce((s, w) => s + (label.includes(w) ? 10 : 1), 0) : 0;
    return { ...item, score };
  }).filter(item => item.score).sort((a, b) => b.score - a.score).slice(0, 15);
  hint.textContent = found.length ? `显示 ${found.length} 个相关段落 · Tab 选择，Enter 打开` : '没有找到结果，试试更短的关键词。';
  for (const item of found) {
    const a = document.createElement('a');
    a.href = item.url;
    const title = document.createElement('strong');
    title.textContent = item.title + ' / ' + item.heading;
    const p = document.createElement('p');
    const pos = Math.max(0, normalize(item.text).indexOf(words[0]) - 30);
    p.textContent = item.text.replace(/[#*`]/g, '').slice(pos, pos + 150).replace(/\n/g, ' ') + '…';
    a.append(title, p);
    results.append(a);
  }
}
document.querySelector('.search-trigger').addEventListener('click', openSearch);
document.querySelector('.search-close').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', e => {
  const rect = dialog.getBoundingClientRect();
  if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) dialog.close();
});
input.addEventListener('input', runSearch);
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    openSearch();
  }
  if (e.key === 'Escape' && document.body.classList.contains('menu-open')) {
    menu.click();
    menu.focus();
  }
});
for (const pre of document.querySelectorAll('.prose pre')) {
  const button = document.createElement('button');
  button.className = 'copy-button';
  button.type = 'button';
  button.textContent = '复制';
  button.setAttribute('aria-label', '复制此代码块');
  const code = pre.querySelector('code').textContent;
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(code);
      button.textContent = '已复制';
      document.querySelector('#copy-status').textContent = '代码已复制；执行前请阅读适用条件。';
      setTimeout(() => {
        button.textContent = '复制';
        document.querySelector('#copy-status').textContent = '';
      }, 2500);
    } catch {
      button.textContent = '请手动选择复制';
    }
  });
  pre.append(button);
}
const tocLinks = [...document.querySelectorAll('.toc a')];
if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(entries => {
    const visible = entries.filter(e => e.isIntersecting);
    if (!visible.length) return;
    const id = visible[0].target.id;
    for (const a of tocLinks) a.classList.toggle('current', decodeURIComponent(a.hash.slice(1)) === id);
  }, { rootMargin: '-70px 0px -65% 0px' });
  document.querySelectorAll('h2[id],section[id]').forEach(el => observer.observe(el));
}
