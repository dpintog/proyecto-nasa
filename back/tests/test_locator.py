"""Unit tests for subimage locator."""

import numpy as np
import cv2
import pytest
from pathlib import Path
import tempfile

from subimage_locator import locate_subimage, LocateResult


def create_textured_image(width: int, height: int, seed: int = 42) -> np.ndarray:
    """Create a random textured image for testing."""
    np.random.seed(seed)
    # Generate Perlin-like noise texture
    image = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
    # Add some structure with Gaussian blur
    image = cv2.GaussianBlur(image, (5, 5), 0)
    # Add some features
    for _ in range(10):
        x, y = np.random.randint(10, width - 10), np.random.randint(10, height - 10)
        cv2.circle(image, (x, y), np.random.randint(5, 15), 
                   tuple(np.random.randint(0, 256, 3).tolist()), -1)
    return image


def test_locate_exact_crop():
    """Test locating an exact unscaled crop."""
    # Create a textured image
    big = create_textured_image(800, 600, seed=42)
    
    # Extract a crop
    x0, y0, w, h = 200, 150, 150, 100
    small = big[y0:y0+h, x0:x0+w].copy()
    
    # Locate it
    result = locate_subimage(big, small)
    
    assert result.found, "Should find exact crop"
    assert result.x is not None and result.y is not None
    assert abs(result.x - x0) < 5, f"X position off: expected {x0}, got {result.x}"
    assert abs(result.y - y0) < 5, f"Y position off: expected {y0}, got {result.y}"
    assert result.scale is not None
    assert abs(result.scale - 1.0) < 0.05, f"Scale should be ~1.0, got {result.scale}"
    assert result.confidence > 0.5


def test_locate_scaled_crop():
    """Test locating a scaled crop with small rotation."""
    # Create a textured image
    big = create_textured_image(800, 600, seed=43)
    
    # Extract and scale a crop
    x0, y0, w, h = 250, 200, 120, 80
    crop = big[y0:y0+h, x0:x0+w].copy()
    
    # Scale by 1.5x
    scale = 1.5
    small = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    
    # Add small rotation (3 degrees)
    center = (small.shape[1] // 2, small.shape[0] // 2)
    M = cv2.getRotationMatrix2D(center, 3, 1.0)
    small = cv2.warpAffine(small, M, (small.shape[1], small.shape[0]))
    
    # Locate it
    result = locate_subimage(big, small, min_scale=0.5, max_scale=2.5)
    
    assert result.found, "Should find scaled and rotated crop"
    assert result.scale is not None
    # Scale should be close to 1/1.5 (since small is 1.5x bigger than the crop in big)
    expected_scale = 1.0 / scale
    assert abs(result.scale - expected_scale) / expected_scale < 0.1, \
        f"Scale error too large: expected {expected_scale}, got {result.scale}"
    assert result.confidence > 0.3


def test_locate_unrelated_images():
    """Test that unrelated images return found=False."""
    big = create_textured_image(800, 600, seed=100)
    small = create_textured_image(200, 150, seed=999)
    
    result = locate_subimage(big, small)
    
    assert not result.found, "Should not find match in unrelated images"
    assert result.confidence < 0.5


def test_corners_are_valid():
    """Test that returned corners form a valid quadrilateral inside the image."""
    big = create_textured_image(800, 600, seed=50)
    x0, y0, w, h = 100, 100, 200, 150
    small = big[y0:y0+h, x0:x0+w].copy()
    
    result = locate_subimage(big, small)
    
    assert result.found
    assert result.corners is not None
    assert len(result.corners) == 4
    
    # All corners should be inside the image
    for x, y in result.corners:
        assert 0 <= x < big.shape[1], f"Corner x={x} outside image width {big.shape[1]}"
        assert 0 <= y < big.shape[0], f"Corner y={y} outside image height {big.shape[0]}"


def test_result_to_dict():
    """Test LocateResult serialization to dict."""
    result = LocateResult(
        found=True,
        method="features",
        scale=1.5,
        x=100.5,
        y=200.3,
        corners=[(10.0, 20.0), (30.0, 40.0), (50.0, 60.0), (70.0, 80.0)],
        inliers=25,
        score=None,
        confidence=0.85,
        visualization_path=None
    )
    
    d = result.to_dict()
    
    assert d["found"] is True
    assert d["method"] == "features"
    assert d["scale"] == 1.5
    assert len(d["corners"]) == 4
    assert d["corners"][0] == [10.0, 20.0]


def test_template_matching_fallback():
    """Test that template matching works when features might fail."""
    # Create a simple gradient image (fewer features)
    big = np.zeros((600, 800, 3), dtype=np.uint8)
    for i in range(600):
        big[i, :] = [i * 255 // 600, 128, 255 - i * 255 // 600]
    
    # Add a distinctive pattern
    cv2.rectangle(big, (300, 200), (500, 400), (255, 255, 0), -1)
    cv2.circle(big, (400, 300), 50, (0, 255, 255), -1)
    
    # Extract and scale
    x0, y0, w, h = 280, 180, 240, 240
    crop = big[y0:y0+h, x0:x0+w].copy()
    small = cv2.resize(crop, None, fx=0.8, fy=0.8, interpolation=cv2.INTER_LINEAR)
    
    result = locate_subimage(big, small, min_scale=0.5, max_scale=1.5, scales=40)
    
    # Should find it (either method)
    assert result.found
    assert result.method in ["features", "template"]


def test_cli_integration(tmp_path):
    """Test CLI interface with temporary files."""
    from subimage_locator.cli import main
    
    # Create test images
    big = create_textured_image(600, 400, seed=123)
    x0, y0, w, h = 150, 100, 100, 80
    small = big[y0:y0+h, x0:x0+w].copy()
    
    big_path = tmp_path / "big.png"
    small_path = tmp_path / "small.png"
    out_path = tmp_path / "result.png"
    json_path = tmp_path / "result.json"
    
    cv2.imwrite(str(big_path), big)
    cv2.imwrite(str(small_path), small)
    
    # Run CLI
    exit_code = main([
        "--big", str(big_path),
        "--small", str(small_path),
        "--out", str(out_path),
        "--json", str(json_path)
    ])
    
    assert exit_code == 0, "CLI should return 0 when found"
    assert out_path.exists(), "Visualization should be created"
    assert json_path.exists(), "JSON output should be created"
    
    # Check JSON content
    import json
    result_data = json.loads(json_path.read_text())
    assert result_data["found"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
