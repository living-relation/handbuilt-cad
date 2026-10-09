#!/bin/bash
export PATH=$HOME/.local/bin:$PATH
cd ~/projects/handbuilt-models
find . -path ./.venv -prune -o -path ./.git -prune -o -type d -exec chmod 755 {} + -o -type f -exec chmod 644 {} +
find . -path ./.venv -prune -o -name '*.sh' -exec chmod 755 {} +
chmod -R u+rwX,go+rX,go-w .git
[ -x .venv/bin/python ] || uv venv .venv --python 3.13
uv pip install --python .venv/bin/python build123d==0.13.0 trimesh numpy scipy matplotlib rtree 2>&1 | tail -3
.venv/bin/python -c "import sys,build123d,trimesh,numpy,scipy,matplotlib,rtree; print('OK py', sys.version.split()[0], 'build123d', build123d.__version__, 'trimesh', trimesh.__version__, 'numpy', numpy.__version__)"
cd pcv_adapter && T=$(mktemp -d) && cp pcv_adapter.py $T/ && (cd $T && ~/projects/handbuilt-models/.venv/bin/python pcv_adapter.py | tail -2; ls) ; rm -rf $T