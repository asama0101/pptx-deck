# 見本10本・プロンプト例の取り込み Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 見本10本_v2.pptx の構図と、プロンプト例.md の規則（ヘッド・描画の規準・設計図→検証）を、`skills/pptx-deck` の部品庫・原稿の検査・SKILL.md に取り入れる。

**Architecture:** 検査は `pptx_deck/script_lint.py`（原稿）と `check.py`（体裁。`measure.js` の計測値を使う）に足す。見た目は `assets/web/base.css`・`theme.py`（階調）と `assets/components/**` の断片で直す。工程は SKILL.md に書く。PPTX の出力方式は変えない。

**Tech Stack:** Python 3.14（venv: `%LOCALAPPDATA%\pptx-deck\venv`）、python-pptx、Playwright(Python)、pytest、LibreOffice（画像化）。

**Spec:** `docs/specs/2026-10-12_1800_sample-and-prompt.md`（承認済み）

## Global Constraints
- 文字の下限は現行のまま: 本文 14pt 以上・注記 10pt 以上（`check.py` の `MIN_PT_DEFAULT=14`・`MIN_PT_SMALL=10`）。
- フォントは BIZ UDPゴシック。出典は既定で書かない（必要なときだけ）。
- 維持するもの: 装飾アイコン、橙の強調色（推奨・承認を求める 1 点）、3 案→最終の流れ。
- ダッシュ「——」「—」と So What 帯は使わない（採用）。
- 章名は現行（そのスライドが答える問い）のまま。
- 色は `var(--…)` だけ（白 `#FFFFFF` 以外の 16 進直書きは `test_component_header_comment` が落とす）。
- 部品庫の各断片に、用途の冒頭コメントと、2 種類以上の `data-note` を付ける（既存テスト）。
- コマンドは `"$LOCALAPPDATA/pptx-deck/venv/Scripts/python.exe" -m pytest …`（以降 `PYTEST`）。作業ディレクトリは `skills/pptx-deck`。
- 一時ファイルはスクラッチパッド（`%TEMP%` 配下）に置く。コミットメッセージは日本語。

## Review Focus
- 素材がヘッドのない空の見出し・極端に短い／長い見出し → 見出しの検査は、cover・section・agenda・closing を除外し、空はすでにある「見出しがありません」で 1 回だけ指摘する（二重に出さない）。
- 「ー」（長音）や「―」を含む正当な語（例「サーバー」「ルーター」）→ ダッシュと誤検出しない（検出するのは U+2014・U+2015・U+2500 だけ）。
- 値だけの短い text（「38」「▲4」）が複数ある表・グラフ → `sameWord` が誤検出しない（6 字未満は対象外、軸ラベル・単位は数えない）。
- 日本語の 1 行 1〜2 字の孤立（「、」「。」だけの行を含む）→ `orphanLine` は最終行が 2 字以下のときだけ警告（1 行だけの文は対象外）。
- 論点が 0 個（書かない）の原稿 → 既存の原稿を壊さない（論点は任意。書いたときだけ 3〜6 個を検査する）。

---

### Task 1: ヘッドの規則を `lint-script` に入れる

**Files:**
- Modify: `skills/pptx-deck/pptx_deck/script_lint.py`
- Test: `skills/pptx-deck/tests/test_script_lint.py`

**Interfaces:**
- Produces: `script_lint.lint(md) -> list[str]`（既存）に、見出し・論点・文型の検査を足す。`script_lint.sentence_type(head: str) -> str`（`"因果"|"条件"|"逆接"|"起因"|"評価"|"提言"|"その他"`）を公開する。

- [ ] **Step 1: 失敗するテストを書く**（`tests/test_script_lint.py` の末尾）

```python
import pytest

BODY = "\n## S02 背景\n- layout: content\n- 章名: なぜか\n- 見出し: {head}\n- 本文:\n  - 要点\n"
HEAD = "# 題\n- 目的: x\n- 対象: y\n\n## S01 表紙\n- layout: cover\n- 見出し: 題\n"


def lint_head(head):
    return "\n".join(script_lint.lint(HEAD + BODY.format(head=head)))


def test_good_head_passes():
    assert lint_head("削減で生む原資が成長投資を支えるため、4件は一括での承認が必要だ") == ""


@pytest.mark.parametrize("head,word", [
    ("コストの分析", "判断"),                                                  # 題名であって主張ではない（判断語・接続語がない）
    ("費用は1.7億円。A案より低い", "二段"),
    ("本ページでは費用を比較し、B案が最も安いと判断すべきだ", "自己言及"),
    ("B案は——費用が最も低く、採用すべきだ", "ダッシュ"),
    ("短いため、採用すべきだ", "字数"),
    ("費用が高いため、" + "あ" * 60 + "べきだ", "字数"),
])
def test_bad_heads(head, word):
    assert word in lint_head(head)


def test_cover_section_closing_are_exempt():
    md = HEAD + "\n## S02 章\n- layout: section\n- 章名: x\n- 見出し: 背景\n- 本文:\n  - a\n\n## S03 結び\n- layout: closing\n- 見出し: 以上\n"
    assert script_lint.lint(md) == []


def test_empty_head_is_reported_once():
    got = script_lint.lint(HEAD + BODY.format(head=""))
    assert sum("見出し" in g for g in got) == 1


def test_three_same_type_in_a_row():
    heads = ["費用が低いため、B案を採るべきだ" + "ので" * 0] * 3
    md = HEAD
    for i, h in enumerate(["A案は費用が低いため、採用に値する", "B案は期間が短いため、採用に値する", "C案は停止が少ないため、採用に値する"], start=2):
        md += BODY.format(head=h).replace("S02", f"S{i:02d}")
    assert "文型" in "\n".join(script_lint.lint(md))


def test_sentence_type():
    assert script_lint.sentence_type("費用が低いため、B案を採る") == "因果"
    assert script_lint.sentence_type("承認すれば、着手できる") == "条件"
    assert script_lint.sentence_type("伸びは首位だが、問題は増分にある") == "逆接"
    assert script_lint.sentence_type("集中させるべきだ") == "提言"


def test_issue_count_is_checked_only_when_written():
    ok = "# 題\n- 目的: x\n- 対象: y\n- 論点:\n  - ①a\n  - ②b\n  - ③c\n\n## S01 表紙\n- layout: cover\n- 見出し: 題\n"
    assert script_lint.lint(ok) == []
    two = ok.replace("  - ③c\n", "")
    assert "論点" in "\n".join(script_lint.lint(two))
    assert script_lint.lint(HEAD) == []                  # 書かなければ検査しない
```

