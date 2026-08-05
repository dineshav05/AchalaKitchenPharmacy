import razorpay
import streamlit as st
from PIL import Image
from openai import OpenAI
import base64
import hashlib
import markdown
from io import BytesIO
from xhtml2pdf import pisa
from supabase import create_client, Client

st.set_page_config(
    page_title="Achala Digital Vaidya | Clinical & Ayurvedic AI",
    page_icon="Achala_Digital_Vaidya_logo.png",  # You can use an emoji OR an image path like "Achala_Digital_Vaidya.png"
    layout="centered",
    initial_sidebar_state="expanded"
)

# Use .get() so it doesn't crash if the key is missing
api_key = st.secrets.get("OPENAI_API_KEY")

if not api_key:
    st.error("OpenAI API Key is missing. Please set it in Streamlit Secrets.")
    st.stop() # Stops the code cleanly without a traceback

# Initialize the client
client = OpenAI(api_key=api_key)

# --- Base64 Image Encoder ---
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# --- Encode Both Logos ---
logo_base64 = get_base64_image("Achala_Digital_Vaidya.png")
allopathic_logo_base64 = get_base64_image("Allopatic_Clinic.png")

# ---------------------------------------------------------
# UNIFIED ROUTING & LANDING PAGE LOGIC (NO SIDEBAR)
# ---------------------------------------------------------

# 1. Initialize memory states so the app remembers user choices
if "clinic_mode" not in st.session_state:
    st.session_state.clinic_mode = None
if "report_language" not in st.session_state:
    st.session_state.report_language = "English"

