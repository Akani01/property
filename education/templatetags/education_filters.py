from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Return the value for a given key from a dictionary."""
    if not isinstance(dictionary, dict):
        return ''
    return dictionary.get(key, '')