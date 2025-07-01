import requests
from bs4 import BeautifulSoup, NavigableString
from django.core.management.base import BaseCommand, CommandError
from quotes_app.models import Quote, Author, Category, Source # Aangepast van Tag naar Source
from django.utils import timezone
import html
import traceback
import re
import unicodedata
from urllib.parse import urljoin

# Uw nieuwe functie voor precieze tekstextractie
def extract_text_with_linebreaks(soup_element):
    # ... (uw functie hier, onveranderd) ...
    lines = []
    current_line_parts = []
    for elem in soup_element.recursiveChildGenerator():
        if isinstance(elem, NavigableString):
            text = str(elem).strip()
            if text:
                current_line_parts.append(text)
        elif elem.name == 'br':
            lines.append(' '.join(current_line_parts))
            current_line_parts = []
        elif elem.name in ['p', 'div', 'blockquote', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if current_line_parts:
                lines.append(' '.join(current_line_parts))
                current_line_parts = []
            lines.append('\n')
    if current_line_parts:
        lines.append(' '.join(current_line_parts))
    final_text_raw = '\n'.join(lines)
    final_text_cleaned_newlines = re.sub(r'\n{2,}', '\n\n', final_text_raw).strip()
    return final_text_cleaned_newlines

# Uw clean_text functie
def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('‘', "'").replace('’', "'")
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('…', '...')
    text = text.replace('\u200b', '')
    text = text.replace('\u00A0', ' ')
    cleaned_chars = []
    for char in text:
        category = unicodedata.category(char)
        if char in ['\n', '\t', '\r', ' '] or category not in ('Cc', 'Cf', 'Cn', 'Co', 'Cs'):
            cleaned_chars.append(char)
    final_text = ''.join(cleaned_chars)
    return final_text.strip()

class Command(BaseCommand):
    help = 'Scrapes all pages from the "Love & Dreams" section with final formatting.'

    def process_quote_block(self, block_elements, category_name):
        block_content_html = ''.join(str(e) for e in block_elements if e is not None)
        soup = BeautifulSoup(block_content_html, 'lxml')
        author_tag = soup.find('span', class_='author')
        source_tag = soup.find('span', class_='source')
        author_name = clean_text(author_tag.get_text()) if author_tag else None
        source_name = clean_text(source_tag.get_text()) if source_tag else None
        if author_tag: author_tag.decompose()
        if source_tag: source_tag.decompose()
        quote_text = extract_text_with_linebreaks(soup)
        quote_text = re.sub(r'\(contributed by .*?\)', '', quote_text, flags=re.IGNORECASE).strip()
        if quote_text:
            try:
                source_obj, _ = Source.objects.get_or_create(name=source_name) if source_name else (None, False)
                final_author_obj, _ = Author.objects.get_or_create(name=author_name) if author_name else (None, False)
                main_category_obj, _ = Category.objects.get_or_create(name=category_name)
                quote_obj, created = Quote.objects.get_or_create(text=quote_text, defaults={'author': final_author_obj, 'source': source_obj})
                if created: self.stdout.write(self.style.SUCCESS(f'  + Added: "{quote_text[:45]}..." by {author_name if author_name else "Unknown Author"} (Source: {source_name if source_name else "None"})'))
                else: self.stdout.write(self.style.WARNING(f'  ! Quote already exists: "{quote_text[:45]}..."'))
                if not quote_obj.categories.filter(id=main_category_obj.id).exists():
                    quote_obj.categories.add(main_category_obj)
            except Exception as e:
                traceback.print_exc()
                self.stdout.write(self.style.ERROR(f"  ! DB Error for quote '{quote_text[:45]}...': {e}"))
        else:
            self.stdout.write(self.style.WARNING('  ! Skipped empty quote block.'))

    def get_page_soup(self, session, url):
        # ... ongewijzigd ...
        pass
    def find_next_page_link(self, soup, current_url):
        # ... ongewijzigd ...
        pass
        
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Starting web scraping...'))
        start_url = 'https://generationterrorists.com/cgi-bin/quotes.cgi?start=0&section=Love+and+Dreams&per_page=1500'
        
        with requests.Session() as session:
            try:
                response = session.get(start_url, headers={'User-Agent': 'Mozilla/5.0'})
                response.raise_for_status()
                
                # --- DE FIX VOOR SPECIALE TEKENS ---
                response.encoding = response.apparent_encoding
                # --- EINDE FIX ---
                
                soup = BeautifulSoup(response.text, 'lxml') # Gebruik lxml
                
                # Uw logica voor het vinden van de content
                main_table = soup.find('table', width='700')
                if not main_table:
                    raise CommandError("Could not find main content table with width='700'.")
                
                all_tds = main_table.find_all('td')
                if len(all_tds) < 2:
                    raise CommandError("Main content table does not have enough <td> elements.")
                main_content_td = all_tds[1]
                
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