"""Stable source identities live alongside Office's local numeric IDs."""

from lxml import etree
from .xml import el, ensure, tag

IDENTITY_NS = "urn:presentation-document:v1"
IDENTITY_URI = "urn:presentation-document:v1:identity"


def write_identity(parent, id, extension="a:extLst"):
    extlist = ensure(parent, extension)
    prefix = extension.split(":")[0]
    for node in list(extlist):
        if node.get("uri") == IDENTITY_URI:
            extlist.remove(node)
    ext = el(prefix + ":ext", {"uri": IDENTITY_URI})
    node = etree.SubElement(ext, "{" + IDENTITY_NS + "}identity")
    node.set("id", id)
    extlist.append(ext)


def read_identity(parent, default):
    if parent.tag == tag("p:cSld"):
        node = parent.find(
            tag("p:extLst") + "/" + tag("p:ext") + "/{" + IDENTITY_NS + "}identity"
        )
    else:
        cnv = parent.find(".//" + tag("p:cNvPr"))
        node = (
            cnv.find(
                tag("a:extLst") + "/" + tag("a:ext") + "/{" + IDENTITY_NS + "}identity"
            )
            if cnv is not None
            else None
        )
    return node.get("id", default) if node is not None else default
