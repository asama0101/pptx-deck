"""開始ページ（入力と保存先を選ぶ HTML）を作る。作業フォルダの一覧は scan で調べて埋め込む（サーバーなし）。"""

import json
from pathlib import Path

from . import paths, scan

TEMPLATE = paths.ASSETS / "web" / "start-page.html"
_MARK = "/*__DATA__*/null"


def render(data: dict) -> str:
    """テンプレートの印をデータの JSON に置き換える。`</` は `<\\/` にして、script を途中で閉じさせない。"""
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(_MARK) != 1:
        raise ValueError(f"開始ページのテンプレートに {_MARK} が 1 つではありません: {TEMPLATE}")
    return template.replace(_MARK, json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))


def build(cwd: Path, out: Path | None = None) -> Path:
    out = paths.temp_dir("start") / "start-page.html" if out is None else out
    out.write_text(render(scan.scan(cwd)), encoding="utf-8")
    return out
