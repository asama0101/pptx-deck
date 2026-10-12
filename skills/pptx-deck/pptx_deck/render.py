"""PPTX → PDF（LibreOffice）→ PNG（pymupdf）。一時ファイルは tempfile で作る。"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def find_soffice() -> str:
    found = shutil.which("soffice")
    if found:
        return found
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe",
              r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if os.path.exists(p):
            return p
    raise RuntimeError("LibreOffice が見つかりません（確認用の画像が作れません）")


def pptx_to_pngs(pptx: Path, out_dir: Path, width_px: int = 1280, stem: str = "slide") -> list[Path]:
    import fitz  # pymupdf

    soffice = find_soffice()
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pptx-deck-so-") as td:
        profile = Path(td) / "profile"
        cmd = [soffice, f"-env:UserInstallation={profile.as_uri()}", "--headless",
               "--convert-to", "pdf", "--outdir", td, str(pptx)]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        pdf = Path(td) / (Path(pptx).stem + ".pdf")
        doc = fitz.open(str(pdf))
        paths = []
        for i, page in enumerate(doc):
            zoom = width_px / page.rect.width
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            p = out_dir / f"{stem}-{i + 1:02d}.png"
            pix.save(str(p))
            paths.append(p)
        doc.close()
    return paths
