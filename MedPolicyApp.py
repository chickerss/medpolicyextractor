import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
import pandas as pd
import re
import fitz  # PyMuPDF

st.set_page_config(page_title="Medical Policy Scraper", layout="centered")
st.title("🏥 Medical Policy Code Extractor")

user_input = st.text_area("Enter one or more URLs (comma or newline separated):", height=150)
skip_pdf = st.checkbox("🚫 Skip PDF crawling", value=False)

# Regex patterns
CPT_PATTERN = r'\b\d{5}\b'
HCPCS_PATTERN = r'\b[A-Z]\d{4}\b'
PLA_PATTERN = r'\b\d{4}U\b'

@st.cache_data(show_spinner=False)
def get_links(url):
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        links = []

        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            full_url = urllib.parse.urljoin(url, href)

            is_pdf = href.lower().endswith(".pdf")
            is_policy = "policy" in href.lower() or "activepolicypage" in href.lower()

            if is_pdf or is_policy:
                links.append({
                    "Title": text or "Untitled",
                    "Link": full_url,
                    "Source URL": url,
                    "Type": "PDF" if is_pdf else "HTML"
                })

        return links
    except Exception as e:
        st.error(f"Error fetching {url}: {e}")
        return []

def extract_codes(text):
    codes = []
    for pattern, label in [(CPT_PATTERN, "CPT"), (HCPCS_PATTERN, "HCPCS"), (PLA_PATTERN, "PLA")]:
        found = re.findall(pattern, text)
        for code in set(found):
            codes.append((label, code))
    return codes

def extract_from_pdf(url):
    try:
        response = requests.get(url, timeout=15)
        with open("temp.pdf", "wb") as f:
            f.write(response.content)
        with fitz.open("temp.pdf") as doc:
            text = " ".join(page.get_text() for page in doc)
        return extract_codes(text)
    except Exception:
        return []

def extract_from_html(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return extract_codes(text)
    except Exception:
        return []

if st.button("🔍 Start Extraction"):
    urls = [u.strip() for u in user_input.replace(",", "\n").splitlines() if u.strip()]
    if not urls:
        st.warning("Please enter at least one URL.")
    else:
        all_links = []
        code_index = []

        with st.spinner("Scraping and parsing..."):
            for url in urls:
                found_links = get_links(url)
                all_links.extend(found_links)

                for link in found_links:
                    if link["Type"] == "PDF" and skip_pdf:
                        continue

                    if link["Type"] == "PDF":
                        codes = extract_from_pdf(link["Link"])
                    else:
                        codes = extract_from_html(link["Link"])

                    for code_type, code in codes:
                        code_index.append({
                            "Policy Title": link["Title"],
                            "Code Type": code_type,
                            "Code": code,
                            "Policy URL": link["Link"],
                            "Source URL": link["Source URL"]
                        })

        # Show link table
        link_df = pd.DataFrame(all_links)
        st.subheader("🔗 Extracted Links")
        st.dataframe(link_df, use_container_width=True)
        csv_links = link_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Link Table", csv_links, "policy_links.csv", "text/csv")

        # Show code index table
        if code_index:
            code_df = pd.DataFrame(code_index).sort_values(by=["Policy Title", "Code Type", "Code"])
            st.subheader("📑 CPT / HCPCS / PLA Code Index")
            st.dataframe(code_df, use_container_width=True)
            csv_codes = code_df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Code Index", csv_codes, "code_index.csv", "text/csv")
        else:
            st.info("No CPT, HCPCS, or PLA codes found.")
