from playwright.sync_api import sync_playwright
import pandas as pd
import time
import random
import os


def scrape_cars_and_bids_large_scale():
    target_count = 3000
    data = []
    already_scraped_urls = set()

    # 1. Load existing data to resume if it exists
    if os.path.exists("cars_bids_backup.csv"):
        print("--- Found existing backup. Loading progress... ---")
        df_old = pd.read_csv("cars_bids_backup.csv")
        already_scraped_urls = set(df_old['url'].tolist())
        data = df_old.to_dict('records')
        print(f"Resuming from {len(data)} items...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to True for faster, stable performance
        page = browser.new_page()

        print("--- Step 1: Collecting auction links ---")
        page.goto("https://carsandbids.com/past-auctions")

        auction_links = set()

        # Keep scrolling until we have enough, or we hit the site limit
        while len(auction_links) < target_count:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)

            cards = page.query_selector_all("a[href^='/auctions/']")
            for card in cards:
                href = card.get_attribute("href")
                if href and "/auctions/" in href:
                    auction_links.add("https://carsandbids.com" + href)

            current_count = len(auction_links)
            print(f"Found {current_count} links so far...")

            # If we haven't grown in a while, break
            if len(auction_links) >= target_count:
                break

        links_to_scrape = [url for url in auction_links if url not in already_scraped_urls]
        print(f"Total links to scrape: {len(links_to_scrape)}")

        # 2. Scrape each auction
        for i, url in enumerate(links_to_scrape):
            print(f"[{i + 1}/{len(links_to_scrape)}] Scraping: {url}")
            try:
                page.goto(url)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(random.uniform(1.0, 2.0))

                car_info = {"url": url, "title": "N/A", "auction_date": "N/A"}

                # ... (Keep your extraction logic here) ...
                title_el = page.query_selector("h1")
                car_info["title"] = title_el.inner_text().strip() if title_el else "N/A"

                quick_facts = page.query_selector("div.quick-facts")
                if quick_facts:
                    dts = quick_facts.query_selector_all("dt")
                    dds = quick_facts.query_selector_all("dd")
                    for dt, dd in zip(dts, dds):
                        key = dt.inner_text().strip().lower().replace(" ", "_")
                        car_info[key] = dd.inner_text().strip().replace("\nSave", "")

                bid_stats = page.query_selector("ul.bid-stats")
                if bid_stats:
                    for li in bid_stats.query_selector_all("li"):
                        spans = li.query_selector_all("span")
                        if len(spans) >= 2:
                            key = spans[0].inner_text().strip().lower().replace(" ", "_")
                            if any(char.isdigit() for char in key) and "/" in key: continue
                            car_info[key] = spans[1].inner_text().strip().replace("$", "").replace(",", "")

                date_element = page.query_selector("p.end-time")
                if date_element:
                    car_info["auction_date"] = date_element.inner_text().strip()

                data.append(car_info)

                # Save every 20 items to minimize data loss
                if len(data) % 20 == 0:
                    pd.DataFrame(data).to_csv("cars_bids_backup.csv", index=False)

            except Exception as e:
                print(f"Error scraping {url}: {e}")
                continue

        pd.DataFrame(data).to_csv("cars_bids_final_3000.csv", index=False)
        print("Success! Saved final CSV.")
        browser.close()


if __name__ == "__main__":
    scrape_cars_and_bids_large_scale()