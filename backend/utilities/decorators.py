from functools import wraps
from django.http import JsonResponse
from http import HTTPStatus
from jose import jwt
from django.conf import settings
from django.contrib.auth.models import User
import time

def authenticate_user(required_permission=None):
    """
    Decorador que autentica al usuario y verifica si tiene el permiso requerido.
    
    Args:
        required_permission: String con el permiso requerido (opcional). Si es None,
                             solo verifica autenticación.
    """
    def decorator(func):
        @wraps(func)
        def _wrapped_view(request_instance, *args, **kwargs):

            actual_request = None
            if hasattr(request_instance, 'request'):
                actual_request = request_instance.request
            elif args and hasattr(args[0], 'headers'):
                actual_request = args[0]
            elif 'request' in kwargs:
                actual_request = kwargs['request']
            else:
                 actual_request = request_instance


            if not actual_request:
                return JsonResponse({
                    "status": "error",
                    "message": "Error interno: No se pudo determinar el objeto de solicitud."
                }, status=HTTPStatus.INTERNAL_SERVER_ERROR)

            auth_header = actual_request.headers.get('Authorization')
            
            if not auth_header:
                return JsonResponse({
                    "status": "error",
                    "message": "Acceso no autorizado - Falta la cabecera de Autorización."
                }, status=HTTPStatus.UNAUTHORIZED)

            try:
                if not auth_header.startswith("Bearer "):
                    return JsonResponse({
                        "status": "error",
                        "message": "Acceso no autorizado - Formato de token inválido. Debe ser 'Bearer <token>'."
                    }, status=HTTPStatus.UNAUTHORIZED)
                
                token = auth_header.split(" ")[1]
                decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS512'])
            except jwt.ExpiredSignatureError:
                return JsonResponse({
                    "status": "error",
                    "message": "Acceso no autorizado - El token ha expirado."
                }, status=HTTPStatus.UNAUTHORIZED)
            except jwt.JWTError:
                 return JsonResponse({
                    "status": "error",
                    "message": "Acceso no autorizado - Token inválido o corrupto."
                }, status=HTTPStatus.UNAUTHORIZED)
            except IndexError:
                 return JsonResponse({
                    "status": "error",
                    "message": "Acceso no autorizado - Formato de cabecera de Autorización incorrecto."
                }, status=HTTPStatus.UNAUTHORIZED)
            except Exception:
                return JsonResponse({
                    "status": "error",
                    "message": "Acceso no autorizado - Token inválido."
                }, status=HTTPStatus.UNAUTHORIZED)

            if int(decoded.get("exp", 0)) <= int(time.time()):
                return JsonResponse({
                    "status": "error",
                    "message": "Acceso no autorizado - El token ha expirado."
                }, status=HTTPStatus.UNAUTHORIZED)
            
            user_id = decoded.get("id")
            if not user_id:
                return JsonResponse({
                    "status": "error",
                    "message": "Acceso no autorizado - Información de usuario no encontrada en el token."
                }, status=HTTPStatus.UNAUTHORIZED)

            try:
                user = User.objects.get(id=user_id)
                
                actual_request.user = user

                if user.is_superuser:
                    if hasattr(request_instance, 'request'):
                        return func(request_instance, actual_request, *args[1:], **kwargs)
                    else:
                        return func(actual_request, *args, **kwargs)

                if required_permission:
                    if not user.has_perm(required_permission):
                        return JsonResponse({
                            "status": "error",
                            "message": f"Acceso denegado - No tienes el permiso requerido: '{required_permission}'."
                        }, status=HTTPStatus.FORBIDDEN)
                
                if hasattr(request_instance, 'request'):
                    return func(request_instance, actual_request, *args[1:], **kwargs)
                else:
                    return func(actual_request, *args, **kwargs)
                
            except User.DoesNotExist:
                return JsonResponse({
                    "status": "error",
                    "message": "Acceso no autorizado - Usuario no encontrado."
                }, status=HTTPStatus.UNAUTHORIZED)
            except Exception as e:
                return JsonResponse({
                    "status": "error",
                    "message": f"Error interno del servidor durante la autenticación. {e}"
                }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            
        return _wrapped_view
    return decorator