"use strict";

const pont = window.webkit?.messageHandlers?.pont;
const racine = document.getElementById("panneau");
let etat = null;

// Les noms viennent du bridge : jamais dans le HTML sans passer par ici.
const ech = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function envoyer(message) {
  if (pont) pont.postMessage(message);
  else window.fauxBridge(message);
}

function phrase(piece) {
  const { allumees, total } = piece;
  if (allumees === 0) return "Tout est éteint";
  if (allumees === total) return "Tout est allumé";
  return `${allumees} lampe${allumees > 1 ? "s" : ""} allumée${allumees > 1 ? "s" : ""} sur ${total}`;
}

function tuile(s) {
  const c = s.couleurs || [];
  const g = c.length > 1 ? `linear-gradient(135deg, ${c.join(", ")})` : (c[0] || "transparent");
  const o = ((s.intensite || 0) / 100).toFixed(2);
  const n = ech(s.nom);
  const dedans = `<i style="--g:${g};--o:${o}"></i><span>${n}</span>`;
  // --a : la couleur du milieu de la palette, pour l'anneau de la scène en cours.
  return `<button class="scene" data-scene="${ech(s.id)}" aria-pressed="${!!s.active}" style="--a:${c[Math.floor(c.length / 2)] || "transparent"}">${dedans}</button>`;
}

// La carte de la scène en cours : teintée aux couleurs de la scène, avec une pastille par lampe à sa couleur du moment.
function carte(s) {
  const c = s?.couleurs?.length ? s.couleurs : null;
  const g = !c ? "transparent" : c.length > 1 ? `linear-gradient(135deg, ${c.join(", ")})` : c[0];
  const lampes = etat.lampes.map(l => `<i class="${l.on && l.couleur ? "" : "eteinte"}" style="${l.on && l.couleur ? `--c:${l.couleur}` : ""}"></i>`).join("");
  return `<div class="carte ${s ? "" : "vide"}" style="--g:${g}"><i class="echantillon"></i>
    <div><div class="nom">${s ? ech(s.nom) : (etat.piece.on ? "Réglage manuel" : "Lumières éteintes")}</div><div class="lampes" aria-hidden="true">${lampes}</div></div></div>`;
}

// Apparence : suit celle du Mac. En démonstration (navigateur), ?theme=sombre ou ?theme=clair la force.
const apparenceSombre = window.matchMedia("(prefers-color-scheme: dark)");
function poserTheme() {
  const force = new URLSearchParams(location.search).get("theme");
  const sombre = !pont && (force === "sombre" || force === "clair") ? force === "sombre" : apparenceSombre.matches;
  document.documentElement.dataset.theme = sombre ? "sombre" : "clair";
}
poserTheme();
apparenceSombre.addEventListener("change", poserTheme);

// Le curseur est créé une seule fois : le redessiner en plein geste le détruirait sous le doigt.
let curseur = null, valeur = null, groupe = null;
let tenu = false, dernierGeste = 0;

// Un curseur ignore l'état reçu pendant 1,5 s après un geste. Sans rattrapage, la relecture qui suit l'ordre tombe dans
// cette fenêtre et l'affichage ne se corrige qu'au rafraîchissement suivant, 3 ou 4 s plus tard (vu par Antho, 12/11).
let rattrapage = null;
function rattraper() {
  clearTimeout(rattrapage);
  rattrapage = setTimeout(() => { if (etat && !tenu) dessiner(); }, 1600);
}

// Seul endroit où la page calcule une couleur : le temps d'un geste, avant que l'état reçu ne la confirme.
// Portées de design/maquette.html ; deBlanc prend des kelvins (2000 K = #ffb36b, 4500 K = #fff3e2, 6500 K = #dbe7ff).
const rvb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
const hex = t => "#" + t.map(v => Math.round(v).toString(16).padStart(2, "0")).join("");
const melange = (a, b, t) => hex(rvb(a).map((v, i) => v + (rvb(b)[i] - v) * t));
// Couleur d'écran d'un couple (teinte 0-360, saturation 0-100) : le TSV à valeur maximale.
const couleurDe = (h, s) => { const f = n => { const k = (n + h / 60) % 6; return 255 * (1 - s / 100 * Math.max(0, Math.min(k, 4 - k, 1))); }; return hex([f(5), f(3), f(1)]); };
const deBlanc = k => k < 4500 ? melange("#ffb36b", "#fff3e2", (Math.max(k, 2000) - 2000) / 2500) : melange("#fff3e2", "#dbe7ff", (Math.min(k, 6500) - 4500) / 2000);
// Bornes du blanc d'une lampe ; 2000 à 6500 tant que l'état n'en donne pas.
const bornes = l => Array.isArray(l.kelvins) && l.kelvins.length === 2 ? l.kelvins : [2000, 6500];

