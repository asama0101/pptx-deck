"""レビューページ（variants.html・final-review.html）の編集モード。ページに足す CSS・JS・HTML を持つ。

「編集モード」のスイッチ（.rv-edit-toggle）を入れたときだけ、大きな 1 案の文字（fragedit.targets と同じ規則で決めた対象）が
contenteditable になる。直した内容はサムネの断片（.opt / .dopt の .stage .slide）へ書き、回答 md に
「- 編集: {"f","t","before","after"}」で出す。スイッチを入れていないときは、既存の操作に何もしない。
JS は variants._SCRIPT の IIFE の中（function start() の直前）に入り、$・$$・panes・cur・showBig・viewKey・store・snapshot を使う。
CSS 変数・クラス名は、テーマ（theme.css）と混ざらないよう rv- の接頭辞を付ける（.rv の editing だけは例外）。"""

# スライドの上の帯（型と選んだ理由・見どころ・部位のバッジの左）に置くスイッチ
TOGGLE = '<label class="rv-edit-sw"><input type="checkbox" class="rv-edit-toggle"> 編集モード</label>'

# 大きな 1 案の下に出すツールバー（編集中だけ見える）。色はテーマの文字色のクラス（fragedit.TEXT_CLASSES）
BAR = (
    '<div class="rv-edit-bar" role="toolbar" aria-label="選んだ文字の装飾">'
    '<span class="rv-ed-l">選んだ文字</span>'
    '<button type="button" data-ed="bold" title="太字（もう一度押すと外す）"><b>B</b> 太字</button>'
    '<span class="rv-ed-sep"></span><span class="rv-ed-l">色</span><span class="rv-ed-sws">'
    '<button type="button" class="rv-ed-sw" data-ed="cls" data-v="t-dark" title="濃い基調色" style="background:var(--accent-dark,#14263E)"></button>'
    '<button type="button" class="rv-ed-sw" data-ed="cls" data-v="t-accent" title="基調色" style="background:var(--accent,#1B6FD1)"></button>'
    '<button type="button" class="rv-ed-sw" data-ed="cls" data-v="t-emph" title="強調色" style="background:var(--emphasis,#E83E8C)"></button>'
    '<button type="button" class="rv-ed-sw" data-ed="cls" data-v="t-sub" title="薄い文字" style="background:var(--text-sub,#6B7A90)"></button>'
    '<button type="button" class="rv-ed-sw" data-ed="cls" data-v="t-white" title="白" style="background:#FFFFFF"></button></span>'
    '<label class="rv-ed-l" title="任意の色">任意 <input type="color" class="rv-ed-color" value="#E83E8C" aria-label="任意の色"></label>'
    '<span class="rv-ed-sep"></span><span class="rv-ed-l">サイズ</span>'
    '<button type="button" data-ed="size" data-v="-2" aria-label="小さく">－</button>'
    '<input type="number" class="rv-ed-size" min="8" max="120" step="1" aria-label="文字サイズ（px）">'
    '<button type="button" data-ed="size" data-v="2" aria-label="大きく">＋</button>'
    '<span class="rv-ed-sep"></span>'
    '<button type="button" data-ed="reset" title="この文章の編集を元に戻す">リセット</button>'
    '<span class="rv-ed-hint">Enter で改行・Esc で確定</span></div>'
)

