from django.core.management.base import BaseCommand
from property_app.models import Property  # আপনার আসল অ্যাপ ও মডেলের নাম দিন

class Command(BaseCommand):
    help = 'Fixes external image URLs stored in the database'

    def handle(self, *args, **kwargs):
        count = 0
        for prop in Property.objects.all():
            image_path = str(prop.image)
            
            # যদি আনস্প্ল্যাশ বা এক্সটার্নাল লিংক থাকে এবং স্লাশ মিসিং থাকে
            if 'images.unsplash.com' in image_path:
                # ভুলভাবে সেভ হওয়া স্লাশ ঠিক করা (যেমন https:/ থেকে https:// করা)
                fixed_url = image_path.replace('https:/', 'https://').replace('http:/', 'http://')
                prop.image = fixed_url
                prop.save()
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} property images.'))