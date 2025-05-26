from django.urls import path
from .views import *

urlpatterns = [
    path('incident', IncidentRC.as_view()),
    path('incident/<int:id>', IncidentRUD.as_view()),
    path('incident/sdelete/<int:id>', IncidentSD.as_view()),
    path('incident/edit-image', EditImage.as_view()),
]