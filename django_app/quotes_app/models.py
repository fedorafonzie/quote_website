# quotes_app/models.py

from django.db import models
from django.utils import timezone

class Author(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Naam")
    bio = models.TextField(blank=True, null=True, verbose_name="Biografie")
    birth_year = models.IntegerField(blank=True, null=True, verbose_name="Geboortejaar")
    death_year = models.IntegerField(blank=True, null=True, verbose_name="Sterfjaar")

    class Meta:
        verbose_name = "Auteur"
        verbose_name_plural = "Auteurs"
        ordering = ['name'] # Sorteer auteurs alfabetisch

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Naam")

    class Meta:
        verbose_name = "Categorie"
        verbose_name_plural = "Categorieën"
        ordering = ['name']

    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Naam")

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ['name']

    def __str__(self):
        return self.name

class Quote(models.Model):
    text = models.TextField(verbose_name="Tekst van de quote")
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='quotes', verbose_name="Auteur")
    source = models.CharField(max_length=255, blank=True, null=True, verbose_name="Bron")
    year = models.IntegerField(blank=True, null=True, verbose_name="Jaar")
    url = models.URLField(max_length=2000, blank=True, null=True, verbose_name="URL Bron") # Aangepast max_length voor lange URLs
    added_date = models.DateTimeField(default=timezone.now, verbose_name="Toevoegingsdatum")

    # Many-to-Many relaties
    categories = models.ManyToManyField(Category, related_name='quotes', blank=True, verbose_name="Categorieën")
    tags = models.ManyToManyField(Tag, related_name='quotes', blank=True, verbose_name="Tags")

    class Meta:
        verbose_name = "Quote"
        verbose_name_plural = "Quotes"
        ordering = ['-added_date'] # Sorteer quotes op meest recent toegevoegd

    def __str__(self):
        # Verkorte weergave van de quote voor de admin-interface
        return f'"{self.text[:50]}..." by {self.author.name}' if len(self.text) > 50 else f'"{self.text}" by {self.author.name}'