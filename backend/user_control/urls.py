from django.urls import path
from .views import *

urlpatterns = [
    path('user-control', UserRC.as_view()),
    path('user-control/<int:id>', UserRUD.as_view()),
    path('user-control/login', Login.as_view()),
]