// Onglet choisi : gardé ici pour survivre aux états reçus.
let onglet = "scenes";
// Lampes : lignes créées une fois (tant que la suite des identifiants et des zones ne change pas), puis mises à jour en place.
let cleLignes = "", lignes = new Map();
// Titres de zone et leur bouton « Tout éteindre / Tout allumer », créés avec les cartes.
let titres = [];
// Une seule carte dépliée à la fois (id de la lampe), aucune au départ.
let ouverte = null;
// Défilement de chaque zone, gardé à part : une zone cachée perd son défilement.
const defile = { scenes: 0, lampes: 0 };

function creerSqueletteSiBesoin() {
  if (racine.querySelector(".entete")) return;
  racine.innerHTML =
    `<div class="entete"><div class="noms"><div class="piece"></div><div class="etat"></div></div><button type="button" class="roue" aria-label="Réglages" aria-pressed="false"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6.96 2.90L7.15 1.05L8.85 1.05L9.04 2.90L10.87 3.66L12.31 2.48L13.52 3.69L12.34 5.13L13.10 6.96L14.95 7.15L14.95 8.85L13.10 9.04L12.34 10.87L13.52 12.31L12.31 13.52L10.87 12.34L9.04 13.10L8.85 14.95L7.15 14.95L6.96 13.10L5.13 12.34L3.69 13.52L2.48 12.31L3.66 10.87L2.90 9.04L1.05 8.85L1.05 7.15L2.90 6.96L3.66 5.13L2.48 3.69L3.69 2.48L5.13 3.66Z" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/><circle cx="8" cy="8" r="2.2" fill="none" stroke="currentColor" stroke-width="1.2"/></svg></button><button class="inter" role="switch" aria-checked="false" data-tout aria-label="Tout allumer ou éteindre"></button></div>
    <div class="groupe" hidden><svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="2" fill="currentColor"/><path d="M11.80 8.00L12.60 8.00 M10.69 10.69L11.25 11.25 M8.00 11.80L8.00 12.60 M5.31 10.69L4.75 11.25 M4.20 8.00L3.40 8.00 M5.31 5.31L4.75 4.75 M8.00 4.20L8.00 3.40 M10.69 5.31L11.25 4.75" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" fill="none"/></svg><input type="range" min="1" max="100" value="50" style="--v:50%" aria-label="Intensité de la pièce"><svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="2.6" fill="currentColor"/><path d="M12.80 8.00L14.60 8.00 M11.39 11.39L12.67 12.67 M8.00 12.80L8.00 14.60 M4.61 11.39L3.33 12.67 M3.20 8.00L1.40 8.00 M4.61 4.61L3.33 3.33 M8.00 3.20L8.00 1.40 M11.39 4.61L12.67 3.33" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" fill="none"/></svg><output>50 %</output></div>
    <div class="onglets" role="tablist" hidden><button type="button" role="tab" data-onglet="scenes" aria-selected="true">Scènes</button><button type="button" role="tab" data-onglet="lampes" aria-selected="false">Lampes</button></div>
    <div class="actuelle"></div>
    <h2 class="titre titre-scenes" hidden>Scènes</h2>
    <div class="corps"></div>
    <div class="corps liste" hidden></div>
    <div class="reglages" hidden>
      <h2 class="titre">Bridge</h2>
      <div class="bloc">
        <label class="libelle" for="bridge-ip">Adresse</label>
        <input id="bridge-ip" class="champ" type="text" autocomplete="off" spellcheck="false" aria-label="Adresse du bridge">
        <div class="statut"></div>
        <button type="button" class="enregistrer" hidden>Enregistrer</button>
      </div>
      <div class="bloc ligne"><span>Lancer à l'ouverture de session</span><button class="inter" role="switch" aria-checked="false" aria-label="Lancer à l'ouverture de session" data-demarrage></button></div>
      <button type="button" class="quitter"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2v6M4.6 4.2a5 5 0 1 0 6.8 0" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>Quitter Hue Controller</button>
      <div class="bas"><button type="button" class="auteur">Application créée par Anthony Hamo</button><button type="button" class="termine">Terminé</button></div>
    </div>`;
  preparerReglages();
  groupe = racine.querySelector(".groupe");
  curseur = groupe.querySelector("input");
  valeur = groupe.querySelector("output");
  const fin = () => { tenu = false; };
  curseur.addEventListener("pointerdown", () => { tenu = true; });
  window.addEventListener("pointerup", fin);
  window.addEventListener("pointercancel", fin);
  const finLignes = () => lignes.forEach(l => { l.tenu = false; Object.values(l.reg || {}).forEach(r => { r.tenu = false; }); });
  window.addEventListener("pointerup", finLignes);
  window.addEventListener("pointercancel", finLignes);
  curseur.addEventListener("input", () => {
    dernierGeste = Date.now(); rattraper();
    const v = Math.round(Number(curseur.value));
    afficherCurseur(v);
    if (etat?.piece) etat.piece.intensite = v;
    envoyer({ action: "piece", intensite: v });
  });
}

