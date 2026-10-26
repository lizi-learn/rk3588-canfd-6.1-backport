#!/usr/bin/env python3
"""Generate a static Wiki from explicitly selected, public Markdown sources."""
import hashlib
import html
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'wiki'
OUT = HERE / 'dist'
SITE = json.loads((HERE / 'site.json').read_text())
PAGES = SITE['pages']
MAP = {p['source']: '/' + p['slug'] + '.html' for p in PAGES}
MD = MarkdownIt('commonmark', {'html': False}).enable('table')
E = html.escape

def slug(text):
    return re.sub(r'[^\w\-\u3400-\u9fff]+', '-', text.lower()).strip('-') or 'section'

def rewrite_links(tokens, source):
    for t in tokens:
        if t.type in ('link_open', 'image'):
            attr = 'href' if t.type == 'link_open' else 'src'
            href = t.attrGet(attr) or ''
            u = urlsplit(href)
            if not u.scheme and not u.netloc and u.path:
                path = (ROOT / source).parent / unquote(u.path)
                key = path.resolve().relative_to(ROOT).as_posix()
                target = MAP.get(key)
                if not target:
                    target = SITE['repository'] + ('/tree/main/' if path.is_dir() else '/blob/main/') + quote(key)
                t.attrSet(attr, target + ('#' + u.fragment if u.fragment else ''))
        if t.children:
            rewrite_links(t.children, source)

def article(page):
    text = (ROOT / page['source']).read_text()
    tokens = MD.parse(text)
    toc, counts, records = [], {}, []
    current = {'title': page['title'], 'heading': '概览', 'url': '/' + page['slug'] + '.html', 'text': ''}
    for i, t in enumerate(tokens):
        if t.type == 'heading_open':
            label = tokens[i+1].content
            stem = slug(label)
            counts[stem] = counts.get(stem, 0) + 1
            anchor = stem + ('-' + str(counts[stem]-1) if counts[stem] > 1 else '')
            t.attrSet('id', anchor)
            if t.tag == 'h2':
                if current['text']:
                    records.append(current)
                current = {'title': page['title'], 'heading': label, 'url': '/' + page['slug'] + '.html#' + anchor, 'text': ''}
                toc.append((anchor, label))
        if t.type == 'inline':
            current['text'] += ''.join(c.content if c.type in ('text', 'code_inline') else ' ' if c.type in ('softbreak', 'hardbreak') else '' for c in (t.children or [])) + '\n'
        elif t.type in ('fence', 'code_block'):
            current['text'] += t.content + '\n'
    if current['text']:
        records.append(current)
    rewrite_links(tokens, page['source'])
    return MD.renderer.render(tokens, MD.options, {}), toc, records

def nav(active):
    s = f'<a class="nav-home {"active" if active == "home" else ""}" href="/" {"aria-current=page" if active == "home" else ""}>手册首页</a>'
    for group in dict.fromkeys(p['group'] for p in PAGES):
        s += '<div class="nav-group"><p>' + E(group) + '</p>'
        for p in PAGES:
            if p['group'] == group:
                s += f'<a href="/{p["slug"]}.html" class="{"active" if active == p["slug"] else ""}" {"aria-current=page" if active == p["slug"] else ""}>{E(p["title"])}</a>'
        s += '</div>'
    return s