CSS = r"""
.rv .top .rv-edit-sw{margin-left:auto}
.rv .rv-edit-sw{display:inline-flex;gap:6px;align-items:center;cursor:pointer;font-size:13px;font-weight:700;color:var(--fg);background:#22406A;border:1px solid #5B86C4;border-radius:14px;padding:2px 12px}
.rv.editing .rv-edit-sw{background:#5AA9FF;border-color:#5AA9FF;color:#0F1623}
.rv:not(.editing) .rv-edit-bar{display:none}
.rv .rv-edit-bar{display:flex;flex-wrap:wrap;align-items:center;gap:8px 10px;background:var(--panel);border:1px solid var(--rv-line);border-left:3px solid #5AA9FF;padding:8px 12px;font-size:13px}
.rv .rv-ed-l{color:var(--sub);display:inline-flex;gap:6px;align-items:center}
.rv .rv-ed-sep{width:1px;align-self:stretch;background:var(--rv-line)}
.rv .rv-edit-bar button,.rv .rv-edit-bar input[type=number]{font:inherit;font-size:13px;color:var(--fg);background:#25406A;border:1px solid var(--rv-line);padding:3px 10px;min-height:30px;cursor:pointer}
.rv .rv-edit-bar button:hover{border-color:#5AA9FF}
.rv .rv-edit-bar input[type=number]{width:64px;text-align:center;cursor:text}
.rv .rv-ed-sws{display:inline-flex;gap:6px;align-items:center;background:#EEF2F8;border-radius:16px;padding:3px 7px}
.rv .rv-edit-bar .rv-ed-sw{width:22px;height:22px;min-height:0;padding:0;border-radius:50%;border:1px solid #9AA7BA}
.rv .rv-edit-bar input[type=color]{width:34px;height:28px;padding:0 2px;border:1px solid var(--rv-line);background:#25406A;cursor:pointer}
.rv .rv-ed-hint{margin-left:auto;color:var(--sub);font-size:12.5px}
.rv.editing .pt-layer,.rv.editing .co-layer{display:none!important}
.rv.editing .big [contenteditable]{outline:calc(1.5px / var(--s)) dashed #3B8EEA;outline-offset:calc(2px / var(--s));cursor:text}
.rv:not(.editing) .rv-chart-panel{display:none}
.rv .rv-chart-panel[hidden]{display:none}
.rv .rv-chart-panel{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px;background:var(--panel);border:1px solid var(--rv-line);border-left:3px solid #5AA9FF;padding:8px 12px;font-size:13px}
.rv .rv-chart-panel label{display:inline-flex;gap:6px;align-items:center;color:var(--sub)}
.rv .rv-chart-panel input{font:inherit;font-size:13px;color:var(--fg);background:#25406A;border:1px solid var(--rv-line);padding:3px 8px;min-height:30px;width:150px}
.rv .rv-chart-panel .rv-cp-h{font-weight:700;color:var(--fg)}
.rv.editing .big .pp-chart{cursor:pointer;outline:calc(1.5px / var(--s)) dashed #3B8EEA;outline-offset:calc(2px / var(--s))}
.rv.editing .big [contenteditable]:focus{outline:calc(2px / var(--s)) solid #3B8EEA;background:rgba(59,142,234,.08)}
"""

