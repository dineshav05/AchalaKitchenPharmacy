import streamlit as st

# Wrap all the text inside st.markdown() using triple quotes (""")
st.markdown("""
# Cancellation and Refund Policy

**Last Updated:** August 2026

Achala Enterprises strives to provide a seamless and valuable experience through the Achala Digital Vaidya platform. Due to the digital nature of our service, our refund policy is strictly defined below.

**1. Digital Goods and Services**
The ₹49 fee charged on the platform is for the real-time processing, AI analysis, and generation of a digital PDF report. Because this is an instantly delivered digital good, **all sales are final once the PDF report has been successfully generated and made available for download.**

**2. Eligible Refund Scenarios**
We will initiate a full refund (₹49) under the following circumstances:
* **System Failure:** Your payment was successfully deducted from your bank account, but the application crashed, failed to redirect, or encountered an API error that prevented the PDF report from generating.
* **Duplicate Payment:** You were accidentally charged multiple times for a single report upload due to a technical glitch on the payment gateway.

**3. Non-Refundable Scenarios**
Refunds will **not** be provided for:
* Dissatisfaction with the formatting, tone, or specific wording of the AI-generated report.
* Uploading an illegible, blurry, or non-medical image that the AI cannot read. (Please ensure your uploads are clear before proceeding to payment).
* Reports generated successfully but no longer needed by the user.

**4. How to Request a Refund**
If you believe you are eligible for a refund due to a system failure, please contact us within 48 hours of the transaction at [support@achalaenterprises.in] with the following details:
* Your Razorpay Payment ID / UTR Number.
* The date and time of the transaction.
* A brief description of the error encountered.


**5. Refund Processing Time**
Once a refund request is verified and approved, it will be processed immediately from our end. Please allow **5 to 7 business days** for the amount to reflect in your original method of payment, depending on your bank's processing times.
""")