import aiosqlite

from db.init_db import DB_NAME


async def save_posts_in_nonfilter(channel_id, post_id, tags_str, file_url):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""INSERT OR IGNORE INTO nonfilter (channel_id, file_id, tags, file) 
        VALUES (?, ?, ?, ?); """, (channel_id, post_id, tags_str, file_url))
        await db.commit()


async def query_approve_post(file_id, channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
                            UPDATE nonfilter 
                            SET status = 'sent' 
                            WHERE file_id = ?
                        """, (file_id,))
        await db.execute("""
            INSERT INTO query (file_id, channel_id)
            VALUES (?, ?)
        """, (file_id, channel_id))
        await db.commit()


async def query_reject_post(file_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        UPDATE nonfilter 
        SET status = 'sent'
        WHERE file_id = ?
    """, (file_id,))
        await db.commit()


async def is_channel_active(channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT is_active FROM channels WHERE channel_id = ?
        """, (channel_id,))
        row = await cursor.fetchone()
        return row[0]


async def set_channel_active(channel_id, state):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        UPDATE channels SET is_active = ? WHERE channel_id = ?
        """, (state, channel_id))
        await db.commit()
        return


async def is_channel_auto(channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT is_auto FROM channels WHERE channel_id = ?
        """, (channel_id,))
        row = await cursor.fetchone()
        return row[0]


async def set_channel_auto(channel_id, state):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        UPDATE channels SET is_auto = ? WHERE channel_id = ?
        """, (state, channel_id))
        await db.commit()
        return


async def get_bot_status():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT bot_status FROM settings
        """)
        row = await cursor.fetchone()
        return row[0]


async def set_bot_status_off():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        UPDATE settings SET bot_status = FALSE
        """)
        await db.commit()
        return


async def set_bot_status_on():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        UPDATE settings SET bot_status = TRUE
        """)
        await db.commit()
        return


async def get_channel_status(channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT status FROM channels
            WHERE channel_id = ?
        """, (channel_id,))
        row = await cursor.fetchone()
        return row[0]


async def add_post_nonfilter(file_id, file):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO nonfilter (file_id, file) VALUES (?, ?)", (file_id, file))
        await db.commit()


async def add_post_query(file_id, channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO query (file_id, channel_id) VALUES (?, ?)", (file_id, channel_id))
        await db.commit()


async def add_channels(channel_name, channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO channels (channel_name, channel_id) VALUES (?, ?)", (channel_name, channel_id,))
        await db.commit()


async def remove_channels(channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        await db.commit()


async def get_post_nonfilter():
    async with aiosqlite.connect(DB_NAME) as db:
        result = await db.execute("SELECT * FROM nonfilter WHERE status = 'pending'")
        result_nonfilter = await result.fetchall()
        return result_nonfilter


async def get_post_query():
    async with aiosqlite.connect(DB_NAME) as db:
        result = await db.execute("SELECT * FROM query")
        result_query = await result.fetchall()
        return result_query


async def get_channels():
    async with aiosqlite.connect(DB_NAME) as db:
        result = await db.execute("SELECT channel_name, channel_id FROM channels")
        result_channel = await result.fetchall()
        return result_channel


async def get_channel_tags(channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        result = await db.execute("SELECT tags FROM channels WHERE channel_id = ?", (channel_id,))
        row = await result.fetchone()
        return row[0] if row else None


async def get_posts_count(channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        result = await db.execute("SELECT COUNT(*) FROM nonfilter WHERE channel_id = ? AND status = 'pending'",
                                  (channel_id,))
        results_posts = await result.fetchone()
        return results_posts[0]


async def insert_channel_tags(tags, channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE channels SET tags = ? WHERE channel_id = ?", (tags, channel_id))
        await db.commit()
        return


async def delete_channel_tags(channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE channels SET tags = ? WHERE channel_id = ?", (None, channel_id))
        await db.commit()
        return


async def delete_nonfilter_posts(channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM nonfilter WHERE channel_id = ? AND status = 'pending'", (channel_id,))
        await db.commit()
        return


async def delete_query_posts(channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM query WHERE channel_id = ?", (channel_id,))
        await db.commit()
        return


async def delete_query_post(file_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            DELETE FROM query WHERE file_id = ?
        """, (file_id,))
        await db.commit()


async def get_next_post(channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        result = await db.execute("""
        SELECT file_id, file, tags
        FROM nonfilter
        WHERE status = 'pending' and channel_id = ?
        ORDER BY file_id
        LIMIT 1
    """, (channel_id,))
        result_post = await result.fetchone()
        return result_post


async def get_posts(channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        result = await db.execute("""
        SELECT file_id
        FROM nonfilter
        WHERE status = 'pending' and channel_id = ?
    """, (channel_id,))
        result_posts = await result.fetchall()
        return [row[0] for row in result_posts]


async def get_all_query_posts(channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT q.file_id, n.file, n.tags
            FROM query q
            JOIN nonfilter n ON q.file_id = n.file_id
            WHERE q.channel_id = ?
        """, (channel_id,))
        return await cursor.fetchall()