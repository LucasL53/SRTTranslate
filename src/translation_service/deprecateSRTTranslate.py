import os
import pysrt
import xml.etree.ElementTree as ET
from deepl import Translator
def deprecated_srt_translate_xml(srt_file, target_lang):
    """
    Translates an SRT file by sending its contents as an XML document
    to DeepL (with tag handling enabled), then mapping the translated
    text back to the original subtitle time frames.

    Args:
        srt_file (str): Path to the original SRT file.
        target_lang (str): The target language code (e.g. 'JA' for Japanese).
    """
    # Open the SRT file
    subs = pysrt.open(srt_file)

    # Build an XML string wrapping each subtitle.
    # We use the subtitle index as an id attribute.
    xml_parts = ["<subtitles>"]
    for sub in subs:
        # You might want to further escape or clean the text if needed.
        # Here we assume the subtitle text does not contain problematic XML characters.
        xml_parts.append(f'<subtitle id="{sub.index}">{sub.text}</subtitle>')
    xml_parts.append("</subtitles>")
    xml_string = "\n".join(xml_parts)

    # Instantiate the DeepL translator
    translator = Translator(os.environ["DEEPL_AUTH_KEY"])

    # Send the XML string for translation.
    # Note: The additional parameter tag_handling="xml" instructs DeepL to keep the XML structure.
    translated_xml = translator.translate_text(
        xml_string, target_lang=target_lang, tag_handling="xml", formality="prefer_less"
    ).text

    # Parse the translated XML
    root = ET.fromstring(translated_xml)
    # save the translated XML to a file
    with open("translated.xml", "w", encoding="utf-8") as f:
        f.write(translated_xml)

    # For each subtitle in the original SRT file, locate the corresponding
    # <subtitle> element in the translated XML and update its text.
    for sub in subs:
        # Find the XML element with the corresponding id
        subtitle_elem = root.find(f"./subtitle[@id='{sub.index}']")
        if subtitle_elem is not None and subtitle_elem.text is not None:
            sub.text = subtitle_elem.text.strip()
        else:
            print(f"Warning: No translated text found for subtitle id {sub.index}")

    # Save the translated subtitles to a new SRT file.
    new_srt_file = srt_file[:-4] + f"-{target_lang}.srt"
    subs.save(new_srt_file)
    print(f"Translation complete. File saved as {new_srt_file}")