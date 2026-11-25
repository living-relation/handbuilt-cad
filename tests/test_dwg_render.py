"""drawing/dwg.py render(): solid lines of one style are drawn in one call; dashed lines one call each."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "drawing"))
import dwg  # noqa: E402


def test_render_batches_solid_lines_only(tmp_path, monkeypatch):
    from matplotlib.axes import Axes
    calls = []
    real_plot = Axes.plot

    def counting_plot(self, *a, **k):
        calls.append(len(a[0]))
        return real_plot(self, *a, **k)

    monkeypatch.setattr(Axes, "plot", counting_plot)
    sh = dwg.Sheet()
    for i in range(200):
        sh.line((20, 20 + i), (120, 20 + i), "vis")                  # 200 solid lines
    sh.line((150, 20), (250, 20), "hid")                              # 2 dashed lines
    sh.line((150, 40), (250, 40), "ctr")
    png = str(tmp_path / "t")
    dwg.render([sh], str(tmp_path / "t.pdf"), png_prefix=png)
    assert len(calls) == 3                                            # 1 batched solid call + 1 per dashed line
    assert max(calls) == 200 * 3 - 1                                  # 200 two-point lines joined by NaN breaks
    assert os.path.getsize(png + "_sh1.png") > 0


def test_render_draws_every_solid_line(tmp_path):
    import matplotlib.image as mpimg
    sh = dwg.Sheet()
    for y in (50, 100, 150):
        sh.line((50, y), (300, y), "vis")
    png = str(tmp_path / "t")
    dwg.render([sh], str(tmp_path / "t.pdf"), png_prefix=png)
    img = mpimg.imread(png + "_sh1.png")[:, :, 0]
    h = img.shape[0]
    for y in (50, 100, 150):
        row = int(round(h * (1 - y / dwg.PH)))
        assert img[row - 2:row + 3, img.shape[1] // 4].min() < 0.5     # a dark line at each height
