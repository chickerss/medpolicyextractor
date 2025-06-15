import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
import pandas as pd

st.set_page_config(page_title="PDF Link Extractor", layout="centered")
st.title("🔗 PDF Link Extractor")

st.markdown("Enter a webpage URL to extract all linked **PDF files** along with their titles.")

# User input
user_url = st.text_input("🌐 Enter URL", placeholder="https://example.com/page")

@st.cache_data(show_spinner=False)
def extract_pdfs(page_url):
    try:
        response = requests.get(page_url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        pdf_items = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                title = a.get_text(strip=True) or "Untitled"
                full_link = urllib.parse.urljoin(page_url, href)
                pdf_items.append({"Title": title, "Link": full_link})

        return pd.DataFrame(pdf_items)
    except Exception as e:
        st.error(f"Error fetching data from URL: {e}")
        return pd.DataFrame(columns=["Title", "Link"])

# Extract button
if st.button("🔍 Extract PDFs"):
    if user_url:
        with st.spinner("Extracting PDF links..."):
            df = extract_pdfs(user_url)
            if not df.empty:
                st.success(f"Found {len(df)} PDF(s).")
                st.dataframe(df, use_container_width=True)

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download CSV", data=csv, file_name="pdf_links.csv", mime="text/csv")
            else:
                st.warning("No PDF links found on the page.")
    else:
        st.warning("Please enter a valid URL first.")
