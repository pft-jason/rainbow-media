# views.py
from django.shortcuts import render, redirect, get_object_or_404
from .forms import ImageUploadForm, UserRegistrationForm, UserProfileForm, ImageUpdateForm, CommentForm
from django.contrib.auth.decorators import login_required
from .models import Follow, Image, get_image_visibility, UserProfile, search_images, Like, Dislike, Favorite, Comment, ModerationStatus
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.core.paginator import Paginator
from django.contrib.auth import login
from django.contrib.auth.models import User
import json

def search(request):
    query = request.GET.get('q')
    if query:
        images = search_images(query, user=request.user)
    else:
        images = Image.objects.get_filtered_images(user=request.user)
    return render(request, 'search_results.html', {'images': images, 'query': query})

@login_required
def upload_image(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            form.save(user=request.user, commit=True)        
            return redirect('gallery')
        else:
            return render(request, 'upload_image.html', {'form': form, 'error': 'There was an error with your upload.'})
    else:
        form = ImageUploadForm()
    return render(request, 'upload_image.html', {'form': form})

@login_required
def update_image(request, image_id):
    image = get_object_or_404(Image, id=image_id, user=request.user)
    if request.method == 'POST':
        form = ImageUpdateForm(request.POST, request.FILES, instance=image)
        if form.is_valid():
            form.save(commit=True)
            return redirect('image_detail', image_id=image.id)
    else:
        form = ImageUpdateForm(instance=image)
    return render(request, 'update_image.html', {'form': form, 'image': image})

@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    user_images = Image.objects.filter(user=request.user) [:8]  # Display the latest 8 images
    return render(request, 'profile.html', {'user_profile': user_profile, 'user_images': user_images, 'is_following': False})

@login_required
def user_profile(request, username):
    user_profile = get_object_or_404(UserProfile, user__username=username)
    user_images = Image.objects.get_filtered_images(user_profile.user)[:8]  # Display the latest 8 images
    is_following = Follow.objects.filter(follower=request.user, followed=user_profile.user).exists()
    
    return render(request, 'user_profile.html', {
        'user_profile': user_profile,
        'user_images': user_images,
        'is_following': is_following,
    })

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


def gallery(request):
    # Get filtered images based on the current user
    images = Image.objects.get_filtered_images(request.user)

    # Pagination: Show 20 images per page
    paginator = Paginator(images, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'gallery.html', {'page_obj': page_obj})

def user_gallery(request, username):
    user = get_object_or_404(User, username=username)
    images = Image.objects.get_filtered_images(request.user).filter(user=user).order_by('-uploaded_at')
    paginator = Paginator(images, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'user_gallery.html', {'page_obj': page_obj, 'user': user})
    
def image_detail(request, image_id):
    image = get_object_or_404(Image, id=image_id)


    if not request.user.is_staff:
        if not get_image_visibility(request.user, image):
            raise PermissionDenied("You do not have permission to view this image.")
    
    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.user = request.user
            comment.image = image
            comment.save()
            return redirect('image_detail', image_id=image.id)
    else:
        comment_form = CommentForm()

    comments = image.comments.filter(moderation_status=ModerationStatus.APPROVED)
    return render(request, 'image_detail.html', {'image': image, 'comment_form': comment_form, 'comments': comments})

def like_image(request, image_id):
    image = get_object_or_404(Image, id=image_id)
    like, created = Like.objects.get_or_create(user=request.user, image=image)
    if not created:
        # If the like already exists, remove it (toggle like)
        like.delete()
    else:
        # If a dislike exists, remove it
        Dislike.objects.filter(user=request.user, image=image).delete()
    return redirect('image_detail', image_id=image.id)

def dislike_image(request, image_id):
    image = get_object_or_404(Image, id=image_id)
    dislike, created = Dislike.objects.get_or_create(user=request.user, image=image)
    if not created:
        # If the dislike already exists, remove it (toggle dislike)
        dislike.delete()
    else:
        # If a like exists, remove it
        Like.objects.filter(user=request.user, image=image).delete()
    return redirect('image_detail', image_id=image.id)

def download_image(request, image_id):
    image = get_object_or_404(Image, id=image_id)
    # Implement your logic for downloading the image
    # For example, serve the image file as a download
    response = HttpResponse(image.image_file, content_type='application/force-download')
    response['Content-Disposition'] = f'attachment; filename="{image.image_file.name}"'
    return response

def favorite_image(request, image_id):
    image = get_object_or_404(Image, id=image_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, image=image)
    if not created:
        favorite.delete()
    return redirect('image_detail', image_id=image.id)

@login_required
def submit_comment(request, image_id):
    image = get_object_or_404(Image, id=image_id)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.image = image
            comment.save()
            return redirect('image_detail', image_id=image.id)
    else:
        form = CommentForm()
    return render(request, 'submit_comment.html', {'form': form, 'image': image})

@login_required
def moderate_comment(request, comment_id, action):
    comment = get_object_or_404(Comment, id=comment_id)
    if action == 'approve':
        comment.moderation_status = Comment.APPROVED
    elif action == 'reject':
        comment.moderation_status = Comment.REJECTED
    comment.save()
    return redirect('image_detail', image_id=comment.image.id)

@login_required
def follow_user(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)
    follow, created = Follow.objects.get_or_create(follower=request.user, followed=user_to_follow)
    if not created:
        # If the follow relationship already exists, remove it (unfollow)
        follow.delete()
    return redirect('user_profile', username=user_to_follow.username)