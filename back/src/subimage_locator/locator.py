"""Core subimage localization logic using feature matching and template matching."""

from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple
import numpy as np
import cv2


@dataclass
class LocateResult:
    """Result of subimage localization."""
    found: bool
    method: Optional[str]  # "features" | "template" | None
    scale: Optional[float]
    x: Optional[float]
    y: Optional[float]
    corners: Optional[List[Tuple[float, float]]]
    inliers: Optional[int]
    score: Optional[float]
    confidence: float
    visualization_path: Optional[str]

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        result = asdict(self)
        if result['corners'] is not None:
            result['corners'] = [[float(x), float(y)] for x, y in result['corners']]
        return result


def _try_sift():
    """Try to create SIFT detector, return None if unavailable."""
    try:
        return cv2.SIFT_create()
    except (cv2.error, AttributeError):
        return None


def _get_feature_detector():
    """Get best available feature detector (SIFT > AKAZE > ORB)."""
    sift = _try_sift()
    if sift is not None:
        return sift, "SIFT", cv2.NORM_L2
    
    try:
        return cv2.AKAZE_create(), "AKAZE", cv2.NORM_HAMMING
    except (cv2.error, AttributeError):
        pass
    
    return cv2.ORB_create(nfeatures=2000), "ORB", cv2.NORM_HAMMING


def _corners_inside_image(corners: np.ndarray, img_shape: Tuple[int, int]) -> bool:
    """Check if all corners are inside the image bounds."""
    h, w = img_shape[:2]
    for pt in corners:
        x, y = pt[0]
        if x < 0 or x >= w or y < 0 or y >= h:
            return False
    return True


