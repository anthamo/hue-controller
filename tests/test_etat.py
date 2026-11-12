import copy
import json
import re
import unittest
from pathlib import Path

from hue_controller import etat

BRUT = json.loads((Path(__file__).parent / "donnees" / "bridge.json").read_text(encoding="utf-8"))
HEX = re.compile(r"^#[0-9a-f]{6}$")


class TestEtat(unittest.TestCase):
    def setUp(self):
        self.e = etat.construire(BRUT, "Séjour")

    def test_comptes(self):
        self.assertEqual(self.e["connexion"], "ok")
        self.assertEqual(len(self.e["lampes"]), 11)
        self.assertEqual(len(self.e["scenes"]), 22)
        self.assertEqual(self.e["piece"]["nom"], "Séjour")
        self.assertEqual(self.e["piece"]["total"], 11)
        self.assertEqual(self.e["piece"]["allumees"], sum(l["on"] for l in self.e["lampes"]))

    def test_zones(self):
        zones = []
        for l in self.e["lampes"]:
            if l["zone"] not in zones:
                zones.append(l["zone"])
        # Ordre des zones du bridge : Cuisine, puis Salon, puis Salle à manger.
        self.assertEqual(zones, [z["metadata"]["name"] for z in BRUT["zone"]])
        self.assertEqual(set(zones), {"Salon", "Salle à manger", "Cuisine"})

    def test_zones_commandables(self):
        zones = self.e["zones"]
        self.assertEqual([z["nom"] for z in zones], [z["metadata"]["name"] for z in BRUT["zone"]])
        self.assertEqual(sum(z["total"] for z in zones), 11)
        groupes = {g["id"] for g in BRUT["grouped_light"]}
        for z in zones:
            self.assertIsInstance(z["id"], str)
            self.assertTrue(z["id"])
            self.assertIn(z["id"], groupes)
            dedans = [l for l in self.e["lampes"] if l["zone"] == z["nom"]]
            self.assertEqual((z["allumees"], z["total"]), (sum(l["on"] for l in dedans), len(dedans)))

    def test_zone_sans_groupe_ignoree(self):
        brut = copy.deepcopy(BRUT)
        brut["zone"][0]["services"] = []
        zones = etat.construire(brut, "Séjour")["zones"]
        self.assertEqual([z["nom"] for z in zones], [z["metadata"]["name"] for z in BRUT["zone"][1:]])

    def test_zones_vides_en_erreur(self):
        self.assertEqual(etat.erreur("x")["zones"], [])
        self.assertEqual(etat.sans_reglages("x")["zones"], [])

    def test_plafond_cuisine_sans_reglages(self):
        l = next(l for l in self.e["lampes"] if l["nom"] == "Plafond cuisine")
        self.assertEqual(l["reglages"], [])
        self.assertIsNone(l["mode"])
        if l["on"]:
            self.assertEqual(l["couleur"], "#ffe2bd")

    def test_au_plus_une_scene_active(self):
        self.assertLessEqual(sum(s["active"] for s in self.e["scenes"]), 1)

    def test_couleurs_et_palettes(self):
        for s in self.e["scenes"]:
            self.assertTrue(1 <= len(s["couleurs"]) <= 5, s["nom"])
            for c in s["couleurs"]:
                self.assertRegex(c, HEX)
        for l in self.e["lampes"]:
            if l["on"]:
                self.assertRegex(l["couleur"], HEX)
            else:
                self.assertIsNone(l["couleur"])

    def test_json(self):
        self.assertEqual(json.loads(json.dumps(self.e)), self.e)

    def test_piece_introuvable(self):
        e = etat.construire(BRUT, "Grenier")
        self.assertEqual(e, {**etat.erreur("La pièce « Grenier » n'existe pas sur le bridge."), "pieces": self.e["pieces"]})
        self.assertTrue(e["pieces"])
        self.assertEqual(e["connexion"], "erreur")
        self.assertEqual((e["piece"], e["scenes"], e["lampes"]), (None, [], []))

    def test_pieces(self):
        noms = [r["metadata"]["name"] for r in BRUT["room"]]
        self.assertEqual(len(noms), 2)
        self.assertEqual(self.e["pieces"], noms)
        self.assertIn("Séjour", self.e["pieces"])
        self.assertEqual(etat.erreur("x")["pieces"], [])
        self.assertEqual(etat.sans_reglages("x")["pieces"], [])

    def test_sans_reglages(self):
        e = etat.sans_reglages("x")
        self.assertEqual(e["connexion"], "reglages")
        self.assertEqual(e["message"], "x")

    def test_lampes_allumees(self):
        brut = copy.deepcopy(BRUT)
        for l in brut["light"]:
            l["on"] = {"on": True}
        e = etat.construire(brut, "Séjour")
        self.assertEqual(e["piece"]["allumees"], 11)
        for l in e["lampes"]:
            self.assertRegex(l["couleur"], HEX)
        cible = next(l for l in brut["light"] if l["id"] == e["lampes"][1]["id"])
        cible["color_temperature"] = {"mirek": 370, "mirek_valid": True}
        blanc = next(l for l in etat.construire(brut, "Séjour")["lampes"] if l["id"] == cible["id"])
        self.assertEqual((blanc["mode"], blanc["kelvin"]), ("blanc", 2703))

    def test_kelvins(self):
        avec = [l for l in self.e["lampes"] if l["kelvins"] is not None]
        self.assertEqual(len(avec), 10)
        for l in avec:
            self.assertEqual(l["kelvins"], [2000, 6536])
        cuisine = next(l for l in self.e["lampes"] if l["nom"] == "Plafond cuisine")
        self.assertIsNone(cuisine["kelvins"])

    def test_teinte_et_saturation(self):
        couleur = [l for l in self.e["lampes"] if "teinte" in l["reglages"]]
        self.assertEqual(len(couleur), 10)
        for l in couleur:
            self.assertIsInstance(l["teinte"], int)
            self.assertIsInstance(l["saturation"], int)
            self.assertTrue(0 <= l["teinte"] <= 360)
            self.assertTrue(0 <= l["saturation"] <= 100)
        cuisine = next(l for l in self.e["lampes"] if l["nom"] == "Plafond cuisine")
        self.assertIsNone(cuisine["teinte"])
        self.assertIsNone(cuisine["saturation"])

    def test_teinte_d_un_bleu(self):
        brut = copy.deepcopy(BRUT)
        cible = next(l for l in brut["light"] if "color" in l)
        cible["color"]["xy"] = {"x": 0.15, "y": 0.06}
        cible["on"] = {"on": False}  # même éteinte, la couleur rapportée donne le couple
        lampe = next(l for l in etat.construire(brut, "Séjour")["lampes"] if l["id"] == cible["id"])
        self.assertTrue(220 <= lampe["teinte"] <= 260)
        self.assertGreater(lampe["saturation"], 80)

    def test_scene_active(self):
        brut = copy.deepcopy(BRUT)
        piece_id = next(r["id"] for r in brut["room"] if r["metadata"]["name"] == "Séjour")
        cible = next(s for s in brut["scene"] if s["group"]["rid"] == piece_id)
        cible["status"]["active"] = "static"
        e = etat.construire(brut, "Séjour")
        actives = [s for s in e["scenes"] if s["active"]]
        self.assertEqual([s["id"] for s in actives], [cible["id"]])


if __name__ == "__main__":
    unittest.main()
