from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_image, name='upload_image'),
    path('', views.gallery, name='gallery'),
    path('image/<int:image_id>/', views.image_detail, name='image_detail'),  # Example for viewing a single image
]
