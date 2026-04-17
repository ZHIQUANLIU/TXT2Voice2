import os
import re
import zipfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
import posixpath
import fitz

def _strip_xml_tag(tag):
    return tag.split("}", 1)[-1] if tag.startswith("{") else tag

class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._chunks = []

    def handle_data(self, data):
        if data:
            self._chunks.append(data)

    def get_text(self):
        return "".join(self._chunks)

def _html_to_text(html_bytes):
    try:
        s = html_bytes.decode("utf-8")
    except UnicodeDecodeError:
        s = html_bytes.decode("utf-8", errors="replace")
    
    # Remove script and style tags
    s = re.sub(r"<script[^>]*>.*?</script>", "", s, flags=re.DOTALL | re.I)
    s = re.sub(r"<style[^>]*>.*?</style>", "", s, flags=re.DOTALL | re.I)
    
    p = _HTMLTextExtractor()
    try:
        p.feed(s)
        p.close()
    except Exception:
        s = re.sub(r"<[^>]+>", " ", s)
        return re.sub(r"\s+", " ", s).strip()
    
    t = p.get_text()
    t = re.sub(r"\s+", " ", t)
    return t.strip()

class DocumentParser:
    @staticmethod
    def parse_pdf(path):
        doc = fitz.open(path)
        segments = []
        try:
            for page in doc:
                text = page.get_text().strip()
                if text:
                    segments.append(text)
        finally:
            doc.close()
        return segments

    @staticmethod
    def parse_txt(path):
        with open(path, "rb") as f:
            raw = f.read()
        
        text = None
        for enc in ("utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            text = raw.decode("utf-8", errors="replace")
        
        # Smart splitting logic
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Regex for "第x章" or "Chapter X"
        re_chapter = re.compile(r"^\s*(?:第\s*(?:[0-9零一二三四五六七八九十百千万〇两]+|\d+)\s*章|Chapter\s+\d+)", re.IGNORECASE)
        
        lines = text.split("\n")
        chapters = []
        current_title = "序章 / Prologue"
        current_lines = []
        saw_heading = False

        for line in lines:
            if re_chapter.match(line.strip()) and len(line.strip()) < 100:
                saw_heading = True
                if current_lines:
                    body = "\n".join(current_lines).strip()
                    if body:
                        chapters.append((current_title, body))
                current_title = line.strip()
                current_lines = [line]
            else:
                current_lines.append(line)

        if current_lines:
            body = "\n".join(current_lines).strip()
            if body:
                chapters.append((current_title, body))

        if not saw_heading:
            return [("全文", text.strip())]
        return chapters

    @staticmethod
    def parse_epub(path):
        segments = []
        with zipfile.ZipFile(path, "r") as zf:
            names = set(zf.namelist())
            container_xml = zf.read("META-INF/container.xml")
            croot = ET.fromstring(container_xml)
            opf_path = None
            for el in croot.iter():
                if _strip_xml_tag(el.tag) == "rootfile":
                    opf_path = el.attrib.get("full-path")
                    break
            
            if not opf_path:
                raise ValueError("Invalid EPUB: OPF path not found")
            
            opf_path = opf_path.replace("\\", "/")
            opf_dir = posixpath.dirname(opf_path)
            if opf_dir == ".": opf_dir = ""
            
            opf_bytes = zf.read(opf_path)
            opf_root = ET.fromstring(opf_bytes)
            
            manifest = {}
            spine_ids = []
            for el in opf_root.iter():
                t = _strip_xml_tag(el.tag)
                if t == "manifest":
                    for child in el:
                        if _strip_xml_tag(child.tag) != "item": continue
                        mid = child.attrib.get("id")
                        href = child.attrib.get("href")
                        mt = child.attrib.get("media-type", "")
                        if not mid or not href: continue
                        if "image/" in mt: continue
                        manifest[mid] = href
                elif t == "spine":
                    for child in el:
                        if _strip_xml_tag(child.tag) != "itemref": continue
                        idref = child.attrib.get("idref")
                        if idref: spine_ids.append(idref)
            
            for idref in spine_ids:
                href = manifest.get(idref)
                if not href: continue
                full = posixpath.normpath(posixpath.join(opf_dir, href)).lstrip("/")
                
                # Check for variations in naming (slashes)
                if full not in names:
                    alt = full.replace("/", "\\")
                    if alt in names: full = alt
                    else: continue
                
                try:
                    data = zf.read(full)
                    txt = _html_to_text(data)
                    if len(txt) > 20:
                        segments.append(txt)
                except:
                    continue
        return segments

    @classmethod
    def load(cls, path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            return [("Page " + str(i+1), text) for i, text in enumerate(cls.parse_pdf(path))]
        elif ext == ".txt":
            return cls.parse_txt(path)
        elif ext == ".epub":
            return [("Section " + str(i+1), text) for i, text in enumerate(cls.parse_epub(path))]
        else:
            raise ValueError(f"Unsupported file type: {ext}")
