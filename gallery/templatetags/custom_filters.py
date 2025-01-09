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

@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})