"""
Template tags e filtros customizados para o app extratos_app
"""
from django import template
from django.utils.text import slugify

register = template.Library()


@register.filter
def slugify_custom(value):
    """Converte valor para slug compatível com URLs"""
    return slugify(value) if value else ""
