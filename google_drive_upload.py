"""
ComfyUI Custom Node: Google Drive Image Upload
Uploads images from ComfyUI workflows to Google Drive using OAuth 2.0.

For use with ComfyDeploy or any ComfyUI installation.
"""

import os
import io
import json
from datetime import datetime
from typing import Tuple

import numpy as np
from PIL import Image

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


class GoogleDriveUpload:
    """
    ComfyUI node that uploads images to a specified Google Drive folder.
    Uses OAuth 2.0 authentication for personal Google Drive accounts.
    """
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "folder_id": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Google Drive folder ID"
                }),
                "filename_prefix": ("STRING", {
                    "default": "comfyui_output",
                    "multiline": False,
                    "placeholder": "Filename prefix"
                }),
                "image_format": (["PNG", "JPEG", "WEBP"],),
                "jpeg_quality": ("INT", {
                    "default": 95,
                    "min": 1,
                    "max": 100,
                    "step": 1
                }),
                "add_timestamp": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "credentials_json": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "Optional: JSON with client_id, client_secret, refresh_token"
                }),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("status", "file_url",)
    FUNCTION = "upload_to_drive"
    CATEGORY = "image/output"
    OUTPUT_NODE = True

    def get_credentials(self, credentials_json: str = ""):
        """
        Get Google OAuth credentials from either:
        1. Direct JSON input with client_id, client_secret, refresh_token
        2. Environment variables: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
        """
        
        client_id = None
        client_secret = None
        refresh_token = None
        
        # Priority 1: Direct JSON input from node
        if credentials_json and credentials_json.strip():
            try:
                creds_dict = json.loads(credentials_json.strip())
                client_id = creds_dict.get('client_id')
                client_secret = creds_dict.get('client_secret')
                refresh_token = creds_dict.get('refresh_token')
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in credentials_json input: {e}")
        
        # Priority 2: Environment variables (fallback for missing values)
        if not client_id:
            client_id = os.environ.get('GOOGLE_CLIENT_ID')
        if not client_secret:
            client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        if not refresh_token:
            refresh_token = os.environ.get('GOOGLE_REFRESH_TOKEN')
        
        # Validate we have all required values
        if not all([client_id, client_secret, refresh_token]):
            missing = []
            if not client_id:
                missing.append("client_id / GOOGLE_CLIENT_ID")
            if not client_secret:
                missing.append("client_secret / GOOGLE_CLIENT_SECRET")
            if not refresh_token:
                missing.append("refresh_token / GOOGLE_REFRESH_TOKEN")
            
            raise ValueError(
                f"Missing OAuth credentials: {', '.join(missing)}\n\n"
                "Please provide credentials via:\n"
                "1. The 'credentials_json' input field with JSON containing client_id, client_secret, refresh_token\n"
                "2. Environment variables: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN\n\n"
                "Run the get_refresh_token.py script to generate these values."
            )
        
        # Create credentials object
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=self.SCOPES
        )
        
        # Refresh the token to get a valid access token
        credentials.refresh(Request())
        
        return credentials

    def tensor_to_pil(self, image_tensor) -> Image.Image:
        """Convert ComfyUI image tensor to PIL Image."""
        # ComfyUI images are (batch, height, width, channels) with values 0-1
        if len(image_tensor.shape) == 4:
            image_tensor = image_tensor[0]  # Take first image from batch
        
        # Convert to numpy and scale to 0-255
        image_np = (image_tensor.cpu().numpy() * 255).astype(np.uint8)
        
        # Handle different channel counts
        if image_np.shape[-1] == 1:
            image_np = image_np.squeeze(-1)
            return Image.fromarray(image_np, mode='L')
        elif image_np.shape[-1] == 3:
            return Image.fromarray(image_np, mode='RGB')
        elif image_np.shape[-1] == 4:
            return Image.fromarray(image_np, mode='RGBA')
        else:
            raise ValueError(f"Unexpected number of channels: {image_np.shape[-1]}")

    def upload_to_drive(
        self,
        image,
        folder_id: str,
        filename_prefix: str,
        image_format: str,
        jpeg_quality: int,
        add_timestamp: bool,
        credentials_json: str = ""
    ) -> Tuple[str, str]:
        """
        Upload image to Google Drive.
        
        Returns:
            Tuple of (status_message, file_url)
        """
        
        try:
            # Validate folder_id
            if not folder_id or not folder_id.strip():
                return ("Error: folder_id is required", "")
            
            folder_id = folder_id.strip()
            
            # Clean folder_id if user pasted full URL or URL with parameters
            if '?' in folder_id:
                folder_id = folder_id.split('?')[0]
            if '/' in folder_id:
                folder_id = folder_id.split('/')[-1]
            
            # Get credentials
            credentials = self.get_credentials(credentials_json)
            
            # Build Drive service
            service = build('drive', 'v3', credentials=credentials)
            
            # Convert tensor to PIL Image
            pil_image = self.tensor_to_pil(image)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") if add_timestamp else ""
            separator = "_" if timestamp else ""
            
            format_lower = image_format.lower()
            extension = "jpg" if format_lower == "jpeg" else format_lower
            filename = f"{filename_prefix}{separator}{timestamp}.{extension}"
            
            # Convert to bytes
            buffer = io.BytesIO()
            
            if format_lower == "jpeg":
                # Convert RGBA to RGB for JPEG
                if pil_image.mode == 'RGBA':
                    background = Image.new('RGB', pil_image.size, (255, 255, 255))
                    background.paste(pil_image, mask=pil_image.split()[3])
                    pil_image = background
                pil_image.save(buffer, format='JPEG', quality=jpeg_quality)
                mime_type = 'image/jpeg'
            elif format_lower == "png":
                pil_image.save(buffer, format='PNG')
                mime_type = 'image/png'
            elif format_lower == "webp":
                pil_image.save(buffer, format='WEBP', quality=jpeg_quality)
                mime_type = 'image/webp'
            else:
                return (f"Error: Unsupported format {image_format}", "")
            
            buffer.seek(0)
            
            # Prepare file metadata
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            
            # Upload file
            media = MediaIoBaseUpload(buffer, mimetype=mime_type, resumable=True)
            
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
            
            file_id = file.get('id')
            file_name = file.get('name')
            file_url = file.get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view")
            
            status = f"Success: Uploaded '{file_name}' to Google Drive"
            
            return (status, file_url)
            
        except Exception as e:
            error_msg = f"Error uploading to Google Drive: {str(e)}"
            return (error_msg, "")


# Node registration for ComfyUI
NODE_CLASS_MAPPINGS = {
    "GoogleDriveUpload": GoogleDriveUpload
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GoogleDriveUpload": "Upload to Google Drive"
}