# views.py
from django.shortcuts import render, redirect, get_object_or_404
from .forms import ReportForm, ImageUploadForm, UserRegistrationForm, UserProfileForm, ImageUpdateForm, CommentForm
from django.contrib.auth.decorators import login_required
from .models import Tag, Report, AlbumImage, add_image_to_album, Album, Follow, Image, get_image_visibility, UserProfile, search_images, Like, Dislike, Favorite, Comment, ModerationStatus, remove_from_favorites, add_to_favorites, add_like_to_album, add_dislike_to_album, add_album_to_favorites
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth import login
from django.contrib.auth.models import User
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_POST
from django.db.models import Count



def staff_required(view_func):
    decorated_view_func = user_passes_test(lambda u: u.is_staff)(view_func)
    return decorated_view_func

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

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from .models import Image
from .forms import ImageUpdateForm

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
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    user_images = Image.objects.filter(user=request.user) [:8]  # Display the latest 8 images
    user_albums = Album.objects.filter(user=request.user) 
    return render(request, 'profile.html', {'user_profile': user_profile, 'user_images': user_images, 'user_albums': user_albums, 'is_following': False})

@login_required
def user_profile(request, username):
    user_profile = get_object_or_404(UserProfile, user__username=username)
    user_images = Image.objects.filter(user=user_profile.user)
    user_images = Image.objects.get_filtered_images(user=request.user).filter(id__in=user_images).order_by('-uploaded_at')[:8]
    user_albums = Album.objects.filter(user=user_profile.user) 
    is_following = Follow.objects.filter(follower=request.user, followed=user_profile.user).exists()
    
    return render(request, 'user_profile.html', {
        'user_profile': user_profile,
        'user_images': user_images,
        'user_albums': user_albums,
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

    filter_type = request.GET.get('filter', 'newest')
    if filter_type == 'newest':
        images = images.order_by('-uploaded_at')
    elif filter_type == 'oldest':
        images = images.order_by('uploaded_at')
    elif filter_type == 'most_liked':
        images = images.annotate(like_count=Count('liked_by')).order_by('-like_count')
    elif filter_type == 'most_favorited':
        images = images.annotate(favorite_count=Count('favorited_by')).order_by('-favorite_count')

    # Pagination: Show 20 images per page
    paginator = Paginator(images, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'gallery.html', {'page_obj': page_obj})

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
    
@login_required
def create_album(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        album = Album.objects.create(user=request.user, name=name)
        return redirect('profile')
    return render(request, 'create_album.html')

@login_required
def image_detail(request, image_id):
    image = get_object_or_404(Image, id=image_id)

    if not request.user.is_staff:
        if not get_image_visibility(request.user, image):
            raise PermissionDenied("You do not have permission to view this image.")
    
    comment_form = CommentForm()
    user_albums = Album.objects.filter(user=request.user)
    # TODO: set up so user can select whether comments on their images are moderated or not.
    # comments = image.comments.filter(moderation_status=ModerationStatus.APPROVED)
    comments = image.comments.all()
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

@staff_required
def admin_resolve_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    report.status = 'RESOLVED'
    report.save()
    return redirect('admin_reported_images')

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

def tags_view(request):
    tags = Tag.objects.all()
    return render(request, 'gallery/tags.html', {'tags': tags})

def tagged_images_view(request, tag_id):
    tag = Tag.objects.get(id=tag_id)
    images = Image.objects.filter(tags=tag)
    return render(request, 'gallery/tags_gallery.html', {'tag': tag, 'images': images})

def like_album_view(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    add_like_to_album(request.user, album)
    return redirect('album_detail', album_id=album_id)

def dislike_album_view(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    add_dislike_to_album(request.user, album)
    return redirect('album_detail', album_id=album_id)

def favorite_album_view(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    add_album_to_favorites(request.user, album)
    return redirect('album_detail', album_id=album_id)

def report_album_view(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    # Implement report logic here
    return redirect('album_detail', album_id=album_id)