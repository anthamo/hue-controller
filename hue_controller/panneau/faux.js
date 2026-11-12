// Faux bridge pour le navigateur : garde l'état en mémoire et applique les gestes. Ne touche à aucune lampe.
(function () {
  const etat = JSON.parse(JSON.stringify(window.ETAT_FAUX));

  // Le contrat veut une couleur nulle pour une lampe éteinte : on garde la dernière connue pour la rendre au rallumage.
  const memoire = {};
  etat.lampes.forEach(l => { memoire[l.id] = l.couleur || "#ffe2bd"; });

  function compter() {
    etat.lampes.forEach(l => {
      if (l.couleur) memoire[l.id] = l.couleur;
      l.couleur = l.on ? memoire[l.id] : null;
    });
    const allumees = etat.lampes.filter(l => l.on).length;
    etat.piece.allumees = allumees;
    etat.piece.total = etat.lampes.length;
    etat.piece.on = allumees > 0;
    etat.zones.forEach(z => { z.allumees = etat.lampes.filter(l => l.zone === z.nom && l.on).length; });
  }

  // Même calcul que la page (panneau.js) : la couleur d'écran d'un blanc ou d'un couple (teinte, saturation).
  const rvb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  const hex = t => "#" + t.map(v => Math.round(v).toString(16).padStart(2, "0")).join("");
  const melange = (a, b, t) => hex(rvb(a).map((v, i) => v + (rvb(b)[i] - v) * t));
  const couleurDe = (h, s) => { const f = n => { const k = (n + h / 60) % 6; return 255 * (1 - s / 100 * Math.max(0, Math.min(k, 4 - k, 1))); }; return hex([f(5), f(3), f(1)]); };
  const deBlanc = k => k < 4500 ? melange("#ffb36b", "#fff3e2", (Math.max(k, 2000) - 2000) / 2500) : melange("#fff3e2", "#dbe7ff", (Math.min(k, 6500) - 4500) / 2000);
  const fini = (n, a, b) => typeof n === "number" && Number.isFinite(n) && n >= a && n <= b;

  // Réglages en mémoire, comme Python les garde dans le fichier de réglages.
  const reglages = { bridge_ip: "192.168.0.20", demarrage: false };
  const repondreReglages = erreur => setTimeout(() => window.reglages(erreur ? { ...reglages, erreur } : { ...reglages }), 100);

  window.fauxBridge = function (message) {
    if (message.action === "reglages") {
      if (!("bridge_ip" in message)) return repondreReglages();
      const texte = String(message.bridge_ip).trim();
      if (/^\d{1,3}(\.\d{1,3}){3}$/.test(texte)) { reglages.bridge_ip = texte; return repondreReglages(); }
      return repondreReglages("Adresse invalide.");
    }
    if (message.action === "demarrage") {
      if (typeof message.on === "boolean") reglages.demarrage = message.on;
      return repondreReglages();
    }
    if (message.action === "quitter") { console.log("quitter"); return; }
    if (message.action === "scene") {
      if (!etat.scenes.some(s => s.id === message.id)) return;
      etat.scenes.forEach(s => { s.active = s.id === message.id; });
      etat.lampes.forEach(l => { l.on = true; });
      compter();
    } else if (message.action === "piece" && typeof message.on === "boolean") {
      etat.lampes.forEach(l => { l.on = message.on; });
      etat.scenes.forEach(s => { s.active = false; });
      compter();
    } else if (message.action === "zone") {
      const z = etat.zones.find(x => x.id === message.id);
      if (!z || typeof message.on !== "boolean") return;
      etat.lampes.forEach(l => { if (l.zone === z.nom) l.on = message.on; });
      etat.scenes.forEach(s => { s.active = false; });
      compter();
    } else if (message.action === "piece" && "intensite" in message) {
      const v = message.intensite;
      if (typeof v !== "number" || !Number.isFinite(v) || v < 1 || v > 100) return;
      etat.piece.intensite = v;
      etat.lampes.forEach(l => { if (l.on) l.intensite = v; });
    } else if (message.action === "lampe") {
      const l = etat.lampes.find(x => x.id === message.id);
      if (!l) return;
      if (typeof message.on === "boolean") l.on = message.on;
      else if ("kelvin" in message) {
        if (!fini(message.kelvin, 1500, 7000) || !l.reglages?.includes("blanc") || l.reglages.includes("teinte")) return;
        l.mode = "blanc"; l.kelvin = message.kelvin; l.couleur = deBlanc(message.kelvin);
        memoire[l.id] = l.couleur;
      } else if ("teinte" in message || "saturation" in message) {
        if (!fini(message.teinte, 0, 360) || !fini(message.saturation, 0, 100) || !l.reglages?.includes("teinte")) return;
        l.mode = "teinte"; l.teinte = message.teinte; l.saturation = message.saturation; l.kelvin = null; l.couleur = couleurDe(message.teinte, message.saturation);
        memoire[l.id] = l.couleur;
      } else if (typeof message.intensite === "number" && Number.isFinite(message.intensite) && message.intensite >= 1 && message.intensite <= 100) l.intensite = message.intensite;
      else return;
      etat.scenes.forEach(s => { s.active = false; });
      compter();
    } else if (message.action !== "pret") {
      return;
    }
    setTimeout(() => window.recevoir(JSON.parse(JSON.stringify(etat))), 150);
  };
})();
