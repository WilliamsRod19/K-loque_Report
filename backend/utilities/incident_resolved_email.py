def generate_incident_resolved_email_html(
    incident,
    resolver_user_name: str,
    creator_display_name: str,
    image_url_if_any: str = None
) -> str:
    incident_date_formatted = str(incident.date) 
    
    title = "¡Tu Incidente Ha Sido Resuelto!"

    greeting = f"Hola <strong>{creator_display_name or 'Usuario'}</strong>," 
    
    resolution_message = f"Nos complace informarte que tu incidente relacionado con '{incident.incident_type}' reportado el {incident_date_formatted} ha sido marcado como resuelto."
    
    details_html = "<ul>"
    details_html += f"<li><strong>Tipo de Incidente:</strong> {incident.incident_type}</li>"
    details_html += f"<li><strong>Fecha del Incidente:</strong> {incident_date_formatted}</li>"
    details_html += f"<li><strong>Descripción Original:</strong> {incident.description}</li>"
    details_html += f"<li><strong>Estado Actual:</strong> {incident.get_status_display()}</li>"
    if incident.comment:
        details_html += f"<li><strong>Comentario de Resolución por {resolver_user_name}:</strong><br/>{incident.comment}</li>"
    else:
        details_html += f"<li><strong>Comentario de Resolución por {resolver_user_name}:</strong> No se proporcionó un comentario detallado.</li>"

    if image_url_if_any:
        details_html += f"<li><strong>Imagen Original Adjunta:</strong> <a href='{image_url_if_any}'>Ver Imagen</a></li>"
    details_html += "</ul>"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; padding: 20px; margin: 0 auto; max-width: 600px;">
        <div style="background-color: #ffffff; padding: 25px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <h2 style="color: #2ecc71; text-align: center; border-bottom: 2px solid #27ae60; padding-bottom: 10px;">{title}</h2>
            <p style="font-size: 16px;">{greeting}</p>
            <p style="font-size: 16px;">{resolution_message}</p>
            <h3 style="color: #34495e; margin-top: 20px;">Detalles del Incidente y Resolución:</h3>
            {details_html}
            <p style="font-size: 16px; margin-top: 20px;">Si tienes alguna pregunta o consideras que el incidente no ha sido resuelto completamente, por favor contacta a soporte.</p>
            <p style="font-size: 14px; color: #555; margin-top: 25px;">Atentamente,<br>El Equipo de Soporte</p>
            <hr style="margin: 30px 0; border: 0; border-top: 1px solid #eee;">
            <p style="font-size: 12px; color: #7f8c8d; text-align: center;">
                Este es un mensaje automático. Por favor, no respondas directamente a este correo.
            </p>
        </div>
    </div>
    """
    return html_body