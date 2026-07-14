from os import getenv

import aiohttp
from dotenv import load_dotenv


session: aiohttp.ClientSession | None = None

load_dotenv()
E621_USERNAME = getenv("E621_USERNAME")
E621_API_KEY = getenv("E621_API_KEY")


async def create_session():
    global session

    if session is None or session.closed:
        session = aiohttp.ClientSession(
            headers={
                "User-Agent": "E-Bot/1.0"
            },
            auth=aiohttp.BasicAuth(
                login=E621_USERNAME,
                password=E621_API_KEY
            )
        )


async def close_session():
    global session

    if session and not session.closed:
        await session.close()

def get_session() -> aiohttp.ClientSession:
    if session is None:
        raise RuntimeError("Session is not created")
    return session