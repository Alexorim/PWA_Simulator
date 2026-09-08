from typing import Dict, Any
from urllib.parse import urlparse
from pwa_detector import PWAResult

def simulate_pwa(url: str, pwa_result: PWAResult) -> Dict[str, Any]:
    """Generates a simulated PWA manifest for sites that don't have one."""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc or url
    
    name = pwa_result.site_title if pwa_result.site_title else domain
    short_name = name[:12] if name else "App"
    
    scope = f"{parsed_url.scheme}://{parsed_url.netloc}/" if parsed_url.scheme and parsed_url.netloc else "/"
    
    # Filter out invalid icons (data: URIs, empty srcs)
    valid_icons = [i for i in pwa_result.icons if i.get('src', '').startswith('http')]

    return {
        "name": name,
        "short_name": short_name,
        "start_url": url,
        "display": "standalone",
        "orientation": "any",
        "background_color": pwa_result.theme_color if pwa_result.theme_color else "#000000",
        "theme_color": pwa_result.theme_color if pwa_result.theme_color else "#1A1A1A",
        "icons": valid_icons,
        "scope": scope
    }

def merge_manifest(real_manifest: Dict[str, Any], pwa_result: PWAResult) -> Dict[str, Any]:
    """Fills in missing fields in a real PWA manifest with smart defaults."""
    merged = dict(real_manifest)
    
    if "name" not in merged:
        merged["name"] = pwa_result.site_title if pwa_result.site_title else ""
        
    if "display" not in merged:
        merged["display"] = "standalone"
        
    if "background_color" not in merged:
        merged["background_color"] = pwa_result.theme_color if pwa_result.theme_color else "#000000"
        
    if "theme_color" not in merged:
        merged["theme_color"] = pwa_result.theme_color if pwa_result.theme_color else "#1A1A1A"
        
    if "icons" not in merged or not merged["icons"]:
        merged["icons"] = pwa_result.icons
        
    return merged
