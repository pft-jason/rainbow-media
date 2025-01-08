from django.contrib.auth.models import User
from django.db import models, transaction
from django.utils.timezone import now
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.http import Http404
from akismet import Akismet
from django.db.models import Q
from django.core.paginator import Paginator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json




class CustomImageManager(models.Manager):
    def get_filtered_images(self, user):
        """Filters images based on privacy settings."""
        
        # Start by getting all images with related follower information
        images = self.all().prefetch_related(
            models.Prefetch('user__followers', queryset=Follow.objects.all())
        )
        
        # If user is staff, show all images
        if user.is_staff:
            return images

        # Exclude images reported by the user
        if user.is_authenticated:
            reported_images = Report.objects.filter(reported_by=user).values_list('image_id', flat=True)
            images = images.exclude(id__in=reported_images)

        # If user is authenticated but not staff, filter based on privacy settings
        if user.is_authenticated:
            return images.filter(
                Q(privacy="public", moderation_status=ModerationStatus.APPROVED) |
                Q(privacy="users", moderation_status=ModerationStatus.APPROVED) |
                Q(privacy="followers", user__followers__follower=user, moderation_status=ModerationStatus.APPROVED) |
                Q(privacy="private", user=user, moderation_status=ModerationStatus.APPROVED)
            ).distinct()
        else:
            return images.filter(privacy="public", moderation_status=ModerationStatus.APPROVED).distinct()

class CustomAlbumManager(models.Manager):
    def get_filtered_albums(self, user):
        """Filters albums based on privacy settings."""
        
        # Start by getting all albums with related follower information
        albums = self.all().prefetch_related(
            models.Prefetch('user__followers', queryset=Follow.objects.all())
        )
        
        # If user is staff, show all albums
        if user.is_staff:
            return albums

        # Exclude albums reported by the user
        if user.is_authenticated:
            reported_albums = Report.objects.filter(reported_by=user).values_list('album_id', flat=True)
            albums = albums.exclude(id__in=reported_albums)

        # If user is authenticated but not staff, filter based on privacy settings
        if user.is_authenticated:
            return albums.filter(
                Q(privacy="public", moderation_status=ModerationStatus.APPROVED) |
                Q(privacy="users", moderation_status=ModerationStatus.APPROVED) |
                Q(privacy="followers", user__followers__follower=user, moderation_status=ModerationStatus.APPROVED) |
                Q(privacy="private", user=user, moderation_status=ModerationStatus.APPROVED)
            ).distinct()
        else:
            return albums.filter(privacy="public", moderation_status=ModerationStatus.APPROVED).distinct()

# ----------------------------------------------------------------------------- 
# Helper Functions
# -----------------------------------------------------------------------------

def report_image(user, image, report_type, description=""):
    """Create a report for an image and notify moderators."""
    report = Report.objects.create(
        reported_by=user,
        image=image,
        report_type=report_type,
        description=description,
    )


def get_image_visibility(user, image):
    """Check if the user can view the image based on privacy settings."""
    if image.privacy == 'private' and image.user != user:
        raise PermissionDenied("You do not have permission to view this image.")
    elif image.privacy == 'followers' and not Follow.objects.filter(follower=user, followed=image.user).exists():
        raise PermissionDenied("You do not have permission to view this image.")
    elif image.privacy == 'users' and not user.is_authenticated:
        raise PermissionDenied("You do not have permission to view this image.")
    return True


def search_images(query, user=None):
    """Search for images based on title, description, tags, or categories."""
    return Image.objects.get_filtered_images(user).filter(
        Q(title__icontains=query) |
        Q(description__icontains=query) |
        Q(tags__name__icontains=query) |
        Q(category__name__icontains=query)
    ).distinct()


def check_spam(content):
    """Check if the given content is spam using Akismet."""
    akismet = Akismet(key=settings.AKISMET_API_KEY, blog_url=settings.SITE_URL)
    return akismet.comment_check(content)


# ----------------------------------------------------------------------------- 
# Models
# -----------------------------------------------------------------------------

