import os
import asyncio
import time
import json
import pathlib
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from telethon import TelegramClient

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

ACCOUNTS_FILE = pathlib.Path('accounts.json')
SESSIONS_DIR = pathlib.Path('sessions')
SESSIONS_DIR.mkdir(exist_ok=True)

app = FastAPI()

# Track posting tasks per account
posting_tasks = {}

def load_accounts():
    if ACCOUNTS_FILE.exists():
        with open(ACCOUNTS_FILE, 'r') as f:
            return json.load(f)
    return {"accounts": [], "active": None}

def save_accounts(data):
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_session_path(phone):
    return SESSIONS_DIR / f'session_{phone}'

def get_active_session():
    accounts = load_accounts()
    if accounts["active"]:
        return accounts["active"]
    return None

AUTH_HTML = """<!DOCTYPE html><html><head><title>Telegram Authentication</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>* {margin: 0; padding: 0; box-sizing: border-box;} body {font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;} .container {background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 500px; width: 100%; padding: 40px;} .header {text-align: center; margin-bottom: 40px;} h1 {color: #333; font-size: 28px; margin-bottom: 10px;} .subtitle {color: #666; font-size: 14px;} .info-box {background: #e3f2fd; border-left: 4px solid #2196f3; padding: 12px; border-radius: 10px; margin-bottom: 30px; color: #1565c0; font-size: 13px; line-height: 1.6;} .form-group {margin-bottom: 20px;} label {display: block; color: #333; font-weight: 600; margin-bottom: 8px; font-size: 14px;} input {width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 14px; transition: border-color 0.3s;} input:focus {outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);} .submit-btn {width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: transform 0.2s;} .submit-btn:hover {transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);} .steps {background: #f5f5f5; padding: 15px; border-radius: 10px; font-size: 13px; color: #666; line-height: 1.8; margin-top: 30px;} .step {margin-bottom: 10px;}</style></head><body><div class="container"><div class="header"><h1>🔐 Authenticate with Telegram</h1><p class="subtitle">One-time setup required</p></div><div class="info-box">⚠️ You need to authenticate with your Telegram account to use this app.</div><form action="/auth" method="post"><div class="form-group"><label>Phone Number (with country code, e.g., +1234567890):</label><input type="text" name="phone" placeholder="+1234567890" required></div><button type="submit" class="submit-btn">Send Code</button></form></div></body></html>"""

CODE_HTML = """<!DOCTYPE html><html><head><title>Verify Code</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>* {margin: 0; padding: 0; box-sizing: border-box;} body {font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;} .container {background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 500px; width: 100%; padding: 40px;} h1 {color: #333; font-size: 24px; margin-bottom: 10px; text-align: center;} .subtitle {color: #666; font-size: 14px; text-align: center; margin-bottom: 30px;} .form-group {margin-bottom: 20px;} label {display: block; color: #333; font-weight: 600; margin-bottom: 8px; font-size: 14px;} input {width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 14px; transition: border-color 0.3s;} input:focus {outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);} .submit-btn {width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: transform 0.2s;} .submit-btn:hover {transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);} .info {background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; border-radius: 10px; color: #856404; font-size: 13px; margin-bottom: 20px;}</style></head><body><div class="container"><h1>✓ Code Sent!</h1><p class="subtitle">Check your Telegram app for the verification code</p><div class="info">📨 Enter the code below. If you have 2FA enabled, you'll need your password too.</div><form action="/verify" method="post"><input type="hidden" name="phone" value="PHONE_PLACEHOLDER"><div class="form-group"><label>Verification Code:</label><input type="text" name="code" placeholder="12345" required></div><div class="form-group"><label>Password (if 2FA enabled, leave blank otherwise):</label><input type="password" name="password" placeholder=""></div><button type="submit" class="submit-btn">Verify & Login</button></form></div></body></html>"""

