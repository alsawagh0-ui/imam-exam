#!/usr/bin/env python3
"""يبني صفحة الموقع من ملفات المذاكرة (Markdown) وبنك الأسئلة (JSON).

الاستخدام:  python3 imam-exam/build.py
الناتج:    website/exam/index.html  (صفحة واحدة، بدون خادم، بدون قاعدة بيانات)
لتغيير المقرر أو الدرجات عدّل TRACKS أدناه أو ملفات المحتوى فقط.
"""
import json, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT.parent / "website" / "exam" / "index.html"

def md(name):
    return (ROOT / name).read_text(encoding="utf-8")


# ---------- تقسيم دروس "من الصفر" وربط كل درس بأسئلته ----------
import re, unicodedata

_DIAC = re.compile(r"[\u064B-\u0652\u0640]")
def norm(t):
    t = unicodedata.normalize("NFKC", t)
    t = _DIAC.sub("", t)
    for a, b in (("أ","ا"),("إ","ا"),("آ","ا"),("ة","ه"),("ى","ي"),("ؤ","و"),("ئ","ي")):
        t = t.replace(a, b)
    return t

def flat(t):
    t = re.sub(r"[*|_#>`]", " ", norm(t))
    return re.sub(r"\s+", " ", t).strip()

def split_lessons(md_text, pool, own_path=None):
    """يقسم ملف الدروس على العناوين، ويلتقط سطر ::quiz:: ليختار أسئلة الدرس من بنك المادة."""
    lessons, cur = [], None
    for line in md_text.split("\n"):
        if line.startswith("## "):
            if cur: lessons.append(cur)
            cur = {"t": line[3:].strip(), "md": [], "kw": []}
            continue
        if cur is None:
            cur = {"t": "", "md": [], "kw": []}
        if line.startswith("::quiz::"):
            cur["kw"] = [k.strip() for k in line[len("::quiz::"):].split("|") if k.strip()]
            continue
        cur["md"].append(line)
    if cur: lessons.append(cur)

    out, used = [], set()
    own = json.loads(own_path.read_text(encoding="utf-8")) if own_path and own_path.exists() else None
    for L in lessons:
        idxs = []
        body = flat("\n".join(L["md"]))
        if own is not None:
            # تمارين مكتوبة للدرس نفسه، وجواب كل سؤال نصٌّ منقول منه (تتحقق منه audit/check_lesson_q.py)
            idxs = own.get(L["t"], [])
            for q in idxs:
                if flat(q["e"]) not in body: raise SystemExit(f"شاهد ليس من الدرس: {L['t']}: {q['e']}")
        elif L["kw"]:
            # الفقه: لا يدخل الدرسَ إلا سؤالٌ نصُّ شرحه (من دليل الطالب) موجود في الدرس نفسه
            for i, q in enumerate(pool):
                if i in used: continue
                quotes = re.findall(r"«([^»]+)»", q.get("e", ""))
                if quotes and all(flat(x) in body for x in quotes):
                    idxs.append(i); used.add(i)
        out.append({"t": L["t"], "md": "\n".join(L["md"]).strip(), "q": idxs})
    return [L for L in out if L["md"] or L["q"]]

SUBJECTS = {
    "fiqh":    {"name": "الفقه",       "file": "27-الفقه-نصوص-دليل-الطالب.md", "source": "دليل الطالب لنيل المطالب، مرعي بن يوسف الكرمي"},
    "hadith":  {"name": "الحديث",      "file": "12-الحديث-شرح-ابن-دقيق.md", "source": "الأربعون النووية بشرح ابن دقيق العيد"},
    "aqeedah": {"name": "العقيدة",     "file": "13-العقيدة-بريق-الجمان-الأصل.md", "source": "بريق الجمان بشرح أركان الإيمان"},
    "nahw":    {"name": "النحو",       "file": "14-النحو-التحفة-السنية.md",   "source": "التحفة السنية بشرح المقدمة الآجرومية، محمد محيي الدين عبدالحميد"},
    "tafsir":  {"name": "التفسير",     "file": "04-التفسير-جزء-عم.md",         "source": "مختصر زبدة التفسير، جزء عم"},
    "tajweed": {"name": "التجويد",     "file": "05-التجويد.md",                "source": "غاية المريد في علم التجويد، عطية قابل نصر"},
    "mithaq":  {"name": "ميثاق المسجد","file": "09-ميثاق-المسجد.md",            "source": "ميثاق المسجد، الوثيقة المنظمة لعمل الإمام والخطيب والمؤذن"},
}

