"""開始ページの回答（md）を読み、入力・出力先・成果物名を検証して解決する。何も作らない。"""

import re
import tempfile
from pathlib import Path


class IntakeError(ValueError):
    pass


_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = re.compile(r"(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])", re.IGNORECASE)


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    return s


def parse(md: str) -> dict:
    lines = md.replace("\r\n", "\n").split("\n")
    if lines[:1] != ["---"] or "---" not in lines[1:] or "start: 1" not in lines[1 : lines.index("---", 1)]:
        raise IntakeError("開始ページの回答ではありません（先頭に `start: 1` がありません）")
    body = lines[lines.index("---", 1) + 1 :]
    out = {"kind": "", "files": [], "text": "", "out_dir": "", "name": ""}
    text: list[str] = []
    for i, ln in enumerate(body):
        if ln.startswith("## ") and ln[3:].strip() == "本文":
            text = body[i + 1 :]  # 本文は最後の節。貼り付けた Markdown の見出しや箇条書きも、末尾まで本文として読む
            break
        m = re.match(r"-\s*(種別|ファイル|フォルダ|名前)\s*[:：]\s*(.*)$", ln)
        if not m:
            continue
        key, val = m.group(1), _unquote(m.group(2))
        if key == "種別":
            out["kind"] = {"ファイル": "file", "テキスト": "text"}.get(val, "")
        elif key == "ファイル":
            if val:
                out["files"].append(val)
        elif key == "フォルダ":
            out["out_dir"] = val
        else:
            out["name"] = val
    if not out["kind"]:
        raise IntakeError("入力の種別（ファイル／テキスト）がありません")
    out["text"] = "\n".join(text).strip("\n") if out["kind"] == "text" or any(t.strip() for t in text) else ""
    return out


def _check_name(name: str) -> None:
    if not name:
        raise IntakeError("成果物名が空です")
    if _FORBIDDEN.search(name):
        raise IntakeError(f'成果物名に使えない文字があります（半角の < > : " / \\ | ? * と制御文字）: {name}')
    if name in (".", "..") or name != name.rstrip(" ."):
        raise IntakeError(f"成果物名の末尾にドットか空白は使えません（`.`・`..` も不可）: {name}")
    if _RESERVED.fullmatch(name.split(".")[0]):
        raise IntakeError(f"成果物名に Windows の予約名は使えません: {name}")


def _abs(p: str, cwd: Path) -> Path:
    q = Path(p)
    return q if q.is_absolute() else cwd / q


def resolve(raw: dict, cwd: Path) -> dict:
    kind, text = raw["kind"], raw["text"].strip()
    if raw["files"] and text:
        raise IntakeError("ファイルとテキストの両方が指定されています。どちらか一方にしてください")
    files: list[Path] = []
    if kind == "file":
        if not raw["files"]:
            raise IntakeError("ファイルが指定されていません")
        for f in raw["files"]:
            p = _abs(f, cwd)
            if not p.exists():
                raise IntakeError(f"ファイルが見つかりません: {p}")
            if not p.is_file():
                raise IntakeError(f"ファイルではありません（フォルダです）: {p}")
            files.append(p)
    elif not text:
        raise IntakeError("本文が空です")
    name = raw["name"] or (files[0].stem if files else "")
    _check_name(name)
    out_dir = _abs(raw["out_dir"], cwd) if raw["out_dir"] else cwd
    if not out_dir.is_dir():
        raise IntakeError(f"出力先のフォルダが見つかりません: {out_dir}")
    try:
        with tempfile.TemporaryFile(dir=out_dir):
            pass
    except OSError as e:
        raise IntakeError(f"出力先に書き込めません: {out_dir}（{e}）") from e
    workdir = out_dir / "pptx-deck-source" / name
    pptx = out_dir / f"{name}.pptx"
    return {
        "kind": kind,
        "files": [str(p) for p in files],
        "text": text,
        "out_dir": str(out_dir),
        "name": name,
        "workdir": str(workdir),
        "pptx": str(pptx),
        "collisions": [str(p) for p in (workdir, pptx) if p.exists()],
    }
