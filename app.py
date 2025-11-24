import os
import asyncio
import random
import time
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# Load API credentials from environment
API_ID = int(os.getenv("API_ID", ""))
API_HASH = os.getenv("API_HASH", "")

CYCLE_DURATION = 3600  # 1 hour
SESSION_NAME = 'telegram_session'

app = FastAPI()

# HTML for home page
HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Auto Poster</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 700px;
            width: 100%;
            padding: 40px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        h1 {
            color: #333;
            font-size: 32px;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #666;
            font-size: 14px;
        }
        
        .form-group {
            margin-bottom: 30px;
        }
        
        label {
            display: block;
            color: #333;
            font-weight: 600;
            margin-bottom: 12px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        textarea {
            width: 100%;
            padding: 14px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-family: inherit;
            font-size: 14px;
            resize: vertical;
            transition: border-color 0.3s;
        }
        
        textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .file-input-wrapper {
            position: relative;
            overflow: hidden;
            display: inline-block;
            width: 100%;
        }
        
        .file-input-wrapper input[type=file] {
            position: absolute;
            left: -9999px;
        }
        
        .file-input-label {
            display: block;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            cursor: pointer;
            text-align: center;
            font-weight: 600;
            transition: transform 0.2s;
        }
        
        .file-input-label:hover {
            transform: translateY(-2px);
        }
        
        .file-list {
            margin-top: 12px;
            padding: 12px;
            background: #f5f5f5;
            border-radius: 10px;
            max-height: 150px;
            overflow-y: auto;
        }
        
        .file-item {
            color: #666;
            font-size: 13px;
            padding: 6px 0;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .file-item:last-child {
            border-bottom: none;
        }
        
        .group-instructions {
            background: #f0f4ff;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 12px;
            font-size: 13px;
            color: #555;
            border-left: 4px solid #667eea;
        }
        
        .submit-btn {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .submit-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }
        
        .submit-btn:active {
            transform: translateY(0);
        }
        
        .status-box {
            background: #e8f5e9;
            border-left: 4px solid #4caf50;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 20px;
            color: #2e7d32;
        }
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

SUCCESS_HTML_TEMPLATE = """
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
        .back-btn {{ display: inline-block; padding: 12px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; text-decoration: none; font-weight: 600; transition: transform 0.2s; }}
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
    return HOME_HTML

async def post_to_groups(photo_files: list[str], caption: str, groups: list[str]):
    if not API_ID or not API_HASH:
        print("[ERROR] API_ID or API_HASH not configured!")
        return
    
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print("[ERROR] Client not authorized. Please authenticate first.")
            await client.disconnect()
            return
        
        total_groups = len(groups)
        if total_groups == 0:
            print("No groups provided!")
            await client.disconnect()
            return

        avg_interval = CYCLE_DURATION / total_groups
        low = avg_interval * 0.7
        high = avg_interval * 1.3

        print(f"✓ Loaded {total_groups} groups with {len(photo_files)} photos. Starting posting cycle...")

        while True:
            for group in groups:
                try:
                    for idx, photo_file in enumerate(photo_files):
                        if idx == 0:
                            # Send first photo with caption
                            await client.send_file(group, photo_file, caption=caption)
                        else:
                            # Send other photos without caption
                            await client.send_file(group, photo_file)
                    
                    print(f"[+] Sent {len(photo_files)} photo(s) to {group}")

                    sleep_time = random.uniform(low, high)
                    print(f"   Waiting {int(sleep_time)} seconds...\n")
                    await asyncio.sleep(sleep_time)

                except Exception as e:
                    print(f"[ERROR sending to {group}] {e}")

            print("===== 1-HOUR CYCLE FINISHED. Starting new cycle... =====\n")
    
    except Exception as e:
        print(f"[CRITICAL ERROR] {e}")
    finally:
        await client.disconnect()

@app.post("/send")
async def send(caption: str = Form(...), groups: str = Form(...), photos: list[UploadFile] = File(...)):
    # Validate that we have credentials
    if not API_ID or not API_HASH:
        return HTMLResponse(
            "<h3 style='color: red;'>❌ Error: Telegram API credentials not configured!</h3>"
        )
    
    # Check if at least one file was provided
    if not photos or (len(photos) == 1 and photos[0].filename == ''):
        return HTMLResponse(
            "<h3 style='color: red;'>❌ Error: Please select at least one photo!</h3>"
            "<p><a href='/'>← Back to Form</a></p>"
        )
    
    # Save uploaded files temporarily
    photo_files = []
    for photo in photos:
        if photo.filename:  # Skip empty files
            photo_file_path = f"temp_{int(time.time())}_{photo.filename}"
            with open(photo_file_path, "wb") as f:
                f.write(await photo.read())
            photo_files.append(photo_file_path)

    group_list = [g.strip() for g in groups.splitlines() if g.strip()]
    
    if not group_list:
        return HTMLResponse(
            "<h3 style='color: red;'>❌ Error: Please enter at least one group link!</h3>"
            "<p><a href='/'>← Back to Form</a></p>"
        )

    # Start background task for posting
    asyncio.create_task(post_to_groups(photo_files, caption, group_list))

    return HTMLResponse(
        SUCCESS_HTML_TEMPLATE.format(
            photos_count=len(photo_files),
            groups_count=len(group_list)
        )
    )
