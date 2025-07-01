import requests
from bs4 import BeautifulSoup, NavigableString
from django.core.management.base import BaseCommand
from quotes_app.models import Quote, Author, Category, Source
from urllib.parse import urljoin
import unicodedata
import re

# Deze functie is nu simpeler, de hoofdlogica zit in process_quote_block
def clean_text(text):
    if not isinstance(text, str): return ""
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    text = text.replace('…', '...')
    return text.strip()

class Command(BaseCommand):
    help = 'Scrapes all pages from the "Love & Dreams" section with final formatting.'

    # --- DEFINITIEVE process_quote_block FUNCTIE ---
    def process_quote_block(self, block_elements, category_name):
        block_content_html = ''.join(str(e) for e in block_elements if e is not None)
        soup = BeautifulSoup(block_content_html, 'lxml')

        author_tag = soup.find('span', class_='author')
        source_tag = soup.find('span', class_='source')

        author_name = clean_text(author_tag.get_text()) if author_tag else None
        
        # Verwijder de tags om de pure quote over te houden
        if author_tag: author_tag.decompose()
        if source_tag: source_tag.decompose()
        
        # Bouw de tekst handmatig op om <br> tags te converteren naar newlines
        text_parts = []
        for element in soup.stripped_strings:
             text_parts.append(element)
        
        # Gebruik join om de regels te combineren. Dit behoudt de lege regels.
        quote_text = '\n'.join(text_parts)
        
        # Verwijder de '(contributed by...)' tekst
        quote_text = re.sub(r'\(contributed by .*?\)', '', quote_text, flags=re.IGNORECASE)
        quote_text = clean_text(quote_text)


        if quote_text:
            try:
                source_obj, _ = Source.objects.get_or_create(name=category_name)
                final_author_name = author_name if author_name else source_obj.author_name
                author_obj, _ = Author.objects.get_or_create(name=final_author_name) if final_author_name else (None, False)
                main_category_obj, _ = Category.objects.get_or_create(name="Quotes")
                
                quote_obj, created = Quote.objects.get_or_create(
                    text=quote_text,
                    defaults={'author': author_obj, 'source': source_obj}
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  + Added: "{quote_text[:45]}..."'))
                else:
                     self.stdout.write(self.style.WARNING(f'  ! Quote already exists: "{quote_text[:45]}..."'))

                if not quote_obj.categories.filter(id=main_category_obj.id).exists():
                    quote_obj.categories.add(main_category_obj)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ! DB Error: {e}"))

    # ... de rest van de functies blijven hetzelfde ...
    def get_page_soup(self, session, url):
        try:
            response = session.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return BeautifulSoup(response.text, 'lxml')
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"  ! Could not fetch {url}: {e}"))
            return None

    def find_next_page_link(self, soup, current_url):
        next_link = soup.find('a', string=re.compile(r'^\s*next\s*$', re.IGNORECASE))
        if next_link and next_link.get('href'):
            return urljoin(current_url, next_link['href'])
        return None

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Starting FINAL Scrape of "Love and Dreams" ---'))
        start_url = 'https://generationterrorists.com/cgi-bin/quotes.cgi?start=0&section=Love+and+Dreams&per_page=1500'
        
        try:
            response = requests.get(start_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'lxml')

            main_content_td = soup.find('h1').find_parent('td')
            category_name = "Love and Dreams"
            
            start_parsing_element = main_content_td.find('hr', {'size': '1'})
            if not start_parsing_element:
                raise CommandError("Could not find start HR tag.")

            current_element = start_parsing_element.next_sibling
            quote_block_elements = []
            
            while current_element:
                if hasattr(current_element, 'get') and current_element.get('id') == 'pagination':
                    break 
                if hasattr(current_element, 'name') and current_element.name == 'hr' and current_element.get('width') == '50%':
                    if quote_block_elements:
                        self.process_quote_block(quote_block_elements, category_name)
                    quote_block_elements = []
                else:
                    quote_block_elements.append(current_element)
                
                current_element = current_element.next_sibling

            if quote_block_elements:
                self.process_quote_block(quote_block_elements, category_name)

            self.stdout.write(self.style.SUCCESS('\nWeb scraping finished.'))

        except Exception as e:
            traceback.print_exc()
            raise CommandError(f'An unexpected error occurred during scraping: {e}')