import streamlit as st
from langchain.text_splitter import CharacterTextSplitter
import zipfile
from ebooklib import epub
from bs4 import BeautifulSoup
import tempfile
import os
import shutil

# Configuration
CHUNK_SIZE = 1950
CHUNK_OVERLAP = 10
LENGTH_FUNCTION_CHOICE = "Characters"
SPLITTER_CHOICE = "Character"
PREFIX = "translate following text from chinese to english\n"

# Initialize session state
if 'chapters' not in st.session_state:
    st.session_state.chapters = []
if 'processed_epub' not in st.session_state:
    st.session_state.processed_epub = None

def extract_epub_chapters(epub_content):
    """Extract chapters from EPUB"""
    chapters = []
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(epub_content)
        tmp_file_name = tmp_file.name
    try:
        book = epub.read_epub(tmp_file_name)
        for item in book.get_items():
            if item.get_type() == epub.EpubHtml or item.get_name().endswith('.xhtml'):
                content = item.get_content().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(content, 'html.parser')
                chapters.append(soup.get_text(separator="\n"))
    finally:
        os.unlink(tmp_file_name)
    return chapters

def extract_zip_chapters(zip_content):
    """Extract text files from ZIP as chapters"""
    chapters = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        with open(os.path.join(tmp_dir, 'temp.zip'), 'wb') as f:
            f.write(zip_content)
        with zipfile.ZipFile(os.path.join(tmp_dir, 'temp.zip')) as zip_ref:
            zip_ref.extractall(tmp_dir)
            for root, _, files in os.walk(tmp_dir):
                for file in sorted(files):
                    if file.endswith('.txt'):
                        with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                            chapters.append(f.read())
    return chapters

def create_processed_epub(split_chapters):
    """Create EPUB with split chapters"""
    book = epub.EpubBook()
    book.set_identifier('processed_epub')
    book.set_title('Processed Book')
    book.set_language('en')

    for chapter_idx, chunks in enumerate(split_chapters, 1):
        for part_idx, chunk in enumerate(chunks, 1):
            title = f'Chapter {chapter_idx} Part {part_idx}'
            file_name = f'chap_{chapter_idx}_{part_idx}.xhtml'
            
            chapter = epub.EpubHtml(title=title, file_name=file_name)
            chapter.content = f'<h1>{title}</h1><p>{chunk.replace("\n", "<br/>")}</p>'
            book.add_item(chapter)
    
    book.spine = [item for item in book.get_items() if isinstance(item, epub.EpubHtml)]
    return epub.write_epub('/tmp/processed.epub', book)

# UI Components
st.title("EPUB/TXT Processor")

uploaded_file = st.file_uploader("Upload EPUB or ZIP", type=["epub", "zip"])

if uploaded_file:
    file_type = uploaded_file.type
    file_bytes = uploaded_file.read()
    
    if file_type == 'application/epub+zip':
        st.session_state.chapters = extract_epub_chapters(file_bytes)
    elif file_type == 'application/zip':
        st.session_state.chapters = extract_zip_chapters(file_bytes)
    
    if st.session_state.chapters:
        st.success(f"Loaded {len(st.session_state.chapters)} chapters")

if st.button("Process and Package"):
    if not st.session_state.chapters:
        st.error("No chapters to process!")
    else:
        splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len
        )
        
        processed_chapters = []
        for chapter in st.session_state.chapters:
            splits = splitter.split_text(chapter)
            processed_chapters.append([PREFIX + s for s in splits])
        
        create_processed_epub(processed_chapters)
        with open('/tmp/processed.epub', 'rb') as f:
            st.download_button(
                label="Download Processed EPUB",
                data=f,
                file_name='processed.epub',
                mime='application/epub+zip'
            )