A relocatable **Python 3.12** interpreter (CPython 3.12.15) for Kaggle notebooks. Kaggle's notebook images built after 1 October 2026 run Python 3.13 by default, so wheels built for cp312, such as the SGLang "Pennyroyal" wheelhouse and the ARC-AGI-3 competition's `arc_agi_3_wheels`, do not install into the default Python. Some images still ship a `/usr/bin/python3.12`, but it is not guaranteed to be complete; this archive gives a self-contained interpreter to build a Python 3.12 virtual environment from.

## What is inside

| file | what it is |
|---|---|
| `cpython-3.12.15-x86_64-linux-gnu-install_only.tgz.bin` | the python-build-standalone CPython 3.12.15 build (release 20261009, x86_64-unknown-linux-gnu, `install_only`), unchanged apart from its file name: a gzip tar archive |
| `SHA256SUM.txt` | SHA-256 of the archive, listed under its upstream name `cpython-3.12.15+20261009-x86_64-unknown-linux-gnu-install_only.tar.gz` (the bytes are the same as the `.tgz.bin` file) |
| `README.md` | source and licence |

Upstream source: https://github.com/astral-sh/python-build-standalone/releases/tag/20261009

## Use it in a notebook

```python
import glob, subprocess, tarfile

archive = (glob.glob("/kaggle/input/datasets/carsonrodrigues/py312-portable/*.tgz.bin")
           + glob.glob("/kaggle/input/py312-portable/*.tgz.bin"))[0]
with tarfile.open(archive) as tar:
    tar.extractall("/tmp/py312")
python312 = "/tmp/py312/python/bin/python3.12"
subprocess.run([python312, "-m", "venv", "/tmp/venv312"], check=True)
subprocess.run(["/tmp/venv312/bin/pip", "--version"], check=True)
```

The two paths cover Kaggle's two dataset mount layouts. The ARC Prize 2026 GPU notebooks `carsonrodrigues/arc3-duck-*` use the archive this way: when the notebook's Python is not 3.12, they try this interpreter first and fall back to a system Python 3.12 only if it fails a standard-library import check (`kaggle/cells/00_env.py` in https://github.com/rodriguescarson/arc-agi-3).

## Licence

CPython is distributed under the Python Software Foundation License; the archive includes CPython's `LICENSE.txt`, and the upstream release lists the licences of the libraries it bundles.
