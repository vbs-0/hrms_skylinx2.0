import numpy as np
from PIL import Image

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
    Active face matching using face_recognition package (if installed)
    with a Pillow + NumPy normalized correlation fallback.
    """
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
