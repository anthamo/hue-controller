"""Fabrique l'icône de l'app (`hue_controller/AppIcon.icns`) à partir d'une image carrée.

    uv run python outils/icone.py                          # design/icone/sombre.png
    uv run python outils/icone.py design/icone/claire.png  # l'autre version
    uv run python outils/icone.py --apercu /tmp/x.png      # écrit aussi l'image 1024 px pour la regarder

Les images de `design/icone/` sont des carrés pleins, sans transparence. Une icône du Mac est une forme arrondie de
824 px au centre d'un carré de 1024 px, avec des coins transparents : l'outil prend le centre de l'image (le cercle et
l'ampoule, sans les bords où la version sombre avait déjà un fond arrondi décalé), le met à cette taille et découpe les
coins. `iconutil`, livré avec macOS, assemble ensuite les tailles dans le fichier .icns.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from AppKit import (
    NSBezierPath,
    NSBitmapImageRep,
    NSCalibratedRGBColorSpace,
    NSCompositingOperationCopy,
    NSGraphicsContext,
    NSImage,
    NSImageInterpolationHigh,
    NSPNGFileType,
)

PROJET = Path(__file__).resolve().parent.parent
SOURCE = PROJET / "design" / "icone" / "sombre.png"
SORTIE = PROJET / "hue_controller" / "AppIcon.icns"

TOILE = 1024
FORME = 824              # la forme arrondie des icônes du Mac, centrée
RAYON = 185              # ses coins (22,4 % de 824)
CENTRE_SOURCE = (150, 874)  # la partie gardée de l'image source, de 1024 px de côté


def dessiner(source, taille):
    """L'icône à `taille` pixels de côté : la forme arrondie remplie du centre de l'image, coins transparents."""
    image = NSImage.alloc().initWithContentsOfFile_(str(source))
    if image is None:
        raise SystemExit(f"Image illisible : {source}")
    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, taille, taille, 8, 4, True, False, NSCalibratedRGBColorSpace, 0, 0)
    contexte = NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(contexte)
    contexte.setImageInterpolation_(NSImageInterpolationHigh)
    e = taille / TOILE
    marge = (TOILE - FORME) / 2 * e
    cadre = ((marge, marge), (FORME * e, FORME * e))
    NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(cadre, RAYON * e, RAYON * e).addClip()
    # L'image source fait 1024 points de côté ; on n'en garde que le centre.
    debut, fin = CENTRE_SOURCE
    pts = image.size().width / TOILE
    morceau = ((debut * pts, (TOILE - fin) * pts), ((fin - debut) * pts, (fin - debut) * pts))
    image.drawInRect_fromRect_operation_fraction_(cadre, morceau, NSCompositingOperationCopy, 1.0)
    NSGraphicsContext.restoreGraphicsState()
    return rep.representationUsingType_properties_(NSPNGFileType, None)


def fabriquer(source=SOURCE, sortie=SORTIE, apercu=None):
    if not shutil.which("iconutil"):
        raise SystemExit("iconutil est introuvable (il est livré avec macOS).")
    with tempfile.TemporaryDirectory() as d:
        jeu = Path(d) / "AppIcon.iconset"
        jeu.mkdir()
        for cote in (16, 32, 128, 256, 512):
            dessiner(source, cote).writeToFile_atomically_(str(jeu / f"icon_{cote}x{cote}.png"), True)
            dessiner(source, cote * 2).writeToFile_atomically_(str(jeu / f"icon_{cote}x{cote}@2x.png"), True)
        subprocess.run(["iconutil", "-c", "icns", str(jeu), "-o", str(sortie)], check=True)
    if apercu:
        dessiner(source, TOILE).writeToFile_atomically_(str(apercu), True)
    return sortie


if __name__ == "__main__":
    options = argparse.ArgumentParser(description="Fabriquer l'icône de Hue Controller.")
    options.add_argument("source", nargs="?", default=SOURCE, type=Path)
    options.add_argument("--apercu", type=Path, help="écrire aussi l'icône en 1024 px, pour la regarder")
    arguments = options.parse_args()
    print(fabriquer(arguments.source, apercu=arguments.apercu))
    sys.exit(0)
