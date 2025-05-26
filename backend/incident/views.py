from rest_framework.views import APIView
from django.http import JsonResponse
from http import HTTPStatus
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.models import User

import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from datetime import datetime
from incident.models import Incident
from utilities.decorators import authenticate_user
from utilities.incident_create_email import generate_incident_creation_email_html
from utilities.send_email import send_email_notification
from django.utils import timezone
from datetime import timedelta
from utilities.incident_resolved_email import generate_incident_resolved_email_html

def get_base_url_with_port():
    base_url = os.getenv("BASE_URL", "http://localhost")
    port = os.getenv("BASE_URL_BACKEND_PORT")
    if port:
        return f"{base_url}:{port}"
    return base_url


def validate_incident_data(data):
    errors = {}
    required_fields = ['incident_type', 'description', 'date', 'status']
    for field in required_fields:
        if field not in data or not str(data[field]).strip():
            errors[field] = f"El campo '{field}' es requerido y no puede estar vacío."

    if 'incident_type' in data and len(str(data['incident_type'])) > 100:
        errors['incident_type'] = "El tipo de incidente no puede exceder los 100 caracteres."
    
    if 'description' in data and not str(data['description']).strip():
        errors['description'] = "La descripción es requerida."

    if 'date' in data:
        try:
            # Intenta parsear la fecha para validar su formato (YYYY-MM-DD)
            datetime.strptime(str(data['date']), '%Y-%m-%d').date()
        except ValueError:
            errors['date'] = "El formato de la fecha es inválido. Use YYYY-MM-DD."
    
    if 'status' in data and data['status'] not in [s[0] for s in Incident.STATUS_CHOICES]:
        valid_statuses = ", ".join([s[0] for s in Incident.STATUS_CHOICES])
        errors['status'] = f"El estado del incidente no es válido. Opciones válidas: {valid_statuses}."

    if errors:
        return errors
    return None


def get_incident_image_url(image_filename: str) -> str:
    if not image_filename:
        return ""
    
    base_server_url = get_base_url_with_port()
    image_path_prefix = "/uploads/incident_images/" 
    full_image_url = f"{base_server_url}{image_path_prefix}{image_filename}"
 
    return full_image_url


def get_user_first_name_by_id(user_id):
    """
    Obtiene el first_name de un usuario dado su ID.
    Devuelve None si el ID es None, el usuario no existe, o el ID no es válido.
    """
    if user_id is None:
        return None
    try:
        user = User.objects.get(id=user_id)
        return user.first_name if user.first_name else user.username
    except User.DoesNotExist:
        return "Usuario Desconocido"
    except ValueError:
        return "ID de Usuario Inválido"
    except Exception:
        return "Error al obtener nombre"


