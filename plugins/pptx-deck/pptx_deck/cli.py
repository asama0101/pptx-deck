import argparse
import json
import sys
import tempfile
from pathlib import Path

from . import __version__, paths


def _has_font(registered: list[str], family: str) -> bool:
    return any(family in name for name in registered)


def _registered_fonts() -> list[str]:
    """レジストリの登録名（全員向け・利用者向け）。TTC 内のファミリも登録名に並ぶ。"""
    import winreg

    names: list[str] = []
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(root, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts") as k:
                i = 0
                while True:
                    names.append(winreg.EnumValue(k, i)[0])
                    i += 1
        except OSError:
            pass
    return names


def _font_installed() -> bool:
    return _has_font(_registered_fonts(), "BIZ UDPGothic")


def _ensure_derived(work: Path) -> None:
    """template.json があれば、欠けた派生ファイル（prune 済みのもの）を再生成する。無ければ何もしない。"""
    if (work / "template.json").exists():
        from . import lifecycle

        lifecycle.ensure_derived(work)


def cmd_doctor(args) -> int:
    out = {
        "version": __version__,
        "python": {"path": sys.executable},
        "venv": str(paths.venv_dir()),
        "font_biz_udp_gothic": _font_installed(),
    }
    warnings = []
    if not out["font_biz_udp_gothic"]:
        warnings.append(
            "BIZ UDPゴシックが未導入です。計測は代替フォントで行うため、折り返しが PowerPoint とずれる場合があります。"
        )
    out["warnings"] = warnings
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_init(args) -> int:
    from . import initdir

    try:
        r = initdir.init(
            Path(args.workdir), color=args.color, template_path=args.template, force=args.force, footer=args.footer
        )
    except (FileExistsError, ValueError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


def cmd_template_map(args) -> int:
    """テンプレートのレイアウトと、章扉・目次・型との対応（init が推定したもの）を出す。
    --set / --clear で、利用者の修正を template.json に反映する。"""
    from . import initdir, template

    work = paths.resolve_work(args.workdir)
    if not (work / "template.json").exists():
        print(f"エラー: {work} に template.json がありません（成果物の元データが見つかりません）", file=sys.stderr)
        return 2
    cfg = paths.read_cfg(work)
    info = template.TemplateInfo.from_dict(cfg["info"])
    path = work / cfg["template"]
    changed = False
    try:
        for item in args.set or []:
            key, sep, layout = item.partition("=")
            if not sep or not layout:
                raise ValueError(f"--set は 種類か型=レイアウト名 の形で指定してください: {item}")
            info = template.set_mapping(path, info, key.strip(), layout.strip())
            changed = True
        for key in args.clear or []:
            info = template.set_mapping(path, info, key.strip(), None)
            changed = True
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
    if changed:
        cfg["info"] = info.to_dict()
        paths.write_cfg(work, cfg)
        initdir.write_derived(work, cfg)  # 下地の色（theme.css）を直す。作り直す PPTX は build で
    print(json.dumps(template.describe(path, info), ensure_ascii=False, indent=2))
    return 0


def _no_cfg(work: Path) -> int | None:
    """作業フォルダに template.json がなければ案内を出して 2 を返す（あれば None）。"""
    if (work / "template.json").exists():
        return None
    print(f"エラー: {work} に template.json がありません（成果物の元データが見つかりません）", file=sys.stderr)
    return 2


def _load_cfg(work: Path):
    from . import template, theme

    cfg = paths.read_cfg(work)
    return cfg, template.TemplateInfo.from_dict(cfg["info"]), theme.derive(cfg["color"])


def cmd_check(args) -> int:
    from . import check, measure

    html = Path(args.html)
    if not html.is_file():
        print(f"エラー: {html} がありません", file=sys.stderr)
        return 2
    work = paths.resolve_work(args.workdir) if args.workdir else html.parent
    if code := _no_cfg(work):
        return code
    _, info, _ = _load_cfg(work)
    violations = check.check_model(measure.measure(html), info)
    print(json.dumps(violations, ensure_ascii=False, indent=2))
    return 1 if check.errors(violations) else 0


def _guard_edits(work: Path) -> int:
    """断片へ反映していない編集（回答の「- 編集:」）が残っていれば、止める。"""
    from . import fragedit, variants

    todo = [f.name for f in variants.answer_paths(work) if fragedit.has_unapplied(paths.read_text(f))]
    if not todo:
        return 0
    print(
        f"エラー: 断片へ反映していない編集があります（{', '.join(todo)}）。先に apply-edits を実行してください",
        file=sys.stderr,
    )
    return 2


def cmd_apply_edits(args) -> int:
    from . import fragedit, variants

    work = paths.resolve_work(args.workdir)
    try:
        files = (
            [Path(args.answers)]
            if args.answers
            else [f for f in variants.answer_paths(work) if fragedit.has_unapplied(paths.read_text(f))]
        )
        results = [{"answers": f.name, **fragedit.apply_answers(work, f)} for f in files]
    except (ValueError, OSError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
    print(json.dumps(results if results else {"applied": []}, ensure_ascii=False, indent=2))
    if any(r["applied"] for r in results):
        print("断片を書き換えました。finalize をやり直してください", file=sys.stderr)
    skipped = [(r["answers"], s) for r in results for s in r["skipped"]]
    for (
        name,
        s,
    ) in (
        skipped
    ):  # 反映できなかった編集は黙って捨てない。知らせたあとは guard を外す（fragedit.apply_answers の docstring）
        where = f"{s['f']} {s['t']}".strip()
        print(f"反映できませんでした: {name} {where + ' ' if where else ''}（{s['reason']}）", file=sys.stderr)
    if skipped:
        print(
            "上の編集は断片に入っていません。断片か回答を直して再実行するか、断片を手で直してください", file=sys.stderr
        )
        return 1
    return 0


def _check_writable(out: Path) -> str | None:
    """出力先に書けるかを、測定の前に確かめる。書けなければ案内の文を返す。
    既存の PPTX は追記モードで開いて閉じるだけ（中身を変えない）。
    なければ親フォルダを作り、同じ場所に作った一時ファイルで確かめる（out は作らない）。"""
    hint = "PowerPoint で開いていれば閉じてください"
    try:
        if out.exists():
            with out.open("ab"):
                pass
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryFile(dir=out.parent):
                pass
    except OSError as e:
        return f"{out} に書き込めません（{e}）。{hint}。"
    return None


def cmd_build(args) -> int:
    from . import build, check, lifecycle, measure, preview

    work = paths.resolve_work(args.workdir)
    if code := _no_cfg(work):
        return code
    if code := _guard_edits(work):
        return code
    _ensure_derived(work)
    name = paths.deck_name(work)
    try:
        tkey = paths.temp_key(
            name, work
        )  # 確認用の画像の置き場の名前を、書き出す前に確かめる（作業フォルダごとに分ける）
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
    cfg, info, palette = _load_cfg(work)
    html = work / "final.html"
    if not html.exists():
        print("エラー: final.html がありません（先に finalize を実行してください）", file=sys.stderr)
        return 2
    default_out = paths.deck_dir(work) / f"{name}.pptx"
    out = Path(args.out).resolve() if args.out else default_out
    if out.is_dir() or out.suffix.lower() != ".pptx":
        print(f"エラー: --out には .pptx のファイル名を指定してください（{out}）", file=sys.stderr)
        return 2
    if out == default_out and not args.force:
        st = lifecycle.fingerprint_status(work, out)
        if st == "modified":
            print(
                f"エラー: {out.name} は前回のビルドのあとに変更されています。"
                "作り直すと PowerPoint での手直しが消えます。"
                "上書きしてよければ --force、別の名前で出すなら --out <パス> を付けてください。",
                file=sys.stderr,
            )
            return 4
        if st == "unrecorded":
            print(
                f"エラー: {out.name} は記録のない PPTX です（build.json がない、または読めません）。"
                "元の資料かもしれず、作り直すと消えます。"
                "上書きしてよければ --force、別の名前で出すなら --out <パス> を付けてください。",
                file=sys.stderr,
            )
            return 4
    if out != default_out and out.exists() and not args.force:
        print(
            f"エラー: {out} は既に存在します。上書きしてよければ --force、別の名前で出すなら --out を変えてください。",
            file=sys.stderr,
        )
        return 4
    if msg := _check_writable(out):
        print(f"エラー: {msg}", file=sys.stderr)
        return 2
    model = measure.measure(html, raster_dir=paths.temp_dir(tkey) / "picture")  # 絵（pp-picture）は、ここで画像にする
    violations = check.check_model(model, info)
    result = {
        "ok": False,
        "violations": violations,
        "pptx": None,
        "previews": [],
        "removed": [],
        "notes": list(info.notes),
    }
    if check.errors(violations):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    footer = args.footer if args.footer is not None else cfg.get("footer")
    build.build(model, work / cfg["template"], info, palette, out, base_dir=work, footer=footer, work_name=tkey)
    if out == default_out:
        lifecycle.record_build(work, out)  # 検査で止まっても、書いた PPTX を「変更済み」と誤検出しないよう先に記録する
    violations += check.check_pptx(out)
    result["violations"] = violations
    result["pptx"] = str(out)
    try:
        result["previews"] = [str(p) for p in preview.screenshots(html, paths.temp_dir(tkey) / "preview")]
    except Exception as e:  # noqa: BLE001  # PPTX は出ている。確認用の画像だけ作れなかったことを知らせる
        result["notes"].append(f"確認用の画像を作れませんでした: {e}")
    result["ok"] = not check.errors(violations)
    if result["ok"]:
        result["removed"] = lifecycle.prune(work)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


def cmd_export_html(args) -> int:
    from . import htmlexport, lifecycle

    work = paths.resolve_work(args.workdir)
    if code := _guard_edits(work):
        return code
    _ensure_derived(work)
    try:
        result = htmlexport.export(work, Path(args.out).resolve() if args.out else None)
    except (ValueError, OSError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
    if args.prune:
        result["removed"] = lifecycle.prune(work)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_clean(args) -> int:
    from . import lifecycle

    work = paths.resolve_work(args.workdir)
    name = paths.deck_name(work)
    try:
        target = str(paths.temp_dir(name, work))  # 先にパスを求める（temp_dir は作って返す）
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
    lifecycle.clean_temp(name, work)
    print(json.dumps({"cleaned": target}, ensure_ascii=False))
    return 0


def cmd_variants(args) -> int:
    from . import variants

    work = paths.resolve_work(args.workdir)
    if code := _guard_edits(work):
        return code
    _ensure_derived(work)
    try:
        print(variants.assemble(work, round_no=args.round or variants.next_round(work)))
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
    return 0


def _answers_files(work: Path, given: list[str] | None) -> list[Path]:
    from . import variants

    return (
        [Path(p) for p in given] if given else variants.answer_paths(work, include_final=False)
    )  # 最終確認の回答は案を決めない


def _answers_mds(work: Path, given: list[str] | None) -> list[str]:
    return [paths.read_text(f) for f in _answers_files(work, given)]


def _final_preset_mds(work: Path) -> list[str]:
    """前回の最終確認の回答（answers-final.md）。最終確認ページの承認の選択済み表示にだけ使う。"""
    f = work / "answers-final.md"
    return [paths.read_text(f)] if f.exists() else []


def cmd_finalize(args) -> int:
    from . import variants

    work = paths.resolve_work(args.workdir)
    if code := _no_cfg(work):
        return code
    if code := _guard_edits(work):
        return code
    _ensure_derived(work)
    files = _answers_files(work, args.answers)
    mds = [paths.read_text(f) for f in files]  # 回ごとの回答を順に重ねる
    try:
        print(
            variants.finalize(work, mds, allow_comments=args.allow_comments, preset_extra_mds=_final_preset_mds(work))
        )
    except ValueError as e:
        print(f"エラー:\n{e}", file=sys.stderr)
        return 2
    old = paths.read_cfg(work)["color"]
    r = _apply_color_from_answers(
        work, mds, [f.name for f in files]
    )  # 案の統合が成功したあとに、回答の配色を反映する（メッセージは stderr）
    if r == "applied":
        new = paths.read_cfg(work)["color"]
        print(f"配色を {old} → {new} に変えました（theme.css を作り直しました）", file=sys.stderr)
    elif r == "skipped_pptx":
        print(
            "PPTX が作成済みなので配色は変えていません。"
            "変えるなら set-color を使ってください（そのあと build で PPTX を作り直します）",
            file=sys.stderr,
        )
    return 0


def _consume_color(cfg: dict, resolved: str, source: str | None) -> None:
    """反映済みの回答の配色と、それを書いた回答のファイル名（分からなければ記録しない）を覚える。"""
    cfg["answers_color"] = resolved
    if source:
        cfg["answers_color_from"] = source
    else:
        cfg.pop("answers_color_from", None)


def _apply_color_from_answers(work: Path, mds: list[str], names: list[str] | None = None) -> str:
    """回答の「- 配色:」を template.json に反映する。
    "none"（配色なし・現在と同じ）、"applied"、"skipped_pptx"（PPTX があるので変えない）。
    names は mds と同じ順の回答のファイル名。渡すと、反映済みの判定を「値と、それを書いたファイル」で行う
    （set-color のあとに別の回の回答で同じ色を選び直したら反映する）。"""
    from . import initdir, lifecycle, theme, variants

    want = variants.parse_settings(mds)["color"]
    if not want:
        return "none"
    ci = variants.color_index(mds)
    source = names[ci] if names and ci is not None else None
    cfg = paths.read_cfg(work)
    try:
        resolved = theme.resolve(want)
    except ValueError:
        return "none"  # 不正な色は無視する（手で書き換えた回答など）
    if variants.color_consumed(cfg, resolved, source):
        return "none"  # 反映済みの回答値は再適用しない（set-color の選択を戻さない）
    if resolved == cfg["color"]:
        _consume_color(cfg, resolved, source)  # すでに同じ色。反映済みとして覚える
        paths.write_cfg(work, cfg)
        return "none"
    pptx = paths.deck_dir(work) / f"{paths.deck_name(work)}.pptx"
    if lifecycle.fingerprint_status(work, pptx) != "missing":
        if resolved == cfg.get("skipped_color"):
            return "none"  # 同じ警告は繰り返さない（PPTX を消したあとは反映する）
        cfg["skipped_color"] = resolved
        paths.write_cfg(work, cfg)
        return "skipped_pptx"
    initdir.set_color(work, want)
    cfg = paths.read_cfg(work)
    _consume_color(cfg, resolved, source)
    paths.write_cfg(work, cfg)
    return "applied"


def cmd_set_color(args) -> int:
    from . import initdir

    work = paths.resolve_work(args.workdir)
    if not (work / "template.json").exists():
        print(f"エラー: {work} に template.json がありません（成果物の元データが見つかりません）", file=sys.stderr)
        return 2
    try:
        notes = initdir.set_color(work, args.color)
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
    for n in notes:
        print(n, file=sys.stderr)
    print(f"配色を {args.color} に変えました。PPTX は build で作り直してください")
    return 0


def cmd_output_format(args) -> int:
    from . import variants

    print(variants.output_format(paths.resolve_work(args.workdir)))
    return 0


def cmd_review_final(args) -> int:
    from . import variants

    work = paths.resolve_work(args.workdir)
    if code := _guard_edits(work):
        return code
    _ensure_derived(work)
    mds = _answers_mds(work, args.answers)
    try:
        print(
            variants.review_final(
                work, mds, allow_comments=args.allow_comments, preset_extra_mds=_final_preset_mds(work)
            )
        )
    except ValueError as e:
        print(f"エラー:\n{e}", file=sys.stderr)
        return 2
    return 0


def cmd_review_plan(args) -> int:
    from . import plan_review

    work = paths.resolve_work(args.workdir)
    _ensure_derived(work)
    for need in ("design.md", "script.md"):
        if not (work / need).exists():
            print(f"エラー: {work / need} がありません", file=sys.stderr)
            return 2
    print(plan_review.assemble(work, round_no=args.round))
    return 0


def cmd_reopen(args) -> int:
    from . import lifecycle

    work = paths.resolve_work(args.workdir)
    if not (work / "template.json").exists():
        print(f"エラー: {work} に template.json がありません（成果物の元データが見つかりません）", file=sys.stderr)
        return 2
    r = lifecycle.reopen(work)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 4 if r["status"] in ("modified", "unrecorded") and not args.force else 0


def cmd_draft(args) -> int:
    """slides/ の断片を束ねて、確認用の画像と検査の結果を返す（絵の往復で、直すたびに使う）。PPTX は出さない。"""
    import shutil
    import time

    from . import check, draft, measure, preview

    work = paths.resolve_work(args.workdir)
    if code := _no_cfg(work):
        return code
    _ensure_derived(work)
    name = paths.deck_name(work)
    try:
        html, nns = draft.assemble(work, pick=args.pick, slides=args.slide)
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
    try:
        _, info, _ = _load_cfg(work)
        violations = check.check_model(measure.measure(html), info)
        # 確認用の画像は実行ごとの一意なフォルダへ（呼び出し側が見るので残す）。1 日より古い実行は消す
        root = paths.temp_dir(name, work) / "draft"
        root.mkdir(parents=True, exist_ok=True)
        for old in root.iterdir():
            if old.is_dir() and time.time() - old.stat().st_mtime > 86400:
                shutil.rmtree(old, ignore_errors=True)
        out_dir = Path(tempfile.mkdtemp(dir=root, prefix="run-"))
        previews = [str(p) for p in preview.screenshots(html, out_dir)]
    finally:
        html.unlink(missing_ok=True)
    print(
        json.dumps(
            {"ok": not check.errors(violations), "slides": nns, "previews": previews, "violations": violations},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not check.errors(violations) else 1


def cmd_review_picture(args) -> int:
    from . import picture_plan

    work = paths.resolve_work(args.workdir)
    _ensure_derived(work)
    try:
        print(picture_plan.assemble(work, paths.deck_name(work), args.round))
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
    return 0


def cmd_picture_status(args) -> int:
    """絵の提案・構造の確認の回答（answers-picture-*.md）から、絵にする箇所・直す項目・未決を出す。
    未決と修正が 0 件なら frozen。"""
    from . import picture_plan

    work = paths.resolve_work(args.workdir)
    try:
        plan = picture_plan.load_plan(work)
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
    answers = picture_plan.merge_answers([paths.read_text(p) for p in picture_plan.answer_paths(work)])
    r = picture_plan.resolve(plan, answers)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r["frozen"] else 1


def cmd_history(args) -> int:
    from . import history

    work = paths.resolve_work(args.workdir)
    try:
        if args.action == "snapshot":
            r = history.snapshot(work, args.label or "")
        elif args.action == "list":
            r = history.versions(work)
        else:
            if args.version is None:
                raise ValueError("restore には版の番号が要ります（history <名前> list で確かめる）")
            r = history.restore(work, args.version, args.slide)
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


def cmd_lint_script(args) -> int:
    from . import script_lint

    md = paths.read_text(args.script)
    problems = script_lint.lint(md)
    for p in problems:
        print(p)
    for n in script_lint.title_notes(md):  # 題の抜けの案内は、エラーにしない（終了コードに影響しない）
        print(n)
    return 1 if problems else 0


def entry(argv: list[str]) -> int:
    """python -m pptx_deck の入口。依存が足りない仮想環境では、traceback ではなく案内を出す。"""
    try:
        return main(argv)
    except ModuleNotFoundError as e:
        print(f"必要なモジュールがありません: {e.name}")
        print(
            "専用の仮想環境が壊れているか、依存が足りません。"
            '`python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "${CLAUDE_PLUGIN_DATA}" doctor` で確認し、'
            "利用者の承認後に `setup --yes`（同じ `--data` 付き）を実行してください。"
        )
        return 3
    except (
        ValueError,
        OSError,
    ) as e:  # 個別に捕まえていない入力の不備（ファイルがない・書けない・テンプレートが消えた等）
        print(f"エラー: {e}", file=sys.stderr)
        return 2


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="pptx-deck")
    ap.add_argument("--version", action="version", version=f"pptx-deck {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    p = sub.add_parser("init")
    p.add_argument("workdir")
    p.add_argument(
        "--color",
        default=None,
        help="プリセット名（navy|green|gray）または #RRGGBB。省略すると navy（--force なら既存の値を残す）",
    )
    p.add_argument("--template", default=None, help="利用者の .potx / .pptx")
    p.add_argument(
        "--footer",
        default=None,
        help='左下に出すコピーライトの文字列（例: "© 2026 〇〇"）。省略すると空欄（--force なら既存の値を残す）',
    )
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser(
        "template-map",
        help="テンプレートのレイアウトと、章扉・目次・型との対応を出す。--set 型=レイアウト名 / --clear 型 で直す",
    )
    p.add_argument("workdir")
    p.add_argument(
        "--set",
        action="append",
        default=None,
        help="対応を直す（例: agenda=目次 / gantt=スケジュール / section=2）。レイアウトは名前か番号。複数指定できる",
    )
    p.add_argument("--clear", action="append", default=None, help="専用レイアウトをやめて本文で代える（例: gantt）")
    p.set_defaults(fn=cmd_template_map)
    p = sub.add_parser("check")
    p.add_argument("html")
    p.add_argument("--workdir", default=None)
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser("build")
    p.add_argument("workdir")
    p.add_argument("--footer", default=None)
    p.add_argument("--out", default=None, help="PPTX の出力先（省略すると <出力先>/<成果物名>.pptx）")
    p.add_argument("--force", action="store_true", help="前回のビルド後に変更された PPTX も上書きする")
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("export-html", help="final.html を 1 枚で完結する閲覧用 HTML にする（<出力先>/<成果物名>.html）")
    p.add_argument("workdir")
    p.add_argument("--out", default=None, help="HTML の出力先（省略すると <出力先>/<成果物名>.html）")
    p.add_argument("--prune", action="store_true", help="成功後に派生ファイルを片付ける（HTML だけを選んだとき）")
    p.set_defaults(fn=cmd_export_html)
    p = sub.add_parser("clean")
    p.add_argument("workdir")
    p.set_defaults(fn=cmd_clean)
    p = sub.add_parser("variants")
    p.add_argument("workdir")
    p.add_argument("--round", type=int, default=None)
    p.set_defaults(fn=cmd_variants)
    p = sub.add_parser("finalize")
    p.add_argument("workdir")
    p.add_argument(
        "--answers",
        action="append",
        default=None,
        help="回答の Markdown。回ごとに複数回指定できる（後の回答が前の回答を上書きする）",
    )
    p.add_argument("--allow-comments", action="store_true")
    p.set_defaults(fn=cmd_finalize)
    p = sub.add_parser("review-final")
    p.add_argument("workdir")
    p.add_argument(
        "--answers", action="append", default=None, help="finalize と同じ回答の Markdown（回ごとに複数回指定できる）"
    )
    p.add_argument("--allow-comments", action="store_true")
    p.set_defaults(fn=cmd_review_final)
    p = sub.add_parser("apply-edits", help="回答の「- 編集:」を断片へ反映する（反映後は finalize をやり直す）")
    p.add_argument("workdir")
    p.add_argument("--answers", default=None, help="この回答だけ反映する（省略すると、未反映の回答すべて）")
    p.set_defaults(fn=cmd_apply_edits)
    p = sub.add_parser("review-plan")
    p.add_argument("workdir")
    p.add_argument("--round", type=int, default=None)
    p.set_defaults(fn=cmd_review_plan)
    p = sub.add_parser("set-color", help="配色を変える（theme.css を作り直す。PPTX は build で作り直す）")
    p.add_argument("workdir")
    p.add_argument("color", help="プリセット名（navy・green・gray）か #RRGGBB")
    p.set_defaults(fn=cmd_set_color)
    p = sub.add_parser("output-format", help="最終成果物の形式（pptx・html・both のいずれか 1 語）を出す")
    p.add_argument("workdir")
    p.set_defaults(fn=cmd_output_format)
    p = sub.add_parser("reopen")
    p.add_argument("workdir")
    p.add_argument("--force", action="store_true", help="PPTX が変更されていても続ける（手直しは消える）")
    p.set_defaults(fn=cmd_reopen)
    help_draft = "slides/ の断片を束ねて、確認用の画像と検査の結果を返す（絵の往復用。PPTX は出さない）"
    p = sub.add_parser("draft", help=help_draft)
    p.add_argument("workdir")
    p.add_argument("--pick", default="A", help="各スライドで使う案（A/B/C。なければ最初の案）")
    p.add_argument("--slide", action="append", default=None, help="このスライドだけ（例: 02。複数指定できる）")
    p.set_defaults(fn=cmd_draft)
    help_review_picture = (
        "絵にする箇所の提案と、読み取った構造の確認ページ（picture-plan.json から picture-review.html）"
    )
    p = sub.add_parser("review-picture", help=help_review_picture)
    p.add_argument("workdir")
    p.add_argument("--round", type=int, default=None)
    p.set_defaults(fn=cmd_review_picture)
    help_picture_status = (
        "提案・構造の確認の回答（answers-picture-*.md）から、絵にする箇所・直す項目・未決を出す"
        "（終了コード 0＝凍結してよい）"
    )
    p = sub.add_parser("picture-status", help=help_picture_status)
    p.add_argument("workdir")
    p.set_defaults(fn=cmd_picture_status)
    p = sub.add_parser("history", help="絵の往復の履歴（直す前の slides/*.html を残す・戻す）")
    p.add_argument("workdir")
    p.add_argument("action", choices=["snapshot", "list", "restore"])
    p.add_argument("version", nargs="?", type=int, default=None, help="restore する版の番号")
    p.add_argument("--label", default=None, help="snapshot の名前（例: 構図を変える前）")
    p.add_argument("--slide", default=None, help="restore で戻すスライドの番号（例: 02）。省略すると全部")
    p.set_defaults(fn=cmd_history)
    p = sub.add_parser("lint-script")
    p.add_argument("script")
    p.set_defaults(fn=cmd_lint_script)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except paths.LayoutError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
