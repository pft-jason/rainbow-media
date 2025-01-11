# views.py

#-----------------------------------#
# Imports
#-----------------------------------#

import json

from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponse, JsonResponse

from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied

from django.contrib.auth import login
from django.contrib.auth.models import User

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from .models import (
    Tag, Report, AlbumImage, add_image_to_album, Album, Follow, Image, 
    get_image_visibility, UserProfile, search_images, Like, Favorite, Comment, 
    ModerationStatus, remove_from_favorites, add_to_favorites, add_like_to_album, 
    add_album_to_favorites )
from .forms import (
    ReportForm, ImageUploadForm, UserRegistrationForm, UserProfileForm, 
    ImageUpdateForm, CommentForm )

from django.db.models import OuterRef, Exists, Count, Case, When, BooleanField
from gallery.utils import staff_required, add_image_to_album

#-----------------------------------#
# Admin Views
#-----------------------------------#

@staff_required
def admin_page(request):
    pending_images_count = Image.objects.filter(moderation_status=ModerationStatus.PENDING).count()
    reported_images_count = Image.objects.filter(report__status='PENDING').distinct().count()
    return render(request, 'admin_page.html', {
        'pending_images_count': pending_images_count,
        'reported_images_count': reported_images_count,
    })

@staff_required
def admin_pending_images(request):
    pending_images = Image.objects.filter(moderation_status=ModerationStatus.PENDING)
    return render(request, 'admin_pending_images.html', {'pending_images': pending_images})

@staff_required
def admin_reported_images(request):
    reported_images = Image.objects.filter(report__status='PENDING').distinct()
    return render(request, 'admin_reported_images.html', {'reported_images': reported_images})

@staff_required
def admin_reported_comments(request):
    reported_comments = Comment.objects.filter(report__status='PENDING').distinct()
    return render(request, 'admin_reported_comments.html', {'reported_comments': reported_comments})

@staff_required
def admin_user_management(request):
    return render(request, 'admin_user_management.html')

@staff_required
def admin_site_statistics(request):
    return render(request, 'admin_site_statistics.html')

@staff_required
def admin_system_logs(request):
    return render(request, 'admin_system_logs.html')

#-----------------------------------#
# Gallery Views
#-----------------------------------#

def search(request):
    query = request.GET.get('q')
    if query:
        images = search_images(query, user=request.user)
    else:
        images = Image.objects.get_filtered_images(user=request.user)
    return render(request, 'search_results.html', {'images': images, 'query': query})

def gallery(request, tag_id=None):
    if tag_id:
        tag = get_object_or_404(Tag, id=tag_id)
        images = Image.objects.get_filtered_images(request.user).filter(tags=tag)
    else:
        tag = None
        images = Image.objects.get_filtered_images(request.user)

    filter_type = request.GET.get('filter', 'newest')
    if filter_type == 'newest':
        images = images.order_by('-uploaded_at')
    elif filter_type == 'oldest':
        images = images.order_by('uploaded_at')
    elif filter_type == 'most_liked':
        images = images.annotate(like_count=Count('liked_by')).order_by('-like_count')
    elif filter_type == 'most_favorited':
        images = images.annotate(favorite_count=Count('favorited_by')).order_by('-favorite_count')

    if request.user.is_authenticated:    
        # Annotate each image to see if the user has liked it
        user_likes = Like.objects.filter(user=request.user, image=OuterRef('pk'))
        user_favorites = Favorite.objects.filter(user=request.user, image=OuterRef('pk'))
        images = images.annotate(
            user_has_liked=Exists(user_likes),
            user_has_favorited=Exists(user_favorites)    
        )

    paginator = Paginator(images, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'gallery/gallery.html', {'page_obj': page_obj, 'tag': tag})

def album_gallery(request):
    # Get filtered albums based on the current user

    albums = Album.objects.get_filtered_albums(request.user)
    

    filter_type = request.GET.get('filter', 'newest')
    if filter_type == 'newest':
        albums = albums.order_by('-created_at')
    elif filter_type == 'oldest':
        albums = albums.order_by('created_at')
    elif filter_type == 'most_liked':
        albums = albums.annotate(like_count=Count('liked_by')).order_by('-like_count')
    elif filter_type == 'most_favorited':
        albums = albums.annotate(favorite_count=Count('favorited_by')).order_by('-favorite_count')
    print(albums)
    # Pagination: Show 20 albums per page
    paginator = Paginator(albums, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'album_gallery.html', {'page_obj': page_obj})

def tags_view(request):
    tags = Tag.objects.all().order_by('name')
    return render(request, 'gallery/tags.html', {'tags': tags})

#-----------------------------------#
# Form Views
#-----------------------------------#

