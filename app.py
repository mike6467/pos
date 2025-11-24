import os
import asyncio
import random
import time
import aiohttp
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse

# Bot token from Telegram BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

CYCLE_DURATION = 3600  # 1 hour

app = FastAPI()

SETUP_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Auto Poster - Setup</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .container { background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); max-width: 600px; width: 100%; padding: 40px; }
        h1 { color: #333; text-align: center; margin-bottom: 10px; font-size: 28px; }
        .subtitle { text-align: center; color: #666; margin-bottom: 30px; }
        .info-box { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; border-radius: 10px; margin-bottom: 30px; color: #856404; font-size: 13px; line-height: 1.7; }
        .form-group { margin-bottom: 20px; }
        label { display: block; color: #333; font-weight: 600; margin-bottom: 8px; font-size: 14px; }
        input { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 14px; font-family: inherit; }
        input:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
        .btn { width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; text-transform: uppercase; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4); }
        .steps { background: #f5f5f5; padding: 20px; border-radius: 10px; margin-top: 30px; font-size: 13px; color: #555; line-height: 1.8; }
        .step { margin-bottom: 12px; }
        code { background: #e0e0e0; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Add Bot Token</h1>
        <p class="subtitle">Quick setup with Telegram Bot API</p>
        
        <div class="info-box">
            ⚠️ <strong>No authentication needed!</strong> Just use a bot token from @BotFather
        </div>
        
        <form action="/setup" method="post">
            <div class="form-group">
                <label>Telegram Bot Token</label>
                <input type="text" name="bot_token" placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11" required>
            </div>
            
            <button type="submit" class="btn">✓ Set Token</button>
        </form>
        
        <div class="steps">
            <strong>How to get a bot token:</strong>
            <div class="step">
                1️⃣ Open Telegram and search for <code>@BotFather</code>
            </div>
            <div class="step">
                2️⃣ Send <code>/newbot</code> and follow the steps
            </div>
            <div class="step">
                3️⃣ Copy the token and paste it above
            </div>
            <div class="step">
                4️⃣ Add your bot to your groups with admin permissions
            </div>
            <div class="step">
                5️⃣ Done! Start posting automatically
            </div>
        </div>
    </div>
</body>
</html>
"""

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
        .status-box { background: #e8f5e9; border-left: 4px solid #4caf50; padding: 12px; border-radius: 10px; margin-bottom: 20px; color: #2e7d32; font-size: 13px; }
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
        .btn { width: 100%; padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4); }
        .btn-secondary { background: #ff6b6b; font-size: 13px; padding: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📱 Telegram Auto Poster</h1>
            <p class="subtitle">Schedule and automate your posts to multiple Telegram groups</p>
        </div>
        
        <div class="status-box">
            ✓ Bot connected and ready to post!
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
                    ✓ Enter one group ID or username per line<br>
                    ✓ Examples: @groupname, -1001234567890, https://t.me/groupname
                </div>
                <textarea name="groups" rows="8" placeholder="@group1&#10;@group2&#10;-1001234567890&#10;..." required></textarea>
            </div>
            
            <button type="submit" class="btn">🚀 Start Posting</button>
            <button type="button" class="btn btn-secondary" onclick="if(confirm('Remove bot token?')) window.location='/logout'">🚪 Remove Token</button>
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
        body {{ font-family: 'Segoe UI'; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }}
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

def get_bot_token():
    return os.getenv("BOT_TOKEN", "").strip()

@app.get("/", response_class=HTMLResponse)
async def home():
    if not get_bot_token():
        return SETUP_HTML
    return HOME_HTML

@app.post("/setup")
async def setup(bot_token: str = Form(...)):
    """Save bot token"""
    if not bot_token:
        return HTMLResponse("<h3>Error: Bot token required</h3><p><a href='/'>Back</a></p>")
    
    # Test the token by getting bot info
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"https://api.telegram.org/bot{bot_token}/getMe") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        # Token is valid - save it
                        with open(".env.local", "w") as f:
                            f.write(f"BOT_TOKEN={bot_token}\n")
                        os.environ["BOT_TOKEN"] = bot_token
                        
                        bot_name = data["result"].get("username", "Bot")
                        return HTMLResponse(f"""
                            <html>
                            <body style="font-family: Segoe UI; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; justify-content: center; align-items: center; min-height: 100vh;">
                                <div style="background: white; padding: 40px; border-radius: 20px; text-align: center;">
                                    <h1 style="color: #4caf50; font-size: 48px;">✓</h1>
                                    <h2 style="color: #333;">Token Saved!</h2>
                                    <p style="color: #666;">Bot: @{bot_name}</p>
                                    <p style="margin-top: 20px;">Redirecting...</p>
                                    <script>setTimeout(() => window.location.href = '/', 2000);</script>
                                </div>
                            </body>
                            </html>
                        """)
        except Exception as e:
            print(f"[ERROR] {e}")
    
    return HTMLResponse(f"<h3>Error: Invalid bot token</h3><p><a href='/'>Back</a></p>")

@app.get("/logout")
async def logout():
    """Remove bot token"""
    if os.path.exists(".env.local"):
        os.remove(".env.local")
    os.environ.pop("BOT_TOKEN", None)
    
    return HTMLResponse("""
        <html>
        <body style="font-family: Segoe UI; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; justify-content: center; align-items: center; min-height: 100vh;">
            <div style="background: white; padding: 40px; border-radius: 20px; text-align: center;">
                <h2 style="color: #333;">Token Removed</h2>
                <p>Redirecting...</p>
                <script>setTimeout(() => window.location.href = '/', 2000);</script>
            </div>
        </body>
        </html>
    """)

async def post_to_groups(photo_files: list[str], caption: str, groups: list[str]):
    """Post to groups using Telegram Bot API"""
    bot_token = get_bot_token()
    if not bot_token:
        print("[ERROR] No bot token")
        return
    
    total_groups = len(groups)
    if total_groups == 0:
        print("No groups provided!")
        return
    
    avg_interval = CYCLE_DURATION / total_groups
    low = avg_interval * 0.7
    high = avg_interval * 1.3
    
    print(f"✓ Starting posting cycle: {len(photo_files)} photo(s) to {total_groups} group(s)")
    
    api_url = f"https://api.telegram.org/bot{bot_token}"
    
    while True:
        for group in groups:
            try:
                async with aiohttp.ClientSession() as session:
                    for idx, photo_file in enumerate(photo_files):
                        # Read photo file
                        with open(photo_file, 'rb') as f:
                            photo_data = f.read()
                        
                        # Prepare form data
                        data = aiohttp.FormData()
                        data.add_field('chat_id', group)
                        data.add_field('photo', photo_data, filename=photo_file)
                        
                        if idx == 0 and caption:
                            data.add_field('caption', caption)
                        
                        # Send photo
                        async with session.post(f"{api_url}/sendPhoto", data=data) as resp:
                            result = await resp.json()
                            if not result.get("ok"):
                                print(f"[ERROR] {group}: {result.get('description', 'Unknown error')}")
                            else:
                                print(f"[+] Sent photo {idx+1}/{len(photo_files)} to {group}")
                        
                        await asyncio.sleep(0.5)  # Avoid rate limits
                
                sleep_time = random.uniform(low, high)
                print(f"   Waiting {int(sleep_time)} seconds...\n")
                await asyncio.sleep(sleep_time)
            
            except Exception as e:
                print(f"[ERROR] Failed to send to {group}: {e}")
        
        print("===== 1-HOUR CYCLE FINISHED. Starting new cycle... =====\n")

@app.post("/send")
async def send(caption: str = Form(...), groups: str = Form(...), photos: list[UploadFile] = File(...)):
    """Start posting"""
    bot_token = get_bot_token()
    if not bot_token:
        return HTMLResponse("<h3>❌ Bot token not set!</h3><p><a href='/'>Setup First</a></p>")
    
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
    
    # Start posting in background
    asyncio.create_task(post_to_groups(photo_files, caption, group_list))
    
    return HTMLResponse(SUCCESS_HTML.format(
        photos_count=len(photo_files),
        groups_count=len(group_list)
    ))
