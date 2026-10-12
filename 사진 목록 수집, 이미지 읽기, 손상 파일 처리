import os
from PIL import Image

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def check_image(file_path):
    try:
        if os.path.getsize(file_path) == 0:
            return False, "0바이트"
    except OSError:
        return False, "접근 실패"

    try:
        with Image.open(file_path) as img:
            img.verify()
        with Image.open(file_path) as img:
            img.load()
            img.convert("RGB")
        return True, "정상"
    except Exception as e:
        return False, str(e)


def collect_images(folder_path):
    image_paths = []
    failed_files = []

    if not os.path.exists(folder_path):
        return image_paths, failed_files

    for root, _, files in os.walk(folder_path):
        for file_name in files:
            ext = os.path.splitext(file_name)[1].lower()
            if ext in IMAGE_EXTENSIONS:
                file_path = os.path.abspath(os.path.join(root, file_name))
                is_valid, reason = check_image(file_path)
                if is_valid:
                    image_paths.append(file_path)
                else:
                    failed_files.append({"path": file_path, "reason": reason})

    return image_paths, failed_files


def load_image(file_path):
    try:
        return Image.open(file_path).convert("RGB")
    except Exception:
        return None
