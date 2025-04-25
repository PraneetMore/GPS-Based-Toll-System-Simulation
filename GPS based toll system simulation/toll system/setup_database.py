import sqlite3
from werkzeug.security import generate_password_hash

def create_database():
    conn = sqlite3.connect('vehicle.db')
    cursor = conn.cursor()
    
    # Create users table with additional fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Create vehicles table with additional fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            vehicle_id TEXT UNIQUE NOT NULL,
            vehicle_name TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            registration_number TEXT UNIQUE,
            last_longitude REAL,
            last_latitude REAL,
            registration_date DATE,
            insurance_expiry DATE,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Enhanced transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            vehicle_id TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            distance REAL NOT NULL,
            toll REAL NOT NULL,
            fine REAL DEFAULT 0,
            start_longitude REAL NOT NULL,
            start_latitude REAL NOT NULL,
            end_longitude REAL NOT NULL,
            end_latitude REAL NOT NULL,
            payment_status TEXT DEFAULT 'pending',
            transaction_id TEXT UNIQUE,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Enhanced feedback table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            feedback TEXT NOT NULL,
            rating INTEGER CHECK (rating BETWEEN 1 AND 5),
            category TEXT,
            status TEXT DEFAULT 'unread',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Payment methods table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            card_type TEXT,
            last_four TEXT,
            expiry TEXT,
            is_default BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Toll plaza details table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS toll_plazas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            highway TEXT,
            direction TEXT,
            operator TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS simulation_routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id TEXT NOT NULL,
            route_coordinates TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def create_admin_user():
    conn = sqlite3.connect('vehicle.db')
    cursor = conn.cursor()
    
    # Check if admin already exists
    admin = cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
    if not admin:
        hashed_password = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (username, password, email, role) 
            VALUES (?, ?, ?, ?)
        ''', ('admin', hashed_password, 'admin@tollsystem.com', 'admin'))
        conn.commit()
    
    conn.close()

if __name__ == '__main__':
    create_database()
    create_admin_user()