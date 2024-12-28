# views.py
from django.shortcuts import render, redirect
from .forms import ImageUploadForm, UserRegistrationForm
from django.contrib.auth.decorators import login_required
from .models import Image, get_image_visibility
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.core.paginator import Paginator
from django.contrib.auth import login


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

def image_detail(request, image_id):
    try:
        image = Image.objects.get(id=image_id)
    except Image.DoesNotExist:
        raise Http404("Image not found")
    
    # Check if the user has permission to view the image based on privacy settings
    if not get_image_visibility(request.user, image):
        raise PermissionDenied("You do not have permission to view this image.")
    
    return render(request, 'image_detail.html', {'image': image})