@login_required
def report_comment_view(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Check if the user has already reported this comment
    existing_report = Report.objects.filter(reported_by=request.user, comment=comment).exists()
    if existing_report:
        return redirect('gallery')
    
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reported_by = request.user
            report.comment = comment
            report.save()
            return redirect('gallery')
    else:
        form = ReportForm()
    return render(request, 'report_comment.html', {'form': form, 'comment': comment})

@login_required
def upload_image(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            form.save(user=request.user, commit=True) 
            return redirect('gallery')
        else:
            return render(request, 'upload_image.html', {'form': form, 'error': 'There was an error with your upload.'})
    else:
        form = ImageUploadForm(user=request.user)
    return render(request, 'upload_image.html', {'form': form})

@login_required
def update_image(request, image_id):
    image = get_object_or_404(Image, id=image_id)
    if request.user == image.user or request.user.is_staff:
        if request.method == 'POST':
            form = ImageUpdateForm(request.POST, request.FILES, instance=image)
            if form.is_valid():
                form.save(commit=True)
                return redirect('image_detail', image_id=image.id)
        else:
            form = ImageUpdateForm(instance=image)
        return render(request, 'update_image.html', {'form': form, 'image': image})
    else:
        return redirect('gallery')  # Redirect to a different page if the user is not authorized

@login_required
def profile_edit(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = UserProfileForm(instance=user_profile)
    return render(request, 'profile_edit.html', {'form': form})

@login_required
def create_album(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        album = Album.objects.create(user=request.user, name=name)
        return redirect('profile')
    return render(request, 'create_album.html')

@login_required
def report_image_view(request, image_id):
    image = get_object_or_404(Image, id=image_id)
    
    # Check if the user has already reported this image
    existing_report = Report.objects.filter(reported_by=request.user, image=image).exists()
    if existing_report:
        # Redirect to the gallery with a message or handle it as needed
        return redirect('gallery')
    
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reported_by = request.user
            report.image = image
            report.save()
            return redirect('gallery')
    else:
        form = ReportForm()
    return render(request, 'report_image.html', {'form': form, 'image': image})

#-----------------------------------#
# Profile Views
#-----------------------------------#

@login_required
def profile(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    user_images = Image.objects.filter(user=request.user) [:12]  # Display the latest 8 images
    user_albums = Album.objects.filter(user=request.user) 
    return render(request, 'profile.html', {'user_profile': user_profile, 'user_images': user_images, 'user_albums': user_albums, 'is_following': False})

@login_required
def user_profile(request, username):
    user_profile = get_object_or_404(UserProfile, user__username=username)
    user_images = Image.objects.filter(user=user_profile.user)
    user_images = Image.objects.get_filtered_images(user=request.user).filter(id__in=user_images).order_by('-uploaded_at')[:12]
    user_albums = Album.objects.filter(user=user_profile.user) 
    is_following = Follow.objects.filter(follower=request.user, followed=user_profile.user).exists()
    
    return render(request, 'user_profile.html', {
        'user_profile': user_profile,
        'user_images': user_images,
        'user_albums': user_albums,
        'is_following': is_following,
    })

def user_gallery(request, username):
    user = get_object_or_404(User, username=username)
    images = Image.objects.get_filtered_images(request.user).filter(user=user).order_by('-uploaded_at')
    paginator = Paginator(images, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'user_gallery.html', {'page_obj': page_obj, 'user': user})

@login_required
def user_albums(request, username):
    user_profile = get_object_or_404(UserProfile, user__username=username)
    user_albums = Album.objects.filter(user=user_profile.user)
    return render(request, 'user_albums.html', {'user_profile': user_profile, 'user_albums': user_albums})

#-----------------------------------#
# Authentication Views
#-----------------------------------#

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('gallery')
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})

#-----------------------------------#
# Detail Views
#-----------------------------------#

def image_detail(request, image_id):
    image = get_object_or_404(Image, id=image_id)

    if not request.user.is_staff:
        if not get_image_visibility(request.user, image):
            raise PermissionDenied("You do not have permission to view this image.")
    
    comment_form = CommentForm()
    if request.user.is_authenticated:
        user_albums = Album.objects.filter(user=request.user)
    else:
        user_albums = Album.objects.none()  # or handle the case when the user is not authenticated
    # TODO: set up so user can select whether comments on their images are moderated or not.
    # comments = image.comments.filter(moderation_status=ModerationStatus.APPROVED)
    comments = image.comments.all().order_by('-created_at')
    return render(request, 'image_detail.html', {
        'image': image,
        'comment_form': comment_form,
        'user_albums': user_albums,
        'comments': comments,
    })

@login_required
def album_detail(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    return render(request, 'album_detail.html', {'album': album})
