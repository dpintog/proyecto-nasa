"""Command-line interface for subimage locator."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from .locator import locate_subimage, LocateResult


def draw_visualization(
    big_bgr: np.ndarray,
    result: LocateResult,
    output_path: Path
) -> None:
    """
    Draw the located region on the big image and save to output_path.
    
    Args:
        big_bgr: The large image
        result: Localization result
        output_path: Where to save the visualization PNG
    """
    vis = big_bgr.copy()
    
    if result.found and result.corners is not None:
        # Draw the quadrilateral
        corners_int = np.array(result.corners, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(vis, [corners_int], isClosed=True, color=(0, 255, 0), thickness=3)
        
        # Mark top-left corner
        if result.x is not None and result.y is not None:
            center = (int(result.x), int(result.y))
            cv2.circle(vis, center, 8, (0, 0, 255), -1)
            cv2.circle(vis, center, 12, (255, 255, 255), 2)
        
        # Add text with method and confidence
        text = f"{result.method} | conf: {result.confidence:.2f}"
        cv2.putText(vis, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 255, 0), 2, cv2.LINE_AA)
    else:
        # Not found
        cv2.putText(vis, "NOT FOUND", (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, (0, 0, 255), 2, cv2.LINE_AA)
    
    cv2.imwrite(str(output_path), vis)


def main(argv: Optional[list] = None) -> int:
    """
    Main CLI entry point.
    
    Returns:
        0 if found, 2 if not found, 1 on error
    """
    parser = argparse.ArgumentParser(
        description="Locate a scaled crop within a larger image using feature matching or template matching."
    )
    parser.add_argument("--big", type=Path, required=True,
                        help="Path to the large image")
    parser.add_argument("--small", type=Path, required=True,
                        help="Path to the small (crop) image")
    parser.add_argument("--out", type=Path, default=None,
                        help="Path to save visualization PNG (optional)")
    parser.add_argument("--json", type=Path, default=None, dest="json_path",
                        help="Path to save JSON result (if omitted, prints to stdout)")
    parser.add_argument("--min-scale", type=float, default=0.3,
                        help="Minimum scale factor for template matching (default: 0.3)")
    parser.add_argument("--max-scale", type=float, default=3.0,
                        help="Maximum scale factor for template matching (default: 3.0)")
    parser.add_argument("--scales", type=int, default=60,
                        help="Number of scales to try in template matching (default: 60)")
    parser.add_argument("--max-dim", type=int, default=None,
                        help="Max dimension to downscale big image before processing (optional)")
    
    args = parser.parse_args(argv)
    
    # Validate inputs
    if not args.big.exists():
        print(f"Error: Big image not found: {args.big}", file=sys.stderr)
        return 1
    
    if not args.small.exists():
        print(f"Error: Small image not found: {args.small}", file=sys.stderr)
        return 1
    
    # Load images
    try:
        big_bgr = cv2.imread(str(args.big), cv2.IMREAD_COLOR)
        small_bgr = cv2.imread(str(args.small), cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"Error loading images: {e}", file=sys.stderr)
        return 1
    
    if big_bgr is None:
        print(f"Error: Could not read big image: {args.big}", file=sys.stderr)
        return 1
    
    if small_bgr is None:
        print(f"Error: Could not read small image: {args.small}", file=sys.stderr)
        return 1
    
    # Downscale if requested
    scale_factor = 1.0
    if args.max_dim is not None:
        h, w = big_bgr.shape[:2]
        max_side = max(h, w)
        if max_side > args.max_dim:
            scale_factor = args.max_dim / max_side
            new_w = int(w * scale_factor)
            new_h = int(h * scale_factor)
            big_bgr = cv2.resize(big_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Locate subimage
    result = locate_subimage(
        big_bgr, small_bgr,
        min_scale=args.min_scale,
        max_scale=args.max_scale,
        scales=args.scales
    )
    
    # Scale results back if downscaled
    if scale_factor != 1.0 and result.found:
        inv_scale = 1.0 / scale_factor
        if result.x is not None:
            result.x *= inv_scale
        if result.y is not None:
            result.y *= inv_scale
        if result.corners is not None:
            result.corners = [(x * inv_scale, y * inv_scale) for x, y in result.corners]
        # Note: scale factor in result is relative to small image, not affected by downscaling
    
    # Visualization
    if args.out is not None:
        # Re-load full-res image if we downscaled
        if scale_factor != 1.0:
            big_bgr_vis = cv2.imread(str(args.big), cv2.IMREAD_COLOR)
        else:
            big_bgr_vis = big_bgr
        
        draw_visualization(big_bgr_vis, result, args.out)
        result.visualization_path = str(args.out)
    
    # Output JSON
    result_dict = result.to_dict()
    json_str = json.dumps(result_dict, indent=2)
    
    if args.json_path is not None:
        args.json_path.write_text(json_str, encoding="utf-8")
    else:
        print(json_str)
    
    # Exit code
    return 0 if result.found else 2


if __name__ == "__main__":
    sys.exit(main())
