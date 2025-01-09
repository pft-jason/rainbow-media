from django import forms 
from .models import Image, Category, Tag, UserProfile, Comment, Report, Album
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
import json

class ImageUploadForm(forms.ModelForm):
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter tags separated by commas.'}),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        widget=forms.Select,
        required=False,
        help_text="Select a category."
    )
    album = forms.ModelChoiceField(queryset=Album.objects.none(), required=False, label="Select Album")
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Enter a description."
    )

    class Meta:
        model = Image
        fields = ['image_file', 'album', 'title', 'description', 'category', 'alt_text', 'privacy']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['album'].queryset = Album.objects.filter(user=user)

    def save(self, user=None, commit=True):
        instance = super(ImageUploadForm, self).save(commit=False)
        if user:
            instance.user = user
        tags = self.cleaned_data['tags']
        if commit:
            instance.save() 
            for tag_name in tags.split(','):
                tag_name = tag_name.strip()
                if tag_name:
                    tag, created = Tag.objects.get_or_create(name=tag_name)
                    instance.tags.add(tag)
            instance.save()
        return instance

class ImageUpdateForm(forms.ModelForm):
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter tags separated by commas.'}),
    )
    tags_to_remove = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        widget=forms.Select,
        required=False,
        help_text="Select a category."
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Enter a description."
    )

    class Meta:
        model = Image
        fields = ['title', 'description', 'image_file', 'category', 'alt_text', 'privacy']

    def save(self, commit=True):
        instance = super(ImageUpdateForm, self).save(commit=False)
        tags = self.cleaned_data['tags']
        tags_to_remove = self.cleaned_data['tags_to_remove']
        if commit:
            instance.save()  # Save the instance first to ensure it has a primary key
            existing_tags = instance.tags.all()
            all_tags = tags.split(',') + [tag.name for tag in existing_tags]
            instance.tags.clear()
            for tag_name in all_tags:
                tag_name = tag_name.strip()
                if tag_name and tag_name not in tags_to_remove.split(','):
                    tag, created = Tag.objects.get_or_create(name=tag_name)
                    instance.tags.add(tag)
            instance.save()  # Ensure the many-to-many relationship is saved
        return instance

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

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['report_type', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }