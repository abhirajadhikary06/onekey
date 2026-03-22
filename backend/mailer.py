from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from backend.config import (
    MAIL_USERNAME,
    MAIL_PASSWORD,
    MAIL_FROM,
    MAIL_PORT,
    MAIL_SERVER,
    MAIL_STARTTLS,
    MAIL_SSL_TLS,
)

# Only initialize FastMail if we have proper credentials
conf = None
if MAIL_USERNAME and MAIL_PASSWORD and MAIL_SERVER:
    conf = ConnectionConfig(
        MAIL_USERNAME=MAIL_USERNAME,
        MAIL_PASSWORD=MAIL_PASSWORD,
        MAIL_FROM=MAIL_FROM,
        MAIL_PORT=MAIL_PORT,
        MAIL_SERVER=MAIL_SERVER,
        MAIL_STARTTLS=MAIL_STARTTLS,
        MAIL_SSL_TLS=MAIL_SSL_TLS,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True
    )

fast_mail = FastMail(conf) if conf else None

async def send_api_alert_email(email: str, provider: str, status_code: int, response_text: str, model: str = None, endpoint: str = None):
    """
    Utility function to send a detailed email asynchronously on API proxy failures.
    """
    if not fast_mail:
        print("SMTP not configured. Skipping email alert.")
        return False

    # Only send for actual errors (400-500+)
    if status_code < 400:
        return True

    # Ensure response_text is a string
    if not isinstance(response_text, str):
        try:
            response_text = str(response_text)
        except:
            response_text = "[Unparseable Response Content]"

    # Try to clean/format the response JSON for better readability
    try:
        import json
        parsed_json = json.loads(response_text)
        cleaned_response = json.dumps(parsed_json, indent=2)
    except:
        cleaned_response = response_text

    status_type = "Success" if status_code < 400 else "Failure"
    color = "#10b981" if status_code < 400 else "#ef4444"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px;">
        <h2 style="color: {color}; border-bottom: 2px solid {color}; padding-bottom: 10px;">Onekey API Alert: {status_type}</h2>
        <p>A request to <strong>{provider}</strong> was processed with status <strong>{status_code}</strong>.</p>
        
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tr style="background-color: #f8fafc;">
                <td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>Provider</strong></td>
                <td style="padding: 10px; border: 1px solid #e2e8f0;">{provider}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>Model</strong></td>
                <td style="padding: 10px; border: 1px solid #e2e8f0;">{model or 'N/A'}</td>
            </tr>
            <tr style="background-color: #f8fafc;">
                <td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>Status Code</strong></td>
                <td style="padding: 10px; border: 1px solid #e2e8f0;">{status_code}</td>
            </tr>
        </table>
        
        <h3 style="margin-top: 20px;">Details</h3>
        <pre style="background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 10px; border-radius: 5px; overflow-x: auto; font-size: 11px;">
{cleaned_response[:2000]}
        </pre>
        
        <p style="font-size: 12px; color: #64748b; margin-top: 20px;">
            This is an automated alert from your Onekey server.
        </p>
    </div>
    """

    message = MessageSchema(
        subject=f"Onekey Alert: {provider} {status_type} ({status_code})",
        recipients=[email],
        body=html_content,
        subtype=MessageType.html
    )
    
    try:
        await fast_mail.send_message(message)
        print(f"Sent Failure alert to {email} for provider {provider}")
        return True
    except Exception as e:
        print(f"Failed to send email to {email}: {e}")
        return False
