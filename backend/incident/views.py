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

# imports para drf-yasg
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import permissions
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_yasg import utils

from django.db.models import Q

# ReportLab
import io
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import requests

import cloudinary
import cloudinary.uploader

bearer_security_definition = [{'Bearer': []}]


def get_base_url_with_port():
    base_url = os.getenv("BASE_URL", "http://localhost")
    port = os.getenv("BASE_URL_BACKEND_PORT")
    if port:
        return f"{base_url}:{port}"
    return base_url


def validate_incident_data(data):
    errors = {}
    required_fields = ['incident_type', 'description', 'date']
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


incident_object_schema_detailed = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID único del incidente."),
        'incident_type': openapi.Schema(type=openapi.TYPE_STRING, description="Tipo de incidente."),
        'description': openapi.Schema(type=openapi.TYPE_STRING, description="Descripción detallada del incidente."),
        'date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description="Fecha del incidente (YYYY-MM-DD)."),
        'image_url': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI, description="URL completa de la imagen adjunta, si existe.", nullable=True),
        'comment': openapi.Schema(type=openapi.TYPE_STRING, description="Comentario de resolución o seguimiento.", nullable=True),
        'status': openapi.Schema(type=openapi.TYPE_STRING, description="Código del estado actual del incidente (e.g., 'activo', 'resuelto')."),
        'status_display': openapi.Schema(type=openapi.TYPE_STRING, description="Descripción legible del estado actual del incidente."),
        'active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Indica si el incidente está activo (no eliminado lógicamente)."),
        'created_by_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del usuario que creó el incidente (visible para superusuarios).", nullable=True),
        'created_by_name': openapi.Schema(type=openapi.TYPE_STRING, description="Nombre del usuario que creó el incidente."),
        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description="Fecha y hora de creación (YYYY-MM-DD HH:MM:SS) (visible para superusuarios)."),
        'modified_by_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del usuario que modificó por última vez el incidente (visible para superusuarios).", nullable=True),
        'modified_by_name': openapi.Schema(type=openapi.TYPE_STRING, description="Nombre del usuario que modificó por última vez el incidente (visible para superusuarios).", nullable=True),
        'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description="Fecha y hora de la última modificación (YYYY-MM-DD HH:MM:SS) (visible para superusuarios).")
    }
)


incident_object_schema_user = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID único del incidente."),
        'incident_type': openapi.Schema(type=openapi.TYPE_STRING, description="Tipo de incidente."),
        'description': openapi.Schema(type=openapi.TYPE_STRING, description="Descripción detallada del incidente."),
        'date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description="Fecha del incidente (YYYY-MM-DD)."),
        'image_url': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI, description="URL completa de la imagen adjunta, si existe.", nullable=True),
        'comment': openapi.Schema(type=openapi.TYPE_STRING, description="Comentario de resolución o seguimiento.", nullable=True),
        'status': openapi.Schema(type=openapi.TYPE_STRING, description="Código del estado actual del incidente."),
        'status_display': openapi.Schema(type=openapi.TYPE_STRING, description="Descripción legible del estado actual del incidente."),
        'created_by_name': openapi.Schema(type=openapi.TYPE_STRING, description="Nombre del usuario que creó el incidente."),
    }
)


error_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
        'message': openapi.Schema(type=openapi.TYPE_STRING)
    }
)


error_response_with_dict_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
        'message': openapi.Schema(type=openapi.TYPE_STRING),
        'errors': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="Diccionario de errores de validación por campo.",
            additional_properties=openapi.Schema(type=openapi.TYPE_STRING) # Permite cualquier clave con valor string
        )
    }
)


