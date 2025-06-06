import streamlit as st
import pandas as pd
import os
from together import Together
import pdfplumber
import docx
import tempfile
from datetime import datetime
import re
from html import escape
import markdown

# Set up session state for sidebar toggle
if "sidebar_state" not in st.session_state:
    st.session_state.sidebar_state = "expanded"

# Page setup with dynamic sidebar
st.set_page_config(
    page_title="🧠 AI File Chatbot", 
    page_icon="📁", 
    layout="wide",
    initial_sidebar_state=st.session_state.sidebar_state
)

# Custom CSS for chat interface
st.markdown("""
<style>
    .user-message {
        background-color: #3b82f6;
        color: white;
        border-radius: 18px 18px 0px 18px;
        padding: 12px 16px;
        margin-left: auto;
        margin-bottom: 8px;
        max-width: 80%;
        max-height: 300px;
        overflow-y: auto;
    }
    
    .ai-message {
        background-color: #f3f4f6;
        color: #1f2937;
        border-radius: 18px 18px 18px 0px;
        padding: 12px 16px;
        margin-right: auto;
        margin-bottom: 8px;
        max-width: 80%;
        max-height: 300px;
        overflow-y: auto;
    }
    
    .message-timestamp {
        font-size: 0.75rem;
        color: #6b7280;
        margin-top: 4px;
    }
    
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
    }
    
    th, td {
        padding: 8px;
        text-align: left;
        border-bottom: 1px solid #ddd;
    }
    
    th {
        background-color: #f3f4f6;
    }
    
    .ai-message table {
        color: #1f2937;
    }
</style>
""", unsafe_allow_html=True)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style='text-align: center; margin-bottom: 20px;'>
        <h3 style='color: #1f2937;'>📁 File Upload</h3>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "📤 Upload your file (PDF, DOCX, TXT, CSV, Excel)", 
        type=["pdf", "docx", "txt", "csv", "xlsx", "xls"],
        key="file_uploader",
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("""
    <div style='text-align: center;'>
        <p style='color: #6b7280; font-size: small;'>Chat with any file in English or Hindi</p>
    </div>
    """, unsafe_allow_html=True)

# Main content area
st.markdown(
    """
    <div style='text-align: center; margin-bottom: 30px;'>
        <h1 style='color: #1f2937;'>📁 File Chat Assistant</h1>
        <p style='color: #6b7280;'>Ask questions about your uploaded file</p>
    </div>
    """, 
    unsafe_allow_html=True
)

# Sidebar toggle button
if uploaded_file:
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔀 On/Off Sidebar"):
            if st.session_state.sidebar_state == "expanded":
                st.session_state.sidebar_state = "collapsed"
            else:
                st.session_state.sidebar_state = "expanded"
            st.rerun()

def is_hindi_query(text):
    hindi_keywords = ['ky', 'hai', 'kya', 'ye', 'kaun', 'kahan', 'karo', 'kare', 'nahi', 'hai kya']
    return any(keyword in text.lower() for keyword in hindi_keywords)

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

def save_large_file(uploaded_file):
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, uploaded_file.name)

    chunk_size = 50 * 1024 * 1024
    total_size = uploaded_file.size

    with st.status("Processing file...", expanded=True) as status:
        progress_bar = st.progress(0)
        status_text = st.empty()

        with open(temp_file_path, 'wb') as f:
            bytes_read = 0
            while True:
                chunk = uploaded_file.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                bytes_read += len(chunk)
                progress = bytes_read / total_size
                progress_bar.progress(progress)
                status_text.text(f"Processed {bytes_read / (1024*1024):.1f} MB")

        status.update(label="File ready", state="complete", expanded=False)

    return temp_file_path

def process_file(uploaded_file):
    file_type = uploaded_file.name.split(".")[-1].lower()

    if file_type in ["xlsx", "xls"]:
        df = pd.read_excel(uploaded_file)
        return df.to_string(index=False)
    elif file_type == "csv":
        df = pd.read_csv(uploaded_file)
        return df.to_string(index=False)
    elif file_type == "txt":
        return clean_html(uploaded_file.read().decode("utf-8"))
    elif file_type == "pdf":
        with pdfplumber.open(uploaded_file) as pdf:
            text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
            return clean_html(text)
    elif file_type == "docx":
        doc = docx.Document(uploaded_file)
        return clean_html("\n".join(p.text for p in doc.paragraphs))
    else:
        raise ValueError("Unsupported file type")

# Display chat history
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(
            f"""
            <div style='display: flex; justify-content: flex-end;'>
                <div class="user-message">
                    {message["content"]}
                    <div class="message-timestamp" style='text-align: right;'>{message["time"]}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div style='display: flex; justify-content: flex-start;'>
                <div class="ai-message">
                    {message["content"]}
                    <div class="message-timestamp">{message["time"]}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# Process file if uploaded
if uploaded_file:
    try:
        if uploaded_file.size > 200 * 1024 * 1024:
            temp_file_path = save_large_file(uploaded_file)
            try:
                context_text = process_file(uploaded_file)
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
        else:
            context_text = process_file(uploaded_file)

        client = Together(api_key="f749bcb5fa7985b19fa6616adf9ea703006cefc930fdbc381d619f9d00070638")

        if prompt := st.chat_input("Ask about the file (English or Hindi)..."):
            current_time = datetime.now().strftime("%H:%M")
            is_hindi = is_hindi_query(prompt)

            st.session_state.messages.append({
                "role": "user", 
                "content": prompt,
                "time": current_time
            })

            with st.spinner("Thinking .." if is_hindi else "Generating response..."):
                system_prompt = f"""File content:
                {context_text}

                Rules:
                1. Answer in the same language as the question
                2. For Hindi queries (like 'ye kya hai?'), respond in Romanized Hindi
                3. For English queries (like 'what is?') respond in English
                4. Respond in a clear and natural way. If the answer is in table form, use markdown formatting (| col1 | col2 | ... |).
                5. If answer isn't in file, say:
                   - Hindi: "File mein ye jankari nahi hai"
                   - English: "This information isn't in the file"
                """

                try:
                    response = client.chat.completions.create(
                        model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    bot_reply = response.choices[0].message.content
                except Exception as e:
                    bot_reply = "Error processing request" + (" (error aagya)" if is_hindi else "")

            # Format the response
            if "|" in bot_reply and "---" in bot_reply:
                # Convert markdown table to HTML
                table_html = markdown.markdown(bot_reply, extensions=['tables'])
                formatted_reply = f"<div style='overflow-x: auto;'>{table_html}</div>"
            else:
                formatted_reply = escape(bot_reply)

            st.session_state.messages.append({
                "role": "assistant", 
                "content": formatted_reply,
                "time": datetime.now().strftime("%H:%M")
            })

            st.rerun()

    except Exception as e:
        st.error(f"Error processing file: {str(e)}")

else:
    st.info("Please upload a file using the sidebar to begin")