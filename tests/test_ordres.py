import json
import unittest
from pathlib import Path

from hue_controller import couleurs, ordres

BRUT = json.loads((Path(__file__).parent / "donnees" / "bridge.json").read_text(encoding="utf-8"))
ETAT = {"connexion": "ok", "scenes": [{"id": "s1"}, {"id": "s2"}], "lampes": [
    {"id": "l1", "reglages": ["blanc", "teinte"], "kelvins": [2000, 6536]},
    {"id": "l2", "reglages": [], "kelvins": None},
    {"id": "l4", "reglages": ["blanc"], "kelvins": [2200, 6500]},
]}


class FauxBridge:
    def __init__(self):
        self.appels = []

    def lire(self, ressource):
        self.appels.append(ressource)
        return [f"{ressource}-neuf"]


class TestLecture(unittest.TestCase):
    def test_lire_tout(self):
        b = FauxBridge()
        brut = ordres.lire_tout(b)
        self.assertEqual(set(brut), set(ordres.RESSOURCES_FIXES + ordres.RESSOURCES_VIVES))
        self.assertEqual(sorted(b.appels), sorted(brut))

    def test_lire_vif_garde_les_fixes(self):
        b = FauxBridge()
        ancien = {r: [f"{r}-vieux"] for r in ordres.RESSOURCES_FIXES + ordres.RESSOURCES_VIVES}
        brut = ordres.lire_vif(b, ancien)
        self.assertEqual(sorted(b.appels), sorted(ordres.RESSOURCES_VIVES))
        for r in ordres.RESSOURCES_FIXES:
            self.assertEqual(brut[r], [f"{r}-vieux"])
        for r in ordres.RESSOURCES_VIVES:
            self.assertEqual(brut[r], [f"{r}-neuf"])


class TestGroupe(unittest.TestCase):
    def test_groupe_du_sejour(self):
        salle = next(r for r in BRUT["room"] if r["metadata"]["name"] == "Séjour")
        attendu = next(s["rid"] for s in salle["services"] if s["rtype"] == "grouped_light")
        self.assertEqual(ordres.groupe_de(BRUT, "Séjour"), attendu)

    def test_piece_inconnue(self):
        self.assertIsNone(ordres.groupe_de(BRUT, "Grenier"))


class TestTraduire(unittest.TestCase):
    def test_scene(self):
        self.assertEqual(
            ordres.traduire({"action": "scene", "id": "s1"}, ETAT, "g"),
            ("scene", "s1", {"recall": {"action": "active"}}),
        )

    def test_scene_inconnue(self):
        self.assertIsNone(ordres.traduire({"action": "scene", "id": "zz"}, ETAT, "g"))

    def test_scene_id_mauvais_type(self):
        self.assertIsNone(ordres.traduire({"action": "scene", "id": ["s1"]}, ETAT, "g"))
        self.assertIsNone(ordres.traduire({"action": "scene"}, ETAT, "g"))

    def test_piece(self):
        for on in (True, False):
            self.assertEqual(
                ordres.traduire({"action": "piece", "on": on}, ETAT, "g"),
                ("grouped_light", "g", {"on": {"on": on}}),
            )

    def test_piece_pas_un_booleen(self):
        for on in (1, 0, "true", None):
            self.assertIsNone(ordres.traduire({"action": "piece", "on": on}, ETAT, "g"))
        self.assertIsNone(ordres.traduire({"action": "piece"}, ETAT, "g"))

    def test_piece_sans_groupe(self):
        self.assertIsNone(ordres.traduire({"action": "piece", "on": True}, ETAT, None))

    def test_intensite(self):
        for n in (1, 50, 100, 33.5):
            self.assertEqual(
                ordres.traduire({"action": "piece", "intensite": n}, ETAT, "g"),
                ("grouped_light", "g", {"dimming": {"brightness": n}}),
            )

    def test_intensite_refusee(self):
        for n in (0, 0.5, 101, -3, True, False, "50", None, [50]):
            self.assertIsNone(ordres.traduire({"action": "piece", "intensite": n}, ETAT, "g"))
        self.assertIsNone(ordres.traduire({"action": "piece", "intensite": 50}, ETAT, None))

    def test_on_et_intensite_ensemble(self):
        self.assertIsNone(ordres.traduire({"action": "piece", "on": True, "intensite": 50}, ETAT, "g"))

    def test_refus_divers(self):
        self.assertIsNone(ordres.traduire({"action": "pret"}, ETAT, "g"))
        for m in ("scene", None, ["scene"], 3):
            self.assertIsNone(ordres.traduire(m, ETAT, "g"))

    def test_etat_absent_ou_pas_ok(self):
        m = {"action": "piece", "on": True}
        self.assertIsNone(ordres.traduire(m, None, "g"))
        self.assertIsNone(ordres.traduire(m, {"connexion": "erreur", "scenes": []}, "g"))
        self.assertIsNone(ordres.traduire({"action": "scene", "id": "s1"}, {"connexion": "erreur", "scenes": [{"id": "s1"}]}, "g"))


class TestLampe(unittest.TestCase):
    def test_on(self):
        for on in (True, False):
            self.assertEqual(
                ordres.traduire({"action": "lampe", "id": "l1", "on": on}, ETAT, None),
                ("light", "l1", {"on": {"on": on}}),
            )

    def test_intensite(self):
        for n in (1, 50, 100, 33.5):
            self.assertEqual(
                ordres.traduire({"action": "lampe", "id": "l2", "intensite": n}, ETAT, None),
                ("light", "l2", {"dimming": {"brightness": n}, "dynamics": {"duration": ordres.FONDU_MS}}),
            )

    def test_id_refuse(self):
        for m in ({"action": "lampe", "on": True}, {"action": "lampe", "id": "zz", "on": True},
                  {"action": "lampe", "id": ["l1"], "on": True}, {"action": "lampe", "id": 1, "on": True}):
            self.assertIsNone(ordres.traduire(m, ETAT, None))
        self.assertIsNone(ordres.traduire({"action": "lampe", "id": "l1", "on": True}, {"connexion": "ok"}, None))

    def test_corps_refuse(self):
        self.assertIsNone(ordres.traduire({"action": "lampe", "id": "l1", "on": True, "intensite": 50}, ETAT, None))
        self.assertIsNone(ordres.traduire({"action": "lampe", "id": "l1"}, ETAT, None))
        for on in (1, 0, "true", None):
            self.assertIsNone(ordres.traduire({"action": "lampe", "id": "l1", "on": on}, ETAT, None))
        for n in (0, 0.5, 101, -3, True, False, "50", None, [50]):
            self.assertIsNone(ordres.traduire({"action": "lampe", "id": "l1", "intensite": n}, ETAT, None))

    def test_kelvin(self):
        for k, mirek in ((2200, 455), (6500, 154), (2700, 370), (3000.0, 333)):
            self.assertEqual(
                ordres.traduire({"action": "lampe", "id": "l4", "kelvin": k}, ETAT, None),
                ("light", "l4", {"color_temperature": {"mirek": mirek}, "dynamics": {"duration": ordres.FONDU_MS}}),
            )

    def test_kelvin_refuse(self):
        for n in (2199, 6501, 0, -1, True, "3000", None, [3000]):
            self.assertIsNone(ordres.traduire({"action": "lampe", "id": "l4", "kelvin": n}, ETAT, None))
        self.assertIsNone(ordres.traduire({"action": "lampe", "id": "l2", "kelvin": 3000}, ETAT, None))
        # Une lampe de couleur qui a aussi le blanc l'accepte : elle peut être mise en blanc, à la chaleur voulue.
        self.assertEqual(
            ordres.traduire({"action": "lampe", "id": "l1", "kelvin": 4000}, ETAT, None),
            ("light", "l1", {"color_temperature": {"mirek": 250}, "dynamics": {"duration": ordres.FONDU_MS}}),
        )

    def test_couleur(self):
        o = ordres.traduire({"action": "lampe", "id": "l1", "teinte": 240, "saturation": 100}, ETAT, None)
        self.assertEqual(o[:2], ("light", "l1"))
        self.assertEqual(o[2]["dynamics"], {"duration": ordres.FONDU_MS})
        x, y = couleurs.hex_vers_xy(couleurs.couleur_de(240, 100))
        self.assertEqual(o[2]["color"], {"xy": {"x": round(x, 4), "y": round(y, 4)}})
        for t, s in ((0, 0), (360, 100), (12.5, 33.3)):
            self.assertIsNotNone(ordres.traduire({"action": "lampe", "id": "l1", "teinte": t, "saturation": s}, ETAT, None))

    def test_couleur_refusee(self):
        def m(**kw):
            return ordres.traduire({"action": "lampe", "id": "l1", **kw}, ETAT, None)
        for n in (-1, 361, True, "120", None, [120]):
            self.assertIsNone(m(teinte=n, saturation=50))
        for n in (-1, 101, True, "50", None, [50]):
            self.assertIsNone(m(teinte=120, saturation=n))
        self.assertIsNone(m(teinte=120))
        self.assertIsNone(m(saturation=50))
        # Lampe sans "teinte" dans ses réglages.
        for i in ("l2", "l4"):
            self.assertIsNone(ordres.traduire({"action": "lampe", "id": i, "teinte": 120, "saturation": 50}, ETAT, None))

    def test_deux_actions_refusees(self):
        def m(**kw):
            return ordres.traduire({"action": "lampe", "id": "l1", **kw}, ETAT, None)
        self.assertIsNone(m(kelvin=3000, teinte=120, saturation=50))
        self.assertIsNone(m(on=True, kelvin=3000))
        self.assertIsNone(m(on=True, teinte=120, saturation=50))
        self.assertIsNone(m(intensite=50, teinte=120, saturation=50))


ETAT_ZONES = {"connexion": "ok", "scenes": [], "lampes": [], "zones": [{"id": "z1", "nom": "Salon", "allumees": 1, "total": 2}]}