// Vue Réglages : ses éléments sont créés une fois avec le squelette ; un état reçu n'y touche que la ligne d'état.
let reglagesOuverts = false, reglagesRecus = null, erreurReglages = null;
let champ = null, statut = null, enregistrer = null, interDemarrage = null;
const adresseConnue = () => (reglagesRecus && reglagesRecus.bridge_ip) || "";

function preparerReglages() {
  champ = racine.querySelector(".champ");
  statut = racine.querySelector(".statut");
  enregistrer = racine.querySelector(".enregistrer");
  interDemarrage = racine.querySelector("[data-demarrage]");
  champ.addEventListener("input", majReglages);
  champ.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); envoyerAdresse(); } });
}

function envoyerAdresse() { envoyer({ action: "reglages", bridge_ip: champ.value }); }

function majReglages() {
  if (!champ) return;
  const connecte = etat && etat.connexion === "ok";
  statut.textContent = erreurReglages || (connecte ? "Connecté" : (etat && etat.message) || "Non connecté");
  statut.classList.toggle("erreur", !!erreurReglages);
  enregistrer.hidden = champ.value === adresseConnue();
}

function basculerReglages(ouvrir) {
  reglagesOuverts = ouvrir;
  racine.classList.toggle("en-reglages", ouvrir);
  racine.querySelector(".reglages").hidden = !ouvrir;
  racine.querySelector(".roue").setAttribute("aria-pressed", String(ouvrir));
  if (ouvrir) {
    majReglages();
    envoyer({ action: "reglages" });
  } else {
    const corps = racine.querySelector(".corps:not(.liste)"), liste = racine.querySelector(".liste");
    if (!corps.hidden) corps.scrollTop = defile.scenes;
    if (!liste.hidden) liste.scrollTop = defile.lampes;
  }
}

// Réponse de Python aux messages de réglages. On ne remplace pas ce que l'utilisateur est en train de taper.
window.reglages = function (r) {
  const avant = adresseConnue();
  reglagesRecus = r;
  erreurReglages = r.erreur || null;
  if (champ) {
    if (!(document.activeElement === champ && champ.value !== avant)) champ.value = adresseConnue();
    interDemarrage.setAttribute("aria-checked", String(!!r.demarrage));
    majReglages();
  }
};

function afficherCurseur(v) {
  curseur.value = v;
  curseur.style.setProperty("--v", v + "%");
  valeur.textContent = v + " %";
}

// Décision 7 : tenu, ou touché depuis moins de 1,5 s, le curseur ignore l'état reçu (sauf `force`, pour l'interrupteur).
function majCurseur(force) {
  const ok = etat.connexion === "ok";
  groupe.hidden = !ok;
  if (!ok) return;
  if (!force && (tenu || Date.now() - dernierGeste < 1500)) return;
  afficherCurseur(Math.min(100, Math.max(1, Math.round(etat.piece.intensite) || 1)));
  curseur.disabled = !etat.piece.on;
}

