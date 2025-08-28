import os
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import API_URL, FOLDER_PATH, USER_ID, LOG_FILE, THREADS,FOLDER_PATH_PROCESSED
from utils import get_image_files, get_uploaded_article_ids, prepare_image_for_upload

def log_attempt(article_id, file_path, status_msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{article_id} - {file_path} - {status_msg}\n")

def is_upload_successful(api_response_json, http_status):
    """
    Vérifie si l'upload a réussi selon différents formats de réponse JSON.
    """
    if http_status != 200:
        return False
    if isinstance(api_response_json, dict):
        # Cas clé "success"
        if "success" in api_response_json:
            return True
        # Cas clé "code" avec valeur "success"
        if api_response_json.get("code", "").lower() == "success":
            return True
    return False

def upload_file(file_path):
    article_id = os.path.splitext(os.path.basename(file_path))[0]
    file_to_send_path = None
    original_file_is_temp = False

    try:
        # Préparation de l'image
        file_to_send_path = prepare_image_for_upload(file_path)
        if file_to_send_path is None:
            log_attempt(article_id, file_path, "Échec de la préparation de l'image en JPG.")
            return
        original_file_is_temp = True

        # Envoi du fichier
        with open(file_to_send_path, "rb") as f:
            files = {"file": (os.path.basename(file_to_send_path), f, "image/jpeg")}
            data = {"article_id": article_id, "user_id": str(USER_ID)}
            response = requests.post(API_URL, files=files, data=data, timeout=120)

        # Lecture de la réponse
        try:
            api_response_json = response.json()
        except Exception:
            api_response_json = None

        # Déterminer si l'upload est réussi
        success = is_upload_successful(api_response_json, response.status_code)

        # Préparer le message pour le log
        if api_response_json:
            status_msg = f"API Response: {api_response_json}"
        else:
            status_msg = f"API Response: {response.text}"

        if success:
            log_attempt(article_id, file_path, f"Uploaded successfully. {status_msg}")
        else:
            log_attempt(article_id, file_path, f"Upload failed. Status Code: {response.status_code}. {status_msg}")

        # Affichage console pour debug
        print(f"\n=== Article {article_id} ===")
        print("HTTP Status Code:", response.status_code)
        print("Success:", success)
        print("Response:", status_msg)
        print("============================")

    except requests.exceptions.Timeout:
        log_attempt(article_id, file_path, "HTTPConnectionPool: Read timed out. (timeout=120)")
    except Exception as e:
        log_attempt(article_id, file_path, f"Erreur inattendue: {str(e)}")
    finally:
        if original_file_is_temp and file_to_send_path and os.path.exists(file_to_send_path):
            try:
                # move the file to a backup location
                os.makedirs(FOLDER_PATH_PROCESSED, exist_ok=True)
                file_to_send_path_processed = os.path.join(FOLDER_PATH_PROCESSED, os.path.basename(file_to_send_path))
                os.replace(file_to_send_path, file_to_send_path_processed)
                
                

            except:
                pass

def main():
    image_files = get_image_files(FOLDER_PATH)
    # uploaded_ids = get_uploaded_article_ids(LOG_FILE)
    # get processed files ids from name of files in FOLDER_PATH_PROCESSED
    processed_files = get_image_files(FOLDER_PATH_PROCESSED)
    uploaded_ids = [os.path.splitext(os.path.basename(f))[0] for f in processed_files]

    files_to_upload = [f for f in image_files if os.path.splitext(os.path.basename(f))[0] not in uploaded_ids]
    print(f"{len(files_to_upload)} fichiers à uploader.")
    
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = [executor.submit(upload_file, f) for f in files_to_upload]
        for _ in tqdm(as_completed(futures), total=len(futures), desc="Uploading"):
            pass
    
    print(f"Upload terminé. Vérifiez {LOG_FILE} pour les erreurs.")

if __name__ == "__main__":
    main()
