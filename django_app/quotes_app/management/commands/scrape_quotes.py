import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from quotes_app.models import Quote, Author, Category, Source
from django.utils import timezone
import html
import traceback
import re
import unicodedata

# Helper functie om tekst op te schonen van onzichtbare/ongewenste tekens en newlines
def clean_text_for_db(text):
    if not isinstance(text, str):
        return ""
    
    # 1. Unicode normalisatie: zet compatibiliteitskarakters om naar hun "standaard" vorm.
    text = unicodedata.normalize('NFKC', text)
    
    # 2. Expliciete vervanging van typografische aanhalingstekens en ellipsis
    # Dit is cruciaal om rendering issues in verschillende omgevingen te voorkomen.
    text = text.replace('‘', "'").replace('’', "'") # Linker en rechter enkel aanhalingsteken/apostrof
    text = text.replace('“', '"').replace('”', '"') # Linker en rechter dubbel aanhalingsteken
    text = text.replace('…', '...') # Unicode ellipsis vervangen door drie punten
    
    # 3. Verwijder Zero Width Space (ZWS) en converteer Non-breaking space
    text = text.replace('\u200b', '') # Zero Width Space (U+200B)
    text = text.replace('\u00A0', ' ') # Non-breaking space (U+00A0) vervangen door gewone spatie

    # 4. Filter overgebleven niet-afdrukbare of ongewenste controle/formaat karakters
    # Behoud alleen afdrukbare tekens plus standaard witruimte (newline, tab, spatie, carriage return).
    cleaned_chars = []
    for char in text:
        category = unicodedata.category(char)
        # Houd spatie, newline, tab, carriage return, OF tekens die GEEN Control (Cc), Format (Cf),
        # Unassigned (Cn), Private Use (Co), Surrogate (Cs) zijn.
        if char in ['\n', '\t', '\r', ' '] or category not in ('Cc', 'Cf', 'Cn', 'Co', 'Cs'):
            cleaned_chars.append(char)
            
    # Combineer de gefilterde karakters tot een string
    filtered_text = ''.join(cleaned_chars)
    
    # 5. Consolidatie van newlines en opruimen van lege regels
    # Split de tekst op alle newlines, strip elke individuele regel,
    # filter lege regels eruit, en voeg ze dan weer samen met één newline.
    lines = filtered_text.split('\n')
    stripped_lines = [line.strip() for line in lines] # Strip en filter lege lijnen
    
    # Voeg de opgeschoonde lijnen weer samen met een enkele newline
    final_text = '\n'.join(stripped_lines)

    return final_text.strip() # Final strip voor witruimte aan begin/einde van de hele quote

