"""
ComfyUI Custom Node: Google Drive Image Upload
Uploads images from ComfyUI workflows to Google Drive using a Service Account.

For use with ComfyDeploy or any ComfyUI installation.
"""

import os
import io
import json
import base64
import tempfile
from datetime import datetime
from typing import Tuple

import numpy as np
from PIL import Image

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


class GoogleDriveUpload:
    """
    ComfyUI node that uploads images to a specified Google Drive folder.
    Uses Service Account authentication for serverless environments.
    """
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
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
                "service_account_json": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "Paste Service Account JSON here (optional if using env var)"
                }),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("status", "file_url",)
    FUNCTION = "upload_to_drive"
    CATEGORY = "image/output"
    OUTPUT_NODE = True

    def get_credentials(self, service_account_json: str = ""):
        """
        Get Google credentials from either:
        1. Direct JSON input (service_account_json parameter)
        2. Base64 encoded environment variable (GOOGLE_SERVICE_ACCOUNT_BASE64)
        3. JSON string environment variable (GOOGLE_SERVICE_ACCOUNT_JSON)
        4. File path environment variable (GOOGLE_APPLICATION_CREDENTIALS)
        """
        
        # Priority 1: Direct JSON input from node
        if service_account_json and service_account_json.strip():
            try:
                credentials_dict = json.loads(service_account_json.strip())
                return service_account.Credentials.from_service_account_info(
                    credentials_dict, scopes=self.SCOPES
                )
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in service_account_json input: {e}")
        
        # Priority 2: Base64 encoded environment variable
        base64_creds = os.environ.get('GOOGLE_SERVICE_ACCOUNT_BASE64')
        if base64_creds:
            try:
                decoded = base64.b64decode(base64_creds).decode('utf-8')
                credentials_dict = json.loads(decoded)
                return service_account.Credentials.from_service_account_info(
                    credentials_dict, scopes=self.SCOPES
                )
            except Exception as e:
                raise ValueError(f"Failed to decode GOOGLE_SERVICE_ACCOUNT_BASE64: {e}")
        
        # Priority 3: JSON string environment variable
        json_creds = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if json_creds:
            try:
                credentials_dict = json.loads(json_creds)
                return service_account.Credentials.from_service_account_info(
                    credentials_dict, scopes=self.SCOPES
                )
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
        
        # Priority 4: File path (standard Google approach)
        file_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if file_path and os.path.exists(file_path):
            return service_account.Credentials.from_service_account_file(
                file_path, scopes=self.SCOPES
            )
        
        raise ValueError(
            "No Google credentials found. Please provide credentials via:\n"
            "1. The 'service_account_json' input field\n"
            "2. GOOGLE_SERVICE_ACCOUNT_BASE64 environment variable\n"
            "3. GOOGLE_SERVICE_ACCOUNT_JSON environment variable\n"
            "4. GOOGLE_APPLICATION_CREDENTIALS file path"
        )

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
        service_account_json: str = ""
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
            credentials = self.get_credentials(service_account_json)
            
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