- [ ] **Step 2: 落ちることを確認**

Run: `PYTEST tests/test_script_lint.py -q`
Expected: FAIL（`sentence_type` がない・見出しの検査がない）

- [ ] **Step 3: 実装する**（`script_lint.py`。import の下に定数、`lint()` の末尾の前に検査、ヘッダーの `論点` の読み取りを足す）

```python
_JUDGE = ["すべきだ", "べきだ", "に限られる", "に値する", "を左右しない", "ではなく", "にすぎず", "が見込める",
          "できる", "が必要だ", "必要がある", "ある", "縮む", "減る", "増える", "高い", "低い", "ない", "切れる"]
_CONNECT = ["ため", "だが", "ことで", "ば、", "が、", "ので"]
_BODY_LAYOUTS = {"content", "diagram", "table", "chart"}
_DASH = re.compile("[\u2014\u2015\u2500]")
_SELF = re.compile(r"本ページ|この1枚|この１枚|本スライド")
_TYPES = [("提言", re.compile(r"べきだ|必要がある|が必要だ")), ("逆接", re.compile(r"だが|が、")),
          ("条件", re.compile(r"ば、")), ("起因", re.compile(r"ではなく")),
          ("評価", re.compile(r"を左右しない|の範囲にあり")), ("因果", re.compile(r"ため、|ことで"))]


def sentence_type(head: str) -> str:
    for name, rx in _TYPES:
        if rx.search(head):
            return name
    return "その他"


def _issues(md: str):
    items, cur, in_header = [], False, True
    for line in md.splitlines():
        if line.startswith("## "):
            break
        m = _FIELD.match(line)
        if m:
            cur = m.group(1).strip() == "論点"
            continue
        it = _ITEM.match(line)
        if it and cur:
            items.append(it.group(1).strip())
    return items


def _head_problems(sid, head):
    out = []
    n = len(head)
    if not (30 <= n <= 60):
        out.append(f"{sid}: 見出しの字数が {n} です（30〜60 字。まず 1 行 36 字幅で書く）")
    if "。" in head.rstrip("。"):
        out.append(f"{sid}: 見出しが「A。B」の二段構えです（接続語で 1 文に畳む）")
    if _DASH.search(head):
        out.append(f"{sid}: 見出しにダッシュを使わないでください")
    if _SELF.search(head):
        out.append(f"{sid}: 見出しに自己言及（本ページ・この1枚）を書かないでください")
    if not (any(j in head for j in _JUDGE) or any(c in head for c in _CONNECT)):
        out.append(f"{sid}: 見出しに判断語か接続語がありません（題名ではなく、判断を言い切る一文に）")
    return out
```

`lint()` の `for i, s in enumerate(slides…)` の中、`if not f.get("見出し")` の `else` として:

```python
        if not f.get("見出し"):
            out.append(f"{sid}: 見出しがありません")
        elif layout in _BODY_LAYOUTS:
            out.extend(_head_problems(sid, f["見出し"]))
```

（元の `if not f.get("見出し"): out.append(...)` の 2 行を上の 3 行に置き換える）。`for` の後ろ、`return out` の前に:

```python
    issues = _issues(md)
    if issues and not (3 <= len(issues) <= 6):
        out.append(f"論点は 3〜6 個にしてください（今は {len(issues)} 個）")
    run, prev = 0, None
    for s in slides:
        h = s["fields"].get("見出し")
        if s["fields"].get("layout") not in _BODY_LAYOUTS or not isinstance(h, str):
            run, prev = 0, None
            continue
        t = sentence_type(h)
        run = run + 1 if t == prev and t != "その他" else 1
        prev = t
        if run == 3:
            out.append(f"{s['id']}: 隣り合う 3 枚の見出しが同じ文型（{t}）です。文型を散らしてください")
    return out
```

- [ ] **Step 4: 既存の原稿を直す**: `tests/test_script_lint.py` の `OK`（S02・S03 の見出し）と `assets/sample/script.md` は、このままだと新しい規則で落ちる。`OK` の S02 を `現行基盤は2028年に保守が切れるため、今期中に移行先を決める必要がある`（33 字）に、S03 を `B案は費用・期間・リスクの3項目で最も釣り合っているため、採用に値する`（35 字）に直す。`sample/script.md` は Task 7 で置き換えるので、`test_sample_script_is_valid` は Task 7 まで `pytest.mark.xfail(reason="Task 7 で置き換え")` を付ける。

- [ ] **Step 5: 通ることを確認**

