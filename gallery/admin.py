from django.contrib import admin
from .models import UserProfile, Image, Tag, Category, Report, Comment, Like, Dislike, Favorite, Album

# Registering models in the admin interface
admin.site.register(UserProfile)
admin.site.register(Image)
admin.site.register(Tag)
admin.site.register(Category)
admin.site.register(Report)
admin.site.register(Comment)
admin.site.register(Like)
admin.site.register(Dislike)
admin.site.register(Favorite)
admin.site.register(Album)
