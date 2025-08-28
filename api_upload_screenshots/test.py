# test_prepare_image.py
import os
from PIL import Image
from utils import prepare_image_for_upload  # ou utils.py selon où se trouve la fonction

# Remplacez ce chemin par une image existante sur votre machine
file_path = r"C:\Users\ouang\Desktop\img\17203485.png"

# Appeler la fonction pour créer le JPG temporaire
temp_jpg_path = prepare_image_for_upload(file_path)  # Variable renommée

# Vérifier que le fichier a bien été créé
if temp_jpg_path and os.path.exists(temp_jpg_path):  # Variable renommée
    print(f"Fichier temporaire créé avec succès : {temp_jpg_path}")  # Variable renommée
    
    # Tenter d'ouvrir l'image pour vérifier la qualité
    try:
        with Image.open(temp_jpg_path) as img:  # Variable renommée
            print(f"Image ouverte avec succès : format={img.format}, size={img.size}, mode={img.mode}")
            img.show()  # ouvre l'image dans le visualiseur par défaut
    except Exception as e:
        print(f"Impossible d'ouvrir l'image : {e}")
else:
    print("La fonction n'a pas créé de fichier JPG temporaire.")