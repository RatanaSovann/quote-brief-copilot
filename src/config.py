"""Model names, prices and the exchange rate. The only place any of these live.

Change a model or price here and every cost line in the project follows.
"""

EXTRACT_MODEL = "claude-sonnet-5-5"   # extraction + reply drafting
CLASSIFY_MODEL = "claude-haiku-4-5"   # enquiry / complaint / not_enquiry (Stage 3)

# USD per million tokens (input, output). Source: Anthropic price list, Sep 2026.
PRICES_USD_PER_MTOK = {
    EXTRACT_MODEL: (2.00, 10.00),
    CLASSIFY_MODEL: (1.00, 5.00),
}

# Fixed rate so cost numbers are reproducible between runs. Update by hand if it drifts.
AUD_PER_USD = 1.52
