import os
import streamlit as st
import time
import docx
import PyPDF2
import concurrent.futures
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# --- Fungsi untuk ekstraksi dokumen ---
def extract_text(file):
    if file.name.endswith((".txt", ".md")):
        return file.read().decode("utf-8", errors="ignore")
    elif file.name.endswith(".docx"):
        doc = docx.Document(file)
        return "\n".join([para.text for para in doc.paragraphs])
    elif file.name.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file)
        return "".join([p.extract_text() or "" for p in reader.pages])
    else:
        return ""

# --- Setup awal Streamlit ---
st.set_page_config(page_title="Multi-Model Chat", page_icon="🤖")

# --- Client OpenRouter ---
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

# --- Model yang digunakan ---
model_list = {
    "Kimi K2": "moonshotai/kimi-k2:free",
    "DeepSeek R1": "deepseek/deepseek-r1-0528:free",
    "DeepSeek Chat V3": "deepseek/deepseek-chat-v3-0324:free",
}

# --- Inisialisasi State ---
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []
if "model_params" not in st.session_state:
    st.session_state.model_params = {
        name: {"temperature": 0.7, "top_p": 1.0}
        for name in model_list
    }
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

# --- Sidebar Param ---
st.sidebar.title("⚙️ Parameter Model")
for name in model_list:
    with st.sidebar.expander(f"🔧 {name}", expanded=True):
        temp = st.slider(f"🌡️ Temp ({name})", 0.0, 1.5,
                         st.session_state.model_params[name]["temperature"], 0.1,
                         key=f"{name}_temp")
        top_p = st.slider(f"📊 Top-p ({name})", 0.1, 1.0,
                          st.session_state.model_params[name]["top_p"], 0.05,
                          key=f"{name}_top_p")
        st.caption("Temperature = kreativitas, Top-p/k = sampling filter.")
        st.session_state.model_params[name] = {
            "temperature": temp,
            "top_p": top_p,
        }

# --- Upload File (Dokumen) ---
# --- Input User ---
st.title("🤖 Multi-Model Chatbot Studio")
st.subheader("📎 Chat with Document (Max 5 files)")
if st.button("🔁 Reset Dokumen"):
    st.session_state.uploaded_files = []
    st.rerun()  # forces widget to clear

uploaded_files = st.file_uploader(
    "Upload file (.txt, .md, .pdf, .docx)", type=["txt", "md", "pdf", "docx"],
    accept_multiple_files=True
)
if uploaded_files:
    st.session_state.uploaded_files = uploaded_files[:5]

context_text = ""
for file in st.session_state.uploaded_files:
    try:
        content = extract_text(file)
        context_text += f"\n\n### {file.name}:\n{content}"
        with st.expander(f"📄 {file.name}"):
            st.code(content[:1000], language="text")
    except Exception as e:
        st.error(f"Gagal membaca {file.name}: {e}")

# --- Fungsi Query Model ---
def query_model(name, model_id, user_input, context, params):
    start = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Gunakan info berikut jika relevan:\n{context}"},
                {"role": "user", "content": user_input}
            ],
            temperature=params["temperature"],
            top_p=params["top_p"],
        )
        elapsed = time.perf_counter() - start
        return name, {
            "text": response.choices[0].message.content,
            "time": elapsed,
            "params": params,
        }
    except Exception as e:
        return name, {
            "text": f"❌ Error: {e}",
            "time": None,
            "params": params,
        }


user_input = st.chat_input("Ketik pertanyaanmu...")

if user_input:
    st.session_state.chat_log.append({"role": "user", "content": user_input})
    st.session_state.chat_log.append({"role": "assistant", "content": "⌛"})  # placeholder

    with st.spinner("Menanyakan ke semua model..."):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    query_model,
                    name, model_id, user_input, context_text, st.session_state.model_params[name]
                )
                for name, model_id in model_list.items()
            ]
            results = [f.result() for f in futures]
        model_responses = dict(results)

    st.session_state.chat_log[-1] = {"role": "assistant", "content": model_responses}

# --- Tampilkan Chat ---
for msg in st.session_state.chat_log:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    elif msg["role"] == "assistant":
        if isinstance(msg["content"], str):
            st.chat_message("assistant").markdown(msg["content"])
        else:
            with st.chat_message("assistant"):
                for name, result in msg["content"].items():
                    time_info = f"⏱️ {result['time']:.2f}s" if result["time"] else "❌"
                    param_info = f"🌡 Temp: {result['params']['temperature']} | 🎯 Top-p: {result['params']['top_p']}"
                    with st.expander(f"📦 {name} ({time_info})", expanded=True):
                        st.caption(param_info)
                        st.markdown(result["text"])
