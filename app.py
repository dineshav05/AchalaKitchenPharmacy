import time
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
from PIL import Image
from openai import OpenAI
import base64
import hashlib
import markdown
from io import BytesIO
from weasyprint import HTML, CSS
from supabase import create_client, Client

# ==========================================
# 🧠 AI PROMPT ARCHITECTURE
# ==========================================

BASE_SAFETY_CORE = """
You are Achala Digital Vaidya, an educational medical assistant dedicated to patient literacy.

STRICT SAFETY & QUALITY RULES:
1. EDUCATIONAL ONLY: You do not diagnose, treat, or modify active medical prescriptions.
2. UNCERTAINTY HANDLING: If text or image sections are blurry or partially cut off, explicitly state 'This portion is illegible'—NEVER guess.
3. HIGH-RISK DE-ESCALATION: If severe trauma or controlled substances (e.g., opioids) are identified, provide a simple summary of text and advise consulting their treating physician immediately.
4. UNIFORM MARKDOWN: You MUST output using the exact headings provided in your active mode instructions.
"""

PERSONA_ALLOPATHY = """
TONE: Objective, clear, precise, and clinical yet easily understandable for a layperson.

OUTPUT STRUCTURE:
### 🩺 ವರದಿ ಸಾರಾಂಶ (Clinical Summary)
[2-3 sentence clear translation of clinical findings]

### 🧪 ಮುಖ್ಯ ಸಂಶೋಧನೆಗಳು (Key Findings & Lab Values)
[Break down complex medical terminology, imaging notes, or abnormal lab values into plain terms]

### 💊 ನಮೂದಿಸಿದ ಔಷಧಿಗಳು (Prescribed Medications Context)
[Briefly explain the standard physiological purpose of the active ingredients without altering dosages]

### ⚠️ ಗಮನಿಸಬೇಕಾದ ಲಕ್ಷಣಗಳು (Red Flag Warnings)
[Standard medical warning signs that require immediate physician contact]
"""

PERSONA_AYURVEDA = """
TONE: Empathetic, warm, holistic, and wise. Inspired by traditional health education and Shri Rajiv Dixit Ji's principles of preventative care.

OUTPUT STRUCTURE:
### 🩺 ವರದಿ ಸಾರಾಂಶ (Report Summary)
[2-3 sentence educational breakdown of the health document]

### 🌿 ಅಡುಗೆಮನೆ ಮತ್ತು ಆಹಾರ ಸಂಸ್ಕೃತಿ (Kitchen Pharmacy & Aahara)
[Provide gentle, food-based lifestyle alignments using common kitchen ingredients like ginger, turmeric, or warm water routines]

### 🧘 ಜೀವನಶೈಲಿ ಮತ್ತು ವಿಹಾರ (Lifestyle & Vihara Guidelines)
[Simple posture, rest, or daily routine recommendations]

### ⚠️ ವೈದ್ಯರನ್ನು ಯಾವಾಗ ಸಂಪರ್ಕಿಸಬೇಕು (When to Consult a Specialist)
[Gentle reminder on symptoms that warrant immediate professional medical care]
"""

def get_system_prompt(mode: str, language: str) -> str:
    """Combines the shared safety foundation with the requested persona and language directive."""
    persona = PERSONA_AYURVEDA if mode == "Ayurveda" else PERSONA_ALLOPATHY
    language_directive = f"\n\nCRITICAL LANGUAGE RULE: You MUST output the entire response exclusively in {language}."
    return BASE_SAFETY_CORE + persona + language_directive

# ==========================================

# ---------------------------------------------------------
# RAZORPAY REST API (Bypasses library dependency issues) 
# ---------------------------------------------------------
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


