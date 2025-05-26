import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

def send_email_notification(html_content: str, subject: str, recipient_email: str):
    smtp_server_host = os.getenv("SMTP_SERVER")
    smtp_port_str = os.getenv("SMTP_PORT")
    smtp_auth_user = os.getenv("SMTP_USER")
    smtp_auth_password = os.getenv("SMTP_PASSWORD")
    sender_email_address = os.getenv("SMTP_BY")

    if not all([smtp_server_host, smtp_port_str, smtp_auth_user, smtp_auth_password, sender_email_address]):
        raise Exception(
            "Error de configuración: Faltan una o más variables de entorno SMTP. "
            "Se requieren: SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_BY."
        )

    try:
        smtp_port = int(smtp_port_str)
    except ValueError:
        raise Exception(f"Error de configuración: El puerto SMTP '{smtp_port_str}' no es un número válido.")

    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = sender_email_address
    message['To'] = recipient_email
    message.attach(MIMEText(html_content, 'html', 'utf-8'))

    smtp_connection = None
    try:
        if smtp_port == 465:
            smtp_connection = smtplib.SMTP_SSL(smtp_server_host, smtp_port, timeout=10)
        else:
            smtp_connection = smtplib.SMTP(smtp_server_host, smtp_port, timeout=10)
            smtp_connection.ehlo()
            smtp_connection.starttls()
            smtp_connection.ehlo()

        smtp_connection.login(smtp_auth_user, smtp_auth_password)
        smtp_connection.sendmail(sender_email_address, recipient_email, message.as_string())

    except Exception as e:
        original_error_type = type(e).__name__
        original_error_msg = str(e)
        raise Exception(f"Error al intentar enviar el correo ({original_error_type}): {original_error_msg}")
    finally:
        if smtp_connection:
            try:
                smtp_connection.quit()
            except Exception:
                # Ignorar errores al intentar cerrar la conexión,
                # ya que el error principal ya fue lanzado.
                pass