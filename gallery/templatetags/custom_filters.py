from django import template
from django.urls import reverse

register = template.Library()

@register.filter
def startswith(value, arg):
    return value.startswith(arg)

@register.filter
def is_active(request_path, url_name):
    try:
        return request_path == reverse(url_name)
    except:
        return False