// Recompte la pièce après un geste sur une lampe ; une scène n'est plus « en cours » dès qu'on touche à une lampe.
function compterZones() {
  (etat.zones || []).forEach(z => { z.allumees = etat.lampes.filter(l => l.zone === z.nom && l.on).length; });
}

function recompter() {
  compterZones();
  etat.piece.allumees = etat.lampes.filter(l => l.on).length;
  etat.piece.on = etat.piece.allumees > 0;
  etat.scenes.forEach(s => { s.active = false; });
}

// Une carte par lampe : la partie haute (halo, nom, état, interrupteur), puis le dépli (luminosité).
function construireLignes(liste) {
  lignes = new Map();
  titres = [];
  liste.innerHTML = "";
  const zones = [];
  etat.lampes.forEach(l => {
    let z = zones.find(x => x.nom === l.zone);
    if (!z) zones.push(z = { nom: l.zone, lampes: [] });
    z.lampes.push(l);
  });
  zones.forEach(z => {
    const titre = document.createElement("h2");
    titre.className = "titre titre-zone";
    titre.innerHTML = `<span></span><button type="button" class="zone-tout"></button>`;
    titre.firstChild.textContent = z.nom;
    titres.push({ nom: z.nom, bouton: titre.querySelector("button") });
    liste.appendChild(titre);
    z.lampes.forEach(l => {
      const el = document.createElement("div");
      el.className = "lampe";
      el.dataset.id = l.id;
      el.innerHTML = `<div class="haut"><button type="button" class="entree" aria-expanded="false"><span class="halo"><i></i></span><span class="textes"><span class="nom"></span><span class="infos"></span></span></button><button class="inter" role="switch" aria-checked="false"></button></div>
        <div class="pli" hidden><div class="rang"><span>Luminosité</span><output></output></div><input type="range" min="1" max="100" value="50">${sousLuminosite(l)}</div>`;
      const ligne = { id: l.id, el, halo: el.querySelector(".halo"), nom: el.querySelector(".nom"), infos: el.querySelector(".infos"),
        entree: el.querySelector(".entree"), pli: el.querySelector(".pli"), valeur: el.querySelector("output"),
        curseur: el.querySelector("input"), inter: el.querySelector(".inter"), tenu: false, dernierGeste: 0, couleur: null,
        choix: null, segments: [...el.querySelectorAll("[data-mode]")] };
      ligne.curseur.addEventListener("pointerdown", () => { ligne.tenu = true; });
      ligne.curseur.addEventListener("input", () => {
        ligne.dernierGeste = Date.now(); rattraper();
        const v = Math.round(Number(ligne.curseur.value));
        const lampe = etat?.lampes.find(x => x.id === ligne.id);
        if (!lampe) return;
        lampe.intensite = v;
        etat.scenes.forEach(s => { s.active = false; });
        dessiner();
        envoyer({ action: "lampe", id: ligne.id, intensite: v });
      });
      // Température du blanc et roue chromatique : créées avec la carte, chacune avec son « tenu / touché », comme la luminosité (décision 7).
      ligne.reg = {};
      const blanc = el.querySelector("input.blanc");
      if (blanc) {
        const r = { el: blanc, tenu: false, dernierGeste: 0 };
        ligne.reg.blanc = r;
        blanc.addEventListener("pointerdown", () => { r.tenu = true; });
        blanc.addEventListener("input", () => gesteReglage(ligne, { kelvin: Math.round(Number(blanc.value)) }));
      }
      const roue = el.querySelector(".chroma");
      if (roue) {
        const r = { el: roue, repere: roue.querySelector(".repere"), tenu: false, dernierGeste: 0 };
        ligne.reg.roue = r;
        // La teinte est l'angle depuis le haut, dans le sens des aiguilles ; la saturation, la distance au centre (bornée au bord).
        const geste = e => {
          const c = roue.getBoundingClientRect(), rayon = c.width / 2;
          const dx = e.clientX - (c.left + rayon), dy = e.clientY - (c.top + rayon);
          const angle = (Math.atan2(dx, -dy) * 180 / Math.PI + 360) % 360;
          gesteReglage(ligne, { teinte: Math.round(angle) % 360, saturation: Math.min(100, Math.round(Math.hypot(dx, dy) / rayon * 100)) });
        };
        roue.addEventListener("pointerdown", e => {
          if (!etat?.lampes.find(x => x.id === ligne.id)?.on) return;
          r.tenu = true;
          try { roue.setPointerCapture(e.pointerId); } catch (_) { /* pas de capture possible : le geste continue sans */ }
          geste(e);
        });
        roue.addEventListener("pointermove", e => { if (r.tenu) geste(e); });
        const fin = () => { r.tenu = false; };
        roue.addEventListener("pointerup", fin);
        roue.addEventListener("pointercancel", fin);
      }
      lignes.set(l.id, ligne);
      liste.appendChild(el);
    });
  });
}

