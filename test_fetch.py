import requests

# De "alles-in-één" URL die alle quotes zou moeten bevatten
URL = 'https://generationterrorists.com/cgi-bin/quotes.cgi?start=0&section=Love+and+Dreams&per_page=1500'
HEADERS = {'User-Agent': 'Mozilla/5.0'}

print(f"Poging om de volledige pagina op te halen van: {URL}")

try:
    # We gebruiken een langere timeout voor deze grote pagina
    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding

    # Sla de exacte HTML die we ontvangen op in een bestand
    with open("pagina_volledig_output.html", "w", encoding="utf-8") as f:
        f.write(response.text)

    print("\n--- SUCCES ---")
    print("De volledige HTML van de pagina is opgeslagen in het bestand 'pagina_volledig_output.html'.")

except Exception as e:
    print(f"\n--- FOUT --- \n{e}")