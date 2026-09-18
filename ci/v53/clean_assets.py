from pathlib import Path
from PIL import Image
import numpy as np

d = Path("DropboxMusicPlayer/app/src/main/res/drawable-nodpi")

def clean(name, x2, y2):
    p = d / name
    im = Image.open(p).convert("RGBA")
    w, h = im.size
    im = im.crop((0, 0, max(1, int(w * x2)), max(1, int(h * y2))))
    a = np.array(im)
    rgb = a[:, :, :3].astype(np.int16)
    # Remove screenshot white/near-white background only. Character linework stays intact.
    hi = rgb.max(axis=2)
    lo = rgb.min(axis=2)
    neutral_white = (lo > 238) & ((hi - lo) < 18)
    a[:, :, 3] = np.where(neutral_white, 0, 255).astype(np.uint8)

    # Trim fully-transparent border.
    alpha = a[:, :, 3]
    ys, xs = np.where(alpha > 0)
    if len(xs):
        pad = 8
        x0 = max(int(xs.min()) - pad, 0)
        x1 = min(int(xs.max()) + pad + 1, a.shape[1])
        y0 = max(int(ys.min()) - pad, 0)
        y1 = min(int(ys.max()) + pad + 1, a.shape[0])
        a = a[y0:y1, x0:x1]

    Image.fromarray(a).save(p, "WEBP", lossless=True, method=6)

# Crops are based only on the supplied Instagram screenshots:
# remove the right black bar and lower Instagram controls/captions.
clean("nudeong_pair.webp",     0.74, 0.50)
clean("nudeong_bowl.webp",     0.76, 0.63)
clean("nudeong_bottle.webp",   0.75, 0.64)
clean("nudeong_progress.webp", 0.64, 0.67)
