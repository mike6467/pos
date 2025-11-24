import os
import asyncio
import time
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from telethon import TelegramClient
import pathlib

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

SESSION_NAME = 'telegram_session'

app = FastAPI()

session_file = pathlib.Path(f'{SESSION_NAME}.session')

AUTH_HTML = """<!DOCTYPE html><html><head><title>Telegram Authentication</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>* {margin: 0; padding: 0; box-sizing: border-box;} body {font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;} .container {background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 500px; width: 100%; padding: 40px;} .header {text-align: center; margin-bottom: 40px;} h1 {color: #333; font-size: 28px; margin-bottom: 10px;} .subtitle {color: #666; font-size: 14px;} .info-box {background: #e3f2fd; border-left: 4px solid #2196f3; padding: 12px; border-radius: 10px; margin-bottom: 30px; color: #1565c0; font-size: 13px; line-height: 1.6;} .form-group {margin-bottom: 20px;} label {display: block; color: #333; font-weight: 600; margin-bottom: 8px; font-size: 14px;} input {width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 14px; transition: border-color 0.3s;} input:focus {outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);} .submit-btn {width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: transform 0.2s;} .submit-btn:hover {transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);} .steps {background: #f5f5f5; padding: 15px; border-radius: 10px; font-size: 13px; color: #666; line-height: 1.8; margin-top: 30px;} .step {margin-bottom: 10px;}</style></head><body><div class="container"><div class="header"><h1>🔐 Authenticate with Telegram</h1><p class="subtitle">One-time setup required</p></div><div class="info-box">⚠️ You need to authenticate once to use this app. We'll send you a code via Telegram.</div><form action="/auth" method="post"><div class="form-group"><label>Phone Number</label><input type="tel" name="phone" placeholder="+1234567890" required></div><button type="submit" class="submit-btn">📱 Send Code</button></form><div class="steps"><strong>How it works:</strong><div class="step">1️⃣ Enter your phone number (with country code)</div><div class="step">2️⃣ Telegram will send you a code</div><div class="step">3️⃣ Enter the code on the next page</div><div class="step">4️⃣ If you have 2FA, also enter password</div><div class="step">5️⃣ Done! Start posting to your groups</div></div></div></body></html>"""

CODE_HTML = """<!DOCTYPE html><html><head><title>Verify Code</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>* {margin: 0; padding: 0; box-sizing: border-box;} body {font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;} .container {background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 500px; width: 100%; padding: 40px;} h1 {color: #333; font-size: 24px; margin-bottom: 10px; text-align: center;} .subtitle {color: #666; font-size: 14px; text-align: center; margin-bottom: 30px;} .form-group {margin-bottom: 20px;} label {display: block; color: #333; font-weight: 600; margin-bottom: 8px; font-size: 14px;} input {width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 14px; transition: border-color 0.3s;} input:focus {outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);} .submit-btn {width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: transform 0.2s;} .submit-btn:hover {transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);} .info {background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; border-radius: 10px; color: #856404; font-size: 13px; margin-bottom: 20px;}</style></head><body><div class="container"><h1>✓ Code Sent!</h1><p class="subtitle">Check your Telegram app for the verification code</p><div class="info">📨 Enter the code below. If you have 2FA enabled, you'll need your password too.</div><form action="/verify" method="post"><input type="hidden" name="phone" value="PHONE_PLACEHOLDER"><div class="form-group"><label>Verification Code</label><input type="text" name="code" placeholder="12345" required></div><div class="form-group"><label>2FA Password (if enabled)</label><input type="password" name="password" placeholder="Leave empty if no 2FA"></div><button type="submit" class="submit-btn">✓ Verify</button></form></div></body></html>"""

