import unittest

from hue_controller import appairage


class TestAppairage(unittest.TestCase):
    def test_trouver(self):
        self.assertEqual(appairage.trouver(lambda: [{"id": "x", "internalipaddress": "192.168.0.20"}, {"id": "y"}]), ["192.168.0.20"])

    def test_trouver_en_panne(self):
        def panne():
            raise OSError("pas de réseau")
        with self.assertRaises(appairage.AppairageErreur):
            appairage.trouver(panne)

    def test_bouton_pas_appuye(self):
        self.assertIsNone(appairage.demander_cle("x", lambda corps: [{"error": {"type": 101, "description": "link button not pressed"}}]))

    def test_cle_obtenue(self):
        vus = []
        def poster(corps):
            vus.append(corps)
            return [{"success": {"username": "la-cle", "clientkey": "autre"}}]
        self.assertEqual(appairage.demander_cle("x", poster), "la-cle")
        self.assertEqual(vus, [{"devicetype": "hue_controller#mac", "generateclientkey": True}])

    def test_autre_erreur(self):
        with self.assertRaises(appairage.AppairageErreur):
            appairage.demander_cle("x", lambda corps: [{"error": {"type": 7}}])

    def test_bridge_muet_sans_fuite(self):
        def panne(corps):
            raise OSError("https://192.168.0.20/api secret")
        with self.assertRaises(appairage.AppairageErreur) as contexte:
            appairage.demander_cle("x", panne)
        self.assertNotIn("secret", str(contexte.exception))

    def test_attendre_puis_obtenir(self):
        reponses = [[{"error": {"type": 101}}], [{"error": {"type": 101}}], [{"success": {"username": "la-cle"}}]]
        self.assertEqual(appairage.attendre_cle("x", lambda corps: reponses.pop(0), pause=lambda s: None), "la-cle")

    def test_attendre_trop_longtemps(self):
        with self.assertRaises(appairage.AppairageErreur):
            appairage.attendre_cle("x", lambda corps: [{"error": {"type": 101}}], essais=3, pause=lambda s: None)

    def test_choisir(self):
        self.assertEqual(appairage.choisir("?", ["Séjour"], lire=lambda q: "9", dire=lambda *a: None), "Séjour")
        reponses = iter(["x", "5", "2"])
        self.assertEqual(appairage.choisir("?", ["Séjour", "Chambre"], lire=lambda q: next(reponses), dire=lambda *a: None), "Chambre")


if __name__ == "__main__":
    unittest.main()
