import requests

# De exacte URL voor pagina 2
URL = 'https://generationterrorists.com/cgi-bin/quotes.cgi?start=50&section=Love+and+Dreams&per_page=50'
HEADERS = {'User-Agent': 'Mozilla/5.0'}

print(f"Poging om de HTML van PAGINA 2 op te halen...")

try:
    response = requests.get(URL, headers=HEADERS, timeout=10)
    response.raise_for_status()
    
    with open("pagina_2_output.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    
    print("\n--- SUCCES ---")
    print("De HTML van PAGINA 2 is opgeslagen in 'pagina_2_output.html'.")

except Exception as e:
    print(f"\n--- FOUT --- \n{e}")