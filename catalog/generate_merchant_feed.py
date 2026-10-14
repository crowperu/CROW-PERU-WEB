#!/usr/bin/env python3
"""CROW PE -> Google Merchant XML. Solo lecturas publicas; no usa datos de clientes."""
import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

BASE = "https://crow.pe"
NAMESPACE = "http://base.google.com/ns/1.0"
ET.register_namespace("g", NAMESPACE)
CLASS = {
    "anillos":"Anillo", "anillo":"Anillo", "aretes":"Arete", "arete":"Arete",
    "collares":"Collar", "collar":"Collar", "pulseras":"Pulsera", "pulsera":"Pulsera",
    "piercings":"Piercing", "charms":"Charm", "polos":"Polo", "polo":"Polo",
    "poleras":"Polera", "gorras":"Gorra", "llaveros":"Llavero",
    "lentes":"Lentes", "ropa":"Prenda", "collares pet":"Collar Pet",
}

def normalized(value):
    value = unicodedata.normalize("NFD", str(value or "").lower())
    return re.sub(r"[^a-z0-9]+", "-", "".join(c for c in value if unicodedata.category(c)!="Mn")).strip("-")

HYGIENE_RETURN_LABEL = "CROW-SIN-CAMBIOS-HIGIENE"
HYGIENE_CATEGORIES = frozenset({"arete", "aretes", "piercing", "piercings"})

def return_policy_label(category):
    """Only jewelry categories excluded from *voluntary exchanges* in Peru.

    A valid Merchant Center exception must keep legally required remedies for
    defective/non-conforming goods; the label is not a denial of statutory rights.
    """
    return HYGIENE_RETURN_LABEL if normalized(category) in HYGIENE_CATEGORIES else None

def kind(category):
    key = normalized(category).replace("-", " ")
    if key in CLASS:
        return CLASS[key]
    if category.endswith("es") and len(category)>4:
        return category[:-2]
    if category.endswith("s") and len(category)>3:
        return category[:-1]
    return category or "Producto"

def full_name(p):
    name = str(p.get("name") or "").strip()
    cls = kind(str(p.get("category") or "").strip())
    if normalized(name) == normalized(cls) or normalized(name).startswith(normalized(cls)+"-"):
        return name
    return f"{cls} {name}" if name else cls

def canonical(p):
    category = str(p.get("category") or "productos")
    pet = p.get("brand_line") == "crow-pet" or "pet" in category.lower()
    name = normalized(full_name(p)) or normalized(p.get("slug")) or p["id"]
    return BASE + ("/crow-pet" if pet else "") + "/" + (normalized(category) or "productos") + "/" + name

def clean_text(x):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", str(x or ""))).strip()

def g(parent, tag, value):
    ET.SubElement(parent, f"{{{NAMESPACE}}}{tag}").text = str(value)

def money(v):
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return Decimal(0)

def main():
    base = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_PUBLISHABLE_KEY"]
    if not base.endswith(".supabase.co"):
        raise ValueError("Unexpected Supabase host")
    columns = ("id,name,category,price,sale_price,stock,status,product_type,sku,"
               "slug,brand_line,image_url,images,description,short_description,color,"
               "material,activo_peru,available_pe")
    query = urllib.parse.urlencode({
        "select": columns, "status": "eq.published", "product_type": "eq.commerce",
        "activo_peru": "eq.true", "available_pe": "eq.true",
        "order": "name.asc", "limit": "1000",
    })
    req = urllib.request.Request(base + "/rest/v1/products?" + query,
                                 headers={"apikey":key, "Accept":"application/json",
                                          "User-Agent":"CROW-Merchant-Feed/1.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        products = json.load(response)
    if not isinstance(products, list) or len(products) < 5:
        raise RuntimeError("Insufficient catalog: refusing to overwrite existing file")

    rss = ET.Element("rss", {"version":"2.0"})
    channel = ET.SubElement(rss, "channel")
    for tag, value in (("title","CROW Perú - Catálogo"),("link",BASE),
                       ("description","Productos CROW vendidos en Perú (PEN)")):
        ET.SubElement(channel, tag).text = value

    used = set()
    ready = 0
    stocked = 0
    for p in products:
        if (p.get("product_type") != "commerce" or p.get("status") != "published"
            or p.get("activo_peru") is not True or p.get("available_pe") is not True
            or normalized(p.get("category")) == "adopcion"):
            continue
        name = clean_text(p.get("name"))
        base_price = money(p.get("price"))
        images = p.get("images") if isinstance(p.get("images"), list) else []
        cover = str(p.get("image_url") or (images[0] if images else "")).strip()
        if not name or base_price<=0 or not cover.startswith("https://"):
            raise RuntimeError(f"Invalid product data for {p.get('id')}")
        product_id = str(p.get("sku") or p["id"]).strip()
        if product_id in used:
            raise RuntimeError("Duplicate product SKU: " + product_id)
        used.add(product_id)
        item = ET.SubElement(channel, "item")
        title = full_name(p)[:150]
        details = clean_text(p.get("description") or p.get("short_description")) or title + " de CROW."
        for tag,value in (("id",product_id),("title",title),("description",details[:5000]),
                          ("link",canonical(p)),("image_link",cover)):
            g(item, tag, value)
        other = []
        for im in images:
            if isinstance(im,str) and im.startswith("https://") and im!=cover and im not in other:
                other.append(im)
        for im in other[:10]:
            g(item,"additional_image_link",im)
        g(item, "brand", "CROW")
        g(item, "identifier_exists", "no") # Productos propios sin GTIN/MPN verificados
        g(item, "condition", "new")
        available = money(p.get("stock")) > 0
        g(item, "availability", "in_stock" if available else "out_of_stock")
        g(item, "price", f"{base_price:.2f} PEN")
        sale = money(p.get("sale_price"))
        if Decimal(0) < sale < base_price:
            g(item, "sale_price", f"{sale:.2f} PEN")
        g(item, "product_type", p.get("category") or "Accesorios")
        policy_label = return_policy_label(p.get("category"))
        if policy_label:
            g(item, "return_policy_label", policy_label)
        if clean_text(p.get("color")):
            g(item, "color", clean_text(p["color"]))
        if clean_text(p.get("material")):
            g(item, "material", clean_text(p["material"]))
        ready += 1
        stocked += int(available)
    if ready < 5:
        raise RuntimeError("No usable products: keeping previous published feed")

    out = Path("google-merchant-pe.xml")
    ET.ElementTree(rss).write(out, encoding="utf-8", xml_declaration=True,
                              short_empty_elements=False)
    print(json.dumps({"products":ready, "in_stock":stocked,
                      "out_of_stock":ready-stocked, "file":str(out)}))

if __name__ == "__main__":
    main()
