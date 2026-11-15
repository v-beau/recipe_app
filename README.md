# 🍲 Meine Rezepte – deine persönliche Rezept-App

Eine kleine App für deine Lieblingsrezepte. Sie läuft kostenlos auf **GitHub Pages**, funktioniert auf dem Handy wie eine richtige App und kann Rezepte von Webseiten **automatisch importieren**: Du legst auf GitHub ein „Issue“ (eine Art Notizzettel) mit dem Rezept-Link an – den Rest erledigt ein Roboter.

Du brauchst **keine Programmierkenntnisse**. Folge einfach den Schritten unten. Rechne beim ersten Mal mit etwa 20 Minuten.

---

## Was die App kann

- 📖 Rezeptliste mit Bild, Zeit, Sternen und Tags
- 🔍 Suche nach Titel und Zutaten, Filter nach Tags, Sortierung
- 🍽️ Detailansicht mit Zutaten, Schritten, Quelle, Notizen
- ➕➖ Portionsrechner – Zutatenmengen und Nährwerte rechnen mit
- 🔥 Nährwerte pro Portion (Kalorien, Eiweiß, Fett, Kohlenhydrate)
- ⭐ Bewertung, Schwierigkeit, „zuletzt gekocht“, eigene Notizen
- 🛒 Einkaufsliste aus mehreren Rezepten, gleiche Zutaten werden zusammengerechnet, zum Abhaken
- ✏️ Rezepte hinzufügen, bearbeiten, löschen – auch durch **Text einfügen mit automatischem Ausfüllen**
- 📷 Eigene Fotos (werden automatisch verkleinert)
- 💾 Backup als Datei exportieren und wieder importieren
- 🌙 Dunkelmodus, große Tasten, funktioniert auch offline
- 🤖 Automatischer Import per GitHub-Issue (mit Schutz vor Fremden und Duplikat-Erkennung)

---

## Die Dateien im Überblick

| Datei / Ordner | Wofür? |
|---|---|
| `index.html` | Die komplette App |
| `recipes.json` | Alle Rezepte (enthält 3 Beispielrezepte zum Ausprobieren) |
| `images/` | Rezeptbilder |
| `icons/` | App-Symbole für den Home-Bildschirm |
| `manifest.json`, `sw.js` | Machen aus der Webseite eine installierbare App (auch offline nutzbar) |
| `scripts/import_recipe.py` | Das Import-Programm, das Rezepte von Webseiten ausliest |
| `scripts/requirements.txt` | Liste der Hilfsprogramme, die der Import braucht |
| `.github/workflows/import-recipe.yml` | Der „Roboter“, der bei neuen Issues den Import startet |
| `.nojekyll` | Kleine technische Datei für GitHub Pages (einfach mit hochladen) |

---

## Schritt 1: Repository auf GitHub erstellen

Ein „Repository“ (kurz „Repo“) ist einfach ein Projektordner auf GitHub.

