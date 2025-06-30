# django_app/quotes_app/admin.py

from django.contrib import admin
# Importeer ALLEEN de modellen die daadwerkelijk bestaan in models.py
from .models import Category, Author, Source, Quote

# Registreer de modellen om ze zichtbaar te maken in de admin-interface
admin.site.register(Category)
admin.site.register(Author)
admin.site.register(Source)
admin.site.register(Quote)