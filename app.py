import os
import asyncio
import random
import time
import json
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from telethon import TelegramClient

# Load API credentials from environment
API_ID = int(os.getenv("API_ID", "0"))
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

# HTML for setup page
SETUP_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Auto Poster - Setup</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .container { background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 500px; width: 100%; padding: 40px; }
        h1 { color: #333; text-align: center; margin-bottom: 30px; font-size: 28px; }
        .info { background: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; border-radius: 10px; margin-bottom: 30px; color: #1565c0; font-size: 13px; line-height: 1.6; }
        .form-group { margin-bottom: 20px; }
        label { display: block; color: #333; font-weight: 600; margin-bottom: 8px; }
        input, textarea { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 14px; font-family: inherit; }
        input:focus, textarea:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
        .btn { width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; text-transform: uppercase; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 Setup Authentication</h1>
        <div class="info">
            💡 <strong>Two ways to authenticate:</strong><br>
            1. Use your phone number (full access)<br>
            2. Use a bot token (easier, recommended)
        </div>
        
        <form action="/setup" method="post">
            <div class="form-group">
                <label>Authentication Method</label>
                <select name="method" required style="width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px;">
                    <option value="phone">📱 Phone Number</option>
                    <option value="bot">🤖 Bot Token</option>
                </select>
            </div>
            
            <div class="form-group" id="phoneInput" style="display: block;">
                <label>Phone Number (with country code)</label>
                <input type="tel" name="phone" placeholder="+1234567890">
            </div>
            
            <div class="form-group" id="botInput" style="display: none;">
                <label>Bot Token (from @BotFather)</label>
                <input type="text" name="bot_token" placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11">
            </div>
            
            <button type="submit" class="btn">Continue</button>
        </form>
    </div>
    
    <script>
        const methodSelect = document.querySelector('select[name="method"]');
        const phoneInput = document.getElementById('phoneInput');
        const botInput = document.getElementById('botInput');
        
        methodSelect.addEventListener('change', function() {
            if (this.value === 'phone') {
                phoneInput.style.display = 'block';
                botInput.style.display = 'none';
            } else {
                phoneInput.style.display = 'none';
                botInput.style.display = 'block';
            }
        });
    </script>
</body>
</html>
"""

# HTML for home page
HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Auto Poster</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .container { background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 700px; width: 100%; padding: 40px; }
        .header { text-align: center; margin-bottom: 40px; }
        h1 { color: #333; font-size: 32px; margin-bottom: 10px; }
        .subtitle { color: #666; font-size: 14px; }
        .status-box { background: #e8f5e9; border-left: 4px solid #4caf50; padding: 12px; border-radius: 10px; margin-bottom: 20px; color: #2e7d32; }
        .form-group { margin-bottom: 30px; }
        label { display: block; color: #333; font-weight: 600; margin-bottom: 12px; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }
        textarea { width: 100%; padding: 14px; border: 2px solid #e0e0e0; border-radius: 10px; font-family: inherit; font-size: 14px; resize: vertical; }
        textarea:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
        .file-input-wrapper { position: relative; overflow: hidden; display: inline-block; width: 100%; }
        .file-input-wrapper input[type=file] { position: absolute; left: -9999px; }
        .file-input-label { display: block; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; cursor: pointer; text-align: center; font-weight: 600; }
        .file-input-label:hover { transform: translateY(-2px); }
        .file-list { margin-top: 12px; padding: 12px; background: #f5f5f5; border-radius: 10px; max-height: 150px; overflow-y: auto; }
        .file-item { color: #666; font-size: 13px; padding: 6px 0; border-bottom: 1px solid #e0e0e0; }
        .file-item:last-child { border-bottom: none; }
        .group-instructions { background: #f0f4ff; padding: 12px; border-radius: 10px; margin-bottom: 12px; font-size: 13px; color: #555; border-left: 4px solid #667eea; }
        .submit-btn { width: 100%; padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; }
        .submit-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4); }
        .logout-btn { background: #ff6b6b; padding: 8px 16px; font-size: 12px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📱 Telegram Auto Poster</h1>
            <p class="subtitle">Schedule and automate your posts to multiple Telegram groups</p>
        </div>
        
        <div class="status-box">
            ✓ Authenticated and ready to post!
        </div>
        
        <form action="/send" enctype="multipart/form-data" method="post">
            <div class="form-group">
                <label>Post Caption</label>
                <textarea name="caption" rows="4" placeholder="Enter your post caption here..."></textarea>
            </div>
            
            <div class="form-group">
                <label>Upload Photos (Multiple Allowed)</label>
                <div class="file-input-wrapper">
                    <input type="file" name="photos" id="photos" multiple accept="image/*" required>
                    <label for="photos" class="file-input-label">📸 Click to select images</label>
                </div>
                <div class="file-list" id="fileList" style="display: none;"></div>
            </div>
            
            <div class="form-group">
                <label>Telegram Group Links</label>
                <div class="group-instructions">
                    ✓ Enter one group link per line<br>
                    ✓ Examples: @groupname, t.me/groupname, https://t.me/groupname
                </div>
                <textarea name="groups" rows="8" placeholder="@group1&#10;@group2&#10;https://t.me/group3&#10;..." required></textarea>
            </div>
            
            <button type="submit" class="submit-btn">🚀 Start Posting</button>
            <button type="button" class="submit-btn logout-btn" onclick="if(confirm('Log out and re-authenticate?')) window.location='/logout'">🚪 Log Out</button>
        </form>
    </div>
    
    <script>
        const fileInput = document.getElementById('photos');
        const fileList = document.getElementById('fileList');
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                fileList.style.display = 'block';
                fileList.innerHTML = '';
                for (let file of this.files) {
                    const item = document.createElement('div');
                    item.className = 'file-item';
                    item.textContent = '✓ ' + file.name + ' (' + (file.size / 1024).toFixed(2) + ' KB)';
                    fileList.appendChild(item);
                }
            } else {
                fileList.style.display = 'none';
            }
        });
    </script>
</body>
</html>
"""

SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Posting Started</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }}
        .container {{ background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 700px; width: 100%; padding: 40px; text-align: center; }}
        .success {{ color: #4caf50; font-size: 48px; margin-bottom: 20px; }}
        h2 {{ color: #333; margin-bottom: 20px; }}
        .details {{ color: #666; font-size: 16px; line-height: 1.8; margin-bottom: 30px; }}
        .back-btn {{ display: inline-block; padding: 12px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; text-decoration: none; font-weight: 600; }}
        .back-btn:hover {{ transform: translateY(-2px); }}
    </style>
</head>
<body>
    <div class="container">
        <div class="success">✓</div>
        <h2>Posting Started!</h2>
        <div class="details">
            <p>📊 <strong>{photos_count}</strong> photo(s) will be sent</p>
            <p>📍 To <strong>{groups_count}</strong> group(s)</p>
            <p>⏱️ On a <strong>1-hour cycle</strong></p>
            <p style="margin-top: 20px; font-size: 14px; color: #999;">The app will now post automatically. You can close this page.</p>
        </div>
        <a href="/" class="back-btn">← Back to Home</a>
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    creds = load_credentials()
    if not creds:
        return SETUP_HTML
    return HOME_HTML

@app.post("/setup")
async def setup(method: str = Form(...), phone: str = Form(None), bot_token: str = Form(None)):
    """Handle initial setup"""
    if not API_ID or not API_HASH:
        return HTMLResponse("<h3>Error: API credentials not configured</h3>")
    
    if method == "phone" and phone:
        try:
            client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
            await client.connect()
            result = await client.send_code_request(phone)
            print(f"[AUTH] Code sent to {phone}")
            
            # Save for verification step
            save_credentials(phone, result.phone_code_hash)
            
            # Show verification form
            return HTMLResponse(f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Verify Code</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                        body {{ font-family: 'Segoe UI'; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }}
                        .container {{ background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 500px; width: 100%; padding: 40px; }}
                        h1 {{ text-align: center; color: #333; margin-bottom: 30px; }}
                        .form-group {{ margin-bottom: 20px; }}
                        label {{ display: block; color: #333; font-weight: 600; margin-bottom: 8px; }}
                        input {{ width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px; }}
                        .btn {{ width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; }}
                        .btn:hover {{ transform: translateY(-2px); }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>✓ Code Sent!</h1>
                        <p style="text-align: center; color: #666; margin-bottom: 30px;">Check your Telegram app for the code</p>
                        <form action="/verify-phone" method="post">
                            <div class="form-group">
                                <label>Verification Code</label>
                                <input type="text" name="code" placeholder="12345" required>
                            </div>
                            <button type="submit" class="btn">✓ Verify</button>
                        </form>
                    </div>
                </body>
                </html>
            """)
        except Exception as e:
            print(f"[ERROR] {e}")
            return HTMLResponse(f"<h3>Error: {str(e)}</h3><p><a href='/'>Back</a></p>")
    
    return HTMLResponse("<h3>Error: Invalid input</h3><p><a href='/'>Back</a></p>")

@app.post("/verify-phone")
async def verify_phone(code: str = Form(...)):
    """Verify phone code"""
    creds = load_credentials()
    if not creds:
        return HTMLResponse("<h3>Error: No authentication session</h3><p><a href='/'>Back</a></p>")
    
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        user = await client.sign_in(creds['phone'], code, phone_code_hash=creds['code_hash'])
        await client.disconnect()
        
        print(f"[AUTH SUCCESS] User authenticated: {user.first_name}")
        
        return HTMLResponse("""
            <html>
            <body style="font-family: Segoe UI; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; justify-content: center; align-items: center; min-height: 100vh;">
                <div style="background: white; padding: 40px; border-radius: 20px; text-align: center; max-width: 500px;">
                    <h1 style="color: #4caf50; font-size: 48px;">✓</h1>
                    <h2 style="color: #333; margin: 20px 0;">Authentication Successful!</h2>
                    <p style="color: #666;">Redirecting to your dashboard...</p>
                    <script>setTimeout(() => window.location.href = '/', 2000);</script>
                </div>
            </body>
            </html>
        """)
    except Exception as e:
        print(f"[VERIFY ERROR] {e}")
        return HTMLResponse(f"<h3>Error: Invalid code - {str(e)}</h3><p><a href='/'>Back</a></p>")

@app.get("/logout")
async def logout():
    """Clear session"""
    if os.path.exists(CREDENTIALS_FILE):
        os.remove(CREDENTIALS_FILE)
    if os.path.exists(f'{SESSION_NAME}.session'):
        os.remove(f'{SESSION_NAME}.session')
    
    return HTMLResponse("""
        <html>
        <body style="font-family: Segoe UI; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; justify-content: center; align-items: center; min-height: 100vh;">
            <div style="background: white; padding: 40px; border-radius: 20px; text-align: center;">
                <h2 style="color: #333; margin-bottom: 20px;">Logged out</h2>
                <p>Redirecting...</p>
                <script>setTimeout(() => window.location.href = '/', 2000);</script>
            </div>
        </body>
        </html>
    """)

async def post_to_groups(photo_files: list[str], caption: str, groups: list[str]):
    """Post to groups"""
    if not API_ID or not API_HASH:
        print("[ERROR] API_ID or API_HASH not configured!")
        return
    
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print("[ERROR] Not authorized - please authenticate first")
            await client.disconnect()
            return
        
        print(f"✓ Connected! Posting {len(photo_files)} photo(s) to {len(groups)} group(s)...")
        
        avg_interval = CYCLE_DURATION / len(groups)
        low = avg_interval * 0.7
        high = avg_interval * 1.3
        
        while True:
            for group in groups:
                try:
                    for idx, photo in enumerate(photo_files):
                        if idx == 0:
                            await client.send_file(group, photo, caption=caption)
                        else:
                            await client.send_file(group, photo)
                    
                    print(f"[+] Sent {len(photo_files)} photo(s) to {group}")
                    
                    sleep_time = random.uniform(low, high)
                    await asyncio.sleep(sleep_time)
                
                except Exception as e:
                    print(f"[ERROR] Failed to send to {group}: {e}")
            
            print("===== 1-HOUR CYCLE COMPLETED. Restarting... =====\n")
    
    except Exception as e:
        print(f"[CRITICAL ERROR] {e}")
    finally:
        await client.disconnect()

@app.post("/send")
async def send(caption: str = Form(...), groups: str = Form(...), photos: list[UploadFile] = File(...)):
    """Send posts"""
    creds = load_credentials()
    if not creds:
        return HTMLResponse("<h3>❌ Not authenticated!</h3><p><a href='/'>Authenticate First</a></p>")
    
    if not photos or (len(photos) == 1 and not photos[0].filename):
        return HTMLResponse("<h3>❌ Select at least one photo!</h3><p><a href='/'>Back</a></p>")
    
    photo_files = []
    for photo in photos:
        if photo.filename:
            path = f"temp_{int(time.time())}_{photo.filename}"
            with open(path, "wb") as f:
                f.write(await photo.read())
            photo_files.append(path)
    
    group_list = [g.strip() for g in groups.splitlines() if g.strip()]
    
    if not group_list:
        return HTMLResponse("<h3>❌ Enter at least one group!</h3><p><a href='/'>Back</a></p>")
    
    asyncio.create_task(post_to_groups(photo_files, caption, group_list))
    
    return HTMLResponse(SUCCESS_HTML.format(
        photos_count=len(photo_files),
        groups_count=len(group_list)
    ))
