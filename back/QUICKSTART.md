# Quick Start Guide - Subimage Locator

## Setup (Windows PowerShell)

### Option 1: Use the automated setup script

```powershell
cd c:\Users\pinto\OneDrive\Documentos\proyecto-nasa\back
.\setup_env.ps1
```

### Option 2: Manual setup

```powershell
# Navigate to the project
cd c:\Users\pinto\OneDrive\Documentos\proyecto-nasa\back

# Create virtual environment
python -m venv .venv

# Activate it
.\.venv\Scripts\Activate.ps1

# If you get execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install dependencies
pip install --upgrade pip
pip install -r .\requirements.txt
```

## Running Tests

```powershell
# Set PYTHONPATH and run tests
$env:PYTHONPATH = "c:\Users\pinto\OneDrive\Documentos\proyecto-nasa\back\src"
pytest tests/test_locator.py -v
```

Expected output: **7 passed** ✅

## Demo: Test with Sample Images

### 1. Generate demo images

```powershell
python create_demo.py
```

This creates:
- `demo/big_image.png` - 800×600 textured image with shapes and text
- `demo/small_crop.png` - scaled + rotated crop from the big image

### 2. Run the locator

```powershell
# Set PYTHONPATH
$env:PYTHONPATH = "c:\Users\pinto\OneDrive\Documentos\proyecto-nasa\back\src"

# Run with visualization
python -m subimage_locator --big demo/big_image.png --small demo/small_crop.png --out demo/result.png --json demo/result.json
```

### 3. Check results

```powershell
# View JSON output
cat demo/result.json

# Open the visualization
start demo/result.png
```

Expected JSON fields:
- `"found": true`
- `"method": "features"` (using SIFT/AKAZE)
- `"scale": ~0.67` (since small is 1.5× bigger, scale is 1/1.5)
- `"confidence": >0.7`
- `"inliers": 40+`

## Using Your Own Images

```powershell
$env:PYTHONPATH = "c:\Users\pinto\OneDrive\Documentos\proyecto-nasa\back\src"

python -m subimage_locator --big path\to\large_image.jpg --small path\to\crop.png --out result.png --json result.json
```

### Tips

- **Large images**: Add `--max-dim 1600` to speed up processing
- **Fine-tune scale range**: Use `--min-scale 0.5 --max-scale 2.0` if you know approximate size
- **More scales**: Increase `--scales 80` for better precision (slower)

## Python API Example

```python
import cv2
from subimage_locator import locate_subimage

# Load images
big = cv2.imread("demo/big_image.png")
small = cv2.imread("demo/small_crop.png")

# Locate
result = locate_subimage(big, small)

if result.found:
    print(f"✅ Found using {result.method}")
    print(f"   Scale: {result.scale:.3f}")
    print(f"   Position: ({result.x:.1f}, {result.y:.1f})")
    print(f"   Confidence: {result.confidence:.2%}")
else:
    print("❌ Not found")
```

## Troubleshooting

### Import errors

Make sure PYTHONPATH is set:
```powershell
$env:PYTHONPATH = "c:\Users\pinto\OneDrive\Documentos\proyecto-nasa\back\src"
```

### SIFT not available

The code automatically falls back to AKAZE or ORB if SIFT is missing. Make sure you have `opencv-contrib-python` installed:
```powershell
pip install opencv-contrib-python
```

### Tests fail

Check installed versions:
```powershell
pip list | Select-String "opencv|numpy|pytest"
```

Expected:
- `opencv-python` ≥ 4.8.0
- `opencv-contrib-python` ≥ 4.8.0
- `numpy` ≥ 1.24.0
- `pytest` ≥ 7.4.0

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Try with your NASA satellite/aerial imagery
- Adjust thresholds in `locator.py` if needed (search for `0.75`, `0.5`, `10` for tunable parameters)
- Add rotation estimation for template matching (see README "Future Improvements")

---

**All tests passing? You're ready to go! 🚀**
