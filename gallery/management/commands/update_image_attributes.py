from django.core.management.base import BaseCommand
from gallery.models import Image
from PIL import Image as PILImage

class Command(BaseCommand):
    help = 'Update image attributes for existing records'

    def handle(self, *args, **kwargs):
        images = Image.objects.all()
        for image in images:
            with PILImage.open(image.image_file.path) as img:
                image.width, image.height = img.size
                image.format = img.format
            image.size = image.image_file.size
            image.save()
        self.stdout.write(self.style.SUCCESS('Successfully updated image attributes for existing records'))