def shell(title, body, active='home', toc=None, source=None):
    toc_html = ''.join(f'<a href="#{E(a)}">{E(t)}</a>' for a,t in (toc or []))
    if not toc_html:
        toc_html = ('<a href="#read">开始阅读</a><a href="#results">实测摘要</a><a href="#questions">常见问题</a>'
                    if active == 'home' and source is None and title == '手册首页' else '<a href="#main">概览</a>')
    source_link = f'<a href="{SITE["repository"]}/blob/main/{source}">查看 / 编辑本文源文件 ↗</a>' if source else f'<a href="{SITE["repository"]}">查看 GitHub 源码 ↗</a>'
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} · YMBOT 5IO</title><meta name="description" content="YMBOT RK3588 开发板实机配置、CAN/RS485 验证、桌面与网络故障排查教学手册。">
<meta name="theme-color" content="#1145e6"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/style.css"><script defer src="/assets/app.js"></script></head>
<body><a class="skip" href="#main">跳到正文</a><header class="header"><a class="brand" href="/" aria-label="YMBOT 5IO 手册首页"><span class="brand-icon">Y</span><span>YMBOT <b>5IO</b><small>开发板系统优化</small></span></a>
<div class="header-actions"><button class="search-trigger" type="button" aria-haspopup="dialog"><span>⌕</span> 搜索手册 <kbd>Ctrl K</kbd></button><a class="github" href="{SITE['repository']}">GitHub ↗</a><button class="menu-toggle" aria-label="打开目录" aria-expanded="false" aria-controls="sidebar">☰</button></div></header>
<div class="layout"><aside class="sidebar" id="sidebar"><div class="edition"><span class="dot"></span> 实机调试手册 <span>v0.3.1</span></div><nav aria-label="手册目录">{nav(active)}</nav><div class="sidebar-note">适用 RK3588 / LBM5-DIBAN-V01A<br>Ubuntu 22.04 · Linux 6.1.172</div></aside>
<main id="main" class="main"><div class="breadcrumb">手册 / {E(title)}</div>{body}<footer><div>{source_link}</div><p>整理于 {SITE['updated']} · 实测范围见各篇正文<br>YMBOT 5IO · 与源码同步维护的静态手册</p></footer></main>
<aside class="toc" aria-label="本页目录"><p>本页内容</p>{toc_html}</aside></div>
<dialog id="search-dialog" aria-labelledby="search-title"><div class="search-top"><label id="search-title" for="search-input">搜索手册</label><button class="search-close" type="button" aria-label="关闭搜索">Esc</button></div><input id="search-input" type="search" autocomplete="off" placeholder="试试：两个 Wi-Fi、CAN 5M、浏览器" aria-controls="search-results"><p class="search-hint" aria-live="polite">输入关键词搜索全文；正文无需 JavaScript 也可阅读。</p><div id="search-results"></div></dialog>
<div id="copy-status" class="copy-status" role="status"></div></body></html>'''

def home():
    return '''<div class="hero"><div class="eyebrow">ENGINEERING FIELD NOTES / 实机经验</div><h1>把调试过程，<br>变成可复用的手册<span>。</span></h1><p class="hero-copy">YMBOT 5IO 开发板系统优化<br>从接手新机到独立验证，让每个结论都有操作、有依据、有边界。</p><div class="hero-tags"><span>RK3588</span><span>LBM5-DIBAN-V01A</span><span>Ubuntu 22.04</span></div><div class="hero-actions"><a class="primary" href="/start.html">从接手新机开始 <span>→</span></a><a class="text-link" href="/faq.html">按问题查阅 ↗</a></div><div class="hero-diagram" aria-hidden="true"><div class="chip">RK<span>3588</span></div><div class="bus-lines"><i></i><i></i><i></i></div><div class="ports"><span>CAN × 2</span><span>RS485 × 2</span><span>GNOME / X11</span></div><small>配置 → 验证 → 留档</small></div></div>