# 2. Render the Main Landing Page if no mode is selected
if st.session_state.clinic_mode is None:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666; font-weight: bold; letter-spacing: 1px; font-size: 12px;'>ACHALA ECOSYSTEM</p>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; margin-bottom: 30px;'>Digital Clinic Workspace</h1>", unsafe_allow_html=True)
    
    # Center the layout for a clean desktop and mobile view
    col1, col2, col3 = st.columns([1, 10, 1])
    
    with col2:
        # --- STEP 1: Language Selection ---
        st.markdown("### 🌐 Step 1: Choose Report Language")
        st.info("The AI will automatically analyze your medical reports and reply in the language selected below.")
        
        languages = ["English", "Hindi", "Kannada", "Telugu", "Tamil", "Marathi", "Malayalam"]
        
        # Save the language directly into session state
        st.session_state.report_language = st.selectbox(
            "Select Language:",
            languages,
            index=languages.index(st.session_state.report_language),
            label_visibility="collapsed"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- STEP 2: Clinic Selection (Flashcards) ---
        st.markdown("### 🏥 Step 2: Select Operating Mode")
        card_col1, card_col2 = st.columns(2)
        
        # Flashcard 1: Ayurvedic
        with card_col1:
            with st.container(border=True):
                st.markdown("#### 🌿 Achala Digital Vaidya")
                st.write("*Kitchen Pharmacy AI*")
                st.write("Decode your diagnosis. Heal with heritage. An empowering Ayurvedic guide.")
                st.write("") 
                if st.button("Launch Ayurvedic Clinic", key="btn_ayurveda", use_container_width=True):
                    st.session_state.clinic_mode = "Ayurvedic"
                    st.rerun()
                    
        # Flashcard 2: Allopathic
        with card_col2:
            with st.container(border=True):
                st.markdown("#### 🩺 Clinical Translator")
                st.write("*Evidence-Based AI*")
                st.write("Empowering patients through clear, evidence-based medical translations.")
                st.write("")
                if st.button("Launch Allopathic Clinic", key="btn_allopathic", use_container_width=True):
                    st.session_state.clinic_mode = "Allopathic"
                    st.rerun()
                    
    # Stop the rest of the chat UI from loading until a card is clicked
    st.stop()

# 3. Active Chat Header (Replaces the Sidebar Navigation)
# If the user is inside a clinic, show them their current settings and a back button
if st.session_state.clinic_mode is not None:
    nav_col1, nav_col2 = st.columns([3, 1])
    with nav_col1:
        st.markdown(f"<span style='color:#666; font-size: 14px;'>**Mode:** {st.session_state.clinic_mode} &nbsp;|&nbsp; **Language:** {st.session_state.report_language}</span>", unsafe_allow_html=True)
    with nav_col2:
        if st.button("⚙️ Settings", use_container_width=True):
            st.session_state.clinic_mode = None
            st.rerun()
    st.write("---")
    
    # IMPORTANT: Map the session state to your existing language variable 
    # so the rest of your code doesn't break!
    selected_language = st.session_state.report_language

# 1. Define UI Variables and AI Brain Based on Clinic Setup
if clinic_mode == "Ayurvedic (Achala Digital Vaidya)":
    current_logo = logo_base64  
    brand_title = "Achala Digital Vaidya"
    brand_badge = "Kitchen Pharmacy AI"
    brand_caption = '"Decode your diagnosis. Heal with heritage. An empowering Ayurvedic guide to joint and back pain, inspired by Shri Rajiv Dixit Ji."'
    
    # LETTERHEAD VARIABLES
    pdf_hospital_name = "Achala Digital Vaidya"
    pdf_sub_header = "Digital Vaidya • Advanced Visual Analysis Report"
    pdf_footer_text = "Guided by the Ayurvedic principles of Shri Rajiv Dixit Ji."
    
    # The Ayurvedic Brain
    SYSTEM_PROMPT = """
    You are Rajiv Dixit AI, an expert consultant in Ayurveda and Vata-induced joint pain. Your goal is to help the common man reverse chronic back and joint pain using accessible, budget-friendly kitchen remedies.
    Follow these rules strictly:
    1. Identify if the user's symptoms point to a Vata imbalance (e.g., cracking joints, long morning stiffness, shifting body pain).
    2. Recommend affordable home remedies based on Rajiv Dixit's protocols (Parijat decoction, Chuna, Methi Dana).
    3. SAFETY GUARDRAIL: You MUST explicitly check if the user has a history of kidney stones or gallstones BEFORE recommending Chuna (Edible Limestone). If they answer yes, strictly forbid Chuna.
    4. Enforce foundational lifestyle rules: sit down while drinking water (sip by sip), completely eliminate refined oils.
    5. Keep your tone compassionate, simple, and professional.
    6. NEVER use numbered lists (1, 2, 3...) for patient details. Use Markdown subheadings (e.g., ### Patient Information) and bullet points.
    """

else:
    current_logo = allopathic_logo_base64  
    brand_title = "Patient Education & Clinical Translator"
    brand_badge = "Evidence-Based AI"
    brand_caption = '"Empowering patients through clear, evidence-based medical translations and clinical clarity."'
    
    # LETTERHEAD VARIABLES
    pdf_hospital_name = "Clinical Translation Portal"
    pdf_sub_header = "Evidence-Based Medical Analysis Report"
    pdf_footer_text = "Disclaimer: This report is a simplified explanation of complex clinical findings for educational use."
    
    # The Allopathic / Orthopedic Brain (The Trojan Horse)
    SYSTEM_PROMPT = """
    You are a highly professional Clinical Translation Assistant working for an Orthopedic Hospital.
    Your sole job is to translate complex English medical reports, MRIs, and X-ray summaries into simple, easy-to-understand regional languages for the patient.
    Follow these rules strictly:
    1. STRICT RULE: DO NOT recommend alternative medicines, Ayurvedic herbs, or home remedies. 
    2. STRICT RULE: Always reinforce the doctor's prescribed treatment plan (e.g., Physiotherapy, Surgery, NSAIDs).
    3. Break down complex medical jargon (like "osteophyte formation" or "joint space narrowing") into simple analogies.
    4. Keep the tone clinical, reassuring, and highly respectful of modern evidence-based medicine.
    5. NEVER use numbered lists (1, 2, 3...) for patient details. Use Markdown subheadings (e.g., ### Patient Information) and bullet points.
    """

# 2. Inject the variables into a SINGLE dynamic HTML header
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

# Render the dynamic header
st.markdown(dynamic_header_html, unsafe_allow_html=True)

# Initialize or force-sync the active System Prompt inside Session State
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
else:
    # Forcefully update index 0 to match the current sidebar selection
    st.session_state.messages[0] = {"role": "system", "content": SYSTEM_PROMPT}

# --- Render Chat History ---
for message in st.session_state.messages:
    # Skip drawing the system prompt on the screen
    if message["role"] == "system":
        continue

    with st.chat_message(message["role"]):
        # 1. If it's a normal string (like the AI's response or a normal text chat)
        if isinstance(message["content"], str):
            st.markdown(message["content"])
            
        # 2. If it is a complex payload list (like when the user uploads an image)
        elif isinstance(message["content"], list):
            for item in message["content"]:
                if item["type"] == "text":
                    st.markdown(item["text"])
                elif item["type"] == "image_url":
                    st.caption("📎 *Image/Report Attached*")

# ---------------------------------------------------------
# STATE INITIALIZATIONS
# ---------------------------------------------------------
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
# PREMIUM FEATURE: RAZORPAY + SUPABASE LEDGER
# ---------------------------------------------------------
if not st.session_state.premium_unlocked:
    # 1. The Core Value Proposition
    st.info("🔒 **Premium Feature:** Upload a photo of your joint or a medical report for deep visual analysis and get a downloadable PDF. (Fee: ₹49)")
    
    # 2. The Dynamic Language Warning (Highlights their current selection)
    st.warning(f"⚠️ **Important:** Your report will be generated in **{selected_language}**. If you need a different language (like Hindi, Kannada and other regional languages), please select it from the left menu by clicking >> sign *before* paying!")
    
    # Initialize the Razorpay Client safely using .get()
    try:
        razorpay_client = razorpay.Client(
            auth=(st.secrets.get("RAZORPAY_KEY_ID", ""), st.secrets.get("RAZORPAY_KEY_SECRET", ""))
        )
    except Exception:
        st.error("Razorpay API keys missing in Secrets.")
    
    # --- UI STATE 1: GENERATE LINK ---
    if st.session_state.payment_step == "start":
        if st.button("Generate Secure Payment Link", type="primary", use_container_width=True):
            with st.spinner("Connecting to secure payment gateway..."):
                try:
                    payment_data = {
                        "amount": 4900, # 4900 paise = ₹49
                        "currency": "INR",
                        "description": "Achala Digital Vaidya - Premium Analysis",
                        "customer": {"name": "Achala User", "email": "user@achaladigital.com"},
                        "notify": {"sms": False, "email": False},
                        "reminder_enable": False
                    }
                    payment_link = razorpay_client.payment_link.create(payment_data)
                    
                    # Save to memory and move to next step
                    st.session_state.razorpay_link_id = payment_link['id']
                    st.session_state.razorpay_url = payment_link['short_url']
                    st.session_state.payment_step = "pending"
                    st.rerun()
                except Exception as e:
                    st.error("⚠️ Gateway temporarily unavailable. Please check your Razorpay keys and try again.")

    # --- UI STATE 2: WAITING FOR VERIFICATION ---
    elif st.session_state.payment_step == "pending":
        st.warning("⏳ **Payment link generated!** Follow the 2 steps below:")
        
        # HTML button for opening payment gateway in a new tab
        st.markdown(
            f"""
            <div style='text-align:center; padding: 15px;'>
                <a href='{st.session_state.razorpay_url}' target='_blank' 
                   style='font-size: 18px; font-weight: bold; background-color: #007bff; color: white; 
                          padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block;'>
                   1️⃣ Click Here to Pay ₹49 (Opens in new tab)
                </a>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        st.write("---")
        st.markdown("#### 2️⃣ Did you complete the payment?")
        st.write("Once your UPI app says successful, click the verification button below to unlock your report.")
        
        # Verification check
        if st.button("✅ Yes, I have paid. Verify my transaction.", type="primary", use_container_width=True):
            with st.spinner("Checking transaction status with the bank..."):
                try:
                    # Ask Razorpay for the status
                    link_details = razorpay_client.payment_link.fetch(st.session_state.razorpay_link_id)
                    
                    if link_details['status'] == 'paid':
                        # SILENT SUPABASE LEDGER LOGGING
                        try:
                            supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
                            supabase.table("claimed_utrs").insert({
                                "utr_number": link_details['id'], 
                                "status": "PAID"
                            }).execute()
                        except Exception as db_error:
                            pass # Do not block the user if the ledger fails
                        
                        st.session_state.premium_unlocked = True
                        st.session_state.payment_step = "success"
                        st.rerun()
                    else:
                        st.error("⚠️ We haven't received the payment yet. If money was deducted, it may take 30-60 seconds to reflect. Please wait a moment and click verify again.")
                except Exception as e:
                    st.error("Could not reach the payment server. Please try verifying again.")

# ---------------------------------------------------------
# STATE 3: PREMIUM UNLOCKED & FILE UPLOADER
# ---------------------------------------------------------
else:
    st.success("✅ Payment Verified! Premium Features Unlocked.")
    
    # Auto-clearing uploader using the dynamic key
    uploaded_file = st.file_uploader(
        "Upload your medical report or joint image here:", 
        type=["png", "jpg", "jpeg"],
        key=f"uploader_{st.session_state.uploader_key}"
    )
    
    if uploaded_file is not None:
        file_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
        
        # Check if this exact file has already been processed by the AI
        if file_hash in st.session_state.analyzed_files:
            st.warning("⚠️ Kindly upload a report or image only once. This is a duplicate.")
            uploaded_file = None # Nullify it so it doesn't process again
        else:
            st.success("✅ Image loaded successfully! Please type your symptoms in the chat box below and hit Send to begin.")


def encode_image(upload):
    return base64.b64encode(upload.getvalue()).decode('utf-8')


def display_letterhead_report(ai_content, logo_base64_string):
    """Wraps the AI text in a beautiful Achala Enterprises digital letterhead."""
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
    
    # 1. Display user message and uploaded image
    with st.chat_message("user"):
        st.markdown(user_input)
        if uploaded_file:
            st.image(uploaded_file, width=250)

    # 2. Prepare the message content for the AI
    message_content = [{"type": "text", "text": user_input}]
    
    if uploaded_file is not None:
        current_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
        
        # SMART CACHE: Only attach the image to the AI payload if it's brand new
        if current_hash not in st.session_state.analyzed_files:
            base64_image = encode_image(uploaded_file)
            message_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })

    # Save user's message to history
    st.session_state.messages.append({"role": "user", "content": message_content})

    # 3. Generate Assistant Response
    with st.chat_message("assistant"):
        # --- UX FIX: Added a visual spinner so the app doesn't look frozen ---
        with st.spinner("Consulting the Achala Intelligence Engine... Please wait a few seconds."):
            try: 
                # Create a temporary copy of the chat history
                api_messages = st.session_state.messages.copy()
                
                # Inject a strict system command telling the AI to use the user's selected language
                api_messages.append({
                    "role": "system", 
                    "content": f"CRITICAL TRANSLATION RULE: You MUST generate your ENTIRE response, including the report analysis, headings, and Ayurvedic recommendations, strictly in {selected_language}. Ensure medical terms are translated beautifully so the common man can understand."
                })
                
                # Call the AI Engine
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=api_messages,
                    temperature=0.6,
                )
                ai_response = response.choices[0].message.content
                
                if uploaded_file is not None:
                    # Display the premium letterhead in the UI
                    display_letterhead_report(ai_response, current_logo)
                    
                    # Build the printable PDF version
                    structured_html_content = markdown.markdown(ai_response, extensions=['extra', 'sane_lists', 'nl2br'])
                    
                    report_html = f"""
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <style>
                            @page {{ size: a4 portrait; margin: 2cm; }}
                            body {{ font-family: 'Helvetica', sans-serif; color: #2b2b2b; font-size: 14px; line-height: 1.6; }}
                            .content-section h3 {{ color: #0f4c5c; border-bottom: 1px solid #e0e0e0; padding-bottom: 5px; margin-top: 25px; font-size: 18px; }}
                            .content-section ul {{ padding-left: 15px; }}
                            .content-section li {{ margin-bottom: 8px; }}
                            .footer-section {{ text-align: center; font-size: 11px; color: #888; border-top: 1px solid #e0e0e0; padding-top: 15px; margin-top: 40px; }}
                        </style>
                    </head>
                    <body>
                        <table style="width: 100%; border-bottom: 2px solid #0f4c5c; padding-bottom: 10px; margin-bottom: 20px;">
                            <tr>
                                <td style="width: 15%; vertical-align: middle;">
                                    <img src="data:image/png;base64,{current_logo}" width="70">
                                </td>
                                <td style="width: 85%; vertical-align: middle; text-align: left;">
                                    <h2 style="margin: 0; color: #0f4c5c; font-size: 26px; letter-spacing: 0.5px;">{pdf_hospital_name}</h2>
                                    <p style="margin: 3px 0 0 0; color: #666; font-weight: bold; font-size: 13px; text-transform: uppercase;">{pdf_sub_header}</p>
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
                    
                    # Generate the PDF
                    pdf_buffer = BytesIO()
                    pisa_status = pisa.CreatePDF(report_html, dest=pdf_buffer)
                    
                    # Display the Download Button
                    if not pisa_status.err:
                        st.download_button(
                            label="📄 Download Official PDF Report",
                            data=pdf_buffer.getvalue(),
                            file_name="Medical_Analysis_Report.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
                    else:
                        st.error("⚠️ Error generating the PDF report. Please try again.")
                else:
                    # --- BUG FIX: Instantly print the standard text to the screen if no file is uploaded ---
                    st.markdown(ai_response)
                
                # Add assistant response to chat history memory
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
                if uploaded_file is not None:
                    # Save the fingerprint so it can't be uploaded again
                    st.session_state.analyzed_files.append(hashlib.md5(uploaded_file.getvalue()).hexdigest())
                    
                    # Force the file uploader to clear itself for the next run
                    st.session_state.uploader_key += 1
                
            except Exception as e: 
                st.error(f"Error communicating with the Achala Intelligence Engine. Please try again. ({str(e)})")