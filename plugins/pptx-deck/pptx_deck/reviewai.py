"""レビューページの「AI に頼む」の依頼を出す側（待ち受けの判定・キュー・応答なしの処理）。ページに足す CSS・JS を持つ。

Claude は window.__aiWatchAt に最後に待ち受けた時刻（Date.now()）を立て、window.__aiQueue の依頼を読んで処理し、
結果を window.__aiReply({id, ok, ...}) で返す（受け付けたら true、無視したら false）。部位の行の「頼む」は、待ち受け中
（__aiWatchAt が 130 秒以内）で、その断片の依頼が未処理でないときだけ押せる。依頼から 180 秒返事がなければ「応答なし」にして、
指示は部位のコメントに残す。依頼中の断片は、編集モードでも直せない（reviewext の enableEdit・commit が __rvAiBusy を見る）。
JS は reviewext.JS の直後（variants._SCRIPT の IIFE の中）に入り、$・$$・panes・cur・viewKey・dsel・showBig・editing・editLines を使う。
CSS のクラス名は .rv の下に置く。"""

JS = r"""
  // ---- AI に頼む: 依頼を出す ----
  var AI_LEASE = 130000, AI_TIMEOUT = 180000, aiSeq = 0;
  var aiPending = {};                                          // 未処理の依頼の表: id → {p, f, key, text, undo, timer}（返事・応答なしで消す）
  window.__aiQueue = [];                                       // Claude が読む未処理の依頼
  function aiWatching() { return Date.now() - (window.__aiWatchAt || 0) < AI_LEASE; }
  function aiFrag(p, key) {                                    // 部位の行の key（案|部位名）から、直す断片の名前と案・デザイン
    var k = key.slice(0, key.indexOf('|')) || viewKey(p), d = dsel(p, k);
    var h = (d > 1 ? $('.dopt[data-k="' + k + '"][data-d="' + d + '"]', p) : null) || $('.opt[data-k="' + k + '"]', p);
    return { k: k, d: d, f: h ? h.dataset.f : '' };
  }
  function aiBusy(p, f) { return Object.keys(aiPending).some(function (id) { return aiPending[id].p === p && aiPending[id].f === f; }); }
  window.__rvAiBusy = aiBusy;                                  // reviewext: 依頼中の断片は編集モードで直せない
  window.__rvAiPending = function (p) { return Object.keys(aiPending).some(function (id) { return aiPending[id].p === p; }); };   // 回答をコピーの確認
  function aiRedraw(p, f) {                                    // 編集モードで断片 f を大きく表示していれば描き直す（直せる・直せないを enableEdit で付け直す）
    var v = viewKey(p);
    if (editing && p === panes[cur] && aiFrag(p, v + '|').f === f) showBig(p, v);
  }
  function aiRefresh(p) { (p ? [p] : panes).forEach(aiPaint); }
  function aiPaint(p) {
    var st = $('.aiState', p); if (!st) return;
    var rows = $$('.plist li', p), busy = false;
    rows.forEach(function (li) {
      var q = aiBusy(p, aiFrag(p, li.dataset.key).f), b = $('.aiAsk', li);
      busy = busy || q;
      if (b) b.disabled = !aiWatching() || q;
    });
    var undos = $$('.aiUndo', p);
    undos.forEach(function (b) { var q = aiBusy(p, b.closest('[data-f]').dataset.f); busy = busy || q; b.disabled = !aiWatching() || q; });
    st.textContent = !rows.length && !undos.length ? '' : busy ? 'Claude が直しています…'
      : p.__aiErr ? p.__aiErr : p.__aiLost ? '応答がありません。指示を部位のコメントに移しました'
      : aiWatching() ? '' : !rows.length ? '元に戻すには Claude の待ち受けが必要です'
      : 'いま Claude が待ち受けていません。指示を回答に入れて送ると、あとで直します';
  }
  function aiDrop(id) {                                        // 依頼を表とキューから外す（返事・応答なし）
    var r = aiPending[id]; if (!r) return null;
    clearTimeout(r.timer); delete aiPending[id];
    window.__aiQueue = window.__aiQueue.filter(function (q) { return q.id !== id; });
    return r;
  }
  function aiTimeout(id) {                                     // 180 秒返事がない
    var r = aiDrop(id); if (!r) return;
    if (r.undo) r.p.__aiErr = '応答がありません';              // 元に戻すは、移す指示がない
    else r.p.__aiLost = true;                                  // 指示は部位のコメント（textarea）にそのまま残る
    aiPaint(r.p); aiRedraw(r.p, r.f);
  }
  function aiKD(p, f) {                                        // 断片 f の案と、デザイン（.opt なら 1）
    var h = $$('.opt[data-f], .dopt[data-f]', p).filter(function (x) { return x.dataset.f === f; })[0];
    return h ? { k: h.dataset.k, d: Number(h.dataset.d || 1) } : { k: '', d: 1 };
  }
  function aiAfterPaint(p) {                                   // 直したあとの「元に戻す」「頼み直す」
    var box = $('.aiAfter', p); if (!box) return;
    box.textContent = '';
    Object.keys(p.__rvAi || {}).forEach(function (f) {
      var d = document.createElement('div'); d.dataset.f = f;
      d.innerHTML = '<span></span> <button type="button" class="b1 aiUndo">元に戻す</button> <button type="button" class="b1 aiRetry">頼み直す</button>';
      $('span', d).textContent = '「' + p.__rvAi[f].part + '」を直しました';
      $('.aiUndo', d).onclick = function () { aiUndoAsk(p, f); };
      $('.aiRetry', d).onclick = function () {
        var a = p.__rvAi[f], li = partRow(p, aiKD(p, f).k + '|' + a.part, a.text);
        li.dataset.retry = '1';                                // この行から頼むと、Claude は前の AI の結果を戻してから直し直す
        $('textarea', li).focus();
      };
      box.appendChild(d);
    });
    aiPaint(p);
  }
  function aiUndoAsk(p, f) {
    if (!aiWatching() || aiBusy(p, f)) return;
    var id = 'ai-' + Date.now().toString(36) + '-' + (++aiSeq), kd = aiKD(p, f);
    window.__aiQueue.push({ id: id, type: 'undo', slide: p.dataset.slide, k: kd.k, d: kd.d, f: f, part: '', text: '', edits: [], retry: false, idx: -1 });
    aiPending[id] = { p: p, f: f, key: '', text: '', undo: true, timer: setTimeout(function () { aiTimeout(id); }, AI_TIMEOUT) };
    p.__aiLost = false; p.__aiErr = ''; aiPaint(p); aiRedraw(p, f);
  }
  window.__rvAiAfter = aiAfterPaint;
  window.__rvAiAsk = function (p, key, li) {
    var text = $('textarea', li).value, fr = aiFrag(p, key);
    if (!text.trim() || !aiWatching() || aiBusy(p, fr.f)) return;
    var id = 'ai-' + Date.now().toString(36) + '-' + (++aiSeq);   // ページを開き直しても重ならない
    var retry = li.dataset.retry === '1' && !!(p.__rvAi || {})[fr.f];   // 「頼み直す」の行（元に戻したあとは、ふつうの依頼）
    // 頼み直すは、前の AI の結果を戻してから直し直すので、その上で打ち換えた文字（編集の記録）は送らない
    var edits = retry ? [] : editLines(p).filter(function (l) { try { return JSON.parse(l.slice('- 編集: '.length)).f === fr.f; } catch (e) { return false; } });
    var idx = (p.__ptIdx || {})[key];                          // 断片の中の、data-part の文書順の位置（同名の部位を Claude が特定する）
    if (typeof idx !== 'number') idx = -1;
    window.__aiQueue.push({ id: id, type: 'edit', slide: p.dataset.slide, k: fr.k, d: fr.d, f: fr.f, part: key.slice(key.indexOf('|') + 1), text: text, edits: edits, retry: retry, idx: idx });
    aiPending[id] = { p: p, f: fr.f, key: key, text: text, timer: setTimeout(function () { aiTimeout(id); }, AI_TIMEOUT) };
    p.__aiLost = false; p.__aiErr = ''; aiPaint(p); aiRedraw(p, fr.f);
  };
  // Claude の返事。受け付けたら true。依頼の表にない id（応答なしにしたあと・処理済み）は、何もせず false
  function aiApply(p, f, html) {                               // 断片 f のサムネの中身を置き換え、表示中なら大きな表示も描き直す
    $$('[data-f]', p).filter(function (h) { return h.dataset.f === f; }).forEach(function (h) {
      var st = $('.stage', h); if (!st) return;
      st.innerHTML = html;
      $$('.pp-chart', st).forEach(function (c) { if (window.__chartPreview) window.__chartPreview(c); });
    });
    if (window.__arrows) window.__arrows(p);
    var e = editsOf(p), o = p.__rvOrig || {};                  // この断片への手作業の編集は、新しい断片には当てはまらないので捨てる
    Object.keys(e).forEach(function (k) { if (e[k].f === f) delete e[k]; });
    Object.keys(o).forEach(function (k) { if (k.indexOf(f + '#') === 0) delete o[k]; });
    var v = viewKey(p);
    if (aiFrag(p, v + '|').f === f) showBig(p, v);
  }
  window.__aiReply = function (r) {
    if (!r || !aiPending[r.id]) return false;
    var q = aiDrop(r.id), p = q.p, li = $('.plist li[data-key="' + q.key.replace(/"/g, '\\"') + '"]', p);
    if (r.ok !== true || typeof r.html !== 'string') {         // 失敗: 画面は変えない。指示は欄に残る
      p.__aiLost = false; p.__aiErr = String(r.error || 'error'); aiRefresh(); aiRedraw(p, q.f);
      return r.ok !== true;                         // ok なのに html が無い返事は、ページが適用していないので false
    }
    if (q.undo) {                                              // 元に戻す: 戻した断片で置き換え、もう一度は戻せない（覚えた全文も消す）
      aiApply(p, q.f, r.html); delete (p.__rvAi || {})[q.f];
      p.__aiLost = false; p.__aiErr = ''; aiAfterPaint(p); partChanged(p);
      return true;
    }
    aiApply(p, q.f, r.html);
    if (li) { $('textarea', li).value = ''; li.remove(); }      // 頼んだ内容は回答に出さない（頼み直すために、頼んだ時点の指示を覚えておく）
    // html は、再読み込みしたときに断片を AI の版へ置き換えるため（snapshot() の ai に入る）
    (p.__rvAi || (p.__rvAi = {}))[q.f] = { f: q.f, part: q.key.slice(q.key.indexOf('|') + 1), text: q.text, html: r.html };
    if (p.dataset.auto === '1' && !hasFix(p)) setVerdict(p, '要修正', true);   // 指示で付いた自動の要修正は、指示が消えたら外す
    p.__aiLost = false; p.__aiErr = ''; aiAfterPaint(p); partChanged(p); aiRefresh();
    return true;
  };
  window.__rvAiApply = aiApply;                                // restore(): 再読み込みのとき、覚えた全文で断片を置き換える
  window.__rvAiRefresh = aiRefresh;
  setInterval(function () { aiRefresh(); }, 1000);             // Claude が待ち受けの時刻を立てたのを拾う
"""

CSS = r"""
.rv .aiAsk{white-space:nowrap}
.rv .aiAsk:disabled{opacity:.45;cursor:not-allowed}
.rv .aiState{font-size:12.5px;color:var(--sub);margin-top:6px}
.rv .aiState:empty{display:none}
.rv .aiAfter{margin-top:8px;font-size:12.5px}
.rv .aiAfter:empty{display:none}
.rv .aiUndo:disabled{opacity:.45;cursor:not-allowed}
"""
