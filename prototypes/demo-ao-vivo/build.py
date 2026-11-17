"""Gera index.html embutindo a biblioteca de QR (qrcode-generator 2.0.4, MIT).
Uso: python3 prototypes/demo-ao-vivo/build.py <caminho para qrcode.js> [url do artefato no claude.ai]"""
import sys
from pathlib import Path
here = Path(__file__).parent
lib = Path(sys.argv[1]).read_text()
url = sys.argv[2] if len(sys.argv) > 2 else ""
out = (here / "demo.tpl.html").read_text().replace("__QRLIB__", lib).replace("__ARTIFACT_URL__", url)
(here / "index.html").write_text(out)
print("index.html:", len(out), "bytes")
