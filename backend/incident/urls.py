from django.urls import path
from .views import *

urlpatterns = [
    path('incident', IncidentRC.as_view()),
    path('incident/<int:id>', IncidentRUD.as_view()),
    path('incident/sdelete/<int:id>', IncidentSD.as_view()),
    path('incident/edit-image', EditImage.as_view()),
    path('incident/active-reports', ActiveReports.as_view()),
    path('incident/specific-report/<int:id>', SpecificReport.as_view()),
    path('incident/archive-report/<int:id>', ArchivedReport.as_view()),
]