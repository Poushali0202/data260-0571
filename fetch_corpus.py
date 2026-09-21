import hashlib
import json
import re
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "corpus"
MANIFEST = ROOT / "reports" / "hw03" / "CORPUS_MANIFEST.json"
HEADERS = {"User-Agent": "data260-hw3-corpus-fetch/1.0 (student homework; python-requests)"}

WIKIPEDIA = [
    ("wikipedia_product_recall.txt", "Product recall"),
    ("wikipedia_fda_food_safety_modernization_act.txt", "FDA Food Safety Modernization Act"),
    ("wikipedia_food_safety_and_inspection_service.txt", "Food Safety and Inspection Service"),
    ("wikipedia_peanut_corporation_of_america.txt", "Peanut Corporation of America"),
    ("wikipedia_2008_canadian_listeriosis_outbreak.txt", "2008 Canadian listeriosis outbreak"),
    ("wikipedia_2006_spinach_e_coli_outbreak.txt", "2006 North American E. coli outbreak in spinach"),
    ("wikipedia_2011_germany_e_coli_outbreak.txt", "2011 Germany E. coli O104:H4 outbreak"),
    ("wikipedia_2022_infant_formula_shortage.txt", "2022 United States infant formula shortage"),
    ("wikipedia_global_supply_chain_crisis.txt", "2021-2023 global supply chain crisis"),
    ("wikipedia_cold_chain.txt", "Cold chain"),
    ("wikipedia_traceability.txt", "Traceability"),
    ("wikipedia_food_distribution.txt", "Food distribution"),
    ("wikipedia_grocery_store.txt", "Grocery store"),
]
FDA_PAGES = [
    ("fda_recalls_background_and_definitions.txt",
     "https://www.fda.gov/safety/industry-guidance-recalls/recalls-background-and-definitions"),
    ("fda_101_product_recalls.txt",
     "https://www.fda.gov/consumers/consumer-updates/fda-101-product-recalls"),
    ("fda_food_recalls_what_you_need_to_know.txt",
     "https://www.fda.gov/food/buy-store-serve-safe-food/food-recalls-what-you-need-know"),
    ("fda_fsma_food_traceability_rule.txt",
     "https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods"),
    ("fda_fsma_preventive_controls_human_food.txt",
     "https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-preventive-controls-human-food"),
    ("usda_ers_food_service_market_segments.txt",
     "https://www.ers.usda.gov/topics/food-markets-prices/food-service-industry/market-segments"),
]
ECFR_URL = "https://www.ecfr.gov/api/versioner/v1/full/2026-09-01/title-21.xml?part=7&subpart=C"
OPENFDA_URL = "https://api.fda.gov/food/enforcement.json"
OPENFDA_PARAMS = {"search": "report_date:[20250101 TO 20261231]", "sort": "report_date:desc", "limit": 100}


def clean(text):
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip() + "\n"


def wikipedia_article(title):
    url = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
    soup = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=60).text, "lxml")
    content = soup.select_one("#mw-content-text .mw-parser-output")
    for tag in content.select("table, .navbox, .reflist, .mw-editsection, sup, figure, .hatnote, .toc, style, .shortdescription, .sidebar, .metadata, .ambox, .thumb"):
        tag.decompose()
    lines = []
    for element in content.find_all(["h2", "h3", "p", "li"]):
        text = element.get_text(" ").strip()
        if element.name == "h2" and text in ("See also", "References", "Notes", "External links", "Further reading"):
            break
        if text:
            lines.append(text)
    return url, clean("\n\n".join(lines))


def html_page(url):
    soup = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=60).text, "lxml")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "aside", "form"]):
        tag.decompose()
    main = soup.find("main") or soup.body
    return clean(main.get_text("\n"))


def ecfr_subpart():
    response = requests.get(ECFR_URL, headers={**HEADERS, "Accept": "application/xml"}, timeout=60)
    return clean(BeautifulSoup(response.text, "xml").get_text("\n"))


def openfda_reports():
    results = requests.get(OPENFDA_URL, params=OPENFDA_PARAMS, headers=HEADERS, timeout=60).json()["results"]
    blocks = []
    for item in results:
        blocks.append("\n".join([
            f"Recall number: {item.get('recall_number')}",
            f"Recalling firm: {item.get('recalling_firm')} ({item.get('city')}, {item.get('state')})",
            f"Product: {item.get('product_description')}",
            f"Reason for recall: {item.get('reason_for_recall')}",
            f"Classification: {item.get('classification')}",
            f"Status: {item.get('status')}",
            f"Recall initiated: {item.get('recall_initiation_date')}, report date: {item.get('report_date')}",
            f"Product quantity: {item.get('product_quantity')}",
            f"Distribution: {item.get('distribution_pattern')}",
        ]))
    return "openFDA food enforcement reports, most recent 100 records reported since 2025-01-01.\n\n" + "\n\n".join(blocks) + "\n"


def save(name, url, text, manifest):
    path = CORPUS / name
    path.write_text(text, encoding="utf-8")
    data = path.read_bytes()
    manifest.append({
        "file": name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "source_url": url,
        "accessed": date.today().isoformat(),
    })
    print(f"{len(data):>7} bytes  {name}")


def main():
    CORPUS.mkdir(exist_ok=True)
    manifest = []
    for name, title in WIKIPEDIA:
        url, text = wikipedia_article(title)
        save(name, url, text, manifest)
        time.sleep(2)
    for name, url in FDA_PAGES:
        save(name, url, html_page(url), manifest)
        time.sleep(1)
    save("ecfr_21_cfr_part_7_subpart_c_recalls.txt", ECFR_URL, ecfr_subpart(), manifest)
    query = OPENFDA_URL + "?" + requests.compat.urlencode(OPENFDA_PARAMS)
    save("openfda_food_enforcement_reports.txt", query, openfda_reports(), manifest)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    total = sum(item["bytes"] for item in manifest)
    print(f"{len(manifest)} files, {total} bytes total, manifest written to {MANIFEST}")


if __name__ == "__main__":
    main()
