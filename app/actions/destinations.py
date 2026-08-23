"""Official BIS destination URL constants for action handoffs.

These URLs are the authoritative channels users must be directed to.
This module must NOT be used to fake or simulate any transactional action
(e.g., HUID verification) — it only provides the destination for HANDOFF.
"""

# Official BIS CARE app — HUID/licence/R-number verification,
# consumer verification, complaints, Know Your Standards, etc.
BIS_CARE_APP_URL = "https://www.bis.gov.in/bis-apps/?lang=en"

# Official BIS hallmarking overview / consumer guidance page
BIS_HALLMARKING_INFO_URL = "https://www.bis.gov.in/hallmarking-overview/?lang=en"

# Official BIS Know Your Standard search
BIS_KNOW_YOUR_STANDARD_URL = "https://www.bis.gov.in/know-your-standard/?lang=en"

# Official BIS Main Site (fallback for unclassified queries)
BIS_MAIN_URL = "https://www.bis.gov.in/?lang=en"
