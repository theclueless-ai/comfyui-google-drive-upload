"""
ComfyUI Google Drive Upload Node
================================

A custom node for uploading images directly to Google Drive.
Designed for use with ComfyDeploy and other serverless environments.

Setup:
------
1. Create a Google Cloud Service Account
2. Share your target Drive folder with the Service Account email
3. Provide credentials via environment variable or node input

Environment Variables (pick one):
- GOOGLE_SERVICE_ACCOUNT_BASE64: Base64 encoded JSON credentials
- GOOGLE_SERVICE_ACCOUNT_JSON: Raw JSON string credentials  
- GOOGLE_APPLICATION_CREDENTIALS: Path to credentials file

"""

from .google_drive_upload import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

# Version info
__version__ = "1.0.0"
__author__ = "Daniel"