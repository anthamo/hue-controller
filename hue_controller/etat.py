"""Construit l'état envoyé à la page (voir « Le contrat entre la page et Python » dans ARCHITECTURE.md).

Fonctions pures : aucune lecture réseau, tout vient du dictionnaire `brut` lu sur le bridge.
"""

from . import couleurs

BLANC_CHAUD = "#ffe2bd"
AUTRES = "Autres"


def _arrondi(v):
    # Moitié vers le haut, comme couleurs._arrondi, pas l'arrondi bancaire de Python.
    return int(v + 0.5)


def erreur(message):
    return {"connexion": "erreur", "message": message, "piece": None, "pieces": [], "scenes": [], "lampes": [], "zones": []}


def sans_reglages(message):
    return {"connexion": "reglages", "message": message, "piece": None, "pieces": [], "scenes": [], "lampes": [], "zones": []}


def _ids_lampes_de_appareil(appareil):
    return [s["rid"] for s in appareil.get("services", []) if s.get("rtype") == "light"]


def _mirek(lampe):
    ct = lampe.get("color_temperature")
    if ct and ct.get("mirek"):
        return ct["mirek"]
    return None


def _couleur_xy(c):
    xy = (c or {}).get("xy")
    if xy:
        return couleurs.xy_vers_hex(xy["x"], xy["y"])
    return None


def _mode(lampe):
    # Le bridge garde le dernier mirek même quand la lampe est passée en couleur : mirek_valid tranche.
    if _mirek(lampe) and lampe["color_temperature"].get("mirek_valid"):
        return "blanc"
    if lampe.get("color"):
        return "teinte"
    return None


def _couleur_allumee(lampe):
    mode = _mode(lampe)
    if mode == "blanc":
        return couleurs.kelvin_vers_hex(1e6 / _mirek(lampe))
    if mode == "teinte":
        return _couleur_xy(lampe["color"]) or BLANC_CHAUD
    return BLANC_CHAUD


def _lampe(lampe, zone):
    mode = _mode(lampe)
    allumee = bool(lampe.get("on", {}).get("on"))
    hex_ = _couleur_allumee(lampe)
    reglages = []
    if "color_temperature" in lampe:
        reglages.append("blanc")
    if "color" in lampe:
        reglages.append("teinte")
    schema = (lampe.get("color_temperature") or {}).get("mirek_schema") or {}
    kelvins = None
    if "blanc" in reglages and schema.get("mirek_minimum") and schema.get("mirek_maximum"):
        kelvins = [_arrondi(1e6 / schema["mirek_maximum"]), _arrondi(1e6 / schema["mirek_minimum"])]
    teinte = saturation = None
    if "teinte" in reglages and (lampe["color"] or {}).get("xy"):
        # Toujours depuis la couleur rapportée, quel que soit le mode : le curseur garde son dernier réglage.
        couleur_xy = _couleur_xy(lampe["color"])
        teinte, saturation = _arrondi(couleurs.teinte_de(couleur_xy)) % 360, couleurs.saturation_de(couleur_xy)
    return {
        "id": lampe["id"],
        "nom": lampe["metadata"]["name"],
        "zone": zone,
        "on": allumee,
        "intensite": _arrondi(lampe.get("dimming", {}).get("brightness", 0)),
        "couleur": hex_ if allumee else None,
        "reglages": reglages,
        "mode": mode,
        "kelvin": _arrondi(1e6 / _mirek(lampe)) if mode == "blanc" else None,
        "teinte": teinte,
        "saturation": saturation,
        "kelvins": kelvins,
    }


def _couleur_action(action):
    c = _couleur_xy(action.get("color"))
    if c:
        return c
    mirek = (action.get("color_temperature") or {}).get("mirek")
    if mirek:
        return couleurs.kelvin_vers_hex(1e6 / mirek)
    return BLANC_CHAUD


def _scene(scene):
    allumees = [a["action"] for a in scene.get("actions", []) if a.get("action", {}).get("on", {}).get("on")]
    intensites = [a["dimming"]["brightness"] for a in allumees if "dimming" in a]
    actif = scene.get("status", {}).get("active")
    return {
        "id": scene["id"],
        "nom": scene["metadata"]["name"],
        "couleurs": couleurs.palette([_couleur_action(a) for a in allumees]),
        "intensite": _arrondi(sum(intensites) / len(intensites)) if intensites else 0,
        "active": bool(actif) and actif != "inactive",
    }


def construire(brut, piece):
    salle = next((r for r in brut["room"] if r["metadata"]["name"] == piece), None)
    pieces = [r["metadata"]["name"] for r in brut["room"]]
    if salle is None:
        # La liste reste donnée : c'est elle qui permet d'en choisir une autre.
        return {**erreur(f"La pièce « {piece} » n'existe pas sur le bridge."), "pieces": pieces}

    appareils = {d["id"]: d for d in brut["device"]}
    lampes_par_id = {l["id"]: l for l in brut["light"]}
    ids = []
    for enfant in salle["children"]:
        if enfant["rtype"] == "device" and enfant["rid"] in appareils:
            ids += _ids_lampes_de_appareil(appareils[enfant["rid"]])
        elif enfant["rtype"] == "light":
            ids.append(enfant["rid"])
    ids = [i for i in ids if i in lampes_par_id]

    # Première zone (ordre du bridge) qui contient la lampe.
    zone_de = {}
    ordre_zones = []
    groupes_zone = {}  # nom de zone -> id de son grouped_light (une zone sans groupe n'est pas commandable)
    for z in brut["zone"]:
        nom = z["metadata"]["name"]
        ordre_zones.append(nom)
        gid = next((s["rid"] for s in z.get("services", []) if s.get("rtype") == "grouped_light"), None)
        if gid:
            groupes_zone[nom] = gid
        for e in z["children"]:
            if e["rtype"] == "light":
                zone_de.setdefault(e["rid"], nom)
    rang = {nom: i for i, nom in enumerate(ordre_zones)}
    rang[AUTRES] = len(ordre_zones)

    lampes = [_lampe(lampes_par_id[i], zone_de.get(i, AUTRES)) for i in ids]
    lampes.sort(key=lambda l: rang[l["zone"]])  # tri stable : l'ordre du bridge reste dans une zone

    # Les comptes suivent les lampes affichées sous chaque titre : ce que la page recompte aussi.
    zones = []
    for nom in ordre_zones:
        dedans = [l for l in lampes if l["zone"] == nom]
        if dedans and nom in groupes_zone:
            zones.append({"id": groupes_zone[nom], "nom": nom, "allumees": sum(1 for l in dedans if l["on"]), "total": len(dedans)})

    groupe_id = next((s["rid"] for s in salle.get("services", []) if s["rtype"] == "grouped_light"), None)
    groupe = next((g for g in brut["grouped_light"] if g["id"] == groupe_id), {})

    return {
        "connexion": "ok",
        "piece": {
            "nom": piece,
            "on": bool(groupe.get("on", {}).get("on")),
            "intensite": _arrondi(groupe.get("dimming", {}).get("brightness", 0)),
            "allumees": sum(1 for l in lampes if l["on"]),
            "total": len(lampes),
        },
        "pieces": pieces,
        "scenes": [_scene(s) for s in brut["scene"] if s.get("group", {}).get("rid") == salle["id"]],
        "lampes": lampes,
        "zones": zones,
    }
