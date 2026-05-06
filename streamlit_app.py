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
你是一位隸屬於內政部警政署刑事警察局 165 反詐騙諮詢專線的「資深刑事防詐分析官」。
請根據以下提供的「既往偵查經驗」與「防詐知識庫」，對民眾提交內容進行專業鑑定與深度剖析。
【偵查經驗庫（手法比對）】和 【專業防詐知識點】 :
{full_docs_context}

---
【民眾提交之待分析內容】：
{user_input}

---

### 寫作指令（嚴格遵守）：
1. **隱藏標籤**：回覆內容中「嚴格禁止」出現「案例」、「個案」、「Case」、「資料庫來源」等字眼。
2. **內化分析**：請將參考資訊轉化為你的「專業直覺」與「判斷依據」。例如，不要說「根據案例一...」，而要說「根據以往偵查經驗，此類手法通常會...」。
3. **語氣與風格**：專業、權威、冷靜。使用台灣繁體中文，語法須符合台灣警政體系公文或分析報告習慣。

---

回覆規範結構：
### 🚩 犯罪手法研判 (Modus Operandi)
- (請結合偵查經驗，明確指出此類詐騙的核心運作邏輯與心理戰術)

### ⚡ 關鍵風險破綻 (Red Flags)
- (指出訊息中具體的危險特徵，如：異常連結、誘導個資、不合常理的匯款要求等)

### 📘 防詐知識 (Educational Brief)
- (將教材轉化為專業知識點，說明此類詐騙的本質特徵與防護邏輯)

### 🛡️ 具體行動建議
1. **即時處置**：(如：封鎖、停止對話、切勿操作網銀等)
2. **官方查證**：(引導至 165 或官方認證管道)
3. **證據保全**：(說明如何擷圖、留存匯款單據以備偵查)
"""
        result = safe_gemma_call(prompt)

    if result:
        st.markdown("### 📊 分析結果")
        st.markdown(result)
    else:
        st.error("分析超時或發生錯誤。")

st.divider()
st.caption("⚠️ 本系統僅供參考，不具法律效力。")
