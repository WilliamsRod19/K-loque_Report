def generate_user_update_notification_html(user_first_name: str, changes: dict, new_password_if_any: str = None) -> str:
    """
    Genera el HTML para el correo de notificación de actualización de cuenta.
    """
    title = "Actualización Importante de tu Cuenta"
    greeting = f"Hola <strong>{user_first_name or 'usuario'}</strong>,"
    
    intro_messages = {
        "email_changed": "Hemos actualizado tu dirección de correo electrónico.",
        "password_changed": "Tu contraseña ha sido modificada.",
        "made_admin": "Se te han otorgado privilegios de administrador.",
        "account_activated": "Tu cuenta ha sido activada.",
        "account_deactivated": "Tu cuenta ha sido desactivada.",
    }

    changes_list_html = "<ul>"
    notifications_sent = []

    if changes.get("email_changed_to"):
        changes_list_html += f"<li>Tu dirección de correo electrónico ha cambiado a: <strong>{changes['email_changed_to']}</strong>.</li>"
        notifications_sent.append(intro_messages["email_changed"])
    
    if changes.get("password_changed"):
        if new_password_if_any:
            changes_list_html += f"<li style='color:red;'><strong>Importante:</strong> Tu contraseña ha sido actualizada. Tu nueva contraseña es: <strong>{new_password_if_any}</strong>. Por favor, guárdala en un lugar seguro y considera cambiarla inmediatamente después de iniciar sesión si no solicitaste esta acción.</li>"
        else:
            changes_list_html += "<li>Tu contraseña ha sido actualizada.</li>"
        notifications_sent.append(intro_messages["password_changed"])

    if changes.get("made_admin"):
        changes_list_html += "<li>Ahora tienes permisos de administrador en la plataforma.</li>"
        notifications_sent.append(intro_messages["made_admin"])
        
    if changes.get("became_active"):
        changes_list_html += "<li>Tu cuenta ha sido activada. Ya puedes iniciar sesión.</li>"
        notifications_sent.append(intro_messages["account_activated"])
    elif changes.get("became_inactive"):
        changes_list_html += "<li>Tu cuenta ha sido desactivada.</li>"
        notifications_sent.append(intro_messages["account_deactivated"])

    changes_list_html += "</ul>"

    if not changes:
        changes_list_html = ""

    if len(notifications_sent) > 1:
        title = "Actualizaciones Importantes en tu Cuenta"
        intro_message = "Hemos realizado varias actualizaciones importantes en tu cuenta:"
    elif notifications_sent:
        intro_message = notifications_sent[0]
    else:
        intro_message = "Se ha procesado una actualización en tu cuenta."


    html_body = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; padding: 20px; margin: 0 auto; max-width: 600px;">
        <div style="background-color: #ffffff; padding: 25px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <h2 style="color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px;">{title}</h2>
            <p style="font-size: 16px;">{greeting}</p>
            <p style="font-size: 16px;">{intro_message}</p>
            {changes_list_html if changes else ""}
            <p style="font-size: 16px; margin-top: 20px;">Si no solicitaste estos cambios o tienes alguna pregunta, por favor, contacta a nuestro equipo de soporte inmediatamente.</p>
            <p style="font-size: 14px; color: #555; margin-top: 25px;">Atentamente,<br>El Equipo de K-loque Report</p>
            <hr style="margin: 30px 0; border: 0; border-top: 1px solid #eee;">
            <p style="font-size: 12px; color: #7f8c8d; text-align: center;">
                Este es un mensaje automático. Por favor, no respondas directamente a este correo.
            </p>
        </div>
    </div>
    """
    return html_body