import unittest
from unittest import mock

from hue_controller.bridge import Bridge, BridgeErreur

CLE = "cle-secrete-123"


class FauxTransport:
    def __init__(self, reponse=None, exception=None):
        self.reponse = reponse if reponse is not None else {"data": []}
        self.exception = exception
        self.appels = []

    def __call__(self, methode, chemin, corps):
        self.appels.append((methode, chemin, corps))
        if self.exception:
            raise self.exception
        return self.reponse


class TestTransport(unittest.TestCase):
    def test_lire_appelle_le_bon_chemin_et_rend_data(self):
        t = FauxTransport({"data": [{"id": "a"}]})
        self.assertEqual(Bridge("1.2.3.4", CLE, t).lire("light"), [{"id": "a"}])
        self.assertEqual(t.appels, [("GET", "/clip/v2/resource/light", None)])

    def test_ecrire_envoie_le_bon_corps(self):
        t = FauxTransport()
        corps = {"recall": {"action": "active"}}
        Bridge("1.2.3.4", CLE, t).ecrire("scene", "abc", corps)
        self.assertEqual(t.appels, [("PUT", "/clip/v2/resource/scene/abc", corps)])

    def test_exception_du_transport_devient_bridge_erreur(self):
        t = FauxTransport(exception=OSError(f"boum {CLE}"))
        with self.assertRaises(BridgeErreur) as c:
            Bridge("1.2.3.4", CLE, t).lire("light")
        self.assertNotIn(CLE, str(c.exception))

    def test_reponse_sans_data(self):
        with self.assertRaises(BridgeErreur):
            Bridge("1.2.3.4", CLE, FauxTransport({"errors": []})).lire("light")


class FausseReponse:
    def __init__(self, statut=200, corps=b'{"data": [1]}'):
        self.status = statut
        self._corps = corps

    def read(self):
        return self._corps


class FausseConnexion:
    def __init__(self, reponses):
        self.reponses = list(reponses)  # une réponse, ou une exception à lever
        self.requetes = []
        self.fermee = False

    def request(self, methode, chemin, body=None, headers=None):
        self.requetes.append((methode, chemin, body, headers))

    def getresponse(self):
        suivant = self.reponses.pop(0)
        if isinstance(suivant, Exception):
            raise suivant
        return suivant

    def close(self):
        self.fermee = True


class TestReseau(unittest.TestCase):
    def bridge_avec(self, *connexions):
        patch = mock.patch("http.client.HTTPSConnection", side_effect=list(connexions))
        self.creation = patch.start()
        self.addCleanup(patch.stop)
        return Bridge("1.2.3.4", CLE)

    def test_en_tete_cle_et_corps_json(self):
        c = FausseConnexion([FausseReponse(200, b"{}")])
        Bridge_ = self.bridge_avec(c)
        Bridge_.ecrire("light", "x", {"on": {"on": True}})
        methode, chemin, body, en_tetes = c.requetes[0]
        self.assertEqual((methode, chemin), ("PUT", "/clip/v2/resource/light/x"))
        self.assertEqual(body, '{"on": {"on": true}}')
        self.assertEqual(en_tetes["hue-application-key"], CLE)

    def test_connexion_gardee_ouverte(self):
        c = FausseConnexion([FausseReponse(), FausseReponse()])
        b = self.bridge_avec(c)
        b.lire("light")
        b.lire("room")
        self.assertEqual(self.creation.call_count, 1)

    def test_une_nouvelle_tentative_si_la_connexion_est_tombee(self):
        morte = FausseConnexion([ConnectionResetError()])
        neuve = FausseConnexion([FausseReponse()])
        b = self.bridge_avec(morte, neuve)
        self.assertEqual(b.lire("light"), [1])
        self.assertTrue(morte.fermee)

    def test_deux_pannes_de_suite_levent_bridge_erreur(self):
        b = self.bridge_avec(
            FausseConnexion([OSError(CLE)]), FausseConnexion([OSError(CLE)])
        )
        with self.assertRaises(BridgeErreur) as c:
            b.lire("light")
        self.assertNotIn(CLE, str(c.exception))

    def test_statut_hors_2xx(self):
        b = self.bridge_avec(FausseConnexion([FausseReponse(403, b"{}")]))
        with self.assertRaises(BridgeErreur) as c:
            b.lire("light")
        self.assertNotIn(CLE, str(c.exception))

    def test_json_illisible(self):
        b = self.bridge_avec(FausseConnexion([FausseReponse(200, b"<html>")]))
        with self.assertRaises(BridgeErreur):
            b.lire("light")


if __name__ == "__main__":
    unittest.main()
