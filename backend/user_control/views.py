from rest_framework.views import APIView
from django.http import JsonResponse
from http import HTTPStatus
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as django_login
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re

# JWT
from jose import jwt
from django.conf import settings
from datetime import datetime, timedelta
import time
import os

from utilities.decorators import authenticate_user
from user_control.serializers import UserSerializer
from utilities.user_put_email import generate_user_update_notification_html
from utilities.send_email import send_email_notification

# imports para drf-yasg
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import permissions


bearer_security_definition = [{'Bearer': []}]


def get_base_url_with_port():
    base_url = os.getenv("BASE_URL", "http://localhost")
    port = os.getenv("BASE_URL_BACKEND_PORT")
    if port:
        return f"{base_url}:{port}"
    return base_url


def validate_required_fields(data, fields):
    for field in fields:
        value = data.get(field)
        if value is None:
            return JsonResponse({
                "status": "error",
                "message": f"El campo '{field}' es requerido."
            }, status=HTTPStatus.BAD_REQUEST)
        if isinstance(value, str) and not value.strip():
            return JsonResponse({
                "status": "error",
                "message": f"El campo '{field}' no puede estar vacío."
            }, status=HTTPStatus.BAD_REQUEST)
    return None


def validate_password_complexity(password):
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if not re.search(r"[A-Z]", password):
        return "La contraseña debe contener al menos una letra mayúscula."
    if not re.search(r"[a-z]", password):
        return "La contraseña debe contener al menos una letra minúscula."
    if not re.search(r"\d", password):
        return "La contraseña debe contener al menos un número."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
         return "La contraseña debe contener al menos un carácter especial."
    return None


def validate_name_format(field, field_name):
    if not re.match(r"^[a-zA-ZÀ-ÿ\s'-]+$", field):
        return f"El campo '{field_name}' contiene caracteres no válidos. Solo se permiten letras y espacios."
    return None

user_object_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID único del usuario.", example=1),
        'username': openapi.Schema(type=openapi.TYPE_STRING, description="Nombre de usuario.", example="kloquereport"),
        'first_name': openapi.Schema(type=openapi.TYPE_STRING, description="Nombre(s) del usuario. Puede estar vacío.", example=""),
        'last_name': openapi.Schema(type=openapi.TYPE_STRING, description="Apellido(s) del usuario. Puede estar vacío.", example=""),
        'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description="Correo electrónico.", example="me@kloquereport.com"),
        'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Indica si la cuenta del usuario está activa.", example=True),
        'is_admin': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Indica si el usuario tiene privilegios de administrador (superuser).", example=True),
        'last_login': openapi.Schema(type=openapi.TYPE_STRING, description="Fecha y hora del último inicio de sesión (Formato: DD-MM-YYYY HH:MM). Puede ser nulo.", example="26-05-2025 18:23", nullable=True),
        'date_joined': openapi.Schema(type=openapi.TYPE_STRING, description="Fecha y hora de registro (Formato: DD-MM-YYYY HH:MM).", example="24-05-2025 11:32")
    }
)

