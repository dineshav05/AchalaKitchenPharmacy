import streamlit as st
from PIL import Image
from openai import OpenAI
import base64
import hashlib
import markdown
from io import BytesIO
from xhtml2pdf import pisa


# Pull the key directly from Streamlit's encrypted secrets dictionary
api_key = st.secrets["OPENAI_API_KEY"]

# Initialize the client
client = OpenAI(api_key=api_key)

# 1. Initialize the OpenAI Client Safely
# This tells the code to look for the key in Streamlit's secure dashboard, NOT in the code.

# --- 3. Base64 Image Encoder ---
def get_base64_image(image_path):
    import base64
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# --- 4. Encode Both Logos ---
logo_base64 = get_base64_image("Achala_Digital_Vaidya.png")
allopathic_logo_base64 = get_base64_image("Allopatic_Clinic.png")

# --- Sidebar Settings ---
with st.sidebar:
    st.title("⚙️ Preferences")
    selected_language = st.selectbox(
        "🌐 Choose Report Language:",
        ["English", "Hindi (हिंदी)", "Kannada (ಕನ್ನಡ)", "Tamil (தமிழ்)", "Telugu (తెలుగు)", "Marathi (मराठी)", "Gujarati (ગુજરાતી)", "Bengali (বাংলা)"]
    )
    st.info(f"The Digital Vaidya & Clinical Translator will automatically analyze your reports and reply in **{selected_language}**.")


# --- CLINIC ADMINISTRATOR SETTINGS ---
with st.sidebar:
    st.markdown("### ⚙️ Clinic Setup")
    clinic_mode = st.radio(
        "Select Operating Mode:",
        ["Ayurvedic (Achala Digital Vaidya)", "Allopathic (Clinical Translator)"]
    )

# 1. Define UI Variables and AI Brain Based on Clinic Setup
if clinic_mode == "Ayurvedic (Achala Digital Vaidya)":
    current_logo = logo_base64  
    brand_title = "Achala Digital Vaidya"
    brand_badge = "Kitchen Pharmacy AI"
    brand_caption = '"Decode your diagnosis. Heal with heritage. An empowering Ayurvedic guide to joint and back pain, inspired by Shri Rajiv Dixit Ji."'
    
    # 🚨 NEW LETTERHEAD VARIABLES
    pdf_hospital_name = "Achala Enterprises"
    pdf_sub_header = "Digital Vaidya • Advanced Visual Analysis Report"
    pdf_footer_text = "Guided by the Ayurvedic principles of Shri Rajiv Dixit Ji."
    
    # 🧠 The Ayurvedic Brain
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
    
    # 🚨 NEW LETTERHEAD VARIABLES
    pdf_hospital_name = "Clinical Translation Portal"
    pdf_sub_header = "Evidence-Based Medical Analysis Report"
    pdf_footer_text = "Disclaimer: This report is a simplified explanation of complex clinical findings for educational use."
    
    # 🧠 The Allopathic / Orthopedic Brain (The Trojan Horse)
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
    # 🚨 THE BRAIN FIX: Forcefully update index 0 to match the current sidebar selection!
    st.session_state.messages[0] = {"role": "system", "content": SYSTEM_PROMPT}

# --- Render Chat History ---
for message in st.session_state.messages:
    
    # 🚨 THE FIX: Skip drawing the system prompt on the screen!
    if message["role"] == "system":
        continue

    with st.chat_message(message["role"]):
        
        # 1. If it's a normal string (like the AI's response or a normal text chat)
        if isinstance(message["content"], str):
            st.markdown(message["content"])
            
        # 2. If it is a complex payload list (like when the user uploads an image)
        elif isinstance(message["content"], list):
            for item in message["content"]:
                # Only print the text portion of the payload to the screen
                if item["type"] == "text":
                    st.markdown(item["text"])
                # We hide the massive base64 image string and just show a neat little tag
                elif item["type"] == "image_url":
                    st.caption("📎 *Image/Report Attached*")

# 1. Initialize a memory bank for processed files
if "processed_files" not in st.session_state:
    st.session_state.processed_files = []

# 1. Initialize states for payment tracking
if "premium_unlocked" not in st.session_state:
    st.session_state.premium_unlocked = False #True for no validate
if "show_qr" not in st.session_state:
    st.session_state.show_qr = False #True for no validate

# --- THE FIX: Initialize the variable as empty for free users ---
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

# 2. Check if the user has paid
if not st.session_state.premium_unlocked:
    st.info("🔒 **Premium Feature:** Upload a photo of your joint or a medical report for deep visual analysis and tailored dietary matching.")
    if not st.session_state.show_qr:
        pay_col, info_col = st.columns([1, 2], vertical_alignment="center")
        with pay_col:
            if st.button("Unlock Feature (₹49)"):
                st.session_state.show_qr = True
                st.rerun()
        with info_col:
            st.caption("⚡ One-time fee per analysis. Pay securely via any UPI App (GPay, PhonePe, Paytm).")
            
    else:
        qr_col, text_col = st.columns([1, 1])
        with qr_col:
            st.image("QRCODE.jpeg", width=250)
        with text_col:
            st.write("### Complete Your Payment")
            st.write("1. Open **GPay, PhonePe, or Paytm** on your phone.")
            st.write("2. Scan the QR code or send **₹49** directly to:")
            st.code("dinesha.vishwanatha05-2@okaxis")
            
            st.write("---")
            st.write("### 🔐 Verify Transaction")
            
            # Form forces the input before execution
            with st.form("payment_verification_form"):
                utr_input = st.text_input(
                    "Enter 12-Digit UPI Ref No. / UTR ID:", 
                    placeholder="e.g., 3145XXXXXXXX",
                    max_chars=12
                )
                submit_verification = st.form_submit_button("Submit & Unlock Dashboard")
                
                if submit_verification:
                    # Clean up the input text
                    clean_utr = utr_input.strip()
                    
                    # Basic Validation: Ensure it is a 12-digit number common to Indian UPI systems
                    if len(clean_utr) == 12 and clean_utr.isdigit():
                        st.session_state.premium_unlocked = True
                        
                        # In your logs dashboard, you will see who submitted what key
                        # Perfect for checking your bank statement later
                        st.toast(f"UTR Submitted for verification: {clean_utr}") 
                        st.success("UTR Recorded! Opening Dashboard...")
                        st.rerun()
                    else:
                        st.error("❌ Invalid Transaction ID. Please enter the full 12-digit numerical UTR found in your UPI app receipt.")

