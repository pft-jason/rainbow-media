from django import forms 
from .models import Image, Category, Tag, UserProfile
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class ImageUploadForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(queryset=Category.objects.all(), required=False)
    tags = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)
    
    class Meta:
        model = Image
        fields = ['title', 'description', 'image_file', 'categories', 'tags']

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['bio', 'profile_picture', 'social_links']