class TestZone(unittest.TestCase):
    def test_on(self):
        for on in (True, False):
            self.assertEqual(
                ordres.traduire({"action": "zone", "id": "z1", "on": on}, ETAT_ZONES, None),
                ("grouped_light", "z1", {"on": {"on": on}}),
            )

    def test_id_refuse(self):
        for m in ({"action": "zone", "on": True}, {"action": "zone", "id": "zz", "on": True},
                  {"action": "zone", "id": ["z1"], "on": True}, {"action": "zone", "id": 1, "on": True}):
            self.assertIsNone(ordres.traduire(m, ETAT_ZONES, None))
        self.assertIsNone(ordres.traduire({"action": "zone", "id": "z1", "on": True}, ETAT, None))
        self.assertIsNone(ordres.traduire({"action": "zone", "id": "z1", "on": True}, {"connexion": "ok", "zones": []}, None))

    def test_corps_refuse(self):
        self.assertIsNone(ordres.traduire({"action": "zone", "id": "z1"}, ETAT_ZONES, None))
        for on in (1, 0, "true", None):
            self.assertIsNone(ordres.traduire({"action": "zone", "id": "z1", "on": on}, ETAT_ZONES, None))
        self.assertIsNone(ordres.traduire({"action": "zone", "id": "z1", "on": True, "intensite": 50}, ETAT_ZONES, None))
        self.assertIsNone(ordres.traduire({"action": "zone", "id": "z1", "intensite": 50}, ETAT_ZONES, None))


PAS = ordres.Cadence.INTERVALLES["light"]


def dimming(n, groupe="g"):
    return ("grouped_light", groupe, {"dimming": {"brightness": n}})


class TestCadence(unittest.TestCase):
    def test_rien(self):
        c = ordres.Cadence()
        self.assertTrue(c.vide())
        self.assertEqual(c.prochain(0), (None, None))

    def test_dix_intensites(self):
        c = ordres.Cadence()
        c.poser(dimming(1))
        self.assertEqual(c.prochain(0), (dimming(1), 0))
        for n in range(2, 11):
            c.poser(dimming(n))
        self.assertFalse(c.vide())
        self.assertEqual(c.prochain(0.5), (None, 0.5))
        self.assertEqual(c.prochain(1.0), (dimming(10), 0))
        self.assertTrue(c.vide())
        self.assertEqual(c.prochain(5), (None, None))

    def test_scene_ne_attend_pas(self):
        c = ordres.Cadence()
        c.poser(dimming(1))
        c.prochain(0)
        c.poser(dimming(2))
        scene = ("scene", "s1", {"recall": {"action": "active"}})
        c.poser(scene)
        self.assertEqual(c.prochain(0.2), (scene, 0))
        self.assertEqual(c.prochain(0.2), (None, 0.8))

    def test_scene_deux_fois_de_suite(self):
        c = ordres.Cadence()
        scene = ("scene", "s1", {"recall": {"action": "active"}})
        c.poser(scene)
        self.assertEqual(c.prochain(0), (scene, 0))
        c.poser(scene)
        self.assertEqual(c.prochain(0), (scene, 0))

    def test_lampes_differentes(self):
        c = ordres.Cadence()
        a = ("light", "a", {"dimming": {"brightness": 10}})
        b = ("light", "b", {"dimming": {"brightness": 20}})
        c.poser(a)
        c.poser(b)
        self.assertEqual(c.prochain(0), (a, 0))
        self.assertEqual(c.prochain(0.05), (None, PAS - 0.05))
        self.assertEqual(c.prochain(PAS), (b, 0))

    def test_deux_lampes_une_ressource(self):
        c = ordres.Cadence()
        a = ordres.traduire({"action": "lampe", "id": "l1", "intensite": 10}, ETAT, None)
        b = ordres.traduire({"action": "lampe", "id": "l2", "intensite": 20}, ETAT, None)
        c.poser(a)
        c.poser(b)
        self.assertEqual(c.prochain(0), (a, 0))
        self.assertEqual(c.prochain(0), (None, PAS))
        self.assertEqual(c.prochain(PAS), (b, 0))

    def test_on_et_dimming_ne_se_remplacent_pas(self):
        c = ordres.Cadence()
        allume = ("light", "a", {"on": {"on": True}})
        dim = ("light", "a", {"dimming": {"brightness": 10}})
        c.poser(allume)
        c.poser(dim)
        self.assertEqual(c.prochain(0), (allume, 0))
        self.assertEqual(c.prochain(PAS), (dim, 0))
        self.assertTrue(c.vide())

    def test_remplacement_garde_la_place(self):
        c = ordres.Cadence()
        c.poser(("light", "a", {"dimming": 1}))
        c.poser(("light", "b", {"dimming": 1}))
        c.poser(("light", "a", {"dimming": 2}))
        self.assertEqual(c.prochain(0)[0], ("light", "a", {"dimming": 2}))


if __name__ == "__main__":
    unittest.main()
