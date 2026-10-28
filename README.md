# InfraRent Africa

Application Streamlit de **gestion, collecte de données et analyse d'une flotte d'engins de chantier** (BTP, contexte Cameroun, démarche inspirée de la gestion d'actifs ISO 55000).

| Rôle | Accès |
|---|---|
| **Chef de Chantier** | Uniquement le formulaire de saisie quotidienne |
| **Administrateur / Directeur de Projet** | Tableau de bord, maintenance, pannes & carnet de santé, HSE, saisie, rapports & exports, gestion du parc |

Au premier lancement, **5 semaines de données fictives** sont générées pour que tous les écrans soient immédiatement exploitables.

---

## 1. Lancer l'application en local

**Prérequis** : Python 3.11 ou plus récent ([python.org](https://www.python.org/downloads/) — cochez « Add Python to PATH » sous Windows).

Ouvrez un terminal dans le dossier du projet, puis :

**Windows (PowerShell)**
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```
> Si PowerShell refuse d'activer l'environnement : `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, puis réessayez.

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Le navigateur s'ouvre sur <http://localhost:8501>.

**Comptes de démonstration** (affichés sur l'écran de connexion tant qu'aucun secret n'est configuré)

| Identifiant | Mot de passe | Rôle |
|---|---|---|
| `directeur` | `Infra@2026` | Administrateur |
| `chef1` | `Chantier@1` | Chef de Chantier – Zone A |
| `chef2` | `Chantier@2` | Chef de Chantier – Zone B |

Pour arrêter l'application : `Ctrl + C` dans le terminal.

---

## 2. Structure du dépôt

```
InfraRent-Africa/
├── app.py                 # Point d'entrée : connexion, navigation par rôle
├── requirements.txt       # Dépendances (versions testées)
├── README.md              # Ce guide
├── .gitignore             # Exclut secrets, données et caches
├── .streamlit/
│   └── config.toml        # Thème (bleu foncé / gris technique)
├── core/
│   ├── config.py          # Constantes métier, seuils, couleurs, comptes de démo
│   ├── auth.py            # Authentification et rôles (st.session_state)
│   ├── data.py            # Lecture/écriture CSV, jeu de données de démo
│   ├── kpi.py             # Calculs : coûts, L/h, disponibilité, vidange, MTBF/MTTR
│   └── ui.py              # Style, cartes KPI, bandeau d'alerte, thème Plotly
├── views/
│   ├── saisie.py          # Formulaire terrain (chef de chantier)
│   ├── dashboard.py       # KPIs financiers et opérationnels
│   ├── maintenance.py     # Alertes de vidange, interventions
│   ├── pannes.py          # Historique des pannes + carnet de santé
│   ├── hse.py             # Incidents Hygiène-Sécurité-Environnement
│   └── exports.py         # Rapport hebdo CSV, sauvegarde, parc, administration
└── data/                  # CSV créés automatiquement (non versionnés)
    ├── flotte.csv         # Référentiel des engins
    ├── saisies.csv        # Relevés quotidiens
    └── maintenance.csv    # Interventions
```

---

## 3. Mettre le code sur GitHub

1. **Installez Git** : <https://git-scm.com/downloads>, puis configurez-vous une seule fois :
   ```bash
   git config --global user.name "Votre Nom"
   git config --global user.email "votre.email@exemple.com"
   ```
2. **Créez un dépôt vide** sur <https://github.com/new> : nom `InfraRent-Africa`, ne cochez *ni* README *ni* .gitignore (ils existent déjà). Public ou privé, au choix.
3. **Envoyez le code** depuis le dossier du projet (remplacez `VOTRE-PSEUDO`) :
   ```bash
   git init
   git add .
   git commit -m "InfraRent Africa : première version"
   git branch -M main
   git remote add origin https://github.com/VOTRE-PSEUDO/InfraRent-Africa.git
   git push -u origin main
   ```
   À la première connexion, une fenêtre vous demande de vous authentifier auprès de GitHub.
4. Vérifiez sur GitHub que `app.py`, `core/`, `views/` et `requirements.txt` sont bien présents. Le dossier `data/` et le fichier `.streamlit/secrets.toml` ne doivent **pas** apparaître : c'est voulu (`.gitignore`).

Pour publier une modification ensuite : `git add .` → `git commit -m "description"` → `git push`.

---

## 4. Déployer gratuitement sur Streamlit Community Cloud

1. Allez sur <https://share.streamlit.io> et connectez-vous avec votre compte **GitHub** (autorisez l'accès à vos dépôts).
2. Cliquez sur **Create app** → **Deploy a public app from GitHub** (ou *From existing repo*).
3. Renseignez :
   - **Repository** : `VOTRE-PSEUDO/InfraRent-Africa`
   - **Branch** : `main`
   - **Main file path** : `app.py`
4. Ouvrez **Advanced settings** :
   - **Python version** : 3.12 (ou 3.13).
   - **Secrets** : collez vos comptes (voir §5) — **indispensable avant de partager le lien**, sinon les comptes de démonstration restent actifs.
5. Cliquez sur **Deploy**. Après 2 à 3 minutes, l'application est en ligne sur une adresse du type `https://infrarent-africa.streamlit.app`.
6. **Partagez ce lien** avec vos camarades. Chaque modification poussée sur `main` redéploie l'application automatiquement.

> Une application inactive est mise en veille par Streamlit : un bouton « Wake up » apparaît au prochain accès, le réveil prend quelques secondes.

---

## 5. Sécuriser les comptes (à faire avant de partager le lien)

Dans Streamlit Cloud : **⋮ de l'application → Settings → Secrets**, ou en local dans un fichier `.streamlit/secrets.toml` (jamais publié grâce au `.gitignore`).

```toml
[users.directeur]
password = "UnMotDePasseSolide!2026"
role = "admin"
nom = "Directeur de Projet"

[users.chef_douala]
password = "AutreMotDePasse#1"
role = "chef"
nom = "Chef de Chantier – Douala"
```

- Le nom de la section (`directeur`, `chef_douala`…) est l'**identifiant de connexion** : évitez les points et les espaces.
- `role` vaut `"admin"` ou `"chef"`. Chaque utilisateur est tracé par son nom dans les saisies.
- Les mots de passe peuvent être stockés sous forme d'empreinte SHA-256 (`password_sha256 = "..."` à la place de `password`) :
  ```bash
  python -c "import hashlib; print(hashlib.sha256('MonMotDePasse'.encode()).hexdigest())"
  ```
- Dès que la section `[users]` existe, les comptes de démonstration disparaissent.

---

## 6. Limites à connaître (important pour un usage réel)

- **Le stockage CSV est temporaire sur Streamlit Community Cloud** : le disque est réinitialisé à chaque redémarrage ou redéploiement. Utilisez régulièrement **Rapports & données → Sauvegarde & restauration** pour télécharger les CSV et les recharger si besoin.
- Les CSV conviennent à quelques utilisateurs simultanés. Au-delà, ou pour une exploitation durable, migrez `core/data.py` (seul fichier concerné) vers Google Sheets, Supabase ou PostgreSQL.
- Passer en production : **Rapports & données → Parc d'engins** (saisissez vos vrais engins), puis **Administration → Vider les données opérationnelles** pour supprimer la démo.

---

## 7. Règles métier et hypothèses

| Indicateur | Calcul | Où l'ajuster |
|---|---|---|
| **Coût de revient horaire** | (litres × prix du gasoil + heures × taux d'entretien de l'engin) ÷ heures de marche | Prix du gasoil : champ du tableau de bord (730 FCFA/L par défaut). Taux d'entretien : onglet *Parc d'engins* |
| **Consommation L/h** | litres ÷ heures de marche, comparée à la référence de l'engin. Orange à +15 %, rouge à +30 % | `core/config.py` (`SEUIL_SURCONSO_*`) |
| **Disponibilité** | jours « En service » ÷ jours saisis (jours-engins) | `core/config.py` (`SEUIL_DISPO_*`) |
| **Alerte vidange** | heures cumulées depuis la dernière vidange. Vert < 80 %, orange ≥ 80 %, rouge ≥ intervalle (250 h) | Intervalle par engin dans *Parc d'engins* ; 80 % dans `config.py` |
| **MTBF / MTTR** | heures de marche ÷ nombre de pannes / durée moyenne d'une immobilisation (jours) | `core/kpi.py` |
| **Fréquence HSE** | incidents pour 1 000 h de marche | `core/kpi.py` |

Points à retenir :

- Le carburant saisi est la quantité **ajoutée en fin de journée (plein à plein)**, assimilée à la consommation du jour.
- Une **vidange** enregistrée dans *Maintenance* remet le compteur d'alerte de l'engin à zéro.
- Le coût d'entretien est une **estimation** (taux horaire × heures) ; les coûts réels des interventions sont suivis séparément dans le carnet de santé.
- Une nouvelle saisie pour le même engin et la même date **remplace** la précédente (correction), avec nouvel horodatage et nouvel auteur.
- Les données de démonstration sont entièrement fictives.

---

## 8. Dépannage

| Problème | Solution |
|---|---|
| `streamlit : commande introuvable` | Activez l'environnement virtuel (`.venv`) ou utilisez `python -m streamlit run app.py` |
| Échec de `pip install` | Vérifiez `python --version` (3.11 minimum) |
| Le déploiement échoue sur Cloud | Ouvrez *Manage app* pour lire les logs ; vérifiez que `requirements.txt` est à la racine |
| Données de démo absentes / corrompues | Supprimez le dossier `data/` : il est régénéré au prochain lancement |
| Le fichier CSV s'ouvre mal dans Excel | Les exports utilisent `;` et l'UTF-8 : ouvrez-les par double-clic, ou *Données → À partir d'un fichier texte* |
