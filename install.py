"""
Install script for ComfyUI Google Drive Upload Node.
This script is executed by ComfyUI-Manager after requirements.txt is processed.
"""

import subprocess
import sys
import os

def is_installed(package_name):
    """Check if a package is installed."""
    try:
        __import__(package_name.replace("-", "_").split("==")[0])
        return True
    except ImportError:
        return False

def install_package(package):
    """Install a package using pip."""
    print(f"[GoogleDriveUpload] Installing {package}...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", package, "--no-cache-dir"
    ])

def main():
    """Main installation function."""
    print("[GoogleDriveUpload] Running install script...")
    
    packages = [
        ("google.oauth2", "google-auth"),
        ("google.auth.transport.requests", "google-auth-httplib2"),
        ("google_auth_oauthlib", "google-auth-oauthlib"),
        ("googleapiclient", "google-api-python-client"),
    ]
    
    installed_count = 0
    for module_name, package_name in packages:
        try:
            __import__(module_name)
            print(f"[GoogleDriveUpload] {package_name} already installed")
        except ImportError:
            install_package(package_name)
            installed_count += 1
    
    if installed_count > 0:
        print(f"[GoogleDriveUpload] Installed {installed_count} packages")
    else:
        print("[GoogleDriveUpload] All dependencies already satisfied")
    
    print("[GoogleDriveUpload] Installation complete!")

if __name__ == "__main__":
    main()