class IncidentRC(APIView):


    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]


    @swagger_auto_schema(
        operation_id="api_incident_list",
        operation_description="Obtiene una lista de incidentes. Los superusuarios ven todos los incidentes con detalles completos. Los usuarios regulares solo ven los incidentes creados por ellos con detalles limitados. Requiere autenticación.",
        security=bearer_security_definition, # @authenticate_user() implica que se requiere token
        responses={
            HTTPStatus.OK: openapi.Response(
                description="Lista de incidentes recuperada exitosamente.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="ok"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=incident_object_schema_detailed,
                            description="Array de incidentes. La estructura de cada incidente puede variar ligeramente si el solicitante es superusuario o no."
                        )
                    }
                )
            ),
            HTTPStatus.UNAUTHORIZED: openapi.Response(description="Token no provisto o inválido.", schema=error_response_schema),
            HTTPStatus.INTERNAL_SERVER_ERROR: openapi.Response(description="Error interno del servidor.", schema=error_response_schema)
        },
    )
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
            image_url = incident.image_url
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


    @swagger_auto_schema(
        operation_id="api_incident_create",
        operation_description="Crea un nuevo incidente. Requiere autenticación.",
        security=bearer_security_definition,
        consumes=['multipart/form-data'],
        manual_parameters=[
            openapi.Parameter(
                name='incident_type',
                in_=openapi.IN_FORM,
                description="Tipo de incidente (máx 100 caracteres).",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                name='description',
                in_=openapi.IN_FORM,
                description="Descripción detallada del incidente.",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                name='date',
                in_=openapi.IN_FORM,
                description="Fecha del incidente (YYYY-MM-DD).",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                required=True
            ),
            openapi.Parameter(
                name='image',
                in_=openapi.IN_FORM,
                description="Imagen adjunta (opcional, JPG, JPEG, PNG, máx 5MB).",
                type=openapi.TYPE_FILE,
                required=False
            )
        ],
        responses={
            HTTPStatus.CREATED: openapi.Response(
                description="Incidente creado exitosamente.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="ok"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Incidente creado exitosamente."),
                        'incident_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del incidente recién creado."),
                        'image_filename_saved': openapi.Schema(type=openapi.TYPE_STRING, description="Nombre del archivo de imagen guardado, si se subió alguno.", nullable=True)
                    }
                )
            ),
            HTTPStatus.BAD_REQUEST: openapi.Response(description="Datos inválidos.", schema=error_response_with_dict_schema),
            HTTPStatus.UNAUTHORIZED: openapi.Response(description="Token no provisto o inválido.", schema=error_response_schema),
            HTTPStatus.INTERNAL_SERVER_ERROR: openapi.Response(description="Error interno del servidor.", schema=error_response_schema)
        },
    )
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

        image_upload_result = None
        if image_file:
            allowed_extensions = ['.jpg', '.jpeg', '.png']
            ext = os.path.splitext(image_file.name)[1].lower()
            if ext not in allowed_extensions:
                return JsonResponse({"status": "error", "message": f"Tipo de archivo no permitido. Permitidos: {', '.join(allowed_extensions)}"}, status=HTTPStatus.BAD_REQUEST)
            if image_file.size > 5 * 1024 * 1024: # 5MB
                return JsonResponse({"status": "error", "message": "La imagen excede el tamaño máximo (5MB)."}, status=HTTPStatus.BAD_REQUEST)

            try:
                image_upload_result = cloudinary.uploader.upload(
                    image_file,
                    folder="incident_images"
                )
            except Exception as e:
                return JsonResponse({"status": "error", "message": f"Error al subir la imagen: {str(e)}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        
        try:
            incident = Incident.objects.create(
                incident_type=form_data.get('incident_type'),
                description=form_data.get('description'),
                date=form_data.get('date'),
                status=form_data.get('status', Incident.STATUS_ACTIVE),
                comment=form_data.get('comment', None),
                image_url=image_upload_result.get('secure_url') if image_upload_result else None,
                image_public_id=image_upload_result.get('public_id') if image_upload_result else None,
                active=form_data.get('active', True),
                created_by=user_id_making_request,
                modified_by=user_id_making_request
            )

            incident_email_data = {
                'incident_type': incident.incident_type,
                'description': incident.description,
                'date': incident.date,
                'status_display': incident.get_status_display(),
                'image_url': incident.image_url
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
                "image_url": incident.image_url
            }, status=HTTPStatus.CREATED)

        except Exception as e:
            if image_upload_result and image_upload_result.get('public_id'):
                cloudinary.uploader.destroy(image_upload_result.get('public_id'))
            return JsonResponse({"status": "error", "message": f"No se pudo crear el incidente: {str(e)}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


class IncidentRUD(APIView):


    permission_classes = [permissions.AllowAny]


    @swagger_auto_schema(
        operation_id="api_incident_retrieve",
        operation_description="Recupera un incidente específico por su ID. Los superusuarios ven todos los detalles. Los usuarios regulares solo pueden ver sus propios incidentes y con detalles limitados. Requiere autenticación.",
        manual_parameters=[
            openapi.Parameter('id', openapi.IN_PATH, description="ID del incidente a recuperar.", required=True, type=openapi.TYPE_INTEGER),
        ],
        security=bearer_security_definition,
        responses={
            HTTPStatus.OK: openapi.Response(
                description="Incidente recuperado exitosamente.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="ok"),
                        'data': incident_object_schema_detailed
                    }
                )
            ),
            HTTPStatus.BAD_REQUEST: openapi.Response(description="ID de incidente inválido.", schema=error_response_schema),
            HTTPStatus.UNAUTHORIZED: openapi.Response(description="Token no provisto o inválido.", schema=error_response_schema),
            HTTPStatus.FORBIDDEN: openapi.Response(description="No tienes permiso para ver este incidente.", schema=error_response_schema),
            HTTPStatus.NOT_FOUND: openapi.Response(description="Incidente no encontrado.", schema=error_response_schema),
            HTTPStatus.INTERNAL_SERVER_ERROR: openapi.Response(description="Error interno del servidor.", schema=error_response_schema)
        },
    )
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

        image_url = incident.image_url
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
    

    @swagger_auto_schema(
        operation_id="api_incident_resolve",
        operation_description="Actualiza un incidente, permitiendo principalmente añadir un comentario y cambiar el estado a 'resuelto'. Requiere permiso 'incident.change_incident'.",
        manual_parameters=[
            openapi.Parameter('id', openapi.IN_PATH, description="ID del incidente a actualizar.", required=True, type=openapi.TYPE_INTEGER),
        ],
        security=bearer_security_definition,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="Campos para actualizar. Solo 'comment' y 'status' (a 'resuelto') son permitidos.",
            properties={
                'comment': openapi.Schema(type=openapi.TYPE_STRING, description="Comentario de resolución. Requerido si se cambia el estado a 'resuelto'.", nullable=True),
                'status': openapi.Schema(type=openapi.TYPE_STRING, description="Nuevo estado del incidente. Solo se permite 'resuelto' a través de este endpoint.", example=Incident.STATUS_RESOLVED, enum=[Incident.STATUS_RESOLVED]),
            },
            # No hay 'required' a nivel de objeto porque ambos son opcionales
        ),
        responses={
            HTTPStatus.OK: openapi.Response(
                description="Incidente actualizado exitosamente o no se realizaron cambios.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="ok"), # o "info"
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': incident_object_schema_detailed
                    }
                )
            ),
            HTTPStatus.BAD_REQUEST: openapi.Response(description="Datos inválidos o no permitidos para la actualización.", schema=error_response_schema),
            HTTPStatus.UNAUTHORIZED: openapi.Response(description="Token no provisto o inválido.", schema=error_response_schema),
            HTTPStatus.FORBIDDEN: openapi.Response(description="Permiso 'incident.change_incident' requerido.", schema=error_response_schema),
            HTTPStatus.NOT_FOUND: openapi.Response(description="Incidente no encontrado.", schema=error_response_schema),
            HTTPStatus.INTERNAL_SERVER_ERROR: openapi.Response(description="Error interno del servidor.", schema=error_response_schema)
        },
    )
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
                    image_url = incident.image_url
                    
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
                "image_url": incident.image_url,
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


    @swagger_auto_schema(
        operation_id="api_incident_delete",
        operation_description="Elimina permanentemente un incidente por su ID. Requiere permiso 'incident.delete_incident'.",
        manual_parameters=[
            openapi.Parameter('id', openapi.IN_PATH, description="ID del incidente a eliminar.", required=True, type=openapi.TYPE_INTEGER),
        ],
        security=bearer_security_definition,
        responses={
            HTTPStatus.OK: openapi.Response(
                description="Incidente eliminado exitosamente.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="ok"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Incidente '...' eliminado exitosamente."),
                    }
                )
            ),
            HTTPStatus.BAD_REQUEST: openapi.Response(description="ID de incidente inválido.", schema=error_response_schema),
            HTTPStatus.UNAUTHORIZED: openapi.Response(description="Token no provisto o inválido.", schema=error_response_schema),
            HTTPStatus.FORBIDDEN: openapi.Response(description="No tienes permiso para eliminar este incidente o permiso 'incident.delete_incident' requerido.", schema=error_response_schema),
            HTTPStatus.NOT_FOUND: openapi.Response(description="Incidente no encontrado.", schema=error_response_schema),
            HTTPStatus.INTERNAL_SERVER_ERROR: openapi.Response(description="Error interno del servidor.", schema=error_response_schema)
        },
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
            incident_public_id = incident.image_public_id
            incident_name_for_message = incident.incident_type

            incident.delete()

            if incident_public_id:
                try:
                    cloudinary.uploader.destroy(incident_public_id)
                except Exception as e:
                    print(f"Error al eliminar imagen de Cloudinary ({incident_public_id}): {e}")
            return JsonResponse(
                {"status": "ok", "message": f"Incidente '{incident_name_for_message}' eliminado exitosamente."},
                status=HTTPStatus.OK
            )
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Ocurrió un error al eliminar el incidente: {str(e)}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        