def get_accounts_html():
    accounts = load_accounts()
    accounts_list = accounts.get("accounts", [])
    active = accounts.get("active")
    
    accounts_html = ""
    for phone in accounts_list:
        status = "✅ ACTIVE" if phone == active else "Switch"
        button_html = "" if phone == active else f'<a href="/switch/{phone}" style="margin-left: 10px; padding: 6px 12px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; font-size: 12px;">Switch</a>'
        accounts_html += f'<div style="padding: 10px; background: #f5f5f5; margin: 5px 0; border-radius: 5px; display: flex; justify-content: space-between; align-items: center;"><span>{phone} - {status}</span>{button_html}</div>'
    
    return accounts_html if accounts_html else "<p style='color: #666;'>No accounts yet</p>"

def get_home_html():
    accounts_html = get_accounts_html()
    return f"""<!DOCTYPE html><html><head><title>Telegram Auto Poster</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>* {{margin: 0; padding: 0; box-sizing: border-box;}} body {{font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;}} .container {{background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 700px; width: 100%; padding: 40px;}} .header {{text-align: center; margin-bottom: 40px;}} h1 {{color: #333; font-size: 32px; margin-bottom: 10px;}} .subtitle {{color: #666; font-size: 14px;}} .accounts-section {{background: #f9f9f9; padding: 20px; border-radius: 15px; margin-bottom: 30px; border: 2px solid #e0e0e0;}} .accounts-section h2 {{color: #333; font-size: 16px; margin-bottom: 15px;}} .form-group {{margin-bottom: 30px;}} label {{display: block; color: #333; font-weight: 600; margin-bottom: 12px; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;}} textarea {{width: 100%; padding: 14px; border: 2px solid #e0e0e0; border-radius: 10px; font-family: inherit; font-size: 14px; resize: vertical; transition: border-color 0.3s;}} textarea:focus {{outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);}} .file-input-wrapper {{position: relative; overflow: hidden; display: inline-block; width: 100%;}} .file-input-wrapper input[type=file] {{position: absolute; left: -9999px;}} .file-input-label {{display: block; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; cursor: pointer; text-align: center; font-weight: 600; transition: transform 0.2s;}} .file-input-label:hover {{transform: translateY(-2px);}} .file-list {{margin-top: 12px; padding: 12px; background: #f5f5f5; border-radius: 10px; max-height: 150px; overflow-y: auto;}} .file-item {{color: #666; font-size: 13px; padding: 6px 0; border-bottom: 1px solid #e0e0e0;}} .file-item:last-child {{border-bottom: none;}} .submit-btn {{width: 100%; padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: transform 0.2s;}} .submit-btn:hover {{transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);}} .add-account-btn {{display: inline-block; padding: 12px 24px; background: #28a745; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; transition: transform 0.2s;}} .add-account-btn:hover {{transform: translateY(-2px);}} .active-badge {{display: inline-block; padding: 4px 8px; background: #667eea; color: white; border-radius: 4px; font-size: 11px; margin-top: 10px;}}</style></head><body><div class="container"><div class="header"><h1>📱 Telegram Auto Poster</h1><p class="subtitle">Multi-Account Support</p></div><div class="accounts-section"><h2>👤 Your Accounts</h2>{accounts_html}<a href="/add-account" class="add-account-btn" style="margin-top: 15px;">+ Add New Account</a></div><div class="form-group"><label>📝 Caption:</label><textarea name="caption" placeholder="Write your caption here..." required></textarea></div><form action="/send" method="post" enctype="multipart/form-data"><input type="hidden" name="caption" id="caption"><div class="form-group"><label>📸 Select Photos:</label><div class="file-input-wrapper"><label for="photos" class="file-input-label">Choose Files (select multiple)</label><input type="file" id="photos" name="photos" accept="image/*" multiple required onchange="updateFileList()"></div><div class="file-list" id="file-list"></div></div><button type="submit" class="submit-btn">🚀 Start Posting</button></form><script>function updateFileList() {{ const files = document.getElementById('photos').files; const fileList = document.getElementById('file-list'); fileList.innerHTML = ''; if (files.length === 0) return; for (let i = 0; i < files.length; i++) {{ const item = document.createElement('div'); item.className = 'file-item'; item.textContent = (i+1) + '. ' + files[i].name; fileList.appendChild(item); }} }} document.querySelector('form').onsubmit = function() {{ document.getElementById('caption').value = document.querySelector('textarea[name=caption]').value; }}</script></div></body></html>"""

