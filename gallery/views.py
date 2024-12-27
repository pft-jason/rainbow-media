# views.py
from django.shortcuts import render, redirect
from .forms import ImageUploadForm
from django.contrib.auth.decorators import login_required
from .models import Image

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

def gallery(request):
    images = Image.objects.filter(is_public=True)  # Only show public images
    return render(request, 'gallery.html', {'images': images})