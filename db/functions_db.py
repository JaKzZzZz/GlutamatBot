from os import getenv

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from db import requests_db
from main import tags_to_query

load_dotenv()
E621_USERNAME = getenv("E621_USERNAME")
E621_API_KEY = getenv("E621_API_KEY")


async def fetch_and_save_posts(channel_id):
    tags = await requests_db.get_channel_tags(channel_id)
    query_tags = tags_to_query(tags)

    last_post_id = await requests_db.get_last_post_id(channel_id)

    params = {
        "limit": 20,
        "tags": query_tags,
    }

    if last_post_id is not None:
        params["page"] = f"b{last_post_id}"

    headers = {
        "User-Agent": "E-Bot/1.0"
    }

    response = requests.get("https://e621.net/posts.json", params=params, headers=headers, auth=HTTPBasicAuth(E621_USERNAME, E621_API_KEY))

    print(response.url)

    if response.status_code != 200:
        print("Ошибка запроса:", response.status_code)
        return

    data = response.json()

    posts = data.get("posts")

    if not posts:
        print("Ошибка запроса:", response.status_code)
        return 0

    for post in data["posts"]:
        post_id = post.get("id")
        tags = post.get("tags", {}).get("general", [])
        artist_name = post.get("tags", {}).get("artist", [])
        artist_name_str = ",".join(artist_name)
        file_url = post.get("sample", {}).get("url")
        tags_str = " ".join(tags)

        try:
            await requests_db.save_posts_in_nonfilter(channel_id, post_id, tags_str, file_url, artist_name_str)

        except Exception as e:
            print("Ошибка записи:", e)

    await requests_db.update_last_post_id(posts[-1]["id"], channel_id)

    print("Сохранено в БД")




