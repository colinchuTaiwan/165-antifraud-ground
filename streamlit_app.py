import os
import time
import random
import requests
import streamlit as st
from pathlib import Path

# =========================
# 0. 環境變數處理 (Streamlit Secrets)
# =========================


LITELLM_URL = st.secrets.get("LITELLM_URL", "")
LITELLM_KEY = st.secrets.get("LITELLM_KEY", "")
MODEL_NAME = st.secrets.get("MODEL_NAME", "")

CASE_DOCS_DIR = "case_docs"
KNOWLEDGE_DB_DIR = "knowledge_db"

# 確保雲端環境資料夾存在
for d in [CASE_DOCS_DIR, KNOWLEDGE_DB_DIR]:
    Path(d).mkdir(exist_ok=True)

# =========================
# 1. 讀取所有本地文獻
# =========================
def load_all_local_docs():
    """將所有 txt 檔案合併成一個大型 Context 區塊"""
    context_text = ""
    
    case_files = list(Path(CASE_DOCS_DIR).glob("*.txt"))
    context_text += "--- 歷史詐騙案例彙整 ---\n"
    if not case_files:
        context_text += "(目前暫無案例檔案)\n"
    for f in case_files:
        try:
            context_text += f"【檔案：{f.name}】\n{f.read_text(encoding='utf-8')}\n\n"
        except Exception:
            pass
    
    kb_files = list(Path(KNOWLEDGE_DB_DIR).glob("*.txt"))
    context_text += "--- 官方防詐教材 ---\n"
    if not kb_files:
        context_text += "(目前暫無教材檔案)\n"
    for f in kb_files:
        try:
            context_text += f"【主題：{f.name}】\n{f.read_text(encoding='utf-8')}\n\n"
        except Exception:
            pass
            
    return context_text

# =========================
# 2. API 呼叫
# =========================
def safe_gemma_call(prompt):
    if not LITELLM_KEY:
        return "❌ 錯誤：尚未在 Streamlit Secrets 設定 API Key"

    headers = {
        "Content-Type": "application/json",
        "Authorization": LITELLM_KEY
    }

    for i in range(5):
        try:
            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "system", 
                        "content": "你是165防詐分析官。請根據提供的知識庫進行分析，若無關聯請直說。"
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1
            }

            res = requests.post(
                LITELLM_URL,
                headers=headers,
                json=payload,
                timeout=(5, 60)
            )

            if res.status_code == 200:
                return res.json()['choices'][0]['message']['content']

            if res.status_code in [429, 500, 503]:
                time.sleep(min(2 ** i, 20) + random.random())
        except Exception as e:
            if i == 4:
                return f"❌ API 錯誤: {e}"
    return None

# =========================
# 3. UI 介面
# =========================
st.set_page_config(page_title="165 防詐分析系統", layout="wide")
st.title("🚨 165 智慧防詐分析系統 ")


user_input = st.text_area("請輸入可疑對話、簡訊或網址內容：", height=250)
run = st.button("啟動分析")

# =========================
# 4. 主流程
# =========================
if run and user_input.strip():
    with st.spinner("LLM 正在掃描知識庫文件..."):
        
        full_docs_context = load_all_local_docs()

        prompt = f"""
以下是我們的【防詐知識庫】：
{full_docs_context}

---
【待分析用戶內容】：
{user_input}

請進行結構化分析：
## 💡 刑事分析報告
### 🚩 手法判定
### ⚡ 關鍵風險點
### 📘 防詐教育
### 🛡️ 建議行動

⚠️ 僅能依據知識庫回答。
"""
        result = safe_gemma_call(prompt)

    if result:
        st.markdown("### 📊 分析結果")
        st.markdown(result)
    else:
        st.error("分析超時或發生錯誤。")

st.divider()
st.caption("⚠️ 本系統僅供參考，不具法律效力。")
