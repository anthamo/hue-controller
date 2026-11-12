"""Parle au bridge Hue : lire une ressource, en écrire une. Rien d'autre."""

import http.client
import json
import ssl


class BridgeErreur(Exception):
    """Toute panne du bridge. Le message est court et ne contient jamais la clé."""


class Bridge:
    def __init__(self, ip, cle, transport=None):
        self._ip = ip
        self._cle = cle
        self._transport = transport
        self._connexion = None

    def lire(self, ressource):
        reponse = self._appeler("GET", f"/clip/v2/resource/{ressource}", None)
        try:
            return reponse["data"]
        except (KeyError, TypeError):
            raise BridgeErreur("Réponse du bridge illisible") from None

    def ecrire(self, ressource, id, corps):
        self._appeler("PUT", f"/clip/v2/resource/{ressource}/{id}", corps)

    def _appeler(self, methode, chemin, corps):
        if self._transport is not None:
            try:
                return self._transport(methode, chemin, corps)
            except BridgeErreur:
                raise
            except Exception:
                # Le détail d'une exception étrangère pourrait citer la clé.
                raise BridgeErreur("Le bridge ne répond pas") from None
        return self._appeler_reseau(methode, chemin, corps)

    def _appeler_reseau(self, methode, chemin, corps):
        donnees = None if corps is None else json.dumps(corps)
        en_tetes = {"hue-application-key": self._cle}
        if donnees is not None:
            en_tetes["Content-Type"] = "application/json"
        # Une connexion gardée ouverte peut avoir été fermée par le bridge
        # entre deux appels : on la refait une seule fois.
        for essai in (1, 2):
            if self._connexion is None:
                self._connexion = http.client.HTTPSConnection(
                    self._ip, timeout=3, context=ssl._create_unverified_context()
                )
            try:
                self._connexion.request(methode, chemin, body=donnees, headers=en_tetes)
                reponse = self._connexion.getresponse()
                brut = reponse.read()
                statut = reponse.status
                break
            except (OSError, http.client.HTTPException):
                self.fermer()
                if essai == 2:
                    raise BridgeErreur("Le bridge ne répond pas") from None
        if not 200 <= statut < 300:
            raise BridgeErreur(f"Le bridge a refusé la demande (HTTP {statut})")
        try:
            return json.loads(brut)
        except ValueError:
            raise BridgeErreur("Réponse du bridge illisible") from None

    def fermer(self):
        if self._connexion is not None:
            try:
                self._connexion.close()
            except Exception:
                pass
            self._connexion = None
