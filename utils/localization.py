import yaml
import os

# Load translation files
lang_data = {}
base_dir = os.path.join(os.path.dirname(__file__), "..", "locales")
for lang in ["ru", "en"]:
    try:
        with open(os.path.join(base_dir, f"{lang}.yml"), "r", encoding="utf-8") as f:
            lang_data[lang] = yaml.safe_load(f)
    except FileNotFoundError:
        lang_data[lang] = {}

def gettext(key: str, lang: str = "en"):
    return lang_data.get(lang, {}).get(key, key)
