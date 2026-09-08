import os
import hashlib
import io
import requests
from typing import List, Optional
from PIL import Image
from urllib.parse import urlparse
from config import ICON_CACHE_DIR, USER_AGENT, REQUEST_TIMEOUT

def _url_to_cache_path(url: str) -> str:
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    return os.path.join(ICON_CACHE_DIR, f"{url_hash}.ico")

def _parse_size(sizes_str: str) -> int:
    if not sizes_str or sizes_str.lower() == 'any':
        return 0
    try:
        # sizes_str might be something like "192x192 256x256"
        first_size = sizes_str.split()[0]
        # "192x192" -> 192
        width_str = first_size.lower().split('x')[0]
        return int(width_str)
    except Exception:
        return 0

def _download_icon(url: str) -> Optional[bytes]:
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.content
    except requests.RequestException:
        return None

def get_best_icon(icons: List[dict], min_size: int = 64) -> Optional[str]:
    if not icons:
        return None

    # Filter and score icons
    scored_icons = []
    for icon in icons:
        src = icon.get('src')
        if not src:
            continue
            
        sizes_str = icon.get('sizes', '')
        size = _parse_size(sizes_str)
        
        # Penalize icons smaller than min_size, otherwise prefer larger size
        score = size if size >= min_size else (size - 10000)
        scored_icons.append((score, src))
        
    if not scored_icons:
        return None
        
    scored_icons.sort(key=lambda x: x[0], reverse=True)
    best_src = scored_icons[0][1]
    
    icon_bytes = _download_icon(best_src)
    if not icon_bytes:
        return None
        
    cache_path = _url_to_cache_path(best_src)
    try:
        image = Image.open(io.BytesIO(icon_bytes))
        image.save(cache_path, format="ICO")
        return cache_path
    except Exception:
        return None

def favicon_fallback(domain: str) -> Optional[str]:
    domain = domain.rstrip('/')
    parsed_domain = urlparse(domain)
    base_url = f"{parsed_domain.scheme}://{parsed_domain.netloc}"
    if not parsed_domain.scheme:
        base_url = f"https://{domain}"

    # Try original favicon first
    original_favicon_url = f"{base_url}/favicon.ico"
    icon_bytes = _download_icon(original_favicon_url)
    
    if icon_bytes:
        cache_path = _url_to_cache_path(original_favicon_url)
        try:
            image = Image.open(io.BytesIO(icon_bytes))
            image.save(cache_path, format="ICO")
            return cache_path
        except Exception:
            pass # fallback to Google if this fails
            
    # Fallback to Google Favicon API
    google_api_url = f"https://www.google.com/s2/favicons?domain={base_url}&sz=128"
    icon_bytes = _download_icon(google_api_url)
    
    if icon_bytes:
        cache_path = _url_to_cache_path(google_api_url)
        try:
            image = Image.open(io.BytesIO(icon_bytes))
            image.save(cache_path, format="ICO")
            return cache_path
        except Exception:
            return None
            
    return None