class IncidentSD(APIView): #Soft delete


    permission_classes = [permissions.AllowAny]


    @swagger_auto_schema(
        operation_id="api_incident_set_active_status",
        operation_description="Activa o desactiva (eliminación lógica) un incidente. Requiere permiso 'incident.change_incident'.",
        manual_parameters=[
            openapi.Parameter('id', openapi.IN_PATH, description="ID del incidente a activar/desactivar.", required=True, type=openapi.TYPE_INTEGER),
        ],
        security=bearer_security_definition,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['active'],
            properties={
                'active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Nuevo estado de activación (true para activar, false para desactivar).")
            }
        ),
        responses={
            HTTPStatus.OK: openapi.Response(
                description="Estado de activación del incidente actualizado exitosamente o no se realizaron cambios.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="ok"), # o "info"
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'active': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                            }
                        )
                    }
                )
            ),
            HTTPStatus.BAD_REQUEST: openapi.Response(description="Datos inválidos (e.g., falta el campo 'active' o no es booleano).", schema=error_response_schema),
            HTTPStatus.UNAUTHORIZED: openapi.Response(description="Token no provisto o inválido.", schema=error_response_schema),
            HTTPStatus.FORBIDDEN: openapi.Response(description="Permiso 'incident.change_incident' requerido.", schema=error_response_schema),
            HTTPStatus.NOT_FOUND: openapi.Response(description="Incidente no encontrado.", schema=error_response_schema),
            HTTPStatus.INTERNAL_SERVER_ERROR: openapi.Response(description="Error interno del servidor.", schema=error_response_schema)
        },
    )
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


    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]


    @swagger_auto_schema(
        operation_id="api_incident_edit_image",
        operation_description="Actualiza o añade la imagen de un incidente existente. Solo permitido dentro de las 24 horas de creación del incidente. Requiere permiso 'incident.add_incident'.",
        security=bearer_security_definition,
        consumes=['multipart/form-data'],
        manual_parameters=[
            openapi.Parameter(
                name='id',
                in_=openapi.IN_FORM,
                description="ID del incidente cuya imagen se va a actualizar.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                name='incident_image',
                in_=openapi.IN_FORM,
                description="Nuevo archivo de imagen (JPG, JPEG, PNG, máx 5MB).",
                type=openapi.TYPE_FILE,
                required=True
            )
        ],
        responses={
            HTTPStatus.OK: openapi.Response(
                description="Imagen del incidente actualizada exitosamente.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="ok"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Imagen del incidente actualizada exitosamente."),
                        'incident_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'new_image_filename': openapi.Schema(type=openapi.TYPE_STRING),
                        'new_image_url': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI)
                    }
                )
            ),
            HTTPStatus.BAD_REQUEST: openapi.Response(description="Datos inválidos (e.g., falta ID/imagen, ID no numérico, tipo/tamaño de archivo incorrecto).", schema=error_response_schema),
            HTTPStatus.UNAUTHORIZED: openapi.Response(description="Token no provisto o inválido.", schema=error_response_schema),
            HTTPStatus.FORBIDDEN: openapi.Response(description="No se puede modificar la imagen después de 24 horas o permiso 'incident.add_incident' requerido.", schema=error_response_schema),
            HTTPStatus.NOT_FOUND: openapi.Response(description="Incidente no encontrado.", schema=error_response_schema),
            HTTPStatus.INTERNAL_SERVER_ERROR: openapi.Response(description="Error interno del servidor.", schema=error_response_schema)
        },
    )
    @authenticate_user()
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

        old_public_id = incident.image_public_id

        try:
            upload_result = cloudinary.uploader.upload(
                new_image_file,
                folder="incident_images"
            )

            incident.image_url = upload_result.get('secure_url')
            incident.image_public_id = upload_result.get('public_id')
            incident.modified_by = request.user.id
            incident.save(update_fields=['image_url', 'image_public_id', 'modified_by', 'updated_at'])

            if old_public_id:
                try:
                    cloudinary.uploader.destroy(old_public_id)
                except Exception as e:
                    print(f"No se pudo eliminar la imagen anterior de Cloudinary ({old_public_id}): {e}")

            return JsonResponse({
                "status": "ok",
                "message": "Imagen del incidente actualizada exitosamente.",
                "incident_id": incident.id,
                "new_image_url": incident.image_url
            }, status=HTTPStatus.OK)

        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Error al actualizar la imagen del incidente: {str(e)}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