@app.get("/", response_class=HTMLResponse)
async def home():
    accounts = load_accounts()
    if not accounts["accounts"]:
        return AUTH_HTML
    active_phone = accounts.get("active")
    if active_phone and active_phone in posting_tasks and posting_tasks[active_phone] is not None and not posting_tasks[active_phone].done():
        status_html = f"""<!DOCTYPE html><html><head><title>Posting Status</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>* {{margin: 0; padding: 0; box-sizing: border-box;}} body {{font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;}} .container {{background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 600px; width: 100%; padding: 40px; text-align: center;}} .header {{margin-bottom: 30px;}} .icon {{font-size: 60px; margin-bottom: 20px; animation: pulse 1s infinite;}} @keyframes pulse {{0%, 100% {{opacity: 1;}} 50% {{opacity: 0.6;}}}} h1 {{color: #667eea; font-size: 28px; margin-bottom: 10px;}} .status-info {{background: #f0f4ff; border-left: 4px solid #667eea; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: left;}} .status-item {{color: #333; font-size: 14px; margin: 10px 0;}} .button-group {{display: flex; gap: 15px; margin-top: 30px; justify-content: center; flex-wrap: wrap;}} .btn {{padding: 14px 24px; border: none; border-radius: 10px; font-size: 14px; font-weight: 600; text-decoration: none; cursor: pointer; transition: transform 0.2s;}} .btn-stop {{background: #ff6b6b; color: white;}} .btn-stop:hover {{transform: translateY(-2px);}} .btn-back {{background: #667eea; color: white;}} .btn-back:hover {{transform: translateY(-2px);}}</style></head><body><div class="container"><div class="header"><div class="icon">🚀</div><h1>✓ Posting In Progress</h1></div><div class="status-info"><div class="status-item"><strong>📱 Account:</strong> {active_phone}</div><div class="status-item"><strong>⏱️ Status:</strong> Currently posting to your groups</div><div class="status-item"><strong>⏱️ Interval:</strong> 5 seconds between groups</div><div class="status-item"><strong>🔄 Cycle:</strong> 10 minutes wait between cycles</div></div><div class="button-group"><a href="/" class="btn btn-back">🔄 Refresh Status</a><a href="/stop" class="btn btn-stop">⏹️ Stop Posting</a></div></div></body></html>"""
        return status_html
    return get_home_html()

@app.get("/add-account", response_class=HTMLResponse)
async def add_account():
    return AUTH_HTML

@app.post("/auth")
async def auth(phone: str = Form(...)):
    if not API_ID or not API_HASH:
        return HTMLResponse("<h3>Error: API credentials not configured</h3>")
    try:
        session_path = str(get_session_path(phone))
        client = TelegramClient(session_path, API_ID, API_HASH)
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
    
    session_path = str(get_session_path(phone))
    client = TelegramClient(session_path, API_ID, API_HASH)
    try:
        await client.connect()
        
        code_callback = lambda: code
        password_callback = lambda: password if password.strip() else None
        
        await client.start(
            phone=phone,
            code_callback=code_callback,
            password=password_callback
        )
        
        accounts = load_accounts()
        if phone not in accounts["accounts"]:
            accounts["accounts"].append(phone)
        accounts["active"] = phone
        save_accounts(accounts)
        
        print(f"[AUTH SUCCESS] Account {phone} authenticated")
        await client.disconnect()
        return HTMLResponse("<h3>✓ Authenticated Successfully!</h3><p>Redirecting...</p><script>setTimeout(() => window.location.href = '/', 2000);</script>")
    
    except Exception as e:
        print(f"[VERIFY ERROR] {type(e).__name__}: {str(e)}")
        try:
            await client.disconnect()
        except:
            pass
        return HTMLResponse(f"<h3>❌ Authentication Failed</h3><p>Error: {str(e)}</p><p><a href='/'>Back to start</a></p>")

