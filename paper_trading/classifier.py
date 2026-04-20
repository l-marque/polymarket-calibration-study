"""Classificateur de catégorie basé sur les slugs (repris du notebook 01)."""

CRYPTO_PREFIXES = (
    "btc-", "bitcoin-", "eth-", "ethereum-", "sol-", "solana-",
    "doge-", "xrp-", "crypto-", "will-btc", "will-eth", "will-sol",
    "will-bitcoin", "will-ethereum", "ada-", "bnb-", "avax-",
    "matic-", "link-", "dot-", "uni-",
)

def classify(slug: str) -> str:
    """Retourne la catégorie basée sur le slug."""
    if not slug:
        return "other"
    s = slug.lower()
    if any(s.startswith(p) for p in CRYPTO_PREFIXES):
        return "crypto"
    return "other"