class ActiveReports(APIView):

    permission_classes = [permissions.AllowAny]

    def draw_header(self, canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica-Bold', 16)
        header_y_position = doc.pagesize[1] - 0.75 * inch
        canvas.drawCentredString(letter[0] / 2.0, header_y_position, "Reporte de Incidentes Activos")
        canvas.setFont('Helvetica', 9)
        canvas.drawString(inch, 0.75 * inch, f"Página {doc.page}")
        canvas.restoreState()

    @authenticate_user()
    def get(self, request):
        base_query = Incident.objects.filter(
            status=Incident.STATUS_ACTIVE, 
            active=True
        )

        if request.user.is_superuser:
            incidents_to_report = base_query.order_by('created_at')
        else:
            incidents_to_report = base_query.filter(created_by=request.user.id).order_by('created_at')

        if not incidents_to_report.exists():
            return JsonResponse({"status": "info", "message": "No hay incidentes activos para mostrar en el reporte."}, status=HTTPStatus.OK)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1.2 * inch, rightMargin=72, leftMargin=72, bottomMargin=72)
        styles = getSampleStyleSheet()

        story = []
        
        for incident in incidents_to_report:
            story.append(Paragraph(f"ID: {incident.id} - {incident.incident_type}", styles['h2']))
            story.append(Spacer(1, 0.1 * inch))

            created_by_name = get_user_first_name_by_id(incident.created_by) or "N/A"
            details_data = [
                ['Fecha:', str(incident.date)],
                ['Reportado Por:', created_by_name],
                ['Descripción:', Paragraph(incident.description, styles['BodyText'])]
            ]
            
            details_table = Table(details_data, colWidths=[1.2*inch, 5.3*inch])
            details_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(details_table)
            story.append(Spacer(1, 0.2 * inch))

            if incident.image_url:
                try:
                    response = requests.get(incident.image_url, stream=True)
                    response.raise_for_status()

                    img = Image(io.BytesIO(response.content), width=3*inch, height=2.25*inch, kind='proportional')
                    story.append(img)
                except Exception as e:
                    story.append(Paragraph(f"Error al cargar imagen: {e}", styles['Italic']))

            story.append(Spacer(1, 0.5 * inch))

        doc.build(story, onFirstPage=self.draw_header, onLaterPages=self.draw_header)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="reporte_incidentes_activos.pdf"'
        return response


