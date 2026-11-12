import contextlib
import io
import json
import stat
import tempfile
import unittest
from pathlib import Path

from hue_controller import reglages

IP = "192.0.2.77"
CLE = "cle-secrete-de-test"


class TestReglages(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dossier = Path(self._tmp.name)
        self.chemin = self.dossier / "sous" / "reglages.json"

    def test_aller_retour(self):
        r = {"bridge_ip": IP, "cle": CLE, "piece": "Cuisine"}
        reglages.enregistrer(r, self.chemin)
        self.assertEqual(reglages.charger(self.chemin), r)

    def test_fichier_absent(self):
        self.assertIsNone(reglages.charger(self.dossier / "absent.json"))

    def test_json_casse(self):
        self.chemin.parent.mkdir()
        self.chemin.write_text("{pas du json")
        self.assertIsNone(reglages.charger(self.chemin))

    def test_piece_par_defaut(self):
        self.chemin.parent.mkdir()
        self.chemin.write_text(json.dumps({"bridge_ip": IP, "cle": CLE}))
        self.assertEqual(reglages.charger(self.chemin)["piece"], "Séjour")

    def test_mode_600(self):
        reglages.enregistrer({"bridge_ip": IP, "cle": CLE, "piece": "Séjour"}, self.chemin)
        self.assertEqual(stat.S_IMODE(self.chemin.stat().st_mode), 0o600)

    def test_pas_de_temporaire_restant(self):
        reglages.enregistrer({"bridge_ip": IP, "cle": CLE, "piece": "Séjour"}, self.chemin)
        self.assertEqual([p.name for p in self.chemin.parent.iterdir()], ["reglages.json"])

    def _lancer(self, contenu):
        env = self.dossier / "faux.env"
        env.write_text(contenu)
        sortie, erreur = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(sortie), contextlib.redirect_stderr(erreur):
            code = reglages.principal(["--depuis", str(env)], self.chemin)
        return code, sortie.getvalue(), erreur.getvalue()

    def test_commande_depuis_env(self):
        code, sortie, erreur = self._lancer(
            f'# commentaire\nHUE_BRIDGE_IP="{IP}"\nHUE_APP_KEY={CLE}\nAUTRE=x\n'
        )
        self.assertEqual(code, 0)
        self.assertEqual(sortie, f"Réglages écrits dans {self.chemin}\n")
        self.assertNotIn(IP, sortie + erreur)
        self.assertNotIn(CLE, sortie + erreur)
        self.assertEqual(
            reglages.charger(self.chemin),
            {"bridge_ip": IP, "cle": CLE, "piece": "Séjour"},
        )

    def test_variable_absente(self):
        code, sortie, erreur = self._lancer(f"HUE_BRIDGE_IP={IP}\n")
        self.assertEqual(code, 1)
        self.assertIn("HUE_APP_KEY", erreur)
        self.assertNotIn(IP, sortie + erreur)
        self.assertFalse(self.chemin.exists())



class TestAdresseValide(unittest.TestCase):
    def test_acceptees(self):
        self.assertEqual(reglages.adresse_valide("  192.168.1.20 "), "192.168.1.20")
        self.assertEqual(reglages.adresse_valide("10.0.0.5"), "10.0.0.5")
        self.assertEqual(reglages.adresse_valide("philips-hue.local"), "philips-hue.local")

    def test_refusees(self):
        for texte in ("8.8.8.8", "", "   ", "http://192.168.1.2", "192.168.1.2:80", "a b", "user@hote",
                      "hote/chemin", "127.0.0.1", "224.0.0.1", "300.1.1.1", "::1", "fe80::1", "a" * 254, None, 12):
            with self.subTest(texte=texte):
                self.assertIsNone(reglages.adresse_valide(texte))


if __name__ == "__main__":
    unittest.main()