class ModerationStatus(models.TextChoices):
    """Enumeration of possible moderation statuses for images and comments."""
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class SiteSettings(models.Model):
    """Global settings for site-wide features such as moderation."""
    moderation_enabled = models.BooleanField(default=True)
    comment_moderation_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f'Site Settings (Moderation: {self.moderation_enabled}, Comment Moderation: {self.comment_moderation_enabled})'


class UserSettings(models.Model):
    """User-specific settings for moderation and content preferences."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    comment_moderation_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.user.username}\'s Settings (Comment Moderation: {self.comment_moderation_enabled})'


class UserProfile(models.Model):
    """User profile storing bio, profile picture, and privacy settings."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
    social_links = models.JSONField(default=dict, blank=True)
    privacy_settings = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class UserActivity(models.Model):
    """Tracks user activities like liking images, posting comments, or following users."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_feed")
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    target_image = models.ForeignKey('Image', on_delete=models.CASCADE, null=True, blank=True)
    target_comment = models.ForeignKey('Comment', on_delete=models.CASCADE, null=True, blank=True)
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="activity_target")

    def __str__(self):
        return f"{self.user.username} performed {self.action}"


class Category(models.Model):
    """Categories to group images for easier classification."""
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Tags for images to allow for categorization and easy searching."""
    name = models.CharField(max_length=50, unique=True)
    moderation_status = models.CharField(
        max_length=10,
        choices=ModerationStatus.choices,
        default=ModerationStatus.PENDING,
    )

    def __str__(self):
        return self.name


class Image(models.Model):
    """Represents an image uploaded by a user, with features like title, description, tags, and categories."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='images')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image_file = models.ImageField(upload_to='images/')
    uploaded_at = models.DateTimeField(default=now)
    views = models.PositiveIntegerField(default=0)
    is_public = models.BooleanField(default=True)
    category = models.ForeignKey(Category, related_name='images', on_delete=models.CASCADE, blank=True, null=True)
    tags = models.ManyToManyField(Tag, related_name='images', blank=True)
    popularity_score = models.FloatField(default=0.0)
    objects = CustomImageManager()
    privacy = models.CharField(max_length=20, choices=[('public', 'Public'), ('users', 'Site Members Only'), ('followers', 'Followers Only'), ('private', 'Private')], default='public')

    moderation_status = models.CharField(max_length=10, choices=ModerationStatus.choices, default=ModerationStatus.PENDING)
    moderation_updated_at = models.DateTimeField(null=True, blank=True)
    moderated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="moderated_images", limit_choices_to={'is_staff': True})

    alt_text = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.pk:
            self.popularity_score = self.calculate_popularity_score()
        if self.moderation_status != ModerationStatus.PENDING:
            self.moderation_updated_at = now()
        super().save(*args, **kwargs)

    def calculate_popularity_score(self):
        """Calculates the popularity score based on likes and views."""
        likes_count = self.likes.count()
        return (likes_count * 2) + self.views

    def __str__(self):
        return self.title


class Comment(models.Model):
    """Represents a comment made by a user on an image."""
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    moderation_status = models.CharField(max_length=10, choices=ModerationStatus.choices, default=ModerationStatus.PENDING)
    moderation_updated_at = models.DateTimeField(null=True, blank=True)
    moderated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="moderated_comments")

    def save(self, *args, **kwargs):
        if self.moderation_status != ModerationStatus.PENDING:
            self.moderation_updated_at = now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.image.title}"


class Like(models.Model):
    """Represents a like on an image by a user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="likes")
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="liked_by")
    liked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'image')


class Dislike(models.Model):
    """Represents a dislike on an image by a user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dislikes")
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="dislikes")
    disliked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'image')


class Favorite(models.Model):
    """Represents an image that a user has marked as a favorite."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="favorited_by")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'image')

    def __str__(self):
        return f"{self.user.username} favorites {self.image.title}"


