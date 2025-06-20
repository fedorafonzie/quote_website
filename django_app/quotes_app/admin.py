# QUOTE_WEBSITE/django_app/quotes_app/admin.py

from django.contrib import admin
from .models import Author, Category, Tag, Quote # Importeer je modellen

# Registreer je modellen hier
admin.site.register(Author)
admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(Quote)