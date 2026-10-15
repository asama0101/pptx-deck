"""スライド案のレビューページ（variants.html・final-review.html）の生成、回答の解析、最終 HTML（final.html）の統合。

レビューページは、点検ページ（Artifact）と同じ形。左に一覧、右に 1 枚ずつ縦に並べる（大きな 1 案、見どころ・前回のコメント・今回の直し、判断欄＝案のサムネ・承認／要修正・コメント）。「回答をコピー」は、判断欄の最後の行（右端）にある。「回答をコピー」を押すと、クリップボードへ入れると同時に
window.__answersMd（回答の md）と window.__submitted が立つ。回答の形式は従来から変えない。"""
import html as _html
import json
import re
from pathlib import Path

from . import paths, svgids

FRAG = re.compile(r"^(\d{2})-([A-Z])(?:-d([23]))?\.html$")      # NN-A.html（デザイン 1）・NN-A-d2.html・NN-A-d3.html（同じ型のデザイン 2・3）
HEAD = ('<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>{title}</title>'
        '<link rel="stylesheet" href="theme.css"><link rel="stylesheet" href="base.css">'
        '<script src="chart-preview.js" defer></script>{extra}</head><body>')

_STYLE = r"""<style>
:root{--rv-bg:#14263E;--panel:#1B3250;--rv-line:#33496B;--fg:#EAF0F8;--sub:#AEBBD0;--ok:#6FC3A0;--cm:#F0A060;--co:#E83E8C;--sel:#25406A}
body{font-family:'BIZ UDPGothic','Yu Gothic','Meiryo',sans-serif;margin:0;padding:0;background:var(--rv-bg);color:var(--fg);font-size:15px;line-height:1.6}
.rv, .rv *{box-sizing:border-box}
.rv h1,.rv h2,.rv h3,.rv p,.rv ol,.rv ul{margin:0;padding:0}.rv ol,.rv ul{list-style:none}
.rv{max-width:1280px;margin:0 auto;padding:20px 16px 40px;display:flex;flex-direction:column;gap:16px}
.rv h1{font-size:22px;line-height:1.4}
.rv .lead{color:var(--sub);font-size:13.5px}
.rv .strip{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:13.5px;color:var(--sub);align-items:center}.rv .strip b{color:var(--fg)}
.rv .body{display:grid;gap:16px;grid-template-columns:270px minmax(0,1fr);align-items:start}
.rv nav{background:var(--panel);padding:10px 0;max-height:80vh;overflow-y:auto;overflow-x:hidden;position:sticky;top:8px}
.rv nav button{display:grid;grid-template-columns:14px 1fr;gap:8px;align-items:center;width:100%;text-align:left;font:inherit;font-size:14px;color:var(--fg);background:none;border:0;border-left:3px solid transparent;padding:6px 14px 6px 11px;cursor:pointer}
.rv nav button[aria-current="true"]{background:var(--sel);border-left-color:#fff;font-weight:700}
.rv nav small{display:block;color:var(--sub);font-weight:400;font-size:12px;line-height:1.35;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rv .st{width:10px;height:10px;border-radius:50%;border:2px solid var(--sub)}.rv .st.ok{background:var(--ok);border-color:var(--ok)}.rv .st.cm{background:var(--cm);border-color:var(--cm)}
.rv [hidden]{display:none!important}
.rv .pane{display:grid;gap:14px;min-width:0}
.rv .top{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:baseline}
.rv .top h2{font-size:20px}
.rv .showco{display:inline-flex;gap:6px;align-items:center;font-size:13.5px}
.rv .nh{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:6px 12px;margin-bottom:6px}.rv .nh h3{margin-bottom:0}
.rv .thumb{position:relative;width:100%;aspect-ratio:16/9;overflow:hidden;background:#fff;border:1px solid var(--rv-line);--s:.5;padding:0;display:block}
.rv .thumb .stage{position:absolute;left:0;top:0;width:1280px;height:720px;transform-origin:0 0}
.rv .thumb .slide{margin:0}
.rv .co-layer{position:absolute;left:0;top:0;width:1280px;height:720px;pointer-events:none}
.rv .co{position:absolute;border:calc(3px / var(--s)) solid var(--co);background:rgba(232,62,140,.07)}
.rv .co-n{position:absolute;right:calc(-14px / var(--s));top:calc(-14px / var(--s));width:calc(28px / var(--s));height:calc(28px / var(--s));border-radius:50%;background:var(--co);color:#fff;font:700 calc(16px / var(--s))/calc(28px / var(--s)) sans-serif;text-align:center}
.rv .nocol .co-layer{display:none}
.rv .cols{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr))}
.rv .pt-layer{position:absolute;left:0;top:0;width:1280px;height:720px;pointer-events:none}
.rv .pt{position:absolute;pointer-events:auto;cursor:pointer;font:700 calc(13px / var(--s))/1.25 sans-serif;padding:calc(2px / var(--s)) calc(7px / var(--s));background:#1B6FD1;color:#fff;border:0;border-radius:calc(11px / var(--s));white-space:nowrap}
.rv .pt.has{background:#E8A33E;color:#1a1a1a}
.rv .pt.up{transform:translateY(-100%)}
.rv .nopt .pt-layer{display:none}
.rv .plist{display:grid;gap:6px}.rv .plist li{display:grid;grid-template-columns:150px minmax(0,1fr) auto;gap:8px;align-items:start}
.rv .plist li b{font-size:13px;padding-top:6px}.rv .plist textarea{height:44px}
.rv .cols>div{background:var(--panel);padding:12px 14px;font-size:13.5px;min-width:0}
.rv .cols h3{font-size:12px;letter-spacing:.06em;color:var(--sub);margin-bottom:6px}
.rv .cols .q{border-left:3px solid var(--cm);padding-left:10px}.rv .cols .fix{border-left:3px solid var(--ok);padding-left:10px}
.rv .legend{display:grid;gap:4px}
.rv .legend li{display:grid;grid-template-columns:22px 1fr;gap:8px;font-size:13.5px;line-height:1.5}
.rv .dot{width:20px;height:20px;border-radius:50%;background:var(--co);color:#fff;font:700 12px/20px sans-serif;text-align:center;margin-top:1px}
.rv .judge{display:grid;gap:10px;background:var(--panel);padding:12px 14px}
.rv .judge .sub{color:var(--sub);font-size:13.5px}
.rv .opts{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-start}
.rv .opt,.rv .dopt{display:flex;flex-direction:column;gap:6px;width:min(31%,260px)}
.rv .dgroup{display:grid;gap:8px;border-top:1px solid var(--rv-line);padding-top:10px}.rv .dgroup .sub{font-weight:700}
.rv .opts.single{display:none}
.rv .opt .thumb,.rv .dopt .thumb{cursor:pointer}.rv .opt.view .thumb,.rv .dopt.view .thumb{outline:3px solid #fff;outline-offset:2px}
.rv .opt label,.rv .dopt label{font-weight:700;display:flex;gap:6px;align-items:center;cursor:pointer}
.rv .opt small{color:var(--sub);font-weight:400;font-size:12.5px;line-height:1.4}
.rv textarea{width:100%;height:64px;font:inherit;font-size:14px;padding:8px 10px;background:var(--rv-bg);color:var(--fg);border:1px solid var(--rv-line)}
.rv .btns{display:flex;flex-wrap:wrap;gap:8px}
.rv button.b1{font:inherit;font-size:14px;padding:8px 16px;border:1px solid var(--rv-line);background:transparent;color:var(--fg);cursor:pointer;border-radius:0}
.rv .verdict .b1[aria-pressed="true"].ok{background:var(--ok);color:#0F1623;border-color:var(--ok);font-weight:700}
.rv .verdict .b1[aria-pressed="true"].ng{background:var(--cm);color:#0F1623;border-color:var(--cm);font-weight:700}
.rv .nav2{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.rv :focus-visible{outline:2px solid var(--co);outline-offset:2px}
.rv .act{margin-left:auto;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.rv .act button{font:inherit;font-weight:700;padding:7px 26px;border:0;background:#fff;color:#14263E;cursor:pointer}
.rv .copybox{width:100%;height:90px;font:12px/1.4 Consolas,monospace}
.rv .state{color:var(--ok);font-weight:700;font-size:13px}
@media (max-width:820px){.rv .body{grid-template-columns:1fr}.rv nav{position:static;max-height:220px}.rv .opt,.rv .dopt{width:min(100%,300px)}}
.rv .doc{background:#fff;color:#1a1a1a;padding:18px 22px;border:1px solid var(--rv-line);font-size:14px;line-height:1.7;max-height:68vh;overflow:auto}
.rv .doc h3{font-size:17px;margin:4px 0 8px}.rv .doc h4{font-size:14px;margin:14px 0 4px;color:#33496B}
.rv .doc p{margin:2px 0}.rv .doc ul{margin:2px 0 2px 18px;list-style:disc}.rv .doc li{margin:1px 0}
.rv .doc table{border-collapse:collapse;margin:6px 0;width:100%}.rv .doc th,.rv .doc td{border:1px solid #c9d2e0;padding:4px 8px;text-align:left;vertical-align:top}.rv .doc th{background:#eef2f8;white-space:nowrap}
.rv .cols[hidden]{display:none}
</style>"""