@app.get("/switch/{phone}", response_class=HTMLResponse)
async def switch_account(phone: str):
    accounts = load_accounts()
    if phone in accounts["accounts"]:
        accounts["active"] = phone
        save_accounts(accounts)
        print(f"[SWITCH] Switched to account {phone}")
        return HTMLResponse(f"<h3>✓ Switched to {phone}</h3><p>Redirecting...</p><script>setTimeout(() => window.location.href = '/', 2000);</script>")
    return HTMLResponse("<h3>Error: Account not found</h3><p><a href='/'>Back</a></p>")

async def post_to_groups(photo_file_paths: list, caption: str, active_phone: str):
    session_path = str(get_session_path(active_phone))
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
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
            print(f"[{active_phone}] [ERROR] No groups found!")
            return
        
        print(f"[{active_phone}] Found {len(groups)} groups (excluding admin groups). Starting posting cycle...")
        
        last_message_ids = {}
        
        while True:
            # Check if task was cancelled
            if active_phone not in posting_tasks or posting_tasks[active_phone] is None:
                print(f"[{active_phone}] Posting stopped by user")
                break
            
            for group in groups:
                # Check if task was cancelled
                if active_phone not in posting_tasks or posting_tasks[active_phone] is None:
                    print(f"[{active_phone}] Posting stopped by user")
                    break
                
                try:
                    group_name = group.title if hasattr(group, 'title') else group
                    
                    if group.id in last_message_ids:
                        try:
                            messages = await client.get_messages(group, limit=1)
                            if messages:
                                latest_msg_id = messages[0].id
                                if latest_msg_id <= last_message_ids[group.id]:
                                    print(f"[{active_phone}] [-] Skipped {group_name} (no new messages since last post)")
                                    await asyncio.sleep(5)
                                    continue
                        except Exception as e:
                            print(f"[{active_phone}] [WARNING] Could not check messages in {group_name}: {e}")
                    
                    await client.send_file(group, photo_file_paths, caption=caption)
                    
                    try:
                        messages = await client.get_messages(group, limit=1)
                        if messages:
                            last_message_ids[group.id] = messages[0].id
                    except:
                        pass
                    
                    print(f"[{active_phone}] [+] Sent {len(photo_file_paths)} images to {group_name}")
                    await asyncio.sleep(5)
                except Exception as e:
                    if "CHAT_SEND_PHOTOS_FORBIDDEN" in str(e):
                        try:
                            await client.send_message(group, caption)
                            
                            try:
                                messages = await client.get_messages(group, limit=1)
                                if messages:
                                    last_message_ids[group.id] = messages[0].id
                            except:
                                pass
                            
                            group_name = group.title if hasattr(group, 'title') else group
                            print(f"[{active_phone}] [+] Sent caption only to {group_name} (photos forbidden)")
                            await asyncio.sleep(5)
                        except Exception as e2:
                            print(f"[{active_phone}] [ERROR] Failed to send caption to {group}: {e2}")
                    else:
                        print(f"[{active_phone}] [ERROR] Failed to send to {group}: {e}")
            
            if active_phone in posting_tasks and posting_tasks[active_phone] is not None:
                print(f"[{active_phone}] ===== Cycle completed. Waiting 10 minutes before next cycle... =====")
                await asyncio.sleep(600)
        
        if active_phone in posting_tasks:
            del posting_tasks[active_phone]

