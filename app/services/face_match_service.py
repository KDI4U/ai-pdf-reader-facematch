import os
import io
import urllib.request
import logging
from pathlib import Path
from typing import Optional, Tuple, Any

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.schemas.face_match_schema import FaceMatchResponse, FaceMatchDetails

logger = logging.getLogger(__name__)

# Model download URLs (official OpenCV Zoo)
YUNET_MODEL_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SFACE_MODEL_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

YUNET_FILENAME = "face_detection_yunet_2023mar.onnx"
SFACE_FILENAME = "face_recognition_sface_2021dec.onnx"

DEFAULT_FACE_MATCH_THRESHOLD = float(os.getenv("DEFAULT_FACE_MATCH_THRESHOLD", "0.38"))


class FaceMatcher:
    _instance = None

    def __init__(self):
        self.yunet_path = self._resolve_model_path(YUNET_FILENAME, YUNET_MODEL_URL)
        self.sface_path = self._resolve_model_path(SFACE_FILENAME, SFACE_MODEL_URL)

        # Initialize recognizer
        self.recognizer = cv2.FaceRecognizerSF.create(
            model=str(self.sface_path),
            config=""
        )

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = FaceMatcher()
        return cls._instance

    def _resolve_model_path(self, filename: str, download_url: str) -> Path:
        """Find the model on disk or download it if missing."""
        current_file_dir = Path(__file__).resolve().parent
        candidates = [
            current_file_dir.parent.parent / "models" / filename,
            current_file_dir.parent / "models_weights" / filename,
            Path(os.getcwd()) / "models" / filename,
            current_file_dir.parent / "models" / filename,
        ]

        for p in candidates:
            if p.exists() and p.stat().st_size > 1000:
                return p

        # Default save path: root / models
        target_dir = current_file_dir.parent.parent / "models"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / filename

        logger.info(f"Downloading model {filename} to {target_file}...")
        try:
            req = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(target_file, "wb") as f:
                f.write(resp.read())
            logger.info(f"Model {filename} downloaded successfully.")
        except Exception as e:
            logger.error(f"Failed to download model {filename}: {e}")
            raise RuntimeError(f"Face model {filename} could not be found or downloaded: {e}")

        return target_file

    def get_detector(self, width: int, height: int, score_threshold: float = 0.6) -> Any:
        return cv2.FaceDetectorYN.create(
            model=str(self.yunet_path),
            config="",
            input_size=(width, height),
            score_threshold=score_threshold,
            nms_threshold=0.3,
            top_k=5000
        )

    def decode_image_bytes(self, image_bytes: bytes) -> np.ndarray:
        """
        Convert raw image bytes into a BGR OpenCV numpy array.
        Handles mobile EXIF rotation so rotated selfies are corrected.
        """
        try:
            pil_img = Image.open(io.BytesIO(image_bytes))
            # Automatically apply EXIF orientation
            pil_img = ImageOps.exif_transpose(pil_img)
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
            # Convert RGB (PIL) to BGR (OpenCV)
            rgb_arr = np.array(pil_img)
            bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
            return bgr_arr
        except Exception:
            # Fallback to direct OpenCV decode
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode the provided image bytes. Please ensure it is a valid JPG/PNG.")
            return img

    def enhance_illumination(self, img: np.ndarray) -> np.ndarray:
        """Apply CLAHE to eliminate harsh shadows (under cap) and glare (on glasses)."""
        try:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l)
            return cv2.cvtColor(cv2.merge((l_enhanced, a, b)), cv2.COLOR_LAB2BGR)
        except Exception:
            return img

    def extract_face_feature(self, img: np.ndarray) -> Tuple[Optional[np.ndarray], bool]:
        """
        Intelligent Multi-Pass Face Detection:
        Robust to real-world variations: spectacles/glasses, caps, facial hair, and shadows.
        - Pass 1: Standard detection (threshold 0.55).
        - Pass 2: Occlusion-tolerant detection (threshold 0.35) for glasses / cap.
        - Pass 3: CLAHE shadow-removal & illumination enhancement.
        - Pass 4: Multi-scale pyramid (resize 0.8x / 1.25x).
        """
        h, w = img.shape[:2]
        if h == 0 or w == 0:
            return None, False

        def _get_best_face(faces_tuple):
            if faces_tuple is None or faces_tuple[1] is None or len(faces_tuple[1]) == 0:
                return None
            detected = faces_tuple[1]
            best = None
            max_area = -1
            for face in detected:
                area = face[2] * face[3]
                if area > max_area:
                    max_area = area
                    best = face
            return best

        # Pass 1: Standard detection
        detector = self.get_detector(w, h, score_threshold=0.55)
        best_face = _get_best_face(detector.detect(img))

        # Pass 2: Occlusion-tolerant detection (glasses / cap)
        if best_face is None:
            detector_loose = self.get_detector(w, h, score_threshold=0.35)
            best_face = _get_best_face(detector_loose.detect(img))

        # Pass 3: Illumination enhancement (removes cap brim shadows & glass reflections)
        if best_face is None:
            enhanced_img = self.enhance_illumination(img)
            detector_enh = self.get_detector(w, h, score_threshold=0.35)
            best_face = _get_best_face(detector_enh.detect(enhanced_img))
            if best_face is not None:
                img = enhanced_img

        # Pass 4: Multi-scale attempt (if face is slightly too far or too close)
        if best_face is None and min(w, h) >= 200:
            for scale in [0.8, 1.25]:
                nw, nh = int(w * scale), int(h * scale)
                if nw > 50 and nh > 50:
                    scaled_img = cv2.resize(img, (nw, nh))
                    d_scaled = self.get_detector(nw, nh, score_threshold=0.35)
                    scaled_face = _get_best_face(d_scaled.detect(scaled_img))
                    if scaled_face is not None:
                        best_face = scaled_face.copy()
                        best_face[:14] = best_face[:14] / scale
                        break

        if best_face is None:
            return None, False

        # Align and crop face using OpenCV SFace
        aligned_face = self.recognizer.alignCrop(img, best_face)
        feature = self.recognizer.feature(aligned_face)
        return feature, True

    def compare_features(
        self,
        feature1: np.ndarray,
        feature2: np.ndarray,
        threshold: float
    ) -> Tuple[bool, float, float, float]:
        """
        Compare two 128-d face features.
        Returns: (matched, cosine_score, match_percentage, l2_distance)
        """
        cosine_score = float(self.recognizer.match(feature1, feature2, cv2.FaceRecognizerSF_FR_COSINE))
        l2_dist = float(self.recognizer.match(feature1, feature2, cv2.FaceRecognizerSF_FR_NORM_L2))

        # Clamp cosine score between 0.0 and 1.0 for percentage calculation
        normalized_score = max(0.0, min(1.0, cosine_score))
        match_percentage = round(normalized_score * 100, 2)

        matched = cosine_score >= threshold
        return matched, cosine_score, match_percentage, l2_dist


