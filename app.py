import os
import asyncio
import time
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from telethon import TelegramClient
import pathlib

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

SESSIONS_DIR = pathlib.Path('sessions')
SESSIONS_DIR.mkdir(exist_ok=True)
ACTIVE_SESSION_FILE = pathlib.Path('active_session.txt')

app = FastAPI()

def get_active_session():
    if ACTIVE_SESSION_FILE.exists():
        return ACTIVE_SESSION_FILE.read_text().strip()
    return None

def set_active_session(session_name):
    ACTIVE_SESSION_FILE.write_text(session_name)

def get_available_accounts():
    accounts = []
    for session_file in SESSIONS_DIR.glob('*.session'):
        accounts.append(session_file.stem)
    return sorted(accounts)

AUTH_HTML = """<!DOCTYPE html><html><head><title>Telegram Authentication</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>* {margin: 0; padding: 0; box-sizing: border-box;} body {font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;} .container {background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 500px; width: 100%; padding: 40px;} .header {text-align: center; margin-bottom: 40px;} h1 {color: #333; font-size: 28px; margin-bottom: 10px;} .subtitle {color: #666; font-size: 14px;} .info-box {background: #e3f2fd; border-left: 4px solid #2196f3; padding: 12px; border-radius: 10px; margin-bottom: 30px; color: #1565c0; font-size: 13px; line-height: 1.6;} .form-group {margin-bottom: 20px;} label {display: block; color: #333; font-weight: 600; margin-bottom: 8px; font-size: 14px;} input {width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 14px; transition: border-color 0.3s;} input:focus {outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);} .submit-btn {width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: transform 0.2s;} .submit-btn:hover {transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);} .steps {background: #f5f5f5; padding: 15px; border-radius: 10px; font-size: 13px; color: #666; line-height: 1.8; margin-top: 30px;} .step {margin-bottom: 10px;} .back-link {text-align: center; margin-top: 20px;} .back-link a {color: #667eea; text-decoration: none; font-size: 13px; font-weight: 600;}</style></head><body><div class="container"><div class="header"><h1>📱 Telegram Auto Poster</h1><p class="subtitle">Sign in to your account</p></div><div class="info-box">Enter your phone number to start. You'll receive a verification code on Telegram.</div><form action="/auth" method="post"><div class="form-group"><label for="phone">📱 Phone Number</label><input type="tel" id="phone" name="phone" placeholder="+1234567890" required></div><button type="submit" class="submit-btn">Send Code</button></form><div class="steps"><div class="step">1️⃣ Enter your phone number (with country code)</div><div class="step">2️⃣ You'll get a code on Telegram</div><div class="step">3️⃣ Enter the code to verify</div><div class="step">4️⃣ If 2FA is enabled, enter your password</div></div></div></body></html>"""

CODE_HTML = """<!DOCTYPE html><html><head><title>Verify Code</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>* {margin: 0; padding: 0; box-sizing: border-box;} body {font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;} .container {background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 500px; width: 100%; padding: 40px;} h1 {color: #333; font-size: 24px; margin-bottom: 10px; text-align: center;} .subtitle {color: #666; font-size: 14px; text-align: center; margin-bottom: 30px;} .form-group {margin-bottom: 20px;} label {display: block; color: #333; font-weight: 600; margin-bottom: 8px; font-size: 14px;} input {width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 14px; transition: border-color 0.3s;} input:focus {outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);} .submit-btn {width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: transform 0.2s;} .submit-btn:hover {transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);} .info {background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; border-radius: 10px; color: #856404; font-size: 13px; margin-bottom: 20px;}</style></head><body><div class="container"><h1>✓ Code Sent!</h1><p class="subtitle">Check your Telegram app for the verification code</p><div class="info">📨 Enter the code below. If you have 2FA enabled, you'll need your password too.</div><form action="/verify" method="post"><input type="hidden" name="phone" value="PHONE_PLACEHOLDER"><div class="form-group"><label>Verification Code</label><input type="text" name="code" placeholder="Enter 5-digit code" required></div><div class="form-group"><label>2FA Password (if enabled)</label><input type="password" name="password" placeholder="Leave empty if not enabled"></div><button type="submit" class="submit-btn">Verify</button></form></div></body></html>"""