1. Falls noch nicht geschehen: Konto auf **[github.com](https://github.com)** anlegen (kostenlos).
2. Oben rechts auf **+** tippen → **New repository**.
3. **Repository name:** z. B. `rezepte` (kleingeschrieben, ohne Leerzeichen).
4. **Public** auswählen (bei kostenlosen Konten nötig, siehe Schritt 8).
5. Auf **Create repository** tippen.

> 📱 **Handy:** Funktioniert im Browser genauso. Das „+“ findest du oben rechts neben deinem Profilbild.

---

## Schritt 2: Dateien hochladen

Entpacke zuerst die ZIP-Datei auf deinem Computer.

### Am Computer (empfohlen)

1. Öffne dein neues Repository auf GitHub.
2. Tippe auf den Link **uploading an existing file** (oder **Add file → Upload files**).
3. Öffne den entpackten Ordner, markiere **alles darin** (nicht den Ordner selbst!) und ziehe es in das Browserfenster.
4. Unten auf **Commit changes** klicken.
5. **Prüfen:** Im Repository muss jetzt ein Ordner `.github` zu sehen sein.

> ⚠️ **Wichtig – der Ordner `.github`:** Ordner, deren Name mit einem Punkt beginnt, sind auf Mac und Windows oft **unsichtbar** und werden dann nicht mit hochgeladen.
> - **Mac:** Im Finder `Cmd + Shift + .` (Punkt) drücken, dann sind sie sichtbar.
> - **Windows:** Im Explorer **Ansicht → Einblenden → Ausgeblendete Elemente** anhaken.
>
> Fehlt `.github` trotzdem, leg die Datei von Hand an: **Add file → Create new file**, als Namen genau `.github/workflows/import-recipe.yml` eintippen (die Schrägstriche erzeugen die Ordner automatisch), den Inhalt der Datei `import-recipe.yml` hineinkopieren und **Commit changes** klicken.

### Nur mit dem Handy

Ordner kann man am Handy nicht hochladen. So geht's trotzdem:
1. **Add file → Upload files**: zuerst die Dateien im Hauptordner (`index.html`, `recipes.json`, `manifest.json`, `sw.js`, `README.md`, `.nojekyll`) hochladen.
2. Für jeden Ordner (`icons`, `images`, `scripts`): **Add file → Upload files**, dann oben im Pfad-Feld den Ordnernamen gefolgt von `/` eintippen (z. B. `icons/`) und die Dateien des Ordners auswählen.
3. Die Workflow-Datei wie oben beschrieben mit **Create new file** anlegen.

---

## Schritt 3: GitHub Pages aktivieren (App online stellen)

1. Im Repository auf **Settings** (Zahnrad) tippen.
2. Links im Menü **Pages** wählen.
3. Bei **Source**: **Deploy from a branch**.
4. Bei **Branch**: `main` und `/ (root)` auswählen → **Save**.
5. Nach 1–2 Minuten erscheint oben die Adresse deiner App, z. B. **`https://deinname.github.io/rezepte/`**. Diese Adresse ist deine App! 🎉

> 📱 **Handy:** Wenn du „Settings“ nicht siehst, tippe im Repository oben auf **…** oder stelle im Browser-Menü auf **Desktop-Website anfordern** um.

---

## Schritt 4: Schreibrechte für den Import-Roboter aktivieren

Damit der Roboter neue Rezepte speichern darf:

1. **Settings → Actions → General**.
2. Ganz nach unten zu **Workflow permissions** scrollen.
3. **Read and write permissions** auswählen → **Save**.

(Oben auf derselben Seite sollte bei **Actions permissions** „Allow all actions and reusable workflows“ ausgewählt sein – das ist normalerweise schon so.)

---

## Schritt 5: Erstes Rezept automatisch importieren

**Variante A – direkt auf GitHub:**
1. Im Repository auf **Issues** → **New issue** tippen.
2. In den **Titel** nur den Link zur Rezeptseite einfügen, z. B. `https://www.beispielseite.de/rezepte/lasagne`
3. Optional in die Beschreibung:
   ```
   Tags: Pasta, Familie
   Notiz: Doppelte Menge Käse!
   ```
4. **Submit new issue** (bzw. **Create**) tippen.

**Variante B – aus der App (bequemer am Handy):**
1. In der App unten auf **➕ Neu** → **🔗 Rezept-Link automatisch importieren**.
2. Link einfügen → **Auf GitHub importieren**. GitHub öffnet sich mit fertig ausgefülltem Issue – nur noch absenden.

**Was dann passiert:** Nach ca. 1 Minute schreibt der Roboter einen Kommentar ins Issue (✅ Erfolg, ℹ️ schon vorhanden oder ❌ Fehler mit Erklärung) und schließt es. Nach 1–2 weiteren Minuten ist das Rezept in der App (eventuell die App einmal neu laden).
Den Fortschritt siehst du im Repository unter **Actions**.

**Wenn eine Seite den Import blockiert:** Manche Seiten sperren Roboter. Dann bekommst du eine Meldung im Issue. Lösung: Rezepttext auf der Webseite markieren und kopieren → App → **➕ Neu → 📋 Rezepttext einfügen** → **Felder ausfüllen** → prüfen → **Speichern**.

> 🔒 **Sicherheit:** Der Import startet nur, wenn **du** (Besitzer) oder ein eingeladener **Collaborator** das Issue erstellt. Issues von Fremden werden ignoriert.
> ♻️ **Duplikate:** Ist ein Rezept mit derselben Quell-Adresse schon vorhanden, wird es nicht noch einmal eingetragen.

---

## Schritt 6: App auf den Home-Bildschirm legen

Öffne die App-Adresse aus Schritt 3 auf dem Handy:

- **iPhone/iPad (Safari):** Unten auf das **Teilen-Symbol** (Quadrat mit Pfeil) → **Zum Home-Bildschirm** → **Hinzufügen**.
- **Android (Chrome):** Oben rechts **⋮** → **Zum Startbildschirm hinzufügen** bzw. **App installieren**.

Jetzt hat die App ein eigenes Symbol und öffnet sich ohne Browserleiste.

> 💡 **Android-Extra:** Nach der Installation erscheint „Rezepte“ im **Teilen-Menü**. Wenn du in Chrome auf einer Rezeptseite auf **Teilen → Rezepte** tippst, öffnet sich die App mit dem Link schon ausgefüllt.

---

## Schritt 7: Mit Freunden teilen

- **Nur ansehen:** Schick einfach die App-Adresse (`https://deinname.github.io/rezepte/`). Freunde sehen alle Rezepte, die auf GitHub gespeichert sind. Änderungen, die sie in ihrer App machen, landen nur auf ihrem eigenen Handy – deine Sammlung bleibt unverändert.
- **Mitmachen lassen:** **Settings → Collaborators → Add people** → GitHub-Namen eingeben. Nach Annahme der Einladung dürfen sie ebenfalls Rezepte per Issue importieren.
  ⚠️ Collaborators können im Repository **alles** ändern und löschen – lade nur Menschen ein, denen du vertraust.

---

## Schritt 8: Wichtig – deine App ist öffentlich

Bei **kostenlosen GitHub-Konten** ist GitHub Pages nur mit **öffentlichen** Repositories möglich. Das heißt:
- Jeder, der die Adresse kennt, kann deine Rezepte sehen.
- Auch das Repository (inklusive Issues und `recipes.json`) ist für alle einsehbar.
- Trage also **keine privaten Informationen** in Rezepte, Notizen oder Issues ein.

(Private Pages gibt es nur mit kostenpflichtigen GitHub-Plänen.)

---

## Gut zu wissen: Wo werden meine Änderungen gespeichert?

Es gibt zwei „Speicherorte“:

1. **GitHub (`recipes.json`)** – hier landen die automatisch importierten Rezepte. Alle Geräte und Freunde sehen diese.
2. **Dein Gerät** – alles, was du **in der App** machst (Rezept von Hand anlegen, bearbeiten, löschen, Sterne, Notizen, „heute gekocht“, eigene Fotos, Einkaufsliste), wird im Browser auf **diesem einen Gerät** gespeichert.

Unter **⚙️ Mehr** siehst du, wie viele Änderungen nur auf deinem Gerät sind.

### Änderungen sichern (Backup)
**⚙️ Mehr → ⬇️ Backup exportieren** speichert alle Rezepte als Datei `recipes.json`. Mit **⬆️ Backup importieren** holst du sie zurück, z. B. auf ein neues Handy. Mach das ab und zu – wenn du die Browserdaten löschst, sind Änderungen auf dem Gerät sonst weg.

### Änderungen dauerhaft auf GitHub übernehmen (für alle Geräte und Freunde)
1. **⚙️ Mehr → ⬇️ Backup exportieren** → du erhältst `recipes.json`.
2. Auf GitHub im Repository **Add file → Upload files** → diese `recipes.json` hochladen → **Commit changes**. Die alte Datei wird ersetzt.
3. Nach 1–2 Minuten sehen alle die neue Version.

> Hinweis: Eigene Fotos stecken dann direkt in `recipes.json`, dadurch wird die Datei größer. Das ist in Ordnung, solange es nicht Hunderte Fotos sind.

---

## Hilfe bei Problemen

| Problem | Lösung |
|---|---|
| Die App zeigt „recipes.json konnte nicht geladen werden“ | Öffne die App über die GitHub-Pages-Adresse, nicht durch Doppelklick auf `index.html`. |
| Nach dem Issue passiert nichts | Unter **Actions** nachsehen. Fehlt der Workflow → Ordner `.github` wurde nicht hochgeladen (Schritt 2). Wurde das Issue von jemand anderem erstellt → nur Besitzer/Collaborators dürfen importieren. |
| ❌ „Technischer Fehler beim Import“ | Schritt 4 prüfen (Read and write permissions). |
| Neues Rezept erscheint nicht in der App | 1–3 Minuten warten, dann in der App **⚙️ Mehr → 🔄 Neu laden**. |
| Import-Button in der App sagt „Repository eintragen“ | Unter **⚙️ Mehr → GitHub-Verbindung** `deinname/rezepte` eintragen. |
| Ein Bild fehlt | Manche Seiten erlauben das Herunterladen nicht. Bearbeite das Rezept und füge ein eigenes Foto hinzu. |
| Beispielrezepte stören | In der App öffnen → **🗑 Löschen**. Dauerhaft für alle: Backup exportieren und wie oben auf GitHub hochladen. |

Viel Spaß beim Kochen! 👩‍🍳👨‍🍳
