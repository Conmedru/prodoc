"""Configuration for prodoctorov.ru scraper."""

BASE_URL = "https://prodoctorov.ru"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# Rate limiting
REQUEST_DELAY_MIN = 1.0  # seconds
REQUEST_DELAY_MAX = 2.5  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Request timeout
REQUEST_TIMEOUT = 30  # seconds

# Pilot specialties: slug -> display name
PILOT_SPECIALTIES = {
    "oftalmolog": "Офтальмолог",
    "detskiy-oftalmolog": "Детский офтальмолог",
    "pediatr": "Педиатр",
    "nevrolog": "Невролог",
}

# Pilot city
PILOT_CITY = "moskva"
PILOT_CITY_NAME = "Москва"

# Output
OUTPUT_DIR = "output"