// Sous Luminosité : lampe de couleur = sélecteur Couleur / Blanc (s'il y a un blanc) puis roue et température, un seul visible ;
// lampe blanche = la température ; blanc fixe = rien.
function sousLuminosite(l) {
  const couleur = l.reglages?.includes("teinte"), blanc = l.reglages?.includes("blanc");
  if (!couleur) return blanc ? `<div class="rang sous"><span>Température</span></div><input type="range" class="blanc" min="2000" max="6500" value="2700">` : "";
  return (blanc ? `<div class="onglets mode" role="tablist" aria-label="Réglage de la lampe"><button type="button" role="tab" data-mode="couleur" aria-selected="true">Couleur</button><button type="button" role="tab" data-mode="blanc" aria-selected="false">Blanc</button></div>` : "")
    + `<div class="chroma" role="slider" aria-valuemin="0" aria-valuemax="359" aria-valuenow="0"><i class="repere"></i></div>`
    + (blanc ? `<input type="range" class="blanc apres" min="2000" max="6500" value="2700">` : "");
}

// Un interrupteur est un geste voulu : l'état qu'il provoque doit passer sur tous les curseurs.
function libere(g) { g.dernierGeste = 0; g.local = null; Object.values(g.reg).forEach(r => { r.dernierGeste = 0; }); }

// Température ou roue tirée : la lampe prend tout de suite la couleur du geste (halo, repère, ligne d'état),
// l'état reçu fera foi après. Teinte et saturation partent toujours ensemble : le bridge reçoit un seul couple.
function gesteReglage(g, v) {
  const lampe = etat?.lampes.find(x => x.id === g.id);
  const r = "kelvin" in v ? g.reg.blanc : g.reg.roue;
  if (!lampe || !r) return;
  r.dernierGeste = Date.now(); rattraper();
  let message;
  if ("kelvin" in v) {
    lampe.mode = "blanc"; lampe.kelvin = v.kelvin; lampe.couleur = deBlanc(v.kelvin);
    message = { action: "lampe", id: g.id, kelvin: v.kelvin };
  } else {
    lampe.mode = "teinte"; lampe.teinte = v.teinte; lampe.saturation = v.saturation; lampe.kelvin = null; lampe.couleur = couleurDe(v.teinte, v.saturation);
    message = { action: "lampe", id: g.id, teinte: v.teinte, saturation: v.saturation };
  }
  g.couleur = lampe.couleur;
  // Copie locale : tant que la carte est touchée, un état reçu en retard ne la fait pas revenir en arrière.
  g.local = { mode: lampe.mode, kelvin: lampe.kelvin, couleur: lampe.couleur, teinte: lampe.teinte, saturation: lampe.saturation };
  etat.scenes.forEach(s => { s.active = false; });
  dessiner();
  envoyer(message);
}

// Réglage tenu, ou touché depuis moins de 1,5 s : il ignore l'état reçu (décision 7).
const touche = r => !!r && (r.tenu || Date.now() - r.dernierGeste < 1500);

// Un des curseurs ou la roue de la carte est tenu ou vient d'être touché.
const carteTouchee = g => g.tenu || Date.now() - g.dernierGeste < 1500 ||
  Object.values(g.reg).some(r => r.tenu || Date.now() - r.dernierGeste < 1500);

