"""Main scraper orchestrator for prodoctorov.ru."""
import logging
import json
import os
from datetime import datetime

from scraper.config import BASE_URL, PILOT_SPECIALTIES, PILOT_CITY, PILOT_CITY_NAME, OUTPUT_DIR
from scraper.fetcher import Fetcher
from scraper.parsers import parse_listing_page, parse_doctor_page, DoctorInfo
from scraper.exporter import export_to_excel

logger = logging.getLogger(__name__)


class ProdoctorovScraper:
    """Scraper for prodoctorov.ru doctor data."""

    def __init__(self):
        self.fetcher = Fetcher()
        self.doctors: list[DoctorInfo] = []
        self._checkpoint_dir = os.path.join(OUTPUT_DIR, "checkpoints")

    def collect_doctor_urls(self, city: str, specialty_slug: str) -> list[str]:
        """Collect all doctor URLs for a given city and specialty."""
        urls = []
        page = 1
        max_page = 1

        while page <= max_page:
            listing_url = f"{BASE_URL}/{city}/{specialty_slug}/"
            if page > 1:
                listing_url += f"?page={page}"

            logger.info(f"Fetching listing page {page}/{max_page}: {listing_url}")
            html_text = self.fetcher.get_html(listing_url)

            if html_text is None:
                logger.warning(f"Failed to fetch listing page {page}")
                page += 1
                continue

            page_urls, detected_max = parse_listing_page(html_text)
            if detected_max > max_page:
                max_page = detected_max
                logger.info(f"Updated max page to {max_page}")

            for url in page_urls:
                full_url = f"{BASE_URL}{url}"
                if full_url not in urls:
                    urls.append(full_url)

            logger.info(f"Page {page}: found {len(page_urls)} doctors (total: {len(urls)})")
            page += 1

        return urls

    def scrape_doctor(self, url: str) -> DoctorInfo | None:
        """Scrape a single doctor's detail page."""
        html_text = self.fetcher.get_html(url)
        if html_text is None:
            return None

        try:
            doctor = parse_doctor_page(html_text, url=url)
            return doctor
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            return None

    def _save_checkpoint(self, specialty_slug: str, doctors: list[DoctorInfo]):
        """Save intermediate results to JSON checkpoint."""
        os.makedirs(self._checkpoint_dir, exist_ok=True)
        filepath = os.path.join(self._checkpoint_dir, f"{specialty_slug}.json")

        data = []
        for d in doctors:
            data.append({
                "url": d.url,
                "full_name": d.full_name,
                "city": d.city,
                "specialties": d.specialties,
                "current_workplaces": d.current_workplaces,
                "work_addresses": d.work_addresses,
                "experience_years": d.experience_years,
            })

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Checkpoint saved: {filepath} ({len(data)} doctors)")

    def _load_checkpoint(self, specialty_slug: str) -> list[DoctorInfo]:
        """Load doctors from a checkpoint file."""
        filepath = os.path.join(self._checkpoint_dir, f"{specialty_slug}.json")
        if not os.path.exists(filepath):
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        doctors = []
        for d in data:
            doctors.append(DoctorInfo(
                url=d["url"],
                full_name=d["full_name"],
                city=d["city"],
                specialties=d["specialties"],
                current_workplaces=d["current_workplaces"],
                work_addresses=d["work_addresses"],
                experience_years=d["experience_years"],
            ))
        logger.info(f"Loaded {len(doctors)} doctors from checkpoint: {filepath}")
        return doctors

    def scrape_specialty(
        self,
        city: str,
        specialty_slug: str,
        specialty_name: str,
        resume: bool = True,
    ) -> list[DoctorInfo]:
        """Scrape all doctors for a given specialty in a city."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Scraping: {specialty_name} in {city}")
        logger.info(f"{'='*60}")

        # Check for existing checkpoint
        existing = []
        existing_urls = set()
        if resume:
            existing = self._load_checkpoint(specialty_slug)
            existing_urls = {d.url for d in existing}

        # Collect all doctor URLs
        doctor_urls = self.collect_doctor_urls(city, specialty_slug)
        logger.info(f"Total doctor URLs: {len(doctor_urls)}")

        # Filter out already scraped
        to_scrape = [u for u in doctor_urls if u not in existing_urls]
        logger.info(f"Already scraped: {len(existing_urls)}, remaining: {len(to_scrape)}")

        specialty_doctors = list(existing)
        checkpoint_interval = 25

        for i, url in enumerate(to_scrape):
            logger.info(f"[{i+1}/{len(to_scrape)}] Scraping: {url}")
            doctor = self.scrape_doctor(url)

            if doctor is not None:
                if not doctor.city:
                    doctor.city = PILOT_CITY_NAME
                specialty_doctors.append(doctor)
            else:
                logger.warning(f"Failed to scrape: {url}")

            # Periodic checkpoint
            if (i + 1) % checkpoint_interval == 0:
                self._save_checkpoint(specialty_slug, specialty_doctors)

        # Final checkpoint
        self._save_checkpoint(specialty_slug, specialty_doctors)

        logger.info(f"Completed {specialty_name}: {len(specialty_doctors)} doctors")
        return specialty_doctors

    def run_pilot(self, city: str = PILOT_CITY, specialties: dict | None = None):
        """Run the pilot scrape for specified specialties."""
        if specialties is None:
            specialties = PILOT_SPECIALTIES

        logger.info(f"Starting pilot scrape for {city}")
        logger.info(f"Specialties: {list(specialties.keys())}")

        all_doctors = []
        for slug, name in specialties.items():
            doctors = self.scrape_specialty(city, slug, name)
            all_doctors.extend(doctors)

        # Deduplicate by URL
        seen_urls = set()
        unique_doctors = []
        for d in all_doctors:
            if d.url not in seen_urls:
                seen_urls.add(d.url)
                unique_doctors.append(d)

        logger.info(f"\nTotal unique doctors: {len(unique_doctors)}")

        # Export
        filepath = export_to_excel(unique_doctors)
        logger.info(f"Excel exported: {filepath}")

        # Print stats
        stats = self.fetcher.stats()
        logger.info(f"Request stats: {stats}")

        return unique_doctors
