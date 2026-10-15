import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import datetime

app = FastAPI(title="K-Team Exam Support Pro API")

# Cấu hình CORS để cho phép trang web độc lập gọi API vào server Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

DB_NAME = "exam_production.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS licenses (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE, machine_guid TEXT)''')
    cursor.execute("INSERT OR IGNORE INTO licenses (key, machine_guid) VALUES ('KTEAM-2026-SECRET', '41c0b179-ee0f-44d4-83af-6639a50a555a')")
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS exam_answers (id INTEGER PRIMARY KEY AUTOINCREMENT, exam_code TEXT, question_key TEXT, answer_value TEXT, answer_content TEXT)''')
    cursor.execute("INSERT OR IGNORE INTO exam_answers (exam_code, question_key, answer_value, answer_content) VALUES ('EXAM01', 'Q1', 'A', 'Sample Answer A')")
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, content TEXT, time TEXT)''')
    conn.commit()
    conn.close()

init_db()

class LicenseRequest(BaseModel):
    key: str
    machineGuid: str

class ExamRequest(BaseModel):
    examCode: str
    questionKey: str = None

class AnswerRequest(BaseModel):
    examCode: str
    questionKey: str
    answerValue: str
    answerContent: str = ""

class ChatRequest(BaseModel):
    content: str

@app.get("/")
def read_root():
    return {"status": "online", "message": "K-Team Exam Support Backend is running"}


# --- API CUNG CẤP DỮ LIỆU CHO WEB DASHBOARD ĐỘC LẬP ---
@app.get("/api/admin/dashboard-data")
def get_dashboard_data():
    # Lấy danh sách ảnh
    images = []
    if os.path.exists(UPLOAD_DIR):
        images = sorted(os.listdir(UPLOAD_DIR), reverse=True)
    
    latest_image = f"/uploads/{images[0]}" if images else None

    # Lấy danh sách đáp án
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT exam_code, question_key, answer_value, answer_content FROM exam_answers ORDER BY id DESC")
    answers_rows = cursor.fetchall()

    # Lấy lịch sử chat
    cursor.execute("SELECT sender, content, time FROM messages ORDER BY id DESC LIMIT 20")
    msgs_rows = cursor.fetchall()
    conn.close()

    answers = [{"exam_code": r[0], "question_key": r[1], "answer_value": r[2], "answer_content": r[3]} for r in answers_rows]
    messages = [{"sender": r[0], "content": r[1], "time": r[2]} for r in reversed(msgs_rows)]

    return {
        "total_images": len(images),
        "latest_image": latest_image,
        "answers": answers,
        "messages": messages
    }

@app.post("/api/admin/add-answer")
def api_add_answer(req: AnswerRequest):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM exam_answers WHERE exam_code = ? AND question_key = ?", (req.examCode, req.questionKey))
    cursor.execute("INSERT INTO exam_answers (exam_code, question_key, answer_value, answer_content) VALUES (?, ?, ?, ?)", 
                   (req.examCode, req.questionKey, req.answerValue, req.answerContent))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/admin/send-chat")
def api_send_chat(req: ChatRequest):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (sender, content, time) VALUES (?, ?, ?)", ("admin", req.content, now))
    conn.commit()
    conn.close()
    return {"status": "success"}


# --- CÁC API CHO C# CLIENT ---
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

@app.post("/api/seb/tool/get-all")
def get_exam_data(req: ExamRequest, x_auth_id: str = Header(None)):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT question_key, answer_value, answer_content FROM exam_answers WHERE exam_code = ?", (req.examCode,))
    rows = cursor.fetchall()
    conn.close()

    data_dict = {}
    for r in rows:
        data_dict[r[0]] = {
            "answerMatchingValue": r[1],
            "answerMatchingContent": r[2]
        }
    return {"status": "ok", "data": data_dict}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)