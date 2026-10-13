"""Build zh-CN and zh-TW catalogs.

Manual UI translations live in manual.tsv (english<TAB>simplified).
Item, trait, and technology names that match Space Haven's own library/texts
are filled from the installed game when that file is present. Traditional
Chinese is converted from the simplified catalog.
"""
import html
import json
import pathlib
import re
import zipfile

import zhconv

ROOT = pathlib.Path(__file__).resolve().parents[1]
I18N = pathlib.Path(__file__).resolve().parent
JAR = pathlib.Path(r"D:\SteamLibrary\steamapps\common\SpaceHaven\spacehaven.jar")


def load_manual():
    table = {}
    for line in (I18N / "manual.tsv").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        english, simplified = line.split("\t", 1)
        table[english] = simplified
    return table


def load_game_glossary():
    glossary = {}
    if not JAR.exists():
        return glossary
    with zipfile.ZipFile(JAR) as archive:
        text = archive.read("library/texts").decode("utf-8", errors="replace")
    for block in re.findall(r"<t\b[^>]*>(.*?)</t>", text, flags=re.DOTALL):
        en = re.search(r"<EN>(.*?)</EN>", block, flags=re.DOTALL)
        cn = re.search(r"<CN>(.*?)</CN>", block, flags=re.DOTALL)
        if not en or not cn:
            continue
        english = html.unescape(re.sub(r"\s+", " ", en.group(1)).strip())
        simplified = html.unescape(re.sub(r"\s+", " ", cn.group(1)).strip())
        if english and simplified:
            glossary.setdefault(english, simplified)
    return glossary


def id_names():
    text = (ROOT / "IdCollection.vb").read_text(encoding="utf-8")
    return set(re.findall(r'\{\s*-?\d+\s*,\s*"([^"]+)"', text))


def traditional(text):
    for source, target in (
        ("文件夾", "資料夾"),
        ("文件", "檔案"),
        ("默認", "預設"),
        ("程序", "程式"),
        ("信息", "資訊"),
        ("質量", "品質"),
        ("軟件", "軟體"),
        ("內存", "記憶體"),
        ("網絡", "網路"),
        ("打印", "列印"),
        ("鼠標", "滑鼠"),
        ("視頻", "視訊"),
        ("服務器", "伺服器"),
        ("支持", "支援"),
        ("設置", "設定"),
    ):
        text = text.replace(source, target)
    return text


def main():
    manual = load_manual()
    glossary = load_game_glossary()
    catalog = dict(manual)
    folded = {}
    for english, simplified in glossary.items():
        folded.setdefault(english.casefold(), simplified)
    for name in id_names():
        if name in catalog:
            continue
        translation = glossary.get(name) or folded.get(name.casefold())
        if translation:
            catalog[name] = translation
    keys = [line for line in (ROOT / "_keys.txt").read_text(encoding="utf-8").splitlines()]
    missing = [key for key in keys if key not in catalog and key not in {"English", "X", "Language / 语言 / 語言"}]
    (I18N / "missing.txt").write_text("\n".join(missing), encoding="utf-8")
    missing_names = sorted(name for name in id_names() if name not in catalog)
    (I18N / "missing-names.txt").write_text("\n".join(missing_names), encoding="utf-8")
    zh_cn = {key: value for key, value in catalog.items() if value and value != key}
    zh_tw = {key: traditional(zhconv.convert(value, "zh-tw")) for key, value in zh_cn.items()}
    (I18N / "zh-CN.json").write_text(json.dumps(zh_cn, ensure_ascii=False, indent=2), encoding="utf-8")
    (I18N / "zh-TW.json").write_text(json.dumps(zh_tw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"catalog {len(zh_cn)} missing {len(missing)} names {len(missing_names)} glossary {len(glossary)}")


if __name__ == "__main__":
    main()