Run: `PYTEST tests/test_script_lint.py -q`
Expected: PASS（xfail 1 件）

- [ ] **Step 6: コミット**

```bash
git add skills/pptx-deck/pptx_deck/script_lint.py skills/pptx-deck/tests/test_script_lint.py
git commit -m "feat: 原稿の検査にヘッドの規則（字数・判断語・二段構え・ダッシュ・自己言及・文型の連続）と論点の個数を追加"
```

---

### Task 2: 体裁の検査 `dash`・`sameWord`・`orphanLine`・`emptyBand`

**Files:**
- Modify: `skills/pptx-deck/pptx_deck/check.py`、`skills/pptx-deck/pptx_deck/measure.js`（text 要素に `lastLineChars` を足す）
- Test: `skills/pptx-deck/tests/test_check.py`、`skills/pptx-deck/tests/test_measure.py`

**Interfaces:**
- Consumes: `tests.test_build` の `text_el(idx, x, y, w, h, text, role=None, size=20)`・`slide(layout, elements)`、`measure.js` の text 要素の `paras[].runs[].text`。
- Produces: text 要素の `lastLineChars: int | None`（最終行の文字数。1 行だけの要素は `None`）。違反の rule 名 `dash`・`sameWord`・`orphanLine`・`emptyBand`（すべて severity `warning`）。

- [ ] **Step 1: 失敗するテストを書く**（`tests/test_check.py` の末尾）

```python
def warn_rules(model):
    return sorted({v["rule"] for v in check.check_model(model, INFO) if v["severity"] == "warning"})


def test_dash_is_flagged_but_long_vowel_is_not():
    assert "dash" in warn_rules([slide("content", [TITLE, text_el(1, 64, 160, 500, 40, "A案——低い")])])
    assert "dash" not in warn_rules([slide("content", [TITLE, text_el(1, 64, 160, 500, 40, "サーバーとルーター")])])


def test_same_word_twice_is_flagged_short_values_are_not():
    a = text_el(1, 64, 160, 400, 40, "標準仕様データベースで代替")
    b = text_el(2, 64, 220, 400, 40, "標準仕様データベースで代替")
    assert "sameWord" in warn_rules([slide("content", [TITLE, a, b])])
    c, d = text_el(3, 64, 280, 100, 40, "38"), text_el(4, 200, 280, 100, 40, "38")
    assert "sameWord" not in warn_rules([slide("content", [TITLE, c, d])])


def test_orphan_last_line():
    t = text_el(1, 64, 160, 400, 80, "長い文が折り返して最後に二字")
    t["lastLineChars"] = 2
    assert "orphanLine" in warn_rules([slide("content", [TITLE, t])])
    t["lastLineChars"] = None
    assert "orphanLine" not in warn_rules([slide("content", [TITLE, t])])


def test_empty_band_when_body_stops_far_above_the_area_bottom():
    assert "emptyBand" in warn_rules([slide("content", [TITLE, text_el(1, 64, 160, 500, 40, "本文だけ")])])
    full = text_el(2, 64, 560, 500, 60, "下まで使う本文")
    assert "emptyBand" not in warn_rules([slide("content", [TITLE, full])])
    assert "emptyBand" not in warn_rules([slide("cover", [TITLE])])           # 表紙・章扉・目次・裏表紙は対象外
```

`tests/test_measure.py` に（既存の HTML 断片の作り方に合わせる。同ファイルの先頭の補助関数を使う）:

```python
def test_last_line_chars(tmp_path):
    html = tmp_path / "t.html"
    html.write_text('<html><body><section class="slide" data-layout="content">'
                    '<div class="pp-text" style="left:64px;top:160px;width:200px;font-size:20px">あいうえおかきくけこさ</div>'
                    '<div class="pp-text" style="left:64px;top:300px;width:600px;font-size:20px">一行だけ</div>'
                    '</section></body></html>', encoding="utf-8")
    els = measure.measure(html)[0]["elements"]
    assert els[0]["lastLineChars"] in (1, 2) and els[1]["lastLineChars"] is None
```

- [ ] **Step 2: 落ちることを確認**

Run: `PYTEST tests/test_check.py tests/test_measure.py -q`
Expected: FAIL（rule がない・`lastLineChars` がない）

- [ ] **Step 3: `measure.js` を直す**: text 要素の `e.paras = parasOf(el);` の直後に足す。

```js
        const tn = []; const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
        for (let n = w.nextNode(); n; n = w.nextNode()) if (n.textContent.trim()) tn.push(n);
        e.lastLineChars = null;
        if (tn.length) {
          const last = tn[tn.length - 1], r2 = document.createRange();
          const total = last.textContent.length, rows = new Map();
          for (let i = 0; i < total; i++) {
            r2.setStart(last, i); r2.setEnd(last, i + 1);
            const b = r2.getBoundingClientRect();
            if (b.width > 0) rows.set(Math.round(b.top), (rows.get(Math.round(b.top)) || 0) + 1);
          }
          if (rows.size > 1) e.lastLineChars = rows.get([...rows.keys()].sort((a, b) => a - b).pop());
        }
```

- [ ] **Step 4: `check.py` を直す**: 定数に `AREA_BOTTOM_GAP = 120`・`SAME_WORD_MIN = 6`・`_DASH = re.compile("[\u2014\u2015\u2500]")`（`import re` を足す）。`check_model` の `for s in model:` の中、`titleMissing` の後に足す。

