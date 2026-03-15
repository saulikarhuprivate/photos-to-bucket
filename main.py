import os
import requests
from google.cloud import storage
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Konfiguraatio ympäristömuuttujista
ALBUM_ID = os.environ.get('ALBUM_ID')
BUCKET_NAME = os.environ.get('BUCKET_NAME')
# Huom: OAuth-tokenit tulisi hakea turvallisesti, esim. Secret Managerista
# Tässä esimerkissä oletetaan, että Refresh Token on saatavilla
REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN')
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')

def get_authenticated_session():
    """Luo ja päivittää OAuth2-istunnon Google Photos API:a varten."""
    creds = Credentials(
        None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )
    creds.refresh(Request())
    session = requests.Session()
    session.headers.update({'Authorization': f'Bearer {creds.token}'})
    return session

def upload_to_gcs(bucket, blob_name, content, content_type):
    """Tallentaa datan Google Cloud Storageen."""
    blob = bucket.blob(blob_name)
    blob.upload_from_string(content, content_type=content_type)
    print(f"Tallennettu: {blob_name}")

def sync_photos(request):
    """Cloud Functionin pääfunktio."""
    if not all([ALBUM_ID, BUCKET_NAME, REFRESH_TOKEN]):
        return "Ympäristömuuttujat puuttuvat", 500

    session = get_authenticated_session()
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)

    search_url = "https://photoslibrary.googleapis.com/v1/mediaItems:search"
    next_page_token = None
    processed_count = 0
    skipped_count = 0

    while True:
        # 1. Hae albumin mediatiedostot sivutuksella (pagination)
        payload = {"albumId": ALBUM_ID, "pageSize": 100}
        if next_page_token:
            payload["pageToken"] = next_page_token
        
        response = session.post(search_url, json=payload)
        if response.status_code != 200:
            return f"Virhe haettaessa albumia: {response.text}", 500

        data = response.json()
        items = data.get('mediaItems', [])

        for item in items:
            # Varmista, että kyseessä on kuva, ei video
            if 'photo' not in item.get('mediaMetadata', {}):
                continue

            base_url = item['baseUrl']
            filename = item['filename']
            item_id = item['id']

            web_blob_name = f"photos/full/{item_id}_{filename}"
            thumb_blob_name = f"photos/thumbs/{item_id}_{filename}"

            # 2. Tarkista onko kuva jo olemassa Cloud Storagessa (idempotenssi)
            if bucket.blob(web_blob_name).exists() and bucket.blob(thumb_blob_name).exists():
                skipped_count += 1
                continue

            # 3. Määritä koot
            # =w1920-h1080: Web-optimoitu (säilyttää kuvasuhteen)
            # =w300-h300-c: Thumbnail (neliöksi rajattu)
            web_url = f"{base_url}=w1920-h1080"
            thumb_url = f"{base_url}=w300-h300-c"
            mime_type = item.get('mimeType', 'image/jpeg')

            # 4. Lataa ja tallenna web-versio
            web_res = requests.get(web_url)
            if web_res.status_code == 200:
                upload_to_gcs(bucket, web_blob_name, web_res.content, mime_type)

            # 5. Lataa ja tallenna thumbnail
            thumb_res = requests.get(thumb_url)
            if thumb_res.status_code == 200:
                upload_to_gcs(bucket, thumb_blob_name, thumb_res.content, mime_type)

            processed_count += 1

        next_page_token = data.get('nextPageToken')
        if not next_page_token:
            break

    return f"Prosessoitu {processed_count} uutta kuvaa, ohitettu {skipped_count} jo olemassa olevaa.", 200
