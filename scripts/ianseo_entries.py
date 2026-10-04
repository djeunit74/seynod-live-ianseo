"""Read published ENA tables without depending on one column layout."""
import re
import unicodedata
from html import unescape
from html.parser import HTMLParser


def normalized(value):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", str(value)).encode("ascii", "ignore").decode().lower())


def club_matches(club, keywords):
    codes = re.findall(r"\b\d{6,8}\b", club)
    return not keywords or any(
        key in codes if re.fullmatch(r"\d{6,8}", key) else normalized(key) in normalized(club)
        for key in keywords if normalized(key)
    )


class Rows(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.cells, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.cells = []
        elif tag in ("td", "th") and self.cells is not None:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.cells.append(re.sub(r"\s+", " ", unescape("".join(self.cell))).strip())
            self.cell = None
        elif tag == "tr" and self.cells is not None:
            self.rows.append(self.cells)
            self.cells = self.cell = None


def extract_entries(page, keywords=()):
    parser = Rows()
    parser.feed(page)
    entries, columns, current_club = [], {}, ""
    aliases = {
        "name": ("athlete", "archer", "name", "nom"),
        "club": ("country", "nation", "club", "societe", "pays"),
        "target": ("target", "cible"),
        "category": ("class", "category", "categorie", "division"),
        "depart": ("session", "depart", "start", "departure"),
    }
    for cells in parser.rows:
        if not cells:
            continue
        nonempty = [c for c in cells if c]
        if len(nonempty) == 1 and re.match(r"^\d{6,8}\s*-\s*.+", nonempty[0]):
            current_club = nonempty[0]
            columns = {}
            continue
        detected = {field: i for i, c in enumerate(cells) for field, labels in aliases.items() if normalized(c) in labels}
        if "name" in detected:
            columns = detected
            continue
        # Grouped ENA: name, target, category, session. Flat ENA includes club.
        layout = columns or ({"name": 0, "target": 1, "category": 2, "depart": 3} if current_club else {"name": 0, "target": 1, "club": 2, "category": 3, "depart": 4})
        def value(field):
            i = layout.get(field)
            return cells[i] if i is not None and i < len(cells) else ""
        name, club = value("name"), value("club") or current_club
        if len(cells) < 3 or not name or not club or re.match(r"^[-\d\s]+$", name) or not club_matches(club, keywords):
            continue
        depart = value("depart")
        time = re.search(r"\b\d{1,2}[h:]\d{2}\b", depart)
        entries.append({"name": name, "club": club, "target": value("target"), "category": value("category"), "session": value("category"), "depart": depart, "time": time.group() if time else ""})
    return list({(e["name"], e["club"], e["depart"], e["target"]): e for e in entries}.values())