else:
    # This section unlocks ONLY after a successful payment
    st.success("🔓 **Premium Active:** Visual Analysis Enabled")
    
   # 2. The File Uploader
    uploaded_file = st.file_uploader("Upload a photo of your joint or a medical report (PNG, JPG)", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        import hashlib
        file_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
        
        # Initialize memory for analyzed files if it doesn't exist
        if "analyzed_files" not in st.session_state:
            st.session_state.analyzed_files = []
            
        # Check if this exact file has already been processed by the AI
        if file_hash in st.session_state.analyzed_files:
            st.warning("⚠️ Kindly upload a report or image only once. This is a duplicate.")
        else:
            st.success("✅ Image loaded successfully! Please type your symptoms in the chat box below and hit Send to begin.")
            
    def encode_image(upload):
        import base64
        return base64.b64encode(upload.getvalue()).decode('utf-8')


# Place this function near the top of your file with your other functions
def display_letterhead_report(ai_content, logo_base64_string):
    """Wraps the AI text in a beautiful Achala Enterprises digital letterhead."""
    
    # Notice how the HTML touches the absolute left edge. No spaces!
    letterhead_html = f"""
<div style="border: 2px solid #0f4c5c; border-radius: 8px; padding: 25px; background-color: #ffffff; color: #2b2b2b; font-family: 'Arial', sans-serif; box-shadow: 0px 4px 15px rgba(0,0,0,0.05); margin-top: 20px;">
    <div style="display: flex; align-items: center; border-bottom: 2px solid #004d40; padding-bottom: 15px; margin-bottom: 20px;">
        <img src="data:image/png;base64,{current_logo}" width="70" style="margin-right: 20px; border-radius: 50%;">
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

# 6. Handle User Input
# --- The Chat Input and AI Execution Block ---
if user_input := st.chat_input("Describe your pain or upload an image above..."):
    
    # 1. Display user message and uploaded image
    with st.chat_message("user"):
        st.markdown(user_input)
        if uploaded_file:
            st.image(uploaded_file, width=250)

    # 2. Prepare the message content for the AI
    message_content = [{"type": "text", "text": user_input}]
    
    if uploaded_file is not None:
        import hashlib
        current_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
        
        # SMART CACHE: Only attach the image to the AI payload if it's brand new
        if current_hash not in st.session_state.analyzed_files:
            base64_image = encode_image(uploaded_file)
            message_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })
            # Add to our memory bank so it triggers the duplicate warning next time
            st.session_state.analyzed_files.append(current_hash)

    # Save user's message to history
    st.session_state.messages.append({"role": "user", "content": message_content})

    # 3. Generate Assistant Response
    with st.chat_message("assistant"):
        try: # --- OUTER TRY BLOCK BEGINS ---
            
            # --- SMART TRANSLATION PAYLOAD ---
            # Create a temporary copy of the chat history
            api_messages = st.session_state.messages.copy()
            
            # Inject a strict system command telling the AI to use the user's selected language
            api_messages.append({
                "role": "system", 
                "content": f"CRITICAL TRANSLATION RULE: You MUST generate your ENTIRE response, including the report analysis, headings, and Ayurvedic recommendations, strictly in {selected_language}. Ensure medical terms are translated beautifully so the common man can understand."
            })
            
            # Call the AI Engine using the modified payload
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=api_messages,
                temperature=0.6,
            )
            ai_response = response.choices[0].message.content
            
            # --- THE CONDITIONAL RENDERING BLOCK ---
            if uploaded_file is not None:
                # 1. Display the premium letterhead in the UI
                # We use the 'current_logo' variable defined in your clinic setup!
                display_letterhead_report(ai_response, current_logo)
                
               # 2. Build the printable PDF version
                # First, translate the AI's Markdown into beautifully structured HTML
                structured_html_content = markdown.markdown(ai_response, extensions=['extra', 'sane_lists', 'nl2br'])
                
                # Inject it into a PDF-optimized template (using tables for perfect alignment)
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
                
                # 3. Generate the PDF inside a hidden memory buffer
                pdf_buffer = BytesIO()
                pisa_status = pisa.CreatePDF(report_html, dest=pdf_buffer)
                
                # 4. Display the Download Button
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
            
            # Save assistant's reply to history
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            
        except Exception as e: # --- THIS IS THE RESTORED EXCEPT BLOCK! ---
            st.error("Error communicating with the AI Engine. Please check your API key.")