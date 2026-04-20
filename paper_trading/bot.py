"""Bot paper trading principal. Tourne en boucle."""
import sys
import time
import logging
from pathlib import Path

# Ajoute le dossier courant au PATH pour les imports
sys.path.insert(0, str(Path(__file__).parent))

from config import POLL_INTERVAL_SECONDS, LOG_DIR
from poller import find_candidates
from portfolio import open_position, resolve_open_positions, print_summary


# Logging
LOG_FILE = LOG_DIR / "bot.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def run_once():
    """Exécute un cycle : résout les positions ouvertes, puis ouvre de nouvelles positions."""
    logger.info("--- Nouveau cycle ---")
    try:
        resolve_open_positions()
    except Exception as e:
        logger.error(f"Erreur dans resolve_open_positions: {e}")

    try:
        candidates = find_candidates()
        for market in candidates:
            open_position(market)
    except Exception as e:
        logger.error(f"Erreur dans find_candidates/open_position: {e}")

    print_summary()


def main():
    logger.info("=== Bot paper trading démarré ===")
    logger.info(f"Poll interval : {POLL_INTERVAL_SECONDS}s")
    while True:
        try:
            run_once()
            logger.info(f"Sommeil {POLL_INTERVAL_SECONDS}s...")
            time.sleep(POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logger.info("Arrêt manuel demandé. Bye.")
            break
        except Exception as e:
            logger.exception(f"Erreur inattendue dans la boucle principale: {e}")
            time.sleep(60)  # attendre 1 min avant de retenter


if __name__ == "__main__":
    main()