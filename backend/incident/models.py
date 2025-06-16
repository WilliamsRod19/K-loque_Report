from django.db import models
from django.conf import settings

# Create your models here.

class Incident(models.Model):

    STATUS_ACTIVE = 'activo'
    STATUS_RESOLVED = 'resuelto'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Incidente Activo'),
        (STATUS_RESOLVED, 'Incidente Resuelto'),
    ]

    incident_type = models.CharField(max_length=100, null=False, blank=False, verbose_name="tipo de incidente")
    description = models.TextField(null=False, blank=False, verbose_name="descripción")
    date = models.CharField(max_length=50, null=False, blank=False, verbose_name="fecha del incidente")
    image_url = models.URLField(max_length=255, null=True, blank=True, verbose_name="URL de la Imagen")
    image_public_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="Cloudinary Public ID")
    comment = models.TextField(null=True, blank=True, verbose_name="comentario de solución")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        null=False,
        blank=False,
        verbose_name="estado del incidente"
    )

    active = models.BooleanField(default=True, verbose_name="activo")
    created_by = models.IntegerField(null=True, blank=True, verbose_name="creado por")
    created_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name="fecha de creación")
    modified_by = models.IntegerField(null=True, blank=True, verbose_name="modificado por")
    updated_at = models.DateTimeField(auto_now=True, editable=False, verbose_name="última modificación")

    def str(self):
        return f"{self.incident_type} - ({self.get_status_display()})"

    class Meta:
        db_table = 'incident'
        verbose_name = "Incidente"
        verbose_name_plural = "Incidentes"