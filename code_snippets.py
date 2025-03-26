# Template for the CharacterTextSplitter
CHARACTER = """
from langchain.text_splitter import CharacterTextSplitter
splitter = CharacterTextSplitter(
    separator="\\n\\n",
    chunk_size={chunk_size},
    chunk_overlap={chunk_overlap},
    length_function={length_function}
)
"""

# Template for the RecursiveCharacterTextSplitter
RECURSIVE_CHARACTER = """
from langchain.text_splitter import RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(
    chunk_size={chunk_size},
    chunk_overlap={chunk_overlap},
    length_function={length_function}
)
"""

# Template for language-specific splitter using RecursiveCharacterTextSplitter.from_language
LANGUAGE = """
from langchain.text_splitter import RecursiveCharacterTextSplitter, Language
splitter = RecursiveCharacterTextSplitter.from_language(
    language="{language}",
    chunk_size={chunk_size},
    chunk_overlap={chunk_overlap},
    length_function={length_function}
)
"""

# String used to display the length function for characters.
CHARACTER_LENGTH = "len"

# String used to display the length function for tokens (placeholder).
TOKEN_LENGTH = "token_length_function"
