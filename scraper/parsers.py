"""HTML parsers for prodoctorov.ru listing and doctor detail pages."""
import re
import json
import html
import logging
from dataclasses import dataclass, field
from bs4 import BeautifulSoup

from scraper.config import BASE_URL

logger = logging.getLogger(__name__)


@dataclass
class DoctorInfo:
    """Parsed doctor data."""
    url: str = ""
    full_name: str = ""
    city: str = ""
    specialties: list[str] = field(default_factory=list)
    current_workplaces: list[str] = field(default_factory=list)
    work_addresses: list[str] = field(default_factory=list)
    experience_years: str = ""


def parse_listing_page(html_text: str) -> tuple[list[str], int]:
    """Parse a specialty listing page.
    
    Returns:
        tuple of (list of doctor relative URLs, max page number)
    """
    soup = BeautifulSoup(html_text, "lxml")
    
    doctor_urls = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.match(r"^/[^/]+/vrach/\d+-[^/]+/$", href):
            doctor_urls.add(href)
        elif re.match(r"^/[^/]+/vrach/\d+-[^/]+/#", href):
            clean = href.split("#")[0]
            if not clean.endswith("/"):
                clean += "/"
            doctor_urls.add(clean)

    max_page = 1
    for a in soup.find_all("a", href=True):
        match = re.search(r"[?&]page=(\d+)", a["href"])
        if match:
            page_num = int(match.group(1))
            if page_num > max_page:
                max_page = page_num

    urls = sorted(doctor_urls)
    logger.info(f"Found {len(urls)} doctor URLs, max page: {max_page}")
    return urls, max_page


def _extract_name_and_city(soup: BeautifulSoup) -> tuple[str, str]:
    """Extract doctor name and city from h1 using schema.org itemprop attributes."""
    name = ""
    city = ""
    
    h1 = soup.find("h1")
    if not h1:
        return "", ""
    
    # Primary: use itemprop attributes scoped within h1
    name_el = h1.find(attrs={"itemprop": "name"})
    if name_el:
        # itemprop="name" span may contain nested child spans (e.g. vue icons) — get direct text
        direct_text = name_el.find(text=True, recursive=False)
        if direct_text:
            name = direct_text.strip()
        else:
            name = name_el.get_text(strip=True)
    
    city_el = h1.find(attrs={"itemprop": "addressLocality"})
    if city_el:
        city = city_el.get_text(strip=True)
    
    # Fallback: parse h1 children directly
    if not name:
        spans = h1.find_all("span", recursive=False)
        if len(spans) >= 2:
            name = spans[0].get_text(strip=True)
            city = spans[1].get_text(strip=True)
        else:
            name = h1.get_text(strip=True)
    
    return name, city


def _extract_specialties(soup: BeautifulSoup) -> list[str]:
    """Extract doctor specialties."""
    specs = []
    
    specs_container = soup.find(class_="b-doctor-intro__specs")
    if specs_container:
        for a in specs_container.find_all("a"):
            text = a.get_text(strip=True)
            if text:
                specs.append(text)
    
    if not specs:
        spec_el = soup.find(class_="b-doctor-intro__spec")
        if spec_el:
            text = spec_el.get_text(strip=True)
            if text:
                specs.append(text)
    
    return specs


def _extract_experience_years(soup: BeautifulSoup) -> str:
    """Extract years of experience."""
    el = soup.find(string=lambda s: s and "Стаж" in s)
    if el:
        parent = el.find_parent()
        if parent:
            text = parent.get_text(strip=True)
            match = re.search(r"(\d+)\s*(лет|год|года)", text)
            if match:
                return match.group(0)
    return ""