st.set_page_config(
    page_title="Achala Digital Vaidya | Clinical & Ayurvedic AI",
    page_icon="Achala_Digital_Vaidya_logo.png",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Use .get() so it doesn't crash if the key is missing
api_key = st.secrets.get("OPENAI_API_KEY")

if not api_key:
    st.error("OpenAI API Key is missing. Please set it in Streamlit Secrets.")
    st.stop()

# Initialize the client
client = OpenAI(api_key=api_key)

# --- Base64 Image Encoder ---
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except FileNotFoundError:
        return "" # Prevents crash if images aren't uploaded to github yet

# --- Encode Both Logos ---
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
    
    selected_language = st.session_state.report_language

if st.session_state.clinic_mode == "Ayurvedic":
    current_logo = logo_base64
    brand_title = "Achala Digital Vaidya"
    brand_badge = "KITCHEN PHARMACY AI"
    brand_caption = '"Decode your diagnosis. Heal with heritage. An empowering Ayurvedic guide to joint and back pain, inspired by Shri Rajiv Dixit Ji."'
    pdf_hospital_name = "Achala Digital Vaidya"
    pdf_sub_header = "Digital Vaidya • Advanced Visual Analysis Report"
    pdf_footer_text = "Guided by the Ayurvedic principles of Shri Rajiv Dixit Ji."
    SYSTEM_PROMPT = """
    You are an Educational Medical Report Assistant for Achala Digital Vaidya.
    Your role is purely to translate, explain, and summarize the patient's existing hospital document into simple terms for patient literacy.

    STRICT SAFETY RULES:
    1. Do NOT evaluate, alter, or judge active pharmaceutical prescriptions or controlled medications.
    2. Provide simple, educational language translations of medical terms (e.g., explaining 'Spondylosis' or 'Osteoarthritis').
    3. Keep all advice strictly educational and general. Always advise the patient to follow their treating physician's prescription.
    You are Rajiv Dixit AI, an expert consultant in Ayurveda and Vata-induced joint pain. Your goal is to help the common man reverse chronic back and joint pain using accessible, budget-friendly kitchen remedies.
    Follow these rules strictly:
    1. Identify if the user's symptoms point to a Vata imbalance.
    2. Recommend affordable home remedies based on Rajiv Dixit's protocols (Parijat decoction, Chuna, Methi Dana).
    3. SAFETY GUARDRAIL: You MUST explicitly check if the user has a history of kidney stones or gallstones BEFORE recommending Chuna (Edible Limestone). If they answer yes, strictly forbid Chuna.
    4. Enforce foundational lifestyle rules: sit down while drinking water (sip by sip), completely eliminate refined oils.
    5. Keep your tone compassionate, simple, and professional.
    6. NEVER use numbered lists (1, 2, 3...) for patient details. Use Markdown subheadings (e.g., ### Patient Information) and bullet points.
    """

elif st.session_state.clinic_mode == "Allopathic":
    current_logo = allopathic_logo_base64 
    brand_title = "Patient Education & Clinical Translator"
    brand_badge = "EVIDENCE-BASED AI"
    brand_caption = '"Empowering patients through clear, evidence-based medical translations and clinical clarity."'
    pdf_hospital_name = "Clinical Translation Portal"
    pdf_sub_header = "Evidence-Based Medical Analysis Report"
    pdf_footer_text = "Disclaimer: This report is a simplified explanation of complex clinical findings for educational use."
    SYSTEM_PROMPT = """
    You are an Educational Medical Report Assistant for Achala Digital Vaidya.
    Your role is purely to translate, explain, and summarize the patient's existing hospital document into simple terms for patient literacy.

    STRICT SAFETY RULES:
    1. Do NOT evaluate, alter, or judge active pharmaceutical prescriptions or controlled medications.
    2. Provide simple, educational language translations of medical terms (e.g., explaining 'Spondylosis' or 'Osteoarthritis').
    3. Keep all advice strictly educational and general. Always advise the patient to follow their treating physician's prescription.
    You are a highly professional Clinical Translation Assistant working for an Orthopedic Hospital.
    Your sole job is to translate complex English medical reports, MRIs, and X-ray summaries into simple, easy-to-understand regional languages for the patient.
    Follow these rules strictly:
    1. STRICT RULE: DO NOT recommend alternative medicines, Ayurvedic herbs, or home remedies. 
    2. STRICT RULE: Always reinforce the doctor's prescribed treatment plan (e.g., Physiotherapy, Surgery, NSAIDs).
    3. Break down complex medical jargon into simple analogies.
    4. Keep the tone clinical, reassuring, and highly respectful of modern evidence-based medicine.
    5. NEVER use numbered lists (1, 2, 3...) for patient details. Use Markdown subheadings (e.g., ### Patient Information) and bullet points.
    """

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

# 1. THEN, generate the prompt using those variables
dynamic_system_prompt = get_system_prompt(mode=selected_mode, language=selected_language)

# 2. Inject it into your existing session state logic
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": dynamic_system_prompt}]
else:
    # Overwrite the old system prompt if the user changed the language or mode
    st.session_state.messages[0] = {"role": "system", "content": dynamic_system_prompt}

# 3. Your existing chat rendering loop
for message in st.session_state.messages:
    if message["role"] == "system":
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

# 1. Listen for Razorpay returning the user to the app after payment
query_params = st.query_params
payment_status = query_params.get("razorpay_payment_link_status")
payment_id = query_params.get("razorpay_payment_id")

if payment_status == "paid":
    st.session_state.premium_unlocked = True
    
    # Securely log it to Supabase so it's on record
    if payment_id and "ledger_logged" not in st.session_state:
        try:
            supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
            supabase.table("claimed_utrs").insert({
                "utr_number": payment_id, 
                "status": "PAID"
            }).execute()
            st.session_state.ledger_logged = True
        except Exception:
            pass # Fails silently without bothering the user


if not st.session_state.premium_unlocked:
    st.info("🔒 **Premium Feature:** Upload a photo of your joint or a medical report for deep visual analysis and get a downloadable PDF. (Fee: ₹49)")
    
    # --- UI STATE 1: GENERATE LINK ---
    if st.session_state.payment_step == "start":
        if st.button("Generate Secure Payment Link", type="primary", use_container_width=True):
            with st.spinner("Connecting to secure payment gateway..."):
                checkout_url = create_payment_link(receipt_id="ACHALA_ORDER_001")
                
                if checkout_url:
                    st.session_state.razorpay_url = checkout_url
                    st.session_state.payment_step = "pending"
                    st.rerun()

    # --- UI STATE 2: WAITING FOR USER TO CLICK ---
    elif st.session_state.payment_step == "pending":
        st.warning("⏳ **Payment link generated!** Click the button below to pay securely.")
        
        # Native Streamlit Link Button for smooth redirect
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
    
    uploaded_file = st.file_uploader(
        "Upload your medical report or joint image here:", 
        type=["png", "jpg", "jpeg"],
        key=f"uploader_{st.session_state.uploader_key}"
    )
    
    if uploaded_file is not None:
        file_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
        if file_hash in st.session_state.analyzed_files:
            st.warning("⚠️ Kindly upload a report or image only once. This is a duplicate.")
            uploaded_file = None 
        else:
            st.success("✅ Image loaded successfully! Please type your symptoms in the chat box below and hit Send to begin.")


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
        if uploaded_file:
            st.image(uploaded_file, width=250)

    message_content = [{"type": "text", "text": user_input}]
    
    if uploaded_file is not None:
        current_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
        if current_hash not in st.session_state.analyzed_files:
            base64_image = encode_image(uploaded_file)
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
                    {"role": "user", "content": message_content} # Your image and text payload
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
                    temperature=0.3, # Keeps the output formatting strict
                )
                
                ai_response = response.choices[0].message.content
                
                st.markdown(ai_response)
                
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
            except Exception as e:
                st.error(f"Error communicating with the Achala Intelligence Engine. Please try again. ({e})")
                
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
                    
                    # Use WeasyPrint to generate the PDF natively with proper text shaping
                    pdf_bytes = HTML(string=report_html).write_pdf()
                    
                    st.download_button(
                        label="📄 Download Official PDF Report",
                        data=pdf_bytes,
                        file_name=f"Achala_Vaidya_Report_{selected_language}.pdf",
                        mime="application/pdf",
                        type="primary"
                    )
                
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
                if uploaded_file is not None:
                    st.session_state.analyzed_files.append(hashlib.md5(uploaded_file.getvalue()).hexdigest())
                    st.session_state.uploader_key += 1
                
            except Exception as e: 
                st.error(f"Error communicating with the Achala Intelligence Engine. Please try again. ({str(e)})")