```python
        texts = []
        for e in els:
            if e["kind"] == "text":
                t = "".join(r.get("text", "") for p in e["paras"] for r in p["runs"]).strip()
                texts.append((e, t))
                if _DASH.search(t):
                    out.append(_v("dash", n, f"text#{e['idx']}: ダッシュ（—）を使わないでください", "warning"))
                if e.get("lastLineChars") is not None and e["lastLineChars"] <= 2:
                    out.append(_v("orphanLine", n, f"text#{e['idx']}: 最終行が {e['lastLineChars']} 字だけです。幅か文を直してください", "warning"))
        seen = {}
        for e, t in texts:
            if len(t) >= SAME_WORD_MIN and not e.get("chrome"):
                seen.setdefault(t, []).append(e["idx"])
        for t, idxs in seen.items():
            if len(idxs) > 1:
                out.append(_v("sameWord", n, f"同じ文言「{t[:12]}」が 1 枚に {len(idxs)} 回あります。軸・見出しにくくり出してください", "warning"))
        if s["layout"] in ("content", "diagram", "table", "chart"):
            body = [e for e in els if not e.get("chrome") and not e.get("ph") and e.get("role") != "title" and e["kind"] != "line"]
            if body:
                bottom = max(_r(e)["y"] + _r(e)["h"] for e in body)
                area_bottom = max((z["y"] for z in keepout), default=SLIDE_H)
                if bottom < area_bottom - AREA_BOTTOM_GAP:
                    out.append(_v("emptyBand", n, f"本文が下端（y {area_bottom}）の手前 {area_bottom - bottom:.0f}px で終わっています。無所属の空白帯を残さない", "warning"))
```

`keepout` は既存の `info.keepout` 由来の矩形リスト。標準の領域は y 676 以降のため `area_bottom` は 676 になる。

- [ ] **Step 5: 通ることを確認**

Run: `PYTEST tests/test_check.py tests/test_measure.py -q`
Expected: PASS。続けて `PYTEST -q` で全体を流し、部品庫の断片が新しい警告（`emptyBand`・`sameWord`）で落ちないことを確認する（`test_component_is_clean_and_buildable` は `violations == []` を要求するため、警告も含めて 0 件が必要）。落ちた断片は、Task 5〜6 で直す対象としてメモし、このタスクでは `test_components.py` の判定を `check.errors(violations) == []` に緩めず、断片側で直す（`emptyBand` は本文を下へ伸ばす、`sameWord` は文言を変える）。

- [ ] **Step 6: コミット**

```bash
git add skills/pptx-deck/pptx_deck/check.py skills/pptx-deck/pptx_deck/measure.js skills/pptx-deck/tests/test_check.py skills/pptx-deck/tests/test_measure.py
git commit -m "feat: 体裁の検査に dash・sameWord・orphanLine・emptyBand を追加"
```

---

### Task 3: 配色の階調・記号文法・角丸の抑制（`theme.py`・`base.css`）

**Files:**
- Modify: `skills/pptx-deck/pptx_deck/theme.py`、`skills/pptx-deck/assets/web/base.css`
- Test: `skills/pptx-deck/tests/test_theme.py`

**Interfaces:**
- Produces: `Palette.accent_mid`＝基調色に白を 52% 混ぜた色、`accent_light`＝75% 混ぜた色、新しく `accent_soft`＝28% 混ぜた色（CSS 変数 `--accent-soft`）。`bg_soft`（パネル地）は `#EEF3F6`、`line` は `#D9DEE3`、`text_sub` は `#6B7C85` ではなくコントラスト 4.5 を満たす `#595959` を維持（注記の読みやすさ）。base.css に `.f-outline`（枠線のみ・計画）、`.dashed`（破線）、`.dotted`（点線）、`.r` の角丸を 10px から 2px に。

- [ ] **Step 1: 失敗するテストを書く**（`tests/test_theme.py` の末尾）

```python
def test_tints_follow_28_52_75_percent_white():
    p = theme.derive("#1976D2")
    assert p.accent == "#1976D2"
    assert p.accent_soft == theme.mix("#1976D2", "#FFFFFF", 0.28)
    assert p.accent_mid == theme.mix("#1976D2", "#FFFFFF", 0.52)
    assert p.accent_light == theme.mix("#1976D2", "#FFFFFF", 0.75)


def test_panel_and_rule_colors():
    p = theme.derive("navy")
    assert p.bg_soft == "#EEF3F6" and p.line == "#D9DEE3"


def test_theme_css_has_accent_soft():
    assert "--accent-soft:" in theme.theme_css(theme.derive("navy"))
```

- [ ] **Step 2: 落ちることを確認** — Run: `PYTEST tests/test_theme.py -q` → FAIL（`accent_soft` がない）

- [ ] **Step 3: 実装する**: `Palette` に `accent_soft: str` を足し、`derive` を `accent_soft=mix(accent, "#FFFFFF", 0.28), accent_mid=mix(accent, "#FFFFFF", 0.52), accent_light=mix(accent, "#FFFFFF", 0.75)`、`line="#D9DEE3"`、`bg_soft="#EEF3F6"` に変える。`theme_css` の `rows` に `("accent-soft", p.accent_soft)` を足す。`base.css`: `.r { border-radius: 2px; }`、末尾に

```css
/* 記号文法: 塗り＝実績・自社／枠線のみ＝計画・目標／濃色＝主役・淡色＝文脈 */
.f-soft2  { background: var(--accent-soft); }
.f-outline { background: #FFFFFF; border: 1.5px solid var(--accent); }
/* 実線＝実績・確定／破線＝予測・計画・消える要素／点線＝補助輪郭（pp-line と併用） */
.pp-line.dashed { background: none; border-top: 2px dashed var(--accent); height: 0; }
.pp-line.dotted { background: none; border-top: 2px dotted var(--text-sub); height: 0; }
.pp-shape.dashed { border: 1.5px dashed var(--accent); background: #FFFFFF; }
```

