"""Create a sample of ~20 doctors (5 per specialty) for format approval."""
import logging
import sys

from scraper.config import BASE_URL, PILOT_SPECIALTIES, PILOT_CITY, PILOT_CITY_NAME
from scraper.fetcher import Fetcher
from scraper.parsers import parse_listing_page, parse_doctor_page, DoctorInfo
from scraper.exporter import export_to_excel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def collect_sample(city: str = PILOT_CITY, per_specialty: int = 5) -> list[DoctorInfo]:
    """Collect a small sample of doctors for format approval."""
    fetcher = Fetcher()
    all_doctors: list[DoctorInfo] = []

    for slug, name in PILOT_SPECIALTIES.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Collecting sample: {name}")
        logger.info(f"{'='*60}")

        # Fetch first page only
        listing_url = f"{BASE_URL}/{city}/{slug}/"
        html = fetcher.get_html(listing_url)
        if not html:
            logger.warning(f"Failed to fetch {listing_url}")
            continue

        urls, _ = parse_listing_page(html)
        logger.info(f"Found {len(urls)} doctors on page 1, taking first {per_specialty}")

        for rel_url in urls[:per_specialty]:
            doctor_url = f"{BASE_URL}{rel_url}"
            logger.info(f"Scraping: {doctor_url}")

            doctor_html = fetcher.get_html(doctor_url)
            if not doctor_html:
                logger.warning(f"Failed to fetch doctor page: {doctor_url}")
                continue

            try:
                doctor = parse_doctor_page(doctor_html, url=doctor_url)
                if not doctor.city:
                    doctor.city = PILOT_CITY_NAME
                all_doctors.append(doctor)
                logger.info(f"  ✓ {doctor.full_name} | {doctor.current_workplaces}")
            except Exception as e:
                logger.error(f"  ✗ Error parsing {doctor_url}: {e}")

        logger.info(f"Collected {len(all_doctors)} total so far")

    logger.info(f"\n{'='*60}")
    logger.info(f"Sample collection complete: {len(all_doctors)} doctors")
    logger.info(f"{'='*60}")

    return all_doctors


if __name__ == "__main__":
    doctors = collect_sample(per_specialty=5)
    if doctors:
        filepath = export_to_excel(doctors, filename="sample_20_doctors.xlsx")
        logger.info(f"\nExcel saved: {filepath}")
    else:
        logger.error("No doctors collected!")
