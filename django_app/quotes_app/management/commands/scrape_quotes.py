import requests
from bs4 import BeautifulSoup, NavigableString
from django.core.management.base import BaseCommand
from quotes_app.models import Quote, Author, Category, Source
from urllib.parse import urljoin, urlparse, parse_qs
import unicodedata
import re
import traceback

def clean_text_for_db(text):
    if not isinstance(text, str): return ""
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    text = text.replace('…', '...').replace('\u200b', '').replace('\u00A0', ' ')
    cleaned_chars = [c for c in text if c in ['\n', '\t', '\r', ' '] or unicodedata.category(c) not in ('Cc', 'Cf', 'Cn', 'Co', 'Cs')]
    filtered_text = ''.join(cleaned_chars)
    lines = filtered_text.split('\n')
    stripped_lines = [line.strip() for line in lines]
    return '\n'.join(stripped_lines).strip()

class Command(BaseCommand):
    help = 'Scrapes all subcategories of the main "Quotes" section.'

    def process_quote_block(self, block_elements, subcategory_name):
        block_content_html = ''.join(str(e) for e in block_elements if e is not None)
        soup = BeautifulSoup(block_content_html, 'lxml')

        author_tag = soup.find('span', class_='author')
        source_tag = soup.find('span', class_='source')
        author_name = clean_text_for_db(author_tag.get_text()) if author_tag else None
        
        if author_tag: author_tag.decompose()
        if source_tag: source_tag.decompose()
        
        quote_text = clean_text_for_db(soup.get_text(separator='\n', strip=True))
        quote_text = re.sub(r'\(contributed by .*?\)', '', quote_text, flags=re.IGNORECASE).strip()

        if quote_text:
            try:
                author_obj, _ = Author.objects.get_or_create(name=author_name) if author_name else (None, False)
                main_category_obj, _ = Category.objects.get_or_create(name="Quotes")
                source_obj, _ = Source.objects.get_or_create(name=subcategory_name)
                
                quote_obj, created = Quote.objects.get_or_create(
                    text=quote_text,
                    defaults={'author': author_obj, 'source': source_obj}
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  + Added: "{quote_text[:45]}..."'))
                
                if not quote_obj.categories.filter(id=main_category_obj.id).exists():
                    quote_obj.categories.add(main_category_obj)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ! DB Error for quote '{quote_text[:20]}...': {e}"))

    def get_page_soup(self, session, url):
        try:
            response = session.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return BeautifulSoup(response.text, 'lxml')
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"  ! Could not fetch {url}: {e}"))
            return None

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Starting full scrape of "Quotes" section ---'))
        
        index_url = 'https://generationterrorists.com/index_quotes.shtml'
        base_url = 'https://generationterrorists.com'
        
        with requests.Session() as session:
            # Stap 1: Haal de indexpagina op
            index_soup = self.get_page_soup(session, index_url)
            if not index_soup:
                raise CommandError("Could not fetch the main quotes index page.")

            # Stap 2: Verzamel, filter en vorm de URLs om
            urls_to_scrape = []
            header_tag = index_soup.find('b', string=re.compile(r'^\s*QUOTES\s*$', re.IGNORECASE))
            content_td = header_tag.find_parent('td')
            
            for link in content_td.find_all('a', href=True):
                href = link.get('href')
                # FILTER: Alleen links die naar het cgi-script gaan
                if 'cgi-bin/quotes.cgi' in href:
                    # Vorm de URL om naar de "alles-in-één" versie
                    section_query = href.split('section=')[-1]
                    all_in_one_url = f"{base_url}/cgi-bin/quotes.cgi?start=0&section={section_query}&per_page=1500"
                    urls_to_scrape.append({'name': link.get_text(strip=True), 'url': all_in_one_url})

            self.stdout.write(self.style.SUCCESS(f"Found {len(urls_to_scrape)} subcategories to scrape."))
            
            # Stap 3: Loop door de verzamelde URLs en pas de scrape-logica toe
            for item in urls_to_scrape:
                url = item['url']
                subcategory_name = item['name']
                self.stdout.write(f"\n--- Processing Subcategory: {subcategory_name} ---")
                
                page_soup = self.get_page_soup(session, url)
                if not page_soup:
                    continue

                main_content_td = page_soup.find('h1').find_parent('td')
                if not main_content_td:
                    self.stdout.write(self.style.WARNING(f"Could not find content for {subcategory_name}. Skipping."))
                    continue

                start_parsing_element = main_content_td.find('hr', {'size': '1'})
                if not start_parsing_element:
                    self.stdout.write(self.style.WARNING(f"Could not find start HR tag for {subcategory_name}. Skipping."))
                    continue

                current_element = start_parsing_element.next_sibling
                quote_block_elements = []
                
                while current_element:
                    if hasattr(current_element, 'get') and current_element.get('id') == 'pagination':
                        break
                    if hasattr(current_element, 'name') and current_element.name == 'hr' and current_element.get('width') == '50%':
                        if quote_block_elements:
                            self.process_quote_block(quote_block_elements, subcategory_name)
                        quote_block_elements = []
                    else:
                        quote_block_elements.append(current_element)
                    current_element = current_element.next_sibling
                
                if quote_block_elements:
                    self.process_quote_block(quote_block_elements, subcategory_name)
        
        self.stdout.write(self.style.SUCCESS('\n--- Full "Quotes" section scrape finished. ---'))