#!/usr/bin/env python3
import json
import re
import zipfile
from xml.etree import ElementTree as ET

DOCX_PATH = "system-integrator-litt.docx"


def read_document_xml(docx_path: str) -> bytes:
    with zipfile.ZipFile(docx_path, "r") as zf:
        return zf.read("word/document.xml")


def extract_paragraph_text(p, ns) -> str:
    texts = []
    for t in p.findall('.//w:t', ns):
        texts.append(t.text or "")
    # Normalize whitespace and entities
    s = "".join(texts)
    s = s.replace("\u00a0", " ")  # non-breaking spaces
    s = s.replace("&amp;", "&")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_isv_sections(xml_bytes: bytes):
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    root = ET.fromstring(xml_bytes)
    body = root.find("w:body", ns)
    isvs = []
    current = None

    for p in body.findall("w:p", ns):
        style = p.find("w:pPr/w:pStyle", ns)
        style_val = style.get(f"{{{ns['w']}}}val") if style is not None else None
        text = extract_paragraph_text(p, ns)
        if not text:
            continue

        if style_val == "Heading1":
            # Start a new ISV section
            if current:
                # finalize previous
                current["content"] = current["content"].strip()
                isvs.append(current)
            current = {"name": text, "content": ""}
        else:
            if current is not None:
                # Append paragraph content
                if current["content"]:
                    current["content"] += "\n"
                current["content"] += text

    if current:
        current["content"] = current["content"].strip()
        isvs.append(current)

    return isvs


KNOWN_SIS = [
    # Global GSIs
    "Accenture",
    "Deloitte",
    "EY",
    "KPMG",
    "PwC",
    "IBM",
    "Kyndryl",
    "NTT Data",
    # Global IT services/SIs
    "Capgemini",
    "Atos",
    "Eviden",
    "Sopra Steria",
    "CGI",
    "Tata Consultancy Services",
    "TCS",
    "Infosys",
    "Wipro",
    "HCL",
    "HCLTech",
    "EPAM",
    "BearingPoint",
    # France/Europe specialists commonly seen
    "Devoteam",
    "Orange Business",
    "Inetum",
    "Business & Decision",
    "Micropole",
    "Onepoint",
    "OCTO Technology",
    "Worldline",
]


def unique_preserve_order(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def find_partner_types(text: str):
    types = []
    patterns = [
        ("cloud platform partners", r"cloud platform partners"),
        ("technology partners", r"technology partners"),
        ("OEM partners", r"OEM partners"),
        ("resource (services) partners", r"resource \(services\) partners|resource partners|services partners"),
        ("consulting partners", r"consult(ing|ancy) partners"),
    ]
    low = text.lower()
    for label, pat in patterns:
        if re.search(pat, low):
            types.append(label)
    return unique_preserve_order(types)


def find_sis(text: str):
    found = []
    for name in KNOWN_SIS:
        # Match case-insensitive, tolerate non-breaking space variants for '&'
        pat = re.escape(name)
        # Accommodate 'Business & Decision' vs 'Business and Decision' and xml spacing
        pat = pat.replace(r"\&", r"(?:&|and)")
        if re.search(pat, text, flags=re.IGNORECASE):
            # Normalize aliases
            norm = name
            if name == "TCS":
                norm = "Tata Consultancy Services (TCS)"
            if name == "HCL":
                norm = "HCLTech"
            found.append(norm)
    return unique_preserve_order(found)


def sentences(text: str):
    # Simple sentence splitter
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def find_france_notes(text: str):
    notes = []
    for s in sentences(text):
        if re.search(r"\b(France|French|Paris)\b", s, flags=re.IGNORECASE):
            notes.append(s)
    # Keep top 2 concise notes
    return notes[:2]


def find_services(text: str):
    services = []
    keywords = [
        "consulting",
        "implementation",
        "managed services",
        "migration",
        "data architecture",
        "training",
        "co-selling",
        "strategy",
        "integration",
    ]
    low = text.lower()
    for k in keywords:
        if k in low:
            services.append(k)
    return unique_preserve_order(services)


def find_program(text: str):
    # Extract short highlight about partner program tiers or changes
    for s in sentences(text):
        if re.search(r"partner program|Gold|Silver|practice|revamp", s, flags=re.IGNORECASE):
            return s
    return None


def find_french_specialists(text: str):
    names = [
        "Devoteam",
        "Business & Decision",
        "Sopra Steria",
        "Orange Business",
        "Inetum",
        "Micropole",
        "Onepoint",
        "OCTO Technology",
        "Lamarck Group",
        "Ishango",
        "OVHcloud",
    ]
    found = []
    for n in names:
        pat = re.escape(n).replace(r"\&", r"(?:&|and)")
        if re.search(pat, text, flags=re.IGNORECASE):
            found.append(n)
    return unique_preserve_order(found)


def build_qa_for_isv(item):
    text = item["content"]
    qa = []

    types = find_partner_types(text)
    if types:
        qa.append({
            "question": "Partner types",
            "answer": ", ".join(types)
        })

    sis = find_sis(text)
    if sis:
        qa.append({
            "question": "Top GSIs/SIs in France",
            "answer": ", ".join(sis)
        })

    fr = find_france_notes(text)
    if fr:
        qa.append({
            "question": "France-specific notes",
            "answer": " ".join(fr)
        })

    svcs = find_services(text)
    if svcs:
        qa.append({
            "question": "Common services",
            "answer": ", ".join(svcs)
        })

    prog = find_program(text)
    if prog:
        qa.append({
            "question": "Program highlights",
            "answer": prog
        })

    fr_spec = find_french_specialists(text)
    if fr_spec:
        qa.append({
            "question": "French specialists",
            "answer": ", ".join(fr_spec)
        })

    return qa


def main():
    xml_bytes = read_document_xml(DOCX_PATH)
    sections = extract_isv_sections(xml_bytes)

    profs = []
    for sec in sections:
        qa = build_qa_for_isv(sec)
        profs.append({
            "name": sec["name"],
            "answers": qa,
        })

    # Save JSON
    out_path = "data/isv_profiles.json"
    out_path_web = "web/data/isv_profiles.json"
    import os
    os.makedirs("data", exist_ok=True)
    os.makedirs("web/data", exist_ok=True)
    payload = {"profiles": profs}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(out_path_web, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote {out_path} and {out_path_web} with {len(profs)} profiles")


if __name__ == "__main__":
    main()
