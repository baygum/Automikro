import rasterio
import pandas as pd
import numpy as np

# path buat input dan output
tiff_path = "./basemapllm.tiff"
csv_path = "./output_pixels.csv"

# buka file tiff
with rasterio.open(tiff_path) as src:
    transform = src.transform
    width = src.width
    height = src.height

    # baca band RGB
    r = src.read(1)
    g = src.read(2)
    b = src.read(3)

# buat grid pixel
rows, cols = np.meshgrid(
    np.arange(height),
    np.arange(width),
    indexing="ij"
)

# konversi pixel → koordinat lat long
xs, ys = rasterio.transform.xy(transform, rows, cols)
xs = np.array(xs).flatten()
ys = np.array(ys).flatten()

# ubah nilai rgb ke hex
hex_colors = [
    f"#{r_:02X}{g_:02X}{b_:02X}"
    for r_, g_, b_ in zip(
        r.flatten(),
        g.flatten(),
        b.flatten()
    )
]

# simpan ke csv
df = pd.DataFrame({
    "x": xs,
    "y": ys,
    "hex": hex_colors
})

df.to_csv(csv_path, index=False)

print(f"SELESAI: {len(df)} piksel ditulis ke {csv_path}")
