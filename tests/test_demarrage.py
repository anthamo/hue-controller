import os
import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hue_controller import demarrage


class TestDemarrage(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.chemin = Path(self._tmp.name) / "LaunchAgents" / "essai.plist"

    def test_activer_ecrit_un_plist_relisible(self):
        demarrage.activer(self.chemin, uv="/opt/uv", dossier="/projet")
        brut = plistlib.loads(self.chemin.read_bytes())
        self.assertEqual(brut["Label"], demarrage.ETIQUETTE)
        self.assertEqual(
            brut["ProgramArguments"],
            ["/opt/uv", "run", "--project", "/projet", "python", "-m", "hue_controller"],
        )
        self.assertEqual(brut["WorkingDirectory"], "/projet")
        self.assertIs(brut["RunAtLoad"], True)
        self.assertNotIn("KeepAlive", brut)
        self.assertEqual(list(self.chemin.parent.glob("*.tmp")), [])

    def test_actif_suit(self):
        self.assertFalse(demarrage.actif(self.chemin))
        demarrage.activer(self.chemin, uv="/opt/uv", dossier="/projet")
        self.assertTrue(demarrage.actif(self.chemin))
        demarrage.desactiver(self.chemin)
        self.assertFalse(demarrage.actif(self.chemin))

    def test_desactiver_deux_fois(self):
        demarrage.activer(self.chemin, uv="/opt/uv", dossier="/projet")
        demarrage.desactiver(self.chemin)
        demarrage.desactiver(self.chemin)

    def test_uv_introuvable(self):
        with mock.patch.object(demarrage.shutil, "which", lambda _: None):
            with self.assertRaises(RuntimeError):
                demarrage.activer(self.chemin, uv=None, dossier="/projet")
        self.assertFalse(self.chemin.exists())

    def test_dossier_par_defaut_est_le_projet(self):
        demarrage.activer(self.chemin, uv="/opt/uv")
        brut = plistlib.loads(self.chemin.read_bytes())
        self.assertTrue((Path(brut["WorkingDirectory"]) / "hue_controller").is_dir())


class TestLanceur(unittest.TestCase):
    def test_installer_app(self):
        with tempfile.TemporaryDirectory() as d:
            app = demarrage.installer_app(app=Path(d) / "Hue Controller.app", uv="/chemin/uv", dossier="/un dossier/projet")
            infos = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
            self.assertEqual(infos["CFBundleExecutable"], "hue-controller")
            self.assertTrue(infos["LSUIElement"])
            programme = app / "Contents" / "MacOS" / "hue-controller"
            self.assertTrue(os.access(programme, os.X_OK))
            self.assertIn("'/un dossier/projet'", programme.read_text())


if __name__ == "__main__":
    unittest.main()
