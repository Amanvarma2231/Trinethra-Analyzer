import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path(__file__).parent / "trinethra.db"

def init_db():
    """Initializes the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Analysis History Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS analysis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        transcript TEXT NOT NULL,
        model TEXT,
        score REAL,
        confidence TEXT,
        results_json TEXT NOT NULL,
        metadata_json TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def save_analysis(transcript: str, model: str, score: float, confidence: str, results: Dict[str, Any], metadata: Dict[str, Any] = None):
    """Saves an analysis result to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO analysis_history (transcript, model, score, confidence, results_json, metadata_json)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        transcript, 
        model, 
        score, 
        confidence, 
        json.dumps(results), 
        json.dumps(metadata) if metadata else None
    ))
    
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieves analysis history."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM analysis_history ORDER BY timestamp DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    
    history = []
    for row in rows:
        item = dict(row)
        item['results'] = json.loads(item['results_json'])
        if item['metadata_json']:
            item['metadata'] = json.loads(item['metadata_json'])
        history.append(item)
        
    conn.close()
    return history

def get_analysis_by_id(analysis_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a specific analysis by ID."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM analysis_history WHERE id = ?', (analysis_id,))
    row = cursor.fetchone()
    
    if row:
        item = dict(row)
        item['results'] = json.loads(item['results_json'])
        if item['metadata_json']:
            item['metadata'] = json.loads(item['metadata_json'])
        conn.close()
        return item
        
    conn.close()
    return None

def delete_analysis(analysis_id: int):
    """Deletes an analysis record."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM analysis_history WHERE id = ?', (analysis_id,))
    conn.commit()
    conn.close()
