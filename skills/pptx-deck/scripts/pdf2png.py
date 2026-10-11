import json
import sys

import pymupdf

pdf, out, dpi = sys.argv[1], sys.argv[2], int(sys.argv[3])
doc = pymupdf.open(pdf)
paths = []
for i, page in enumerate(doc, 1):
    p = f"{out}/slide-{i:02d}.png"
    page.get_pixmap(dpi=dpi).save(p)
    paths.append(p)
print(json.dumps(paths))
