import os
import asyncio
import random
import time
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from telethon import TelegramClient

# Load API credentials from environment
API_ID = int(os.getenv("API_ID", "1234567"))  # fallback for testing
API_HASH = os.getenv("API_HASH", "your_api_hash_here")

CYCLE_DURATION = 3600  # 1 hour

app = FastAPI()

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Auto Poster</title>
</head>
<body>
    <h2>Telegram Auto Poster</h2>
    <form action="/send" enctype="multipart/form-data" method="post">
        <label>Caption:</label><br>
        <textarea name="caption" rows="4" cols="50"></textarea><br><br>

        <label>Photo:</label><br>
        <input type="file" name="photo"><br><br>

        <label>Groups (one link per line):</label><br>
        <textarea name="groups" rows="6" cols="50"></textarea><br><br>

        <input type="submit" value="Start Posting">
    </form>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_FORM

async def post_to_groups(photo_file_path: str, caption: str, groups: list[str]):
    async with TelegramClient('session', API_ID, API_HASH) as client:
        total_groups = len(groups)
        if total_groups == 0:
            print("No groups provided!")
            return

        avg_interval = CYCLE_DURATION / total_groups
        low = avg_interval * 0.7
        high = avg_interval * 1.3

        print(f"Loaded {total_groups} groups. Starting posting cycle...")

        while True:
            for group in groups:
                try:
                    await client.send_file(group, photo_file_path, caption=caption)
                    print(f"[+] Sent to {group}")

                    sleep_time = random.uniform(low, high)
                    print(f"   Waiting {int(sleep_time)} seconds...\n")
                    await asyncio.sleep(sleep_time)

                except Exception as e:
                    print(f"[ERROR sending to {group}] {e}")

            print("===== 1-HOUR CYCLE FINISHED. Starting new cycle... =====\n")

@app.post("/send")
async def send(caption: str = Form(...), groups: str = Form(...), photo: UploadFile = File(...)):
    # Save uploaded file temporarily
    photo_file_path = f"temp_{int(time.time())}_{photo.filename}"
    with open(photo_file_path, "wb") as f:
        f.write(await photo.read())

    group_list = [g.strip() for g in groups.splitlines() if g.strip()]

    # Start background task for posting
    asyncio.create_task(post_to_groups(photo_file_path, caption, group_list))

    return HTMLResponse(f"<h3>Started posting to {len(group_list)} groups!</h3>")
