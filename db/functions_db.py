import requests
from requests.auth import HTTPBasicAuth

from db import requests_db
from main import tags_to_query


async def fetch_and_save_posts(channel_id):
    tags = await requests_db.get_channel_tags(channel_id)
    query_tags = tags_to_query(tags)

    url = f"https://e621.net/posts.json?limit=20&tags={query_tags}"

    print(url)

    username = "JAKZZ"
    api_key = "D4nG2RKgRRGqXQ4DuShuHhFv"

    headers = {
        "User-Agent": "E-Bot/1.0"
    }

    response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, api_key))

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
        file_url = post.get("sample", {}).get("url")
        tags_str = " ".join(tags)

        try:
            await requests_db.save_posts_in_nonfilter(channel_id, post_id, tags_str, file_url)

        except Exception as e:
            print("Ошибка записи:", e)

    print("Сохранено в БД")




