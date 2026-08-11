# Data Layout

`processed/minimal_etl/` contains the committed graph export, disease search list, signal list, overlap ledger, and summary used by the frontend.

`raw/orange_book/` contains the manually downloaded FDA EOBZIP files used for approved-use evidence. FDA bot protection prevents reliable automated downloading, so refreshing these files is a documented manual step.

The large raw API response directories are intentionally ignored by Git. They are reproducible caches, not the source of truth for the checked-in demo. The ETL scripts in `scripts/` can recreate them when the relevant APIs are available.

Source data remains subject to the terms of its original provider. The repository's code and reports do not relicense upstream source data.