// « Blanc chaud / neutre / froid » pour un blanc, « Couleur » pour une teinte ; rien si la lampe n'a pas de mode.
function texteMode(l) {
  if (l.mode === "teinte") return " · Couleur";
  if (l.mode !== "blanc") return "";
  const k = l.kelvin;
  return " · " + (k != null && k < 3300 ? "Blanc chaud" : k != null && k < 5000 ? "Blanc neutre" : "Blanc froid");
}

// Le bouton d'une zone suit les lampes affichées sous son titre ; pas de bouton pour un titre hors de `etat.zones` (« Autres »).
function majTitres() {
  titres.forEach(t => {
    const zone = (etat.zones || []).find(z => z.nom === t.nom);
    t.bouton.hidden = !zone;
    if (!zone) return;
    const une = etat.lampes.some(l => l.zone === t.nom && l.on);
    t.bouton.dataset.zone = zone.id;
    t.bouton.textContent = une ? "Tout éteindre" : "Tout allumer";
    t.bouton.setAttribute("aria-label", (une ? "Tout éteindre dans " : "Tout allumer dans ") + t.nom);
  });
}

// Décision 7, par lampe : tenu, ou touché depuis moins de 1,5 s, le curseur ignore l'état reçu
// (valeur, pourcentage de la ligne d'état, valeur du dépli, désactivé).
function majLignes() {
  etat.lampes.forEach(l => {
    const g = lignes.get(l.id);
    if (!g) return;
    if (l.couleur) g.couleur = l.couleur;
    const allumee = !!l.on;
    // Carte touchée : halo, mode et poignées viennent de la copie locale du geste, pas de l'état reçu.
    const touchee = carteTouchee(g);
    if (!touchee) g.local = null;
    const lm = touchee && g.local ? g.local : l;
    const coul = allumee ? (lm.couleur || g.couleur) : null;
    const garde = g.tenu || Date.now() - g.dernierGeste < 1500;
    const v = garde ? Math.round(Number(g.curseur.value)) : Math.min(100, Math.max(1, Math.round(l.intensite) || 1));
    g.el.classList.toggle("eteinte", !allumee);
    g.halo.style.setProperty("--c", coul || "");
    g.nom.textContent = l.nom;
    g.infos.textContent = allumee ? v + " %" + texteMode(lm) : "Éteinte";
    g.valeur.textContent = v + " %";
    g.inter.setAttribute("aria-checked", String(allumee));
    g.inter.setAttribute("aria-label", l.nom);
    g.curseur.setAttribute("aria-label", "Luminosité de " + l.nom);
    const ouvert = ouverte === g.id;
    g.entree.setAttribute("aria-expanded", String(ouvert));
    g.pli.hidden = !ouvert;
    g.el.classList.toggle("ouverte", ouvert);
    // Teinte et saturation absentes de l'état : 30 et 100.
    const h = lm.teinte != null ? lm.teinte : 30, sat = lm.saturation != null ? lm.saturation : 100;
    // Segment ouvert : le choix de l'utilisateur tant que la carte n'est pas refermée, sinon le mode de la lampe.
    const mode = g.choix || (lm.mode === "blanc" ? "blanc" : "couleur");
    g.segments.forEach(b => b.setAttribute("aria-selected", String(b.dataset.mode === mode)));
    const blanc = g.reg.blanc, roue = g.reg.roue;
    if (blanc) {
      blanc.el.hidden = !!roue && mode !== "blanc";
      blanc.el.setAttribute("aria-label", "Température de " + l.nom);
      // La poignée porte la couleur de la lampe quand la lampe est en blanc.
      blanc.el.style.setProperty("--pouce", lm.mode === "blanc" && coul ? coul : "");
      if (!touche(blanc)) {
        const [mini, maxi] = bornes(l);
        blanc.el.min = mini; blanc.el.max = maxi;
        blanc.el.value = Math.min(maxi, Math.max(mini, l.mode === "blanc" && l.kelvin != null ? l.kelvin : 2700));
      }
      blanc.el.disabled = !allumee;
    }
    if (roue) {
      roue.el.hidden = mode !== "couleur";
      roue.el.setAttribute("aria-label", "Couleur de " + l.nom);
      roue.el.setAttribute("aria-valuenow", String(h));
      roue.el.setAttribute("aria-valuetext", `teinte ${h}, saturation ${sat} %`);
      roue.el.setAttribute("aria-disabled", String(!allumee));
      // Le repère est à (teinte, saturation) : l'angle depuis le haut, la distance depuis le centre (rayon 96 px).
      const a = h * Math.PI / 180, d = sat / 100 * 96;
      roue.repere.style.left = (96 + d * Math.sin(a)).toFixed(1) + "px";
      roue.repere.style.top = (96 - d * Math.cos(a)).toFixed(1) + "px";
      roue.repere.style.background = couleurDe(h, sat);
    }
    if (garde) return;
    g.curseur.value = v;
    g.curseur.style.setProperty("--v", v + "%");
    g.curseur.disabled = !allumee;
  });
}

