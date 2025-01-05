from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib import admin
from django.urls import path
from gallery import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    
    path('upload/', views.upload_image, name='upload_image'),
    path('', views.gallery, name='gallery'),
    path('image/<int:image_id>/', views.image_detail, name='image_detail'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('user/<str:username>/gallery/', views.user_gallery, name='user_gallery'),
    path('image/<int:image_id>/update/', views.update_image, name='update_image'), 
    path('search/', views.search, name='search'),
    path('image/<int:image_id>/add_to_album/', views.add_to_album, name='add_to_album'),
    path('image/<int:image_id>/like/', views.like_image, name='like_image'),
    path('image/<int:image_id>/dislike/', views.dislike_image, name='dislike_image'),
    path('image/<int:image_id>/download/', views.download_image, name='download_image'),
    path('image/<int:image_id>/favorite/', views.favorite_image, name='favorite_image'),
    path('image/<int:image_id>/comment/', views.submit_comment, name='submit_comment'),
    path('comment/<int:comment_id>/<str:action>/', views.moderate_comment, name='moderate_comment'),
    path('album/<int:album_id>/', views.album_detail, name='album_detail'),
    path('user/<str:username>/', views.user_profile, name='user_profile'),  # New URL pattern
    path('user/<int:user_id>/follow/', views.follow_user, name='follow_user'),
    path('albums/<str:username>/', views.user_albums, name='user_albums'),
    path('album/create/', views.create_album, name='create_album'),
    path('save_image_order/<int:album_id>/', views.save_image_order, name='save_image_order'),
    
    path('admin_page/', views.admin_page, name='admin_page'),  # Add this line
    path('admin/pending-images/', views.admin_pending_images, name='admin_pending_images'),
    path('admin/reported-images/', views.admin_reported_images, name='admin_reported_images'),
    path('admin/reported-comments/', views.admin_reported_comments, name='admin_reported_comments'),
    path('admin/user-management/', views.admin_user_management, name='admin_user_management'),
    path('admin/site-statistics/', views.admin_site_statistics, name='admin_site_statistics'),
    path('admin/system-logs/', views.admin_system_logs, name='admin_system_logs'),
    

    path('admin/pending-images/approve/<int:image_id>/', views.admin_approve_image, name='admin_approve_image'),
    path('admin/reported-images/', views.admin_reported_images, name='admin_reported_images'),
    path('admin/', admin.site.urls),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)