from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib import admin
from django.urls import path
from gallery import views
from django.views.generic import RedirectView
from gallery import interactions

urlpatterns = [

# GALLERY URLS

    #--------------------------#
    # Redirects                #
    #--------------------------#
    path('', RedirectView.as_view(url='/explore/media/', permanent=False)),    

    #--------------------------#
    # Authentication URLs      #
    #--------------------------#
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    #--------------------------#
    # Gallery URLs             #
    #--------------------------#
    path('explore/media/', views.gallery, name='gallery'),
    path('gallery/tag/<int:tag_id>/', views.gallery, name='tagged_images'),
    path('explore/albums/', views.album_gallery, name='albums'),
    path('explore/tags/', views.tags_view, name='tags'),
    path('search/', views.search, name='search'),

    #--------------------------#
    # Forms URLs               #
    #--------------------------#
    path('upload/', views.upload_image, name='upload_image'),
    path('image/<int:image_id>/update/', views.update_image, name='update_image'), 
    path('image/<int:image_id>/add_to_album/', interactions.add_to_album, name='add_to_album'),
    path('image/<int:image_id>/comment/', interactions.submit_comment, name='submit_comment'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('comment/<int:comment_id>/<str:action>/', interactions.moderate_comment, name='moderate_comment'),
    path('album/create/', views.create_album, name='create_album'),
    path('report_image/<int:image_id>/', views.report_image_view, name='report_image'),
    path('report_comment/<int:comment_id>/', views.report_comment_view, name='report_comment'),

    #--------------------------#
    # Detail URLs              #
    #--------------------------#
    path('explore/image/<int:image_id>/', views.image_detail, name='image_detail'),
    path('explore/tags/<int:tag_id>/', views.gallery, name='tagged_images'),
    path('album/<int:album_id>/', views.album_detail, name='album_detail'),

    #--------------------------#
    # Image Interaction URLs   #
    #--------------------------#
    path('image/<int:image_id>/download/', interactions.download_image, name='download_image'),
    path('image/<int:image_id>/like/', interactions.like_image, name='like_image'),
    path('image/<int:image_id>/favorite/', interactions.favorite_image, name='favorite_image'),

    #--------------------------#
    # Album Interaction URLs   #
    #--------------------------#
    path('like_album/<int:album_id>/', interactions.like_album_view, name='like_album'),
    path('favorite_album/<int:album_id>/', interactions.favorite_album_view, name='favorite_album'),
    path('report_album/<int:album_id>/', interactions.report_album_view, name='report_album'),
    path('set_cover_image/', interactions.set_cover_image, name='set_cover_image'),
    path('save_image_order/<int:album_id>/', interactions.save_image_order, name='save_image_order'),

    #--------------------------#
    # Profile URLs             #
    #--------------------------#
    path('profile/', views.profile, name='profile'),
    path('user/<str:username>/', views.user_profile, name='user_profile'),  # New URL pattern
    path('user/<int:user_id>/follow/', interactions.follow_user, name='follow_user'),
    path('user/<str:username>/gallery/', views.user_gallery, name='user_gallery'),
    path('albums/<str:username>/', views.user_albums, name='user_albums'),

# ADMIN URLS

    #--------------------------#
    # Admin URLs               #
    #--------------------------#
    path('admin_page/', views.admin_page, name='admin_page'),
    
    #--------------------------#
    # Admin Image URLs         #
    #--------------------------#
    path('admin/pending-images/', views.admin_pending_images, name='admin_pending_images'),
    path('admin/reported-images/', views.admin_reported_images, name='admin_reported_images'),
    path('admin/reported-comments/', views.admin_reported_comments, name='admin_reported_comments'),
    path('admin/reported-comments/resolve/<int:report_id>/', interactions.admin_resolve_comment_report, name='admin_resolve_comment_report'),
    path('admin/user-management/', views.admin_user_management, name='admin_user_management'),
    path('admin/site-statistics/', views.admin_site_statistics, name='admin_site_statistics'),
    path('admin/system-logs/', views.admin_system_logs, name='admin_system_logs'),

    #--------------------------#
    # Admin Interaction URLs   #
    #--------------------------#
    path('admin/reported-images/resolve/<int:report_id>/', interactions.admin_resolve_report, name='admin_resolve_report'),
    path('admin/pending-images/approve/<int:image_id>/', interactions.admin_approve_image, name='admin_approve_image'),
    
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)