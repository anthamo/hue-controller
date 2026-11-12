"""Essai de faisabilité (12/11/2026) : une icône dans la barre de menus, un panneau accroché dessous,
une page HTML dedans, et un aller-retour entre la page et Python.

    uv run essais/panneau.py            # l'icône reste, cliquer dessus ; Ctrl-C pour arrêter
    uv run essais/panneau.py --essai    # ouvre le panneau seul, vérifie l'aller-retour, s'arrête
"""

import sys

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSImage,
    NSMakeRect,
    NSObject,
    NSPopover,
    NSPopoverBehaviorTransient,
    NSRectEdgeMinY,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSViewController,
)
from PyObjCTools import AppHelper
from WebKit import WKUserContentController, WKWebView, WKWebViewConfiguration

PAGE = """<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;background:transparent;font:13px -apple-system;color:#1d1d1f}
body{padding:16px}button{font:inherit}</style>
<b>Séjour</b><p id="etat">en attente de Python…</p><button onclick="dire('clic')">Dire bonjour à Python</button>
<script>
  const dire = quoi => window.webkit.messageHandlers.pont.postMessage({action: quoi});
  window.recevoir = texte => { document.getElementById('etat').textContent = texte; dire('recu'); };
  dire('pret');
</script>"""

ESSAI = "--essai" in sys.argv
vus = []


class Pont(NSObject, protocols=[objc.protocolNamed("WKScriptMessageHandler")]):
    def userContentController_didReceiveScriptMessage_(self, controleur, message):
        action = message.body()["action"]
        vus.append(action)
        print("la page dit :", action, flush=True)
        if action == "pret":
            app.page.evaluateJavaScript_completionHandler_("recevoir('Python a répondu')", None)


class App(NSObject):
    def applicationDidFinishLaunching_(self, _):
        self.icone = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        bouton = self.icone.button()
        bouton.setImage_(NSImage.imageWithSystemSymbolName_accessibilityDescription_("lightbulb", "Lumières"))
        bouton.setTarget_(self)
        bouton.setAction_("basculer:")

        reglages = WKWebViewConfiguration.alloc().init()
        self.pont = Pont.alloc().init()
        reglages.userContentController().addScriptMessageHandler_name_(self.pont, "pont")
        self.page = WKWebView.alloc().initWithFrame_configuration_(NSMakeRect(0, 0, 360, 200), reglages)
        self.page.setValue_forKey_(False, "drawsBackground")  # le fond translucide du panneau passe au travers
        self.page.loadHTMLString_baseURL_(PAGE, None)

        vue = NSViewController.alloc().init()
        vue.setView_(self.page)
        self.panneau = NSPopover.alloc().init()
        self.panneau.setContentViewController_(vue)
        self.panneau.setContentSize_((360, 200))
        self.panneau.setBehavior_(NSPopoverBehaviorTransient)

        if ESSAI:
            AppHelper.callLater(1, self.basculer_, None)
            AppHelper.callLater(3, self.bilan)

    def basculer_(self, _):
        if self.panneau.isShown():
            self.panneau.close()
        else:
            bouton = self.icone.button()
            self.panneau.showRelativeToRect_ofView_preferredEdge_(bouton.bounds(), bouton, NSRectEdgeMinY)

    def bilan(self):
        print("panneau ouvert :", bool(self.panneau.isShown()), "| messages :", vus, flush=True)
        AppHelper.stopEventLoop()


application = NSApplication.sharedApplication()
application.setActivationPolicy_(NSApplicationActivationPolicyAccessory)  # pas d'icône dans le Dock
app = App.alloc().init()
application.setDelegate_(app)
AppHelper.runEventLoop()
