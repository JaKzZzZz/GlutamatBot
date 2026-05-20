import aiosqlite

DB_NAME = "posts.sql"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS nonfilter (
        file_id INTEGER PRIMARY KEY,
        file VARCHAR(255) NOT NULL,
        tags VARCHAR(1024) NOT NULL,
        status TEXT DEFAULT 'pending', -- pending / sent 
        channel_id VARCHAR(255)
        );
        CREATE TABLE IF NOT EXISTS query (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER NOT NULL,
        channel_id VARCHAR(255),
        FOREIGN KEY (file_id) REFERENCES nonfilter(file_id)
        );
        CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY,
        channel_name VARCHAR(255),
        channel_id VARCHAR(255) UNIQUE NOT NULL,
        is_active BOOLEAN DEFAULT TRUE, -- on / off,
        is_auto BOOLEAN DEFAULT FALSE, -- on / off,
        tags VARCHAR(1024)
        );
        CREATE TABLE IF NOT EXISTS settings (
        bot_status BOOLEAN DEFAULT TRUE -- on / off
        );
        INSERT INTO settings VALUES (TRUE)
        """)
        await db.commit()