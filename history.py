import json
import os
from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime
from config import HISTORY_FILE, MAX_HISTORY

@dataclass
class HistoryEntry:
    url: str
    title: str
    favicon_path: Optional[str]
    timestamp: str

def get_history() -> List[HistoryEntry]:
    if not os.path.exists(HISTORY_FILE):
        return []
    
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [HistoryEntry(**item) for item in data]
    except (json.JSONDecodeError, IOError, TypeError):
        return []

def _save_history(history: List[HistoryEntry]):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump([asdict(entry) for entry in history], f, indent=4)
    except IOError:
        pass

def add_entry(url: str, title: str, favicon_path: Optional[str] = None):
    history = get_history()
    
    # Deduplicate by removing existing entry with same URL
    history = [entry for entry in history if entry.url != url]
    
    # Create new entry
    new_entry = HistoryEntry(
        url=url,
        title=title,
        favicon_path=favicon_path,
        timestamp=datetime.utcnow().isoformat()
    )
    
    # Insert at the top
    history.insert(0, new_entry)
    
    # Trim to MAX_HISTORY
    history = history[:MAX_HISTORY]
    
    _save_history(history)

def clear_history():
    _save_history([])

def remove_entry(url: str):
    history = get_history()
    history = [entry for entry in history if entry.url != url]
    _save_history(history)