（`.pp-line.dashed` が PPTX で破線になるかは Task 4 で `build.py` の線の書き出しを確かめる。`build.py` に `prstDash` の出力がなければ、そこで足す）

- [ ] **Step 4: 全体を流す**

Run: `PYTEST -q`
Expected: PASS。`accent_light` が 88%→75% に濃くなったため、薄色の面に載せた文字のコントラスト（`test_component_is_clean_and_buildable`・`contrast`）が落ちる断片が出たら、その断片の文字色を `var(--text)` に直す（基調色の文字は白地だけ、の既存規則）。

- [ ] **Step 5: コミット** — `git add skills/pptx-deck/pptx_deck/theme.py skills/pptx-deck/assets/web/base.css skills/pptx-deck/tests/test_theme.py` → `git commit -m "feat: 配色の階調を 28・52・75% 白混ぜに、パネル地・罫線を見本の色に、記号文法の部品と角丸の抑制を追加"`

---

### Task 4: 破線・点線を PPTX に書き出す

**Files:**
- Modify: `skills/pptx-deck/pptx_deck/build.py`、`skills/pptx-deck/pptx_deck/measure.js`（線の `dash` を測る）
- Test: `skills/pptx-deck/tests/test_build.py`

**Interfaces:**
- Consumes: Task 3 の `.dashed`・`.dotted`。
- Produces: measure の line・shape 要素に `dash: "dash"|"sysDot"|None`、`build.py` が `a:prstDash` を書く。

- [ ] **Step 1: 失敗するテストを書く**（`tests/test_build.py` の既存の線のテストに倣う。`line_el`・`shape_el` の補助があればそれを使い、なければ `text_el` と同じ形の dict を作る）

```python
def test_dashed_line_and_shape_are_written(tmp_path):
    ln = {"kind": "line", "idx": 1, "rect": {"x": 100, "y": 200, "w": 300, "h": 0}, "color": "1976D2", "w": 2, "dash": "dash",
          "arrow": None, "dir": None, "role": None, "ph": None, "bg": "FFFFFF", "overlap": False, "chrome": False}
    out = build_one(tmp_path, [ln])                                 # 同ファイルの既存補助で 1 枚を書き出す関数に合わせる
    from pptx import Presentation
    xml = Presentation(str(out)).slides[0].shapes[-1]._element.xml
    assert 'prstDash val="dash"' in xml
```

- [ ] **Step 2: 落ちることを確認** — Run: `PYTEST tests/test_build.py -q -k dashed` → FAIL

- [ ] **Step 3: 実装する**: `measure.js` の line 要素の生成箇所（`pp-line` の分岐）で、`const bs = cs.borderTopStyle; e.dash = bs === 'dashed' ? 'dash' : bs === 'dotted' ? 'sysDot' : null;`、shape の分岐でも同様（`borderOf` の戻りに `dash` を足す）。`build.py` の線・図形の書き出しで、`dash` があれば `ln` 要素に `a:prstDash` を足す:

```python
from pptx.oxml.ns import qn
from lxml import etree

def _set_dash(line_fmt, dash):
    if not dash:
        return
    ln = line_fmt._get_or_add_ln()
    for old in ln.findall(qn("a:prstDash")):
        ln.remove(old)
    d = etree.SubElement(ln, qn("a:prstDash"))
    d.set("val", dash)
```

（`a:prstDash` は `a:solidFill` の後ろに置く必要がある。`SubElement` で末尾に足して順序が崩れる場合は、`ln.find(qn("a:solidFill")).addnext(d)` にする）

- [ ] **Step 4: 通ることを確認** — Run: `PYTEST tests/test_build.py tests/test_measure.py -q` → PASS。LibreOffice で `.dashed` を使う断片（Task 5 以降）を画像にして破線が出ることを目で確認する。

- [ ] **Step 5: コミット** — `git commit -m "feat: 破線・点線を測り、PPTX の線種（prstDash）に書き出す"`

---

### Task 5: 見本に合わせて既存の断片を作り直す（表・判断・グラフ）

**Files（Modify。すべて `skills/pptx-deck/assets/components/` 配下）:**
- `tables/compare.html`（見本 1 エグゼクティブサマリ・10 論証テーブル）、`tables/rating.html`、`layouts/decision.html`（見本 2 クロージング決定）、`charts/waterfall-note.html`（見本 3）
- Test: `tests/test_components.py`（既存の網羅テストを使う。新しいテストは Step 1 の 1 件）

**Interfaces:**
- Consumes: Task 3 の色・記号文法の class、Task 2 の警告（0 件が必要）。
- Produces: 各断片が、見本の構図に沿った「用途」コメントと `data-note` を持つ。

**見本からの写し方（共通）**
- 構図の寸法は見本を 1280×720 で実測した値のまま使う: 左右余白 57px→既存の 64px に揃える（テンプレートの領域に合わせる）、図表タイトル（`lead`）は題の下 y 150〜160。
- 文字は下限（本文 14pt＝約 19px、注記 10pt＝約 14px）を守る。見本の 10pt の行は、項目を減らすか文を短くして入れる。
- 角丸は使わない（`.r` を外す。`.r` は 2px に下がったので残してもよいが、面を並べる図は外す）。面は `f-soft`（パネル地 #EEF3F6）・`f-white`（白＋罫線）・`f-accent`・`f-outline`。
- 見どころ（`data-note`）は 2〜4 点。1 点は強調（推奨・承認を求める対象）にして、強調色は 1 スライドに 1 点。

