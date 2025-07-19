import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
import re
import os
import io

def extract_toc_entries(pages):
    toc_text = "".join(page.extract_text() or "" for page in pages)
    pattern = re.compile(r"#\d+:\s+(.*?):\s+(.*?Checklist.*?)\.{3,}\s+(\d+)", re.DOTALL)
    matches = pattern.findall(toc_text)
    entries = [(int(page_num) - 1, f"{title1.strip()} - {title2.strip()}") for title1, title2, page_num in matches]
    return entries

def split_pdf_by_toc(uploaded_files):
    readers = [PdfReader(f) for f in uploaded_files]
    all_pages = [page for reader in readers for page in reader.pages]

    # Find candidate TOC pages from the beginning of each file (pages 1–5)
    toc_entries = []
    for reader in readers:
        pages_to_check = reader.pages[1:6] if len(reader.pages) > 5 else reader.pages[1:]
        entries = extract_toc_entries(pages_to_check)
        if entries:
            toc_entries.extend(entries)

    if not toc_entries:
        return []

    split_ranges = []
    for i, (start, name) in enumerate(toc_entries):
        end = toc_entries[i + 1][0] if i + 1 < len(toc_entries) else len(all_pages)
        split_ranges.append((start, end, name))

    result_files = []
    for start, end, name in split_ranges:
        writer = PdfWriter()
        for page in all_pages[start:end]:
            writer.add_page(page)

        buffer = io.BytesIO()
        writer.write(buffer)
        buffer.seek(0)

        safe_name = re.sub(r'[\\/*?:"<>|]', "_", name.strip()) + ".pdf"
        result_files.append((safe_name, buffer))
    return result_files

st.title("ACC Build Checklist Splitter")
st.markdown("Upload all parts of the checklist report (e.g., Part 1, Part 2, etc.). This tool will extract the table of contents and split the file accordingly.")

uploaded_files = st.file_uploader("Upload All Report Parts (in order)", type="pdf", accept_multiple_files=True)

if uploaded_files and len(uploaded_files) >= 2:
    with st.spinner("Splitting checklists using TOC..."):
        results = split_pdf_by_toc(uploaded_files)

    if results:
        st.success(f"Successfully split into {len(results)} checklists!")
        for filename, filedata in results:
            st.download_button(label=f"Download {filename}", data=filedata, file_name=filename, mime="application/pdf")
    else:
        st.error("Could not find any TOC entries. Please make sure the TOC pages are included in the uploaded files.")

elif uploaded_files:
    st.warning("Please upload at least 2 files (e.g., Part 1, Part 2, ...)")
