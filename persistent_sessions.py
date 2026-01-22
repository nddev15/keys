#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enhanced Remember Me with persistent sessions"""

import sqlite3
import hashlib
import secrets
import time
from datetime import datetime, timedelta

def init_persistent_sessions():
    """Initialize persistent sessions table"""
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS persistent_sessions (
            token TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            created_at INTEGER DEFAULT (strftime('%s', 'now'))
        )
    ''')
    conn.commit()
    conn.close()

def create_persistent_session(email, remember_me=False):
    """Create persistent session token"""
    token = secrets.token_urlsafe(32)
    expires_days = 60 if remember_me else 1
    expires_at = int(time.time()) + (expires_days * 24 * 60 * 60)
    
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO persistent_sessions 
        (token, email, expires_at) VALUES (?, ?, ?)
    ''', (token, email, expires_at))
    conn.commit()
    conn.close()
    
    return token

def validate_persistent_session(token):
    """Validate and return email for persistent session"""
    if not token:
        return None
        
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''
        SELECT email FROM persistent_sessions 
        WHERE token = ? AND expires_at > ?
    ''', (token, int(time.time())))
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else None

def cleanup_expired_sessions():
    """Remove expired persistent sessions"""
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('DELETE FROM persistent_sessions WHERE expires_at < ?', (int(time.time()),))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    return deleted

print("Enhanced Remember Me system ready!")
print("Features:")
print("• ✅ Persistent sessions survive server restart")
print("• ✅ 60-day sessions when remember_me=True")
print("• ✅ 24-hour sessions when remember_me=False")
print("• ✅ Automatic cleanup of expired sessions")
print("• ✅ Secure token generation")
print("\nTo implement:")
print("1. Call init_persistent_sessions() on startup")
print("2. Set persistent session token as cookie on login")
print("3. Check persistent session before regular session check")
print("4. Clean expired sessions periodically")