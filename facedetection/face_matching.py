import numpy as np
from PIL import Image

# Primary matcher: InsightFace (ArcFace/buffalo_l). dlib and pixel-NCC both
# fail to separate similar-looking faces (proven on real data: dlib scored two
# different people at 0.24 while a genuine pair scored 0.57 — impostor closer
# than genuine). InsightFace gives clean separation (0.9 same / 0.18 different).
# The dlib/NCC path below is kept ONLY as a degraded fallback if InsightFace
# can't load, so a library hiccup doesn't hard-crash check-in.
# ponytail: cosine >= FACE_MATCH_THRESHOLD == same person. 0.4 gives a wide
# margin over impostors (~0.2) without false-rejecting genuine users (~0.5-0.9);
# raise toward 0.5 if impostors ever slip through.
FACE_MATCH_THRESHOLD = 0.4

_INSIGHT_APP = None
_INSIGHT_TRIED = False


def _get_insight_app():
    """Lazily build a single FaceAnalysis app per process (model load is slow
    and ~300MB, so it must be reused, not rebuilt per request)."""
    global _INSIGHT_APP, _INSIGHT_TRIED
    if _INSIGHT_TRIED:
        return _INSIGHT_APP
    _INSIGHT_TRIED = True
    try:
        from insightface.app import FaceAnalysis

        app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        app.prepare(ctx_id=-1, det_size=(640, 640))
        _INSIGHT_APP = app
    except Exception as e:
        print(f"InsightFace unavailable, falling back to dlib/NCC: {e}")
        _INSIGHT_APP = None
    return _INSIGHT_APP


def _insight_embedding(image_path):
    """Largest-face normalized embedding, or None if no face / lib unavailable."""
    app = _get_insight_app()
    if app is None:
        return None
    import cv2

    img = cv2.imread(image_path)
    if img is None:
        return None
    faces = app.get(img)
    if not faces:
        return None
    # largest face (closest to camera)
    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return face.normed_embedding


try:
    import face_recognition
    USE_FACE_RECOGNITION = True
except ImportError:
    USE_FACE_RECOGNITION = False

try:
    import cv2
    _FACE_CASCADE = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
except ImportError:
    _FACE_CASCADE = None


def _crop_to_face(image_path):
    """Detect the largest face with OpenCV's Haar cascade and crop to it.
    Returns (image, face_found). If OpenCV is unavailable, face_found is
    always True (no detection capability — can't tell), so callers only treat
    face_found=False as a hard reject when OpenCV IS available and genuinely
    found nothing (e.g. a photo of a wall)."""
    img = Image.open(image_path).convert("L")
    if _FACE_CASCADE is None:
        return img, True
    arr = np.array(img)
    faces = _FACE_CASCADE.detectMultiScale(arr, scaleFactor=1.1, minNeighbors=5)
    if len(faces) == 0:
        return img, False
    # largest detected face (closest to camera)
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return img.crop((x, y, x + w, y + h)), True


def has_face(image_path):
    """True if a face is detectable in the image (or detection is unavailable,
    in which case we can't rule it out and let comparison decide)."""
    app = _get_insight_app()
    if app is not None:
        try:
            import cv2

            img = cv2.imread(image_path)
            return img is not None and len(app.get(img)) > 0
        except Exception as e:
            print(f"InsightFace detection error, falling back: {e}")
    try:
        _, found = _crop_to_face(image_path)
        return found
    except Exception as e:
        print(f"Error in face detection: {e}")
        return True


def compare_faces_fallback(image_path_1, image_path_2, threshold=0.6):
    """
    Fallback method using OpenCV face-crop + Pillow/NumPy normalized
    cross-correlation (NCC) of pixel intensities on just the face region.
    Returns (is_match, similarity_score).
    """
    try:
        cropped1, found1 = _crop_to_face(image_path_1)
        cropped2, found2 = _crop_to_face(image_path_2)
        if not found1 or not found2:
            # No face detected in one or both images (e.g. a wall) — reject
            # outright rather than falling back to a whole-photo comparison.
            return False, 0.0
        img1 = cropped1.resize((128, 128))
        img2 = cropped2.resize((128, 128))

        arr1 = np.array(img1, dtype=np.float32)
        arr2 = np.array(img2, dtype=np.float32)

        # Zero-mean normalization
        mean1 = np.mean(arr1)
        mean2 = np.mean(arr2)

        arr1 -= mean1
        arr2 -= mean2

        std1 = np.std(arr1)
        std2 = np.std(arr2)

        if std1 == 0 or std2 == 0:
            return False, 0.0

        ncc = np.mean(arr1 * arr2) / (std1 * std2)
        # Map NCC from [-1.0, 1.0] range to [0.0, 1.0] range
        similarity = float((ncc + 1.0) / 2.0)

        # ponytail: pixel-correlation on a Haar-cropped face is a rough proxy,
        # not real face embeddings — upgrade to `face_recognition`/dlib (needs
        # cmake to build) if impostor false-accepts become a problem.
        return similarity >= threshold, similarity
    except Exception as e:
        print(f"Error in fallback face matching: {e}")
        return False, 0.0


def compare_faces(image_path_1, image_path_2):
    """
    Face matching. Primary path: InsightFace ArcFace embeddings + cosine
    similarity (the only method that reliably separates similar-looking
    faces). Falls back to dlib, then pixel-NCC, only if InsightFace is
    unavailable. Returns (is_match, similarity_score).
    """
    emb1 = _insight_embedding(image_path_1)
    emb2 = _insight_embedding(image_path_2)
    if emb1 is not None and emb2 is not None:
        similarity = float(np.dot(emb1, emb2))  # both are L2-normalized
        return similarity >= FACE_MATCH_THRESHOLD, similarity
    if emb1 is not None or emb2 is not None:
        # InsightFace loaded and found a face in one image but not the other
        # (e.g. a wall / no face) — that's a genuine non-match, don't fall
        # through to the weaker matchers and risk a false accept.
        if _get_insight_app() is not None:
            return False, 0.0

    if USE_FACE_RECOGNITION:
        try:
            img1 = face_recognition.load_image_file(image_path_1)
            img2 = face_recognition.load_image_file(image_path_2)
            
            enc1s = face_recognition.face_encodings(img1)
            enc2s = face_recognition.face_encodings(img2)
            
            if not enc1s or not enc2s:
                # No faces detected in one or both images
                return False, 0.0
                
            # Compare the first face found in each image
            results = face_recognition.compare_faces([enc1s[0]], enc2s[0], tolerance=0.6)
            distance = face_recognition.face_distance([enc1s[0]], enc2s[0])[0]
            similarity = float(1.0 - distance)
            return bool(results[0]), similarity
        except Exception as e:
            print(f"Error in face_recognition matching, calling fallback: {e}")
            
    # Fallback to structural/intensity correlation check
    return compare_faces_fallback(image_path_1, image_path_2)