class UserRC(APIView):
    #Usuario Read and Create (registrar).

    permission_classes = [permissions.AllowAny]


    @swagger_auto_schema(
        operation_id="api_user_list_all",
        operation_description="Obtiene la lista de todos los usuarios. Requiere permiso 'user.view_user'.",
        security=bearer_security_definition,
        responses={
            HTTPStatus.OK: openapi.Response(
                description="Lista de usuarios recuperada exitosamente.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=user_object_schema
                        )
                    }
                )
            ),
            HTTPStatus.FORBIDDEN: openapi.Response(
                description="Acceso denegado. Permiso 'user.view_user' requerido.",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"), 'message': openapi.Schema(type=openapi.TYPE_STRING)})
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR: openapi.Response(
                description="Error interno del servidor.",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"), 'message': openapi.Schema(type=openapi.TYPE_STRING)})
            ),
        },
    )
    @authenticate_user(required_permission='user.view_user')
    def get(self, request):
        try:
            users = User.objects.all().order_by('id')
            
            serializer = UserSerializer(users, many=True)
            
            return JsonResponse({"data": serializer.data}, status=HTTPStatus.OK)
            
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": f"Ocurrió un error al procesar la solicitud. {e}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

    #Registrar
    @swagger_auto_schema(
        operation_id="api_user_create_new",
        operation_description="Registra (crea) un nuevo usuario. Requiere permiso 'user.add_user'.",
        security=bearer_security_definition,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['first_name', 'last_name', 'username', 'email', 'password'],
            properties={
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description="Nombre(s) del nuevo usuario."),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description="Apellido(s) del nuevo usuario."),
                'username': openapi.Schema(type=openapi.TYPE_STRING, description="Nombre de usuario único para el login."),
                'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description="Correo electrónico único del usuario."),
                'password': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description="Contraseña. Debe cumplir requisitos de complejidad.")
            }
        ),
        responses={
            HTTPStatus.CREATED: openapi.Response( # 201 Created
                description="Usuario creado exitosamente.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="ok"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Usuario creado exitosamente."),
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del usuario recién creado.")
                    }
                )
            ),
            HTTPStatus.BAD_REQUEST: openapi.Response(
                description="Solicitud incorrecta (e.g., campos faltantes, formato inválido, contraseña no cumple complejidad).",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"), 'message': openapi.Schema(type=openapi.TYPE_STRING)})
            ),
            HTTPStatus.CONFLICT: openapi.Response(
                description="Conflicto de datos (e.g., username o email ya existen).",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"), 'message': openapi.Schema(type=openapi.TYPE_STRING)})
            ),
            HTTPStatus.FORBIDDEN: openapi.Response(
                description="Acceso denegado. Permiso 'user.add_user' requerido.",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"), 'message': openapi.Schema(type=openapi.TYPE_STRING)})
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR: openapi.Response(
                description="Error interno del servidor.",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"), 'message': openapi.Schema(type=openapi.TYPE_STRING)})
            ),
        },
    )
    @authenticate_user(required_permission='user.add_user') #Este permiso es necesario ya que solo el admin podrá crear
    def post(self, request):
        required_fields = ["first_name", "last_name", "username", "email", "password"]
        error_response = validate_required_fields(request.data, required_fields)
        if error_response:
            return error_response

        first_name = request.data.get("first_name").strip()
        last_name = request.data.get("last_name").strip()
        username = request.data.get("username").strip()
        email = request.data.get("email").strip().lower()
        password = request.data.get("password")

        name_error = validate_name_format(first_name, "nombre")
        if name_error:
            return JsonResponse({"status": "error", "message": name_error}, status=HTTPStatus.BAD_REQUEST)

        name_error = validate_name_format(last_name, "apellido")
        if name_error:
            return JsonResponse({"status": "error", "message": name_error}, status=HTTPStatus.BAD_REQUEST)

        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({
                "status": "error",
                "message": "El formato del correo electrónico no es válido."
            }, status=HTTPStatus.BAD_REQUEST)

        password_error = validate_password_complexity(password)
        if password_error:
            return JsonResponse({"status": "error", "message": password_error}, status=HTTPStatus.BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return JsonResponse({
                "status": "error",
                "message": f"El nombre de usuario '{username}' ya está en uso."
            }, status=HTTPStatus.CONFLICT)

        if User.objects.filter(email=email).exists():
            return JsonResponse({
                "status": "error",
                "message": f"El correo electrónico '{email}' ya está registrado."
            }, status=HTTPStatus.CONFLICT)

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=False,
                    is_active=True
                )

            return JsonResponse({
                "status": "ok",
                "message": "Usuario creado exitosamente.",
                "user_id": user.id
            }, status=HTTPStatus.CREATED)

        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": f"No se pudo guardar el usuario. Por favor, inténtelo de nuevo más tarde. {e}"
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        

