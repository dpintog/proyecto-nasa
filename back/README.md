# Subimage Locator

**Production-quality Python tool to locate scaled crops within larger images using feature matching and template matching.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## Features

- **Dual-pipeline architecture**: Feature matching (SIFT/AKAZE/ORB + RANSAC) with template matching fallback
- **Robust to transformations**: Handles scale changes, small rotations, perspective shifts, and illumination variations
- **Production-ready**: Type hints, comprehensive tests, CLI + library API
- **Visualization**: Draws detected region with corners and confidence overlay
- **JSON output**: Structured results for integration with pipelines

## Installation

### Windows (PowerShell)

```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r .\requirements.txt
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Quick Start

### Command Line

```powershell
# Basic usage - prints JSON to stdout
python -m subimage_locator --big large_image.jpg --small crop.png

# With visualization and JSON file
python -m subimage_locator --big large_image.jpg --small crop.png --out result.png --json result.json

# Limit processing resolution for speed
python -m subimage_locator --big huge_image.jpg --small crop.png --max-dim 1600 --out result.png
```

### Python API

```python
import cv2
from subimage_locator import locate_subimage

# Load images
big = cv2.imread("large_image.jpg")
small = cv2.imread("crop.png")

# Locate the crop
result = locate_subimage(big, small, min_scale=0.3, max_scale=3.0)

if result.found:
    print(f"Found using {result.method}")
    print(f"Scale: {result.scale:.2f}")
    print(f"Position: ({result.x:.1f}, {result.y:.1f})")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Corners: {result.corners}")
else:
    print("Not found")
```

## CLI Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--big` | Yes | - | Path to large image |
| `--small` | Yes | - | Path to small (crop) image |
| `--out` | No | None | Path to save visualization PNG |
| `--json` | No | stdout | Path to save JSON result |
| `--min-scale` | No | 0.3 | Minimum scale factor for template matching |
| `--max-scale` | No | 3.0 | Maximum scale factor for template matching |
| `--scales` | No | 60 | Number of scales to try |
| `--max-dim` | No | None | Downscale big image to this max dimension for faster processing |

## JSON Output Schema

```json
{
  "found": true,
  "method": "features",
  "scale": 1.5,
  "x": 234.5,
  "y": 156.2,
  "corners": [
    [234.5, 156.2],
    [384.5, 156.2],
    [384.5, 281.2],
    [234.5, 281.2]
  ],
  "inliers": 42,
  "score": null,
  "confidence": 0.87,
  "visualization_path": "result.png"
}
```

**Field descriptions:**

- `found` (bool): Whether the small image was located in the big image
- `method` (str|null): Detection method used (`"features"` or `"template"`)
- `scale` (float|null): Scale factor of small image in big image
- `x`, `y` (float|null): Top-left corner position in big image
- `corners` (array|null): Four corner coordinates `[[x,y], ...]` for polygon overlay
- `inliers` (int|null): Number of RANSAC inliers (features method only)
- `score` (float|null): Template matching correlation score (template method only)
- `confidence` (float): Overall confidence score 0-1
- `visualization_path` (str|null): Path to saved visualization if `--out` was used

## Exit Codes

- `0`: Match found successfully
- `1`: Input error (missing files, corrupt images, etc.)
- `2`: No match found

## Algorithm Details

### 1. Feature Matching (Primary)

- Detects keypoints using **SIFT** (falls back to AKAZE or ORB if unavailable)
- Matches descriptors with FLANN (SIFT) or BruteForce (binary)
- Applies **Lowe's ratio test** (threshold 0.75)
- Estimates **homography** with RANSAC
- Fits **similarity transform** on inliers to extract clean scale and translation
- Requires ≥10 inliers with corners inside big image

### 2. Template Matching (Fallback)

- Sweeps log-spaced scales between `min_scale` and `max_scale`
- Uses **normalized cross-correlation** (ZNCC: `cv2.TM_CCOEFF_NORMED`)
- Accepts match if correlation > 0.5 (configurable in code)
- Computes axis-aligned bounding box corners

### Confidence Calculation

- **Features**: `min(1.0, inliers / total_matches)`
- **Template**: Correlation score (0-1)

## Testing

Run the test suite:

```powershell
pytest tests/ -v
```

Tests include:

- ✅ Exact crop localization
- ✅ Scaled crop with small rotation
- ✅ Unrelated images (negative test)
- ✅ Corner validation
- ✅ Template matching fallback
- ✅ CLI integration

**Acceptance criteria (from tests):**

- Synthetic crops (0.5-2.0× scale, ≤8° rotation): `|scale_error| ≤ 5%`, position error ≤ 5px
- Unrelated images: `found = False`

## Performance Tips

1. **Use `--max-dim`** to downscale large images before processing (speeds up 4-16×)
2. **Reduce `--scales`** if template matching is slow (try 30-40 for faster results)
3. **Crop region of interest** in big image if you know approximate location
4. **Grayscale conversion** happens internally; no need to preprocess

## Limitations & Future Improvements

- **Rotation**: Feature matching handles ≤30° well; template matching assumes upright
- **Perspective**: Moderate perspective changes OK with features; severe distortion may fail
- **Repetitive patterns**: May produce false positives; consider increasing inlier threshold
- **Very small crops**: < 50×50 px may not have enough features

### Potential Enhancements

- **LoFTR/LightGlue**: Deep learning matchers for extreme viewpoint/scale changes (requires PyTorch)
- **Log-polar Fourier**: Estimate rotation+scale before template matching
- **Multiscale SIFT**: Detect features at multiple pyramid levels
- **GPU acceleration**: Use `cv2.cuda` for faster template matching

## License

MIT License - see project root for details.

## Contributing

Contributions welcome! Please ensure:

- Tests pass: `pytest tests/ -v`
- Code follows PEP8: `flake8 src/`
- Type hints added: `mypy src/`

## Example Use Cases

- **Satellite imagery**: Locate aerial photos within larger maps
- **Document analysis**: Find cropped signatures, logos, stamps
- **Quality control**: Detect product labels/barcodes on production lines
- **Forensics**: Match image crops to source photos
- **AR/robotics**: Localize known patterns in camera feeds

---

**Built with ❤️ for the NASA project**
