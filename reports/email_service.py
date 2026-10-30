import logging
import resend
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def send_login_otp_resend(recipient_email: str, otp: str, is_admin: bool = False) -> dict:
    """
    Sends a 6-digit login OTP email.
    Tries Resend API first. If Resend rejects due to unverified domain or trial restrictions,
    automatically falls back to SMTP so the OTP is guaranteed to land in the user's inbox.
    """
    portal_name = "Admin" if is_admin else "Citizen"
    subject = f"Civic Mapping {portal_name} Login OTP"

    if settings.DEBUG:
        print(f"\n==================================================")
        print(f"[OTP LOG] Portal: {portal_name}")
        print(f"[OTP LOG] Recipient: {recipient_email}")
        print(f"[OTP LOG] Code: {otp}")
        print(f"==================================================\n")

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6f8; margin: 0; padding: 24px; color: #1e293b; }}
            .card {{ max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 32px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
            .brand {{ font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 8px; }}
            .subtitle {{ font-size: 14px; color: #64748b; margin-bottom: 24px; }}
            .otp-box {{ background: #eff6ff; border: 2px dashed #3b82f6; border-radius: 8px; padding: 18px; text-align: center; margin: 24px 0; }}
            .otp-code {{ font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #1d4ed8; font-family: monospace; }}
            .footer {{ font-size: 12px; color: #94a3b8; margin-top: 24px; text-align: center; border-top: 1px solid #f1f5f9; padding-top: 16px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="brand">&#127961;&#65039; Neighbourhood Civic Mapping</div>
            <div class="subtitle">{portal_name} Portal Authentication</div>
            <p>Hello,</p>
            <p>Your one-time login verification code is:</p>
            <div class="otp-box">
                <div class="otp-code">{otp}</div>
            </div>
            <p>This code is valid for <strong>5 minutes</strong>. Do not share this code with anyone.</p>
            <div class="footer">
                If you did not request this OTP, you can safely ignore this email.<br>
                &copy; Neighbourhood Civic Infrastructure Mapping
            </div>
        </div>
    </body>
    </html>
    """

    plain_text = (
        f"Your Civic Mapping {portal_name} login OTP is: {otp}\n\n"
        "This OTP is valid for 5 minutes. Do not share this OTP with anyone.\n"
    )

    # 1. Try Resend API first
    try:
        resend.api_key = settings.RESEND_API_KEY
        params = {
            "from": getattr(settings, "RESEND_FROM_EMAIL", "Civic Mapping <onboarding@resend.dev>"),
            "to": [recipient_email],
            "subject": subject,
            "html": html_content,
            "text": plain_text,
        }
        response = resend.Emails.send(params)
        logger.info(f"Resend email dispatched successfully: {response}")
        print(f"[OTP SUCCESS] Dispatched via Resend API to {recipient_email}")
        return {"success": True, "error": None, "response": response, "channel": "resend"}

    except Exception as exc:
        err_str = str(exc)
        logger.warning(f"Resend dispatch failed ({err_str}). Falling back to SMTP...")
        print(f"[RESEND NOTICE] {err_str}")
        print(f"[OTP FALLBACK] Sending via SMTP to {recipient_email}...")

        # 2. Seamless fallback to SMTP so ANY email receives the OTP in their inbox
        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_text,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER),
                to=[recipient_email],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)
            logger.info(f"SMTP email fallback sent successfully to {recipient_email}")
            print(f"[OTP SUCCESS] Dispatched via SMTP fallback to {recipient_email}")
            return {"success": True, "error": None, "channel": "smtp"}
        except Exception as smtp_err:
            logger.error(f"Both Resend and SMTP failed: {smtp_err}", exc_info=True)
            return {"success": False, "error": f"Email delivery failed: {smtp_err}", "channel": None}