HOME_HTML = """<!DOCTYPE html><html><head><title>Telegram Auto Poster</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>* {margin: 0; padding: 0; box-sizing: border-box;} body {font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;} .container {background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 700px; width: 100%; padding: 40px; display: flex; flex-direction: column;} .header {text-align: center; margin-bottom: 30px;} h1 {color: #333; font-size: 32px; margin-bottom: 8px;} .subtitle {color: #666; font-size: 14px;} .account-bar {background: #f5f5f5; padding: 12px 16px; border-radius: 10px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;} .current-account {color: #333; font-size: 13px; font-weight: 600;} .account-buttons {display: flex; gap: 8px; flex-wrap: wrap;} .switch-btn, .logout-btn, .add-account-btn {padding: 6px 12px; border: none; border-radius: 6px; font-size: 11px; font-weight: 600; cursor: pointer; transition: transform 0.2s;} .switch-btn {background: #667eea; color: white;} .switch-btn:hover {transform: translateY(-2px); background: #5568d3;} .add-account-btn {background: #4caf50; color: white;} .add-account-btn:hover {transform: translateY(-2px); background: #45a049;} .logout-btn {background: #ff6b6b; color: white;} .logout-btn:hover {transform: translateY(-2px); background: #ff5252;} .switch-dropdown {position: relative; display: inline-block;} .dropdown-content {display: none; position: absolute; background-color: white; min-width: 150px; box-shadow: 0 8px 16px rgba(0,0,0,0.2); z-index: 1; border-radius: 6px; top: 100%;} .dropdown-content a {color: #333; padding: 10px 16px; text-decoration: none; display: block; font-size: 12px;} .dropdown-content a:hover {background-color: #f1f1f1;} .switch-dropdown:hover .dropdown-content {display: block;} .form-section {background: #f9f9f9; padding: 25px; border-radius: 15px; margin-bottom: 20px;} .form-group {margin-bottom: 18px;} label {display: block; color: #333; font-weight: 600; margin-bottom: 8px; font-size: 14px;} input, textarea {width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 14px; transition: border-color 0.3s;} textarea {resize: vertical; min-height: 100px;} input:focus, textarea:focus {outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);} .file-input {position: relative;} .file-input input[type="file"] {display: none;} .file-button {display: inline-block; padding: 12px 20px; background: #667eea; color: white; border-radius: 10px; cursor: pointer; font-weight: 600;} .file-button:hover {background: #5568d3; transform: translateY(-2px);} .file-list {margin-top: 10px; font-size: 12px; color: #666;} .submit-btn {width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: transform 0.2s;} .submit-btn:hover {transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);}</style><script>function handleFileSelect() {const input = document.getElementById('photos'); const fileList = document.getElementById('fileList'); fileList.innerHTML = ''; if (input.files.length > 0) {fileList.innerHTML = `${input.files.length} file(s) selected`;}}</script></head><body><div class="container"><div class="header"><h1>📸 Telegram Auto Poster</h1><p class="subtitle">Post to all your groups instantly</p></div><div class="account-bar"><div class="current-account">👤 Logged in as: CURRENT_ACCOUNT</div><div class="account-buttons"><div class="switch-dropdown"><button class="switch-btn">Switch Account</button><div class="dropdown-content">ACCOUNTS_DROPDOWN</div></div><a href="/add-account" class="add-account-btn">+ Add Account</a><a href="/logout" class="logout-btn">Logout</a></div></div><form action="/send" method="post" enctype="multipart/form-data" class="form-section"><div class="form-group"><label for="caption">📝 Caption</label><textarea id="caption" name="caption" placeholder="Enter caption for your post..." required></textarea></div><div class="form-group file-input"><label class="file-button">📁 Choose Photos<input type="file" id="photos" name="photos" accept="image/*" multiple required onchange="handleFileSelect()"></label><div class="file-list" id="fileList"></div></div><button type="submit" class="submit-btn">✈️ START POSTING</button></form></div></body></html>"""

@app.get("/", response_class=HTMLResponse)
async def home():
    accounts = get_available_accounts()
    if not accounts:
        return AUTH_HTML
    
    active = get_active_session()
    if not active:
        active = accounts[0]
        set_active_session(active)
    
    dropdown_html = ""
    for account in accounts:
        dropdown_html += f'<a href="/switch-account/{account}">👤 {account}</a>'
    
    home = HOME_HTML.replace("CURRENT_ACCOUNT", active)
    home = home.replace("ACCOUNTS_DROPDOWN", dropdown_html)
    return home

@app.get("/add-account", response_class=HTMLResponse)
async def add_account():
    return AUTH_HTML

