import os
import pysrt
from deepl import Translator


def srt_translate(srt_file, target_lang):
    '''
    Translates the captions in an existing .srt file to the target language

    Args:
    srt_file: the path to the .srt file
    target_lang: the language code for the target language (e.g. 'JA' for Japanese)
    '''
    subs = pysrt.open(srt_file)
    translator = Translator(os.environ['DEEPL_AUTH_KEY'])
    for sub in subs:
        sub.text = translator.translate_text(sub.text, target_lang = target_lang)
    new_srt_file = srt_file[:-4] + '-' + target_lang + '.srt'
    subs.save(new_srt_file)
    print('done')


def main():
    # Example usage
    srt_translate('SEOUL_VLOG_2.srt', 'JA')


if __name__ == '__main__':
    main()