import streamlit as st
import io, zipfile, tempfile, os, re
from ebooklib import epub
from bs4 import BeautifulSoup
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter

# -------------------------
# Configuration
# -------------------------
CHUNK_SIZE = 1950
CHUNK_OVERLAP = 10
LENGTH_FUNCTION_CHOICE = "Characters"  # Options: "Characters" or "Tokens"
SPLITTER_CHOICE = "Character"           # Options: "Character", "RecursiveCharacter", or "Language.English"
PREFIX = "translate following text from chinese to english\n"

if LENGTH_FUNCTION_CHOICE == "Characters":
    length_function = len
else:
    enc = tiktoken.get_encoding("cl100k_base")
    def length_function(text: str) -> int:
        return len(enc.encode(text))

# -------------------------
# Helpers for Natural Sorting
# -------------------------
def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    return [atoi(c) for c in re.split(r'(\d+)', text)]

# -------------------------
# Chapter Extraction Functions
# -------------------------
def extract_chapters_from_epub(epub_content):
    chapters = []
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(epub_content)
        tmp_name = tmp.name
    try:
        book = epub.read_epub(tmp_name)
        for item in book.get_items():
            if item.get_type() == epub.EpubHtml or item.get_name().endswith('.xhtml'):
                try:
                    content = item.get_content().decode('utf-8')
                except Exception:
                    try:
                        content = item.get_content().decode('gb18030')
                    except Exception:
                        content = item.get_content().decode('latin-1', errors='ignore')
                chapters.append(BeautifulSoup(content, 'html.parser').get_text(separator="\n"))
    finally:
        os.unlink(tmp_name)
    return chapters

def extract_chapters_from_zip(zip_bytes):
    chapters = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        txt_files = sorted([f for f in z.namelist() if f.lower().endswith('.txt')], key=natural_keys)
        for filename in txt_files:
            with z.open(filename) as f:
                try:
                    content = f.read().decode('utf-8')
                except Exception:
                    content = f.read().decode('latin-1', errors='ignore')
                chapters.append(content)
    return chapters

# -------------------------
# Text Splitting Function
# -------------------------
def split_text(text):
    if SPLITTER_CHOICE == "Character":
        splitter = CharacterTextSplitter(
            separator="\n\n",
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=length_function
        )
    elif SPLITTER_CHOICE == "RecursiveCharacter":
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=length_function
        )
    elif "Language." in SPLITTER_CHOICE:
        language = SPLITTER_CHOICE.split(".")[1].lower()
        splitter = RecursiveCharacterTextSplitter.from_language(
            language=language,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=length_function
        )
    return [PREFIX + s for s in splitter.split_text(text)]

# -------------------------
# EPUB Packaging Function
# -------------------------
def build_epub(split_chapters):
    book = epub.EpubBook()
    book.set_identifier("id123456")
    book.set_title("Processed Book")
    book.set_language("en")
    book.add_author("Processed via Streamlit App")
    
    epub_items = []
    for chap_index, chapter_chunks in enumerate(split_chapters, start=1):
        for part_index, chunk in enumerate(chapter_chunks, start=1):
            label = f"{chap_index}.{part_index}"
            c = epub.EpubHtml(title=label, file_name=f"chap_{chap_index}_{part_index}.xhtml", lang="en")
            c.content = f"<h1>{label}</h1><p>{chunk.replace(chr(10), '<br/>')}</p>"
            book.add_item(c)
            epub_items.append(c)
    
    book.toc = tuple(epub_items)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + epub_items
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp:
        epub.write_epub(tmp.name, book, {})
        tmp.seek(0)
        epub_bytes = tmp.read()
    os.unlink(tmp.name)
    return epub_bytes

# -------------------------
# Streamlit Interface
# -------------------------
st.title("Long Epub Splitter")
uploaded_file = st.file_uploader("Upload an EPUB or ZIP (of TXT chapters) file", type=["epub", "zip"])

if uploaded_file:
    file_bytes = uploaded_file.read()
    if uploaded_file.name.lower().endswith(".epub"):
        chapters = extract_chapters_from_epub(file_bytes)
    else:
        chapters = extract_chapters_from_zip(file_bytes)
    st.success(f"Loaded {len(chapters)} chapters.")
    if chapters:
        st.text_area("First Chapter Preview", value=chapters[0], height=200)
    
    if st.button("Generate Processed EPUB"):
        all_split = [split_text(ch) for ch in chapters]
        epub_bytes = build_epub(all_split)
        st.download_button("Download Processed EPUB",
                           data=epub_bytes,
                           file_name="processed_book.epub",
                           mime="application/epub+zip")