<section id="read"><div class="section-title"><span>01 / 开始阅读</span><h2>按工作顺序，走完一台设备</h2></div><div class="reading-grid"><a href="/start.html"><span class="step">01</span><h3>接手与一键配置 <span>↗</span></h3><p>联网、账户、桌面和远控。明确适用镜像与需要准备的组件。</p><span class="card-link">阅读操作单 →</span></a><a href="/interfaces.html"><span class="step">02</span><h3>接线与独立验证 <span>↗</span></h3><p>两路 CAN、UART4 / UART7。先核对针脚，再进行实际收发。</p><span class="card-link">查看接口说明 →</span></a><a href="/faq.html"><span class="step">03</span><h3>理解现象与原因 <span>↗</span></h3><p>从“为什么”开始，把排查思路变成下次可以复现的方法。</p><span class="card-link">查阅实机问答 →</span></a></div></section>
<section id="results"><div class="section-title"><span>02 / 实测摘要</span><h2>配置完成之后，还要看验证</h2><p>健康检查、实际收发与长期稳定是不同层次。</p></div><div class="result-panel"><div><span class="result-label">CAN FD · 1M / 5M</span><strong>收齐 12,386,944 帧</strong><p>30分钟压力测试仍有总线 / FIFO 错误，<b>严格验收未通过</b>。</p><a href="/can.html">查看完整结论 →</a></div><div><span class="result-label">RS485 · 双通道</span><strong>1.5M 持续测试通过</strong><p>累计20MiB + 1000次换向。更高速持续测试有丢字节；默认115200。</p><a href="/rs485.html">理解速率边界 →</a></div><div><span class="result-label">启动 · systemd 指标</span><strong>60.614s → 6.6–7.2s</strong><p>Wi-Fi约23–24秒就绪。该指标不等同于上电到远程可操作。</p><a href="/boot.html">读懂测量口径 →</a></div></div></section>
<section id="questions"><div class="section-title"><span>03 / 从一个问题开始</span><h2>同事经常会问</h2></div><div class="question-list"><a href="/wifi.html"><span class="question-topic">网络</span><strong>为什么只有一块网卡，却显示两个 Wi-Fi？</strong><span>→</span></a><a href="/can.html"><span class="question-topic">CAN</span><strong>500k 是上限吗？1M 和 5M 分别指什么？</strong><span>→</span></a><a href="/desktop.html"><span class="question-topic">桌面</span><strong>Chromium 打不开，应该先检查什么？</strong><span>→</span></a><a href="/desktop.html"><span class="question-topic">GPU</span><strong>llvmpipe 是什么？现在硬件加速生效了吗？</strong><span>→</span></a><a href="/branding.html"><span class="question-topic">系统</span><strong>桌面 logo 改了，开机 logo 就都改完了吗？</strong><span>→</span></a></div></section>
<div class="maintain-note"><span>持续积累</span><p>把有价值的问题写下来。记录现象、原因、步骤与验证范围，下一位同事就能沿着证据继续。</p><a href="/maintenance.html">如何补充问答 →</a></div>'''

def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(HERE / 'assets', OUT / 'assets')
    (OUT / 'index.html').write_text(shell('手册首页', home()))
    index = []
    for i, p in enumerate(PAGES):
        body, toc, records = article(p)
        index.extend(records)
        links = ''
        for q, label in ((PAGES[i-1] if i else None, '上一篇'), (PAGES[i+1] if i+1 < len(PAGES) else None, '下一篇')):
            if q:
                links += f'<a href="/{q["slug"]}.html"><small>{label}</small>{E(q["title"])} →</a>'
        content = f'<div class="article-meta">{E(p["group"])} · 更新 {SITE["updated"]}</div><article class="prose">{body}</article><nav class="page-links" aria-label="相邻文章">{links}</nav>'
        (OUT / (p['slug'] + '.html')).write_text(shell(p['title'], content, p['slug'], toc, p['source']))
    (OUT / 'search-index.json').write_text(json.dumps(index, ensure_ascii=False, separators=(',', ':')))
    body = '<article class="prose"><h1>这一页暂时找不到</h1><p>可以从目录继续阅读，或搜索一个关键词。</p><p><a href="/">返回手册首页 →</a></p></article>'
    (OUT / '404.html').write_text(shell('页面未找到', body))
    (OUT / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: ' + SITE['url'] + '/sitemap.xml\n')
    urls = ['/'] + ['/' + p['slug'] + '.html' for p in PAGES]
    (OUT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join('<url><loc>' + SITE['url'] + u + '</loc><lastmod>' + SITE['updated'] + '</lastmod></url>' for u in urls) + '</urlset>')
    (OUT / '_headers').write_text("/*\n  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  Permissions-Policy: camera=(), microphone=(), geolocation=()\n/assets/*\n  Cache-Control: public, max-age=300\n")
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    (OUT / 'build-info.json').write_text(json.dumps({'source_commit': sha, 'content_sha256': hashlib.sha256(b''.join((ROOT/p['source']).read_bytes() for p in PAGES)).hexdigest(), 'pages': len(PAGES)+1, 'updated': SITE['updated']}, indent=2)+'\n')
    print(f'Built {len(PAGES)+1} pages and {len(index)} searchable sections → wiki/dist')

if __name__ == '__main__':
    main()