class IncidentRC(APIView):


    @authenticate_user()
    def get(self, request):
        is_superuser_requesting = request.user.is_superuser
        current_user_id = request.user.id

        if is_superuser_requesting:
            incidents = Incident.objects.all().order_by('-created_at', '-date')
        else:
            incidents = Incident.objects.filter(created_by=current_user_id).order_by('-created_at', '-date')

        data_list = []
        for incident in incidents:
            image_url = get_incident_image_url(incident.image) if incident.image else None
            created_by_name = get_user_first_name_by_id(incident.created_by)
            modified_by_name = get_user_first_name_by_id(incident.modified_by)

            incident_date_str = str(incident.date) 

            incident_data_for_current_loop = {}
            if is_superuser_requesting:
                incident_data_for_current_loop = {
                    "id": incident.id,
                    "incident_type": incident.incident_type,
                    "description": incident.description,
                    "date": incident_date_str,
                    "image_url": image_url,
                    "comment": incident.comment,
                    "status": incident.status,
                    "status_display": incident.get_status_display(),
                    "active": incident.active,
                    "created_by_id": incident.created_by, 
                    "created_by_name": created_by_name,
                    "created_at": incident.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "modified_by_id": incident.modified_by,
                    "modified_by_name": modified_by_name,
                    "updated_at": incident.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                }
            else:
                incident_data_for_current_loop = {
                    "id": incident.id,
                    "incident_type": incident.incident_type,
                    "description": incident.description,
                    "date": incident_date_str,
                    "image_url": image_url,
                    "comment": incident.comment,
                    "status": incident.status,
                    "status_display": incident.get_status_display(),
                    "created_by_name": created_by_name,
                }
            data_list.append(incident_data_for_current_loop)
        
        return JsonResponse({"status": "ok", "data": data_list}, status=HTTPStatus.OK)


    @authenticate_user()
    @transaction.atomic
    def post(self, request):

        user_id_making_request = request.user.id

        form_data = request.data.copy()
        image_file = request.FILES.get('image', None)

        validation_errors = validate_incident_data(form_data)
        if validation_errors:
            return JsonResponse({
                "status": "error",
                "message": "Datos inválidos. Por favor, corrija los errores.",
                "errors": validation_errors
            }, status=HTTPStatus.BAD_REQUEST)

        saved_image_filename = None
        if image_file:
            allowed_extensions = ['.jpg', '.jpeg', '.png']
            ext = os.path.splitext(image_file.name)[1].lower()
            if ext not in allowed_extensions:
                return JsonResponse({"status": "error", "message": f"Tipo de archivo no permitido para la imagen ('{ext}'). Permitidos: {', '.join(allowed_extensions)}"}, status=HTTPStatus.BAD_REQUEST)
            
            # Validar tamaño de archivo
            if image_file.size > 5 * 1024 * 1024: # 5MB
                return JsonResponse({"status": "error", "message": "La imagen excede el tamaño máximo permitido (5MB)."}, status=HTTPStatus.BAD_REQUEST)

            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'incident_images'))
            # Crear un nombre de archivo único para evitar colisiones
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            filename_prefix = f"incident_{user_id_making_request}_{timestamp}"
            saved_image_filename = fs.save(f"{filename_prefix}{ext}", image_file)
            
        try:
            incident = Incident.objects.create(
                incident_type=form_data.get('incident_type'),
                description=form_data.get('description'),
                date=form_data.get('date'),
                status=form_data.get('status', Incident.STATUS_ACTIVE),
                comment=form_data.get('comment', None),
                image=saved_image_filename,
                active=form_data.get('active', True),
                created_by=user_id_making_request,
                modified_by=user_id_making_request
            )

            incident_email_data = {
                'incident_type': incident.incident_type,
                'description': incident.description,
                'date': incident.date,
                'status_display': incident.get_status_display(),
                'image_url': get_incident_image_url(incident.image) if incident.image else None,
            }

            # Enviar correo de notificación
            admin_email_recipient = os.getenv("SMTP_BY")
            if admin_email_recipient:
                html_email = generate_incident_creation_email_html(incident_email_data, request.user.username)
                send_email_notification(
                    html_content=html_email,
                    subject=f"Nuevo Incidente Reportado: {incident.incident_type}",
                    recipient_email=admin_email_recipient
                )
            else:
                print("Correo no se enviókrnl")

            return JsonResponse({
                "status": "ok",
                "message": "Incidente creado exitosamente.",
                "incident_id": incident.id,
                "image_filename_saved": saved_image_filename
            }, status=HTTPStatus.CREATED)

        except DjangoValidationError as ve:
            return JsonResponse({"status": "error", "message": "Error de validación.", "errors": ve.message_dict}, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"No se pudo crear el incidente: {str(e)}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


class IncidentRUD(APIView):


    @authenticate_user() 
    def get(self, request, id):
        try:
            incident_id = int(id)
            incident = Incident.objects.get(pk=incident_id)
        except Incident.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Incidente no encontrado."}, status=HTTPStatus.NOT_FOUND)
        except ValueError:
            return JsonResponse({"status": "error", "message": "ID de incidente inválido. Debe ser un número entero."}, status=HTTPStatus.BAD_REQUEST)

        is_superuser_requesting = request.user.is_superuser
        current_user_id = request.user.id

        if not is_superuser_requesting and incident.created_by != current_user_id:
            return JsonResponse(
                {"status": "error", "message": "No tienes permiso para ver este incidente o no existe."}, status=HTTPStatus.FORBIDDEN 
            )

        image_url = get_incident_image_url(incident.image) if incident.image else None
        created_by_name = get_user_first_name_by_id(incident.created_by)
        modified_by_name = get_user_first_name_by_id(incident.modified_by)

        incident_date_str = str(incident.date)

        data = {}
        if is_superuser_requesting:
            data = {
                "id": incident.id,
                "incident_type": incident.incident_type,
                "description": incident.description,
                "date": incident_date_str,
                "image_url": image_url,
                "comment": incident.comment,
                "status": incident.status,
                "status_display": incident.get_status_display(),
                "active": incident.active,
                "created_by_id": incident.created_by,
                "created_by_name": created_by_name,
                "created_at": incident.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "modified_by_id": incident.modified_by, 
                "modified_by_name": modified_by_name, 
                "updated_at": incident.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
        else:
            data = {
                "id": incident.id,
                "incident_type": incident.incident_type,
                "description": incident.description,
                "date": incident_date_str,
                "image_url": image_url,
                "comment": incident.comment,
                "status": incident.status,
                "status_display": incident.get_status_display(),
                "active": incident.active,
                "created_by_name": created_by_name,
            }
        
        return JsonResponse({"status": "ok", "data": data}, status=HTTPStatus.OK)
    

    @authenticate_user(required_permission='incident.change_incident')
    @transaction.atomic
    def put(self, request, id):
        try:
            incident_id = int(id)
            incident = Incident.objects.get(pk=incident_id)
        except Incident.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Incidente no encontrado."}, status=HTTPStatus.NOT_FOUND)
        except ValueError:
            return JsonResponse({"status": "error", "message": "ID de incidente inválido. Debe ser un número entero."}, status=HTTPStatus.BAD_REQUEST)

        data = request.data
        if not isinstance(data, dict):
            return JsonResponse({"status": "error", "message": "Cuerpo de la solicitud inválido, se esperaba un objeto JSON."}, status=HTTPStatus.BAD_REQUEST)

        allowed_keys_for_update = {'comment', 'status'}
        provided_keys = set(data.keys())
        
        if not provided_keys:
             return JsonResponse({"status": "error", "message": "No se proporcionaron datos para actualizar."}, status=HTTPStatus.BAD_REQUEST)

        extra_keys = provided_keys - allowed_keys_for_update
        if extra_keys:
            return JsonResponse(
                {"status": "error", "message": f"Campos no permitidos para actualización: {', '.join(extra_keys)}. Solo se permite 'comment' y 'status'."},
                status=HTTPStatus.BAD_REQUEST
            )

        new_comment_from_request = data.get('comment')
        new_status_from_request = data.get('status')

        fields_updated_in_db = []
        email_notification_required = False

        if new_comment_from_request is not None:
            if not isinstance(new_comment_from_request, str):
                return JsonResponse({"status": "error", "message": "El comentario debe ser una cadena de texto."}, status=HTTPStatus.BAD_REQUEST)

            current_comment = incident.comment if incident.comment is not None else ""
            new_comment_stripped = new_comment_from_request.strip()

            if current_comment != new_comment_stripped:
                incident.comment = new_comment_stripped if new_comment_stripped else None
                fields_updated_in_db.append('comment')

        if new_status_from_request is not None:
            if new_status_from_request != Incident.STATUS_RESOLVED:
                return JsonResponse(
                    {"status": "error", "message": f"A través de este endpoint, solo se puede cambiar el estado a '{Incident.STATUS_RESOLVED}' (Incidente Resuelto)."},
                    status=HTTPStatus.BAD_REQUEST
                )
            
            comment_for_resolution_check = incident.comment if 'comment' not in fields_updated_in_db else new_comment_from_request
            
            if not comment_for_resolution_check or not str(comment_for_resolution_check).strip():
                return JsonResponse(
                    {"status": "error", "message": "Se requiere un comentario de resolución (no vacío) para marcar el incidente como resuelto."},
                    status=HTTPStatus.BAD_REQUEST
                )
            
            if incident.status != Incident.STATUS_RESOLVED:
                incident.status = Incident.STATUS_RESOLVED
                fields_updated_in_db.append('status')
                email_notification_required = True

        if not fields_updated_in_db:
            return JsonResponse(
                {"status": "info", "message": "No se realizaron cambios o los datos proporcionados son los mismos que los actuales."},
                status=HTTPStatus.OK
            )

        incident.modified_by = request.user.id
        fields_updated_in_db.append('modified_by')

        try:
            incident.save(update_fields=fields_updated_in_db)

            if email_notification_required:
                creator_id = incident.created_by
                creator_email_address = None
                creator_display_name = "Usuario Creador"

                if creator_id:
                    try:
                        creator_user = User.objects.get(id=creator_id)
                        creator_email_address = creator_user.email
                        creator_display_name = get_user_first_name_by_id(creator_id) or "Usuario Creador"
                    except User.DoesNotExist:
                        print(f"El creador del incidente ID {incident.id} (Usuario ID: {creator_id}) no fue encontrado. No se puede enviar email.")
                
                if creator_email_address:
                    resolver_name = request.user.get_full_name() or request.user.username
                    image_url = get_incident_image_url(incident.image) if incident.image else None
                    
                    html_email_body = generate_incident_resolved_email_html(
                        incident=incident,
                        resolver_user_name=resolver_name,
                        creator_display_name=creator_display_name,
                        image_url_if_any=image_url
                    )
                    send_email_notification(
                        html_content=html_email_body,
                        subject=f"RESOLUCIÓN: Incidente '{incident.incident_type}'",
                        recipient_email=creator_email_address
                    )
                elif creator_id:
                     print(f"El creador (ID: {creator_id}) del incidente ID {incident.id} no tiene una dirección de correo electrónico configurada. No se envió notificación de resolución.")


            response_data_incident = {
                "id": incident.id,
                "incident_type": incident.incident_type,
                "description": incident.description,
                "date": str(incident.date),
                "image_url": get_incident_image_url(incident.image),
                "comment": incident.comment,
                "status": incident.status,
                "status_display": incident.get_status_display(),
                "active": incident.active,
                "modified_by_id": incident.modified_by,
                "modified_by_name": get_user_first_name_by_id(incident.modified_by),
                "updated_at": incident.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            return JsonResponse({
                "status": "ok",
                "message": "Incidente actualizado exitosamente.",
                "data": response_data_incident
            }, status=HTTPStatus.OK)

        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": f"No se pudo completar la actualización del incidente: {str(e)}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )


    @authenticate_user(required_permission='incident.delete_incident')
    @transaction.atomic
    def delete(self, request, id):
        try:
            incident_id = int(id)
            incident = Incident.objects.get(pk=incident_id)
        except Incident.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Incidente no encontrado."}, status=HTTPStatus.NOT_FOUND)
        except ValueError:
            return JsonResponse({"status": "error", "message": "ID de incidente inválido."}, status=HTTPStatus.BAD_REQUEST)

        if incident.created_by != request.user.id and not request.user.is_superuser:
            return JsonResponse({"status": "error", "message": "No tienes permiso para eliminar este incidente."}, status=HTTPStatus.FORBIDDEN)

        try:
            incident_image_filename = incident.image
            incident_name_for_message = incident.incident_type

            incident.delete()

            if incident_image_filename:
                image_path = os.path.join(settings.MEDIA_ROOT, 'incident_images', incident_image_filename)
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except OSError as e_remove:
                        print(f"No se pudo eliminar el archivo de imagen '{image_path}': {e_remove}")
            
            return JsonResponse(
                {"status": "ok", "message": f"Incidente '{incident_name_for_message}' eliminado exitosamente."},
                status=HTTPStatus.OK
            )
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Ocurrió un error al eliminar el incidente: {str(e)}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        

class IncidentSD(APIView): #Soft delete

    @authenticate_user(required_permission='incident.change_incident')
    @transaction.atomic
    def patch(self, request, id): # El 'id' del incidente vendrá de la URL
        try:
            incident_id = int(id)
            incident = Incident.objects.get(pk=incident_id)
        except Incident.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Incidente no encontrado."},
                status=HTTPStatus.NOT_FOUND
            )
        except ValueError:
            return JsonResponse(
                {"status": "error", "message": "El ID de incidente proporcionado no es válido. Debe ser un número entero."},
                status=HTTPStatus.BAD_REQUEST
            )

        if 'active' not in request.data:
            return JsonResponse(
                {"status": "error", "message": "El campo 'active' (con valor true o false) es requerido en el cuerpo de la solicitud."},
                status=HTTPStatus.BAD_REQUEST
            )

        new_active_status_from_payload = request.data.get('active')

        if not isinstance(new_active_status_from_payload, bool):
            if isinstance(new_active_status_from_payload, str):
                if new_active_status_from_payload.lower() == 'true':
                    new_active_status = True
                elif new_active_status_from_payload.lower() == 'false':
                    new_active_status = False
                else:
                    return JsonResponse(
                        {"status": "error", "message": "El valor del campo 'active' es inválido. Debe ser true, false, 'true', o 'false'."},
                        status=HTTPStatus.BAD_REQUEST
                    )
            else:
                return JsonResponse(
                    {"status": "error", "message": "El valor del campo 'active' debe ser un booleano (true o false)."},
                    status=HTTPStatus.BAD_REQUEST
                )
        else:
            new_active_status = new_active_status_from_payload

        if incident.active == new_active_status:
            current_status_text = "activo" if incident.active else "inactivo"
            return JsonResponse(
                {"status": "info", "message": f"El incidente ID {incident.id} ya se encuentra {current_status_text}. No se realizaron cambios."},
                status=HTTPStatus.OK
            )

        try:
            incident.active = new_active_status
            incident.modified_by = request.user.id 
            incident.save(update_fields=['active', 'modified_by', 'updated_at'])
            
            action_message_verb = "activado" if new_active_status else "desactivado"
            return JsonResponse(
                {"status": "ok", 
                 "message": f"Incidente ID {incident.id} ('{incident.incident_type}') {action_message_verb} exitosamente.",
                 "data": {"id": incident.id, "active": incident.active}
                },
                status=HTTPStatus.OK
            )
        except Exception as e:

            return JsonResponse(
                {"status": "error", "message": f"Ocurrió un error al intentar actualizar el estado del incidente: {str(e)}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )


class EditImage(APIView):
    @authenticate_user(required_permission='incident.add_incident')
    @transaction.atomic
    def post(self, request): # Usamos POST para enviar el archivo y el ID
        incident_id_str = request.data.get("id")
        if not incident_id_str:
            return JsonResponse({"status": "error", "message": "El campo 'id' (ID del incidente) es requerido."}, status=HTTPStatus.BAD_REQUEST)
        
        try:
            incident_id = int(incident_id_str)
            incident = Incident.objects.get(pk=incident_id)
        except ValueError:
            return JsonResponse({"status": "error", "message": "El 'id' del incidente proporcionado no es un número válido."}, status=HTTPStatus.BAD_REQUEST)
        except Incident.DoesNotExist:
            return JsonResponse({"status": "error", "message": f"Incidente con ID '{incident_id_str}' no encontrado."}, status=HTTPStatus.NOT_FOUND)

        if (timezone.now() - incident.created_at) > timedelta(days=1):
            return JsonResponse(
                {"status": "error", "message": "No se puede modificar la imagen de un incidente después de 24 horas de su creación."},
                status=HTTPStatus.FORBIDDEN
            )

        new_image_file = request.FILES.get('incident_image')
        if not new_image_file:
            return JsonResponse({"status": "error", "message": "No se adjuntó ningún archivo de imagen (se esperaba en el campo 'incident_image')."}, status=HTTPStatus.BAD_REQUEST)

        allowed_extensions = ['.jpg', '.jpeg', '.png']
        ext = os.path.splitext(new_image_file.name)[1].lower()
        if ext not in allowed_extensions:
            return JsonResponse({"status": "error", "message": f"Tipo de archivo no permitido ('{ext}'). Permitidos: {', '.join(allowed_extensions)}."}, status=HTTPStatus.BAD_REQUEST)
        
        if new_image_file.size > 5 * 1024 * 1024:
            return JsonResponse({"status": "error", "message": "La imagen excede el tamaño máximo permitido (5MB)."}, status=HTTPStatus.BAD_REQUEST)

        fs_location = os.path.join(settings.MEDIA_ROOT, 'incident_images')
        os.makedirs(fs_location, exist_ok=True)
        fs = FileSystemStorage(location=fs_location)
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

        filename_prefix = f"incident_{incident.id}_{request.user.id}_{timestamp}" 
        new_image_filename = fs.save(f"{filename_prefix}{ext}", new_image_file)

        old_image_filename = incident.image

        try:
            incident.image = new_image_filename
            incident.modified_by = request.user.id
            incident.save(update_fields=['image', 'modified_by', 'updated_at'])

            if old_image_filename:
                old_image_path = os.path.join(settings.MEDIA_ROOT, 'incident_images', old_image_filename)
                if os.path.exists(old_image_path):
                    try:
                        os.remove(old_image_path)
                    except OSError as e_remove:
                        print(f"No se pudo eliminar el archivo de imagen anterior '{old_image_path}': {e_remove}")
            
            return JsonResponse({
                "status": "ok",
                "message": "Imagen del incidente actualizada exitosamente.",
                "incident_id": incident.id,
                "new_image_filename": new_image_filename,
                "new_image_url": get_incident_image_url(new_image_filename)
            }, status=HTTPStatus.OK)

        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Error al actualizar la imagen del incidente: {str(e)}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)