class Command(BaseCommand):
    help = 'Scrapes quotes from generationterrorists.com and populates the database.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting web scraping...'))

        base_site_url = 'http://www.generationterrorists.com/' # Let op: http, niet https
        # Voor nu richten we ons op één specifieke sectie/pagina
        # Later kunnen we dit uitbreiden om alle secties en paginatie af te handelen.
        initial_section_path = 'cgi-bin/quotes.cgi?section=Love and Dreams'
        start_url = f'{base_site_url}{initial_section_path}'

        try:
            self.stdout.write(f'Fetching URL: {start_url}')
            response = requests.get(start_url)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')

            # De quotes bevinden zich in de tweede <td> van de hoofdtabel (width="700")
            # De eerste <td> is voor de navigatie.
            main_content_td = soup.find('table', width='700').find_all('td')[1]

            category_name = initial_section_path.split('section=')[-1].replace('+', ' ')
            
            scraped_quotes_count = 0
            
            start_parsing_element = None
            h1_tag = main_content_td.find('h1')
            if h1_tag:
                hr_after_h1 = h1_tag.find_next_sibling('hr', size="1")
                if hr_after_h1:
                    current_element = hr_after_h1.next_sibling
                    while current_element and (current_element.name == 'br' or (isinstance(current_element, str) and not current_element.strip())):
                         current_element = current_element.next_sibling
                    start_parsing_element = current_element

            if not start_parsing_element:
                raise CommandError("Could not find the starting point for quotes parsing.")


            current_element = start_parsing_element
            quote_block_elements = []
            
            while current_element:
                if current_element.name == 'div' and current_element.get('id') == 'pagination':
                    break 

                if current_element.name == 'hr' and current_element.get('width') == '50%':
                    if quote_block_elements:
                        self.process_quote_block(quote_block_elements, category_name, base_site_url)
                        scraped_quotes_count += 1
                        
                    quote_block_elements = []
                else:
                    quote_block_elements.append(current_element)
                
                current_element = current_element.next_sibling

            if quote_block_elements:
                 self.process_quote_block(quote_block_elements, category_name, base_site_url)
                 scraped_quotes_count += 1


            self.stdout.write(self.style.SUCCESS(f'Web scraping finished. Total new quotes added: {scraped_quotes_count}.'))

        except requests.exceptions.RequestException as e:
            raise CommandError(f'Error fetching URL {start_url}: {e}')
        except Exception as e:
            traceback.print_exc()
            raise CommandError(f'An unexpected error occurred during scraping: {e}')

    # Nieuwe helper functie om een geïsoleerd quote blok te verwerken
    def process_quote_block(self, block_elements, category_name, base_site_url):
        block_content_html = ''.join(str(e) for e in block_elements if e is not None)
        block_soup = BeautifulSoup(block_content_html, 'html.parser')

        full_quote_text = ''
        p_tag_in_block = block_soup.find('p', align='right')
        
        if p_tag_in_block:
            # Collect all text and <br> elements before the p_tag
            raw_text_elements = []
            for element in p_tag_in_block.previous_siblings:
                if element.name in ['hr', 'img', 'h1', 'div']: # Stop at block delimiters
                    break
                raw_text_elements.append(element)
            
            # Reverse and join the raw text content
            # Convert <br> tags to newlines, and get string content for others
            temp_list_for_text = []
            for element in reversed(raw_text_elements):
                if isinstance(element, str):
                    temp_list_for_text.append(element)
                elif element.name == 'br':
                    temp_list_for_text.append('\n')
                # Ignore other tags that might be siblings but not content
            
            raw_text_content = ''.join(temp_list_for_text)
            
            # Apply cleaning (including newline consolidation)
            full_quote_text = clean_text_for_db(raw_text_content)

        else: # Fallback
            full_quote_text = clean_text_for_db(block_soup.get_text(strip=True))

        author_name = None
        source_name = None
        
        author_tag = block_soup.find('span', class_='author')
        if author_tag:
            author_name = clean_text_for_db(author_tag.get_text(strip=True))

        source_tag = block_soup.find('span', class_='source')
        if source_tag:
            source_name = clean_text_for_db(source_tag.get_text(strip=True))
        
        # --- Database opslag ---
        
        if full_quote_text:
            try:
                # Maak de gerelateerde objecten aan of haal ze op
                author_obj, _ = Author.objects.get_or_create(name=author_name) if author_name else (None, False)
                # De hoofdcategorie is altijd "Quotes" in dit script
                main_category_obj, _ = Category.objects.get_or_create(name="Quotes")
                # De subcategorie (bv "Love and Dreams") wordt de Source
                source_obj, _ = Source.objects.get_or_create(name=category_name)

                # Maak de Quote aan en link naar de juiste objecten
                quote_obj, created_quote = Quote.objects.get_or_create(
                    text=full_quote_text,
                    defaults={'author': author_obj, 'source': source_obj}
                )
        
                # Koppel de hoofdcategorie
                if created_quote or not quote_obj.categories.filter(id=main_category_obj.id).exists():
                    quote_obj.categories.add(main_category_obj)

                if created_quote:
                    self.stdout.write(self.style.SUCCESS(f'Successfully added quote: "{full_quote_text[:50]}..."'))
                else:
                    self.stdout.write(self.style.WARNING(f'Quote already exists (skipped): "{full_quote_text[:50]}..."'))

            except Exception as db_error:
                traceback.print_exc()
                self.stdout.write(self.style.ERROR(f'Error saving quote to DB: {db_error}'))
        else:
            self.stdout.write(self.style.WARNING('Skipped empty quote text (or text extraction failed for block).'))