- [ ] **Step 1: 見本との見比べの検査を 1 件足す**（`tests/test_components.py`）

```python
def test_sample_structure_markers():
    """見本10本の構図を写した断片が、決めた要素を持つ（構図の消し込み）。"""
    want = {
        "tables/compare": ["論点", "求める決定"],
        "layouts/decision": ["決定事項", "投資の考え方"],
        "charts/waterfall-note": ["打ち手", "削減"],
    }
    for rel, words in want.items():
        text = (COMP / f"{rel}.html").read_text(encoding="utf-8")
        for w in words:
            assert w in text, f"{rel}: 「{w}」がありません（見本の構図）"
```

- [ ] **Step 2: 落ちることを確認** — Run: `PYTEST tests/test_components.py -q -k sample_structure` → FAIL

- [ ] **Step 3: 断片を直す**（1 本ずつ。各本の終わりに Step 4 を実行する）
  - `tables/compare.html`: 列を「論点｜求める決定｜主要根拠｜詳細参照」の 4 列にした表（先頭行は薄い灰の小さな見出し、先頭の論点行だけ `f-soft` の面と左端の基調色の縦線で強調、行の区切りは罫線）。行は 4 行。文言は見本 1 の語を使う（ただし見本の 2 行の根拠は、1 行 40 字までに短くして 14pt に収める）。
  - `layouts/decision.html`: 上に「決定事項（承認対象①〜④）」の表（決定事項｜内容｜オーナー｜直近アクション）、下左に直近スケジュール（矢羽根 3 つ。完了＝塗り・計画＝枠線 `f-outline`）、下右に「投資の考え方」の数字カード 3 枚（白＋罫線＋上端に基調色の細い帯）。最下部に論点ボックス（`f-soft` の帯、左に基調色の太字「論点」＋「〜の可否」1 行）。強調色は承認の 1 点だけ。
  - `charts/waterfall-note.html`: 左に滝グラフ（`data-chart` の `waterfall`、全要素に実数ラベル）、右に打ち手表（項目｜削減の方向性｜現行｜削減後｜削減幅の棒＋▲値）と、下に基調色の面の合計帯（`合計 100 → 90`）。表の右に置く棒は `pp-shape` の幅を値に比例させる（数値の大小は面積・長さに比例）。
  - `tables/rating.html`: 見本 10 の論証テーブルの基本形に寄せる（行頭に ①②③、各セルは「■事実」と「➢含意・打ち手」の 2 段。基調色の太字は打ち手の 1 点だけ）。表の下に論点ボックス。
  - 各断片の冒頭の「用途」コメントを、見本の構図の説明（何を決めさせる表か）に書き換える。

- [ ] **Step 4: 断片ごとに確認**

Run: `PYTEST tests/test_components.py -q -k "compare or decision or waterfall or rating"`
Expected: PASS（違反 0 件。警告を含む）。続けて断片を画像にして、見本（`C:\Users\sioay\AppData\Local\Temp\claude\…\scratchpad\ref\sNN.png`）と見比べる。画像化は、`PYTEST` と同じ venv の Python で `initdir.init` した作業フォルダに断片を `slides/` として置き、`run.py build` → `render` の出力 PNG を開く（手順は `tests/test_e2e_library.py` を参照）。崩れ（はみ出し・重なり・空白帯）を直す。

- [ ] **Step 5: コミット** — `git add skills/pptx-deck/assets/components skills/pptx-deck/tests/test_components.py` → `git commit -m "feat: 部品庫の表・判断・滝グラフを見本10本の構図に作り直す"`

---

### Task 6: 見本に合わせて既存の断片を作り直す（図解）と、軸統一を追加

**Files:**
- Modify: `assets/components/diagrams/tree.html`（見本 4）、`before-after.html`（見本 6）、`matrix.html`（見本 7）、`gantt.html`（見本 8）、`layers.html`（見本 9）
- Create: `assets/components/charts/small-multiples.html`（見本 5 軸統一）
- Test: `tests/test_components.py`

**Interfaces:**
- Consumes: Task 3・4（`.dashed`・`.f-outline`）。
- Produces: `charts/small-multiples` が部品庫に増える（`test_components.py` が自動で拾う）。SKILL.md の型の一覧への追記は Task 8。

- [ ] **Step 1: 失敗するテストを書く**（Task 5 の `want` に足す）

```python
    want.update({
        "diagrams/tree": ["効果", "実現期間"],
        "diagrams/before-after": ["止める", "廃止"],
        "diagrams/matrix": ["抽出ロジック"],
        "diagrams/gantt": ["現在", "完了", "計画"],
        "diagrams/layers": ["リーチ"],
        "charts/small-multiples": ["軸"],
    })
```

（`want` はテスト関数内の辞書なので、この追記は同関数の末尾に置く）

- [ ] **Step 2: 落ちることを確認** — Run: `PYTEST tests/test_components.py -q -k sample_structure` → FAIL

