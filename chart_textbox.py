"""Add an editable DrawingML text box inside an existing Excel chart."""
from pathlib import Path
import os
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as ET

C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
D = "http://schemas.openxmlformats.org/drawingml/2006/chartDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P = "http://schemas.openxmlformats.org/package/2006/relationships"
T = "http://schemas.openxmlformats.org/package/2006/content-types"
for prefix, uri in (("c", C), ("cdr", D), ("a", A), ("r", R)):
    ET.register_namespace(prefix, uri)


def sub(parent, uri, tag, **attributes):
    return ET.SubElement(parent, f"{{{uri}}}{tag}", attributes)


def add_ratio_textbox(workbook_path, ratios):
    """Locate Raw_Overview chart and add static, editable fitted height ratios."""
    with ZipFile(workbook_path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    chart_path = None
    for name, data in entries.items():
        if name.startswith("xl/charts/chart") and name.endswith(".xml"):
            root = ET.fromstring(data)
            formulas = root.findall(f".//{{{C}}}f")
            if any("Raw_Overview!" in (f.text or "") or "'Raw_Overview'!" in (f.text or "") for f in formulas):
                chart_path = name
                break
    if chart_path is None:
        return

    drawing = ET.Element(f"{{{C}}}userShapes")
    anchor = sub(drawing, D, "relSizeAnchor")
    # Plot: (0.18, 0.02), size (0.80, 0.80).
    # Text box: 1.5 x 3.5 inches inside a 5 x 5 inch chart.
    for tag, x, y in (("from", "0.43", "0.07"), ("to", "0.73", "0.77")):
        point = sub(anchor, D, tag)
        sub(point, D, "x").text = x
        sub(point, D, "y").text = y
    shape = sub(anchor, D, "sp")
    nonvisual = sub(shape, D, "nvSpPr")
    sub(nonvisual, D, "cNvPr", id="1", name="ID_IG_Ratios")
    sub(nonvisual, D, "cNvSpPr", txBox="1")
    properties = sub(shape, D, "spPr")
    transform = sub(properties, A, "xfrm")
    sub(transform, A, "off", x="1965960", y="320040")
    sub(transform, A, "ext", cx="1371600", cy="3200400")
    geometry = sub(properties, A, "prstGeom", prst="rect")
    sub(geometry, A, "avLst")
    sub(properties, A, "noFill")
    sub(sub(properties, A, "ln"), A, "noFill")
    body = sub(shape, D, "txBody")
    settings = sub(body, A, "bodyPr", wrap="none", anchor="ctr",
                   lIns="0", rIns="0", tIns="0", bIns="0")
    sub(settings, A, "noAutofit")
    sub(body, A, "lstStyle")
    for ratio in ratios:
        paragraph = sub(body, A, "p")
        paragraph_properties = sub(paragraph, A, "pPr", algn="ctr")
        # Use equal fixed-height line slots across the 3.5-inch (252 pt) box.
        spacing = sub(paragraph_properties, A, "lnSpc")
        sub(spacing, A, "spcPts", val=str(round(25200 / max(len(ratios), 1))))
        sub(sub(paragraph_properties, A, "spcBef"), A, "spcPts", val="0")
        sub(sub(paragraph_properties, A, "spcAft"), A, "spcPts", val="0")
        for text, lowered in (("I", False), ("D", True), ("/I", False),
                              ("G", True), (f"={ratio:.4f}", False)):
            run = sub(paragraph, A, "r")
            font = sub(run, A, "rPr", lang="en-US", sz="1000" if lowered else "1400",
                       b="0", i="0", baseline="-25000" if lowered else "0")
            sub(sub(font, A, "solidFill"), A, "srgbClr", val="000000")
            sub(font, A, "latin", typeface="Arial")
            sub(run, A, "t").text = text

    drawing_path = "xl/drawings/raman_ratio_text.xml"
    rel_path = str(Path(chart_path).parent / "_rels" / (Path(chart_path).name + ".rels"))
    relationships = ET.fromstring(entries[rel_path]) if rel_path in entries else ET.Element(f"{{{P}}}Relationships")
    existing = {e.get("Id") for e in relationships}
    number = 1
    while f"rId{number}" in existing:
        number += 1
    relationship_id = f"rId{number}"
    sub(relationships, P, "Relationship", Id=relationship_id,
        Type=R + "/chartUserShapes", Target="../drawings/raman_ratio_text.xml")
    chart = ET.fromstring(entries[chart_path])
    ref = ET.Element(f"{{{C}}}userShapes", {f"{{{R}}}id": relationship_id})
    extension = chart.find(f"{{{C}}}extLst")
    chart.insert(list(chart).index(extension), ref) if extension is not None else chart.append(ref)
    types = ET.fromstring(entries["[Content_Types].xml"])
    sub(types, T, "Override", PartName="/" + drawing_path,
        ContentType="application/vnd.openxmlformats-officedocument.drawingml.chartshapes+xml")
    for name, root in ((drawing_path, drawing), (rel_path, relationships),
                       (chart_path, chart), ("[Content_Types].xml", types)):
        entries[name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    handle, temporary = tempfile.mkstemp(suffix=".xlsx", dir=Path(workbook_path).parent)
    os.close(handle)
    try:
        with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
            for name, data in entries.items():
                archive.writestr(name, data)
        os.replace(temporary, workbook_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
