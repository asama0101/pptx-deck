"""3 案ページ（variants.html）の生成、回答の解析、最終 HTML（final.html）の統合。"""
import html as _html
import re
from pathlib import Path

FRAG = re.compile(r"^(\d{2})-([A-Z])\.html$")
HEAD = ('<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>{title}</title>'
        '<link rel="stylesheet" href="theme.css"><link rel="stylesheet" href="base.css">'
        '<script src="chart-preview.js" defer></script>{extra}</head><body>')

_STYLE = """<style>
body{font-family:'BIZ UDPGothic','Yu Gothic','Meiryo',sans-serif;margin:0;padding:24px;background:#E5E5E5}
.wrap{max-width:1700px;margin:0 auto}
h1{font-size:22px;margin:0 0 4px}.lead{color:#595959;margin:0 0 24px}
.sl{background:#fff;border:1px solid #BFBFBF;border-radius:8px;padding:16px;margin:0 0 20px}
.sl h2{font-size:18px;margin:0 0 12px}
.row{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start}
.opt{display:flex;flex-direction:column;gap:6px}
.opt label{font-weight:700;display:flex;gap:6px;align-items:center;cursor:pointer}
.thumb{width:512px;height:288px;overflow:hidden;border:1px solid #BFBFBF;position:relative}
.thumb .scaled{width:1280px;height:720px;transform:scale(.4);transform-origin:0 0}
.thumb .slide{margin:0}
textarea{width:100%;box-sizing:border-box;height:56px;margin-top:12px;font:inherit;padding:6px}
.bar{position:sticky;bottom:0;background:#fff;border-top:1px solid #BFBFBF;padding:12px 24px;display:flex;gap:16px;align-items:center}
button{font:inherit;font-weight:700;padding:8px 24px;border:0;border-radius:6px;background:#1F3A5F;color:#fff;cursor:pointer}
#state{color:#1E6B52;font-weight:700}
</style>"""

_SCRIPT = """<script>
document.getElementById('submit').onclick = function () {
  var lines = ['---', 'deck: __DECK__', 'round: __ROUND__', '---'];
  document.querySelectorAll('[data-slide]').forEach(function (sec) {
    var sel = sec.querySelector('input[type=radio]:checked');
    var c = sec.querySelector('textarea').value.replace(/\\r?\\n/g, ' ');
    lines.push('## S' + sec.dataset.slide, '- 選択: ' + (sel ? sel.value : ''), '- コメント: ' + c);
  });
  window.__answersMd = lines.join('\\n') + '\\n';
  window.__submitted = true;
  document.getElementById('state').textContent = '送信しました。Claude に戻ってください。';
};
</script>"""


def collect(work: Path) -> dict[str, dict[str, str]]:
    d = Path(work) / "slides"
    if not d.is_dir():
        raise ValueError(f"{d} がありません（slides/NN-A.html の形で案を置いてください）")
    out: dict[str, dict[str, str]] = {}
    for f in sorted(d.iterdir()):
        m = FRAG.match(f.name)
        if m:
            out.setdefault(m.group(1), {})[m.group(2)] = f.read_text(encoding="utf-8")
    if not out:
        raise ValueError(f"{d} に NN-A.html の形のファイルがありません")
    return out


def assemble(work: Path, round_no: int = 1) -> Path:
    work = Path(work)
    frags = collect(work)
    parts = [HEAD.format(title="スライド案の選択", extra=_STYLE),
             '<div class="wrap"><h1>スライド案の選択</h1>'
             f'<p class="lead">ラウンド {round_no}。各スライドの案を選び、直したい点があればコメントに書いて、最後に「送信」を押してください。</p>']
    for nn, opts in frags.items():
        parts.append(f'<div class="sl" data-slide="{nn}"><h2>S{nn}</h2><div class="row">')
        letters = sorted(opts)
        for k in letters:
            parts.append(f'<div class="opt"><div class="thumb"><div class="scaled">{opts[k]}</div></div>')
            if len(letters) > 1:
                parts.append(f'<label><input type="radio" name="s{nn}" value="{k}"> 案 {k}</label>')
            else:
                parts.append(f'<label><input type="radio" name="s{nn}" value="A"> 採用</label>'
                             f'<label><input type="radio" name="s{nn}" value="FIX"> 要修正</label>')
            parts.append("</div>")
        parts.append('</div><textarea placeholder="どうしてほしいか（任意）"></textarea></div>')
    parts.append('</div><div class="bar"><button id="submit">送信</button><span id="state"></span></div>')
    parts.append(_SCRIPT.replace("__DECK__", _html.escape(work.name)).replace("__ROUND__", str(round_no)))
    parts.append("</body></html>")
    out = work / "variants.html"
    out.write_text("".join(parts), encoding="utf-8")
    return out


def parse_answers(md: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    cur = None
    for line in md.splitlines():
        m = re.match(r"^## S(\d{2})\s*$", line)
        if m:
            cur = m.group(1)
            out[cur] = {"choice": "", "comment": ""}
        elif cur and line.startswith("- 選択:"):
            out[cur]["choice"] = line.split(":", 1)[1].strip()
        elif cur and line.startswith("- コメント:"):
            out[cur]["comment"] = line.split(":", 1)[1].strip()
    return out


def merge_answers(mds: list[str]) -> dict[str, dict]:
    """複数回の回答を順に重ねる。選択が入っているスライドだけ、後の回答で置き換える。
    2 回目以降に答えなかったスライド（選択が空）は、前の回答を消さない。"""
    out: dict[str, dict] = {}
    for md in mds:
        for nn, a in parse_answers(md).items():
            if a["choice"] or nn not in out:
                out[nn] = a
    return out


def finalize(work: Path, answers_md: "str | list[str]", allow_comments: bool = False) -> Path:
    work = Path(work)
    frags = collect(work)
    ans = merge_answers([answers_md] if isinstance(answers_md, str) else list(answers_md))
    problems = []
    for nn in sorted(frags):
        a = ans.get(nn)
        if not a or a["choice"] not in frags[nn]:
            got = a["choice"] if a and a["choice"] else "未回答"
            problems.append(f"S{nn}: 案が決まっていません（回答: {got}）")
        elif a["comment"] and not allow_comments:
            problems.append(f"S{nn}: コメントが未反映です: {a['comment']}")
    if problems:
        raise ValueError("\n".join(problems))
    body = "\n".join(frags[nn][ans[nn]["choice"]] for nn in sorted(frags))
    out = work / "final.html"
    out.write_text(HEAD.format(title=work.name, extra="") + body + "</body></html>", encoding="utf-8")
    return out
