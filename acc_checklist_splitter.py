import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
import re
import os
import io
import zipfile
from datetime import datetime
import pandas as pd

def extract_toc_entries(pages):
    toc_text = "".join(page.extract_text() or "" for page in pages)
    pattern = re.compile(r"#\d+:\s+(.*?):\s+(.*?Checklist.*?)\.{3,}\s+(\d+)", re.DOTALL)
    matches = pattern.findall(toc_text)
    entries = [(int(page_num) - 1, f"{title1.strip()} - {title2.strip()}", page_num) for title1, title2, page_num in matches]
    return entries

def split_pdf_by_toc(uploaded_files):
    readers = [PdfReader(f) for f in uploaded_files]
    all_pages = [page for reader in readers for page in reader.pages]

    toc_entries = []
    for reader in readers:
        pages_to_check = reader.pages[1:6] if len(reader.pages) > 5 else reader.pages[1:]
        entries = extract_toc_entries(pages_to_check)
        if entries:
            toc_entries.extend(entries)

    if not toc_entries:
        return None, None, None, None

    split_ranges = []
    for i, (start, name, page_str) in enumerate(toc_entries):
        end = toc_entries[i + 1][0] if i + 1 < len(toc_entries) else len(all_pages)
        split_ranges.append((start, end, name, page_str))

    zip_buffer = io.BytesIO()
    manifest_data = []
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for start, end, name, page_str in split_ranges:
            writer = PdfWriter()
            for page in all_pages[start:end]:
                writer.add_page(page)

            buffer = io.BytesIO()
            writer.write(buffer)
            buffer.seek(0)

            safe_name = re.sub(r'[\\/*?:"<>|]', "_", name.strip()) + ".pdf"
            zipf.writestr(safe_name, buffer.read())
            manifest_data.append({"Checklist Name": name, "Start Page": page_str, "File Name": safe_name})
    zip_buffer.seek(0)
    return zip_buffer, manifest_data, len(split_ranges), toc_entries[0][1] if toc_entries else "checklists"

st.title("ACC Build Checklist Splitter")
st.markdown("Upload all parts of the checklist report (e.g., Part 1, Part 2, etc.). This tool will extract the table of contents and split the file accordingly into one ZIP.")

uploaded_files = st.file_uploader("Upload All Report Parts (in order)", type="pdf", accept_multiple_files=True)

if uploaded_files and len(uploaded_files) >= 2:
    with st.spinner("Splitting checklists using TOC and building ZIP..."):
        zip_data, manifest_data, count, project_prefix = split_pdf_by_toc(uploaded_files)

    if zip_data and manifest_data:
        today_str = datetime.now().strftime("%Y-%m-%d")
        zip_filename = f"{project_prefix.split()[0]}_checklists_{today_str}.zip"

        st.download_button("📦 Download All Checklists as ZIP", data=zip_data.getvalue(), file_name=zip_filename, mime="application/zip")

        st.success(f"Successfully split into {count} checklists!")

        st.markdown("### 📋 Manifest of Checklists")
        manifest_df = pd.DataFrame(manifest_data)
        st.dataframe(manifest_df, use_container_width=True)
    else:
        st.error("No checklists could be extracted from the uploaded files.")

elif uploaded_files:
    st.warning("Please upload at least 2 files (e.g., Part 1, Part 2, ...)")