JS = r"""
  // ---- 編集モード（reviewext）。スイッチがオフの間は、どの処理も何もしない ----
  var editing = false, lastRange = null;
  var TEXT_CLASSES = ['t-white', 't-accent', 't-emph', 't-sub', 't-dark', 'b'];

  // 編集できる文字の対象（文書順）。fragedit.targets と同じ規則: 容器は .pp-text と .pp-table の中の td・th。
  // .pp-picture の中と、容器の中の容器は数えない。容器が直下に p・ul>li・ol>li を持てばそれらが 1 つずつ、なければ容器そのもの
  function editTargets(root) {
    var boxes = [], out = [];
    (function visit(n) {
      for (var c = n.firstElementChild; c; c = c.nextElementSibling) {
        if (c.classList.contains('pp-picture')) continue;
        var cell = (c.localName === 'td' || c.localName === 'th') && c.parentElement && c.parentElement.closest('.pp-table');
        if (c.classList.contains('pp-text') || cell) boxes.push(c); else visit(c);
      }
    })(root);
    boxes.forEach(function (c) {
      var b = [];
      for (var ch = c.firstElementChild; ch; ch = ch.nextElementSibling) {
        if (ch.localName === 'p') b.push(ch);
        else if (ch.localName === 'ul' || ch.localName === 'ol') {
          for (var li = ch.firstElementChild; li; li = li.nextElementSibling) if (li.localName === 'li') b.push(li);
        }
      }
      out.push.apply(out, b.length ? b : [c]);
    });
    return out;
  }

  // fragedit.sanitize_inline と同じ: b・strong・span（許した class と style だけ）・br 以外を外す。script・style は中身ごと消す
  var HEX = /^#[0-9a-fA-F]{3,8}$/, VAR = /^var\(--[A-Za-z0-9_-]+\)$/, PX = /^\d+px$/,
      RGB = /^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*[\d.]+\s*)?\)$/;
  function cssColor(v) {
    v = v.trim();
    if (HEX.test(v) || VAR.test(v)) return v;
    var m = RGB.exec(v);
    if (m && +m[1] <= 255 && +m[2] <= 255 && +m[3] <= 255) {
      return '#' + [m[1], m[2], m[3]].map(function (x) { return ('0' + (+x).toString(16).toUpperCase()).slice(-2); }).join('');
    }
    return null;
  }
  function cleanStyle(s) {
    var out = [];
    s.split(';').forEach(function (d) {
      var i = d.indexOf(':'); if (i < 0) return;
      var k = d.slice(0, i).trim().toLowerCase(), v = d.slice(i + 1).trim();
      if (k === 'color') v = cssColor(v);
      else if (k === 'font-size') v = PX.test(v) ? v : null;
      else if (k === 'font-weight') v = (v === '700' || v === '400' || v === 'bold') ? v : null;
      else v = null;
      if (v) out.push(k + ':' + v);
    });
    return out.join(';');
  }
  function escText(t) { return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\u00a0/g, '&nbsp;'); }
  function cleanInto(n, out) {
    for (var c = n.firstChild; c; c = c.nextSibling) {
      if (c.nodeType === 3) { out.push(escText(c.data)); continue; }
      if (c.nodeType !== 1) continue;
      var tag = c.localName;
      if (tag === 'script' || tag === 'style') continue;
      if (tag === 'br') { out.push('<br>'); continue; }
      if (tag !== 'b' && tag !== 'strong' && tag !== 'span') { cleanInto(c, out); continue; }
      var a = '';
      if (tag === 'span') {
        var cls = (c.getAttribute('class') || '').split(/\s+/).filter(function (x) { return TEXT_CLASSES.indexOf(x) >= 0; });
        if (cls.length) a += ' class="' + cls.join(' ') + '"';
        var st = cleanStyle(c.getAttribute('style') || '');
        if (st) a += ' style="' + st + '"';
      }
      out.push('<' + tag + a + '>'); cleanInto(c, out); out.push('</' + tag + '>');
    }
  }
  function sanitizeHtml(html) {
    var t = document.createElement('template'); t.innerHTML = html;          // template の中では script も画像の読み込みも動かない
    var out = []; cleanInto(t.content, out);
    t.innerHTML = out.join(''); mergeSpans(t.content);                       // 通したあとの形で、入れ子の span をまとめる
    out = []; cleanInto(t.content, out);
    return out.join('');
  }

  // span の指定（prop）: 'size' は style の font-size、'color' は文字色のクラスか style の color
  var COLOR_CLASSES = ['t-white', 't-accent', 't-emph', 't-sub', 't-dark'];
  function classesOf(s) { return (s.getAttribute('class') || '').split(/\s+/).filter(Boolean); }
  function decls(s) {
    var o = [];
    (s.getAttribute('style') || '').split(';').forEach(function (d) { var i = d.indexOf(':'); if (i > 0) o.push([d.slice(0, i).trim().toLowerCase(), d.slice(i + 1).trim()]); });
    return o;
  }
  function setAttrs(s, cls, o) {
    if (cls.length) s.setAttribute('class', cls.join(' ')); else s.removeAttribute('class');
    if (o.length) s.setAttribute('style', o.map(function (d) { return d[0] + ':' + d[1]; }).join(';')); else s.removeAttribute('style');
  }
  function keyOf(prop) { return prop === 'size' ? 'font-size' : 'color'; }
  function hasProp(s, prop) {
    return decls(s).some(function (d) { return d[0] === keyOf(prop); }) ||
      (prop === 'color' && classesOf(s).some(function (c) { return COLOR_CLASSES.indexOf(c) >= 0; }));
  }
  function unwrap(n) { while (n.firstChild) n.parentNode.insertBefore(n.firstChild, n); n.remove(); }
  function dropProp(s, prop) {                               // 指定を外す。属性がなくなった span は中身だけ残す
    setAttrs(s, classesOf(s).filter(function (c) { return prop !== 'color' || COLOR_CLASSES.indexOf(c) < 0; }),
      decls(s).filter(function (d) { return d[0] !== keyOf(prop); }));
    if (!s.attributes.length) unwrap(s);
  }
  // 中が span 1 つだけの span は、1 つにまとめる（内側の指定が勝つ）。fragedit._merge_spans と同じ規則
  function mergeSpans(n) {
    for (var c = n.firstChild; c; c = c.nextSibling) {
      if (c.nodeType !== 1) continue;
      while (c.localName === 'span' && c.childNodes.length === 1 && c.firstChild.localName === 'span') {
        var k = c.firstChild, kc = classesOf(k), kd = decls(k), keys = kd.map(function (d) { return d[0]; });
        var col = hasProp(k, 'color'), wt = kc.indexOf('b') >= 0 || keys.indexOf('font-weight') >= 0;
        var cls = classesOf(c).filter(function (x) { return !(col && COLOR_CLASSES.indexOf(x) >= 0) && !(wt && x === 'b'); });
        kc.forEach(function (x) { if (cls.indexOf(x) < 0) cls.push(x); });
        setAttrs(c, cls, decls(c).filter(function (d) {
          return keys.indexOf(d[0]) < 0 && !(col && d[0] === 'color') && !(wt && d[0] === 'font-weight');
        }).concat(kd));
        unwrap(k);
      }
      mergeSpans(c);
    }
  }

  // 記録: p.__rvEd = { "<f>#<t>": {f, t, before, after} }。元の内容（before）は、最初に書き換える前に p.__rvOrig へ取っておく
  function editsOf(p) { return p.__rvEd || (p.__rvEd = {}); }
  function thumbsOf(p, f) {
    return $$('[data-f]', p).filter(function (h) { return h.dataset.f === f; })
      .map(function (h) { return $('.stage .slide', h); }).filter(Boolean);
  }
  // グラフのラベル（t = c<i>.cat<j> | c<i>.ser<j>）。c<i> は断片の .pp-chart を文書順に数える（.pp-picture の中は数えない。fragedit と同じ）
  var CHART_T = /^c(\d+)\.(cat|ser)(\d+)$/;
  function chartsOf(root) { return $$('.pp-chart', root).filter(function (h) { return !h.closest('.pp-picture'); }); }
  function chartSpec(h) { try { return JSON.parse(h.dataset.chart); } catch (e) { return null; } }
  function labelOf(root, t) {                                  // 今のラベル。なければ null
    var m = CHART_T.exec(t), h = m && chartsOf(root)[+m[1]], d = h && chartSpec(h);
    var x = d && (m[2] === 'cat' ? (d.categories || [])[+m[3]] : ((d.series || [])[+m[3]] || {}).name);
    return typeof x === 'string' ? x : null;
  }
  function setLabel(root, t, v) {                              // data-chart の JSON を書き換えて描き直す
    var m = CHART_T.exec(t), h = m && chartsOf(root)[+m[1]], d = h && chartSpec(h);
    if (!d || labelOf(root, t) === null) return;
    if (m[2] === 'cat') d.categories[+m[3]] = v; else d.series[+m[3]].name = v;
    h.dataset.chart = JSON.stringify(d);
    if (window.__chartPreview) window.__chartPreview(h);
  }
  function origOf(p, f, t) {
    var m = p.__rvOrig || (p.__rvOrig = {}), k = f + '#' + t;
    if (!Object.prototype.hasOwnProperty.call(m, k)) {
      var s = thumbsOf(p, f)[0], x = s && editTargets(s)[+t.slice(1)];
      m[k] = t[0] === 'c' ? (s ? labelOf(s, t) : '') : x ? x.innerHTML : '';
    }
    return m[k];
  }
  function setHtml(x, h) {                                   // 同じ内容なら触らない（選択範囲を壊さない）
    var n = document.createElement('div'); n.innerHTML = h;
    if (n.innerHTML !== x.innerHTML) x.innerHTML = h;
  }
  function writeThumbs(p, f, t, h) {
    thumbsOf(p, f).forEach(function (s) { var x = editTargets(s)[+t.slice(1)]; if (x) setHtml(x, h); });
  }
  function applyEdits(p, ed) {                               // 保存してあった編集を、サムネの断片へ書き戻す（restore から）
    Object.keys(ed || {}).forEach(function (k) {
      var r = ed[k];
      if (!r || typeof r.f !== 'string' || typeof r.after !== 'string') return;
      var s = thumbsOf(p, r.f)[0];
      if (CHART_T.test(r.t)) {                                         // グラフのラベルは文字列そのまま（HTML ではない）
        var o0 = s && labelOf(s, r.t);
        if (o0 === null || o0 === undefined || r.before !== o0 || r.after === o0) return;
        origOf(p, r.f, r.t);
        thumbsOf(p, r.f).forEach(function (x) { setLabel(x, r.t, r.after); });
        editsOf(p)[k] = { f: r.f, t: r.t, before: o0, after: r.after };
        return;
      }
      if (!/^t\d+$/.test(r.t) || !s || !editTargets(s)[+r.t.slice(1)]) return;                // 断片が変わって対象がなくなっていれば、引き継がない
      var orig = origOf(p, r.f, r.t);
      var after = sanitizeHtml(r.after);                                 // 保存した内容も、書き戻す前にもう一度通す
      // ページを作り直したあと（同じ deck・round で同じ保存先）は、その位置に別の文字があるかもしれない。
      // 元の文字が今の断片と違う記録と、すでに反映済み（今の断片が直した内容）の記録は引き継がない
      if (typeof r.before !== 'string' || sanitizeHtml(r.before) !== sanitizeHtml(orig) || after === sanitizeHtml(orig)) return;
      writeThumbs(p, r.f, r.t, after);
      editsOf(p)[k] = { f: r.f, t: r.t, before: orig, after: after };
    });
  }
  function editLines(p) {
    var e = editsOf(p);
    return Object.keys(e).map(function (k) {
      var j = JSON.stringify({ f: e[k].f, t: e[k].t, before: e[k].before, after: e[k].after });
      return '- 編集: ' + j.replace(/[\u0085\u2028\u2029]/g, function (c) { return '\\u' + ('000' + c.charCodeAt(0).toString(16)).slice(-4); });   // Python の splitlines で行が割れないように
    });
  }

  // 直した文字を確定する（blur・ツールバーの操作のあと）。元と同じに戻したら記録を消す
  function commit(el) {
    var o = el.__rv; if (!o) return;
    var raw = el.innerHTML; if (raw === o.start) return;
    var key = o.f + '#' + o.t, eds = editsOf(o.p), orig = origOf(o.p, o.f, o.t);
    var after = sanitizeHtml(raw), now;
    if (after === sanitizeHtml(orig)) { delete eds[key]; now = orig; }
    else { eds[key] = { f: o.f, t: o.t, before: orig, after: after }; now = after; }
    writeThumbs(o.p, o.f, o.t, now);
    setHtml(el, now);
    o.start = el.innerHTML;
    store(snapshot());
  }
  function insertNode(n) {
    var s = getSelection(); if (!s.rangeCount) return;
    var r = s.getRangeAt(0); r.deleteContents(); r.insertNode(n); r.setStartAfter(n); r.collapse(true);
    s.removeAllRanges(); s.addRange(r);
  }
  function lineBreak() { if (!document.execCommand('insertLineBreak')) insertNode(document.createElement('br')); }
  function insertText(t) { if (t && !document.execCommand('insertText', false, t)) insertNode(document.createTextNode(t)); }
  function onKey(e) {
    if (e.isComposing || e.keyCode === 229) return;          // 変換中の Enter は IME に任せる
    if (e.key === 'Enter') { e.preventDefault(); lineBreak(); }
    else if (e.key === 'Escape') { e.preventDefault(); this.blur(); }
  }
  function onPaste(e) {                                      // 貼り付けは文字だけ（装飾・タグは持ち込まない）
    e.preventDefault();
    var t = e.clipboardData ? e.clipboardData.getData('text/plain') : '';
    t.split(/\r?\n/).forEach(function (line, i) { if (i) lineBreak(); insertText(line); });
  }
  // showBig の最後から呼ぶ。編集中なら、大きな 1 案の対象を編集できるようにする（src はサムネの断片）
  function enableEdit(p, clone, src) {
    closePanel();
    if (!editing || !src) return;
    var h = src.closest('[data-f]'); if (!h) return;
    chartsOf(clone).forEach(function (c, i) { c.addEventListener('click', function () { openPanel(p, h.dataset.f, i, c); }); });
    editTargets(clone).forEach(function (el, i) {
      el.setAttribute('contenteditable', 'true');
      el.__rv = { p: p, f: h.dataset.f, t: 't' + i, start: el.innerHTML };
      el.addEventListener('keydown', onKey);
      el.addEventListener('paste', onPaste);
      el.addEventListener('blur', function () { commit(el); });
    });
  }
  // グラフのラベル用パネル（ページに 1 つだけ。開くたびに今のスライドのツールバーの下へ移す）。数値（values）は直せない
  var panel = null;
  function closePanel() { if (panel) panel.hidden = true; }
  function openPanel(p, f, i, host) {
    var d = chartSpec(host), bar = $('.rv-edit-bar', p); if (!d || !bar) return;
    if (!panel) { panel = document.createElement('div'); panel.className = 'rv-chart-panel'; panel.setAttribute('aria-label', 'グラフのラベル'); }
    bar.insertAdjacentElement('afterend', panel);
    panel.innerHTML = '<span class="rv-cp-h">グラフのラベル</span>';
    function field(name, t, v) {
      var l = document.createElement('label'), inp = document.createElement('input');
      l.appendChild(document.createTextNode(name)); inp.type = 'text'; inp.value = v; inp.dataset.t = t;
      inp.addEventListener('input', function () { chartLabel(p, f, host, t, inp.value); });
      l.appendChild(inp); panel.appendChild(l);
    }
    (d.categories || []).forEach(function (c, j) { field('カテゴリ' + (j + 1), 'c' + i + '.cat' + j, c); });
    (d.series || []).forEach(function (s, j) { field('系列' + (j + 1), 'c' + i + '.ser' + j, s.name); });
    panel.hidden = false;
  }
  function chartLabel(p, f, host, t, v) {                    // 大きな 1 案とサムネの断片を直し、元に戻したら記録を消す
    var eds = editsOf(p), key = f + '#' + t, orig = origOf(p, f, t);
    if (v === orig) delete eds[key]; else eds[key] = { f: f, t: t, before: orig, after: v };
    setLabel(host.closest('.slide'), t, v);
    thumbsOf(p, f).forEach(function (x) { setLabel(x, t, v); });
    store(snapshot());
  }
  function setEditing(on) {
    var a = document.activeElement;
    if (a && a.__rv) commit(a);
    editing = !!on;
    $('.rv').classList.toggle('editing', editing);
    $$('.rv-edit-toggle').forEach(function (x) { x.checked = editing; });
    if (!editing) closePanel();
    if (!editing) { lastRange = null; $$('[contenteditable]').forEach(function (x) { x.removeAttribute('contenteditable'); }); }
    var p = panes[cur]; if (p && p.dataset.doc !== '1') showBig(p, viewKey(p));
  }

  // ツールバー: 選んだ文字（最後に選んだ範囲）を b / span で包む
  function hostOf(n) { for (; n && n !== document; n = n.parentNode) if (n.__rv) return n; return null; }
  function startEl(r) { var n = r.startContainer; return n.nodeType === 1 ? n : n.parentElement; }
  // 押したツールバーのスライド（pane）の、見えている対象だけを返す（隠れた前のスライドに残った選択には効かせない）
  function picked(pane) {
    var r = lastRange; if (!editing || !r || r.collapsed || !pane || pane.hidden) return null;
    var el = hostOf(r.commonAncestorContainer);
    return el && document.contains(el) && el.__rv.p === pane ? { r: r, el: el } : null;
  }
  // 操作のあと: 空になった b・span を消して確定し、同じ文字（a〜z）を選び直す。確定で HTML が整え直されても、文字の位置で選べる
  function finish(el, a, z) {
    var s = -1, e = -1, r = document.createRange();
    if (a) { r.selectNodeContents(el); r.setEndBefore(a); s = r.toString().length; r.setStartBefore(a); r.setEndAfter(z); e = s + r.toString().length; }
    $$('b,strong,span', el).forEach(function (x) { if (!x.textContent && !x.querySelector('br')) x.remove(); });
    el.normalize();
    commit(el);
    if (e <= s) return;
    var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), n, at = 0, got = false;
    r = document.createRange();
    while ((n = w.nextNode())) {
      var end = at + n.data.length;
      if (!got && s < end) { r.setStart(n, s - at); got = true; }
      if (got && e <= end) { r.setEnd(n, e - at); break; }
      at = end;
    }
    if (!got) return;
    var sel = getSelection(); sel.removeAllRanges(); sel.addRange(r); lastRange = r.cloneRange();
  }
  function isolate(t, r) {                                   // t を「r の前・r・r の後」に分け、t には r の中身だけを残す
    var a = document.createRange(); a.setStartBefore(t); a.setEnd(r.startContainer, r.startOffset);
    t.parentNode.insertBefore(a.extractContents(), t);
    var b = document.createRange(); b.setStart(r.endContainer, r.endOffset); b.setEndAfter(t);
    t.parentNode.insertBefore(b.extractContents(), t.nextSibling);
  }
  // 選んだ文字の指定（prop）を k:v（k が 'class' なら色のクラス）にする。同じ指定の span は入れ子にしない:
  // 祖先にあればその span を選んだ範囲で分けて直し、なければ新しい span で包む。包んだ中の同じ指定は外す
  function setProp(pane, prop, k, v) {
    var c = picked(pane); if (!c) return;
    var t = null;
    for (var n = c.r.commonAncestorContainer; n && n !== c.el; n = n.parentNode) if (n.localName === 'span' && hasProp(n, prop)) t = n;
    if (t) isolate(t, c.r);
    else { t = document.createElement('span'); t.appendChild(c.r.extractContents()); c.r.insertNode(t); }
    $$('span', t).forEach(function (s) { if (hasProp(s, prop)) dropProp(s, prop); });
    var cls = classesOf(t).filter(function (x) { return prop !== 'color' || COLOR_CLASSES.indexOf(x) < 0; });
    var o = decls(t).filter(function (d) { return d[0] !== keyOf(prop) || d[0] === k; }), i = -1;
    o.forEach(function (d, j) { if (d[0] === k) i = j; });
    if (k === 'class') cls.push(v); else if (i >= 0) o[i] = [k, v]; else o.push([k, v]);
    setAttrs(t, cls, o);
    finish(c.el, t, t);
  }
  function toggleBold(pane) {
    var c = picked(pane); if (!c) return;
    var b = null;
    for (var n = c.r.commonAncestorContainer; n && n !== c.el; n = n.parentNode) if (n.localName === 'b' || n.localName === 'strong') b = n;
    if (!b) {
      b = document.createElement('b'); b.appendChild(c.r.extractContents());
      $$('b,strong', b).forEach(unwrap);                     // 太字の中の太字は外す
      c.r.insertNode(b);
      return finish(c.el, b, b);
    }
    var first = b.firstChild, last = b.lastChild;
    unwrap(b);
    finish(c.el, first, last);
  }
  // リセット: フォーカスのある対象（なければ、最後に選んだ範囲を含む対象）を元の内容に戻し、その記録を消す。
  // 対象がない、または押したツールバーのスライド（pane）の対象でなければ何もしない（隠れた前のスライドの編集を戻さない）
  function resetTarget(pane) {
    var a = document.activeElement, el = a && a.__rv ? a : (lastRange ? hostOf(lastRange.commonAncestorContainer) : null);
    if (!editing || !el || !el.__rv || !document.contains(el) || el.__rv.p !== pane || pane.hidden) return;
    var o = el.__rv, orig = origOf(o.p, o.f, o.t);
    delete editsOf(o.p)[o.f + '#' + o.t];
    writeThumbs(o.p, o.f, o.t, orig);
    el.innerHTML = orig;
    o.start = el.innerHTML;
    lastRange = null;
    store(snapshot());
  }
  function resize(pane, delta) {
    var c = picked(pane); if (!c) return;
    var cur0 = parseFloat(getComputedStyle(startEl(c.r)).fontSize) || 16;
    setProp(pane, 'size', 'font-size', Math.max(1, Math.round(cur0 + delta)) + 'px');
  }
  document.addEventListener('selectionchange', function () {
    if (!editing) return;
    var s = getSelection(); if (!s.rangeCount) return;
    var r = s.getRangeAt(0), el = hostOf(r.commonAncestorContainer); if (!el) return;
    lastRange = r.cloneRange();
    var size = $('.rv-edit-bar .rv-ed-size', el.__rv.p);
    if (size && document.activeElement !== size) size.value = Math.round(parseFloat(getComputedStyle(startEl(r)).fontSize)) || '';
  });
  $$('.rv-edit-bar').forEach(function (bar) {
    var pane = bar.closest('.pane');
    bar.addEventListener('mousedown', function (e) { if (e.target.closest('button')) e.preventDefault(); });   // 押しても文字の選択を外さない
    bar.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-ed]'); if (!b) return;
      var k = b.dataset.ed;
      if (k === 'bold') toggleBold(pane);
      else if (k === 'cls') setProp(pane, 'color', 'class', b.dataset.v);
      else if (k === 'reset') resetTarget(pane);
      else if (k === 'size') resize(pane, +b.dataset.v);
    });
    $('.rv-ed-color', bar).addEventListener('change', function () { setProp(pane, 'color', 'color', this.value); });
    $('.rv-ed-size', bar).addEventListener('change', function () { var v = Math.round(+this.value); if (v > 0) setProp(pane, 'size', 'font-size', v + 'px'); });
  });
  $$('.rv-edit-toggle').forEach(function (cb) { cb.onchange = function () { setEditing(this.checked); }; });
  window.setEditing = setEditing;
  window.editTargets = editTargets;
  window.sanitizeHtml = sanitizeHtml;

"""