class SpecificReport(APIView):
    permission_classes = [permissions.AllowAny]

    def draw_header(self, canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica-Bold', 16)
        header_y_position = doc.pagesize[1] - 0.75 * inch
        canvas.drawCentredString(letter[0] / 2.0, header_y_position, "Reporte de Incidente Específico")
        canvas.setFont('Helvetica', 9)
        canvas.drawString(inch, 0.75 * inch, f"Página {doc.page}")
        canvas.restoreState()

    @authenticate_user()
    def get(self, request, id):
        try:
            incident = Incident.objects.get(
                pk=id, 
                status=Incident.STATUS_ACTIVE, 
                active=True
            )
        except Incident.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Incidente activo con el ID proporcionado no encontrado."}, status=HTTPStatus.NOT_FOUND)

        if not request.user.is_superuser and incident.created_by != request.user.id:
            return JsonResponse({"status": "error", "message": "No tienes permiso para generar un reporte de este incidente."}, status=HTTPStatus.FORBIDDEN)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1.2 * inch, rightMargin=72, leftMargin=72, bottomMargin=72)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(f"Detalle del Incidente", styles['h1']))
        story.append(Spacer(1, 0.2 * inch))

        data = [
            ["ID Incidente:", Paragraph(str(incident.id), styles['BodyText'])],
            ["Tipo de Incidente:", Paragraph(incident.incident_type, styles['BodyText'])],
            ["Fecha del Incidente:", str(incident.date)],
            ["Estado:", incident.get_status_display()],
            ["Descripción:", Paragraph(incident.description, styles['BodyText'])],
            ["Reportado por:", get_user_first_name_by_id(incident.created_by)],
            ["Fecha de Creación:", incident.created_at.strftime('%Y-%m-%d %H:%M:%S')],
        ]

        table = Table(data, colWidths=[1.5*inch, 5.5*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.2 * inch))

        if incident.image_url:
            story.append(Paragraph("Imagen Adjunta:", styles['h2']))
            try:
                response = requests.get(incident.image_url, stream=True)
                response.raise_for_status()
                img = Image(io.BytesIO(response.content), width=4*inch, height=3*inch, kind='proportional')
                story.append(img)
            except Exception as e:
                story.append(Paragraph(f"No se pudo cargar la imagen: {e}", styles['BodyText']))

        doc.build(story, onFirstPage=self.draw_header, onLaterPages=self.draw_header)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reporte_incidente_{id}.pdf"'
        return response
    

