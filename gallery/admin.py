from django.contrib import admin
from .models import AlbumImage, UserProfile, Image, Tag, Category, Report, Comment, Like, Favorite, Album, AlbumLike, AlbumFavorite, AlbumImage

class ImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'uploaded_at', 'moderation_status', 'width', 'height', 'format', 'size')  # Add new fields to list view
    list_filter = ('moderation_status', 'privacy')  # Add filters
    search_fields = ('title', 'description')  # Allow search by title or description
    readonly_fields = ('width', 'height', 'format', 'size')  # Allow search by title or description

# Registering models in the admin interface
admin.site.register(UserProfile)
admin.site.register(Image, ImageAdmin)
admin.site.register(Tag)
admin.site.register(Category)
admin.site.register(Report)
admin.site.register(Comment)
admin.site.register(Like)
admin.site.register(Favorite)
admin.site.register(Album)
admin.site.register(AlbumImage)
admin.site.register(AlbumLike)
admin.site.register(AlbumFavorite)

