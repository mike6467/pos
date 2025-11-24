import os
import asyncio
import random
import time
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import pathlib

# Load API credentials from environment
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

CYCLE_DURATION = 3600  # 1 hour
SESSION_NAME = 'telegram_session'

app = FastAPI()

session_file = pathlib.Path(f'{SESSION_NAME}.session')

AUTH_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Authentication</title>
    <style>
        body { font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px; }
        .form-group { margin: 20px 0; }
        input, textarea { width: 100%; padding: 10px; font-size: 14px; }
        button { padding: 10px 20px; font-size: 16px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>🔐 One-Time Setup - Authenticate with Telegram</h1>
    <p>Enter your phone number to authenticate (you'll receive a code in Telegram):</p>
    
    <form action="/auth-phone" method="post">
        <div class="form-group">
            <label>Phone Number:</label>
            <input type="tel" name="phone" placeholder="+1234567890" required>
        </div>
        <button type="submit">Send Code</button>
    </form>
</body>
</html>
"""

VERIFY_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Verify Code</title>
    <style>
        body { font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px; }
        .form-group { margin: 20px 0; }
        input { width: 100%; padding: 10px; font-size: 14px; }
        button { padding: 10px 20px; font-size: 16px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>Verify Code</h1>
    <p>Check your Telegram app for the verification code</p>
    
    <form action="/auth-verify" method="post">
        <input type="hidden" name="phone" value="{phone}">
        <input type="hidden" name="phone_code_hash" value="{phone_code_hash}">
        <div class="form-group">
            <label>Verification Code:</label>
            <input type="text" name="code" placeholder="12345" required>
        </div>
        <button type="submit">Verify</button>
    </form>
</body>
</html>
"""

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
    if not session_file.exists():
        return AUTH_HTML
    return HTML_FORM

@app.post("/auth-phone")
async def auth_phone(phone: str = Form(...)):
    """Send verification code to phone"""
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        result = await client.send_code_request(phone)
        await client.disconnect()
        
        print(f"[AUTH] Code sent to {phone}")
        return HTMLResponse(VERIFY_HTML_TEMPLATE.format(
            phone=phone,
            phone_code_hash=result.phone_code_hash
        ))
    except Exception as e:
        print(f"[ERROR] {e}")
        return HTMLResponse(f"<h3>Error: {str(e)}</h3><p><a href='/'>Back</a></p>")

@app.post("/auth-verify")
async def auth_verify(phone: str = Form(...), code: str = Form(...), phone_code_hash: str = Form(...)):
    """Verify code and save session"""
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        
        try:
            user = await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            print(f"[AUTH SUCCESS] Authenticated as {user.first_name}")
        except SessionPasswordNeededError:
            await client.disconnect()
            return HTMLResponse("<h3>Error: 2FA not supported</h3><p><a href='/'>Back</a></p>")
        
        await client.disconnect()
        
        return HTMLResponse("""
            <h3>✓ Authenticated Successfully!</h3>
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
    # Save uploaded file temporarily
    photo_file_path = f"temp_{int(time.time())}_{photo.filename}"
    with open(photo_file_path, "wb") as f:
        f.write(await photo.read())

    group_list = [g.strip() for g in groups.splitlines() if g.strip()]

    # Start background task for posting
    asyncio.create_task(post_to_groups(photo_file_path, caption, group_list))

    return HTMLResponse(f"<h3>Started posting to {len(group_list)} groups!</h3>")
