"""
Bunny CDN Storage Utility

This module provides functions to upload and delete files from Bunny CDN Storage.
It replaces the Cloudinary upload functions in the project.
"""

import requests
from django.conf import settings
import os
import re


def get_bunny_config():
    """Get Bunny CDN configuration from settings"""
    return {
        'api_key': getattr(settings, 'BUNNY_STORAGE_API_KEY', ''),
        'storage_zone': getattr(settings, 'BUNNY_STORAGE_ZONE', ''),
        'region': getattr(settings, 'BUNNY_STORAGE_REGION', ''),
        'cdn_url': getattr(settings, 'BUNNY_CDN_URL', ''),
    }


def get_storage_url(config):
    """Get the storage API URL based on region"""
    region = config['region']
    if region:
        return f"https://{region}.storage.bunnycdn.com"
    return "https://storage.bunnycdn.com"


def upload_to_bunny(file, path, content_type=None):
    """
    Upload file to Bunny CDN Storage Zone
    
    Args:
        file: File object (can be InMemoryUploadedFile or file-like object)
        path: Path where file should be stored (e.g., 'product_images/product_123/image.jpg')
        content_type: Optional content type override
    
    Returns:
        CDN URL of uploaded file
    
    Raises:
        Exception on upload failure
    """
    config = get_bunny_config()
    storage_url = get_storage_url(config)
    
    # Clean path - remove leading slash if present
    path = path.lstrip('/')
    
    # Full URL for upload
    url = f"{storage_url}/{config['storage_zone']}/{path}"
    
    headers = {
        "AccessKey": config['api_key'],
    }
    
    # Read file content
    if hasattr(file, 'read'):
        file.seek(0)  # Ensure we're at the start of the file
        content = file.read()
    else:
        content = file
    
    response = requests.put(url, data=content, headers=headers)
    
    if response.status_code in [200, 201]:
        # Return CDN URL
        cdn_url = f"{config['cdn_url']}/{path}"
        return cdn_url
    else:
        raise Exception(f"Bunny upload failed ({response.status_code}): {response.text}")


def upload_to_bunny_from_url(source_url, path):
    """
    Download file from URL and upload to Bunny CDN
    
    Args:
        source_url: URL to download file from
        path: Path where file should be stored
    
    Returns:
        CDN URL of uploaded file
    """
    # Download file
    response = requests.get(source_url)
    if response.status_code != 200:
        raise Exception(f"Failed to download from {source_url}")
    
    config = get_bunny_config()
    storage_url = get_storage_url(config)
    
    path = path.lstrip('/')
    url = f"{storage_url}/{config['storage_zone']}/{path}"
    
    headers = {
        "AccessKey": config['api_key'],
    }
    
    upload_response = requests.put(url, data=response.content, headers=headers)
    
    if upload_response.status_code in [200, 201]:
        return f"{config['cdn_url']}/{path}"
    else:
        raise Exception(f"Bunny upload failed: {upload_response.text}")


def delete_from_bunny(path_or_url):
    """
    Delete file from Bunny CDN Storage Zone
    
    Args:
        path_or_url: Either the path or full CDN URL of the file
    
    Returns:
        True if deleted successfully, False otherwise
    """
    config = get_bunny_config()
    
    # If it's a full URL, extract the path
    if path_or_url.startswith('http'):
        # Extract path from CDN URL
        cdn_url = config['cdn_url']
        if cdn_url and path_or_url.startswith(cdn_url):
            path = path_or_url.replace(cdn_url, '').lstrip('/')
        else:
            # Try to extract path from URL
            path = '/'.join(path_or_url.split('/')[3:])
    else:
        path = path_or_url.lstrip('/')
    
    storage_url = get_storage_url(config)
    url = f"{storage_url}/{config['storage_zone']}/{path}"
    
    headers = {
        "AccessKey": config['api_key'],
    }
    
    response = requests.delete(url, headers=headers)
    return response.status_code in [200, 404]  # 404 means already deleted


def extract_public_id_from_cloudinary(url):
    """
    Extract public_id from Cloudinary URL for migration purposes
    
    Args:
        url: Cloudinary URL
    
    Returns:
        Public ID string or None
    """
    if 'cloudinary.com' not in url:
        return None
    
    match = re.search(r"/upload/(?:v\d+/)?(.+)$", url)
    if match:
        # Remove file extension
        public_id = match.group(1)
        return public_id.rsplit('.', 1)[0]
    return None


def get_path_from_cloudinary_url(url):
    """
    Convert Cloudinary URL to Bunny path
    
    Args:
        url: Cloudinary URL
    
    Returns:
        Path suitable for Bunny storage
    """
    if 'cloudinary.com' not in url:
        return None
    
    match = re.search(r"/upload/(?:v\d+/)?(.+)$", url)
    if match:
        return match.group(1)
    return None