class ArchivedReport(APIView):
    permission_classes = [permissions.AllowAny]

    def draw_header(self, canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica-Bold', 16)
        header_y_position = doc.pagesize[1] - 0.75 * inch
        canvas.drawCentredString(letter[0] / 2.0, header_y_position, "Reporte de Incidente Archivado")
        canvas.setFont('Helvetica', 9)
        canvas.drawString(inch, 0.75 * inch, f"Página {doc.page}")
        canvas.restoreState()

    @authenticate_user()
    def get(self, request, id):
        try:
            incident = Incident.objects.get(
                Q(status=Incident.STATUS_RESOLVED) | Q(active=False),
                pk=id
            )
        except Incident.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Incidente resuelto o inactivo con el ID proporcionado no encontrado."}, status=HTTPStatus.NOT_FOUND)

        if not request.user.is_superuser and incident.created_by != request.user.id:
            return JsonResponse({"status": "error", "message": "No tienes permiso para generar un reporte de este incidente."}, status=HTTPStatus.FORBIDDEN)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1.2 * inch, rightMargin=72, leftMargin=72, bottomMargin=72)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(f"Detalle del Incidente Archivado", styles['h1']))
        story.append(Spacer(1, 0.2 * inch))

        data = [
            ["ID Incidente:", Paragraph(str(incident.id), styles['BodyText'])],
            ["Tipo de Incidente:", Paragraph(incident.incident_type, styles['BodyText'])],
            ["Fecha del Incidente:", str(incident.date)],
            ["Descripción:", Paragraph(incident.description, styles['BodyText'])],
            ["Reportado por:", get_user_first_name_by_id(incident.created_by)],
            ["Fecha de Creación:", incident.created_at.strftime('%Y-%m-%d %H:%M:%S')],
        ]

        if incident.status == Incident.STATUS_RESOLVED:
            data.append(["Estado Final:", incident.get_status_display()])
            data.append(["Comentario de Solución:", Paragraph(incident.comment or "N/A", styles['BodyText'])])
            data.append(["Resuelto/Modificado por:", get_user_first_name_by_id(incident.modified_by)])
            data.append(["Fecha de Actualización:", incident.updated_at.strftime('%Y-%m-%d %H:%M:%S')])
        
        if not incident.active:
             data.append(["Visibilidad:", Paragraph("Inactivo (Oculto en listados activos)", styles['BodyText'])])


        table = Table(data, colWidths=[1.8*inch, 5.2*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.2 * inch))

        if incident.image_url:
            story.append(Paragraph("Imagen Adjunta:", styles['h2']))
            try:
                response = requests.get(incident.image_url, stream=True)
                response.raise_for_status()
                img = Image(io.BytesIO(response.content), width=4*inch, height=3*inch, kind='proportional')
                story.append(img)
            except Exception as e:
                story.append(Paragraph(f"No se pudo cargar la imagen: {e}", styles['BodyText']))

        doc.build(story, onFirstPage=self.draw_header, onLaterPages=self.draw_header)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reporte_archivado_{id}.pdf"'
        return response