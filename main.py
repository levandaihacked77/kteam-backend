import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sqlite3

app = FastAPI(title="K-Team Exam Pro Dashboard")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

DB_NAME = "exam_production.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            machine_guid TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO licenses (key, machine_guid) VALUES ('KTEAM-2026-SECRET', '41c0b179-ee0f-44d4-83af-6639a50a555a')")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            content TEXT,
            time TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class LicenseRequest(BaseModel):
    key: str
    machineGuid: str

class MessageRequest(BaseModel):
    content: str

# 1. Giao diện Dashboard Web Pro y hệt mẫu
@app.get("/", response_class=HTMLResponse)
def dashboard():
    images = []
    if os.path.exists(UPLOAD_DIR):
        images = sorted(os.listdir(UPLOAD_DIR), reverse=True)
    
    # Lấy lịch sử chat
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT sender, content, time FROM messages ORDER BY id DESC LIMIT 20")
    msgs = cursor.fetchall()
    conn.close()

    chat_html = ""
    for m in reversed(msgs):
        bg = "#333" if m[0] == "admin" else "#222"
        chat_html += f"""
        <div style="background: {bg}; padding: 8px 12px; border-radius: 8px; margin-bottom: 8px; font-size: 13px;">
            <b style="color: #4CAF50;">{m[0]}:</b> {m[1]}
            <div style="font-size: 10px; color: #888; text-align: right; margin-top: 2px;">{m[2]}</div>
        </div>
        """

    latest_img = f"/uploads/{images[0]}" if images else "https://via.placeholder.com/600x400?text=Chua+co+anh+chup+man+hinh"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <title>K-Team Exam Support Pro</title>
        <meta http-equiv="refresh" content="5">
        <style>
            * {{ box-sizing: border-box; }}
            body {{ font-family: Arial, sans-serif; background: #0f0f0f; color: #e0e0e0; margin: 0; padding: 10px; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }}
            .top-bar {{ display: flex; justify-content: space-between; align-items: background: #1a1a1a; padding: 8px 15px; border-radius: 6px; background: #1a1a1a; margin-bottom: 10px; border: 1px solid #333; }}
            .main-container {{ display: flex; flex: 1; gap: 10px; overflow: hidden; }}
            
            /* Cột trái: Chat */
            .left-panel {{ width: 280px; background: #181818; border-radius: 8px; display: flex; flex-direction: column; border: 1px solid #333; padding: 10px; }}
            .chat-box {{ flex: 1; overflow-y: auto; margin-bottom: 10px; padding-right: 5px; }}
            .chat-input-area {{ display: flex; gap: 5px; }}
            .chat-input-area input {{ flex: 1; background: #222; border: 1px solid #444; color: #fff; padding: 8px; border-radius: 4px; }}
            .chat-input-area button {{ background: #4CAF50; color: #white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; font-weight: bold; }}

            /* Cột giữa: Xem ảnh */
            .center-panel {{ flex: 1; background: #181818; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px solid #333; padding: 10px; position: relative; }}
            .screen-img {{ max-width: 100%; max-height: 75vh; border: 2px solid #333; border-radius: 6px; background: #000; }}
            .mode-buttons {{ position: absolute; top: 15px; display: flex; gap: 10px; }}
            .mode-btn {{ background: #333; color: #fff; border: none; padding: 6px 15px; border-radius: 20px; font-weight: bold; font-size: 12px; cursor: pointer; }}
            .mode-btn.active {{ background: #ff5722; }}

            /* Cột phải: Thông tin Client & List ảnh */
            .right-panel {{ width: 260px; background: #181818; border-radius: 8px; border: 1px solid #333; padding: 15px; display: flex; flex-direction: column; }}
            .info-box {{ background: #222; padding: 10px; border-radius: 6px; font-size: 13px; margin-bottom: 15px; border: 1px solid #444; }}
        </style>
    </head>
    <body>
        <div class="top-bar">
            <div><span style="background: #e91e63; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">Chưa có đề</span></div>
            <div><b>Còn lại:</b> <span style="color: #ff9800;">--:--:--</span></div>
            <button style="background: #d32f2f; color: white; border: none; padding: 3px 10px; border-radius: 4px; cursor: pointer;">Thoát</button>
        </div>

        <div class="main-container">
            <!-- Trò chuyện & Gửi đáp án -->
            <div class="left-panel">
                <div style="font-weight: bold; margin-bottom: 8px; font-size: 14px; border-bottom: 1px solid #333; padding-bottom: 5px;">Trò chuyện</div>
                <div class="chat-box">
                    {chat_html}
                </div>
                <form action="/api/admin/chat" method="POST" class="chat-input-area">
                    <input type="text" name="content" placeholder="Nhập đáp án hoặc tin nhắn..." required autocomplete="off" />
                    <button type="submit">Gửi</button>
                </form>
            </div>

            <!-- Màn hình xem ảnh chụp -->
            <div class="center-panel">
                <div class="mode-buttons">
                    <button class="mode-btn">NOCAP MODE</button>
                    <button class="mode-btn active">CAP MODE</button>
                </div>
                <img src="{latest_img}" class="screen-img" />
                <div style="margin-top: 10px; font-size: 13px; color: #aaa;">Ảnh mới nhất ({len(images)} ảnh đã chụp)</div>
            </div>

            <!-- Thông tin Client -->
            <div class="right-panel">
                <div class="info-box">
                    <div style="font-size: 11px; color: #888;">KEY</div>
                    <div style="font-weight: bold; color: #4CAF50; margin-bottom: 8px; font-size: 12px;">SEB-851Q-BK5N-BL45</div>
                    <div style="font-size: 11px; color: #888;">TÊN KHÁCH</div>
                    <div style="font-weight: bold;">Chí Bảo Khách Hàng</div>
                </div>
                <div style="font-weight: bold; font-size: 13px; margin-bottom: 8px;">Ảnh chụp ({len(images)})</div>
                <div style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 5px;">
                    {"".join([f'<div style="background: #252525; padding: 6px; border-radius: 4px; font-size: 11px; word-break: break-all;">{img}</div>' for img in images])}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# 2. API nhận tin nhắn chat / gửi đáp án
@app.post("/api/admin/chat")
def post_chat(content: str):
    import datetime
    now = datetime.datetime.now().strftime("%H:%M:%S %d/%m/%2026")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (sender, content, time) VALUES (?, ?, ?)", ("admin", content, now))
    conn.commit()
    conn.close()
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/", status_code=303)

# 3. API xác thực License
@app.post("/api/license/verify")
def verify_license(req: LicenseRequest):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM licenses WHERE key = ?", (req.key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"status": "success", "message": "Key activated successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid license key")

# 4. API nhận ảnh chụp màn hình từ Client
@app.post("/api/seb/tool/screenshot")
def upload_screenshot(file: UploadFile = File(...), x_auth_id: str = Header(None)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "uploaded", "filename": file.filename}

@app.post("/api/tool/seb-upload")
def upload_seb_screenshot(file: UploadFile = File(...), x_auth_id: str = Header(None)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "uploaded", "filename": file.filename}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)