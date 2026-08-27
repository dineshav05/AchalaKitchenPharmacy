import time
import base64
import hashlib
from io import BytesIO

import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import markdown
from gtts import gTTS

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
# 🧠 AI PROMPT ARCHITECTURE (UPGRADED VISION)
# ==========================================

BASE_SAFETY_CORE = """
You are Achala Digital Vaidya, an educational clinical and radiological literacy assistant.

STRICT SAFETY & QUALITY RULES:
1. EDUCATIONAL ONLY: You do not provide definitive final medical prescriptions, but you MUST provide thorough, detailed, and granular anatomical, radiological, and visual observations to empower patient literacy.
2. UNCERTAINTY HANDLING: If text or image sections are blurry or partially cut off, explicitly state 'This portion is illegible'—NEVER guess.
3. TYPOGRAPHY RULE: DO NOT use emojis anywhere in your response to prevent PDF rendering errors.
"""

MULTIMODAL_VISION_PROTOCOL = """
🔬 ADVANCED RADIOLOGICAL & VISUAL INSPECTION PROTOCOL:
When an X-ray, MRI, CT scan, or clinical photo is uploaded, you MUST perform a thorough, multi-step analysis:

1. 🚨 CRITICAL PATIENT EXTRACTION & EMPATHY RULE:
   - Aggressively scan the ENTIRE document (including bottom footers, borders, and headers) to extract the patient's Name, Age, and Hospital.
   - You are strictly forbidden from starting your response normally. You MUST begin your very first sentence exactly like this: 'Namaste [Name] ji, I have carefully reviewed your report.' (If no name is found, use 'Namaste ji').
   - IMMEDIATELY following the greeting, you MUST write one deeply empathetic sentence acknowledging their specific age and visible pain/symptoms.

2. SYSTEMATIC RADIOLOGICAL ASSESSMENT:
   - Modality & Projections: Identify exact views.
   - Cortical & Bone Alignment: Review each visible bone, noting alignment, joint space preservation, and fracture lines.
   - Soft Tissue Shadows: Note any soft tissue swelling or density.

3. CLINICAL PHOTOGRAPH CORRELATION:
   - Describe visible swelling, contour deformity, and localized bruising.
   - Correlate external bruising with underlying radiographic bony structures.

4. STRUCTURED QUESTIONS FOR THE DOCTOR:
   - Provide 2-3 specific, high-yield questions the patient should ask their treating orthopedic doctor.
"""

ACUTE_TRAUMA_TRIAGE = """
🚨 ACUTE TRAUMA TRIAGE PROTOCOL:
If the user describes a sudden accident, fall, acute impact, or sudden severe swelling:
* Deploy Ottawa Rules Assessment: Note weight-bearing capability (4 steps), localized bony tenderness, and range of motion.
* Allopathic Mode: Recommend immediate R.I.C.E. protocol (Rest, Ice, Compression, Elevation), immobilisation, and urgent physical review by an orthopedic clinician.
* Ayurvedic Mode: Offer soothing first-aid comfort (turmeric/herbal poultices) while strictly reiterating that bone integrity and ligamentous stability require clinical confirmation.
"""

PERSONA_ALLOPATHY = """
TONE: Objective, analytical, precise, and clinical yet easy for a patient to understand.

OUTPUT STRUCTURE:
You must format your response with the following translated headings:
### Patient & Study Details
[Extracted Name, Age, Study Date, Hospital/Clinic Name, Study Type & Views]

### Detailed Visual & Radiographic Observations
[Systematic breakdown of: 1) Physical Photo Findings (swelling, ecchymosis pattern); 2) Radiographic Findings (bone by bone alignment, metatarsals, phalanges, joint spaces, cortical margins)]

### Clinical Interpretation & Trauma Context
[Clear explanation of the injury pattern (e.g., severe soft tissue contusion/sprain vs potential non-displaced fracture/Lisfranc strain), explaining mechanisms and implications]

### Immediate Care & Red Flags
[R.I.C.E. protocol, signs of compartment syndrome/neurovascular compromise, weight-bearing guidance]

### Questions for Your Orthopedic Doctor
[Bullet points of precise clinical questions to ask during examination]
"""

