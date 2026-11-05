"""Sozlamalar va yo'llar."""
import os, re, yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CRS = "EPSG:32642"          # UTM 42N — Sentinel-2 T42 plitkalari; hamma hisob shu to'rda (10 m)


def yuklash(path=None):
    path = path or os.path.join(ROOT, "config", "sozlamalar.yaml")
    with open(path, encoding="utf-8") as f:
        s = yaml.safe_load(f)
    s["manba_cfg"] = s["manbalar"][s["manba"]]
    return s


def yol(*q):
    return os.path.join(ROOT, *q)


def kirish_yoli(s):
    p = s["kirish_konturlar"]
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(ROOT, p))


def slug(tuman):
    t = tuman.lower().replace("'", "").replace(" tumani", "").replace(" shahri", "_sh")
    return re.sub(r"[^a-z0-9_]+", "_", t).strip("_")
