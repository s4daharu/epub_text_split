import streamlit as st
from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from ebooklib import epub
from bs4 import BeautifulSoup
import tempfile
import os
import zipfile
import re

# Configuration
CHUNK_SIZE = 1950
CHUNK_OVERLAP = 10
PREFIX = "translate following text from chinese to english\n"

# Session state
if 'chapters' not in st.session_state:
    st.session_state.chapters = []
if 'processed_epub' not in st.session_state:
    st.session_state.processed_epub = None

def extract_epub_chapters(epub_content):
    """Extract chapters from EPUB with multiple encoding support"""
    chapters = []
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(epub_content)
        tmp_file_name = tmp_file.name
    try:
        book = epub.read_epub(tmp_file_name)
        for item in book.get_items():
            if isinstance(item, epub.EpubHtml):
                content = item.get_content()
                for encoding in ['utf-8', 'gb18030', 'latin-1']:
                    try:
                        text = content.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                soup = BeautifulSoup(text, 'html.parser')
                chapters.append(soup.get_text(separator="\n"))
    finally:
        os.unlink(tmp_file_name)
    return chapters

def extract_zip_chapters(zip_content):
    """Extract and numerically sort text files from ZIP"""
    chapters = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        with open(os.path.join(tmp_dir, 'temp.zip'), 'wb') as f:
            f.write(zip_content)
        with zipfile.ZipFile(os.path.join(tmp_dir, 'temp.zip')) as zip_ref:
            zip_ref.extractall(tmp_dir)
            files = []
            for root, _, filenames in os.walk(tmp_dir):
                for filename in filenames:
                    if filename.endswith('.txt'):
                        match = re.match(r'^(\d+)', filename)
                        if match:
                            num = int(match.group(1))
                            files.append((num, os.path.join(root, filename)))
            files.sort(key=lambda x: x[0])
            for _, file_path in files:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    chapters.append(f.read())
    return chapters

def create_processed_epub(split_chapters):
    """Generate EPUB with X.Y chapter labeling"""
    book = epub.EpubBook()
    book.set_identifier('processed_epub')
    book.set_title('Processed Book')
    book.set_language('en')

    for chapter_num, chunks in enumerate(split_chapters, 1):
        for part_num, chunk in enumerate(chunks, 1):
            title = f'{chapter_num}.{part_num}'
            file_name = f'chap_{chapter_num}_{part_num}.xhtml'
            
            epub_chapter = epub.EpubHtml(title=title, file_name=file_name)
            epub_chapter.content = f'<h1>{title}</h1><p>{chunk.replace("\n", "<br/>")}</p>'
            book.add_item(epub_chapter)
    
    book.spine = [item for item in book.get_items() if isinstance(item, epub.EpubHtml)]
    epub_path = os.path.join(tempfile.gettempdir(), 'processed.epub')
    epub.write_epub(epub_path, book)
    return epub_path

# UI Components
st.title("EPUB/ZIP Translation Processor")

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
        
        epub_path = create_processed_epub(processed_chapters)
        with open(epub_path, 'rb') as f:
            st.download_button(
                label="Download Processed EPUB",
                data=f,
                file_name='processed.epub',
                mime='application/epub+zip'
            )
        os.unlink(epub_path)