class UserRUD(APIView):


    permission_classes = [permissions.AllowAny]
    

    @swagger_auto_schema(
        operation_id="api_user_retrieve_by_id",
        operation_description="Recupera los datos de un usuario específico por su ID. Requiere permiso 'user.view_user'.",
        manual_parameters=[
            openapi.Parameter(
                name='id',
                in_=openapi.IN_PATH,
                description="ID numérico del usuario a recuperar.",
                required=True,
                type=openapi.TYPE_INTEGER
            ),
        ],
        security=bearer_security_definition, # Indica que este endpoint requiere el token Bearer
        responses={
            HTTPStatus.OK: openapi.Response( # 200 OK
                description="Datos del usuario recuperados exitosamente.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'data': user_object_schema
                    }
                )
            ),
            HTTPStatus.BAD_REQUEST: openapi.Response( # 400 Bad Request
                description="El ID de usuario proporcionado no es válido (e.g., no es un número entero).",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="El ID de usuario proporcionado no es válido. Debe ser un número entero."),
                    }
                )
            ),
            HTTPStatus.FORBIDDEN: openapi.Response( # 403 Forbidden (manejado por decorador @authenticate_user)
                description="Acceso denegado. No tienes el permiso requerido: 'user.view_user'.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Acceso denegado - No tienes el permiso requerido: 'user.view_user'."),
                    }
                )
            ),
            HTTPStatus.NOT_FOUND: openapi.Response( # 404 Not Found
                description="Usuario no encontrado con el ID proporcionado.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Usuario no encontrado."),
                    }
                )
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR: openapi.Response( # 500 Internal Server Error
                description="Error interno del servidor al intentar recuperar los datos del usuario.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Ocurrió un error inesperado al intentar recuperar los datos del usuario."),
                    }
                )
            ),
        }
    )
    @authenticate_user(required_permission='user.view_user')
    def get(self, request, id): # 'id' viene de la URL, ej: http://192.168.1.6:8000/api/v1/user-control/2
        try:
            user_id = int(id)

            user_instance = User.objects.get(pk=user_id)

            serializer = UserSerializer(user_instance)

            return JsonResponse({"data": serializer.data}, status=HTTPStatus.OK)

        except User.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Usuario no encontrado."},
                status=HTTPStatus.NOT_FOUND
            )
        except ValueError:
            return JsonResponse(
                {"status": "error", "message": "El ID de usuario proporcionado no es válido. Debe ser un número entero."},
                status=HTTPStatus.BAD_REQUEST
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": "Ocurrió un error inesperado al intentar recuperar los datos del usuario."},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        


    @swagger_auto_schema(
        operation_id="api_user_update_by_id",
        operation_description="Actualiza la información de un usuario específico por su ID. Todos los campos en el cuerpo son opcionales. Requiere permiso 'user.change_user'.",
        manual_parameters=[
            openapi.Parameter(
                name='id',
                in_=openapi.IN_PATH,
                description="ID numérico del usuario a actualizar.",
                required=True,
                type=openapi.TYPE_INTEGER
            ),
        ],
        security=bearer_security_definition,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="Campos a actualizar del usuario. Todos son opcionales.",
            properties={
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description="Nuevo nombre(s) del usuario."),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description="Nuevo apellido(s) del usuario."),
                'username': openapi.Schema(type=openapi.TYPE_STRING, description="Nuevo nombre de usuario."),
                'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description="Nuevo correo electrónico."),
                'password': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description="Nueva contraseña. Debe cumplir con los requisitos de complejidad."),
                'is_admin': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Establecer si el usuario es administrador (superuser)."),
                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Establecer si la cuenta del usuario está activa.")
            },
        ),
        responses={
            HTTPStatus.OK: openapi.Response(
                description="Usuario actualizado exitosamente. También puede devolver un estado 'info' si no se proporcionaron datos diferentes para actualizar (en cuyo caso 'data' podría ser nulo o no estar presente).",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Estado de la operación.",
                            example="ok"
                        ),
                        'message': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Mensaje descriptivo del resultado.",
                            example="Usuario actualizado exitosamente."
                        ),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description="Datos del usuario actualizado. Puede ser nulo si el 'status' es 'info'.",
                            properties={
                                'id': openapi.Schema(
                                    type=openapi.TYPE_INTEGER,
                                    description="ID único del usuario.",
                                    example=5
                                ),
                                'username': openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    description="Nombre de usuario.",
                                    example="juan"
                                ),
                                'first_name': openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    description="Nombre(s) del usuario.",
                                    example="Juan"
                                ),
                                'last_name': openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    description="Apellido(s) del usuario.",
                                    example="Pablo"
                                ),
                                'email': openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    format=openapi.FORMAT_EMAIL,
                                    description="Correo electrónico del usuario.",
                                    example="me@juan.com"
                                ),
                                'is_active': openapi.Schema(
                                    type=openapi.TYPE_BOOLEAN,
                                    description="Indica si la cuenta del usuario está activa.",
                                    example=False
                                ),
                                'is_admin': openapi.Schema(
                                    type=openapi.TYPE_BOOLEAN,
                                    description="Indica si el usuario tiene privilegios de administrador (corresponde a 'is_superuser' en el modelo Django User).",
                                    example=True
                                ),
                                'last_login': openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    description="Fecha y hora del último inicio de sesión (Formato: DD-MM-YYYY HH:MM). Es nulo si el usuario nunca ha iniciado sesión o si el valor es nulo en la base de datos.",
                                    example=None,
                                    nullable=True
                                ),
                                'date_joined': openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    description="Fecha y hora de registro del usuario (Formato: DD-MM-YYYY HH:MM).",
                                    example="25-05-2025 18:10"
                                )
                            },
                            nullable=True 
                        )
                    }
                )
            ),
            HTTPStatus.BAD_REQUEST: openapi.Response(
                description="Solicitud incorrecta (e.g., ID inválido, JSON inválido, campo vacío, formato de nombre/email/contraseña incorrecto).",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"), 'message': openapi.Schema(type=openapi.TYPE_STRING)})
            ),
            HTTPStatus.NOT_FOUND: openapi.Response(
                description="Usuario no encontrado con el ID proporcionado.",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"), 'message': openapi.Schema(type=openapi.TYPE_STRING, example="Usuario no encontrado.")})
            ),
            HTTPStatus.CONFLICT: openapi.Response(
                description="Conflicto de datos (e.g., username o email ya en uso por otro usuario).",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"), 'message': openapi.Schema(type=openapi.TYPE_STRING, example="El nombre de usuario '...' ya está en uso.")})
            ),
            HTTPStatus.FORBIDDEN: openapi.Response( # Manejado por decorador @authenticate_user
                description="Acceso denegado. No tienes el permiso requerido: 'user.change_user'.",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"), 'message': openapi.Schema(type=openapi.TYPE_STRING)})
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR: openapi.Response(
                description="Error interno del servidor al intentar actualizar el usuario.",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"), 'message': openapi.Schema(type=openapi.TYPE_STRING)})
            ),
        },
    )
    @authenticate_user(required_permission='user.change_user')
    def put(self, request, id): # 'id' viene de la URL, ej: http://192.168.1.6:8000/api/v1/user-control/2
        try:
            user_id = int(id)
            user_instance = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Usuario no encontrado."}, status=HTTPStatus.NOT_FOUND)
        except ValueError:
            return JsonResponse({"status": "error", "message": "El ID de usuario proporcionado no es válido."}, status=HTTPStatus.BAD_REQUEST)

        data = request.data
        if not isinstance(data, dict):
             return JsonResponse({"status": "error", "message": "Cuerpo de la solicitud inválido, se esperaba un objeto JSON."}, status=HTTPStatus.BAD_REQUEST)
        if not data: # Si el cuerpo está vacío
            return JsonResponse({"status": "error", "message": "No se proporcionaron datos para actualizar."}, status=HTTPStatus.BAD_REQUEST)

        original_is_superuser = user_instance.is_superuser
        original_is_active = user_instance.is_active
        
        fields_to_update_on_model = {}
        changes_for_email_notification = {}
        new_plain_password_for_email = None

        # 1. Validar y procesar first_name
        if "first_name" in data:
            first_name = str(data["first_name"]).strip()
            if not first_name: # Si se envía "" o "  "
                 return JsonResponse({"status": "error", "message": "El campo 'nombre' no puede estar vacío si se proporciona."}, status=HTTPStatus.BAD_REQUEST)
            name_error = validate_name_format(first_name, "nombre")
            if name_error:
                return JsonResponse({"status": "error", "message": name_error}, status=HTTPStatus.BAD_REQUEST)
            if user_instance.first_name != first_name:
                user_instance.first_name = first_name
                fields_to_update_on_model['first_name'] = first_name
        
        # 2. Validar y procesar last_name
        if "last_name" in data:
            last_name = str(data["last_name"]).strip()
            if not last_name:
                 return JsonResponse({"status": "error", "message": "El campo 'apellido' no puede estar vacío si se proporciona."}, status=HTTPStatus.BAD_REQUEST)
            name_error = validate_name_format(last_name, "apellido")
            if name_error:
                return JsonResponse({"status": "error", "message": name_error}, status=HTTPStatus.BAD_REQUEST)
            if user_instance.last_name != last_name:
                user_instance.last_name = last_name
                fields_to_update_on_model['last_name'] = last_name

        # 3. Validar y procesar username
        if "username" in data:
            username = str(data["username"]).strip()
            if not username:
                 return JsonResponse({"status": "error", "message": "El campo 'username' no puede estar vacío si se proporciona."}, status=HTTPStatus.BAD_REQUEST)
            if user_instance.username != username:
                if User.objects.filter(username__iexact=username).exclude(pk=user_instance.pk).exists():
                    return JsonResponse({"status": "error", "message": f"El nombre de usuario '{username}' ya está en uso."}, status=HTTPStatus.CONFLICT)
                user_instance.username = username
                fields_to_update_on_model['username'] = username
        
        # 4. Validar y procesar email
        if "email" in data:
            email = str(data["email"]).strip().lower()
            if not email:
                return JsonResponse({"status": "error", "message": "El campo 'email' no puede estar vacío si se proporciona."}, status=HTTPStatus.BAD_REQUEST)
            try:
                validate_email(email) # Usa el validador de Django
            except ValidationError:
                return JsonResponse({"status": "error", "message": "El formato del correo electrónico no es válido."}, status=HTTPStatus.BAD_REQUEST)
            if user_instance.email != email:
                if User.objects.filter(email__iexact=email).exclude(pk=user_instance.pk).exists():
                    return JsonResponse({"status": "error", "message": f"El correo electrónico '{email}' ya está registrado."}, status=HTTPStatus.CONFLICT)
                user_instance.email = email
                fields_to_update_on_model['email'] = email
                changes_for_email_notification["email_changed_to"] = email
        
        # 5. Validar y procesar password
        if "password" in data and data["password"] is not None:
            password = str(data["password"])
            if not password:
                return JsonResponse({"status": "error", "message": "La contraseña no puede estar vacía."}, status=HTTPStatus.BAD_REQUEST)
            password_error = validate_password_complexity(password)
            if password_error:
                return JsonResponse({"status": "error", "message": password_error}, status=HTTPStatus.BAD_REQUEST)
            user_instance.set_password(password) # Hashea y establece la contraseña
            new_plain_password_for_email = password
            changes_for_email_notification["password_changed"] = True
            # No se añade 'password' a fields_to_update_on_model, set_password se encarga o save() lo hace.

        # 6. Procesar is_admin (is_superuser)
        if "is_admin" in data:
            is_admin_value = data.get("is_admin")
            if not isinstance(is_admin_value, bool):
                return JsonResponse({"status": "error", "message": "El valor de 'is_admin' debe ser booleano (true/false)."}, status=HTTPStatus.BAD_REQUEST)
            if user_instance.is_superuser != is_admin_value:
                user_instance.is_superuser = is_admin_value
                fields_to_update_on_model['is_superuser'] = is_admin_value
                if is_admin_value and not original_is_superuser : # Se hizo admin
                    changes_for_email_notification["made_admin"] = True
        
        # 7. Procesar is_active
        if "is_active" in data:
            is_active_value = data.get("is_active")
            if not isinstance(is_active_value, bool):
                return JsonResponse({"status": "error", "message": "El valor de 'is_active' debe ser booleano (true/false)."}, status=HTTPStatus.BAD_REQUEST)
            if user_instance.is_active != is_active_value:
                user_instance.is_active = is_active_value
                fields_to_update_on_model['is_active'] = is_active_value
                if is_active_value and not original_is_active: # Se activó
                    changes_for_email_notification["became_active"] = True
                elif not is_active_value and original_is_active: # Se desactivó
                     changes_for_email_notification["became_inactive"] = True

        # Si no hay campos para actualizar en el modelo (pero podría haber cambio de contraseña)
        if not fields_to_update_on_model and not new_plain_password_for_email:
            if not changes_for_email_notification:
                return JsonResponse(
                    {"status": "info", "message": "No se proporcionaron datos diferentes para actualizar."},
                    status=HTTPStatus.OK
                )
        
        try:
            with transaction.atomic():
                if fields_to_update_on_model.keys() or new_plain_password_for_email:
                    user_instance.save(update_fields=list(fields_to_update_on_model.keys()) if fields_to_update_on_model else None)

                send_notification_email_flag = bool(changes_for_email_notification)

                if send_notification_email_flag:
                    email_subject = "Actualización de Cuenta"
                    if len(changes_for_email_notification) > 1: email_subject = "Actualizaciones Importantes en tu Cuenta"
                    elif "password_changed" in changes_for_email_notification: email_subject = "Tu Contraseña ha Cambiado"

                    html_email_body = generate_user_update_notification_html(
                        user_first_name=user_instance.first_name,
                        changes=changes_for_email_notification,
                        new_password_if_any=new_plain_password_for_email
                    )
                    
                    send_email_notification(
                        html_content=html_email_body,
                        subject=email_subject,
                        recipient_email=user_instance.email
                    )

            response_serializer = UserSerializer(user_instance)
            return JsonResponse(
                {"status": "ok", "message": "Usuario actualizado exitosamente.", "data": response_serializer.data},
                status=HTTPStatus.OK
            )

        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": f"No se pudo completar la actualización: {str(e)}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        

    @swagger_auto_schema(
        operation_id="api_user_delete_by_id",
        operation_description="Elimina un usuario específico por su ID. Requiere permiso 'user.delete_user'.",
        manual_parameters=[
            openapi.Parameter(
                name='id',
                in_=openapi.IN_PATH,
                description="ID numérico del usuario a eliminar.",
                required=True,
                type=openapi.TYPE_INTEGER
            ),
        ],
        security=bearer_security_definition, # Indica que este endpoint requiere el token Bearer
        responses={
            HTTPStatus.OK: openapi.Response( # 200 OK
                description="Usuario eliminado exitosamente.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="ok"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Usuario 'nombredeusuario' eliminado exitosamente."),
                    }
                )
            ),
            HTTPStatus.BAD_REQUEST: openapi.Response( # 400 Bad Request
                description="El ID de usuario proporcionado no es válido (e.g., no es un número entero).",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="El ID de usuario proporcionado no es válido. Debe ser un número entero."),
                    }
                )
            ),
            HTTPStatus.FORBIDDEN: openapi.Response( # 403 Forbidden
                description="Acceso denegado. No tienes permisos para eliminar este usuario (e.g., intentar eliminar un superusuario, auto-eliminación no permitida, o falta de permiso 'user.delete_user').",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                        'message': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="No tienes permisos para eliminar a un usuario administrador. / No puedes eliminar tu propia cuenta. Contacta a un administrador. / Acceso denegado - No tienes el permiso requerido: 'user.delete_user'."
                        ),
                    }
                )
            ),
            HTTPStatus.NOT_FOUND: openapi.Response( # 404 Not Found
                description="Usuario no encontrado con el ID proporcionado.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Usuario no encontrado."),
                    }
                )
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR: openapi.Response( # 500 Internal Server Error
                description="Error interno del servidor al intentar eliminar el usuario.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Ocurrió un error al intentar eliminar el usuario."),
                    }
                )
            )
        }
    )
    @authenticate_user(required_permission='user.delete_user')
    def delete(self, request, id): # 'id' viene de la URL, ej: http://192.168.1.6:8000/api/v1/user-control/2
        try:
            user_id = int(id)
            user_instance = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Usuario no encontrado."},
                status=HTTPStatus.NOT_FOUND
            )
        except ValueError:
            return JsonResponse(
                {"status": "error", "message": "El ID de usuario proporcionado no es válido. Debe ser un número entero."},
                status=HTTPStatus.BAD_REQUEST
            )

        if user_instance.is_superuser and not request.user.is_superuser:
            return JsonResponse(
                {"status": "error", "message": "No tienes permisos para eliminar a un usuario administrador."},
                status=HTTPStatus.FORBIDDEN
            )

        if request.user.id == user_instance.id:
            if not request.user.is_superuser:
                 return JsonResponse(
                    {"status": "error", "message": "No puedes eliminar tu propia cuenta. Contacta a un administrador."},
                    status=HTTPStatus.FORBIDDEN
                )
            return JsonResponse(
                {"status": "error", "message": "La auto-eliminación de cuentas no está permitida a través de este endpoint."},
                status=HTTPStatus.FORBIDDEN
            )

        try:
            with transaction.atomic():
                deleted_username = user_instance.username 

                user_instance.delete()
            
            return JsonResponse(
                {"status": "ok", "message": f"Usuario '{deleted_username}' eliminado exitosamente."},
                status=HTTPStatus.OK 
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": f"Ocurrió un error al intentar eliminar el usuario: {str(e)}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )


class Login(APIView):


    permission_classes = [permissions.AllowAny]
    

    @swagger_auto_schema(
        operation_id="api_login_user",
        operation_description="Endpoint para iniciar sesión y obtener un token de autenticación.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email_or_username', 'password'],
            properties={
                'email_or_username': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Correo electrónico o nombre de usuario del usuario."
                ),
                'password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_PASSWORD,
                    description="Contraseña del usuario."
                ),
            }
        ),
        responses={
            HTTPStatus.OK: openapi.Response( # 200 OK
                description="Inicio de sesión exitoso. Devuelve el token y datos básicos del usuario.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="ok"
                        ),
                        'message': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Inicio de sesión exitoso."
                        ),
                        'token': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Token JWT de autenticación.",
                            example="eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpZCI6MSwidXNlcm5hb...uz7g"
                        ),
                        'user': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description="Datos básicos del usuario autenticado.",
                            properties={
                                'id': openapi.Schema(
                                    type=openapi.TYPE_INTEGER,
                                    description="ID del usuario.",
                                    example=1
                                ),
                                'username': openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    description="Nombre de usuario.",
                                    example="kloquereport"
                                ),
                                'email': openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    format=openapi.FORMAT_EMAIL,
                                    description="Correo electrónico del usuario.",
                                    example="me@kloquereport.com"
                                ),
                                'first_name': openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    description="Nombre(s) del usuario. Puede estar vacío.",
                                    example=""
                                )
                            }
                        )
                    }
                )
            ),
            HTTPStatus.BAD_REQUEST: openapi.Response( # 400 Bad Request
                description="Solicitud incorrecta (e.g., campos faltantes o formato inválido).",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="El campo 'X' es requerido."),
                    }
                )
            ),
            HTTPStatus.UNAUTHORIZED: openapi.Response( # 401 Unauthorized
                description="Credenciales inválidas, usuario no encontrado o el usuario no está activo.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Credenciales inválidas o usuario no encontrado."),
                    }
                )
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR: openapi.Response( # 500 Internal Server Error
                description="Error interno al intentar generar el token.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example="error"),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="No se pudo generar el token de autenticación."),
                    }
                )
            )
        },
        tags=['Autenticación']
    )
    def post(self, request):
        required_fields = ["email_or_username", "password"]
        error_response = validate_required_fields(request.data, required_fields)
        if error_response:
            return error_response

        email_or_username = request.data.get("email_or_username").strip()
        password = request.data.get("password")

        user_obj = None
        try:
            user_obj = User.objects.get(Q(username=email_or_username) | Q(email=email_or_username.lower()))
        except User.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": "Credenciales inválidas o usuario no encontrado."
            }, status=HTTPStatus.UNAUTHORIZED)

        user = authenticate(request, username=user_obj.username, password=password)

        if user is not None:
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            now = datetime.now()
            expiration = now + timedelta(days=1)
            expiration_timestamp = int(datetime.timestamp(expiration))
            
            base_url_with_port = get_base_url_with_port()

            payload = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_superuser": user.is_superuser,
                "iss": base_url_with_port,
                "iat": int(time.time()),
                "exp": expiration_timestamp
            }

            try:
                token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS512')
                return JsonResponse({
                    "status": "ok",
                    "message": "Inicio de sesión exitoso.",
                    "token": token,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name
                    }
                })
            except Exception as e:
                return JsonResponse({
                    "status": "error",
                    "message": f"No se pudo generar el token de autenticación. {e}"
                }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        else:
            return JsonResponse({
                "status": "error",
                "message": "Credenciales inválidas o usuario no encontrado."
            }, status=HTTPStatus.UNAUTHORIZED)