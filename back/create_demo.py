"""Demo script to generate example images and test the locator."""

import cv2
import numpy as np
from pathlib import Path

# Create demo directory
demo_dir = Path(__file__).parent / "demo"
demo_dir.mkdir(exist_ok=True)

# Create a textured big image
np.random.seed(42)
big = np.random.randint(0, 256, (600, 800, 3), dtype=np.uint8)
big = cv2.GaussianBlur(big, (5, 5), 0)

# Add some distinctive features
cv2.rectangle(big, (200, 150), (400, 350), (255, 200, 100), -1)
cv2.circle(big, (300, 250), 80, (100, 255, 200), -1)
cv2.circle(big, (300, 250), 40, (200, 100, 255), -1)

# Add some text
cv2.putText(big, "NASA PROJECT", (220, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

# Save big image
cv2.imwrite(str(demo_dir / "big_image.png"), big)

# Extract a crop and scale it
x0, y0, w, h = 250, 200, 100, 100
crop = big[y0:y0+h, x0:x0+w].copy()

# Scale by 1.5x and add small rotation
small = cv2.resize(crop, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_LINEAR)
center = (small.shape[1] // 2, small.shape[0] // 2)
M = cv2.getRotationMatrix2D(center, 5, 1.0)
small = cv2.warpAffine(small, M, (small.shape[1], small.shape[0]))

# Save small image
cv2.imwrite(str(demo_dir / "small_crop.png"), small)

print(f"Demo images created in {demo_dir}/")
print(f"- big_image.png (800x600)")
print(f"- small_crop.png (scaled and rotated crop)")
print("\nRun the locator with:")
print(f"  python -m subimage_locator --big demo/big_image.png --small demo/small_crop.png --out demo/result.png --json demo/result.json")