@app.post("/send")
async def send(caption: str = Form(...), photos: list[UploadFile] = File(...)):
    active_phone = get_active_session()
    if not active_phone:
        return HTMLResponse("<h3>Error: No active account selected</h3><p><a href='/'>Back</a></p>")
    
    photo_paths = []
    timestamp = int(time.time())
    
    for i, photo in enumerate(photos):
        photo_path = f"temp_{timestamp}_{i}_{photo.filename}"
        with open(photo_path, "wb") as f:
            f.write(await photo.read())
        photo_paths.append(photo_path)
    
    import asyncio as aio
    task = aio.create_task(post_to_groups(photo_paths, caption, active_phone))
    posting_tasks[active_phone] = task
    
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Posting Started</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>* {{margin: 0; padding: 0; box-sizing: border-box;}} body {{font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;}} .container {{background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 600px; width: 100%; padding: 40px; text-align: center;}} .header {{margin-bottom: 30px;}} .success-icon {{font-size: 60px; margin-bottom: 20px; animation: pulse 1s infinite;}} @keyframes pulse {{0%, 100% {{opacity: 1;}} 50% {{opacity: 0.6;}}}} h1 {{color: #667eea; font-size: 28px; margin-bottom: 10px;}} .subtitle {{color: #666; font-size: 14px; margin-bottom: 30px;}} .info-box {{background: #f0f4ff; border-left: 4px solid #667eea; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: left;}} .info-item {{color: #333; font-size: 14px; margin: 10px 0; line-height: 1.6;}} .info-label {{font-weight: 600; color: #667eea;}} .button-group {{display: flex; gap: 15px; margin-top: 30px; flex-wrap: wrap; justify-content: center;}} .btn {{padding: 14px 24px; border: none; border-radius: 10px; font-size: 14px; font-weight: 600; text-decoration: none; cursor: pointer; transition: transform 0.2s;}} .btn-home {{background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;}} .btn-home:hover {{transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);}} .btn-stop {{background: #ff6b6b; color: white;}} .btn-stop:hover {{transform: translateY(-2px); box-shadow: 0 10px 30px rgba(255, 107, 107, 0.4);}} .status {{font-size: 12px; color: #999; margin-top: 20px;}}</style></head><body><div class="container"><div class="header"><div class="success-icon">🚀</div><h1>✓ Posting Started!</h1><p class="subtitle">Your images are being posted to all groups</p></div><div class="info-box"><div class="info-item"><span class="info-label">📸 Images:</span> {len(photo_paths)}</div><div class="info-item"><span class="info-label">👤 Account:</span> {active_phone}</div><div class="info-item"><span class="info-label">⏱️ Interval:</span> 5 seconds between groups</div><div class="info-item"><span class="info-label">🔄 Cycle Wait:</span> 10 minutes</div><div class="info-item"><span class="info-label">📝 Caption:</span> {caption[:50]}...</div></div><div class="button-group"><a href="/" class="btn btn-home">← Back Home</a><a href="/stop" class="btn btn-stop">⏹️ Stop Posting</a></div><div class="status">Check your Telegram groups - posts are coming in real-time!</div></div></body></html>""")

@app.get("/stop")
async def stop_posting():
    active_phone = get_active_session()
    if active_phone and active_phone in posting_tasks:
        task = posting_tasks[active_phone]
        if task:
            task.cancel()
            posting_tasks[active_phone] = None
            print(f"[{active_phone}] Posting stopped by user")
        return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Posting Stopped</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>* {{margin: 0; padding: 0; box-sizing: border-box;}} body {{font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;}} .container {{background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 600px; width: 100%; padding: 40px; text-align: center;}} h1 {{color: #ff6b6b; font-size: 28px; margin-bottom: 20px;}} p {{color: #666; font-size: 14px; margin: 15px 0;}} .btn {{display: inline-block; padding: 14px 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 10px; font-weight: 600; margin-top: 20px; transition: transform 0.2s;}} .btn:hover {{transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);}}</style></head><body><div class="container"><h1>⏹️ Posting Stopped</h1><p>Posting for {active_phone} has been cancelled</p><p style="color: #999; font-size: 12px;">Current cycle will be stopped immediately</p><a href="/" class="btn">← Back Home</a></div></body></html>""")
    return HTMLResponse("<h3>Error: No active posting</h3><p><a href='/'>Back</a></p>")