@app.post("/auth")
async def auth(phone: str = Form(...)):
    if not API_ID or not API_HASH:
        return HTMLResponse("<h3>Error: API credentials not configured</h3>")
    try:
        client = TelegramClient(str(SESSIONS_DIR / 'temp'), API_ID, API_HASH)
        await client.connect()
        result = await client.send_code_request(phone)
        await client.disconnect()
        print(f"[AUTH] Code sent to {phone}")
        html = CODE_HTML.replace("PHONE_PLACEHOLDER", phone)
        return HTMLResponse(html)
    except Exception as e:
        print(f"[AUTH ERROR] {e}")
        return HTMLResponse(f"<h3>Error: {str(e)}</h3><p><a href='/add-account'>Back</a></p>")

@app.post("/verify")
async def verify(phone: str = Form(...), code: str = Form(...), password: str = Form("")):
    if not API_ID or not API_HASH:
        return HTMLResponse("<h3>Error: API credentials not configured</h3>")
    
    session_name = phone.replace('+', '').replace(' ', '')
    session_path = SESSIONS_DIR / session_name
    
    client = TelegramClient(str(session_path), API_ID, API_HASH)
    try:
        await client.connect()
        
        code_callback = lambda: code
        password_callback = lambda: password if password.strip() else None
        
        await client.start(
            phone=phone,
            code_callback=code_callback,
            password=password_callback
        )
        
        set_active_session(session_name)
        print(f"[AUTH SUCCESS] Account authenticated: {session_name}")
        await client.disconnect()
        return HTMLResponse("<h3>✓ Authenticated Successfully!</h3><p>Redirecting...</p><script>setTimeout(() => window.location.href = '/', 2000);</script>")
    
    except Exception as e:
        print(f"[VERIFY ERROR] {type(e).__name__}: {str(e)}")
        try:
            await client.disconnect()
        except:
            pass
        return HTMLResponse(f"<h3>❌ Authentication Failed</h3><p>Error: {str(e)}</p><p><a href='/add-account'>Back to start</a></p>")

@app.get("/switch-account/{account_name}")
async def switch_account(account_name: str):
    accounts = get_available_accounts()
    if account_name in accounts:
        set_active_session(account_name)
        print(f"[SWITCH] Switched to account: {account_name}")
        return HTMLResponse("<h3>✓ Account switched!</h3><p>Redirecting...</p><script>setTimeout(() => window.location.href = '/', 1000);</script>")
    return HTMLResponse("<h3>❌ Account not found</h3><p><a href='/'>Back</a></p>")

@app.get("/logout")
async def logout():
    try:
        active = get_active_session()
        if active:
            session_file = SESSIONS_DIR / f"{active}.session"
            if session_file.exists():
                session_file.unlink()
            ACTIVE_SESSION_FILE.unlink(missing_ok=True)
            print(f"[LOGOUT] Session deleted: {active}")
    except Exception as e:
        print(f"[LOGOUT ERROR] {e}")
    return HTMLResponse("<h3>✓ Logged out successfully!</h3><p>Redirecting...</p><script>setTimeout(() => window.location.href = '/', 2000);</script>")

async def post_to_groups(photo_file_paths: list, caption: str):
    active = get_active_session()
    if not active:
        print("[ERROR] No active session!")
        return
    
    session_path = SESSIONS_DIR / active
    async with TelegramClient(str(session_path), API_ID, API_HASH) as client:
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
        
        print(f"Found {len(groups)} groups (excluding admin groups). Starting posting...")
        
        for group in groups:
            try:
                group_name = group.title if hasattr(group, 'title') else group
                await client.send_file(group, photo_file_paths, caption=caption)
                print(f"[+] Sent {len(photo_file_paths)} images to {group_name}")
                await asyncio.sleep(5)
            except Exception as e:
                if "CHAT_SEND_PHOTOS_FORBIDDEN" in str(e):
                    try:
                        await client.send_message(group, caption)
                        group_name = group.title if hasattr(group, 'title') else group
                        print(f"[+] Sent caption only to {group_name} (photos forbidden)")
                        await asyncio.sleep(5)
                    except Exception as e2:
                        print(f"[ERROR] Failed to send caption to {group}: {e2}")
                else:
                    print(f"[ERROR] Failed to send to {group}: {e}")
        
        print("[DONE] Posting completed!")

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
    
    return HTMLResponse(f"<h3>✓ Started posting {len(photo_paths)} images to all your groups!</h3><p>Posts will be sent with 5-second intervals between groups.</p><p><a href='/'>Back home</a></p>")
