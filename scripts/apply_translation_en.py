# -*- coding: utf-8 -*-
"""把中文数据回填为英文：生成 data/pose-en.json / meta-en.json / translations-en.csv

用法（在仓库根目录）: python3 scripts/apply_translation_en.py

输入为现有的中文版数据（data/pose-zh.json / meta-zh.json），
值映射来自 scripts/i18n_en.py，字段键名一并翻译为英文：
    id            -> id
    体系          -> system
    姿势编号      -> poseNumber
    分类          -> category
    姿势名称      -> poseName
    角度          -> angle
    缩略图        -> thumb
    原图          -> full
    检索          -> search（由英文字段重建）
"""
import csv
import json
import os
import sys
from collections import Counter

import i18n_en

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

with open(os.path.join(DATA, "pose-zh.json"), encoding="utf-8") as f:
    data = json.load(f)
with open(os.path.join(DATA, "meta-zh.json"), encoding="utf-8") as f:
    meta = json.load(f)

# 需要值翻译的字段：中文字段名 -> 英文映射表
VALUE_MAPS = {
    "体系": i18n_en.SYSTEM,
    "分类": i18n_en.CATEGORY,
    "角度": i18n_en.ANGLE,
    "姿势名称": i18n_en.POSE,
}

missing = {k: sorted({x.get(k) for x in data if x.get(k)} - set(m)) for k, m in VALUE_MAPS.items()}
bad = {k: v for k, v in missing.items() if v}
if bad:
    print("!! 缺失英文译词：")
    for k, v in bad:
        for s in v:
            print(f"  [{k}] {s}")
    sys.exit(1)

# 中文字段名 -> 英文字段名
KEY_MAP = {
    "id": "id",
    "体系": "system",
    "姿势编号": "poseNumber",
    "分类": "category",
    "姿势名称": "poseName",
    "角度": "angle",
    "缩略图": "thumb",
    "原图": "full",
}

# 计数（用于 translations-en.csv）
counts = Counter()


def translate_value(field, value):
    m = VALUE_MAPS.get(field)
    if m is None or value is None:
        return value
    counts[(field, value)] += 1
    return m[value]


out_records = []
for item in data:
    rec = {}
    for zh_key, value in item.items():
        en_key = KEY_MAP.get(zh_key)
        if en_key is None:
            # 未知字段：跳过（检索单独重建）
            continue
        if zh_key in VALUE_MAPS:
            rec[en_key] = translate_value(zh_key, value)
        else:
            rec[en_key] = value
    # 重建检索串（供搜索/SEO 用）
    rec["search"] = " ".join(
        str(rec.get(k, "")) for k in ("id", "system", "category", "poseName", "poseNumber", "angle")
    )
    out_records.append(rec)

with open(os.path.join(DATA, "pose-en.json"), "w", encoding="utf-8") as f:
    json.dump(out_records, f, ensure_ascii=False, indent=2)
    f.write("\n")

# meta：体系分类 -> systems
meta_lines = meta.get("体系分类") or meta.get("lines") or []
en_lines = [i18n_en.SYSTEM[v] for v in meta_lines]
with open(os.path.join(DATA, "meta-en.json"), "w", encoding="utf-8") as f:
    json.dump({"systems": en_lines}, f, ensure_ascii=False, indent=2)
    f.write("\n")

# 双语对照表
FIELD_LABEL = {"体系": "system", "分类": "category", "角度": "angle", "姿势名称": "poseName"}
with open(os.path.join(DATA, "translations-en.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["field", "zh", "en", "count"])
    for (field, value), cnt in counts.most_common():
        w.writerow([FIELD_LABEL[field], value, VALUE_MAPS[field][value], cnt])

print(f"pose-en.json: {len(out_records)} records")
print(f"meta-en.json: {len(en_lines)} systems")
print(f"translations-en.csv: {sum(counts.values())} value occurrences, {len(counts)} distinct")
