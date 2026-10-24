"""絵にする箇所の提案と、読み取った構造の確認（picture-review.html）。

<元データ>/picture-plan.json を、HTML のページにする。
利用者は、提案ごとに「絵にする／しない」、構造の項目ごとに「OK／修正」を選ぶ。
「回答をコピー」で window.__answersMd と window.__submitted が立つ（案の選択のページと同じ受け取り方）。
回答は answers-picture-N.md に保存する。

picture-plan.json の形:
  {"title": "...", "intro": "...",
   "proposals": [{"id": "P1", "title": "S05 通信経路", "reason": "なぜ絵にするとよいか（提案の欄）",
                  "asked": false,                       # true: 利用者が「絵にして」と頼んだ。提案の欄を出さない
                  "summary": "読み取った構造の要約",
                  # items の kind: 要素・関係・順序・強調する 1 点・未確定（xx）など
                  "items": [{"id": "P1-1", "kind": "要素", "text": "FW"}, ...],
                  "source": "素材の出どころ（任意）"}]}

回答（answers-picture-N.md）の形:
  ---
  picture-plan: <名前>
  round: N
  ---
  ## P1
  - 提案: する            （する / しない / 依頼済み）
  - 項目 P1-1: OK
  - 項目 P1-2: 修正｜FW は LB の手前
  - コメント: ...
"""

import hashlib
import html as _html
import json
import re
from pathlib import Path

from . import paths

PLAN_FILE = "picture-plan.json"
OUT_FILE = "picture-review.html"
_ANS_FILE = re.compile(r"^answers-picture-(\d+)\.md$")