HOME_HTML = """<!DOCTYPE html><html><head><title>Telegram Auto Poster</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>* {margin: 0; padding: 0; box-sizing: border-box;} body {font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;} .container {background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 700px; width: 100%; padding: 40px;} .header {text-align: center; margin-bottom: 40px; position: relative;} h1 {color: #333; font-size: 32px; margin-bottom: 10px;} .subtitle {color: #666; font-size: 14px;} .logout-btn {position: absolute; top: 0; right: 0; padding: 10px 16px; background: #ff6b6b; color: white; border: none; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer; transition: transform 0.2s;} .logout-btn:hover {transform: translateY(-2px); background: #ff5252;} .form-group {margin-bottom: 30px;} label {display: block; color: #333; font-weight: 600; margin-bottom: 12px; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;} textarea {width: 100%; padding: 14px; border: 2px solid #e0e0e0; border-radius: 10px; font-family: inherit; font-size: 14px; resize: vertical; transition: border-color 0.3s;} textarea:focus {outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);} .file-input-wrapper {position: relative; overflow: hidden; display: inline-block; width: 100%;} .file-input-wrapper input[type=file] {position: absolute; left: -9999px;} .file-input-label {display: block; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; cursor: pointer; text-align: center; font-weight: 600; transition: transform 0.2s;} .file-input-label:hover {transform: translateY(-2px);} .file-list {margin-top: 12px; padding: 12px; background: #f5f5f5; border-radius: 10px; max-height: 150px; overflow-y: auto;} .file-item {color: #666; font-size: 13px; padding: 6px 0; border-bottom: 1px solid #e0e0e0;} .file-item:last-child {border-bottom: none;} .submit-btn {width: 100%; padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: transform 0.2s;} .submit-btn:hover {transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);}</style></head><body><div class="container"><div class="header"><h1>📱 Telegram Auto Poster</h1><p class="subtitle">Posts to all your joined groups automatically</p><a href="/logout" class="logout-btn">🚪 Logout</a></div><form action="/send" enctype="multipart/form-data" method="post"><div class="form-group"><label>Caption:</label><textarea name="caption" rows="4" placeholder="Enter your post caption here..."></textarea></div><div class="form-group"><label>Photos (select multiple):</label><div class="file-input-wrapper"><input type="file" name="photos" id="photos" accept="image/*" multiple required><label for="photos" class="file-input-label">📸 Click to select images</label></div><div class="file-list" id="fileList" style="display: none;"></div></div><button type="submit" class="submit-btn">🚀 Start Posting</button></form></div><script>const fileInput = document.getElementById('photos'); const fileList = document.getElementById('fileList'); fileInput.addEventListener('change', function() {if (this.files.length > 0) {fileList.style.display = 'block'; fileList.innerHTML = ''; for (let file of this.files) {const item = document.createElement('div'); item.className = 'file-item'; item.textContent = '✓ ' + file.name + ' (' + (file.size / 1024).toFixed(2) + ' KB)'; fileList.appendChild(item);}} else {fileList.style.display = 'none';}});</script></body></html>"""

@app.get("/", response_class=HTMLResponse)
async def home():
    if not session_file.exists():
        return AUTH_HTML
    return HOME_HTML

@app.post("/auth")
async def auth(phone: str = Form(...)):
    if not API_ID or not API_HASH:
        return HTMLResponse("<h3>Error: API credentials not configured</h3>")
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        result = await client.send_code_request(phone)
        await client.disconnect()
        print(f"[AUTH] Code sent to {phone}")
        html = CODE_HTML.replace("PHONE_PLACEHOLDER", phone)
        return HTMLResponse(html)
    except Exception as e:
        print(f"[AUTH ERROR] {e}")
        return HTMLResponse(f"<h3>Error: {str(e)}</h3><p><a href='/'>Back</a></p>")

@app.post("/verify")
async def verify(phone: str = Form(...), code: str = Form(...), password: str = Form("")):
    if not API_ID or not API_HASH:
        return HTMLResponse("<h3>Error: API credentials not configured</h3>")
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    try:
        await client.connect()
        
        code_callback = lambda: code
        password_callback = lambda: password if password.strip() else None
        
        await client.start(
            phone=phone,
            code_callback=code_callback,
            password=password_callback
        )
        
        print(f"[AUTH SUCCESS] Account authenticated")
        await client.disconnect()
        return HTMLResponse("<h3>✓ Authenticated Successfully!</h3><p>Redirecting...</p><script>setTimeout(() => window.location.href = '/', 2000);</script>")
    
    except Exception as e:
        print(f"[VERIFY ERROR] {type(e).__name__}: {str(e)}")
        try:
            await client.disconnect()
        except:
            pass
        return HTMLResponse(f"<h3>❌ Authentication Failed</h3><p>Error: {str(e)}</p><p><a href='/'>Back to start</a></p>")

