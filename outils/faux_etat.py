"""Fabrique l'état du faux bridge de la page (hue_controller/panneau/faux_etat.js) à partir des données de test.

Les données figées ont tout éteint : on y applique une scène, pour que la page de démonstration ait des lampes
allumées et une scène en cours. Aucun appel au bridge.

    PYTHONPATH=. uv run python outils/faux_etat.py
"""

import json
from pathlib import Path

from hue_controller import etat

RACINE = Path(__file__).resolve().parent.parent
SCENE = "Coucher de soleil sur la savane"

brut = json.loads((RACINE / "tests/donnees/bridge.json").read_text())
scene = next(s for s in brut["scene"] if s["metadata"]["name"] == SCENE)
lampes = {l["id"]: l for l in brut["light"]}
for action in scene["actions"]:
    lampe, voulu = lampes[action["target"]["rid"]], action["action"]
    lampe["on"] = voulu.get("on", {"on": True})
    if "dimming" in voulu:
        lampe["dimming"]["brightness"] = voulu["dimming"]["brightness"]
    if "color" in voulu and "color" in lampe:
        lampe["color"]["xy"] = voulu["color"]["xy"]
        if "color_temperature" in lampe:
            lampe["color_temperature"].update(mirek=None, mirek_valid=False)
    elif voulu.get("color_temperature", {}).get("mirek") and "color_temperature" in lampe:
        lampe["color_temperature"].update(mirek=voulu["color_temperature"]["mirek"], mirek_valid=True)
scene["status"] = {"active": "static"}
piece = next(r for r in brut["room"] if r["metadata"]["name"] == "Séjour")
groupe = next(s["rid"] for s in piece["services"] if s["rtype"] == "grouped_light")
allumees = [l for l in etat.construire(brut, "Séjour")["lampes"] if l["on"]]
for g in brut["grouped_light"]:
    if g["id"] == groupe:
        g["on"] = {"on": bool(allumees)}
        g["dimming"] = {"brightness": sum(l["intensite"] for l in allumees) / max(1, len(allumees))}

resultat = etat.construire(brut, "Séjour")
sortie = RACINE / "hue_controller/panneau/faux_etat.js"
sortie.write_text("window.ETAT_FAUX = " + json.dumps(resultat, ensure_ascii=False) + ";\n")
print(resultat["piece"], "|", len(resultat["scenes"]), "scènes |", [l["zone"] for l in resultat["lampes"]].count("Salon"), "lampes au Salon")
print("→", sortie)