class Album(models.Model):
    """Represents an album to organize images for a user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="albums")
    name = models.CharField(max_length=100)
    images = models.ManyToManyField(Image, related_name="albums", through="AlbumImage")
    cover_image = models.ForeignKey(Image, on_delete=models.SET_NULL, null=True, blank=True, related_name='cover_for_albums')
    created_at = models.DateTimeField(auto_now_add=True)
    views = models.PositiveIntegerField(default=0)
    privacy = models.CharField(max_length=10, choices=[('public', 'Public'), ('users', 'Site Members Only'), ('followers', 'Followers Only'), ('private', 'Private')], default='public')
    moderation_status = models.CharField(max_length=10, choices=ModerationStatus.choices, default=ModerationStatus.PENDING)
    moderation_updated_at = models.DateTimeField(null=True, blank=True)
    moderated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="moderated_albums")
    objects = CustomAlbumManager()

    def __str__(self):
        return self.name

    def set_default_cover_image(self):
        if not self.cover_image and self.images.exists():
            self.cover_image = self.images.first()

    def save(self, *args, **kwargs):
        if self.pk:
            self.popularity_score = self.calculate_popularity_score()
        if self.moderation_status != ModerationStatus.PENDING:
            self.moderation_updated_at = now()
        super().save(*args, **kwargs)

    def calculate_popularity_score(self):
        """Calculates the popularity score based on likes and views."""
        likes_count = self.liked_by.count()
        return (likes_count * 2) + self.views

    @classmethod
    def get_or_create_favorites_album(cls, user):
        """Ensures the user has a 'Favorites' album."""
        album, created = cls.objects.get_or_create(user=user, name="Favorites")
        return album


class AlbumImage(models.Model):
    """Represents a relationship between an album and an image."""
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('album', 'image')
        ordering = ['order']

@receiver(post_save, sender=AlbumImage)
def set_album_cover_image(sender, instance, created, **kwargs):
    if created and not instance.album.cover_image:
        instance.album.cover_image = instance.image
        instance.album.save()


class Follow(models.Model):
    """Represents a relationship between users where one follows another."""
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following")
    followed = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followers")
    followed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'followed')


class Report(models.Model):
    """
    Represents a report made by a user against inappropriate content (images or comments).
    """
    REPORT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RESOLVED', 'Resolved'),
    ]
    REPORT_TYPES = [
        ("SPAM", "Spam"),
        ("ABUSE", "Abuse"),
        ("OTHER", "Other"),
    ]

    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports")
    image = models.ForeignKey(Image, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    report_type = models.CharField(max_length=10, choices=REPORT_TYPES)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=REPORT_STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report by {self.reported_by.username} on {'image' if self.image else 'comment'}"

class AlbumLike(models.Model):
    """Represents a like on an album by a user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="album_likes")
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name="liked_by")
    liked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'album')


class AlbumDislike(models.Model):
    """Represents a dislike on an album by a user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="album_dislikes")
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name="disliked_by")
    disliked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'album')

class AlbumFavorite(models.Model):
    """Represents an album that a user has marked as a favorite."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="album_favorites")
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name="favorited_by")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'album')

    def __str__(self):
        return f"{self.user.username} favorites {self.album.name}"

# ----------------------------------------------------------------------------- 
# Moderation Functions
# -----------------------------------------------------------------------------

def log_user_activity(user, action, target_image=None, target_comment=None, target_user=None):
    """Logs user activity for actions like liking, commenting, or following."""
    UserActivity.objects.create(
        user=user,
        action=action,
        target_image=target_image,
        target_comment=target_comment,
        target_user=target_user,
    )


def remove_from_favorites(user, image):
    """Removes an image from the user's favorites."""
    album = Album.get_or_create_favorites_album(user)
    if image.albums.exclude(id=album.id).exists():
        Favorite.objects.filter(user=user, image=image).delete()
    else:
        album.images.remove(image)
        Favorite.objects.filter(user=user, image=image).delete()


def add_to_favorites(user, image):
    """Adds an image to the user's favorites and the 'Favorites' album."""
    Favorite.objects.get_or_create(user=user, image=image)
    album = Album.get_or_create_favorites_album(user)
    album.images.add(image)


