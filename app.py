import os
import asyncio
import random
import time
import json
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from telethon import TelegramClient

# Load API credentials from environment
API_ID = int(os.getenv("API_ID", ""))
API_HASH = os.getenv("API_HASH", "")

CYCLE_DURATION = 3600  # 1 hour
SESSION_NAME = 'telegram_session'
CREDENTIALS_FILE = 'credentials.json'

app = FastAPI()

def load_credentials():
    """Load saved credentials"""
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def save_credentials(phone, code_hash):
    """Save credentials for later use"""
    creds = {'phone': phone, 'code_hash': code_hash}
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(creds, f)

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

AUTH_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Authentication</title>
</head>
<body>
    <h2>Authenticate with Telegram</h2>
    <form action="/auth-phone" method="post">
        <label>Phone Number:</label><br>
        <input type="tel" name="phone" placeholder="+1234567890" required><br><br>
        <input type="submit" value="Send Code">
    </form>
</body>
</html>
"""

VERIFY_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Verify Code</title>
</head>
<body>
    <h2>Verify Code</h2>
    <p>Check your Telegram app for the code</p>
    <form action="/auth-verify" method="post">
        <input type="hidden" name="phone" value="{phone}">
        <label>Verification Code:</label><br>
        <input type="text" name="code" placeholder="12345" required><br><br>
        <input type="submit" value="Verify">
    </form>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    creds = load_credentials()
    if not creds:
        return AUTH_HTML
    return HTML_FORM

@app.post("/auth-phone")
async def auth_phone(phone: str = Form(...)):
    """Send code to phone"""
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        result = await client.send_code_request(phone)
        save_credentials(phone, result.phone_code_hash)
        print(f"[AUTH] Code sent to {phone}")
        await client.disconnect()
        return HTMLResponse(VERIFY_HTML_TEMPLATE.format(phone=phone))
    except Exception as e:
        print(f"[ERROR] {e}")
        return HTMLResponse(f"<h3>Error: {str(e)}</h3><p><a href='/'>Back</a></p>")

@app.post("/auth-verify")
async def auth_verify(phone: str = Form(...), code: str = Form(...)):
    """Verify code"""
    creds = load_credentials()
    if not creds:
        return HTMLResponse("<h3>Error: No session</h3><p><a href='/'>Back</a></p>")
    
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        user = await client.sign_in(phone, code, phone_code_hash=creds['code_hash'])
        await client.disconnect()
        print(f"[AUTH SUCCESS] {user.first_name}")
        return HTMLResponse("""
            <h3>✓ Authenticated!</h3>
            <p>Redirecting...</p>
            <script>setTimeout(() => window.location.href = '/', 2000);</script>
        """)
    except Exception as e:
        print(f"[VERIFY ERROR] {e}")
        return HTMLResponse(f"<h3>Error: {str(e)}</h3><p><a href='/'>Back</a></p>")

async def post_to_groups(photo_file_path: str, caption: str, groups: list[str]):
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
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
    photo_file_path = f"temp_{int(time.time())}_{photo.filename}"
    with open(photo_file_path, "wb") as f:
        f.write(await photo.read())

    group_list = [g.strip() for g in groups.splitlines() if g.strip()]

    asyncio.create_task(post_to_groups(photo_file_path, caption, group_list))

    return HTMLResponse(f"<h3>Started posting to {len(group_list)} groups!</h3>")
