"""Stable source identities live alongside Office's local numeric IDs."""

from lxml import etree
from uuid import uuid4
from .xml import el, ensure, tag

IDENTITY_NS = "urn:presentation-document:v1"
IDENTITY_URI = "urn:presentation-document:v1:identity"


def fresh_identity(original):
    return f"{original}-copy-{uuid4().hex}"


def renew_identities(element):
    """A copied page owns new semantic identities; numeric Office IDs stay local."""
    for node in element.iter("{" + IDENTITY_NS + "}identity"):
        node.set("id", fresh_identity(node.get("id", "object")))


def unique_identity(value, seen):
    """Accept ordinary editor copies that retained our unknown extension markers."""
    if value in seen:
        value = fresh_identity(value)
    seen.add(value)
    return value


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
