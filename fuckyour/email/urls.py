from django.urls import path

from . import views

app_name = "fuckyour.email"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("message/<path:message_id>", views.message, name="message"),
]
