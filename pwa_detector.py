import json
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from config import USER_AGENT, REQUEST_TIMEOUT

@dataclass
class PWAResult:
    has_pwa: bool
    manifest: Optional[Dict[str, Any]] = None
    site_title: str = ''
    theme_color: Optional[str] = None
    favicon_url: Optional[str] = None
    icons: List[Dict[str, Any]] = field(default_factory=list)
    start_url: str = ''
    error: Optional[str] = None

def _normalize_url(url: str) -> str:
    """Normalize URL by adding https:// if missing."""
    url = url.strip()
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError("Invalid URL")
    return url

def _parse_manifest(manifest_url: str, base_url: str) -> Optional[Dict[str, Any]]:
    """Download and parse manifest JSON, resolving relative URLs."""
    try:
        response = requests.get(
            manifest_url,
            headers={'User-Agent': USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )
        response.raise_for_status()
        manifest_data = response.json()
        
        # Resolve relative icon URLs against base_url
        if 'icons' in manifest_data and isinstance(manifest_data['icons'], list):
            for icon in manifest_data['icons']:
                if 'src' in icon:
                    icon['src'] = urljoin(base_url, icon['src'])
                    
        return manifest_data
    except Exception as e:
        logging.warning(f"Failed to parse manifest from {manifest_url}: {e}")
        return None

def _extract_html_icons(soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
    """Extract favicon and icon links from HTML."""
    icons = []
    icon_rels = ['icon', 'apple-touch-icon', 'shortcut icon']
    for link in soup.find_all('link'):
        rel = link.get('rel', [])
        if isinstance(rel, str):
            rel = [rel]
        
        # Check if rel contains any of our target icon values
        if any(r.lower() in icon_rels for r in rel):
            href = link.get('href')
            if href:
                icon_data = {
                    'src': urljoin(base_url, href),
                    'type': link.get('type', ''),
                    'sizes': link.get('sizes', '')
                }
                icons.append(icon_data)
    return icons

def detect_pwa(url: str) -> PWAResult:
    """Detect PWA support and extract metadata."""
    try:
        url = _normalize_url(url)
    except Exception as e:
        return PWAResult(has_pwa=False, error=f"Invalid URL formatting: {e}")

    result = PWAResult(has_pwa=False, start_url=url)
    
    try:
        response = requests.get(
            url,
            headers={'User-Agent': USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )
        response.raise_for_status()
        base_url = response.url
        result.start_url = base_url
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        if soup.title and soup.title.string:
            result.site_title = soup.title.string.strip()
            
        # Extract theme color
        theme_meta = soup.find('meta', attrs={'name': 'theme-color'})
        if theme_meta and theme_meta.get('content'):
            result.theme_color = theme_meta.get('content')
            
        # Extract icons from HTML
        html_icons = _extract_html_icons(soup, base_url)
        if html_icons:
            result.favicon_url = html_icons[0]['src']
            
        result.icons.extend(html_icons)
        
        # Look for manifest
        manifest_link = soup.find('link', rel='manifest')
        if manifest_link and manifest_link.get('href'):
            manifest_url = urljoin(base_url, manifest_link.get('href'))
            manifest_data = _parse_manifest(manifest_url, base_url)
            
            if manifest_data:
                result.manifest = manifest_data
                # Validate it has at least 'name' or 'short_name'
                if 'name' in manifest_data or 'short_name' in manifest_data:
                    result.has_pwa = True
                
                # Resolve start_url if present
                if 'start_url' in manifest_data and manifest_data['start_url']:
                    result.start_url = urljoin(base_url, manifest_data['start_url'])

                # Populate icons list from manifest
                if 'icons' in manifest_data and isinstance(manifest_data['icons'], list):
                    result.icons.extend(manifest_data['icons'])
                    
        return result
        
    except requests.RequestException as e:
        result.error = f"Network error during detection: {str(e)}"
        parsed = urlparse(url)
        if not result.site_title:
            result.site_title = parsed.netloc or url
        return result
    except Exception as e:
        result.error = f"Unexpected error during detection: {str(e)}"
        parsed = urlparse(url)
        if not result.site_title:
            result.site_title = parsed.netloc or url
        return result