PERSONA_AYURVEDA = """
TONE: Empathetic, warm, holistic, and wise, guided by Shri Rajiv Dixit Ji's principles of natural care.

OUTPUT STRUCTURE:
You must format your response with the following translated headings:
### Patient & Study Details
[Extracted Name, Age, Study Date, Study Type & Anatomy]

### Educational Breakdown of Injury & Scans
[Simple explanation of the bone alignment, swelling, and blood pooling/ecchymosis in plain terms]

### Emergency Holistic Comfort & Kitchen Pharmacy
[Immediate soothing, cooling/alkalizing first-aid alignments, anti-inflammatory food protocols]

### Lifestyle, Rest & Recovery Guidelines
[Elevation, zero weight-bearing on acute injury, proper rest rules]

### When to Consult a Specialist
[Clear guidance on urgent orthopedic follow-up and clinical monitoring]
"""

def get_system_prompt(mode: str, language: str) -> str:
    persona = PERSONA_AYURVEDA if mode == "Ayurvedic" else PERSONA_ALLOPATHY
    language_directive = f"\n\nCRITICAL LANGUAGE RULE: You MUST translate and output the ENTIRE response, including all structural headings and body text, exclusively in {language}. Do not include the original English headings."
    
    return BASE_SAFETY_CORE + "\n" + MULTIMODAL_VISION_PROTOCOL + "\n" + ACUTE_TRAUMA_TRIAGE + "\n" + persona + language_directive