def _locate_with_features(
    big_gray: np.ndarray,
    small_gray: np.ndarray,
    small_h: int,
    small_w: int
) -> Optional[LocateResult]:
    """
    Attempt localization using feature matching + RANSAC homography.
    
    Returns LocateResult if successful, None otherwise.
    """
    detector, detector_name, norm_type = _get_feature_detector()
    
    # Detect and compute
    kp1, desc1 = detector.detectAndCompute(big_gray, None)
    kp2, desc2 = detector.detectAndCompute(small_gray, None)
    
    if desc1 is None or desc2 is None or len(kp1) < 4 or len(kp2) < 4:
        return None
    
    # Match features
    if norm_type == cv2.NORM_L2:
        # FLANN for SIFT
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        matcher = cv2.FlannBasedMatcher(index_params, search_params)
    else:
        # BF for binary descriptors
        matcher = cv2.BFMatcher(norm_type, crossCheck=False)
    
    matches = matcher.knnMatch(desc2, desc1, k=2)
    
    # Lowe's ratio test
    good_matches = []
    for m_n in matches:
        if len(m_n) == 2:
            m, n = m_n
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)
    
    if len(good_matches) < 10:
        return None
    
    # Extract matched points
    src_pts = np.float32([kp2[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp1[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    
    # Find homography with RANSAC
    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    
    if H is None:
        return None
    
    inliers = int(mask.sum())
    if inliers < 10:
        return None
    
    # Project corners of small image
    corners_small = np.float32([[0, 0], [small_w, 0], [small_w, small_h], [0, small_h]]).reshape(-1, 1, 2)
    corners_big = cv2.perspectiveTransform(corners_small, H)
    
    # Check if corners are inside big image
    if not _corners_inside_image(corners_big, big_gray.shape):
        return None
    
    # Fit similarity transform on inliers for clean scale and translation
    inlier_mask = mask.ravel().astype(bool)
    src_inliers = src_pts[inlier_mask]
    dst_inliers = dst_pts[inlier_mask]
    
    # Estimate partial affine (similarity: scale, rotation, translation)
    M, _ = cv2.estimateAffinePartial2D(src_inliers, dst_inliers)
    
    if M is None:
        # Fallback to homography-based scale estimation
        scale = np.sqrt(np.abs(np.linalg.det(H[:2, :2])))
        top_left = corners_big[0][0]
        x, y = float(top_left[0]), float(top_left[1])
    else:
        # Extract scale from similarity transform
        scale = np.sqrt(M[0, 0]**2 + M[0, 1]**2)
        # Transform top-left corner
        top_left_small = np.array([[[0, 0]]], dtype=np.float32)
        top_left_big = cv2.transform(top_left_small, M)
        x, y = float(top_left_big[0, 0, 0]), float(top_left_big[0, 0, 1])
    
    # Confidence based on inlier ratio
    confidence = min(1.0, inliers / max(len(good_matches), 1))
    
    corners_list = [(float(pt[0][0]), float(pt[0][1])) for pt in corners_big]
    
    return LocateResult(
        found=True,
        method="features",
        scale=float(scale),
        x=x,
        y=y,
        corners=corners_list,
        inliers=inliers,
        score=None,
        confidence=confidence,
        visualization_path=None
    )


def _locate_with_template(
    big_gray: np.ndarray,
    small_gray: np.ndarray,
    small_h: int,
    small_w: int,
    min_scale: float,
    max_scale: float,
    scales: int,
    threshold: float = 0.5
) -> Optional[LocateResult]:
    """
    Attempt localization using multi-scale template matching.
    
    Returns LocateResult if successful, None otherwise.
    """
    best_score = -1
    best_scale = None
    best_x = None
    best_y = None
    
    # Log-spaced scales
    scale_range = np.logspace(np.log10(min_scale), np.log10(max_scale), scales)
    
    for scale in scale_range:
        new_w = int(small_w * scale)
        new_h = int(small_h * scale)
        
        # Skip if scaled template is larger than big image
        if new_w > big_gray.shape[1] or new_h > big_gray.shape[0]:
            continue
        
        # Resize template
        resized = cv2.resize(small_gray, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Template matching with ZNCC
        result = cv2.matchTemplate(big_gray, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        if max_val > best_score:
            best_score = max_val
            best_scale = scale
            best_x, best_y = max_loc
    
    if best_score < threshold:
        return None
    
    # Compute corners
    w_scaled = small_w * best_scale
    h_scaled = small_h * best_scale
    corners = [
        (float(best_x), float(best_y)),
        (float(best_x + w_scaled), float(best_y)),
        (float(best_x + w_scaled), float(best_y + h_scaled)),
        (float(best_x), float(best_y + h_scaled))
    ]
    
    confidence = float(best_score)
    
    return LocateResult(
        found=True,
        method="template",
        scale=float(best_scale),
        x=float(best_x),
        y=float(best_y),
        corners=corners,
        inliers=None,
        score=float(best_score),
        confidence=confidence,
        visualization_path=None
    )

#el sistema convierte ambas imágenes a gris, intenta localizar small 
# dentro de big primero por emparejado de características 
# (SIFT/AKAZE/ORB + RANSAC + ajuste de similaridad) y,
# si eso falla, hace un barrido multi-escala con template matching (ZNCC).
# Devuelve un objeto LocateResult con found, method, scale, x,y, corners, inliers/score y confidence.

def locate_subimage(
    big_bgr: np.ndarray,
    small_bgr: np.ndarray,
    min_scale: float = 0.3,
    max_scale: float = 3.0,
    scales: int = 60
) -> LocateResult:
    """
    Locate a scaled crop of small_bgr within big_bgr.
    
    Tries feature matching first (robust to rotation/perspective), then falls back
    to multi-scale template matching if features fail.
    
    Args:
        big_bgr: Large image (BGR format from cv2.imread)
        small_bgr: Small image to locate (BGR format)
        min_scale: Minimum scale factor to search
        max_scale: Maximum scale factor to search
        scales: Number of scales to try in template matching
    
    Returns:
        LocateResult with found status, method, scale, position, corners, and confidence
    """
    # Convert to grayscale
    big_gray = cv2.cvtColor(big_bgr, cv2.COLOR_BGR2GRAY)
    small_gray = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2GRAY)
    
    small_h, small_w = small_gray.shape[:2]
    
    # Try feature-based matching first (more robust)
    result = _locate_with_features(big_gray, small_gray, small_h, small_w)
    if result is not None:
        return result
    
    # Fall back to template matching
    result = _locate_with_template(
        big_gray, small_gray, small_h, small_w,
        min_scale, max_scale, scales
    )
    if result is not None:
        return result
    
    # No match found
    return LocateResult(
        found=False,
        method=None,
        scale=None,
        x=None,
        y=None,
        corners=None,
        inliers=None,
        score=None,
        confidence=0.0,
        visualization_path=None
    )
