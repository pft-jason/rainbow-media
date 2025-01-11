from django.contrib.auth.decorators import user_passes_test

def staff_required(view_func):
    decorated_view_func = user_passes_test(lambda u: u.is_staff)(view_func)
    return decorated_view_func

def add_image_to_album(user, image, album_id):
    """Adds an image to the specified album."""
    album = Album.objects.get(id=album_id, user=user)
    album.images.add(image)

def like_album_view(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    add_like_to_album(request.user, album)
    return redirect('album_detail', album_id=album_id)

def favorite_album_view(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    add_album_to_favorites(request.user, album)
    return redirect('album_detail', album_id=album_id)

def report_album_view(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    # Implement report logic here
    return redirect('album_detail', album_id=album_id)