import os
import pysrt
from deepl import Translator


def srt_translate_JA(srt_file):
    '''
    Translates the captions in an existing .srt file to the target language

    Args:
    srt_file: the path to the .srt file
    target_lang: the language code for the target language (e.g. 'JA' for Japanese)
    '''
    subs = pysrt.open(srt_file)
    translator = Translator(os.environ['DEEPL_AUTH_KEY'])
    for sub in subs:
        sub.text = translator.translate_text(sub.text, target_lang = "JA", formality = "more")
    new_srt_file = srt_file[:-4] + '-JA.srt'
    subs.save(new_srt_file)
    print('done')

def srt_translate_KO(srt_file):
    subs = pysrt.open(srt_file)
    translator = Translator(os.environ['DEEPL_AUTH_KEY'])
    for sub in subs:
        sub.text = translator.translate_text(sub.text, target_lang = "KO")
    new_srt_file = srt_file[:-4] + '-' + 'KO.srt'
    subs.save(new_srt_file)
    print('done')

def srt_translate_ES(srt_file):
    subs = pysrt.open(srt_file)
    translator = Translator(os.environ['DEEPL_AUTH_KEY'])
    for sub in subs:
        sub.text = translator.translate_text(sub.text, target_lang = "ES")
    new_srt_file = srt_file[:-4] + '-' + 'ES.srt'
    subs.save(new_srt_file)
    print('done')

def main():
    # Example usage
    # srt_translate_JA('Fall_Quarter_Vlog_SRT_English.srt')
    # srt_translate_KO('Fall_Quarter_Vlog_SRT_English.srt')
    srt_translate_ES('Fall_Quarter_Vlog_SRT_English.srt')


if __name__ == '__main__':
    main()