import streamlit as st
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
from ebooklib import epub
from bs4 import BeautifulSoup
import tempfile
import os
import re

# Session state initialization
if 'chapters' not in st.session_state:
    st.session_state.chapters = []
if 'chapter_index' not in st.session_state:
    st.session_state.chapter_index = 0

# Configuration settings in sidebar
with st.sidebar:
    st.header("Processing Settings")
    CHUNK_SIZE = st.number_input("Chunk Size", min_value=100, value=1950)
    CHUNK_OVERLAP = st.number_input("Chunk Overlap", min_value=0, value=10)
    SPLITTER_CHOICE = st.selectbox("Splitter Type", ["Character", "RecursiveCharacter"])
    LENGTH_FUNCTION = st.selectbox("Length Metric", ["Characters", "Tokens"])

def extract_chapters(epub_content):
    """Extract chapters from EPUB with improved error handling"""
    chapters = []
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(epub_content)
        tmp_file_name = tmp_file.name

    try:
        book = epub.read_epub(tmp_file_name)
        for item in book.get_items():
            if isinstance(item, epub.EpubHtml):
                content = item.get_content()
                # Try multiple encodings
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

def get_token_length(text):
    """Calculate token length using cl100k_base encoding"""
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

# File upload and processing
uploaded_file = st.file_uploader("Upload EPUB", type=["epub"])

if uploaded_file:
    st.session_state.chapters = extract_chapters(uploaded_file.read())
    st.session_state.chapter_index = 0

if st.session_state.chapters:
    # Chapter navigation
    chapter_numbers = list(range(1, len(st.session_state.chapters)+1))
    selected_chapter = st.selectbox("Chapter", chapter_numbers, 
                                   index=st.session_state.chapter_index)
    st.session_state.chapter_index = selected_chapter - 1

    # Navigation buttons
    prev_col, next_col = st.columns(2)
    with prev_col:
        if st.button("← Previous", disabled=(st.session_state.chapter_index == 0)):
            st.session_state.chapter_index -= 1
            st.rerun()
    with next_col:
        if st.button("Next →", disabled=(st.session_state.chapter_index == len(stapters)-1)):
            st.session_state.chapter_index += 1
            st.rerun()

    # Chapter display
    current_chapter = st.session_state.chapters[st.session_state.chapter_index]
    st.text_area(f"Chapter {selected_chapter}", current_chapter, height=300)

    # Splitting controls
    if st.button("Process Chapter"):
        # Determine length function
        length_function = len if LENGTH_FUNCTION == "Characters" else get_token_length

        # Create splitter
        if SPLITTER_CHOICE == "Character":
            splitter = CharacterTextSplitter(
                separator="\n",
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
                length_function=length_function
            )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
                length_function=length_function
            )

        # Process and display chunks
        chunks = splitter.split_text(current_chapter)
        for idx, chunk in enumerate(chunks, 1):
            prefixed_chunk = f"translate following text from chinese to english\n{chunk}"
            st.text_area(f"Chunk {idx}", prefixed_chunk, height=150, key=f"chunk_{idx}")
            st.button(f"Copy Chunk {idx}", key=f"copy_{idx}",
                      on_click=lambda c=prefixed_chunk: st.session_state.update(copy=c))

        # Clipboard handling
        if "copy" in st.session_state:
            st.experimental_set_query_params(text=st.session_state.copy)
            del st.session_state["copy"]

else:
    st.info("Upload an EPUB file to begin")