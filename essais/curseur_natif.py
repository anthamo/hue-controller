"""Essai : le curseur de la page (dessiné par WebKit) face au vrai curseur du Mac (NSSlider),
posé par-dessus la page. Question : lequel a le rendu du système, sur ce macOS et sur un plus ancien ?

    uv run essais/curseur_natif.py [fichier.png]   # ouvre 3 s ; avec un fichier, capture la fenêtre seule
"""

import subprocess
import sys

import objc
from AppKit import (
    NSApplication, NSApplicationActivationPolicyAccessory, NSAppearance, NSBackingStoreBuffered, NSColor, NSMakeRect,
    NSObject, NSPanel, NSPopUpMenuWindowLevel, NSScreen, NSSlider, NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from PyObjCTools import AppHelper
from WebKit import WKWebView, WKWebViewConfiguration

L, H = 360, 200
PAGE = """<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:transparent;font:13px -apple-system;color:#1d1d1f}
p{position:absolute;left:16px;margin:0}input{position:absolute;left:16px;width:328px;margin:0}</style>
<p style="top:8px">Page (WebKit, sans style)</p><input type="range" value="60" style="top:28px">
<p style="top:56px">Mac (NSSlider), taille normale</p>
<p style="top:104px">Mac (NSSlider), petite taille</p>
<p style="top:152px">Mac (NSSlider), mini</p>"""


class Fenetre(NSPanel):
    def canBecomeKeyWindow(self):
        return True


class App(NSObject):
    def applicationDidFinishLaunching_(self, _):
        page = WKWebView.alloc().initWithFrame_configuration_(NSMakeRect(0, 0, L, H), WKWebViewConfiguration.alloc().init())
        page.setValue_forKey_(False, "drawsBackground")
        page.loadHTMLString_baseURL_(PAGE, None)
        verre = objc.lookUpClass("NSGlassEffectView").alloc().initWithFrame_(NSMakeRect(0, 0, L, H))
        verre.setCornerRadius_(20)
        verre.setContentView_(page)
        self.curseurs = []
        for haut, taille in ((76, 0), (124, 1), (172, 2)):  # NSControlSizeRegular, Small, Mini ; la page compte depuis le haut
            c = NSSlider.sliderWithValue_minValue_maxValue_target_action_(60, 1, 100, self, "bouge:")
            c.setControlSize_(taille)
            c.setFrame_(NSMakeRect(16, haut, L - 32, 24))
            page.addSubview_(c)
            self.curseurs.append(c)
        self.fenetre = Fenetre.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, L, H), NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel, NSBackingStoreBuffered, False)
        self.fenetre.setOpaque_(False)
        self.fenetre.setBackgroundColor_(NSColor.clearColor())
        self.fenetre.setLevel_(NSPopUpMenuWindowLevel)
        self.fenetre.setAppearance_(NSAppearance.appearanceNamed_("NSAppearanceNameAqua"))
        self.fenetre.setContentView_(verre)
        e = NSScreen.mainScreen().frame()
        self.fenetre.setFrameOrigin_((e.size.width - L - 16, e.size.height - H - 48))
        self.fenetre.makeKeyAndOrderFront_(None)
        AppHelper.callLater(2, self.capturer)
        AppHelper.callLater(2.8, AppHelper.stopEventLoop)

    def bouge_(self, curseur):
        print("valeur :", round(curseur.doubleValue()), flush=True)

    @objc.python_method
    def capturer(self):
        if len(sys.argv) > 1:
            r = subprocess.run(["screencapture", "-x", "-o", "-l", str(self.fenetre.windowNumber()), sys.argv[1]], capture_output=True, text=True)
            print("capture :", r.returncode, r.stderr.strip()[:100], flush=True)


application = NSApplication.sharedApplication()
application.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
app = App.alloc().init()
application.setDelegate_(app)
AppHelper.runEventLoop()
