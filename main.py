"""Entry point for prodoctorov.ru scraper."""
import argparse
import logging
import sys

from scraper.config import PILOT_SPECIALTIES, PILOT_CITY
from scraper.scraper import ProdoctorovScraper


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("scraper.log", encoding="utf-8"),
        ],
    )


def main():
    parser = argparse.ArgumentParser(description="Prodoctorov.ru doctor scraper")
    parser.add_argument(
        "--city",
        default=PILOT_CITY,
        help="City slug (default: moskva)",
    )
    parser.add_argument(
        "--specialties",
        nargs="*",
        help="Specialty slugs to scrape (default: pilot set)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of doctors per specialty (0 = no limit)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Don't resume from checkpoints",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    parser.add_argument(
        "--resume-excel",
        type=str,
        help="Path to an existing Excel file to resume from. The script will skip URLs already present with a non-empty Specialty field and append new ones.",
    )
    args = parser.parse_args()
    setup_logging(args.verbose)

    scraper = ProdoctorovScraper()

    if args.specialties:
        specs = {s: s for s in args.specialties}
    else:
        specs = PILOT_SPECIALTIES

    doctors = scraper.run_pilot(city=args.city, specialties=specs, resume_excel=args.resume_excel)
    print(f"\nDone! Scraped {len(doctors)} unique doctors.")


if __name__ == "__main__":
    main()