- [ ] **Step 3: 断片を直す／足す**（Task 5 の「共通の写し方」に従う）
  - `diagrams/tree.html`: 左に根（基調色の面）、中に 2 段の枝（面の中に項目名と値）、右に末端の施策（白＋罫線の箱 6 個）と評価列 2 つ（効果・実現期間）。枝の接続は直角の罫線。見本の 9 行は 6 行に減らす（14pt に収める）。
  - `diagrams/before-after.html`: 上段「現行」・下段「改革後」の同型の工程ボックス（6 個）を同じ位置に置き、消える工程は破線（`.pp-shape.dashed`）で「廃止」と書く。段の間に基調色の下向き矢印と一文。最下部にリードタイムの横棒 2 本（長さを値に比例させる）と、差を示す破線の枠・矢印。
  - `diagrams/matrix.html`: 左に 2×2（縦軸・横軸の名前、4 象限の名前、点は `data-shape="ellipse"`、候補象限だけ `f-soft` の面と破線の枠）、右に「抽出ロジック」の枠（条件 3 つ＋打ち手）。左右を矢印の罫線で結ぶ。
  - `diagrams/gantt.html`: 左に行の見出し（基調色の面）、上に年・四半期の帯、本体に完了（塗り）・計画（`f-outline`）の棒、現在を縦線（基調色・太）で貫く。凡例は右上に 1 行。
  - `diagrams/layers.html`: 上に系列の見出し 4 つ（自社の系列は基調色・競合は淡色）、左に層の名前、格子に箱（面積・濃淡で主役と文脈を分ける）、下に「当社リーチ＝〜%」のブラケット。
  - `charts/small-multiples.html`（新規）: 4 つの棒グラフ（`data-chart` の `bar`、軸の最大・最小・目盛を全部 `0〜600` に統一。`fmt` と値ラベルあり）を横に並べ、各パネルの上に地域名と増分を置く。1 つだけ基調色の太字（強調 1 点）。単位は左上に 1 回。用途コメントに「軸の最大・最小・目盛を揃える」と書く。
  - 各断片の冒頭コメントと `data-note`（2 種類以上）を付ける。

- [ ] **Step 4: 断片ごとに確認** — Run: `PYTEST tests/test_components.py -q`（全断片）→ PASS。Task 5 Step 4 と同じ手順で画像にして、見本 4〜9 と見比べる。

- [ ] **Step 5: コミット** — `git add skills/pptx-deck/assets/components skills/pptx-deck/tests/test_components.py` → `git commit -m "feat: 部品庫の図解を見本10本の構図に作り直し、軸統一（小グラフ 4 パネル）を追加"`

---

### Task 7: サンプル原稿を見本10本の内容に置き換える

**Files:**
- Modify: `skills/pptx-deck/assets/sample/script.md`、`skills/pptx-deck/tests/test_script_lint.py`（Task 1 で付けた xfail を外す）

**Interfaces:**
- Consumes: Task 1 の見出しの規則、Task 5・6 の型名。

- [ ] **Step 1: 原稿を書く**: 表紙（S01、layout: cover）と、見本10本の 10 枚（S02〜S11。見本 1 エグゼクティブサマリ → … → 見本 10 論証テーブルの順）の **計 11 枚**にする。結びは作らない（見本 2 のクロージング決定が最終の判断ページ）。既存の書式（`## SNN 名前` / `layout` / `章名` / `見出し` / `本文`か`図表` / `判断の枠`）で書く。先頭の項目に `- 論点:` を 4 つ（①〜④）、`- 配色: #1976D2`、`- 目的`・`- 対象` を書く。layout は表＝`table`、図解＝`diagram`、グラフ＝`chart`、判断＝`content` にする。
  - 見出しは見本の題をそのまま使う（すべて 30〜60 字・判断語か接続語あり。例: `削減で生む原資が成長投資を支えるため、4件は一括での承認が必要だ`）。隣り合う 3 枚が同じ文型にならないことを `lint-script` で確認する。
  - 章名は「そのスライドが答える問い」にする（例: S02 `何を決めてほしいのか`、S04 `原価のどこに打ち手を絞るのか`）。
  - 図表の行は Task 5・6 の型名（`表/compare`・`判断の枠/decision`・`グラフ/waterfall-note`・`図解/tree`・`グラフ/small-multiples`・`図解/before-after`・`図解/matrix`・`図解/gantt`・`図解/layers`・`表/rating`）で書く。
  - 数字はすべて見本のもの（架空）。出典は書かない（既定）。
- [ ] **Step 2: テストを直す**: `test_sample_script_is_valid` の xfail を外し、`len(...) == 11` にする。

- [ ] **Step 3: 通ることを確認**

Run: `PYTEST tests/test_script_lint.py -q` と `"$LOCALAPPDATA/pptx-deck/venv/Scripts/python.exe" run.py lint-script assets/sample/script.md`
Expected: PASS／出力が空。

- [ ] **Step 4: コミット** — `git commit -m "docs: サンプル原稿を見本10本の内容（アルタイル精機・ALTAIR 2030）に置き換える"`

---

### Task 8: SKILL.md に工程・規則・規準を書く（設計図→検証）

**Files:**
- Modify: `skills/pptx-deck/SKILL.md`、`skills/pptx-deck/pptx_deck/initdir.py`（`design.md` の雛形をコピーする場合のみ）、`README.md`
- Create: `skills/pptx-deck/assets/sample/design.md`（設計図の書式の手本）
- Test: `skills/pptx-deck/tests/test_initdir.py`

**Interfaces:**
- Consumes: Task 1〜2 の検査名、Task 6 の型 `charts/small-multiples`。

- [ ] **Step 1: 失敗するテストを書く**（`tests/test_initdir.py`）

```python
def test_init_copies_design_template(tmp_path):
    w = tmp_path / "w"
    initdir.init(w, color="navy")
    assert (w / "design.md").exists()
    assert "ガバニングメッセージ" in (w / "design.md").read_text(encoding="utf-8")
```

