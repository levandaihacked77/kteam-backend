import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from pydantic import BaseModel
import sqlite3

app = FastAPI(title="K-Team Exam Support Backend")

DB_NAME = "exam_production.db"

def init_db():
    if os.path.exists(DB_NAME):
        try:
            os.remove(DB_NAME)
        except:
            pass

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Bảng License
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            machine_guid TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO licenses (key, machine_guid) VALUES ('KTEAM-2026-SECRET', '41c0b179-ee0f-44d4-83af-6639a50a555a')")
    
    # Bảng đáp án bài thi
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exam_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_code TEXT,
            question_key TEXT,
            answer_value TEXT,
            answer_content TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO exam_answers (exam_code, question_key, answer_value, answer_content) VALUES ('EXAM01', 'Q1', 'A', 'Sample Answer A')")
    
    conn.commit()
    conn.close()

init_db()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class LicenseRequest(BaseModel):
    key: str
    machineGuid: str

class ExamRequest(BaseModel):
    examCode: str
    questionKey: str

# Trang chủ để tránh lỗi 404 Not Found khi Render hoặc trình duyệt quét health check
@app.get("/")
def read_root():
    return {"status": "online", "message": "K-Team Exam Support Backend is running"}

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

    return {
        "status": "ok",
        "data": data_dict
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)