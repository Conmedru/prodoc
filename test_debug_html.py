"""Debug script to understand exact HTML structure of doctor pages."""
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

url = "https://prodoctorov.ru/moskva/vrach/654260-kuricyna/"
resp = requests.get(url, headers=HEADERS, timeout=30)
soup = BeautifulSoup(resp.text, "lxml")
html = resp.text

# 1. H1 structure
print("="*60)
print("H1 STRUCTURE")
print("="*60)
h1 = soup.find("h1")
print(f"h1 inner HTML: {h1}")
print(f"h1 children:")
for child in h1.children:
    print(f"  type={type(child).__name__} tag={getattr(child, 'name', 'N/A')} text='{child.get_text(strip=True) if hasattr(child, 'get_text') else str(child).strip()}'")

# 2. Job section structure - find the actual #job section
print("\n" + "="*60)
print("JOB SECTION STRUCTURE")
print("="*60)

# Get raw HTML around id="job"
idx = html.find('id="job"')
if idx >= 0:
    snippet = html[idx:idx+3000]
    print(f"Raw HTML from id='job' (first 3000 chars):")
    print(snippet)
else:
    print("id='job' NOT FOUND in HTML")

# 3. Structured data in doctor-contacts mount point
print("\n" + "="*60)
print("VUE DOCTOR CONTACTS DATA")
print("="*60)
mount = soup.find(id="doctor-contacts")
if mount:
    print(f"Tag: {mount.name}")
    print(f"Inner HTML (first 1000): {str(mount)[:1000]}")

# 4. All script tags with clinic/lpu data
print("\n" + "="*60)
print("SCRIPTS WITH LPU DATA")
print("="*60)
for script in soup.find_all("script"):
    text = script.get_text()
    if "address" in text.lower() and ("lpu" in text.lower() or "clinic" in text.lower() or "klinika" in text.lower()):
        print(f"Script (first 500 chars): {text[:500]}")
        print("---")

# 5. Look for data in html attributes
print("\n" + "="*60)
print("DATA ATTRIBUTES WITH ADDRESSES")
print("="*60)
for el in soup.find_all(True):
    for attr, val in el.attrs.items():
        if isinstance(val, str) and "address" in val.lower() and len(val) > 20:
            print(f"  <{el.name} {attr}='{val[:300]}'")
