import sqlite3
from datetime import datetime


def setup_database(db_name="chat_data.db"):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON;")
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ssn TEXT UNIQUE NOT NULL
        )
    """)
    
    # Updated: 'type' is now INTEGER (still allows NULL)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            content TEXT NOT NULL,
            type INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    return conn

def get_untagged_messages(conn, limit=100):
    """
    Retrieves ID and Content for messages where 'type' is NULL.
    
    Args:
        conn: The database connection.
        limit (int): The maximum number of messages to retrieve. Defaults to 100.
    """
    c = conn.cursor()
    # Added 'LIMIT ?' to the query
    c.execute("SELECT id, content FROM messages WHERE type IS NULL LIMIT ?", (limit,))
    return c.fetchall()

def get_messages(conn, limit=100):
    """
    Retrieves ID and Content for messages.
    
    Args:
        conn: The database connection.
        limit (int): The maximum number of messages to retrieve. Defaults to 100.
    """
    c = conn.cursor()
    # Added 'LIMIT ?' to the query
    c.execute("SELECT id, content, type FROM messages LIMIT ?", (limit,))
    return c.fetchall()

def update_message_type(conn, message_id, new_type):
    """
    Updates the type of a specific message.
    
    Args:
        message_id (int): The ID of the message to update.
        new_type (int): The integer type to assign.
    """
    try:
        c = conn.cursor()
        c.execute("UPDATE messages SET type = ? WHERE id = ?", (new_type, message_id))
        conn.commit()
        # Check if any row was actually modified
        if c.rowcount == 0:
            print(f"Warning: No message found with ID {message_id}")
        # else:
            # print(f"Updated Message {message_id} to type {new_type}")
            
    except sqlite3.Error as e:
        print(f"Database Update Error: {e}")

def store_message(conn, ssn, raw_timestamp, content, msg_type=None):
    """
    Takes a raw timestamp in 'DD/MM/YYYY HH:MM' format, converts it to
    'YYYY-MM-DD HH:MM:SS', and stores the message.
    
    Args:
        msg_type (int, optional): The numeric category of the message. Defaults to None.
    """
    try:
        # 1. Parse the input format (Day/Month/Year Hour:Minute)
        dt_object = datetime.strptime(raw_timestamp, "%d/%m/%Y %H:%M")
        
        # 2. Convert to ISO format (Year-Month-Day Hour:Minute:Second)
        iso_timestamp = dt_object.strftime("%Y-%m-%d %H:%M:%S")
        
    except ValueError as e:
        print(f"Timestamp Error: {e} | Format must be DD/MM/YYYY HH:MM")
        return

    c = conn.cursor()
    
    # Handle User ID
    try:
        c.execute("INSERT OR IGNORE INTO users (ssn) VALUES (?)", (ssn,))
        c.execute("SELECT id FROM users WHERE ssn = ?", (ssn,))
        user_id = c.fetchone()[0]
    except sqlite3.Error as e:
        print(f"Database Error (User): {e}")
        return

    # Store Message
    try:
        c.execute("""
            INSERT INTO messages (user_id, timestamp, content, type) 
            VALUES (?, ?, ?, ?)
        """, (user_id, iso_timestamp, content, msg_type))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database Error (Message): {e}")