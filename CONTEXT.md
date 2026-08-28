# Performance Registry Fetch — Context

Pulls AMFI's fund-performance dataset and writes
`{data_root}/reference/performance_data.csv`. That file is the platform's
authority for the **canonical display name** of a scheme — and, since
2026-08, for that alone.

## Glossary

### Performance Dataset
AMFI's scheme-performance publication, retrieved from the polling API behind
`amfiindia.com/polling/amfi/fund-performance`. One row per scheme carrying its
returns, AUM and classification for a single **Report Date**.

Assembled by walking every **Maturity Type × Category × Subcategory**
combination — the API has no "give me everything" call, so the full dataset is
the union of those requests.
_Avoid_: "the AMFI file" (NAVAll is also an AMFI file), "returns data"
(the names and classification matter more here than the returns)

### Canonical Display Name
The scheme name as it should be **shown to a human**, and the reason this
context is tier-1 rather than a returns feed. AMFI curates these names for
publication, which makes them the cleanest spelling of a fund available to the
platform.

**This context does not own scheme identity.** Identity — `scheme_code`, AMC,
active/inactive and renames — belongs to `sdi-fetcher`'s registry. ADR-0006
originally granted `performance_data.csv` both roles; that was amended by
[mf-ui-and-db ADR-0008](../mf-ui-and-db/docs/adr/0008-scheme-identity-on-scheme-code.md),
which splits them. A display name is a label; identity is what survives the
label changing.
_Avoid_: "canonical name" unqualified (say *display* name — the distinction is
the whole point), "master name", treating this file as an identity source

### Report Date
The business day the dataset describes. Chosen by asking AMFI for its current
report date, then walking **backwards** day by day past reporting holidays
until a published one is found.

The dataset is a snapshot at this date, not a range: re-pulling replaces, never
appends.
_Avoid_: "as-of date", "run date" (the day it was fetched is not this)

### Reporting Holiday
A day AMFI publishes no performance data. Detected by asking, not by a
calendar — market holidays and AMFI's publication schedule are not the same
set, and a hardcoded calendar would rot annually.
_Avoid_: "market holiday", "non-trading day"

### Maturity Type / Category / Subcategory
AMFI's three-level classification, and the loop that assembles the dataset:
open/close-ended, then the broad class (Equity, Debt, Hybrid…), then the SEBI
subcategory (Large Cap, Liquid…).

Stamped onto every row as it is fetched, because the API returns rows that do
not carry their own classification — it is knowable only from which request
they answered.
_Avoid_: "SEBI category" here (that is `sebi_category`, which `sdi-fetcher`
extracts from the SID document — a different source with different spellings)

### Scheme Universe
The set of schemes this dataset covers, and the platform's practical answer to
"which funds exist". Broader than what the pipeline has portfolio data for, so
it is the honest **denominator** when measuring coverage — measuring against
the ingested set instead reports a truncated universe as full coverage.
_Avoid_: "all schemes" (AMFI publishes performance only for schemes it
classifies; NAVAll's plan universe is wider still)

## Relationships

- One **Report Date** per pull; a re-pull for the same date is a replacement
- Every row carries the **Maturity Type / Category / Subcategory** it was
  fetched under — the row cannot report its own classification
- **Canonical Display Name** is this context's; **identity** is
  `sdi-fetcher`'s. The two are joined by ISIN or `scheme_code`, never by
  assuming one authority owns both
- Liveness is `navall/`'s, not this context's — a scheme can appear here and
  have stopped trading

## Boundaries

Fetch and write. This context makes no identity claim, resolves no name against
another source, and has no opinion on whether a scheme is still trading. Its
one job is to hand the platform AMFI's own spelling of each fund, dated.
