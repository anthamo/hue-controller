"""Rend publiable une lecture du bridge (tests/donnees/bridge.json) : identifiants remplacés, détails d'installation retirés.

Les identifiants du bridge sont remplacés par d'autres, toujours les mêmes pour un même identifiant (les liens entre
ressources restent justes). Les numéros de version et les anciens identifiants sont retirés. Les noms des lampes et
des scènes sont gardés : les tests et la page de démonstration s'en servent.

    uv run python outils/anonymiser.py     # réécrit le fichier sur place ; sans effet si c'est déjà fait
"""

import json
import re
import uuid
from pathlib import Path

FICHIER = Path(__file__).resolve().parent.parent / "tests/donnees/bridge.json"
ESPACE = uuid.UUID("6f1d2c3e-0000-4000-8000-000000000000")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
A_RETIRER = {"id_v1", "software_version", "hardware_platform_type"}
NOMS = {"Chambre des parents": "Chambre"}
MARQUE = "anonymise"


def nettoyer(objet):
    if isinstance(objet, dict):
        return {k: nettoyer(v) for k, v in objet.items() if k not in A_RETIRER}
    if isinstance(objet, list):
        return [nettoyer(v) for v in objet]
    if isinstance(objet, str):
        if UUID.match(objet):
            return str(uuid.uuid5(ESPACE, objet))
        return NOMS.get(objet, objet)
    return objet


if __name__ == "__main__":
    brut = json.loads(FICHIER.read_text())
    if brut.get(MARQUE):
        print("Déjà fait.")
    else:
        propre = nettoyer(brut)
        propre[MARQUE] = True
        FICHIER.write_text(json.dumps(propre, ensure_ascii=False, indent=1))
        print("Fait :", FICHIER)
