import os
import pysrt
import xml.etree.ElementTree as ET
from deepl import Translator
from .TargetLanguage import TargetLanguage

def srt_translate(srt_file: str, target_lang: TargetLanguage):
    """
    Takes the srt file and breaks it into sentences,
    maps the sentences to the range of timestamps and reverse indexes,
    translates the sentences using DeepL,
    and then maps the translated sentences back to the original timestamps but in order.

    Args:
        srt_file (str): Path to the original SRT file.
        target_lang (str): The target language code (e.g. 'JA' for Japanese).

    Returns:
        list: A list of translated sentences with their original timestamps.
    """
    try:
        check_deepl_quota()
        subs = validate_srt_file(srt_file)
        print(f"Translating {len(subs)} subtitles from {srt_file} to {target_lang}")

        sentences = break_into_sentences(subs)
        translated_sentences = translate_sentences(sentences, target_lang)
        translated_subs = map_sentences_back_split(sentences, translated_sentences)

        return translated_subs
    except SRTTranslationError as e:
        print(f"Translation error: {str(e)}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise SRTTranslationError(f"Translation failed: {str(e)}")
   


def break_into_sentences(subs):
    """
    Breaks SRT subtitles into complete sentences, accounting for common abbreviations.
    
    Args:
        subs: pysrt subtitles object.
    Returns:
        list: List of dicts containing:
              - text: concatenated sentence text.
              - indices: list of subtitle indices included in the sentence.
              - timestamps: list of (start, end) tuples for each subtitle.
    """
    # Common abbreviations that contain periods but don't end sentences
    abbreviations = {
        'etc.', 'e.g.', 'i.e.', 'vs.', 'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.',
        'Sr.', 'Jr.', 'Co.', 'Ltd.', 'Inc.', 'St.', 'Ave.', 'Ph.D.', 'U.S.',
        'U.K.', 'a.m.', 'p.m.', 'vol.', 'rev.', 'no.', 'p.', 'pp.'
    }
    
    # Add sentence end markers
    sentence_ends = ('.', '!', '?', '...', '…')
    
    sentences = []
    current_sentence = {
        'text': '',
        'indices': [],
        'timestamps': []
    }
    
    for sub in subs:
        text = sub.text.strip()
        
        # Skip empty subtitles
        if not text:
            continue
            
        if not current_sentence['indices']:
            current_sentence['indices'].append(sub.index)
            current_sentence['timestamps'].append((sub.start, sub.end))
        else:
            current_sentence['indices'].append(sub.index)
            current_sentence['timestamps'].append((sub.start, sub.end))
        
        # Handle ellipsis at start of text
        if text.startswith(('...', '…')) and current_sentence['text']:
            current_sentence['text'] = current_sentence['text'].rstrip() + '...'
        
        current_sentence['text'] += ' ' + text
        
        # Check for sentence end
        is_abbreviation = any(text.endswith(abbr) for abbr in abbreviations)
        ends_with_sentence = any(text.endswith(end) for end in sentence_ends)
        
        if ends_with_sentence and not is_abbreviation:
            # Handle quoted sentences
            if text.count('"') % 2 == 0:  # Even number of quotes
                current_sentence['text'] = current_sentence['text'].strip()
                sentences.append(current_sentence)
                current_sentence = {
                    'text': '',
                    'indices': [],
                    'timestamps': []
                }
            
    if current_sentence['text']:
        current_sentence['text'] = current_sentence['text'].strip()
        sentences.append(current_sentence)
        
    return sentences


def translate_sentences(sentences, target_lang):
    """
    Translates a list of sentences transformed into xml into a string.
    
    Args:
        sentences (list): List of dicts containing sentence text and timestamp ranges
        target_lang (str): The target language code (e.g. 'JA' for Japanese)

    Returns:
        text (str): The translated text.
    """
    # Instantiate the DeepL translator
    translator = Translator(os.environ["DEEPL_AUTH_KEY"])

    # Build proper XML with root element
    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<subtitles>"]
    
    # Add each sentence as a subtitle element, escaping special characters
    for sentence in sentences:
        # Escape special characters in the text
        cleaned_text = ' '.join(sentence['text'].split())
        escaped_text = (cleaned_text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))
        xml_parts.append(f"<subtitle id='{sentence['indices'][0]}'>{escaped_text}</subtitle>")
    
    xml_parts.append("</subtitles>")
    xml_string = "\n".join(xml_parts)

    # Translate all sentences at once
    translated_sentences = translator.translate_text(
        xml_string,
        target_lang=target_lang,
        tag_handling="xml",
        formality="prefer_less"
    )

    return translated_sentences.text


