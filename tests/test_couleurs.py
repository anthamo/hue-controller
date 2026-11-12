import unittest

from hue_controller.couleurs import couleur_de, hex_vers_xy, kelvin_vers_hex, melange, palette, saturation_de, teinte_de, xy_vers_hex


def canaux(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


class TestCouleurs(unittest.TestCase):
    def test_xy_orange(self):
        r, g, b = canaux(xy_vers_hex(0.5, 0.4))
        self.assertGreater(r, g)
        self.assertGreater(g, b)
        self.assertTrue(20 <= teinte_de(xy_vers_hex(0.5, 0.4)) <= 50)

    def test_xy_y_nul(self):
        self.assertEqual(xy_vers_hex(0.3, 0), "#ffffff")

    def test_kelvin_chaud_plus_rouge_que_froid(self):
        chaud, froid = canaux(kelvin_vers_hex(2700)), canaux(kelvin_vers_hex(6500))
        self.assertGreater(chaud[0] - chaud[2], froid[0] - froid[2])

    def test_kelvin_forme_hex(self):
        for k in (2000, 4000, 6500):
            self.assertRegex(kelvin_vers_hex(k), r"^#[0-9a-f]{6}$")

    def test_melange(self):
        self.assertEqual(melange("#000000", "#ffffff", 0.5), "#808080")
        self.assertEqual(melange("#102030", "#ffffff", 0), "#102030")

    def test_teinte(self):
        self.assertEqual(teinte_de("#ff0000"), 0)
        self.assertEqual(teinte_de("#00ff00"), 120)
        self.assertEqual(teinte_de("#0000ff"), 240)

    def test_palette_huit_en_cinq_triees(self):
        huit = ["#0000ff", "#ff0000", "#00ff00", "#ffff00", "#00ffff", "#ff00ff", "#ff8000", "#8000ff"]
        p = palette(huit)
        self.assertEqual(len(p), 5)
        teintes = [teinte_de(c) for c in p]
        self.assertEqual(teintes, sorted(teintes))

    def test_palette_uniques(self):
        self.assertEqual(palette(["#ff0000", "#ff0000"]), ["#ff0000"])

    def test_palette_vide(self):
        self.assertEqual(palette([]), [])

    def test_couleur_de(self):
        self.assertEqual(couleur_de(0, 100), "#ff0000")
        self.assertEqual(couleur_de(240, 100), "#0000ff")
        self.assertEqual(couleur_de(120, 50), "#80ff80")
        for t in (0, 77, 240, 359):
            self.assertEqual(couleur_de(t, 0), "#ffffff")
        self.assertEqual(couleur_de(360, 100), couleur_de(0, 100))
        self.assertEqual(couleur_de(-120, 100), couleur_de(240, 100))
        self.assertEqual(couleur_de(0, 150), couleur_de(0, 100))
        self.assertEqual(couleur_de(0, -5), "#ffffff")

    def test_saturation_de(self):
        self.assertEqual(saturation_de("#ff0000"), 100)
        self.assertEqual(saturation_de("#80ff80"), 50)
        self.assertEqual(saturation_de("#ffffff"), 0)
        self.assertEqual(saturation_de("#808080"), 0)
        self.assertEqual(saturation_de("#000000"), 0)

    def test_couleur_de_saturation_aller_retour(self):
        for t, s in ((30, 40), (200, 75), (310, 100)):
            c = couleur_de(t, s)
            self.assertLessEqual(abs(saturation_de(c) - s), 1)

    def test_hex_vers_xy_noir(self):
        self.assertEqual(hex_vers_xy("#000000"), (0.3127, 0.3290))

    def test_aller_retour_teinte(self):
        for d in (0, 60, 120, 180, 240, 300):
            c = couleur_de(d, 100)
            retour = teinte_de(xy_vers_hex(*hex_vers_xy(c)))
            ecart = abs(retour - teinte_de(c))
            ecart = min(ecart, 360 - ecart)
            self.assertLessEqual(ecart, 12)


if __name__ == "__main__":
    unittest.main()
