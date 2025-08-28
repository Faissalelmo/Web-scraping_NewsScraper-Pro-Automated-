"""
Script pour convertir tous les fichiers PNG en JPG dans un dossier
Avec compression et préservation de la qualité
"""

from PIL import Image
import os
from pathlib import Path
import argparse
from typing import List, Tuple
import time

def get_size_format(b: float) -> str:
    """Convertit les bytes en format lisible (KB, MB, etc)"""
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if b < factor:
            return f"{b:.2f}{unit}B"
        b /= factor
    return f"{b:.2f}PB"  # Pour les très grands fichiers

def convert_png_to_jpg(input_dir: str, quality: int = 95, remove_original: bool = True) -> Tuple[int, int, List[str]]:
    """
    Convertit tous les fichiers PNG en JPG dans le dossier spécifié.
    
    Args:
        input_dir: Chemin du dossier contenant les PNG
        quality: Qualité de compression JPG (1-100)
        remove_original: Si True, supprime les fichiers PNG d'origine
    
    Returns:
        Tuple contenant (nb fichiers convertis, nb erreurs, liste des erreurs)
    """
    # Assurer que le dossier existe
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Le dossier {input_dir} n'existe pas!")
        return 0, 0, []

    # Compter les fichiers traités
    converted = 0
    errors = 0

    # Parcourir tous les fichiers PNG
    for png_file in input_path.glob("**/*.png"):
        try:
            # Ouvrir l'image PNG
            with Image.open(png_file) as img:
                # Convertir en RGB (nécessaire pour JPG)
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                # Créer le nouveau nom de fichier
                jpg_file = png_file.with_suffix('.jpg')
                
                # Sauvegarder en JPG avec une bonne qualité
                img.save(jpg_file, 'JPEG', quality=95)
                
                # Supprimer le fichier PNG original
                png_file.unlink()
                
                converted += 1
                print(f"Converti: {png_file.name} -> {jpg_file.name}")
                
        except Exception as e:
            print(f"Erreur lors de la conversion de {png_file.name}: {str(e)}")
            errors += 1

    # Afficher le résumé
    print(f"\nConversion terminée!")
    print(f"✓ {converted} fichiers convertis")
    if errors > 0:
        print(f"✗ {errors} erreurs rencontrées")

if __name__ == "__main__":
    # Dossiers à traiter
    dirs_to_process = [
        "data/csv_screenshots/content_page"
    ]
    
    for directory in dirs_to_process:
        print(f"\nTraitement du dossier: {directory}")
        convert_png_to_jpg(directory)
