def generate_incident_creation_email_html(incident_data: dict, reported_by_user: str) -> str:
    """
    Genera el HTML para el correo de notificación de creación de incidente.
    """
    title = "Nuevo Incidente Reportado"
    greeting = f"Hola Administrador,"
    
    intro_message = f"Se ha reportado un nuevo incidente por el usuario: <strong>{reported_by_user}</strong>."
    
    details_html = "<ul>"
    details_html += f"<li><strong>Tipo de Incidente:</strong> {incident_data.get('incident_type', 'N/A')}</li>"
    details_html += f"<li><strong>Fecha del Incidente:</strong> {incident_data.get('date', 'N/A')}</li>"
    details_html += f"<li><strong>Descripción:</strong> {incident_data.get('description', 'N/A')}</li>"
    details_html += f"<li><strong>Estado Inicial:</strong> {incident_data.get('status_display', incident_data.get('status', 'N/A'))}</li>"
    if incident_data.get('image_url'):
        details_html += f"<li><strong>Imagen Adjunta:</strong> <a href='{incident_data.get('image_url')}'>Ver Imagen</a></li>"
    details_html += "</ul>"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; padding: 20px; margin: 0 auto; max-width: 600px;">
        <div style="background-color: #ffffff; padding: 25px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <h2 style="color: #e74c3c; text-align: center; border-bottom: 2px solid #c0392b; padding-bottom: 10px;">{title}</h2>
            <p style="font-size: 16px;">{greeting}</p>
            <p style="font-size: 16px;">{intro_message}</p>
            <h3 style="color: #34495e; margin-top: 20px;">Detalles del Incidente:</h3>
            {details_html}
            <p style="font-size: 16px; margin-top: 20px;">Por favor, revisa y gestiona este incidente a la brevedad.</p>
            <hr style="margin: 30px 0; border: 0; border-top: 1px solid #eee;">
            <p style="font-size: 12px; color: #7f8c8d; text-align: center;">
                Este es un mensaje automático del sistema de gestión de incidentes.
            </p>
        </div>
    </div>
    """
    return html_body