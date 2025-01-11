from django.shortcuts import get_object_or_404, redirect

from django.contrib import messages

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from django.views.decorators.csrf import csrf_exempt

from django.http import HttpResponse, JsonResponse

from gallery.models import *
from gallery.forms import *

from .utils import *

import json


def download_image(request, image_id):
    image = get_object_or_404(Image, id=image_id)
    # Implement your logic for downloading the image
    # For example, serve the image file as a download
    response = HttpResponse(image.image_file, content_type='application/force-download')
    response['Content-Disposition'] = f'attachment; filename="{image.image_file.name}"'
    return response

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
            messages.error(request, 'There was an error with your comment. Please try again.')
    return redirect('image_detail', image_id=image.id)

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

@login_required
def favorite_image(request, image_id):
    image = get_object_or_404(Image, id=image_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, image=image)
    if created:
        add_to_favorites(request.user, image)
    else:
        remove_from_favorites(request.user, image)
    return redirect('image_detail', image_id=image.id)

@login_required
def add_to_album(request, image_id):
    image = get_object_or_404(Image, id=image_id)
    if request.method == 'POST':
        album_id = request.POST.get('album_id')
        if album_id:
            album = Album.objects.get(id=album_id, user=request.user)
            if album.name == "Favorites":
                print("Adding to favorites")
                add_to_favorites(request.user, image)
            else:
                add_image_to_album(request.user, image, album_id)
            return redirect('image_detail', image_id=image.id)
    return redirect('image_detail', image_id=image.id)

def add_image_to_album(user, image, album_id):
    """Adds an image to the specified album."""
    album = Album.objects.get(id=album_id, user=user)
    album.images.add(image)

@csrf_exempt
def save_image_order(request, album_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        order = data.get('order', [])
        album = Album.objects.get(id=album_id)
        for index, image_id in enumerate(order):
            album_image = AlbumImage.objects.get(album=album, image_id=image_id)
            album_image.order = index
            album_image.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'fail'}, status=400)

@staff_required
def admin_approve_image(request, image_id):
    image = get_object_or_404(Image, id=image_id)
    image.moderation_status = ModerationStatus.APPROVED
    image.save()
    return redirect('admin_pending_images')

@staff_required
def admin_resolve_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    report.status = 'RESOLVED'
    report.save()
    return redirect('admin_reported_images')

@staff_required
def admin_resolve_comment_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    report.status = 'RESOLVED'
    report.save()
    return redirect('admin_reported_comments')

@require_POST
@csrf_exempt
def set_cover_image(request):
    data = json.loads(request.body)
    album_id = data.get('album_id')
    image_id = data.get('image_id')

    try:
        album = Album.objects.get(id=album_id)
        if image_id:
            image = Image.objects.get(id=image_id)
            album.cover_image = image
        else:
            album.cover_image = None
        album.save()
        return JsonResponse({'success': True})
    except Album.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Album not found'})
    except Image.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Image not found'})

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

def like_image(request, image_id):
    image = get_object_or_404(Image, id=image_id)
    like, created = Like.objects.get_or_create(user=request.user, image=image)
    if not created:
        # If the like already exists, remove it (toggle like)
        like.delete()
    return redirect('image_detail', image_id=image.id)

def like_image(request, image_id):
    if request.method == 'POST':
        image = get_object_or_404(Image, id=image_id)
        like, created = Like.objects.get_or_create(user=request.user, image=image)
        if not created:
            # If the like already exists, remove it (toggle like)
            like.delete()
            return JsonResponse({'success': True, 'liked': False})
        return JsonResponse({'success': True, 'liked': True})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def favorite_image(request, image_id):
    if request.method == 'POST':
        image = get_object_or_404(Image, id=image_id)
        favorite, created = Favorite.objects.get_or_create(user=request.user, image=image)
        if created:
            add_to_favorites(request.user, image)
            return JsonResponse({'success': True, 'favorited': True})
        else:
            remove_from_favorites(request.user, image)
            return JsonResponse({'success': True, 'favorited': False})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

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

@login_required
def add_to_album(request, image_id):
    image = get_object_or_404(Image, id=image_id)
    if request.method == 'POST':
        album_id = request.POST.get('album_id')
        if album_id:
            album = Album.objects.get(id=album_id, user=request.user)
            if album.name == "Favorites":
                print("Adding to favorites")
                add_to_favorites(request.user, image)
            else:
                add_image_to_album(request.user, image, album_id)
            return redirect('image_detail', image_id=image.id)
    return redirect('image_detail', image_id=image.id)

@csrf_exempt
def save_image_order(request, album_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        order = data.get('order', [])
        album = Album.objects.get(id=album_id)
        for index, image_id in enumerate(order):
            album_image = AlbumImage.objects.get(album=album, image_id=image_id)
            album_image.order = index
            album_image.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'fail'}, status=400)

@staff_required
def admin_approve_image(request, image_id):
    image = get_object_or_404(Image, id=image_id)
    image.moderation_status = ModerationStatus.APPROVED
    image.save()
    return redirect('admin_pending_images')

@staff_required
def admin_resolve_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    report.status = 'RESOLVED'
    report.save()
    return redirect('admin_reported_images')

@staff_required
def admin_resolve_comment_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    report.status = 'RESOLVED'
    report.save()
    return redirect('admin_reported_comments')

@require_POST
@csrf_exempt
def set_cover_image(request):
    data = json.loads(request.body)
    album_id = data.get('album_id')
    image_id = data.get('image_id')

    try:
        album = Album.objects.get(id=album_id)
        if image_id:
            image = Image.objects.get(id=image_id)
            album.cover_image = image
        else:
            album.cover_image = None
        album.save()
        return JsonResponse({'success': True})
    except Album.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Album not found'})
    except Image.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Image not found'})