_SCRIPT = r"""<script>
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var panes = $$('.pane'), cur = 0, KEY = 'pptxdeck-review-' + __DECK__ + '-__ROUND__';
  var PRESET = __PRESET__;

  function store(o) { try { sessionStorage.setItem(KEY, JSON.stringify(o)); } catch (e) {} }
  function load() { try { return JSON.parse(sessionStorage.getItem(KEY) || '{}') || {}; } catch (e) { return {}; } }
  function snapshot() {
    var o = {};
    panes.forEach(function (p) {
      var r = $('input[type=radio][name^="s"]:checked', p);
      var d = {}; $$('.dgroup input[type=radio]:checked', p).forEach(function (x) { d[x.closest('.dgroup').dataset.k] = x.value; });
      o[p.dataset.slide] = { c: r ? r.value : '', t: $('.cm', p).value, v: p.dataset.verdict || '', d: d, pc: partTexts(p) };
    });
    return o;
  }
  function restore() {
    var o = load();
    panes.forEach(function (p) {
      var a = o[p.dataset.slide]; if (!a) return;
      if (a.c) { var r = $('input[type=radio][name^="s"][value="' + a.c + '"]', p); if (r) r.checked = true; }
      $('.cm', p).value = a.t || '';
      p.dataset.verdict = a.v || '';
      Object.keys(a.d || {}).forEach(function (k) { var x = $('.dgroup[data-k="' + k + '"] input[value="' + a.d[k] + '"]', p); if (x) x.checked = true; });
      Object.keys(a.pc || {}).forEach(function (k) { partRow(p, k, a.pc[k]); });
    });
  }

  // 前回承認したスライドを選択済みにする。同じタブで入力の途中なら、その入力を優先する
  function applyPreset() {
    if (Object.keys(load()).length) return;
    panes.forEach(function (p) {
      var a = PRESET[p.dataset.slide]; if (!a) return;
      var single = p.dataset.single === '1';
      var r = $('input[type=radio][name^="s"][value="' + (single ? 'A' : a.c) + '"]', p);
      if (!r) return;                                           // 案がなくなっていれば引き継がない
      r.checked = true;
      if (!single) {
        p.dataset.verdict = '承認';
        if (a.d > 1) { var x = $('.dgroup[data-k="' + a.c + '"] input[value="' + a.d + '"]', p); if (x) x.checked = true; }
      }
    });
  }

  function fit() {
  // 部位のコメント。key は「案|部位名（番号つき）」。行は、バッジを押したときに作る（空のままの行は回答に出さない）
  function partLabel(key) { var i = key.indexOf('|'); var k = key.slice(0, i), n = key.slice(i + 1); return (k ? '案 ' + k + ' ' : '') + n; }
  function partTexts(p) {
    var o = {}; $$('.plist li', p).forEach(function (li) { var v = $('textarea', li).value; if (v.trim()) o[li.dataset.key] = v; });
    return o;
  }
  function partRow(p, key, text) {
    var li = $('.plist li[data-key="' + key.replace(/"/g, '\\"') + '"]', p);
    if (!li) {
      li = document.createElement('li'); li.dataset.key = key;
      li.innerHTML = '<b></b><textarea aria-label="部位のコメント" placeholder="この部位をどうしてほしいか"></textarea><button type="button" class="b1">消す</button>';
      $('b', li).textContent = partLabel(key);
      $('textarea', li).oninput = function () { partChanged(p); };
      $('button', li).onclick = function () { li.remove(); partChanged(p); };
      $('.plist', p).appendChild(li);
    }
    if (text) $('textarea', li).value = text;
    $('.parts', p).hidden = false;
    return li;
  }
  function partChanged(p) {
    if (Object.keys(partTexts(p)).length && !verdictOf(p)) setVerdict(p, '要修正');     // 部位のコメントを書いたら、要修正にする
    markParts(p); refresh(); store(snapshot());
  }
  function markParts(p) {
    var t = partTexts(p);
    $$('.pt', p).forEach(function (b) { b.classList.toggle('has', !!t[b.dataset.key]); });
  }
  // 大きな 1 案に、部位（data-part）の名前のバッジを重ねる。同じ部位が複数あるときは、左上から右下の順に ①②③ を付ける
  function addPartBadges(p, clone, k, big) {
    var els = $$('[data-part]', clone).map(function (el) { return { el: el, r: rel(el, clone), n: el.getAttribute('data-part') }; });
    els.sort(function (a, b) { return (a.r.y - b.r.y) || (a.r.x - b.r.x); });
    var total = {}, seen = {};
    els.forEach(function (e) { total[e.n] = (total[e.n] || 0) + 1; });
    var layer = document.createElement('div'); layer.className = 'pt-layer';
    els.forEach(function (e) {
      seen[e.n] = (seen[e.n] || 0) + 1;
      var name = total[e.n] > 1 ? e.n + String.fromCharCode(0x2460 + seen[e.n] - 1) : e.n;
      var key = (p.dataset.single === '1' ? '' : k) + '|' + name;
      var b = document.createElement('button'); b.type = 'button'; b.className = 'pt'; b.dataset.key = key;
      b.textContent = name; b.style.left = e.r.x + 'px'; b.style.top = e.r.y + 'px';
      if (e.r.y > 26) b.classList.add('up');                  // 部位の文字にかぶらないよう、枠の左上の外に置く（上に余白がないときは中）
      b.title = name + 'にコメントする';
      b.onclick = function () { var li = partRow(p, key); $('textarea', li).focus(); };
      layer.appendChild(b);
    });
    big.appendChild(layer);
    markParts(p);
  }

    $$('.thumb').forEach(function (t) {
      var w = t.clientWidth; if (!w) return;
      var s = w / 1280;
      t.style.setProperty('--s', s);
      t.firstElementChild.style.transform = 'scale(' + s + ')';
    });
  }
  function rel(el, slide) {
    var x = 0, y = 0, e = el;
    while (e && e !== slide) { x += e.offsetLeft; y += e.offsetTop; e = e.offsetParent; }
    return { x: x, y: y, w: el.offsetWidth, h: el.offsetHeight };
  }
  function viewKey(p) {
    var r = $('input[type=radio][name^="s"]:checked', p);
    return p.dataset.view || (r ? r.value : $('.opt', p).dataset.k);
  }
  function dsel(p, k) { var r = $('.dgroup[data-k="' + k + '"] input[type=radio]:checked', p); return r ? +r.value : 1; }
  function showBig(p, k, d) {
    p.dataset.view = k;
    if (p.dataset.doc === '1') { fit(); return; }
    d = d || dsel(p, k);
    $$('.opt', p).forEach(function (o) { o.classList.toggle('view', o.dataset.k === k); });
    $$('.dgroup', p).forEach(function (g) { g.hidden = g.dataset.k !== k; });      // 選んだ型のデザイン（1〜3）だけを出す
    $$('.dopt', p).forEach(function (o) { o.classList.toggle('view', o.dataset.k === k && +o.dataset.d === d); });
    var vr = $('.vr', p), op = $('.opt[data-k="' + k + '"]', p);
    var vt = op ? [op.dataset.name || '', op.dataset.reason || ''].filter(Boolean).join('：') : '';
    $('span', vr).textContent = vt; vr.hidden = !vt;
    var src = (d > 1 ? $('.dopt[data-k="' + k + '"][data-d="' + d + '"] .stage .slide', p) : null) || $('.opt[data-k="' + k + '"] .stage .slide', p);
    var big = $('.big .stage', p);
    big.innerHTML = '';
    if (!src) return;
    var clone = src.cloneNode(true);
    big.appendChild(clone);
    var layer = document.createElement('div'); layer.className = 'co-layer';
    var legend = $('.legend', p); legend.innerHTML = '';
    var groups = [], seen = {};                                          // 同じ文の data-note は、1 つの見どころとして枠でまとめる
    $$('[data-note]', clone).forEach(function (el) {
      var t = el.getAttribute('data-note');
      if (!Object.prototype.hasOwnProperty.call(seen, t)) { seen[t] = { t: t, els: [] }; groups.push(seen[t]); }
      seen[t].els.push(el);
    });
    groups.forEach(function (g, i) {
      var x0 = 1e9, y0 = 1e9, x1 = 0, y1 = 0;
      g.els.forEach(function (el) {
        var r = rel(el, clone);
        x0 = Math.min(x0, r.x); y0 = Math.min(y0, r.y); x1 = Math.max(x1, r.x + r.w); y1 = Math.max(y1, r.y + r.h);
      });
      var d = document.createElement('div'); d.className = 'co';
      d.style.cssText = 'left:' + x0 + 'px;top:' + y0 + 'px;width:' + (x1 - x0) + 'px;height:' + (y1 - y0) + 'px';
      d.innerHTML = '<span class="co-n">' + (i + 1) + '</span>';
      layer.appendChild(d);
      var li = document.createElement('li');
      li.innerHTML = '<span class="dot">' + (i + 1) + '</span><span></span>';
      li.lastChild.textContent = g.t;
      legend.appendChild(li);
    });
    big.appendChild(layer);
    $('.notes', p).hidden = !legend.firstChild;                          // 見どころ・前回のコメント・今回の直しが何もなければ、枠ごと隠す
    addPartBadges(p, clone, k, big);
    $('.cols', p).hidden = $$('.cols > div:not([hidden])', p).length === 0;
    fit();
  }
  // 承認／要修正。1 案だけのスライド（採用／要修正・最終確認）は選択のラジオ（A / FIX）と連動し、3 案のときは案の選択とは別に持つ
  function verdictOf(p) {
    if (p.dataset.single === '1') {
      var r = $('input[type=radio][name^="s"]:checked', p);
      return r ? (r.value === 'FIX' ? '要修正' : '承認') : '';
    }
    return p.dataset.verdict || '';
  }
  function syncButtons(p) {
    var v = verdictOf(p);
    $$('.verdict button', p).forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.v === v); });
  }
  function setVerdict(p, v) {
    if (verdictOf(p) === v) v = '';                           // 押した状態でもう一度押すと外れる
    if (p.dataset.single === '1') {
      $$('input[type=radio][name^="s"]', p).forEach(function (x) { x.checked = false; x.dataset.was = '0'; });
      if (v) { var r = $('input[type=radio][name^="s"][value="' + (v === '要修正' ? 'FIX' : 'A') + '"]', p); r.checked = true; r.dataset.was = '1'; }
    } else {
      p.dataset.verdict = v;
      if (v === '承認' && !$('input[type=radio][name^="s"]:checked', p)) {   // 承認のとき、案を選んでいなければ表示中の案を選ぶ（要修正は、どの案でもない場合を含むので自動では選ばない）
        var rr = $('.opt[data-k="' + viewKey(p) + '"] input[type=radio]', p);
        if (rr) { rr.checked = true; rr.dataset.was = '1'; }
      }
    }
    refresh(); store(snapshot());
    if (v === '承認' && cur < panes.length - 1) go(cur + 1);       // 承認したら次のスライドへ（要修正と最後は動かない）
  }
  function refresh() {
    panes.forEach(function (p, i) {
      var b = $('#nav button[data-go="' + p.dataset.slide + '"] .st');
      var chosen = !!$('input[type=radio][name^="s"]:checked', p), cm = $('.cm', p).value.trim() !== '' || Object.keys(partTexts(p)).length > 0 || verdictOf(p) === '要修正';
      b.className = 'st' + (cm ? ' cm' : chosen ? ' ok' : '');
      syncButtons(p);
    });
    var done = panes.filter(function (p) { return $('input[type=radio][name^="s"]:checked', p); }).length;
    $('#prog').innerHTML = '選択済み <b>' + done + '</b> / ' + panes.length;
  }
  function go(i) {
    cur = (i + panes.length) % panes.length;
    panes.forEach(function (p, j) { p.hidden = j !== cur; });
    $$('#nav button').forEach(function (b, j) { b.setAttribute('aria-current', j === cur); });
    var p = panes[cur];
    $$('.pp-chart', p).forEach(function (h) { if (window.__chartPreview) window.__chartPreview(h); });   // 非表示の間は大きさが 0 なので、表示してから描く
    if (window.__arrows) window.__arrows(p);
    fit();
    showBig(p, viewKey(p));
    window.scrollTo(0, 0);
  }

  $$('#nav button').forEach(function (b, i) { b.onclick = function () { go(i); }; });
  panes.forEach(function (p) {
    $$('.opt', p).forEach(function (o) {
      var th = $('.thumb', o);
      th.onclick = function () { showBig(p, o.dataset.k); };
      th.onkeydown = function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); showBig(p, o.dataset.k); } };
      $$('input[type=radio]', o).forEach(function (r) {
        r.onchange = function () { showBig(p, o.dataset.k); refresh(); store(snapshot()); };
        r.onclick = function () {      // 選んだラジオをもう一度押すと、選択が外れる
          if (this.dataset.was === '1') { this.checked = false; this.dataset.was = '0'; refresh(); store(snapshot()); }
          else { $$('input[type=radio][name^="s"]', p).forEach(function (x) { x.dataset.was = '0'; }); this.dataset.was = '1'; }
        };
      });
    });
    $$('.dopt', p).forEach(function (o) {
      var th = $('.thumb', o), pick = function () { var r = $('input[type=radio]', o); r.checked = true; showBig(p, o.dataset.k, +o.dataset.d); store(snapshot()); };
      th.onclick = pick;
      th.onkeydown = function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(); } };
      $('input[type=radio]', o).onchange = pick;
    });
    $('.cm', p).oninput = function () { refresh(); store(snapshot()); };
    $('.coToggle', p).onchange = function () { $('.big', p).classList.toggle('nocol', !this.checked); };
    $$('.verdict button', p).forEach(function (b) { b.onclick = function () { setVerdict(p, b.dataset.v); }; });
    $('.ptToggle', p).onchange = function () { $('.big', p).classList.toggle('nopt', !this.checked); };
    $('.clear', p).onclick = function () {
      p.dataset.verdict = '';
      $$('input[type=radio]', p).forEach(function (x) { x.checked = false; x.dataset.was = '0'; });
      refresh(); store(snapshot());
    };
    $('.prev', p).onclick = function () { go(cur - 1); };
    $('.next', p).onclick = function () { go(cur + 1); };
  });
  window.addEventListener('resize', fit);

  function buildMd() {
    var lines = ['---', 'deck: ' + __DECK__, 'round: __ROUND__', '---'];
    document.querySelectorAll('[data-slide]').forEach(function (sec) {
      if (!verdictOf(sec)) return;                                   // 承認か要修正を選んでいないスライドは、回答に含めない
      var sel = sec.querySelector('input[type=radio][name^="s"]:checked');
      var c = sec.querySelector('.cm').value.replace(/\r?\n/g, ' ');
      lines.push('## S' + sec.dataset.slide, '- 選択: ' + (sel ? sel.value : ''));
      var dr = sel ? sec.querySelector('.dgroup[data-k="' + sel.value + '"] input[type=radio]:checked') : null;
      if (dr) lines.push('- デザイン: ' + dr.value);           // 選んだ型にデザイン 2・3 があるときだけ（省略時は 1）
      lines.push('- 判定: ' + verdictOf(sec), '- コメント: ' + c);
    });
      var pt = partTexts(sec);
      Object.keys(pt).forEach(function (key) { lines.push('- 部位: ' + partLabel(key) + ' ／ コメント: ' + pt[key].replace(/\r?\n/g, ' ')); });
    return lines.join('\n') + '\n';
  }
  // 「回答をコピー」（判断欄の最後の行・右端）: 回答をクリップボードへ入れ、同時に window.__answersMd と window.__submitted を立てる。
  // Claude が待ち受けていれば自動で受け取れ、そうでなければ利用者がチャットに貼り付ける（形式は同じ）
  $$('.copyBtn').forEach(function (btn) {
    btn.onclick = function () {
      var pane = btn.closest('.pane'), md = buildMd(), st = $('.state', pane), box = $('.copybox', pane);
      var n = (md.match(/^## S/gm) || []).length;
      if (!n) { st.textContent = '承認か要修正を選んだスライドがありません。選んでから押してください。'; return; }
      window.__answersMd = md;
      window.__submitted = true;
      var fallback = function () {
        box.hidden = false; box.value = md; box.focus(); box.select();
        st.textContent = 'コピーできませんでした。下の文字を選んで、コピーしてください。';
      };
      try {
        navigator.clipboard.writeText(md).then(function () {
          box.hidden = true;
          st.textContent = 'コピーしました。Claude が待っていれば届きます。待っていなければ、チャットに貼り付けてください。';
        }, fallback);
      } catch (e) { fallback(); }
    };
  });

  function start() {
    restore();
    applyPreset();
    $$('input[type=radio][name^="s"]:checked').forEach(function (x) { x.dataset.was = '1'; });
    refresh(); store(snapshot()); go(0);
  }
  if (document.readyState === 'complete') start(); else window.addEventListener('load', start);
})();
</script>"""