def classify_confidence(cosine_score: float, threshold: float) -> Tuple[str, Optional[str]]:
    """Determine confidence tier and variation note (glasses, cap, lighting)."""
    if cosine_score >= 0.65:
        return "HIGH", "Exact facial match verified"
    elif cosine_score >= threshold:
        return "MEDIUM", "Match verified with variations (e.g. spectacles/glasses, cap, facial hair, or lighting)"
    else:
        return "LOW", "No match (features diverge beyond threshold)"


def parse_threshold(threshold: Any) -> float:
    """Safely extracts a float threshold value or falls back to default."""
    if threshold is not None and isinstance(threshold, (int, float)):
        return float(threshold) if float(threshold) > 0 else DEFAULT_FACE_MATCH_THRESHOLD
    if isinstance(threshold, str):
        try:
            val = float(threshold.strip())
            return val if val > 0 else DEFAULT_FACE_MATCH_THRESHOLD
        except (ValueError, TypeError):
            pass
    return DEFAULT_FACE_MATCH_THRESHOLD


def compare_two_images(
    image1_bytes: bytes,
    image2_bytes: bytes,
    user_id: Optional[str] = None,
    threshold: Optional[Any] = None
) -> FaceMatchResponse:
    """Compare any two images directly with optional user_id."""
    match_threshold = parse_threshold(threshold)
    matcher = FaceMatcher.get_instance()

    clean_user_id = str(user_id).strip() if user_id else None
    if clean_user_id and clean_user_id.lower() in ("", "string", "none", "null"):
        clean_user_id = None

    img1 = matcher.decode_image_bytes(image1_bytes)
    img2 = matcher.decode_image_bytes(image2_bytes)

    feat1, found1 = matcher.extract_face_feature(img1)
    feat2, found2 = matcher.extract_face_feature(img2)

    details = FaceMatchDetails(
        uploaded_face_detected=found1,
        profile_face_detected=found2,
        cosine_similarity=None,
        l2_distance=None,
        threshold_used=match_threshold
    )

    if not found1 or not found2:
        msg = "No face detected in image 1" if not found1 else "No face detected in image 2"
        return FaceMatchResponse(
            status="unsuccess",
            matched=False,
            user_id=clean_user_id,
            employee_code=None,
            similarity_score=0.0,
            match_percentage=0.0,
            threshold=match_threshold,
            confidence_level="LOW",
            variation_note=None,
            message=msg,
            profile_image_url=None,
            details=details
        )

    matched, cosine_score, match_percentage, l2_dist = matcher.compare_features(
        feat1, feat2, match_threshold
    )
    details.cosine_similarity = round(cosine_score, 4)
    details.l2_distance = round(l2_dist, 4)
    conf_level, variation_note = classify_confidence(cosine_score, match_threshold)

    return FaceMatchResponse(
        status="success" if matched else "unsuccess",
        matched=matched,
        user_id=clean_user_id,
        employee_code=None,
        similarity_score=round(max(0.0, cosine_score), 4),
        match_percentage=match_percentage,
        threshold=match_threshold,
        confidence_level=conf_level,
        variation_note=variation_note,
        message=f"Comparison completed: {'Match' if matched else 'No match'} ({match_percentage}%).",
        profile_image_url=None,
        details=details
    )