# الدرجات لكل مسار. غيّرها هنا فقط.
TRACKS = {
    "imam": {
        "name": "إمام مسجد",
        "exam_date": "2026-10-06",
        "marks": {"fiqh": 60, "hadith": 10, "aqeedah": 10, "nahw": 10, "tafsir": 4, "tajweed": 4, "mithaq": 2},
        "pass": 70,
        "notes": {"fiqh": "40 درجة عبادات + 20 درجة معاملات"},
        "scope": ["ibadat", "muamalat"],
        # عدد أسئلة الاختبار الفعلي لكل مادة (المجموع 50)
        "exam": {"fiqh": 29, "hadith": 5, "aqeedah": 5, "nahw": 5, "tafsir": 3, "tajweed": 2, "mithaq": 1},
        # ورقة الاختبار الكاملة: لكل مادة عدد أسئلة كل نوع، والدرجة موزعة على الأسئلة
        "paper": {
            "fiqh":    {"mcq": 8, "tf": 6, "fill": 3, "written": 6},
            "hadith":  {"mcq": 2, "tf": 2, "fill": 1, "written": 2},
            "aqeedah": {"mcq": 2, "tf": 2, "fill": 1, "written": 2},
            "nahw":    {"mcq": 3, "tf": 2, "fill": 1, "written": 1},
            "tafsir":  {"mcq": 2, "tf": 1, "fill": 1, "written": 0},
            "tajweed": {"mcq": 2, "tf": 1, "fill": 0, "written": 1},
            "mithaq":  {"mcq": 2},
        },
    },
    "muadhin": {
        "name": "مؤذن",
        "exam_date": "2026-10-06",
        "pass": 70,
        # منهج المؤذنين: لا نحو فيه، والفقه عبادات فقط (طهارة، صلاة، جنائز، زكاة، صوم، حج).
        "marks": {"fiqh": 50, "hadith": 20, "aqeedah": 10, "tafsir": 8, "tajweed": 8, "mithaq": 4},
        "notes": {"fiqh": "العبادات فقط: الطهارة والصلاة والجنائز والزكاة والصوم والحج"},
        "scope": ["ibadat"],
        "exam": {"fiqh": 25, "hadith": 10, "aqeedah": 5, "tafsir": 4, "tajweed": 4, "mithaq": 2},
        "paper": {
            "fiqh":    {"mcq": 6, "tf": 5, "fill": 2, "written": 5},
            "hadith":  {"mcq": 3, "tf": 2, "fill": 1, "written": 3},
            "aqeedah": {"mcq": 2, "tf": 1, "fill": 1, "written": 1},
            "tafsir":  {"mcq": 2, "tf": 1, "fill": 1, "written": 0},
            "tajweed": {"mcq": 2, "tf": 1, "fill": 0, "written": 1},
            "mithaq":  {"mcq": 2},
        },
    },
}

# دروس "من الصفر": مكتوبة للمبتدئ الذي لم يدرس المادة قط
BASICS = {
    "nahw": "20-من-الصفر-النحو.md",
    "aqeedah": "21-من-الصفر-العقيدة.md",
    "hadith": "22-من-الصفر-الحديث.md",
    "tajweed": "23-من-الصفر-التجويد.md",
    "tafsir": "24-من-الصفر-التفسير.md",
    "mithaq": "25-من-الصفر-ميثاق-المسجد.md",
    "fiqh": "26-من-الصفر-الفقه.md",
}

def vetted(lst):
    """لا يُعرض إلا ما طوبق بنص الكتاب: الشرح يُحذف ما لم يكن له مصدر (src)،
    والسؤال يُستبعد إذا رُفض (rej) أو لم يثبت له أصل في الكتاب (hide)."""
    out=[]
    for q in lst:
        if q.get("rej") or q.get("hide"): continue
        q=dict(q)
        src=q.pop("src", None)
        if not src: q.pop("e", None)
        elif q.get("e"): q["e"]=f"{q['e']} ({src})"
        else: q["e"]=f"المصدر: {src}"
        out.append(q)
    return out

questions = vetted(json.loads((ROOT / "questions.json").read_text(encoding="utf-8")))
mcq = vetted(json.loads((ROOT / "mcq.json").read_text(encoding="utf-8")))
tf = vetted(json.loads((ROOT / "tf.json").read_text(encoding="utf-8")))
fill = vetted(json.loads((ROOT / "fill.json").read_text(encoding="utf-8")))
numbers = json.loads((ROOT / "numbers.json").read_text(encoding="utf-8"))
plan = md("00-الخطة-وتحليل-الاختبارات.md")

mufid = json.loads((ROOT / "mufid.json").read_text(encoding="utf-8"))
data = {"built": datetime.date.today().isoformat(), "plan": plan, "numbers": numbers, "mufid": mufid, "tracks": {}, "subjects": {}}
for sid, s in SUBJECTS.items():
    data["subjects"][sid] = {
        "name": s["name"], "source": s["source"],
        "notes": ((md("07-دليل-الطالب-العبادات.md") + "\n\n" + md("10-المعاملات-الكوكب-الغارب.md") + "\n\n" + md("11-الجنايات-والحدود.md") + "\n\n" if sid=="fiqh" else "") + md(s["file"]) + ("\n\n" + md("01b-الفقه-إضافات-من-دليل-الطالب.md") if sid=="fiqh" else ("\n\n" + md("08-غاية-المريد-التجويد.md") if sid=="tajweed" else ("\n\n" + md("02-الحديث-الأربعون-النووية.md") if sid=="hadith" else ("\n\n" + md("03-العقيدة-بريق-الجمان.md") if sid=="aqeedah" else ("\n\n" + md("06-النحو-مراجعة.md") if sid=="nahw" else "")))))) if s["file"] else "## المقرر لم يُرسل بعد\n\nأرسل صور أو ملف ميثاق المسجد ليُضاف هنا.",
        "lessons": split_lessons((ROOT / BASICS[sid]).read_text(encoding="utf-8"),
                                 [q for q in mcq if q["s"] == sid], ROOT / "lesson_q" / f"{sid}.json") if sid in BASICS else [],
        "questions": [q for q in questions if q["s"] == sid],
        "mcq": [q for q in mcq if q["s"] == sid],
        "tf": [q for q in tf if q["s"] == sid],
        "fill": [q for q in fill if q["s"] == sid],
    }
for tid, t in TRACKS.items():
    data["tracks"][tid] = t

template = (ROOT / "template.html").read_text(encoding="utf-8")
payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(template.replace("/*__DATA__*/null", payload), encoding="utf-8")
print("wrote", OUT, f"{OUT.stat().st_size/1024:.0f} KB")
