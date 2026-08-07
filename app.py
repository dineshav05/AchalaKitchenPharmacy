import time
import base64
import hashlib
from io import BytesIO

import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import markdown

# ==========================================
# ⚡ OPTIMIZED ASSET & CLIENT CACHING
# ==========================================

@st.cache_resource
def init_openai_client():
    """Delays importing OpenAI until needed and caches the connection."""
    from openai import OpenAI
    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

@st.cache_resource
def init_supabase_client():
    """Delays importing Supabase and shares a single connection pool."""
    from supabase import create_client, Client
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")
    if url and key:
        return create_client(url, key)
    return None

@st.cache_data
def get_base64_image(image_path):
    """Caches UI images in memory so they only load from disk once."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except FileNotFoundError:
        return "" 

# ==========================================
# 🧠 AI PROMPT ARCHITECTURE
# ==========================================

BASE_SAFETY_CORE = """
You are Achala Digital Vaidya, an educational medical assistant dedicated to patient literacy.

STRICT SAFETY & QUALITY RULES:
1. EDUCATIONAL ONLY: You do not diagnose, treat, or modify active medical prescriptions.
2. UNCERTAINTY HANDLING: If text or image sections are blurry or partially cut off, explicitly state 'This portion is illegible'—NEVER guess.
3. HIGH-RISK DE-ESCALATION: If severe trauma or controlled substances (e.g., opioids) are identified, provide a simple summary of text and advise consulting their treating physician immediately.
4. TYPOGRAPHY RULE: DO NOT use emojis anywhere in your response. Emojis cause PDF rendering errors.
"""

PERSONA_ALLOPATHY = """
TONE: Objective, clear, precise, and clinical yet easily understandable for a layperson.

OUTPUT STRUCTURE:
You must format your response with the following translated headings:
### Report Summary
[2-3 sentence clear translation of clinical findings]

### Key Findings & Lab Values
[Break down complex medical terminology, imaging notes, or abnormal lab values into plain terms]

### Prescribed Medications Context
[Briefly explain the standard physiological purpose of the active ingredients without altering dosages]

### Red Flag Warnings
[Standard medical warning signs that require immediate physician contact]
"""

PERSONA_AYURVEDA = """
TONE: Empathetic, warm, holistic, and wise. Inspired by traditional health education and Shri Rajiv Dixit Ji's principles of preventative care.

OUTPUT STRUCTURE:
You must format your response with the following translated headings:
### Report Summary
[2-3 sentence educational breakdown of the health document]

### Kitchen Pharmacy & Aahara
[Provide gentle, food-based lifestyle alignments using common kitchen ingredients like ginger, turmeric, or warm water routines]

### Lifestyle & Vihara Guidelines
[Simple posture, rest, or daily routine recommendations]

