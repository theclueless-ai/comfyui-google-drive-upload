# ComfyUI Google Drive Upload Node

A custom ComfyUI node that uploads images directly to Google Drive. Designed for serverless environments like **ComfyDeploy**.

## Features

- Upload images in PNG, JPEG, or WEBP format
- Configurable folder destination per execution
- Optional timestamp in filenames
- Multiple authentication methods for flexibility
- Returns upload status and file URL

## Installation

### For ComfyDeploy

1. Add this repository as a custom node in your ComfyDeploy workflow
2. The dependencies will be installed automatically from `requirements.txt`

### For Local ComfyUI

```bash
cd ComfyUI/custom_nodes
git clone <your-repo-url> comfyui-google-drive-upload
cd comfyui-google-drive-upload
pip install -r requirements.txt
```

## Google Cloud Setup

### 1. Create a Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Google Drive API**:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Google Drive API" and enable it
4. Create Service Account:
   - Go to "IAM & Admin" → "Service Accounts"
   - Click "Create Service Account"
   - Name it (e.g., `comfyui-drive-uploader`)
   - Click "Create and Continue" → "Done"
5. Generate Key:
   - Click on your new Service Account
   - Go to "Keys" tab
   - "Add Key" → "Create new key" → "JSON"
   - Save the downloaded JSON file securely

### 2. Share Your Drive Folder

1. Open Google Drive
2. Right-click your target folder → "Share"
3. Paste the Service Account email (found in the JSON as `client_email`)
   - It looks like: `name@project-id.iam.gserviceaccount.com`
4. Give "Editor" permissions

### 3. Get Your Folder ID

The folder ID is in the URL when you open the folder:
```
https://drive.google.com/drive/folders/1pnceWEOPxlMeKmuDWMxmMHzVILGjGeZI
                                        └──────────────────────────────────┘
                                                    This is the folder_id
```

## Authentication Methods

The node supports multiple ways to provide credentials (in priority order):

### Option 1: Direct Input (Easiest for Testing)

Paste the entire Service Account JSON directly into the `service_account_json` input field.

### Option 2: Base64 Environment Variable (Recommended for ComfyDeploy)

```bash
# Encode your JSON file
cat service-account.json | base64

# Set as environment variable in ComfyDeploy
GOOGLE_SERVICE_ACCOUNT_BASE64=<base64-encoded-string>
```

### Option 3: JSON Environment Variable

```bash
# Set the raw JSON as env var (escape quotes properly)
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
```

### Option 4: File Path (Local installations)

```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

## Node Inputs

| Input | Type | Description |
|-------|------|-------------|
| `image` | IMAGE | The image from your ComfyUI pipeline |
| `folder_id` | STRING | Google Drive folder ID |
| `filename_prefix` | STRING | Prefix for the filename (default: `comfyui_output`) |
| `image_format` | ENUM | PNG, JPEG, or WEBP |
| `jpeg_quality` | INT | Quality for JPEG/WEBP (1-100, default: 95) |
| `add_timestamp` | BOOLEAN | Add timestamp to filename (default: true) |
| `service_account_json` | STRING | Optional: Paste Service Account JSON here |

## Node Outputs

| Output | Type | Description |
|--------|------|-------------|
| `status` | STRING | Success message or error description |
| `file_url` | STRING | Direct link to view the uploaded file |

## Example Workflow

```
[Your Image Generation] → [GoogleDriveUpload]
                              ├── folder_id: "1pnceWEOPxlMeKmuDWMxmMHzVILGjGeZI"
                              ├── filename_prefix: "ai_generated"
                              ├── image_format: "PNG"
                              └── add_timestamp: true
```

## Troubleshooting

### "No Google credentials found"
- Verify your Service Account JSON is valid
- Check environment variables are set correctly
- For Base64, ensure no extra whitespace

### "Access denied" or "File not found"
- Confirm the folder is shared with the Service Account email
- Verify the Service Account has "Editor" permissions
- Double-check the folder_id is correct (no URL parameters)

### "API not enabled"
- Enable Google Drive API in your Google Cloud project

## License

MIT License