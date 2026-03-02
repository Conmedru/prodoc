"""Smoke test: parse a few doctors and verify data extraction quality."""
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

from scraper.fetcher import Fetcher
from scraper.parsers import parse_listing_page, parse_doctor_page

fetcher = Fetcher()

# 1. Test listing page parsing
print("\n" + "="*60)
print("TEST: Listing page parsing")
print("="*60)

html = fetcher.get_html("https://prodoctorov.ru/moskva/oftalmolog/")
if html:
    urls, max_page = parse_listing_page(html)
    print(f"Doctors on page 1: {len(urls)}")
    print(f"Max page: {max_page}")
    for u in urls[:5]:
        print(f"  {u}")
else:
    print("FAILED to fetch listing page!")
    sys.exit(1)

# 2. Test doctor detail parsing on several doctors
test_urls = [
    "https://prodoctorov.ru/moskva/vrach/654260-kuricyna/",
    "https://prodoctorov.ru/moskva/vrach/162733-vereshagin/",
    "https://prodoctorov.ru/moskva/vrach/588298-fadeeva/",
]

print("\n" + "="*60)
print("TEST: Doctor detail page parsing")
print("="*60)

for url in test_urls:
    print(f"\n--- {url} ---")
    html = fetcher.get_html(url)
    if not html:
        print("  FAILED to fetch!")
        continue
    
    doc = parse_doctor_page(html, url=url)
    print(f"  Name:        {doc.full_name}")
    print(f"  City:        {doc.city}")
    print(f"  Specialties: {doc.specialties}")
    print(f"  Experience:  {doc.experience_years}")
    print(f"  Workplaces:  {doc.current_workplaces}")
    print(f"  Addresses:   {doc.work_addresses}")
    
    # Quality checks
    issues = []
    if not doc.full_name:
        issues.append("NO NAME")
    if not doc.city:
        issues.append("NO CITY")
    if not doc.specialties:
        issues.append("NO SPECIALTIES")
    if not doc.current_workplaces:
        issues.append("NO WORKPLACES")
    
    if issues:
        print(f"  ⚠ ISSUES: {', '.join(issues)}")
    else:
        print(f"  ✓ All fields present")

print(f"\nFetcher stats: {fetcher.stats()}")
