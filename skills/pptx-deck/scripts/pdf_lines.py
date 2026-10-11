import json
import sys

import pymupdf

doc = pymupdf.open(sys.argv[1])
counts = []
for page in doc:
    n = 0
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") == 0:
            n += len(b["lines"])
    counts.append(n)
print(json.dumps(counts))
