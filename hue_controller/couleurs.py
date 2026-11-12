"""Conversions de couleurs du bridge (xy, kelvins) vers des couleurs d'écran (#rrggbb)."""

import math


def _arrondi(v):
    # Comme Math.round de la maquette (moitié vers le haut), pas l'arrondi bancaire de Python.
    return math.floor(v + 0.5)


def _vers_rvb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def _vers_hex(canaux):
    return "#" + "".join(f"{max(0, min(255, _arrondi(v))):02x}" for v in canaux)


def melange(a, b, t):
    """Mélange deux couleurs hex : t = 0 rend a, t = 1 rend b."""
    return _vers_hex([va + (vb - va) * t for va, vb in zip(_vers_rvb(a), _vers_rvb(b))])


def _gamma(v):
    return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


def xy_vers_hex(x, y):
    """CIE xy vers sRGB à pleine luminosité, matrice Wide RGB D65 utilisée par Philips Hue."""
    if y <= 0:
        # xy n'a pas de sens avec y = 0 (division par zéro) : blanc neutre.
        return "#ffffff"
    Y = 1.0
    X = Y / y * x
    Z = Y / y * (1 - x - y)
    r = X * 1.656492 - Y * 0.354851 - Z * 0.255038
    g = -X * 0.707196 + Y * 1.655397 + Z * 0.036152
    b = X * 0.051713 - Y * 0.121364 + Z * 1.011530
    r, g, b = max(r, 0.0), max(g, 0.0), max(b, 0.0)
    plus_grand = max(r, g, b)
    if plus_grand <= 0:
        return "#ffffff"
    return _vers_hex([_gamma(c / plus_grand) * 255 for c in (r, g, b)])


def hex_vers_xy(h):
    """Inverse de xy_vers_hex : sRGB vers CIE xy, même matrice Wide RGB D65 de Hue."""
    r, g, b = ((c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) for c in (v / 255 for v in _vers_rvb(h)))
    X = r * 0.664511 + g * 0.154324 + b * 0.162028
    Y = r * 0.283881 + g * 0.668433 + b * 0.047685
    Z = r * 0.000088 + g * 0.072310 + b * 0.986039
    somme = X + Y + Z
    if somme <= 0:
        return (0.3127, 0.3290)  # noir : xy n'est pas défini, on rend le point blanc D65
    return (X / somme, Y / somme)


def couleur_de(teinte, saturation):
    """Couleur de cette teinte (degrés, modulo 360) et saturation (0 à 100), à valeur maximale (modèle TSV, V = 1)."""
    s = max(0, min(100, saturation)) / 100
    k = (teinte % 360) / 60
    milieu = 1 - abs(k % 2 - 1)
    r, g, b = [(1, milieu, 0), (milieu, 1, 0), (0, 1, milieu), (0, milieu, 1), (milieu, 0, 1), (1, 0, milieu)][int(k) % 6]
    return _vers_hex([255 * (1 - s + s * c) for c in (r, g, b)])


def kelvin_vers_hex(k):
    """Blanc réglé en kelvins (Tanner Helland), éclairci de 45 % vers le blanc.

    À l'écran, 2700 K brut paraît orange vif : l'éclaircie vient de couleur() dans la maquette.
    """
    t = k / 100
    if t <= 66:
        r = 255
        g = 99.4708025861 * math.log(t) - 161.1195681661
    else:
        r = 329.698727446 * (t - 60) ** -0.1332047592
        g = 288.1221695283 * (t - 60) ** -0.0755148492
    if t >= 66:
        b = 255
    elif t <= 19:
        b = 0
    else:
        b = 138.5177312231 * math.log(t - 10) - 305.0447927307
    brut = _vers_hex([max(0, min(255, c)) for c in (r, g, b)])
    return melange(brut, "#ffffff", 0.45)


def teinte_de(h):
    """Teinte d'une couleur hex, en degrés de 0 à 360."""
    r, g, b = (v / 255 for v in _vers_rvb(h))
    haut, bas = max(r, g, b), min(r, g, b)
    d = (haut - bas) or 1
    if haut == r:
        sixieme = ((g - b) / d + 6) % 6
    elif haut == g:
        sixieme = (b - r) / d + 2
    else:
        sixieme = (r - g) / d + 4
    return sixieme * 60


def saturation_de(h):
    """Saturation TSV d'une couleur hex, en pourcentage entier (0 pour un gris, un blanc ou le noir)."""
    canaux = _vers_rvb(h)
    haut, bas = max(canaux), min(canaux)
    if haut == 0:
        return 0
    return _arrondi((haut - bas) / haut * 100)


def palette(couleurs):
    """Couleurs uniques, triées par teinte, cinq au plus, prises à intervalle régulier."""
    uniques = sorted(dict.fromkeys(couleurs), key=teinte_de)
    n = len(uniques)
    if n <= 5:
        return uniques
    # Cinq indices régulièrement espacés, extrémités comprises. Le pas entier de la maquette
    # (ceil(n/5)) rendrait 4 couleurs pour 8, ce que la vérification du plan exclut.
    return [uniques[_arrondi(i * (n - 1) / 4)] for i in range(5)]
