"""レビューページの「AI に頼む」の依頼を出す側（待ち受けの判定・キュー・応答なしの処理）。ページに足す CSS・JS を持つ。

Claude は window.__aiWatchAt に最後に待ち受けた時刻（Date.now()）を立て、window.__aiQueue の依頼を読んで処理し、
結果を window.__aiReply({id, ok, ...}) で返す。部位の行の「頼む」は、待ち受け中（__aiWatchAt が 130 秒以内）で、
その断片の依頼が未処理でないときだけ押せる。依頼から 180 秒返事がなければ「応答なし」にして、指示は部位のコメントに残す。
JS は reviewext.JS の直後（variants._SCRIPT の IIFE の中）に入り、$・$$・panes・viewKey・dsel・editLines を使う。
CSS のクラス名は .rv の下に置く。"""

JS = r"""
  // ---- AI に頼む: 依頼を出す ----
  var AI_LEASE = 130000, AI_TIMEOUT = 180000, aiSeq = 0;
  var aiPending = {};                                          // 未処理の依頼の表: id → {p, f, key, timer}（返事・応答なしで消す）
  window.__aiQueue = [];                                       // Claude が読む未処理の依頼
  function aiWatching() { return Date.now() - (window.__aiWatchAt || 0) < AI_LEASE; }
  function aiFrag(p, key) {                                    // 部位の行の key（案|部位名）から、直す断片の名前と案・デザイン
    var k = key.slice(0, key.indexOf('|')) || viewKey(p), d = dsel(p, k);
    var h = (d > 1 ? $('.dopt[data-k="' + k + '"][data-d="' + d + '"]', p) : null) || $('.opt[data-k="' + k + '"]', p);
    return { k: k, d: d, f: h ? h.dataset.f : '' };
  }
  function aiBusy(p, f) { return Object.keys(aiPending).some(function (id) { return aiPending[id].p === p && aiPending[id].f === f; }); }
  function aiRefresh(p) { (p ? [p] : panes).forEach(aiPaint); }
  function aiPaint(p) {
    var st = $('.aiState', p); if (!st) return;
    var rows = $$('.plist li', p), busy = false;
    rows.forEach(function (li) {
      var q = aiBusy(p, aiFrag(p, li.dataset.key).f), b = $('.aiAsk', li);
      busy = busy || q;
      if (b) b.disabled = !aiWatching() || q;
    });
    st.textContent = !rows.length ? '' : busy ? 'Claude が直しています…'
      : p.__aiLost ? '応答がありません。指示を部位のコメントに移しました'
      : aiWatching() ? '' : 'いま Claude が待ち受けていません。指示を回答に入れて送ると、あとで直します';
  }
  function aiDrop(id) {                                        // 依頼を表とキューから外す（返事・応答なし）
    var r = aiPending[id]; if (!r) return null;
    clearTimeout(r.timer); delete aiPending[id];
    window.__aiQueue = window.__aiQueue.filter(function (q) { return q.id !== id; });
    return r;
  }
  window.__rvAiAsk = function (p, key, li) {
    var text = $('textarea', li).value, fr = aiFrag(p, key);
    if (!text.trim() || !aiWatching() || aiBusy(p, fr.f)) return;
    var id = 'ai-' + (++aiSeq);
    var edits = editLines(p).filter(function (l) { try { return JSON.parse(l.slice('- 編集: '.length)).f === fr.f; } catch (e) { return false; } });
    window.__aiQueue.push({ id: id, type: 'edit', slide: p.dataset.slide, k: fr.k, d: fr.d, f: fr.f, part: key.slice(key.indexOf('|') + 1), text: text, edits: edits });
    aiPending[id] = { p: p, f: fr.f, key: key, timer: setTimeout(function () {
      var r = aiDrop(id); if (!r) return;
      r.p.__aiLost = true; aiPaint(r.p);                       // 指示は部位のコメント（textarea）にそのまま残る
    }, AI_TIMEOUT) };
    p.__aiLost = false; aiPaint(p);
  };
  // Claude の返事。依頼の表にない id（応答なしにしたあとの返事）は、何もしない
  window.__aiReply = function (r) {
    if (!r || !aiPending[r.id]) return;
    aiDrop(r.id); aiRefresh();
  };
  window.__rvAiRefresh = aiRefresh;
  setInterval(function () { aiRefresh(); }, 1000);             // Claude が待ち受けの時刻を立てたのを拾う
"""

CSS = r"""
.rv .aiAsk{white-space:nowrap}
.rv .aiAsk:disabled{opacity:.45;cursor:not-allowed}
.rv .aiState{font-size:12.5px;color:var(--sub);margin-top:6px}
.rv .aiState:empty{display:none}
"""
