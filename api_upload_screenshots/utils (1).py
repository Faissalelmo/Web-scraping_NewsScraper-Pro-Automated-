# utils.py
import os
from PIL import Image

# Récupérer tous les fichiers images
def get_image_files(folder_path):
    files = [f for f in os.listdir(folder_path) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    files.sort()
    return [os.path.join(folder_path, f) for f in files]

# Lire les article_id déjà uploadés depuis un log existant
def get_uploaded_article_ids(log_file):
    uploaded = set()
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            for line in f:
                try:
                    article_id = line.strip().split(" - ")[0]
                    uploaded.add(article_id)
                except:
                    continue
    return uploaded



#   rgb_img.save(temp_jpg_path, quality=100, subsampling=0)

def prepare_image_for_upload(file_path, max_size=(3000, 3000)):
    """
    Prépare une image pour l'upload en JPEG baseline.
    """
    base, _ = os.path.splitext(file_path)
    temp_jpg_path = base + ".jpg"  # pas .temp.jpg

    try:
        with Image.open(file_path) as img:
            rgb_img = img.convert("RGB")
            if img.width > max_size[0] or img.height > max_size[1]:
                rgb_img.thumbnail(max_size, Image.Resampling.LANCZOS)
            rgb_img.save(
                temp_jpg_path,
                format="JPEG",
                quality=92,
                optimize=True,
                progressive=False  # baseline JPEG
            )
            print(f"✅ Fichier optimisé : {temp_jpg_path} "
                  f"(taille {os.path.getsize(temp_jpg_path)/1024:.1f} Ko)")
            return temp_jpg_path

    except Exception as e:
        print(f"❌ Erreur lors de la préparation de l'image {file_path}: {e}")
        return None