def split_text_into_chunks(text, n_chunks, m_chunks = 1):
    """
    Splits the text into n_chunks parts as evenly as possible by words.
    
    Args:
        text (str): The full text to split.
        n_chunks (int): The number of chunks to split into.
        m_chunks (int optional): The number of chunks in a time frame.
    Returns:
        list: A list of text chunks.
    """
    words = text.split()
    if n_chunks <= 0:
        return []
    if n_chunks == 1:
        return [text]
    
    total_words = len(words)
    base_chunk_size = total_words // n_chunks
    remainder = total_words % n_chunks
    
    chunks = []
    start = 0
    for i in range(n_chunks):
        # Allocate an extra word for the first 'remainder' chunks
        current_chunk_size = base_chunk_size + (1 if i < remainder else 0)
        chunk_words = words[start: start + current_chunk_size]
        chunks.append(" ".join(chunk_words))
        start += current_chunk_size
    return chunks


def map_sentences_back_split(sentences, translated_sentences_xml):
    """
    Maps the translated sentences back to individual subtitle chunks.
    If a sentence spans multiple subtitles (i.e., multiple indices),
    the function splits the translated text into evenly distributed chunks
    across those subtitles.
    
    Args:
        sentences (list): List of dicts with sentence details (including 'indices' and 'timestamps').
        translated_sentences_xml (str): The translated XML text.
    
    Returns:
        list: A list of dicts, each with 'text', 'start_time', and 'end_time' for the individual subtitle chunks.
    """
    # Parse the translated XML
    root = ET.fromstring(translated_sentences_xml)
    
    mapped_results = []
    for sentence in sentences:
        # Use the first subtitle index as reference for matching in the XML.
        if not sentence['indices']:
            continue
        ref_id = sentence['indices'][0]
        subtitle_elem = root.find(f"./subtitle[@id='{ref_id}']")
        if subtitle_elem is not None and subtitle_elem.text is not None:
            full_translated_text = subtitle_elem.text.strip()
            num_chunks = len(sentence['indices'])
            if num_chunks > 1:
                chunks = split_text_into_chunks(full_translated_text, num_chunks)
                # Fallback: if splitting fails unexpectedly.
                if len(chunks) != num_chunks:
                    chunks = [full_translated_text] * num_chunks
            else:
                chunks = [full_translated_text]
            
            # Map chunks to corresponding subtitle timestamps.
            for idx, chunk in enumerate(chunks):
                # Safely get the corresponding timestamp.
                if idx < len(sentence['timestamps']):
                    start_time, end_time = sentence['timestamps'][idx]
                else:
                    start_time, end_time = sentence['timestamps'][0]
                    
                mapped_results.append({
                    'text': chunk,
                    'start_time': start_time,
                    'end_time': end_time
                })
        else:
            print(f"Warning: No translated text found for subtitle starting at index {sentence['indices'][0]}")
            
    return mapped_results


class SRTTranslationError(Exception):
    """Custom exception for SRT translation errors"""
    pass


def check_deepl_quota():
    """
    Checks DeepL API usage and limits.
    
    Raises:
        SRTTranslationError: If API quota is exceeded or close to limit
    """
    try:
        translator = Translator(os.environ.get("DEEPL_AUTH_KEY"))
        usage = translator.get_usage()
        if usage.character.limit_reached:
            raise SRTTranslationError("DeepL API character limit reached")
        
        # Warning if using more than 90% of quota
        if usage.character.count / usage.character.limit > 0.9:
            print(f"Warning: DeepL API usage at {usage.character.count}/{usage.character.limit} characters")
    except Exception as e:
        raise SRTTranslationError(f"Failed to check DeepL API quota: {str(e)}")


def validate_srt_file(srt_file):
    """
    Validates the SRT file exists and is properly formatted.
    
    Args:
        srt_file (str): Path to the SRT file
    Raises:
        SRTTranslationError: If file is invalid or improperly formatted
    """
    if not os.path.exists(srt_file):
        raise SRTTranslationError(f"SRT file not found: {srt_file}")
    
    try:
        subs = pysrt.open(srt_file)
        if len(subs) == 0:
            raise SRTTranslationError(f"SRT file is empty: {srt_file}")
        return subs
    except pysrt.Error as e:
        raise SRTTranslationError(f"Invalid SRT format: {str(e)}")