function afficherOnglet() {
  const ok = etat.connexion === "ok";
  const scenes = racine.querySelector(".corps:not(.liste)"), liste = racine.querySelector(".liste");
  racine.querySelector(".onglets").hidden = !ok;
  racine.querySelectorAll("[data-onglet]").forEach(b => b.setAttribute("aria-selected", String(b.dataset.onglet === onglet)));
  racine.querySelector(".actuelle").hidden = !ok || onglet !== "scenes";
  racine.querySelector(".titre-scenes").hidden = !ok || onglet !== "scenes";
  scenes.hidden = ok && onglet !== "scenes";
  liste.hidden = !ok || onglet !== "lampes";
}

function dessiner(force) {
  creerSqueletteSiBesoin();
  const corps = racine.querySelector(".corps:not(.liste)");
  const liste = racine.querySelector(".liste");
  // Une zone cachée rend 0 : on ne lit le défilement que de celle qu'on voit.
  // Vue Réglages ouverte : les zones sont cachées, leur défilement lu serait 0.
  if (!reglagesOuverts && !corps.hidden) defile.scenes = corps.scrollTop;
  if (!reglagesOuverts && !liste.hidden) defile.lampes = liste.scrollTop;
  const ok = etat.connexion === "ok";
  const nom = ok ? etat.piece.nom : "Hue Controller";
  const dit = ok ? phrase(etat.piece) : (etat.message || "");
  // L'en-tête est créé une fois (la roue dentée garde son état) ; on n'y met à jour que les textes et l'interrupteur.
  racine.querySelector(".entete .piece").textContent = nom;
  racine.querySelector(".entete .etat").textContent = dit;
  const toutInter = racine.querySelector(".entete .inter");
  toutInter.setAttribute("aria-checked", String(ok && !!etat.piece.on));
  toutInter.disabled = !ok;
  // Deux blocs : la scène en cours (une seule place pour le dire), puis toutes les scènes, toujours au même endroit.
  const enCours = ok ? etat.scenes.find(s => s.active) : null;
  racine.querySelector(".actuelle").innerHTML = ok ? `<h2 class="titre">Scène actuelle</h2>` + carte(enCours) : "";
  corps.innerHTML = `<div class="scenes">${ok ? etat.scenes.map(s => tuile(s)).join("") : ""}</div>`;
  if (ok) {
    const cle = etat.lampes.map(l => l.id + "|" + l.zone).join("\n");
    if (cle !== cleLignes) { cleLignes = cle; construireLignes(liste); }
    majLignes();
    majTitres();
  }
  afficherOnglet();
  if (!reglagesOuverts && !corps.hidden) corps.scrollTop = defile.scenes;
  if (!reglagesOuverts && !liste.hidden) liste.scrollTop = defile.lampes;
  majCurseur(force);
  majReglages();
}

// L'app donne la couleur d'accent choisie dans les réglages du Mac ; le navigateur garde le vert par défaut.
window.accent = couleur => racine.style.setProperty("--inter-on", couleur);

window.recevoir = function (nouvelEtat) {
  etat = nouvelEtat;
  dessiner();
};

