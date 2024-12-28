from django import forms 
from .models import Image, Category, Tag, UserProfile
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
import json

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
    twitter = forms.URLField(required=False, label='Twitter')
    linkedin = forms.URLField(required=False, label='LinkedIn')
    facebook = forms.URLField(required=False, label='Facebook')
    instagram = forms.URLField(required=False, label='Instagram')

    class Meta:
        model = UserProfile
        fields = ['bio', 'profile_picture', 'twitter', 'linkedin', 'facebook', 'instagram']

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.social_links:
            social_links = self.instance.social_links
            self.fields['twitter'].initial = social_links.get('Twitter', '')
            self.fields['linkedin'].initial = social_links.get('LinkedIn', '')
            self.fields['facebook'].initial = social_links.get('Facebook', '')
            self.fields['instagram'].initial = social_links.get('Instagram', '')

    def save(self, commit=True):
        instance = super(UserProfileForm, self).save(commit=False)
        instance.social_links = {
            'Twitter': self.cleaned_data.get('twitter', ''),
            'LinkedIn': self.cleaned_data.get('linkedin', ''),
            'Facebook': self.cleaned_data.get('facebook', ''),
            'Instagram': self.cleaned_data.get('instagram', ''),
        }
        if commit:
            instance.save()
        return instance