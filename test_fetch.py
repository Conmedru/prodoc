"""Test script to fetch raw HTML from prodoctorov.ru and understand the structure."""
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

def test_listing_page():
    """Fetch listing page and analyze structure."""
    url = "https://prodoctorov.ru/moskva/oftalmolog/"
    print(f"\n{'='*60}")
    print(f"FETCHING LISTING: {url}")
    print(f"{'='*60}")
    
    resp = requests.get(url, headers=HEADERS, timeout=30)
    print(f"Status: {resp.status_code}")
    print(f"Content-Length: {len(resp.text)}")
    
    soup = BeautifulSoup(resp.text, "lxml")
    
    # Find doctor links
    doctor_links = soup.find_all("a", href=lambda h: h and "/vrach/" in h and h.count("/") >= 4)
    print(f"\nDoctor links found: {len(doctor_links)}")
    for link in doctor_links[:5]:
        print(f"  href={link.get('href')}  text={link.get_text(strip=True)[:60]}")
    
    # Find pagination
    page_links = soup.find_all("a", href=lambda h: h and "page=" in h)
    print(f"\nPagination links: {len(page_links)}")
    for pl in page_links[:5]:
        print(f"  {pl.get('href')} -> {pl.get_text(strip=True)}")
    
    # Look for doctor cards/containers
    print("\n--- Searching for doctor card containers ---")
    for cls_name in ["doctor-card", "doctor_card", "doctor-item", "doctor_item", "b-doctor-card", "card"]:
        found = soup.find_all(class_=lambda c: c and cls_name in c)
        if found:
            print(f"  class containing '{cls_name}': {len(found)} elements")
            print(f"    tag: {found[0].name}, classes: {found[0].get('class')}")
    
    # Print first 200 lines of HTML to find patterns
    lines = resp.text.split("\n")
    # Find lines containing "vrach" links
    for i, line in enumerate(lines):
        if "/vrach/" in line and "href" in line and i < 2000:
            print(f"\n  Line {i}: {line.strip()[:200]}")
            if i > 0:
                # print surrounding context
                for j in range(max(0,i-2), min(len(lines), i+3)):
                    print(f"    [{j}] {lines[j].strip()[:200]}")
            break
    
    return soup

def test_doctor_page():
    """Fetch doctor detail page and analyze structure."""
    url = "https://prodoctorov.ru/moskva/vrach/654260-kuricyna/"
    print(f"\n{'='*60}")
    print(f"FETCHING DOCTOR: {url}")
    print(f"{'='*60}")
    
    resp = requests.get(url, headers=HEADERS, timeout=30)
    print(f"Status: {resp.status_code}")
    print(f"Content-Length: {len(resp.text)}")
    
    soup = BeautifulSoup(resp.text, "lxml")
    
    # Title / Name
    h1 = soup.find("h1")
    print(f"\nh1: {h1.get_text(strip=True) if h1 else 'NOT FOUND'}")
    
    # Look for JSON-LD structured data
    scripts = soup.find_all("script", type="application/ld+json")
    print(f"\nJSON-LD scripts: {len(scripts)}")
    for s in scripts:
        text = s.get_text()[:500]
        print(f"  {text}")
    
    # Look for specialty
    print("\n--- Specialty ---")
    spec_elements = soup.find_all(class_=lambda c: c and ("spec" in c.lower() if c else False))
    for el in spec_elements[:5]:
        print(f"  class={el.get('class')} text={el.get_text(strip=True)[:100]}")
    
    # Look for workplace
    print("\n--- Workplace ---")
    work_elements = soup.find_all(class_=lambda c: c and ("work" in c.lower() or "clinic" in c.lower() or "lpu" in c.lower() if c else False))
    for el in work_elements[:5]:
        print(f"  class={el.get('class')} text={el.get_text(strip=True)[:200]}")
    
    # Look for address
    print("\n--- Address ---")
    addr_elements = soup.find_all(class_=lambda c: c and ("addr" in c.lower() or "address" in c.lower() or "location" in c.lower() if c else False))
    for el in addr_elements[:5]:
        print(f"  class={el.get('class')} text={el.get_text(strip=True)[:200]}")
    
    # Experience section
    print("\n--- Experience section keywords ---")
    for keyword in ["Опыт работы", "Место работы", "Стаж"]:
        el = soup.find(string=lambda s: s and keyword in s)
        if el:
            parent = el.find_parent()
            print(f"  '{keyword}' found in <{parent.name}> class={parent.get('class')}")
            # print sibling content
            for sib in parent.find_next_siblings()[:3]:
                print(f"    sibling <{sib.name}> class={sib.get('class')} text={sib.get_text(strip=True)[:200]}")
    
    # Dump key sections of raw HTML
    text = resp.text
    for marker in ["Опыт работы", "Место работы", "Образование"]:
        idx = text.find(marker)
        if idx >= 0:
            print(f"\n--- Raw HTML around '{marker}' (pos {idx}) ---")
            snippet = text[max(0,idx-200):idx+500]
            print(snippet[:700])

    return soup

if __name__ == "__main__":
    test_listing_page()
    test_doctor_page()