def load_plan(work: Path) -> dict:
    f = Path(work) / PLAN_FILE
    if not f.exists():
        raise ValueError(f"{f} がありません（絵にする箇所と構造を picture-plan.json に書いてください）")
    try:
        plan = json.loads(paths.read_text(f))
    except json.JSONDecodeError as e:
        raise ValueError(f"{PLAN_FILE} の JSON が読めません: {e}") from None
    if not isinstance(plan, dict):
        raise ValueError(f"{PLAN_FILE} の最上位は {{...}}（オブジェクト）にしてください")
    props = plan.get("proposals", [])
    if not isinstance(props, list) or not all(isinstance(p, dict) for p in props):
        raise ValueError("proposals は {...} の配列にしてください")
    ids = [p.get("id") for p in props]
    if not ids:
        raise ValueError("proposals が空です")
    if not all(isinstance(i, str) and re.fullmatch(r"P\d+", i) for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("proposals の id は P1, P2 … で、重複できません")
    for p in props:
        items = p.get("items", [])
        if not isinstance(items, list):
            raise ValueError(f"{p['id']} の items は配列にしてください")
        for n, it in enumerate(items, start=1):
            if not isinstance(it, dict):
                raise ValueError(f"{p['id']} の {n} 番目の項目は {{id, text}} のオブジェクトにしてください")
            iid = it.get("id")
            if not isinstance(iid, str) or not re.fullmatch(rf"{p['id']}-\d+", iid):
                raise ValueError(f"{p['id']} の項目の id は {p['id']}-1, {p['id']}-2 … にしてください（{iid!r}）")
            if not isinstance(it.get("text"), str):
                raise ValueError(f"{iid} の項目に text（文字列）がありません")
    return plan


def answer_paths(work: Path) -> list[Path]:
    fs = [(int(m.group(1)), p) for p in Path(work).glob("answers-picture-*.md") if (m := _ANS_FILE.match(p.name))]
    return [p for _, p in sorted(fs)]


def next_round(work: Path) -> int:
    fs = [int(m.group(1)) for p in Path(work).glob("answers-picture-*.md") if (m := _ANS_FILE.match(p.name))]
    return max(fs, default=0) + 1


def parse_answers(md: str) -> dict[str, dict]:
    """{P1: {"proposal": "する", "items": {"P1-1": ("OK", ""), "P1-2": ("修正", "…")}, "comment": "…"}}"""
    out: dict[str, dict] = {}
    cur = None
    for line in md.splitlines():
        m = re.match(r"^## (P\d+)\s*$", line)
        if m:
            cur = out.setdefault(m.group(1), {"proposal": "", "items": {}, "comment": ""})
            continue
        if cur is None:
            continue
        m = re.match(r"^- 提案:\s*(.*)$", line)
        if m:
            cur["proposal"] = m.group(1).strip()
            continue
        m = re.match(r"^- 項目 (P\d+-\d+):\s*(OK|修正)(?:｜(.*))?$", line)
        if m:
            cur["items"][m.group(1)] = (m.group(2), (m.group(3) or "").strip())
            continue
        m = re.match(r"^- コメント:\s*(.*)$", line)
        if m:
            cur["comment"] = m.group(1).strip()
    return out


def merge_answers(mds: list[str]) -> dict[str, dict]:
    """回の順に重ねる。後の回答が前の回答を上書きする（提案・項目ごと）。"""
    out: dict[str, dict] = {}
    for md in mds:
        for pid, a in parse_answers(md).items():
            cur = out.setdefault(pid, {"proposal": "", "items": {}, "comment": ""})
            if a["proposal"]:
                cur["proposal"] = a["proposal"]
            cur["items"].update(a["items"])
            if a["comment"]:
                cur["comment"] = a["comment"]
    return out


def resolve(plan: dict, answers: dict[str, dict]) -> dict:
    """回答から、絵にする箇所・直す項目・未決を求める。未決・修正が 0 件になったら、構造は凍結してよい。"""
    draw, skip, fixes, pending = [], [], [], []
    for p in plan["proposals"]:
        a = answers.get(p["id"], {"proposal": "", "items": {}, "comment": ""})
        decision = "依頼済み" if p.get("asked") else a["proposal"]
        if decision == "しない":
            skip.append(p["id"])
            continue
        if decision not in ("する", "依頼済み"):
            pending.append(f"{p['id']} 提案")
            continue
        draw.append(p["id"])
        for it in p.get("items", []):
            v = a["items"].get(it["id"])
            if v is None:
                pending.append(it["id"])
            elif v[0] == "修正":
                fixes.append({"id": it["id"], "text": it["text"], "comment": v[1]})
    return {"draw": draw, "skip": skip, "fixes": fixes, "pending": pending, "frozen": not fixes and not pending}


_STYLE = """<style>
:root{--rv-bg:#F4F6FA;--rv-panel:#FFFFFF;--rv-line:#C9D2E0;--rv-fg:#1A2233;--rv-sub:#5B6779;--rv-ok:#1E7F5C;--rv-ng:#B4540A;--rv-acc:#1F3A68}
*{box-sizing:border-box}
body{margin:0;background:var(--rv-bg);color:var(--rv-fg);font-family:'BIZ UDPGothic','Yu Gothic','Meiryo',sans-serif;\
font-size:15px;line-height:1.65}
.rv{max-width:960px;margin:0 auto;padding:24px 16px 60px;display:grid;gap:16px}
.rv h1{margin:0;font-size:22px}.rv h2{margin:0;font-size:18px}\
.rv h3{margin:12px 0 4px;font-size:13px;letter-spacing:.06em;color:var(--rv-sub)}
.rv .lead{margin:0;color:var(--rv-sub);font-size:14px;white-space:pre-wrap}
.rv .card{background:var(--rv-panel);border:1px solid var(--rv-line);padding:16px 18px;display:grid;gap:8px}
.rv .why{margin:0;font-size:14px;color:var(--rv-sub)}
.rv .sum{margin:0}
.rv .prop{border:1px solid var(--rv-line);padding:8px 12px;display:flex;\
gap:18px;flex-wrap:wrap;align-items:center;margin:0}
.rv .prop legend{font-size:13px;color:var(--rv-sub);padding:0 6px}
.rv label{cursor:pointer;display:inline-flex;gap:6px;align-items:center;font-weight:700}
.rv ul.items{list-style:none;margin:0;padding:0;display:grid;gap:6px}
.rv ul.items li{display:grid;grid-template-columns:72px 1fr auto;gap:8px 12px;\
align-items:center;border-top:1px solid var(--rv-line);padding-top:6px}
.rv .k{font-size:12px;color:var(--rv-sub)}
.rv .vd{display:flex;gap:6px}
.rv button{font:inherit;font-size:14px;padding:5px 16px;border:1px solid var(--rv-line);background:#fff;\
color:var(--rv-fg);cursor:pointer;border-radius:0}
.rv .vd button[aria-pressed="true"][data-v="OK"]{background:var(--rv-ok);border-color:var(--rv-ok);\
color:#fff;font-weight:700}
.rv .vd button[aria-pressed="true"][data-v="修正"]{background:var(--rv-ng);border-color:var(--rv-ng);\
color:#fff;font-weight:700}
.rv .cm{grid-column:2 / 4;width:100%;font:inherit;font-size:14px;padding:5px 8px;border:1px solid var(--rv-line)}
.rv textarea.gc{width:100%;height:56px;font:inherit;font-size:14px;padding:6px 8px;border:1px solid var(--rv-line)}
.rv .act{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.rv .act button{background:var(--rv-acc);border-color:var(--rv-acc);color:#fff;font-weight:700;padding:8px 28px}
.rv .state{font-size:13.5px;color:var(--rv-ok);font-weight:700}.rv .state.err{color:var(--rv-ng)}
.rv .box{width:100%;height:120px;font:12px/1.4 Consolas,monospace}
.rv [hidden]{display:none!important}
.rv .off .items,.rv .off h3,.rv .off .sum{opacity:.35}
</style>"""

_SCRIPT = """<script>
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var DECK = __DECK__, ROUND = __ROUND__, KEY = 'pptxdeck-picture-' + DECK + '-' + ROUND + '-' + __PLANHASH__;
  function store() { try { sessionStorage.setItem(KEY, JSON.stringify(snap())); } catch (e) {} }
  function snap() {
    var o = {};
    $$('.card').forEach(function (c) {
      var r = $('input[type=radio]:checked', c), it = {};
      $$('li', c).forEach(function (li) { it[li.dataset.i] = { v: li.dataset.v || '', t: $('.cm', li).value }; });
      o[c.dataset.p] = { p: r ? r.value : '', i: it, c: $('.gc', c).value };
    });
    return o;
  }
  function restore() {
    var o; try { o = JSON.parse(sessionStorage.getItem(KEY) || '{}') || {}; } catch (e) { o = {}; }
    $$('.card').forEach(function (c) {
      var a = o[c.dataset.p]; if (!a) return;
      if (a.p) { var r = $('input[value="' + a.p + '"]', c); if (r) r.checked = true; }
      $$('li', c).forEach(function (li) {
        var x = (a.i || {})[li.dataset.i]; if (!x) return;
        li.dataset.v = x.v || ''; $('.cm', li).value = x.t || '';
      });
      $('.gc', c).value = a.c || '';
    });
  }
  function refresh() {
    $$('.card').forEach(function (c) {
      var r = $('input[type=radio]:checked', c);
      c.classList.toggle('off', !!r && r.value === 'しない');
      $$('li', c).forEach(function (li) {
        $$('.vd button', li).forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.v === li.dataset.v); });
        $('.cm', li).hidden = li.dataset.v !== '修正';
      });
    });
  }
  $$('li').forEach(function (li) {
    $$('.vd button', li).forEach(function (b) {
      b.onclick = function () { li.dataset.v = (li.dataset.v === b.dataset.v) ? '' : b.dataset.v; refresh(); store(); };
    });
    $('.cm', li).oninput = store;
  });
  $$('input[type=radio]').forEach(function (r) { r.onchange = function () { refresh(); store(); }; });
  $$('.gc').forEach(function (t) { t.oninput = store; });

  function build() {
    var missing = [], lines = ['---', 'picture-plan: ' + DECK, 'round: ' + ROUND, '---'];
    $$('.card').forEach(function (c) {
      var id = c.dataset.p, asked = c.dataset.asked === '1', r = $('input[type=radio]:checked', c);
      var prop = asked ? '依頼済み' : (r ? r.value : '');
      if (!prop) { missing.push(id + ' の「絵にするか」'); return; }
      lines.push('## ' + id, '- 提案: ' + prop);
      if (prop !== 'しない') {
        $$('li', c).forEach(function (li) {
          if (!li.dataset.v) { missing.push(li.dataset.i); return; }
          var t = $('.cm', li).value.replace(/[\\r\\n\\v\\f\\x1c-\\x1e\\x85\\u2028\\u2029]+/g, ' ').trim();
          lines.push('- 項目 ' + li.dataset.i + ': ' + li.dataset.v + (li.dataset.v === '修正' && t ? '｜' + t : ''));
        });
      }
      lines.push('- コメント: ' + $('.gc', c).value.replace(/[\\r\\n\\v\\f\\x1c-\\x1e\\x85\\u2028\\u2029]+/g, ' '));
    });
    return { md: lines.join('\\n') + '\\n', missing: missing };
  }
  $('#copy').onclick = function () {
    var st = $('#state'), box = $('#box'), b = build();
    if (b.missing.length) {\
 st.className = 'state err'; st.textContent = '未選択があります: ' + b.missing.join('、'); return; }
    window.__answersMd = b.md; window.__submitted = true;
    var fb = function () { box.hidden = false; box.value = b.md; box.focus(); box.select();\
 st.className = 'state'; st.textContent = 'コピーできませんでした。下の文字を選んで、コピーしてください。'; };
    try {
      navigator.clipboard.writeText(b.md).then(function () { box.hidden = true; st.className = 'state';\
 st.textContent = 'コピーしました。Claude が待っていれば届きます。\
待っていなければ、チャットに貼り付けてください。'; }, fb);
    } catch (e) { fb(); }
  };
  restore(); refresh();
})();
</script>"""


def _e(s) -> str:
    return _html.escape(str(s if s is not None else ""))


def render(plan: dict, deck: str, round_no: int) -> str:
    cards = []
    for p in plan["proposals"]:
        asked = bool(p.get("asked"))
        parts = [
            f'<section class="card" data-p="{_e(p["id"])}" data-asked="{1 if asked else 0}">',
            f"<h2>{_e(p['id'])}　{_e(p.get('title', ''))}</h2>",
        ]
        if p.get("source"):
            parts.append(f'<p class="why">素材: {_e(p["source"])}</p>')
        if asked:
            parts.append('<p class="why">利用者の依頼により、絵にします（提案の欄は省きます）。</p>')
        else:
            parts.append(f'<p class="why">提案の理由: {_e(p.get("reason", ""))}</p>')
            parts.append(
                f'<fieldset class="prop"><legend>この箇所を絵にしますか</legend>'
                f'<label><input type="radio" name="prop-{_e(p["id"])}" value="する">絵にする</label>'
                f'<label><input type="radio" name="prop-{_e(p["id"])}" value="しない">絵にしない</label></fieldset>'
            )
        parts.append(f'<h3>読み取った構造</h3><p class="sum">{_e(p.get("summary", ""))}</p><ul class="items">')
        for it in p.get("items", []):
            parts.append(
                f'<li data-i="{_e(it["id"])}" data-v="">'
                f'<span class="k">{_e(it.get("kind", ""))}</span><span>{_e(it["text"])}</span>'
                '<span class="vd"><button type="button" data-v="OK" aria-pressed="false">OK</button>'
                '<button type="button" data-v="修正" aria-pressed="false">修正</button></span>'
                '<input class="cm" type="text" placeholder="どう直すか（例: FW は LB の手前）" hidden></li>'
            )
        parts.append('</ul><h3>全体のコメント</h3><textarea class="gc"></textarea></section>')
        cards.append("".join(parts))
    head = (
        '<!doctype html><html lang="ja"><head><meta charset="utf-8">'
        f"<title>{_e(plan.get('title', '絵の提案と構造の確認'))}</title>{_STYLE}</head><body>"
    )
    body = (
        f'<main class="rv"><h1>{_e(plan.get("title", "絵の提案と構造の確認"))}</h1>'
        '<p class="lead">'
        + _e(
            plan.get(
                "intro",
                "絵にする箇所と、読み取った構造を確認してください。"
                "構造の各項目に OK か修正を付け、「回答をコピー」を押してください。",
            )
        )
        + "</p>"
        + "".join(cards)
        + '<div class="act"><button id="copy" type="button">回答をコピー</button>'
        '<span id="state" class="state" role="status"></span></div>'
        '<textarea id="box" class="box" hidden readonly></textarea></main>'
    )
    # 計画が変われば保存キーも変わり、前の判定が戻らない
    plan_json = json.dumps(plan, sort_keys=True, ensure_ascii=False)
    plan_hash = hashlib.sha1(plan_json.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
    script = (
        _SCRIPT.replace("__DECK__", json.dumps(deck, ensure_ascii=False).replace("</", "<\\/"))
        .replace("__ROUND__", str(int(round_no)))
        .replace("__PLANHASH__", json.dumps(plan_hash))
    )
    return head + body + script + "</body></html>"


def assemble(work: Path, deck: str, round_no: int | None = None) -> Path:
    work = Path(work)
    plan = load_plan(work)
    out = work / OUT_FILE
    out.write_text(render(plan, deck, round_no or next_round(work)), encoding="utf-8")
    return out