def _extract_workplaces_from_job_section(soup: BeautifulSoup) -> list[str]:
    """Extract current workplaces from the job/experience section.
    
    HTML structure:
      <div id="job">
        <div class="b-doctor-details__item-box">
          <div class="text-body-1">          <!-- one workplace block -->
            <div class="d-flex ...">
              <div class="b-doctor-details__data-icon ui-icon-clinic ..."></div>
              <div class="b-doctor-details__data-title text--text mt-1">Name</div>
            </div>
            <div class="b-doctor-details__item-description ...">
              <div class="text-info--text mb-1">2019 — н. в.</div>
              <div class="text--text">Position</div>
            </div>
          </div>
    """
    workplaces = []
    
    job_section = soup.find(id="job")
    if not job_section:
        return workplaces
    
    # Navigate to the containing section (the anchor's parent holds the content)
    container = job_section
    # Find the item-box that holds workplace entries
    item_box = container.find(class_=lambda c: c and "b-doctor-details__item-box" in c)
    if not item_box:
        # Try parent
        parent = container.find_parent()
        if parent:
            item_box = parent.find(class_=lambda c: c and "b-doctor-details__item-box" in c)
    if not item_box:
        return workplaces
    
    # Each workplace block is a text-body-1 div that contains a clinic icon
    for block in item_box.find_all("div", class_="text-body-1", recursive=True):
        # Must have a clinic icon to be a workplace entry (not just a date continuation)
        icon = block.find(class_=lambda c: c and "ui-icon-clinic" in c)
        if not icon:
            continue
        
        # Get the workplace name
        title_el = block.find(class_=lambda c: c and "b-doctor-details__data-title" in c)
        if not title_el:
            continue
        name = title_el.get_text(strip=True)
        if not name:
            continue
        
        # Check dates — look for "н. в." (present) in this block or subsequent continuation blocks
        is_current = False
        desc = block.find(class_=lambda c: c and "b-doctor-details__item-description" in c)
        if desc:
            date_text = desc.get_text()
            if "н. в." in date_text or "н.в." in date_text:
                is_current = True
        
        # Also check next sibling blocks (date continuations without their own icon/title)
        if not is_current:
            next_sib = block.find_next_sibling("div", class_="text-body-1")
            while next_sib:
                sib_icon = next_sib.find(class_=lambda c: c and "ui-icon-clinic" in c)
                if sib_icon:
                    break  # next workplace block starts
                sib_desc = next_sib.find(class_=lambda c: c and "b-doctor-details__item-description" in c)
                if sib_desc and ("н. в." in sib_desc.get_text() or "н.в." in sib_desc.get_text()):
                    is_current = True
                    break
                next_sib = next_sib.find_next_sibling("div", class_="text-body-1")
        
        if is_current:
            workplaces.append(name)
    
    return workplaces


