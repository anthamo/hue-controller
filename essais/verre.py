"""Essai : le panneau en verre de macOS 26, comme les panneaux de la barre de menus du système.

NSPopover a un fond presque opaque. Ici : une fenêtre sans bord, un fond NSGlassEffectView, la page dedans.

    uv run essais/verre.py [fichier.png]    # ouvre 3 s sous l'icône ; avec un fichier, capture la zone du panneau
"""

import subprocess
import sys

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSBackingStoreBuffered,
    NSColor,
    NSImage,
    NSMakeRect,
    NSObject,
    NSPanel,
    NSPopUpMenuWindowLevel,
    NSScreen,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from PyObjCTools import AppHelper
from WebKit import WKWebView, WKWebViewConfiguration

L, H = 360, 240
PAGE = """<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:transparent;font:13px -apple-system;color:#1d1d1f}
body{padding:16px}b{font-size:16px}div{margin-top:12px;height:44px;border-radius:6px;background:rgba(255,255,255,.5);display:flex;align-items:center;padding:0 12px}</style>
<b>Séjour</b><br>Tout est allumé<div>Honolulu</div><div>Détente</div>"""


class Fenetre(NSPanel):
    def canBecomeKeyWindow(self):  # une fenêtre sans bord refuse le clavier et les clics sinon
        return True


class App(NSObject):
    def applicationDidFinishLaunching_(self, _):
        self.icone = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self.icone.button().setImage_(NSImage.imageWithSystemSymbolName_accessibilityDescription_("lightbulb", "Lumières"))
        self.page = WKWebView.alloc().initWithFrame_configuration_(NSMakeRect(0, 0, L, H), WKWebViewConfiguration.alloc().init())
        self.page.setValue_forKey_(False, "drawsBackground")
        self.page.loadHTMLString_baseURL_(PAGE, None)
        verre = objc.lookUpClass("NSGlassEffectView").alloc().initWithFrame_(NSMakeRect(0, 0, L, H))
        verre.setCornerRadius_(20)
        verre.setContentView_(self.page)
        self.fenetre = Fenetre.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, L, H), NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel, NSBackingStoreBuffered, False)
        self.fenetre.setOpaque_(False)
        self.fenetre.setBackgroundColor_(NSColor.clearColor())
        self.fenetre.setHasShadow_(True)
        self.fenetre.setLevel_(NSPopUpMenuWindowLevel)
        self.fenetre.setContentView_(verre)
        AppHelper.callLater(1, self.ouvrir)
        AppHelper.callLater(2.5, self.capturer)
        AppHelper.callLater(3.2, AppHelper.stopEventLoop)

    @objc.python_method
    def ouvrir(self):
        cadre = self.icone.button().window().frame()
        ecran = NSScreen.mainScreen().frame()
        x = min(max(cadre.origin.x + cadre.size.width / 2 - L / 2, 8), ecran.size.width - L - 8)
        self.fenetre.setFrameOrigin_((x, cadre.origin.y - H - 6))
        self.fenetre.makeKeyAndOrderFront_(None)

    @objc.python_method
    def capturer(self):
        f, ecran = self.fenetre.frame(), NSScreen.mainScreen().frame()
        print("panneau visible :", bool(self.fenetre.isVisible()), flush=True)
        if len(sys.argv) > 1:
            zone = f"{int(f.origin.x)},{int(ecran.size.height - f.origin.y - f.size.height)},{L},{H}"
            r = subprocess.run(["screencapture", "-x", "-R", zone, sys.argv[1]], capture_output=True, text=True)
            print("capture :", r.returncode, r.stderr.strip()[:100], flush=True)


application = NSApplication.sharedApplication()
application.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
app = App.alloc().init()
application.setDelegate_(app)
AppHelper.runEventLoop()