# ==========================================
# RAZORPAY REST API (Dynamic Pricing added)
# ==========================================
def create_payment_link(receipt_id, customer_name="Patient", mode="Allopathic", lang="English", app_mode="Workspace"):
    url = "https://api.razorpay.com/v1/payment_links"
    unique_ref_id = f"ACHALA_ORDER_{int(time.time())}"

    # ⚡ Dynamic Pricing: ₹99 for Triage (9900 paise), ₹49 for Workspace (4900 paise)
    price_in_paise = 9900 if app_mode == "Triage" else 4900

    callback_url = f"https://achala-digital-vaidya.streamlit.app/?clinic_mode={mode}&report_language={lang}&app_mode={app_mode}"

    payload = {
        "amount": price_in_paise,
        "currency": "INR",
        "accept_partial": False,
        "description": f"Achala Digital Vaidya - {app_mode} Analysis",
        "reference_id": unique_ref_id,
        "customer": {"name": customer_name},
        "notify": {"sms": False, "email": False},
        "reminder_enable": False,
        "callback_url": callback_url, 
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

st.markdown("""
    <style>
    /* Main Layout & Glowing Ecosystem Badge */
    .ecosystem-wrapper { display: flex; justify-content: center; width: 100%; margin-bottom: 15px; }
    .ecosystem-header { 
        color: #ffffff; 
        font-weight: 800; 
        letter-spacing: 1.5px; 
        font-size: 11px; 
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 8px 20px; 
        border-radius: 20px; 
        text-transform: uppercase; 
        box-shadow: 0 0 10px rgba(42, 82, 152, 0.5);
    }
    .main-header { text-align: center; margin-bottom: 35px; font-weight: 900; color: #ffffff; letter-spacing: -0.5px; }
    
    /* 🔥 Upgraded Emergency Pulse for Dark Mode */
    @keyframes highAlertPulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 75, 75, 0.8), 0 0 15px rgba(255, 75, 75, 0.2) inset; }
        70% { box-shadow: 0 0 0 22px rgba(255, 75, 75, 0), 0 0 5px rgba(255, 75, 75, 0) inset; }
        100% { box-shadow: 0 0 0 0 rgba(255, 75, 75, 0), 0 0 0 rgba(255, 75, 75, 0) inset; }
    }

    /* 🚨 Triage Card - High Visibility Red */
    .vibrant-card-triage { 
        background: linear-gradient(145deg, #3a1212 0%, #1a0808 100%); 
        border: 2px solid #ff4b4b; 
        border-radius: 24px; 
        padding: 30px 20px; 
        margin-bottom: 15px; 
        text-align: center; 
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1); 
        animation: highAlertPulse 1.8s infinite;
    }
    .vibrant-card-triage:hover { 
        transform: translateY(-6px); 
        box-shadow: 0 15px 35px rgba(255, 75, 75, 0.6), 0 0 20px rgba(255, 75, 75, 0.3) inset;
        border-color: #ff7373;
    }

    /* 🩺 Allopathic Card - Clinical Blue */
    .vibrant-card-allopathic { 
        background: linear-gradient(145deg, #111b24 0%, #090e13 100%); 
        border: 2px solid #2980b9; 
        border-radius: 24px; 
        padding: 30px 20px; 
        margin-bottom: 15px; 
        text-align: center; 
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1); 
    }
    .vibrant-card-allopathic:hover { 
        transform: translateY(-6px); 
        box-shadow: 0 15px 30px rgba(52, 152, 219, 0.4);
        border-color: #3498db;
    }

    /* 🌿 Ayurvedic Card - Nature Green */
    .vibrant-card-ayurveda { 
        background: linear-gradient(145deg, #0a1f12 0%, #040d07 100%); 
        border: 2px solid #27ae60; 
        border-radius: 24px; 
        padding: 30px 20px; 
        margin-bottom: 15px; 
        text-align: center; 
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1); 
    }
    .vibrant-card-ayurveda:hover { 
        transform: translateY(-6px); 
        box-shadow: 0 15px 30px rgba(46, 204, 113, 0.3);
        border-color: #2ecc71;
    }

    /* Universal Typography & Depth */
    .card-icon { font-size: 55px; margin-bottom: 15px; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.6)); }
    .card-title { font-weight: 900; font-size: 20px; margin-bottom: 8px; letter-spacing: -0.3px; color: #ffffff; }
    .card-subtitle { font-style: normal; font-weight: 600; font-size: 13px; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 0.5px; }
    .card-description { color: #cbd5e1; font-size: 14px; line-height: 1.6; margin-bottom: 0px; font-weight: 500;}
    
    /* Premium Button Overrides */
    button[kind="primary"] { border-radius: 14px !important; font-weight: bold !important; padding-top: 10px !important; padding-bottom: 10px !important; }
    button[kind="secondary"] { border-radius: 14px !important; font-weight: bold !important; padding-top: 10px !important; padding-bottom: 10px !important; border: 2px solid #4a5568 !important; background-color: #2d3748 !important; color: #ffffff !important; transition: all 0.2s ease; }
    button[kind="secondary"]:hover { border-color: #718096 !important; background-color: #4a5568 !important; }
    </style>
    """, unsafe_allow_html=True)


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
query_params = st.query_params

if "app_mode" in query_params:
    st.session_state.app_mode = query_params.get("app_mode")
if "clinic_mode" in query_params:
    st.session_state.clinic_mode = query_params.get("clinic_mode")
if "report_language" in query_params:
    st.session_state.report_language = query_params.get("report_language")

if "app_mode" not in st.session_state:
    st.session_state.app_mode = None
if "clinic_mode" not in st.session_state:
    st.session_state.clinic_mode = None
if "report_language" not in st.session_state:
    st.session_state.report_language = "English"

def set_app_mode(mode):
    st.session_state.app_mode = mode

def set_clinic_mode(mode):
    st.session_state.clinic_mode = mode

# GATEWAY 1: Select Triage or Workspace
if st.session_state.app_mode is None:
    st.markdown("""
        <div class='ecosystem-wrapper'>
            <div class='ecosystem-header'>ACHALA ECOSYSTEM</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("<h2 class='main-header'>How can we help you today?</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
            <div class='vibrant-card-triage'>
                <div class='card-icon'>🚨</div>
                <div class='card-title' style='color: #c0392b;'>Acute Trauma Triage</div>
                <div class='card-subtitle' style='color: #e74c3c;'>Emergency & Injury Assessment</div>
                <div class='card-description'>Immediate AI triage for sudden accidents, falls, sprains, or severe swelling.</div>
            </div>
            """, unsafe_allow_html=True)
        st.button("Launch Triage Companion", key="btn_triage", use_container_width=True, type="primary", on_click=set_app_mode, args=("Triage",))

    with col2:
        st.markdown("""
            <div class='vibrant-card-allopathic'>
                <div class='card-icon'>🩺</div>
                <div class='card-title'>Digital Clinical Workspace</div>
                <div class='card-subtitle' style='color: #3498db;'>Chronic Care & Diagnostics</div>
                <div class='card-description'>Decode medical reports and explore Ayurvedic or Allopathic care plans.</div>
            </div>
            """, unsafe_allow_html=True)
        st.button("Launch Clinical Workspace", key="btn_workspace", use_container_width=True, on_click=set_app_mode, args=("Workspace",))
        
    st.stop()

# GATEWAY 2: Workspace Setup (If Workspace Selected)
if st.session_state.app_mode == "Workspace" and st.session_state.clinic_mode is None:
    
    # 🟢 FIX: Added Back Button to navigate from Workspace Setup back to Main Gateway
    if st.button("⬅️ Back to Main Menu"):
        st.session_state.app_mode = None
        st.rerun()

    st.markdown("<h1 class='main-header'>Digital Clinic Workspace</h1>", unsafe_allow_html=True)
    
    with st.expander("🩺 Understanding Your Care: Kitchen Pharmacy vs. Clinical Reality"):
        st.markdown("""
        **Modern diseases often require modern medicine to save a life, but ancient wisdom is required to sustain it. Here is how Achala Digital Vaidya supports your journey:**

        * **Metabolic & Diabetes:** We guide you toward low-GI millets and metabolic balancing. *Clinical Reality:* You must continue medical monitoring for HbA1c levels.
        * **Autoimmune & Arthritis:** We provide alkalizing, root-cause diets to reduce inflammation. *Clinical Reality:* Acute flare-ups require clinical management to prevent joint damage.
        * **Severe Illness (e.g., Cancer):** We strictly offer foundational support for bodily resilience. *Clinical Reality:* Advanced oncology, surgery, and clinical care are absolutely **mandatory**.
        * **Chronic Wear & Tear:** We suggest natural lubrication and calcium alignments. *Clinical Reality:* End-stage structural degradation may require medical intervention.
        
        *We decode your clinical reports so you understand your doctor's plan, while providing the traditional Ayurvedic lifestyle habits needed to support your foundational healing.*
        """)

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

# GATEWAY 3: Triage Setup (Forces Allopathic for Safety)
# GATEWAY 3.1: Triage Setup (Language Selection)
if st.session_state.app_mode == "Triage" and st.session_state.clinic_mode is None:
    if st.button("⬅️ Back to Main Menu"):
        st.session_state.app_mode = None
        st.rerun()

    st.markdown("<h1 class='main-header'>🚨 Emergency Trauma Triage</h1>", unsafe_allow_html=True)
    st.info("For immediate assistance, please select your preferred language below.")
    
    col1, col2, col3 = st.columns([1, 10, 1])
    with col2:
        languages = ["English", "Hindi", "Kannada", "Telugu", "Tamil", "Marathi", "Malayalam"]
        st.session_state.report_language = st.selectbox(
            "Select Language:",
            languages,
            index=languages.index(st.session_state.report_language),
            label_visibility="collapsed"
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Enter Triage Workspace", type="primary", use_container_width=True):
            st.session_state.clinic_mode = "Allopathic"
            st.rerun()
    st.stop()


# ---------------------------------------------------------
# ACTIVE CLINIC / TRIAGE WORKSPACE
# ---------------------------------------------------------
if st.session_state.clinic_mode is not None:
    nav_col1, nav_col2 = st.columns([3, 1])
    with nav_col1:
        st.markdown(f"<span style='color:#666; font-size: 14px;'>**Mode:** {st.session_state.app_mode} - {st.session_state.clinic_mode} &nbsp;|&nbsp; **Language:** {st.session_state.report_language}</span>", unsafe_allow_html=True)
    with nav_col2:
        if st.button("⬅️ Back to Main Menu", use_container_width=True):
            st.session_state.clinic_mode = None
            st.session_state.app_mode = None
            st.rerun()
    st.write("---")
    
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
else:
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

# ---------------------------------------------------------
# SESSION STATE INITIALIZATION & RESET LOGIC
# ---------------------------------------------------------
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
if "generated_pdf" not in st.session_state:
    st.session_state.generated_pdf = None 

def reset_for_next_patient():
    st.session_state.premium_unlocked = False
    st.session_state.payment_step = "completed"
    st.session_state.messages = [] 
    st.session_state.generated_pdf = None 
    st.session_state.uploader_key += 1


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
uploaded_files = None

query_params = st.query_params
payment_status = query_params.get("razorpay_payment_link_status")
payment_id = query_params.get("razorpay_payment_id")

if payment_status == "paid":
    st.session_state.premium_unlocked = True
    
    if "ledger_logged" not in st.session_state:
        if not payment_id:
            st.error("🚨 DEBUG: Payment status is 'paid', but 'razorpay_payment_id' is missing from the URL!")
            st.stop()
            
        supabase = init_supabase_client()
        if supabase is None:
            st.error("🚨 DEBUG: Supabase Client is None! Check your Streamlit Cloud Secrets for SUPABASE_URL and SUPABASE_KEY.")
            st.stop()
        else:
            try:
                supabase.table("claimed_utrs").insert({
                    "utr_number": str(payment_id), 
                    "status": "PAID"
                }).execute()
                st.session_state.ledger_logged = True
            except Exception as e:
                st.error(f"🚨 DEBUG Database Error: {e}")
                st.stop()
            
    st.query_params.clear()


# ---------------------------------------------------------
# STATE MANAGEMENT: PREMIUM UNLOCKED & FILE UPLOADER
# ---------------------------------------------------------

if st.session_state.app_mode == "Triage":
    st.markdown("### 🚨 Emergency Triage Companion")
    st.info("Describe your injury in the chat box below for immediate, free triage guidance. Your emergency PDF report will be generated for free.")
    
    if not st.session_state.premium_unlocked:
        # 🟢 FIX: Added expanded=True to keep accordion open by default
        with st.expander("📸 Unlock Visual & X-Ray Analysis (₹99)", expanded=True):
            st.markdown("Upload a photo of the swelling or a clinic X-ray report for immediate AI decoding.")
            
            if st.session_state.payment_step == "start":
                if st.button("Generate Secure Payment Link (₹99)", type="primary", key="triage_pay_btn"):
                    with st.spinner("Connecting to secure payment gateway..."):
                        checkout_url = create_payment_link(
                            receipt_id="ACHALA_TRIAGE_001",
                            mode="Allopathic", 
                            lang=st.session_state.report_language,
                            app_mode="Triage"
                        )
                        if checkout_url:
                            st.session_state.razorpay_url = checkout_url
                            st.session_state.payment_step = "pending"
                            st.rerun()
                            
            elif st.session_state.payment_step == "pending":
                st.warning("⏳ **Payment link generated!** Click below to pay securely.")
                st.link_button("Proceed to Pay ₹99", st.session_state.razorpay_url, type="primary", use_container_width=True)
                if st.button("Cancel", key="cancel_triage_btn"):
                    st.session_state.payment_step = "start"
                    st.rerun()
                    
            elif st.session_state.payment_step == "completed":
                 if st.button("Analyze Another Report", type="primary"):
                     st.session_state.payment_step = "start"
                     st.rerun()
    else:
        st.success("✅ Payment Verified! Premium Visual Triage Unlocked.")
        uploaded_files = st.file_uploader(
            "Upload emergency image or report", 
            type=["png", "jpg", "jpeg"], 
            accept_multiple_files=True,
            key=f"uploader_{st.session_state.uploader_key}"
        )

elif st.session_state.app_mode == "Workspace":
    if not st.session_state.premium_unlocked:
        st.info("🔒 **Premium Feature:** Upload a photo of your joint or a medical report for deep visual analysis and get a downloadable PDF. (Fee: ₹49)")
        
        if st.session_state.payment_step == "start":
            if st.button("Generate Secure Payment Link (₹49)", type="primary", use_container_width=True):
                with st.spinner("Connecting to secure payment gateway..."):
                    checkout_url = create_payment_link(
                        receipt_id="ACHALA_ORDER_001",
                        mode=st.session_state.clinic_mode,
                        lang=st.session_state.report_language,
                        app_mode="Workspace"
                    )
                    if checkout_url:
                        st.session_state.razorpay_url = checkout_url
                        st.session_state.payment_step = "pending"
                        st.rerun()

        elif st.session_state.payment_step == "completed":
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
    else:
        st.success("✅ Payment Verified! Premium Features Unlocked.")
        uploaded_files = st.file_uploader(
            "Upload your medical report(s) or joint image(s) here:", 
            type=["png", "jpg", "jpeg"], 
            accept_multiple_files=True,
            key=f"uploader_{st.session_state.uploader_key}"
        )

# Ensure duplicate check and success prompt applies to both modes if unlocked
if uploaded_files:
    all_new = True
    current_batch_hashes = set() 
    
    for file in uploaded_files:
        file_hash = hashlib.md5(file.getvalue()).hexdigest()
        if file_hash in st.session_state.analyzed_files or file_hash in current_batch_hashes:
            st.warning(f"⚠️ Duplicate detected: {file.name}. Please remove the duplicate.")
            all_new = False
        current_batch_hashes.add(file_hash)
            
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
            for file in uploaded_files:
                st.image(file, width=250)

    message_content = [{"type": "text", "text": user_input}]
    
    if uploaded_files:
        for file in uploaded_files:
            current_hash = hashlib.md5(file.getvalue()).hexdigest()
            if current_hash not in st.session_state.analyzed_files:
                base64_image = encode_image(file)
                message_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                })

    st.session_state.messages.append({"role": "user", "content": message_content})

    with st.chat_message("assistant"):
        with st.spinner("Consulting the Achala Intelligence Engine... Please wait a few seconds."):
            try: 
                dynamic_prompt = get_system_prompt(mode=selected_mode, language=selected_language)
                
                api_messages = [
                    {"role": "system", "content": dynamic_prompt},
                    {"role": "user", "content": message_content} 
                ]
                
                api_messages.append({
                    "role": "system", 
                    "content": f"CRITICAL INSTRUCTION: You are fully capable of speaking {selected_language}. The user requires this English medical document to be translated and explained entirely in {selected_language}. You MUST generate your ENTIRE response, including all headings, Ayurvedic remedies, and clinical explanations, strictly in {selected_language}. Do not output English."
                })
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=api_messages,
                    temperature=0.3, 
                )
                
                ai_response = response.choices[0].message.content
                
                st.markdown(ai_response)
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
                # ==============================================================
                # AUDIO GENERATION (gTTS)
                # ==============================================================
                gtts_language_codes = {
                    "English": "en",
                    "Hindi": "hi",
                    "Kannada": "kn",
                    "Telugu": "te",
                    "Tamil": "ta",
                    "Marathi": "mr",
                    "Malayalam": "ml"
                }

                audio_lang = gtts_language_codes.get(selected_language, "en")

                # Convert the AI response to speech
                tts = gTTS(text=ai_response, lang=audio_lang, slow=False)
                
                # Save to a temporary buffer
                audio_buffer = BytesIO()
                tts.write_to_fp(audio_buffer)
                audio_buffer.seek(0)
                
                # Display the audio player in the Streamlit UI
                st.markdown(f"**Listen to your report in {selected_language}:**")
                st.audio(audio_buffer, format="audio/mp3")

                # ==============================================================
                # PDF GENERATION 
                # ==============================================================
                if st.session_state.premium_unlocked: 
                    display_letterhead_report(ai_response, current_logo)
                    structured_html_content = markdown.markdown(ai_response, extensions=['extra', 'sane_lists', 'nl2br'])
                    
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
                                background-color: #fcfcfc;
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
                                border-bottom: 3px solid #e74c3c; 
                                padding-bottom: 12px;
                                margin-bottom: 20px;
                                table-layout: fixed;
                            }}
                            .english-header h2 {{ 
                                font-family: 'Helvetica', 'Arial', sans-serif !important;
                                margin: 0; 
                                color: #2c3e50; 
                                font-size: 24px; 
                                font-weight: 900;
                                letter-spacing: -0.5px;
                            }}
                            .english-header p {{ 
                                font-family: 'Helvetica', 'Arial', sans-serif !important;
                                margin: 4px 0 0 0; 
                                color: #e74c3c; 
                                font-size: 12px; 
                                font-weight: bold;
                                text-transform: uppercase;
                                letter-spacing: 1px;
                            }}
                            
                            /* Vibrant Content Sections with SVG Icons */
                            .content-section h3 {{ 
                                background-color: #2c3e50; /* Deep Medical Navy */
                                color: #ffffff; 
                                padding: 10px 15px 10px 42px; /* Left padding makes room for icon */
                                margin-top: 25px; 
                                font-size: 15px; 
                                border-radius: 6px;
                                text-transform: uppercase;
                                letter-spacing: 0.5px;
                                background-repeat: no-repeat;
                                background-position: 12px center;
                                background-size: 20px 20px;
                            }}
                            
                            /* Dynamically map icons based on heading order (Works across all languages!) */
                            /* Icon 1: Summary/Patient Details (Clipboard) */
                            .content-section h3:nth-of-type(1) {{ background-image: url('data:image/svg+xml;utf8,<svg fill="%23ffffff" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>'); }}
                            
                            /* Icon 2: Observations/Aahara (Magnifying Glass/Search) */
                            .content-section h3:nth-of-type(2) {{ background-image: url('data:image/svg+xml;utf8,<svg fill="%23ffffff" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>'); }}
                            
                            /* Icon 3: Clinical Context/Vihara (Star/Lightbulb) */
                            .content-section h3:nth-of-type(3) {{ background-image: url('data:image/svg+xml;utf8,<svg fill="%23ffffff" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zm4.24 16L12 15.45 7.77 18l1.12-4.81-3.73-3.23 4.92-.42L12 5l1.92 4.53 4.92.42-3.73 3.23L16.23 18z"/></svg>'); }}
                            
                            /* Icon 4: Red Flags/Seek Care (Warning Alert - Overrides background to Red) */
                            .content-section h3:nth-of-type(4) {{ background-color: #c0392b; background-image: url('data:image/svg+xml;utf8,<svg fill="%23ffffff" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>'); }}
                            
                            /* Icon 5: Doctor Questions (Chat Bubbles) */
                            .content-section h3:nth-of-type(5) {{ background-image: url('data:image/svg+xml;utf8,<svg fill="%23ffffff" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 9h12v2H6V9zm8 5H6v-2h8v2zm4-6H6V6h12v2z"/></svg>'); }}

                            /* Color-coded Content Lists */
                            .content-section ul {{
                                background-color: #ffffff;
                                border-left: 5px solid #3498db;
                                padding: 15px 15px 15px 40px;
                                border-radius: 0 8px 8px 0;
                                box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                                margin-bottom: 15px;
                            }}
                            .content-section li {{ margin-bottom: 8px; }}
                            .content-section strong {{ color: #c0392b; }}
                            
                            /* Footer Upgrades */
                            .footer-section {{ 
                                text-align: center; 
                                border-top: 2px dashed #bdc3c7; 
                                padding-top: 15px; 
                                margin-top: 40px; 
                            }}
                            .footer-brand {{
                                color: #e74c3c;
                                font-size: 14px;
                                font-weight: 900;
                                text-transform: uppercase;
                                letter-spacing: 1px;
                                margin-bottom: 5px;
                                font-family: 'Helvetica', 'Arial', sans-serif !important;
                            }}
                            .footer-disclaimer {{
                                font-size: 11px;
                                color: #7f8c8d;
                                font-weight: bold;
                                margin: 0;
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
                            <div class="footer-brand">Generated by Achala Digital Vaidya</div>
                            <div class="footer-disclaimer">{pdf_footer_text}</div>
                        </div>
                    </body>
                    </html>
                    """
                    
                    # ⚡ LAZY LOAD WEASYPRINT HERE
                    from weasyprint import HTML
                    pdf_bytes = HTML(string=report_html).write_pdf()
                    
                    # Save PDF to memory
                    st.session_state.generated_pdf = pdf_bytes

                    if uploaded_files:
                        for file in uploaded_files:
                            st.session_state.analyzed_files.append(hashlib.md5(file.getvalue()).hexdigest())
                    
                    st.session_state.uploader_key += 1
                    st.rerun() 
                
            except Exception as e: 
                st.error(f"Error communicating with the Achala Intelligence Engine. Please try again. ({str(e)})")

# ==========================================
# PERSISTENT DOWNLOAD BUTTON
# ==========================================
if st.session_state.generated_pdf is not None:
    st.markdown("---")
    st.download_button(
        label="📄 Download Official PDF Report",
        data=st.session_state.generated_pdf,
        file_name=f"Achala_Vaidya_Report_{selected_language}.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
        on_click=reset_for_next_patient
    )

# ==========================================
# FOOTER & COMPLIANCE LINKS
# ==========================================
st.write("---") 

foot_col1, foot_col2, foot_col3, foot_col4 = st.columns(4)

with foot_col1:
    st.page_link("pages/Contact_Us.py", label="Contact Us", icon="📞")
with foot_col2:
    st.page_link("pages/Terms_and_Conditions.py", label="Terms & Conditions", icon="📜")
with foot_col3:
    st.page_link("pages/Privacy_Policy.py", label="Privacy Policy", icon="🔒")
with foot_col4:
    st.page_link("pages/Refund_Policy.py", label="Refund Policy", icon="💳")

st.markdown(
    """
    <div style='text-align: center; color: #888888; margin-top: 20px; font-size: 12px;'>
        © 2026 Achala Enterprises. All rights reserved.
    </div>
    """, 
    unsafe_allow_html=True
)