# views.py
from django.shortcuts import render, redirect
from .forms import ImageUploadForm
from django.contrib.auth.decorators import login_required
from .models import Image
from django.core.exceptions import PermissionDenied
from django.http import Http404

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
        form = ImageUploadForm()

    return render(request, 'upload_image.html', {'form': form})

def gallery_view(request):
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