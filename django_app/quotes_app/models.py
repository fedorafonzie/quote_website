# django_app/quotes_app/models.py
from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class Author(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

# --- HIER IS HET BELANGRIJKE NIEUWE MODEL ---
class Source(models.Model):
    name = models.CharField(max_length=255, unique=True)
    author_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

class Quote(models.Model):
    text = models.TextField()
    author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True, blank=True)
    
    # --- EN HET AANGEPASTE VELD ---
    source = models.ForeignKey(Source, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotes')
    
    categories = models.ManyToManyField(Category, related_name='quotes')
    added_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'"{self.text[:50]}..."'