### When to Consult a Specialist
[Gentle reminder on symptoms that warrant immediate professional medical care]
"""

def get_system_prompt(mode: str, language: str) -> str:
    """Combines the shared safety foundation with the requested persona and strict language directive."""
    persona = PERSONA_AYURVEDA if mode == "Ayurvedic" else PERSONA_ALLOPATHY
    language_directive = f"\n\nCRITICAL LANGUAGE RULE: You MUST translate and output the ENTIRE response, including all structural headings and body text, exclusively in {language}. Do not include the original English headings."
    return BASE_SAFETY_CORE + persona + language_directive

# ==========================================
# RAZORPAY REST API (Bypasses library dependency issues) 
# ==========================================
def create_payment_link(receipt_id, customer_name="Patient"):
    url = "https://api.razorpay.com/v1/payment_links"
    unique_ref_id = f"ACHALA_ORDER_{int(time.time())}"

    payload = {
        "amount": 4900,
        "currency": "INR",
        "accept_partial": False,
        "description": "Achala Digital Vaidya - Report Analysis",
        "reference_id": unique_ref_id,
        "customer": {"name": customer_name},
        "notify": {"sms": False, "email": False},
        "reminder_enable": False,
        "callback_url": "https://achala-digital-vaidya.streamlit.app/", 
        "callback_method": "get"
    }
    try:
        response = requests.post(
            url, 
            json=payload, 
            auth=HTTPBasicAuth(st.secrets["RAZORPAY_KEY_ID"], st.secrets["RAZORPAY_KEY_SECRET"]),
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("short_url") 
        else:
            st.error(f"Razorpay API Error: {response.text}")
            return None
    except Exception as e:
        st.error(f"Payment gateway error: {e}")
        return None

# ==========================================
# PAGE CONFIGURATION & INITIALIZATION
# ==========================================

st.set_page_config(
    page_title="Achala Digital Vaidya | Clinical & Ayurvedic AI",
    page_icon="Achala_Digital_Vaidya_logo.png",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Initialize cached clients
client = init_openai_client()
if not client:
    st.error("OpenAI API Key is missing. Please set it in Streamlit Secrets.")
    st.stop()

# Encode Both Logos efficiently via cache
logo_base64 = get_base64_image("Achala_Digital_Vaidya.png")
allopathic_logo_base64 = get_base64_image("Allopatic_Clinic.png")

# ---------------------------------------------------------
# UNIFIED ROUTING & LANDING PAGE LOGIC
# ---------------------------------------------------------
if "clinic_mode" not in st.session_state:
    st.session_state.clinic_mode = None
if "report_language" not in st.session_state:
    st.session_state.report_language = "English"

def set_clinic_mode(mode):
    st.session_state.clinic_mode = mode

st.markdown("""
    <style>
    .ecosystem-wrapper { display: flex; justify-content: center; width: 100%; margin-bottom: 15px; }
    .ecosystem-header { color: #666; font-weight: bold; letter-spacing: 1px; font-size: 12px; background-color: #f0f2f6; padding: 8px 20px; border-radius: 20px; }
    .main-header { text-align: center; margin-bottom: 30px; }
    .step-header { text-align: center; margin-bottom: 10px; }

    .vibrant-card-ayurveda { background: linear-gradient(135deg, #fffcf0 0%, #fff7d1 100%); border: 2px solid #ffe89e; border-radius: 20px; padding: 20px; margin-bottom: 10px; text-align: center; transition: transform 0.2s ease; }
    .vibrant-card-allopathic { background: linear-gradient(135deg, #f0f7ff 0%, #e0efff 100%); border: 2px solid #b5d7ff; border-radius: 20px; padding: 20px; margin-bottom: 10px; text-align: center; transition: transform 0.2s ease; }
    
    .vibrant-card-ayurveda:hover, .vibrant-card-allopathic:hover { transform: translateY(-4px); }

    .card-icon { font-size: 45px; margin-bottom: 10px; }
    .card-title { color: #2c3e50; font-weight: bold; font-size: 20px; margin-bottom: 5px; }
    .card-subtitle { color: #7f8c8d; font-style: italic; font-size: 14px; margin-bottom: 15px; }
    .card-description { color: #34495e; font-size: 15px; line-height: 1.5; margin-bottom: 0px;}
    
    button[kind="primary"], button[kind="secondary"] { border-radius: 12px !important; margin-top: 0px !important; }
    div[data-testid="column"] > div > div > div[data-testid="stVerticalBlock"] > div > div { margin-top: 5px !important; }
    </style>
    """, unsafe_allow_html=True)


if st.session_state.clinic_mode is None:
    st.markdown("""
        <div class='ecosystem-wrapper'>
            <div class='ecosystem-header'>ACHALA ECOSYSTEM</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("<h1 class='main-header'>Digital Clinic Workspace</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 10, 1])
    
    with col2:
        st.markdown("<h3 class='step-header'>🌐 Step 1: Choose Report Language</h3>", unsafe_allow_html=True)
        st.info("The AI will automatically analyze your medical reports and reply in the language selected below.")
        
        languages = ["English", "Hindi", "Kannada", "Telugu", "Tamil", "Marathi", "Malayalam"]
        st.session_state.report_language = st.selectbox(
            "Select Language:",
            languages,
            index=languages.index(st.session_state.report_language),
            label_visibility="collapsed"
        )
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h3 class='step-header'>🏥 Step 2: Select Operating Mode</h3>", unsafe_allow_html=True)
        
        card_col1, card_col2 = st.columns(2)
        
        with card_col1:
            st.markdown("""
                <div class='vibrant-card-ayurveda'>
                    <div class='card-icon'>🌿</div>
                    <div class='card-title'>Achala Digital Vaidya</div>
                    <div class='card-subtitle'>Kitchen Pharmacy AI</div>
                    <div class='card-description'>Decode your diagnosis. Heal with heritage. An empowering Ayurvedic guide to joint and back pain.</div>
                </div>
                """, unsafe_allow_html=True)
            st.button("Launch Ayurvedic Clinic", key="btn_ayurveda", use_container_width=True, type="primary", on_click=set_clinic_mode, args=("Ayurvedic",))
                    
        with card_col2:
            st.markdown("""
                <div class='vibrant-card-allopathic'>
                    <div class='card-icon'>🩺</div>
                    <div class='card-title'>Clinical Translator</div>
                    <div class='card-subtitle'>Evidence-Based AI</div>
                    <div class='card-description'>Empowering patients through clear, evidence-based medical translations and clinical clarity.</div>
                </div>
                """, unsafe_allow_html=True)
            st.button("Launch Allopathic Clinic", key="btn_allopathic", use_container_width=True, on_click=set_clinic_mode, args=("Allopathic",))
                    
    st.stop()


# ---------------------------------------------------------
# ACTIVE CLINIC WORKSPACE
# ---------------------------------------------------------
if st.session_state.clinic_mode is not None:
    nav_col1, nav_col2 = st.columns([3, 1])
    with nav_col1:
        st.markdown(f"<span style='color:#666; font-size: 14px;'>**Mode:** {st.session_state.clinic_mode} &nbsp;|&nbsp; **Language:** {st.session_state.report_language}</span>", unsafe_allow_html=True)
    with nav_col2:
        if st.button("⚙️ Settings", use_container_width=True):
            st.session_state.clinic_mode = None
            st.rerun()
    st.write("---")
    
    # Capture variables for the API Call
    selected_language = st.session_state.report_language
    selected_mode = st.session_state.clinic_mode

if st.session_state.clinic_mode == "Ayurvedic":
    current_logo = logo_base64
    brand_title = "Achala Digital Vaidya"
    brand_badge = "KITCHEN PHARMACY AI"
    brand_caption = '"Decode your diagnosis. Heal with heritage. An empowering Ayurvedic guide to joint and back pain, inspired by Shri Rajiv Dixit Ji."'
    pdf_hospital_name = "Achala Digital Vaidya"
    pdf_sub_header = "Digital Vaidya • Advanced Visual Analysis Report"
    pdf_footer_text = "Guided by the Ayurvedic principles of Shri Rajiv Dixit Ji."

elif st.session_state.clinic_mode == "Allopathic":
    current_logo = allopathic_logo_base64 
    brand_title = "Patient Education & Clinical Translator"
    brand_badge = "EVIDENCE-BASED AI"
    brand_caption = '"Empowering patients through clear, evidence-based medical translations and clinical clarity."'
    pdf_hospital_name = "Clinical Translation Portal"
    pdf_sub_header = "Evidence-Based Medical Analysis Report"
    pdf_footer_text = "Disclaimer: This report is a simplified explanation of complex clinical findings for educational use."

dynamic_header_html = f"""
<div style="display: flex; flex-direction: column; align-items: center; text-align: center; padding-bottom: 10px;">
    <img src="data:image/png;base64,{current_logo}" width="80" style="margin-bottom: 8px; border-radius: 50%;">
    <h1 style="margin: 0; font-size: 2.2rem; font-weight: bold; letter-spacing: 0.5px;">
        {brand_title}
    </h1>
    <div style="margin-top: 8px; margin-bottom: 15px;">
        <span style="font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px; color: #888888;">
            {brand_badge}
        </span>
    </div>
    <p style="margin: 0; font-size: 0.95rem; color: #666666; max-width: 650px; font-style: italic; line-height: 1.5;">
        {brand_caption}
    </p>
</div>
<hr style="opacity: 0.2; margin-bottom: 10px;">
"""

st.markdown(dynamic_header_html, unsafe_allow_html=True)

st.info("💡 **Tip for Best Results:** For faster processing and privacy, you may crop or obscure personal details like phone numbers and patient names before uploading.")

# Safely initialize session states without NameErrors
if "messages" not in st.session_state:
    st.session_state.messages = []
if "processed_files" not in st.session_state:
    st.session_state.processed_files = []
if "analyzed_files" not in st.session_state:
    st.session_state.analyzed_files = []
if "premium_unlocked" not in st.session_state:
    st.session_state.premium_unlocked = False
if "payment_step" not in st.session_state:
    st.session_state.payment_step = "start" 
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# Your existing chat rendering loop (safely skips system logic)
for message in st.session_state.messages:
    if message.get("role") == "system":
        continue
    with st.chat_message(message["role"]):
        if isinstance(message["content"], str):
            st.markdown(message["content"])
        elif isinstance(message["content"], list):
            for item in message["content"]:
                if item["type"] == "text":
                    st.markdown(item["text"])
                elif item["type"] == "image_url":
                    st.caption("📎 *Image/Report Attached*")

uploaded_file = None

st.markdown(
    """
    <div style="display: flex; align-items: center; white-space: nowrap; margin-bottom: 1rem;">
        <span style="font-size: 1.4rem; margin-right: 8px;">🔍</span>
        <h3 style="margin: 0; font-size: clamp(1.1rem, 4.5vw, 1.5rem); letter-spacing: -0.5px;">
            Advanced Diagnostic Analysis
        </h3>
    </div>
    """, 
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# PREMIUM FEATURE: RAZORPAY URL REDIRECT & LOGGING
# ---------------------------------------------------------

query_params = st.query_params
payment_status = query_params.get("razorpay_payment_link_status")
payment_id = query_params.get("razorpay_payment_id")

if payment_status == "paid":
    st.session_state.premium_unlocked = True
    
    if payment_id and "ledger_logged" not in st.session_state:
        try:
            supabase = init_supabase_client()
            if supabase:
                # Attempt to insert
                supabase.table("claimed_utrs").insert({
                    "utr_number": payment_id, 
                    "status": "PAID"
                }).execute()
                st.session_state.ledger_logged = True
        except Exception as e:
            # THIS will show you exactly why it's failing on the screen!
            st.error(f"Database Error: {e}")
            
    # Clear the URL parameters so a page refresh doesn't keep them unlocked
    st.query_params.clear()


if not st.session_state.premium_unlocked:
    st.info("🔒 **Premium Feature:** Upload a photo of your joint or a medical report for deep visual analysis and get a downloadable PDF. (Fee: ₹49)")
    
    if st.session_state.payment_step == "start":
        if st.button("Generate Secure Payment Link", type="primary", use_container_width=True):
            with st.spinner("Connecting to secure payment gateway..."):
                checkout_url = create_payment_link(receipt_id="ACHALA_ORDER_001")
                
                if checkout_url:
                    st.session_state.razorpay_url = checkout_url
                    st.session_state.payment_step = "pending"
                    st.rerun()

    if st.session_state.payment_step == "completed":
        st.success("🎉 Thank you for trusting Achala Digital Vaidya!")
        st.info("Your comprehensive medical dossier has been downloaded. We hope this brings clarity to your healing journey.")
        
        if st.button("Analyze Another Report", type="primary"):
            st.session_state.payment_step = "start"
            st.rerun()

    elif st.session_state.payment_step == "pending":
        st.warning("⏳ **Payment link generated!** Click the button below to pay securely.")
        st.link_button("Proceed to Pay ₹49", st.session_state.razorpay_url, type="primary", use_container_width=True)
        st.info("After completing the payment on Razorpay, you will automatically be redirected back here to unlock your analysis.")
        
        if st.button("Cancel"):
            st.session_state.payment_step = "start"
            st.rerun()

# ---------------------------------------------------------
# STATE 3: PREMIUM UNLOCKED & FILE UPLOADER
# ---------------------------------------------------------
else:
    st.success("✅ Payment Verified! Premium Features Unlocked.")
    
uploaded_files = st.file_uploader(
        "Upload your medical report(s) or joint image(s) here:", 
        type=["png", "jpg", "jpeg"], 
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_key}"
    )
    
    if uploaded_files: # This checks if the list has at least one file
        all_new = True
        for file in uploaded_files:
            file_hash = hashlib.md5(file.getvalue()).hexdigest()
            if file_hash in st.session_state.analyzed_files:
                st.warning(f"⚠️ {file.name} has already been analyzed. Please ignore or remove it.")
                all_new = False
                
        if all_new:
            st.success("✅ Images loaded successfully! Please type your symptoms in the chat box below and hit Send to begin.")   


def encode_image(upload):
    return base64.b64encode(upload.getvalue()).decode('utf-8')

def display_letterhead_report(ai_content, logo_base64_string):
    letterhead_html = f"""
<div style="border: 2px solid #0f4c5c; border-radius: 8px; padding: 25px; background-color: #ffffff; color: #2b2b2b; font-family: 'Arial', sans-serif; box-shadow: 0px 4px 15px rgba(0,0,0,0.05); margin-top: 20px;">
    <div style="display: flex; align-items: center; border-bottom: 2px solid #004d40; padding-bottom: 15px; margin-bottom: 20px;">
        <img src="data:image/png;base64,{logo_base64_string}" width="70" style="margin-right: 20px; border-radius: 50%;">
        <div>
            <h2 style="margin: 0; color: #004d40; font-family: 'Helvetica Neue', sans-serif;">{pdf_hospital_name}</h2>
            <p style="margin: 5px 0 0 0; color: #666666; font-size: 14px;">{pdf_sub_header}</p>
        </div>
    </div>
    <div style="line-height: 1.7; font-size: 1.05rem;">
        {ai_content}
    </div>
    <div style="margin-top: 30px; border-top: 1px solid #dddddd; padding-top: 15px; text-align: center;">
        <p style="margin: 0; color: #444444; font-size: 14px; font-weight: bold;">{pdf_footer_text}</p>
    </div>
</div>
"""
    st.markdown(letterhead_html, unsafe_allow_html=True)


# ---------------------------------------------------------
# CHAT EXECUTION BLOCK
# ---------------------------------------------------------
if user_input := st.chat_input("Describe your pain or upload an image above..."):
    
    with st.chat_message("user"):
        st.markdown(user_input)
        if uploaded_files:
            # Display all uploaded images in the chat
            for file in uploaded_files:
                st.image(file, width=250)

    message_content = [{"type": "text", "text": user_input}]
    
    if uploaded_files:
        # Loop through all files and attach them to the AI prompt
        for file in uploaded_files:
            current_hash = hashlib.md5(file.getvalue()).hexdigest()
            if current_hash not in st.session_state.analyzed_files:
                base64_image = encode_image(file)
                message_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                })

    # 1. Append the user's message to the session state history
    st.session_state.messages.append({"role": "user", "content": message_content})

    # 2. Trigger the Assistant UI and API Call
    with st.chat_message("assistant"):
        with st.spinner("Consulting the Achala Intelligence Engine... Please wait a few seconds."):
            try: 
                # 1. Generate the structured prompt dynamically based on the UI state
                dynamic_prompt = get_system_prompt(mode=selected_mode, language=selected_language)
                
                # 2. Build a fresh message list for this specific API call
                api_messages = [
                    {"role": "system", "content": dynamic_prompt},
                    {"role": "user", "content": message_content} 
                ]
                
                # 3. Append your brilliant Multilingual Override Prompt
                api_messages.append({
                    "role": "system", 
                    "content": f"CRITICAL INSTRUCTION: You are fully capable of speaking {selected_language}. The user requires this English medical document to be translated and explained entirely in {selected_language}. You MUST generate your ENTIRE response, including all headings, Ayurvedic remedies, and clinical explanations, strictly in {selected_language}. Do not output English."
                })
                
                # 4. Execute the API Call
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=api_messages,
                    temperature=0.3, 
                )
                
                ai_response = response.choices[0].message.content
                
                st.markdown(ai_response)
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
                # ==============================================================
                # PDF GENERATION (Moved inside the TRY block, where it belongs!)
                # ==============================================================
                if uploaded_file is not None:
                    display_letterhead_report(ai_response, current_logo)
                    structured_html_content = markdown.markdown(ai_response, extensions=['extra', 'sane_lists', 'nl2br'])
                    
                    # --- DYNAMIC FONT MAPPING FOR INDIC LANGUAGES ---
                    font_face_css = ""
                    font_family = "sans-serif"
                    
                    indic_fonts = {
                        "Hindi": "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
                        "Marathi": "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
                        "Kannada": "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSansKannada/NotoSansKannada-Regular.ttf",
                        "Telugu": "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSansTelugu/NotoSansTelugu-Regular.ttf",
                        "Tamil": "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSansTamil/NotoSansTamil-Regular.ttf",
                        "Malayalam": "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSansMalayalam/NotoSansMalayalam-Regular.ttf"
                    }
                    
                    if selected_language in indic_fonts:
                        font_url = indic_fonts[selected_language]
                        font_family = "'IndicFont', sans-serif"
                        font_face_css = f"""
                        @font-face {{
                            font-family: 'IndicFont';
                            src: url('{font_url}');
                        }}
                        """
                        
                    report_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <style>
                            {font_face_css}
                            @page {{ 
                                size: A4 portrait; 
                                margin: 1.5cm; 
                            }}
                            body {{ 
                                font-family: {font_family}; 
                                color: #2b2b2b; 
                                font-size: 13px; 
                                line-height: 1.6; 
                            }}
                            
                            /* Strict image constraint rules for WeasyPrint */
                            img {{
                                max-width: 100%;
                                height: auto;
                            }}
                            .logo-img {{
                                width: 60px !important;
                                max-width: 60px !important;
                                height: auto !important;
                                display: block;
                            }}
                            
                            /* Header structure & typography */
                            .header-table {{
                                width: 100%;
                                border-bottom: 2px solid #0f4c5c;
                                padding-bottom: 12px;
                                margin-bottom: 20px;
                                table-layout: fixed;
                            }}
                            .english-header h2 {{ 
                                font-family: 'Helvetica', 'Arial', sans-serif !important;
                                margin: 0; 
                                color: #0f4c5c; 
                                font-size: 22px; 
                                font-weight: bold;
                                line-height: 1.2;
                            }}
                            .english-header p {{ 
                                font-family: 'Helvetica', 'Arial', sans-serif !important;
                                margin: 4px 0 0 0; 
                                color: #555; 
                                font-size: 11px; 
                                text-transform: uppercase;
                                letter-spacing: 0.5px;
                            }}
                            
                            .content-section h3 {{ 
                                color: #0f4c5c; 
                                border-bottom: 1px solid #e0e0e0; 
                                padding-bottom: 4px; 
                                margin-top: 20px; 
                                font-size: 16px; 
                            }}
                            .footer-section {{ 
                                text-align: center; 
                                font-size: 10px; 
                                color: #777; 
                                border-top: 1px solid #e0e0e0; 
                                padding-top: 12px; 
                                margin-top: 30px; 
                            }}
                        </style>
                    </head>
                    <body>
                        <table class="header-table">
                            <tr>
                                <td style="width: 70px; vertical-align: middle;">
                                    <img src="data:image/png;base64,{current_logo}" class="logo-img">
                                </td>
                                <td class="english-header" style="vertical-align: middle; text-align: left; padding-left: 10px;">
                                    <h2>{pdf_hospital_name}</h2>
                                    <p>{pdf_sub_header}</p>
                                </td>
                            </tr>
                        </table>
                        
                        <div class="content-section">
                            {structured_html_content}
                        </div>
                        
                        <div class="footer-section">
                            {pdf_footer_text}
                        </div>
                    </body>
                    </html>
                    """
                    
                    # ⚡ LAZY LOAD WEASYPRINT HERE
                    # Loading it only at the moment of PDF generation drastically speeds up app startup
                    from weasyprint import HTML
                    pdf_bytes = HTML(string=report_html).write_pdf()

                    def reset_for_next_patient():
                        st.session_state.premium_unlocked = False
                        st.session_state.payment_step = "completed"
                        st.session_state.messages = [] # Clear the chat history
                        st.session_state.uploader_key += 1
                    
                    st.download_button(
                        label="📄 Download Official PDF Report",
                        data=pdf_bytes,
                        file_name=f"Achala_Vaidya_Report_{selected_language}.pdf",
                        mime="application/pdf",
                        type="primary",
                        on_click=reset_for_next_patient
                    )

                   # Save all file hashes to prevent duplicate re-runs
                    if uploaded_files:
                        for file in uploaded_files:
                            st.session_state.analyzed_files.append(hashlib.md5(file.getvalue()).hexdigest())
                    
                    st.session_state.uploader_key += 1
                
            except Exception as e: 
                st.error(f"Error communicating with the Achala Intelligence Engine. Please try again. ({str(e)})")

# ==========================================
# FOOTER & COMPLIANCE LINKS
# ==========================================
st.write("---") # Creates a clean visual divider

# Create 4 balanced columns for a horizontal footer layout
foot_col1, foot_col2, foot_col3, foot_col4 = st.columns(4)

with foot_col1:
    st.page_link("pages/Contact_Us.py", label="Contact Us", icon="📞")
with foot_col2:
    st.page_link("pages/Terms_and_Conditions.py", label="Terms & Conditions", icon="📜")
with foot_col3:
    st.page_link("pages/Privacy_Policy.py", label="Privacy Policy", icon="🔒")
with foot_col4:
    st.page_link("pages/Refund_Policy.py", label="Refund Policy", icon="💳")

# Standard Copyright Notice
st.markdown(
    """
    <div style='text-align: center; color: #888888; margin-top: 20px; font-size: 12px;'>
        © 2026 Achala Enterprises. All rights reserved.
    </div>
    """, 
    unsafe_allow_html=True
)