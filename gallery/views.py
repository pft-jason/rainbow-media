# views.py
from django.shortcuts import render, redirect
from .forms import ImageUploadForm
from django.contrib.auth.decorators import login_required
from .models import Image
from django.core.exceptions import PermissionDenied

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
    # Example: Show a single image
    try:
        image = Image.objects.get(id=image_id)
    except Image.DoesNotExist:
        raise Http404("Image not found")
    return render(request, 'image_detail.html', {'image': image})