# ----------------------------------------------------------------------------- 
# Like/Dislike/Undislike Functions
# -----------------------------------------------------------------------------

def like_image(user, image):
    """Likes an image, ensuring that any previous dislike is removed."""
    Dislike.objects.filter(user=user, image=image).delete()
    Like.objects.get_or_create(user=user, image=image)


def unlike_image(user, image):
    """Removes a like from an image."""
    Like.objects.filter(user=user, image=image).delete()


def dislike_image(user, image):
    """Dislikes an image, ensuring that any previous like is removed."""
    Like.objects.filter(user=user, image=image).delete()
    Dislike.objects.get_or_create(user=user, image=image)


def undislike_image(user, image):
    """Removes a dislike from an image."""
    Dislike.objects.filter(user=user, image=image).delete()

def add_like_to_album(user, album):
    """Likes an album, ensuring that any previous dislike is removed."""
    AlbumDislike.objects.filter(user=user, album=album).delete()
    AlbumLike.objects.get_or_create(user=user, album=album)


def unlike_album(user, album):
    """Removes a like from an album."""
    AlbumLike.objects.filter(user=user, album=album).delete()


def add_dislike_to_album(user, album):
    """Dislikes an album, ensuring that any previous like is removed."""
    AlbumLike.objects.filter(user=user, album=album).delete()
    AlbumDislike.objects.get_or_create(user=user, album=album)


def undislike_album(user, album):
    """Removes a dislike from an album."""
    AlbumDislike.objects.filter(user=user, album=album).delete()


# ----------------------------------------------------------------------------- 
# Image Versioning and History
# -----------------------------------------------------------------------------

class ImageVersion(models.Model):
    """Represents an older version of an image for versioning purposes."""
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="versions")
    file = models.ImageField(upload_to="image_versions/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Version of {self.image.title} created at {self.created_at}"


class ModerationHistory(models.Model):
    """Represents a history record of moderation actions (approval or rejection)."""
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="moderation_history", null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="moderation_history", null=True, blank=True)
    moderator = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=[('approved', 'Approved'), ('rejected', 'Rejected')])
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Action {self.action} by {self.moderator.username}"


def get_image_or_404(image_id):
    """Helper function to get an image or raise 404 error."""
    try:
        return Image.objects.get(id=image_id)
    except Image.DoesNotExist:
        raise Http404("Image not found")


def get_user_or_404(user_id):
    """Helper function to get a user or raise 404 error."""
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise Http404("User not found")


def get_album_or_404(album_id):
    """Helper function to get an album or raise 404 error."""
    try:
        return Album.objects.get(id=album_id)
    except Album.DoesNotExist:
        raise Http404("Album not found")


def check_image_owner(user, image):
    """Ensure the user is the owner of the image."""
    if image.user != user:
        raise PermissionDenied("You do not have permission to modify this image.")


def validate_album_capacity(album):
    """Check if an album has reached its capacity."""
    if album.images.count() >= album.capacity:  # Assuming `capacity` field exists
        raise ValidationError("This album has reached its maximum capacity.")


def update_popularity_score(image):
    """Update the popularity score based on unique users who have added the image to their albums."""
    image.popularity_score = image.likes.count() * 2 + image.views
    image.save()


def handle_comment_moderation(comment):
    """Handle moderation status changes for comments."""
    if comment.moderation_status == ModerationStatus.APPROVED:
        comment.save()  # Can trigger other actions
    elif comment.moderation_status == ModerationStatus.REJECTED:
        comment.delete()

def add_image_to_album(user, image, album_id):
    """Adds an image to the specified album."""
    album = Album.objects.get(id=album_id, user=user)
    album.images.add(image)

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

def add_album_to_favorites(user, album):
    """Adds an album to the user's favorites."""
    AlbumFavorite.objects.get_or_create(user=user, album=album)


def remove_album_from_favorites(user, album):
    """Removes an album from the user's favorites."""
    AlbumFavorite.objects.filter(user=user, album=album).delete()