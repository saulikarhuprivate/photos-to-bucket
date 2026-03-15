# photos-to-bucket

Copies photos from a specific Google Photos album to a Google Cloud Storage bucket used for web publishing. It automatically creates web-optimized versions and square thumbnails of the images.

## Features

- **Google Photos Integration**: Fetches photos from a specified Google Photos album using the Google Photos Library API.
- **Image Optimization**: Automatically generates:
  - Web-optimized full-size images (max 1920x1080, preserving aspect ratio)
  - Square thumbnails (300x300, cropped)
- **Idempotent Sync**: Checks if photos already exist in the target Cloud Storage bucket (`photos/full/` and `photos/thumbs/`) before processing, preventing duplicate work.
- **Serverless Architecture**: Designed to run as a 2nd Gen Google Cloud Function, triggered via HTTP.
- **Automated Deployment**: Includes a `cloudbuild.yaml` for deployment via Google Cloud Build.

## Configuration & Secrets

The function requires the following environment variables:

- `ALBUM_ID`: The ID of the Google Photos album to sync.
- `BUCKET_NAME`: The name of the destination Google Cloud Storage bucket.

The following secrets must be created in Google Secret Manager:

- `CLIENT_ID`: Google OAuth2 Client ID.
- `CLIENT_SECRET`: Google OAuth2 Client Secret.
- `REFRESH_TOKEN`: Google OAuth2 Refresh Token (used to generate short-lived access tokens).

These secrets are securely passed to the Cloud Function as environment variables during deployment.

## Deployment

This project uses Google Cloud Build for deployment.

### Prerequisites

1. Set up a Google Cloud Project.
2. Enable the **Cloud Functions API**, **Cloud Build API**, **Cloud Storage API**, **Google Photos Library API**, and **Secret Manager API**.
3. Create a Google Cloud Storage bucket for the images.
4. Set up an OAuth 2.0 Client in GCP and generate a Refresh Token for a Google account that has access to the target Google Photos album.
5. Create the `CLIENT_ID`, `CLIENT_SECRET`, and `REFRESH_TOKEN` secrets in Google Secret Manager.
6. Ensure the compute service account running the function has the **Secret Manager Secret Accessor** IAM role to read these secrets.

### Deploying via Cloud Build

When setting up the Cloud Build trigger, configure the following **Substitution variables**:

- `_ALBUM_ID`
- `_BUCKET_NAME`
- `_REGION` (optional, defaults to `europe-north1`)

The `cloudbuild.yaml` file will automatically deploy the HTTP-triggered function `sync-photos` with a Python 3.13 runtime.
