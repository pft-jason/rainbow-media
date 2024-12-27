from django import forms 
from .models import Image, Category, Tag

class ImageUploadForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(queryset=Category.objects.all(), required=False)
    tags = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)
    
    class Meta:
        model = Image
        fields = ['title', 'description', 'image_file', 'categories', 'tags']