def collect_designs(work: Path) -> dict[str, dict[str, dict[int, str]]]:
    """スライド → 案（型）→ デザイン番号 → 断片。デザイン 1 は NN-A.html、2・3 は NN-A-d2.html・NN-A-d3.html。
    デザイン 1 のない案（-d2 だけ）は ValueError。"""
    d = Path(work) / "slides"
    if not d.is_dir():
        raise ValueError(f"{d} がありません（slides/NN-A.html の形で案を置いてください）")
    out: dict[str, dict[str, dict[int, str]]] = {}
    for f in sorted(d.iterdir()):
        m = FRAG.match(f.name)
        if m:
            dn = int(m.group(3) or 1)
            # 絵（pp-picture）の SVG の id は、案ごとに一意にする（複数の絵で同じ id の定義が前の絵に引かれて、アイコンや矢じりが消えるのを防ぐ）
            text = svgids.uniquify(f.read_text(encoding="utf-8"), f"s{m.group(1)}{m.group(2).lower()}{dn}-")
            out.setdefault(m.group(1), {}).setdefault(m.group(2), {})[dn] = text
    if not out:
        raise ValueError(f"{d} に NN-A.html の形のファイルがありません")
    for nn, opts in out.items():
        for k, ds in opts.items():
            if 1 not in ds:
                raise ValueError(f"slides/{nn}-{k}.html（デザイン 1）がありません（{nn}-{k}-d2/-d3 だけでは出せません）")
    return out


def collect(work: Path) -> dict[str, dict[str, str]]:
    """スライド → 案 → デザイン 1 の断片（案の選択の画面に出す基本形）。"""
    return {nn: {k: ds[1] for k, ds in opts.items()} for nn, opts in collect_designs(work).items()}


def _variant_info(fragment: str) -> tuple[str, str]:
    """案の型名と選んだ理由。断片の `data-variant="型名｜理由"`（区切りは ｜ か |）から読む。無ければ空。"""
    m = re.search(r'data-variant="([^"]*)"', fragment)
    if not m:
        return "", ""
    parts = re.split(r"[｜|]", m.group(1), maxsplit=1)
    return parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")


def _title_of(fragment: str) -> str:
    """一覧に出すスライドの題（題の要素の文字）。見つからなければ空。"""
    m = re.search(r'<div[^>]*(?:data-role="title"|data-ph="title")[^>]*>(.*?)</div>', fragment, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def parse_notes(md: str) -> dict[str, str]:
    """今回の直しのメモ（round-N-notes.md）。「NN: 直した内容」「- S01: …」の行を読む。"""
    out: dict[str, str] = {}
    for line in md.splitlines():
        m = re.match(r"^\s*(?:[-*]\s*)?S?(\d{2})\s*[:：]\s*(.+?)\s*$", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _page(work: Path, frags: dict[str, dict[str, str]], round_label: str, final: bool = False,
          prev: dict[str, dict] | None = None, notes: dict[str, str] | None = None,
          designs: dict[str, dict[str, dict[int, str]]] | None = None,
          preset: dict | None = None,
          docs: dict[str, str] | None = None, titles: dict[str, str] | None = None) -> str:
    esc = _html.escape
    prev, notes, designs = prev or {}, notes or {}, designs or {}
    title = "最終 HTML の確認" if final else "スライド案の選択"
    if final:
        lead = "選ばれた案を統合した最終版です。1 枚ずつ見て「承認」か「要修正」を選び、直したい点があればコメントに書いて、最後に判断欄の右端の「回答をコピー」を押してください。"
    else:
        lead = (f"ラウンド {round_label}。左の一覧から 1 枚ずつ見ます。案を選び（サムネを押すと大きく見えます）、"
                "直したい点があればコメントに書いて、最後に判断欄の右端の「回答をコピー」を押してください。")
    if docs is not None:
        title = "設計図と原稿の確認"
        lead = ("承認する前に、資料全体と、スライドごとの設計と原稿を確認します。1 枚ずつ見て「承認」か「要修正」を選び、"
                "直したい点があればコメントに書いて、最後に判断欄の右端の「回答をコピー」を押してください。")
    nav, panes = [], []
    for nn, opts in frags.items():
        letters = sorted(opts)
        t = (titles or {}).get(nn) or _title_of(opts[letters[0]])
        nav.append(f'<button data-go="{nn}"><span class="st"></span><span>S{nn}<small>{esc(t)}</small></span></button>')
        single = final or len(letters) == 1 or docs is not None
        doc_attr = ' data-doc="1"' if docs is not None else ""
        p = [f'<section class="pane" data-slide="{nn}" data-single="{1 if single else 0}"{doc_attr} hidden>',
             f'<div class="top"><h2>{esc(t) if docs is not None and nn == "00" else "S" + nn + "　" + esc(t)}</h2></div>',
             (f'<div class="doc">{docs[nn]}</div>' if docs is not None
              else '<div class="big"><div class="thumb"><div class="stage"></div></div></div>'),
             '<div class="cols"' + (' hidden' if docs is not None else '') + '>']
        pc = comment_text(prev.get(nn) or {})
        fx = notes.get(nn, "")
        if pc:
            p.append(f'<div class="q"><h3>前回のコメント</h3>{esc(pc)}</div>')
        if fx:
            p.append(f'<div class="fix"><h3>今回の直し</h3>{esc(fx)}</div>')
        p.append('<div class="vr" hidden><h3>型と選んだ理由</h3><span></span></div>')
        p.append('<div class="notes"><div class="nh"><h3>見どころ</h3>'
                 '<label class="showco"><input type="checkbox" class="coToggle" checked> 見どころの枠を表示</label></div>'
                 '<ol class="legend"></ol></div></div>')
        p.append('<div class="judge"><div class="sub">'
                 + ("この内容を承認しますか。" if single else "案を選び（サムネを押すと大きく見えます）、承認か要修正を押してください。どの案でもない場合は、案を選ばずに要修正を押し、コメントに書いてください。") + '</div>')
        p.append('<div class="opts single">' if single else '<div class="opts">')     # 1 案だけのときは、案の選択（サムネとラジオ）を隠す
        for k in letters:
            vname, vreason = _variant_info(opts[k])
            p.append(f'<div class="opt" data-k="{k}" data-name="{esc(vname, quote=True)}" data-reason="{esc(vreason, quote=True)}">'
        p.append('<div class="parts" hidden><div class="nh"><h3>部位のコメント（スライドの青いバッジを押すと、その部位に書けます）</h3>'
                 '<label class="showco"><input type="checkbox" class="ptToggle" checked> 部位のバッジを表示</label></div>'
                 '<ul class="plist"></ul></div>')
                     f'<div class="thumb" role="button" tabindex="0" aria-label="案 {k} を大きく見る">'
                     f'<div class="stage">{opts[k]}</div></div>')
            if final:
                p.append(f'<label><input type="radio" name="s{nn}" value="A"> 承認</label>'
                         f'<label><input type="radio" name="s{nn}" value="FIX"> 要修正</label>')
            elif len(letters) > 1:
                p.append(f'<label><input type="radio" name="s{nn}" value="{k}"> 案 {k}</label>'
                         + (f'<small>{esc(vname)}</small>' if vname else ""))
            else:
                p.append(f'<label><input type="radio" name="s{nn}" value="A"> 採用</label>'
                         f'<label><input type="radio" name="s{nn}" value="FIX"> 要修正</label>')
            p.append("</div>")
        p.append('</div>')                                                              # 1 行目（案）を閉じる
        if not final:                                                                  # 2 行目: 案（型）を選んだあとに、その型のデザイン 1〜3 から選ぶ
            for k in letters:
                ds = (designs.get(nn) or {}).get(k) or {}
                if len(ds) < 2:
                    continue
                p.append(f'<div class="dgroup" data-k="{k}" hidden><div class="sub">案 {k} のデザイン（同じ内容の見せ方の違い）を選びます</div><div class="opts">')
                for d in sorted(ds):
                    p.append(f'<div class="dopt" data-k="{k}" data-d="{d}"><div class="thumb" role="button" tabindex="0" aria-label="案 {k} のデザイン {d} を大きく見る">'
                             f'<div class="stage">{ds[d]}</div></div>'
                             f'<label><input type="radio" name="d{nn}{k}" value="{d}"> デザイン {d}</label></div>')
                p.append('</div></div>')
        p.append('<div class="btns verdict"><button class="b1 ok" type="button" data-v="承認" aria-pressed="false">承認</button>'
                 '<button class="b1 ng" type="button" data-v="要修正" aria-pressed="false">要修正</button></div>'
                 '<textarea class="cm" placeholder="どうしてほしいか（任意）" aria-label="コメント"></textarea>'
                 '<div class="nav2"><button class="b1 clear" type="button">選択を外す</button>'
                 '<button class="b1 prev" type="button">前へ</button>'
                 '<button class="b1 next" type="button">次へ</button>'
                 '<span class="act"><span class="state"></span><button class="copyBtn" type="button">回答をコピー</button></span></div>'
                 '<textarea class="copybox" hidden readonly aria-label="回答（コピー用）"></textarea></div></section>')
        panes.append("".join(p))
    parts = [HEAD.format(title=title, extra=_STYLE),
             f'<div class="rv"><h1>{title}</h1><p class="lead">{lead}</p>'
             f'<div class="strip"><span>スライド <b>{len(frags)}</b> 枚</span><span id="prog"></span>'
             '</div>'
             f'<div class="body"><nav id="nav" aria-label="スライドの一覧">{"".join(nav)}</nav><div>{"".join(panes)}</div></div>'
             '</div>']
    deck_js = json.dumps(paths.deck_name(work), ensure_ascii=False).replace("</", "<\\/")      # JS の文字列。</script> でも閉じない
    preset_js = json.dumps(preset or {}, ensure_ascii=False).replace("</", "<\\/")
    parts.append(_SCRIPT.replace("__DECK__", deck_js).replace("__ROUND__", round_label).replace("__PRESET__", preset_js))
    parts.append("</body></html>")
    return "".join(parts)


def assemble(work: Path, round_no: int = 1) -> Path:
    """variants.html を作る。2 回目以降は、前回の回答（answers-(N-1).md）のコメントと、
    今回の直しのメモ（round-N-notes.md）があれば並べて出す。"""
    work = Path(work)
    designs = collect_designs(work)
    frags = {nn: {k: ds[1] for k, ds in opts.items()} for nn, opts in designs.items()}
    prev = parse_answers(_read(work / f"answers-{round_no - 1}.md")) if round_no > 1 else {}
    notes = parse_notes(_read(work / f"round-{round_no}-notes.md")) if round_no > 1 else {}
    out = work / "variants.html"
    preset = approved_preset([f.read_text(encoding="utf-8") for f in answer_paths(work, upto=round_no - 1)]) if round_no > 1 else {}
    out.write_text(_page(work, frags, str(round_no), prev=prev, notes=notes, designs=designs, preset=preset), encoding="utf-8")
    return out


def parse_answers(md: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    cur = None
    for line in md.splitlines():
        m = re.match(r"^## S(\d{2})\s*$", line)
        if m:
_PART_LINE = re.compile(r"^- 部位:\s*(.+?)\s*／\s*コメント:\s*(.*)$")


            cur = m.group(1)
            out[cur] = {"choice": "", "comment": "", "parts": []}
        elif cur and line.startswith("- 選択:"):
            out[cur]["choice"] = line.split(":", 1)[1].strip()
        elif cur and line.startswith("- デザイン:"):
            v = line.split(":", 1)[1].strip()
            if v.isdigit():                             # 省略時は 1（デザインの行は任意）
                out[cur]["design"] = int(v)
        elif cur and line.startswith("- 判定:"):
            v = line.split(":", 1)[1].strip()
            if v:                                       # 判定の行は任意（古い回答にはない）。空なら入れない
                out[cur]["verdict"] = v
        elif cur and line.startswith("- コメント:"):
            out[cur]["comment"] = line.split(":", 1)[1].strip()
    return out


def merge_answers(mds: list[str]) -> dict[str, dict]:
    """複数回の回答を順に重ねる。選択が入っているスライドだけ、後の回答で置き換える。
    2 回目以降に答えなかったスライド（選択が空）は、前の回答を消さない。"""
        elif cur and (pm := _PART_LINE.match(line)):      # 部位を指定したコメント（「- 部位: 注釈 ／ コメント: …」。案ごとの回答は「案 A 注釈」）
            out[cur]["parts"].append({"part": pm.group(1).strip(), "comment": pm.group(2).strip()})
    out: dict[str, dict] = {}
    for md in mds:
        for nn, a in parse_answers(md).items():
def comment_text(a: dict) -> str:
    """スライド全体のコメントと、部位ごとのコメントを 1 つの文にする（空なら空）。"""
    items = [a.get("comment", "")] + [f"【{x['part']}】{x['comment']}" for x in a.get("parts", []) if x["comment"]]
    return " ".join(t for t in items if t)


            if a["choice"] or nn not in out:
                out[nn] = a
    return out


_ANS_FILE = re.compile(r"^answers-(\d+|final)\.md$")
_PLAN_FILE = re.compile(r"^answers-plan-(\d+)\.md$")


def answer_paths(work: Path, upto: int | None = None, include_final: bool = True) -> list[Path]:
    """answers-N.md（N は数字）を昇順に、最後に answers-final.md（include_final=False なら含めない）。
    answers-plan-*.md は含めない。案の決定に使う回答は include_final=False で取る（最終確認の回答は案を決めない）。"""
    found: list[tuple[int, Path]] = []
    for f in Path(work).glob("answers-*.md"):
        m = _ANS_FILE.match(f.name)
        if not m:
            continue
        if not m.group(1).isdigit() and not include_final:
            continue
        n = int(m.group(1)) if m.group(1).isdigit() else 10 ** 9
        if upto is not None and n > upto:
            continue
        found.append((n, f))
    return [f for _, f in sorted(found)]


def plan_answer_paths(work: Path) -> list[Path]:
    found = [(int(m.group(1)), f) for f in Path(work).glob("answers-plan-*.md") if (m := _PLAN_FILE.match(f.name))]
    return [f for _, f in sorted(found)]


def plan_next_round(work: Path) -> int:
    nums = [int(m.group(1)) for f in Path(work).glob("answers-plan-*.md") if (m := _PLAN_FILE.match(f.name))]
    return max(nums, default=0) + 1


def next_round(work: Path) -> int:
    nums = [int(m.group(1)) for f in Path(work).glob("answers-*.md") if (m := _ANS_FILE.match(f.name)) and m.group(1).isdigit()]
    return max(nums, default=0) + 1


def approved_preset(mds: list[str]) -> dict[str, dict]:
    """回の順に重ねて、最新の判定が承認でコメントが空のスライドだけ返す（再提示の画面で選択済みにする）。"""
    cur: dict[str, dict] = {}
    for md in mds:
        for nn, a in parse_answers(md).items():
            verdict = a.get("verdict", "")
            if not verdict and not a["choice"]:
                continue
            prev = cur.get(nn, {})
            cur[nn] = {"c": a["choice"] or prev.get("c", ""), "d": a.get("design", prev.get("d", 1)),
                       "v": verdict or "承認", "m": comment_text(a)}
    return {nn: {"c": x["c"], "d": x["d"], "v": x["v"]}
            for nn, x in cur.items() if x["v"] == "承認" and x["c"] and not x["m"]}


def _chosen(work: Path, answers_md: "str | list[str]", allow_comments: bool = False):
    """回答から、選ばれた案（型）とデザインを決める。決まらないスライドやコメント未反映があれば ValueError。
    戻り値は（スライド → 選ばれた断片, 回答）。デザインの回答（- デザイン: N）が無ければデザイン 1。"""
    designs = collect_designs(work)
    ans = merge_answers([answers_md] if isinstance(answers_md, str) else list(answers_md))
    problems, picked = [], {}
    for nn in sorted(designs):
        a = ans.get(nn)
        if not a or a["choice"] not in designs[nn]:
            got = a["choice"] if a and a["choice"] else "未回答"
            problems.append(f"S{nn}: 案が決まっていません（回答: {got}）")
            continue
        d = a.get("design", 1)
        if d not in designs[nn][a["choice"]]:
            problems.append(f"S{nn}: 案 {a['choice']} にデザイン {d} がありません（slides/{nn}-{a['choice']}-d{d}.html を置いてください）")
        elif comment_text(a) and not allow_comments:
            problems.append(f"S{nn}: コメントが未反映です: {comment_text(a)}")
        elif a.get("verdict") == "要修正" and not allow_comments:
            problems.append(f"S{nn}: 要修正と判定されています（直してから再提示してください）")
        else:
            picked[nn] = designs[nn][a["choice"]][d]
    if problems:
        raise ValueError("\n".join(problems))
    return picked, ans


def review_final(work: Path, answers_md: "str | list[str]", allow_comments: bool = False,
                 preset_extra_mds: "list[str] | None" = None) -> Path:
    """最終 HTML の確認ページ（final-review.html）を作る。final.html は変えない（build が使う）。
    「回答をコピー」を押すと、承認は「選択: A」、要修正は「選択: FIX」で、従来と同じ形の回答が返る（answers-final.md に保存する）。"""
    work = Path(work)
    picked, _ = _chosen(work, answers_md, allow_comments)
    one = {nn: {"A": picked[nn]} for nn in sorted(picked)}
    out = work / "final-review.html"
    mds = [answers_md] if isinstance(answers_md, str) else list(answers_md)
    out.write_text(_page(work, one, "final", final=True, preset=approved_preset(mds + list(preset_extra_mds or []))), encoding="utf-8")
    return out


def finalize(work: Path, answers_md: "str | list[str]", allow_comments: bool = False,
             preset_extra_mds: "list[str] | None" = None) -> Path:
    work = Path(work)
    picked, _ = _chosen(work, answers_md, allow_comments)
    body = "\n".join(picked[nn] for nn in sorted(picked))
    out = work / "final.html"
    out.write_text(HEAD.format(title=_html.escape(paths.deck_name(work)), extra="") + body + "</body></html>", encoding="utf-8")
    review_final(work, answers_md, allow_comments, preset_extra_mds)   # 最終の確認ページも同時に作る
    return out