- [ ] **Step 2: 落ちることを確認** — Run: `PYTEST tests/test_initdir.py -q -k design` → FAIL

- [ ] **Step 3: 実装する**
  - `assets/sample/design.md`（新規）: 見出しは「設計図」。資料全体（ガバニングメッセージ・論点一覧（番号つき））、台帳の表 `| No | ヘッド | 文型 | 上位への集約 | 直前からの接続語 | 本体の型 | 論点 |`（見本の 3 行を例にする）、ページごとの項目（ヘッド／文型／型／図表タイトル／レイアウト記述（縦軸・横軸・各エリア・強調の 1 点）／証拠対応表／注記）の雛形。
  - `initdir.py`: `init` が `assets/sample/design.md` を `<名前>/design.md` にコピーする（既存の `script.md` の扱いと同じ。`--force` でも既存を壊さない）。`initdir` が既にサンプルをコピーしているなら、その仕組みに乗せる。
  - `SKILL.md`: 次を書く（既存の節を壊さず、番号を保つ）。
    1. §1 の流れの表に、入力と原稿の間の「設計図」の行を足す（承認①に含める: 設計図と原稿を一緒にチャットで承認）。
    2. §2 に「ヘッドの規則」（完全文・判断語・30〜60 字・まず 1 行 36 字幅・禁止（二段構え・数え上げ・体言止め・ダッシュ・自己言及）・文型を散らす・逆テスト・So What 帯なし）と、論点 3〜6 個（冒頭のサマリで番号を予告し、最終ページで同じ番号で回収）、台帳の書き方を足す。`lint-script` が検査するもの（字数・判断語・二段構え・ダッシュ・自己言及・文型の連続・論点の個数）と、人が見るもの（逆テスト・縦読み・回収）を分けて書く。
    3. §4 に「描画の規準」（配置の 4 原則・記号文法・グラフの作法・禁止）を足す。階調は基調色に白を 28・52・75% 混ぜる（`--accent-soft`・`--accent-mid`・`--accent-light`）。
    4. §5 の rule の表に `dash`・`sameWord`・`orphanLine`・`emptyBand` の直し方を足す。
    5. 「工程5（計測で検証）」の節を足す: 出す前に、ヘッド・数値（ヘッドの数字＝本体の合計。素材に無い数字は作らず前提つきの試算か「xx」）・証拠（ヘッドの各節→本体のどの要素が証明するか）・論理（縦読みで筋が通る）・見た目（`check` の警告 0 件）を確認し、手直しは 1 周。直せないものは「未達」と明記して報告する。
    6. 型の一覧に `small-multiples`（軸統一の小グラフ）を足す。
  - `README.md`: 新しい検査と `design.md`、サンプル原稿の内容が変わったことを書く（関連する節の更新）。

- [ ] **Step 4: 通ることを確認** — Run: `PYTEST -q` → すべて PASS。

- [ ] **Step 5: コミット** — `git add skills/pptx-deck README.md` → `git commit -m "docs: 設計図の工程・ヘッドの規則・描画の規準・工程5を SKILL.md に追加し、design.md の雛形を init がコピーする"`

---

### Task 9: 通しの確認

**Files:** なし（確認のみ。直しが出たら該当の Task のファイルを直す）

- [ ] **Step 1: 全テスト** — Run: `PYTEST -q` → すべて PASS。
- [ ] **Step 2: サンプルを通しで作る**（スクラッチパッド上）: `run.py init sample --color "#1976D2"` →（サンプル原稿の 11 枚の断片を `slides/` に写して）`variants` → `finalize` → `build`。出力 JSON の `ok` が true で、警告が 0 件であること。
- [ ] **Step 3: 見比べ**: `build` の PNG（LibreOffice）を、見本10本の PNG（`scratchpad\ref\s01〜s10.png`）と並べて、構図（要素の位置・強調の 1 点・線種・空白帯なし）を確認し、差を報告する。文字サイズ（下限 14pt）による見本との差は、SPEC の確認事項 1 の決定どおりであることを併せて報告する。
- [ ] **Step 4: 後始末**: `git status` で、意図しない変更・一時ファイルがないことを確認する。`docs/sample/`（利用者の見本）は、コミットするかを利用者に確認する（未追跡のまま残っている）。

---

## Self-Review（作成時に実施）
- **Spec coverage**: A（原稿の規則）→ Task 1・8。B（描画の規準）→ Task 2・3・4・8。C（部品庫の見た目）→ Task 5・6。D（設計図→検証）→ Task 8。サンプル原稿 → Task 7。受入条件 1〜5 → Task 1・2・5〜9。
- **未カバーと理由**: SPEC A の「台帳」「論点の最終ページでの回収」は、機械で判定せず SKILL.md の人の確認事項にした（論点の個数と文型だけ `lint-script`）。SPEC B の「同じ語を 1 枚に 2 度書かない」は、6 字以上の同一文言だけを警告にした（日本語の語の抽出は誤検出が多いため）。
- **断片の HTML**: Task 5・6 の断片は、全文をこの計画に埋め込まず、構図・寸法・使う class・文言の出どころを指定した。既存の断片（`tree.html` など）と同じ書式（`pp-*` 部品・絶対配置）で書き、`test_components.py` と画像の見比べで検証する。
- **型の整合**: `sentence_type`（Task 1）、`lastLineChars`（Task 2）、`.dashed`・`.f-outline`・`--accent-soft`（Task 3）、`dash`（Task 4）は、後続の Task で同じ名前を使っている。
