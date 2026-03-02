"""Deep test of doctor detail page HTML to find workplace/address data."""
import requests
from bs4 import BeautifulSoup
import re
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

def analyze_doctor(url):
    print(f"\n{'='*70}")
    print(f"DOCTOR: {url}")
    print(f"{'='*70}")
    
    resp = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(resp.text, "lxml")
    html = resp.text
    
    # 1. Name
    h1 = soup.find("h1")
    name_raw = h1.get_text(strip=True) if h1 else "N/A"
    print(f"Name raw: {name_raw}")
    
    # 2. Specialty
    spec_el = soup.find(class_="b-doctor-intro__specs")
    specs = []
    if spec_el:
        for a in spec_el.find_all("a"):
            specs.append(a.get_text(strip=True))
    if not specs:
        spec_single = soup.find(class_="b-doctor-intro__spec")
        if spec_single:
            specs.append(spec_single.get_text(strip=True))
    print(f"Specialties: {specs}")
    
    # 3. Look for workplace in Vue data / script tags
    print("\n--- Vue/JS data for workplaces ---")
    for script in soup.find_all("script"):
        text = script.get_text()
        if "lpu" in text.lower() or "clinic" in text.lower() or "workplace" in text.lower():
            # Try to find JSON data
            for line in text.split("\n"):
                if "lpu" in line.lower() or "clinic" in line.lower():
                    print(f"  JS line: {line.strip()[:200]}")
    
    # 4. Look for data attributes on Vue mount points
    vue_mount = soup.find(class_="vue-doctor-page-lpu-list-mount")
    if vue_mount:
        print(f"\n--- Vue mount point ---")
        print(f"  Tag: {vue_mount.name}")
        print(f"  Attrs: {dict(vue_mount.attrs)}")
        for attr, val in vue_mount.attrs.items():
            if attr.startswith("data-") or attr.startswith(":"):
                print(f"  {attr} = {str(val)[:300]}")
    
    # 5. Look for any data-props or data-* attributes with LPU info
    print("\n--- Elements with data-lpu or data-props ---")
    for el in soup.find_all(attrs={"data-lpu": True}):
        print(f"  data-lpu: {el.get('data-lpu')[:200]}")
    for el in soup.find_all(attrs={"data-props": True}):
        props = el.get("data-props", "")
        if "lpu" in props.lower() or "address" in props.lower() or "clinic" in props.lower():
            print(f"  data-props (class={el.get('class')}): {props[:500]}")
    
    # 6. Find #job section
    print("\n--- #job section (work experience) ---")
    job_anchor = soup.find(id="job")
    if job_anchor:
        # Get the content after this anchor
        container = job_anchor.find_parent()
        if container:
            text = container.get_text(separator=" | ", strip=True)[:500]
            print(f"  Content: {text}")
    else:
        # Try to find by searching HTML
        idx = html.find('id="job"')
        if idx >= 0:
            snippet = html[idx:idx+2000]
            print(f"  Raw HTML: {snippet[:1000]}")
    
    # 7. Search for clinic names in the whole page
    print("\n--- doctor-service-prices-lpu ---")
    for el in soup.find_all(class_=lambda c: c and "doctor-service-prices-lpu" in c):
        text = el.get_text(separator=" | ", strip=True)
        if text:
            print(f"  {text[:300]}")
    
    # 8. Check for any hidden/embedded JSON data
    print("\n--- Embedded JSON with doctor data ---")
    for script in soup.find_all("script"):
        text = script.get_text()
        # Look for common patterns
        for pattern in [r'window\.__INITIAL_STATE__\s*=', r'window\.__NUXT__\s*=', r'"doctor":\s*\{', r'"workplaces?":\s*\[']:
            match = re.search(pattern, text)
            if match:
                start = max(0, match.start() - 20)
                print(f"  Pattern '{pattern}': ...{text[start:start+500]}")
    
    # 9. Look for b-doctor-details__data sections
    print("\n--- b-doctor-details sections ---")
    for el in soup.find_all(class_=lambda c: c and "b-doctor-details__data" in c):
        text = el.get_text(separator=" | ", strip=True)
        if text and len(text) > 5:
            print(f"  class={el.get('class')}: {text[:200]}")
    
    # 10. Raw HTML around "Клиника" or clinic names
    for keyword in ["Клиника", "клиника", "Медицин", "Больница"]:
        idx = html.find(keyword)
        if idx >= 0:
            print(f"\n--- Raw around '{keyword}' (pos {idx}) ---")
            print(html[max(0,idx-150):idx+300][:450])
            break

# Test with multiple doctors
analyze_doctor("https://prodoctorov.ru/moskva/vrach/654260-kuricyna/")
analyze_doctor("https://prodoctorov.ru/moskva/vrach/162733-vereshagin/")
