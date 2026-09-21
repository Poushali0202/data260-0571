# Corpus sources (DOMAIN_ID 3: grocery supply and recall notices)

All files in `corpus/` are plain-text snapshots written by `python fetch_corpus.py` on 2026-09-21.
Wikipedia articles were fetched as HTML and reduced to their headings, paragraphs and list items
(tables, infoboxes, references and navigation removed). FDA and USDA ERS pages keep the text of the
page's main element. The eCFR file is the text of 21 CFR Part 7 Subpart C (recalls) from the eCFR
versioner API as of 2026-09-01. The openFDA file holds the 100 most recent food enforcement reports
with a report date from 2025-01-01 on, one block per record. Byte sizes and SHA-256 hashes of every
file are in `CORPUS_MANIFEST.json`.

| Local file | Source URL | Accessed | Bytes |
|---|---|---|---|
| wikipedia_product_recall.txt | https://en.wikipedia.org/wiki/Product_recall | 2026-09-21 | 54940 |
| wikipedia_fda_food_safety_modernization_act.txt | https://en.wikipedia.org/wiki/FDA_Food_Safety_Modernization_Act | 2026-09-21 | 33890 |
| wikipedia_food_safety_and_inspection_service.txt | https://en.wikipedia.org/wiki/Food_Safety_and_Inspection_Service | 2026-09-21 | 11984 |
| wikipedia_peanut_corporation_of_america.txt | https://en.wikipedia.org/wiki/Peanut_Corporation_of_America | 2026-09-21 | 8135 |
| wikipedia_2008_canadian_listeriosis_outbreak.txt | https://en.wikipedia.org/wiki/2008_Canadian_listeriosis_outbreak | 2026-09-21 | 5418 |
| wikipedia_2006_spinach_e_coli_outbreak.txt | https://en.wikipedia.org/wiki/2006_North_American_E._coli_outbreak_in_spinach | 2026-09-21 | 8985 |
| wikipedia_2011_germany_e_coli_outbreak.txt | https://en.wikipedia.org/wiki/2011_Germany_E._coli_O104:H4_outbreak | 2026-09-21 | 16539 |
| wikipedia_2022_infant_formula_shortage.txt | https://en.wikipedia.org/wiki/2022_United_States_infant_formula_shortage | 2026-09-21 | 27557 |
| wikipedia_global_supply_chain_crisis.txt | https://en.wikipedia.org/wiki/2021-2023_global_supply_chain_crisis | 2026-09-21 | 7844 |
| wikipedia_cold_chain.txt | https://en.wikipedia.org/wiki/Cold_chain | 2026-09-21 | 7890 |
| wikipedia_traceability.txt | https://en.wikipedia.org/wiki/Traceability | 2026-09-21 | 9310 |
| wikipedia_food_distribution.txt | https://en.wikipedia.org/wiki/Food_distribution | 2026-09-21 | 16900 |
| wikipedia_grocery_store.txt | https://en.wikipedia.org/wiki/Grocery_store | 2026-09-21 | 23954 |
| fda_recalls_background_and_definitions.txt | https://www.fda.gov/safety/industry-guidance-recalls/recalls-background-and-definitions | 2026-09-21 | 1369 |
| fda_101_product_recalls.txt | https://www.fda.gov/consumers/consumer-updates/fda-101-product-recalls | 2026-09-21 | 6251 |
| fda_food_recalls_what_you_need_to_know.txt | https://www.fda.gov/food/buy-store-serve-safe-food/food-recalls-what-you-need-know | 2026-09-21 | 3782 |
| fda_fsma_food_traceability_rule.txt | https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods | 2026-09-21 | 37566 |
| fda_fsma_preventive_controls_human_food.txt | https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-preventive-controls-human-food | 2026-09-21 | 14165 |
| usda_ers_food_service_market_segments.txt | https://www.ers.usda.gov/topics/food-markets-prices/food-service-industry/market-segments | 2026-09-21 | 8645 |
| ecfr_21_cfr_part_7_subpart_c_recalls.txt | https://www.ecfr.gov/api/versioner/v1/full/2026-09-01/title-21.xml?part=7&subpart=C | 2026-09-21 | 19297 |
| openfda_food_enforcement_reports.txt | https://api.fda.gov/food/enforcement.json?search=report_date%3A%5B20250101+TO+20261231%5D&sort=report_date%3Adesc&limit=100 | 2026-09-21 | 69543 |

Total: 21 files, 393964 bytes.
