import numpy as np
from PIL import Image

try:
    import face_recognition
    USE_FACE_RECOGNITION = True
except ImportError:
    USE_FACE_RECOGNITION = False


def compare_faces_fallback(image_path_1, image_path_2, threshold=0.85):
    """
    Fallback method using Pillow and NumPy.
    Resizes both images to 128x128, converts to grayscale, and computes
    normalized cross-correlation (NCC) of pixel intensities.
    Returns (is_match, similarity_score).
    """
    try:
        img1 = Image.open(image_path_1).convert('L').resize((128, 128))
        img2 = Image.open(image_path_2).convert('L').resize((128, 128))
        
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