@app.get("/logout")
async def logout():
    try:
        if session_file.exists():
            session_file.unlink()
            print("[LOGOUT] Session deleted successfully")
    except Exception as e:
        print(f"[LOGOUT ERROR] {e}")
    return HTMLResponse("<h3>✓ Logged out successfully!</h3><p>Redirecting...</p><script>setTimeout(() => window.location.href = '/', 2000);</script>")

async def post_to_groups(photo_file_paths: list, caption: str):
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        groups = []
        async for dialog in client.iter_dialogs():
            if dialog.is_group:
                try:
                    full_chat = await client.get_entity(dialog.entity)
                    is_admin = full_chat.creator or (hasattr(full_chat, 'admin_rights') and full_chat.admin_rights)
                    if not is_admin:
                        groups.append(dialog.entity)
                except:
                    groups.append(dialog.entity)
        
        if not groups:
            print("[ERROR] No groups found!")
            return
        
        print(f"Found {len(groups)} groups (excluding admin groups). Starting posting cycle...")
        
        # Track last message ID for each group to detect new messages
        last_message_ids = {}
        
        while True:
            for group in groups:
                try:
                    group_name = group.title if hasattr(group, 'title') else group
                    
                    # On first cycle or subsequent cycles, check for new messages
                    has_new_messages = True
                    if group.id in last_message_ids:
                        try:
                            # Get the last message in the group
                            messages = await client.get_messages(group, limit=1)
                            if messages:
                                latest_msg_id = messages[0].id
                                # Only post if there's a newer message than our last message
                                if latest_msg_id <= last_message_ids[group.id]:
                                    print(f"[-] Skipped {group_name} (no new messages since last post)")
                                    await asyncio.sleep(5)
                                    continue
                        except Exception as e:
                            print(f"[WARNING] Could not check messages in {group_name}: {e}")
                    
                    # Post the content
                    await client.send_file(group, photo_file_paths, caption=caption)
                    
                    # Store the message ID after posting
                    try:
                        messages = await client.get_messages(group, limit=1)
                        if messages:
                            last_message_ids[group.id] = messages[0].id
                    except:
                        pass
                    
                    print(f"[+] Sent {len(photo_file_paths)} images to {group_name}")
                    await asyncio.sleep(5)
                except Exception as e:
                    if "CHAT_SEND_PHOTOS_FORBIDDEN" in str(e):
                        try:
                            await client.send_message(group, caption)
                            
                            # Store the message ID after posting
                            try:
                                messages = await client.get_messages(group, limit=1)
                                if messages:
                                    last_message_ids[group.id] = messages[0].id
                            except:
                                pass
                            
                            group_name = group.title if hasattr(group, 'title') else group
                            print(f"[+] Sent caption only to {group_name} (photos forbidden)")
                            await asyncio.sleep(5)
                        except Exception as e2:
                            print(f"[ERROR] Failed to send caption to {group}: {e2}")
                    else:
                        print(f"[ERROR] Failed to send to {group}: {e}")
            
            print("===== Cycle completed. Waiting 30 minutes before next cycle... =====")
            await asyncio.sleep(1800)

@app.post("/send")
async def send(caption: str = Form(...), photos: list[UploadFile] = File(...)):
    photo_paths = []
    timestamp = int(time.time())
    
    for i, photo in enumerate(photos):
        photo_path = f"temp_{timestamp}_{i}_{photo.filename}"
        with open(photo_path, "wb") as f:
            f.write(await photo.read())
        photo_paths.append(photo_path)
    
    import asyncio as aio
    aio.create_task(post_to_groups(photo_paths, caption))
    
    return HTMLResponse(f"<h3>✓ Started posting {len(photo_paths)} images to all your groups!</h3><p>Posts will be sent with 1-minute intervals, then 30-minute wait between cycles.</p><p><a href='/'>Back home</a></p>")
