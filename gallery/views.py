# views.py
from django.shortcuts import render, redirect, get_object_or_404
from .forms import ImageUploadForm, UserRegistrationForm, UserProfileForm
from django.contrib.auth.decorators import login_required
from .models import Image, get_image_visibility, UserProfile
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.core.paginator import Paginator
from django.contrib.auth import login
from django.contrib.auth.models import User
import json



@login_required
def upload_image(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the image with the current user as the owner
            image = form.save(commit=False)
            image.user = request.user
            image.save()
            return redirect('gallery')  # Redirect to the gallery page after upload
        else:
            # Handle invalid form
            return render(request, 'upload_image.html', {'form': form, 'error': 'There was an error with your upload.'})
    else:
        form = ImageUploadForm()

    return render(request, 'upload_image.html', {'form': form})

@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    user_images = Image.objects.filter(user=request.user)[:8]  # Display the latest 8 images
    return render(request, 'profile.html', {'user_profile': user_profile, 'user_images': user_images})

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
    try:
        image = Image.objects.get(id=image_id)
    except Image.DoesNotExist:
        raise Http404("Image not found")
    
    # Check if the user has permission to view the image based on privacy settings
    if not get_image_visibility(request.user, image):
        raise PermissionDenied("You do not have permission to view this image.")
    
    return render(request, 'image_detail.html', {'image': image})