def _normalize_clinic_name(name: str) -> str:
    """Normalize clinic name for fuzzy matching.
    
    Strips common prefixes/suffixes, quotes, and whitespace.
    E.g. 'Клиника «Чудо Доктор»' -> 'чудо доктор'
         '«Чудо-Доктор» на Школьной 46' -> 'чудо доктор'
    """
    n = name.lower()
    # Remove guillemets and regular quotes
    n = re.sub(r'[«»"\'""„]', '', n)
    # Remove common prefixes
    for prefix in ["клиника", "клиники", "медицинский центр", "мц", "центр"]:
        n = re.sub(rf'^{prefix}\s+', '', n)
    # Remove address suffixes like "на Школьной 46"
    n = re.sub(r'\s+на\s+\S+(\s+\S+)?$', '', n)
    # Remove location suffixes like ", г. Москва"
    n = re.sub(r',?\s*г\.\s*\S+.*$', '', n)
    # Normalize hyphens and spaces
    n = re.sub(r'[-–—]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def _fuzzy_match_address(workplace: str, addresses: dict[str, str]) -> str:
    """Fuzzy match a workplace name against address dictionary keys."""
    # Direct substring match
    for clinic_name, clinic_addr in addresses.items():
        if workplace in clinic_name or clinic_name in workplace:
            return clinic_addr
    
    # Normalized match
    wp_norm = _normalize_clinic_name(workplace)
    if not wp_norm:
        return ""
    
    for clinic_name, clinic_addr in addresses.items():
        cn_norm = _normalize_clinic_name(clinic_name)
        if not cn_norm:
            continue
        if wp_norm in cn_norm or cn_norm in wp_norm:
            return clinic_addr
        # Check if key words overlap significantly
        wp_words = set(wp_norm.split())
        cn_words = set(cn_norm.split())
        if len(wp_words) >= 2 and len(wp_words & cn_words) >= len(wp_words) - 1:
            return clinic_addr
    
    return ""


def _extract_addresses_from_vue_lpu_list(soup: BeautifulSoup) -> dict[str, str]:
    """Extract clinic name -> address from Vue :lpu-address-list attribute.
    
    The doctor-page-lpu-list Vue component has a :lpu-address-list attribute
    containing JSON array with current workplace data including addresses.
    """
    addresses = {}
    
    lpu_list_el = soup.find("doctor-page-lpu-list")
    if not lpu_list_el:
        return addresses
    
    raw = lpu_list_el.get(":lpu-address-list", "")
    if not raw:
        return addresses
    
    try:
        data = json.loads(raw)
        for entry in data:
            lpu = entry.get("lpu", {})
            name = lpu.get("name", "").strip()
            addr = entry.get("address", "").strip()
            if not addr:
                addr = lpu.get("address", "").strip()
            if name:
                addresses[name] = addr
    except (json.JSONDecodeError, TypeError) as e:
        logger.debug(f"Failed to parse :lpu-address-list JSON: {e}")
    
    return addresses


def _extract_addresses_from_embedded_json(html_text: str) -> dict[str, str]:
    """Extract clinic name -> address mapping from embedded JSON data in HTML (fallback)."""
    addresses = {}
    
    decoded = html.unescape(html_text)
    
    pattern = r'"name"\s*:\s*"([^"]+)"[^}]*?"address"\s*:\s*"([^"]*)"'
    for match in re.finditer(pattern, decoded):
        name = match.group(1).strip()
        addr = match.group(2).strip()
        if name and addr:
            addresses[name] = addr
    
    return addresses


def _extract_addresses_from_service_prices(soup: BeautifulSoup) -> dict[str, str]:
    """Extract clinic -> address from service prices section."""
    addresses = {}
    
    for el in soup.find_all(class_=lambda c: c and "doctor-service-prices-lpu" in c):
        text = el.get_text(separator="|", strip=True)
        if "|" in text:
            parts = text.split("|")
            if len(parts) >= 2:
                clinic = parts[0].strip()
                addr = parts[1].strip()
                if clinic and addr:
                    addresses[clinic] = addr
    
    return addresses


def parse_doctor_page(html_text: str, url: str = "") -> DoctorInfo:
    """Parse a doctor detail page and extract all needed data."""
    soup = BeautifulSoup(html_text, "lxml")
    doctor = DoctorInfo(url=url)
    
    # Name and city
    doctor.full_name, doctor.city = _extract_name_and_city(soup)
    
    # Specialties
    doctor.specialties = _extract_specialties(soup)
    
    # Experience
    doctor.experience_years = _extract_experience_years(soup)
    
    # Current workplaces
    doctor.current_workplaces = _extract_workplaces_from_job_section(soup)
    
    # Addresses: Vue :lpu-address-list (primary), then embedded JSON, then service prices
    addr_vue = _extract_addresses_from_vue_lpu_list(soup)
    addr_json = _extract_addresses_from_embedded_json(html_text)
    addr_prices = _extract_addresses_from_service_prices(soup)
    all_addresses = {**addr_json, **addr_prices, **addr_vue}  # vue wins on conflict
    
    # Match addresses to current workplaces
    for wp in doctor.current_workplaces:
        addr = all_addresses.get(wp, "")
        if not addr:
            addr = _fuzzy_match_address(wp, all_addresses)
        doctor.work_addresses.append(addr)
    
    # If no current workplaces found but addresses exist, take from service prices
    if not doctor.current_workplaces and all_addresses:
        for name, addr in all_addresses.items():
            doctor.current_workplaces.append(name)
            doctor.work_addresses.append(addr)
    
    logger.debug(
        f"Parsed: {doctor.full_name} | specs={doctor.specialties} | "
        f"work={doctor.current_workplaces}"
    )
    
    return doctor