// Le geste s'affiche tout de suite ; l'état reçu ensuite fait foi.
racine.addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  // La roue et la vue Réglages marchent dans tous les états, y compris sans connexion.
  if (b.classList.contains("roue")) { basculerReglages(!reglagesOuverts); return; }
  if (b.closest(".reglages")) {
    if (b === enregistrer) envoyerAdresse();
    else if (b === interDemarrage) {
      const on = b.getAttribute("aria-checked") !== "true";
      b.setAttribute("aria-checked", String(on));
      envoyer({ action: "demarrage", on });
    } else if (b.classList.contains("quitter")) envoyer({ action: "quitter" });
    else if (b.classList.contains("termine")) basculerReglages(false);
    else if (b.classList.contains("auteur")) envoyer({ action: "auteur" });  // l'app ouvre la page GitHub dans le navigateur
    return;
  }
  if (!etat || etat.connexion !== "ok") return;
  if (b.dataset.onglet) {
    const corps = racine.querySelector(".corps:not(.liste)"), liste = racine.querySelector(".liste");
    if (!corps.hidden) defile.scenes = corps.scrollTop;
    if (!liste.hidden) defile.lampes = liste.scrollTop;
    onglet = b.dataset.onglet;
    afficherOnglet();
    if (!corps.hidden) corps.scrollTop = defile.scenes;
    if (!liste.hidden) liste.scrollTop = defile.lampes;
  } else if (b.classList.contains("zone-tout")) {
    const z = (etat.zones || []).find(x => x.id === b.dataset.zone);
    if (!z) return;
    const dedans = etat.lampes.filter(l => l.zone === z.nom);
    const on = !dedans.some(l => l.on);
    dedans.forEach(l => {
      l.on = on;
      if (!on) l.couleur = null; else if (!l.couleur) l.couleur = lignes.get(l.id)?.couleur ?? null;
      const g = lignes.get(l.id);
      if (g) libere(g);
    });
    recompter();
    dessiner(true);
    envoyer({ action: "zone", id: z.id, on });
  } else if (b.classList.contains("entree")) {
    const id = b.closest(".lampe").dataset.id;
    // Refermer une carte oublie le segment choisi : elle se rouvre sur le mode de la lampe.
    if (ouverte) { const ancienne = lignes.get(ouverte); if (ancienne) ancienne.choix = null; }
    ouverte = ouverte === id ? null : id;
    majLignes();
    // La carte dépliée est plus haute que la place restante (la roue fait 192 px) : on la fait défiler en vue.
    if (ouverte) b.closest(".lampe").scrollIntoView({ block: "nearest", behavior: "smooth" });
  } else if (b.dataset.mode) {
    // Changer de segment n'envoie rien : le premier geste sur la roue ou la température change la lampe.
    const g = lignes.get(b.closest(".lampe").dataset.id);
    if (!g) return;
    g.choix = b.dataset.mode;
    majLignes();
  } else if (b.closest(".lampe")) {
    const id = b.closest(".lampe").dataset.id, g = lignes.get(id), l = etat.lampes.find(x => x.id === id);
    if (!g || !l) return;
    l.on = !l.on;
    if (l.on && !l.couleur) l.couleur = g.couleur;
    if (!l.on) l.couleur = null;
    libere(g);
    recompter();
    dessiner(true);
    envoyer({ action: "lampe", id: l.id, on: l.on });
  } else if (b.dataset.scene) {
    etat.scenes.forEach(s => { s.active = s.id === b.dataset.scene; });
    dessiner();
    envoyer({ action: "scene", id: b.dataset.scene });
  } else if ("tout" in b.dataset) {
    const on = !etat.piece.on;
    etat.piece.on = on;
    etat.piece.allumees = on ? etat.piece.total : 0;
    if (!on) etat.scenes.forEach(s => { s.active = false; });
    etat.lampes.forEach(l => { l.on = on; if (!on) l.couleur = null; else if (!l.couleur) l.couleur = lignes.get(l.id)?.couleur ?? null; });
    lignes.forEach(g => { libere(g); });
    compterZones();
    dessiner(true);
    envoyer({ action: "piece", on });
  }
});

function charger(src) {
  return new Promise((ok, ko) => {
    const s = document.createElement("script");
    s.src = src; s.onload = ok; s.onerror = ko;
    document.body.appendChild(s);
  });
}

async function demarrer() {
  if (!pont) {
    document.documentElement.classList.add("demo");
    await charger("faux_etat.js");
    await charger("faux.js");
  }
  envoyer({ action: "pret" });
}
demarrer();
