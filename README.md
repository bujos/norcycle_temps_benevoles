# Norcycle - Temps bénévole

Application web Streamlit permettant de saisir, consulter et analyser le temps bénévole effectué par les membres Norcycle.

L'application remplace le fichier Excel de suivi des heures bénévoles par une solution web simple, persistante et multi-utilisateur basée sur :

- Streamlit;
- GitHub;
- Supabase / PostgreSQL;
- comptes administrateurs et usagers;
- statistiques interactives;
- export Excel;
- rapport PDF avec graphiques.

## Fonctionnalités

### Saisie du temps bénévole

Chaque usager peut saisir rapidement :

- le nom de la personne;
- la date;
- le nombre d'heures;
- la tâche effectuée;
- une note optionnelle.

La saisie est conçue pour être simple, rapide et utilisable sur mobile.

### Gestion des comptes

L'application supporte deux rôles :

| Rôle | Accès |
|---|---|
| `admin` | Gestion des comptes, listes, imports, suppressions et statistiques |
| `user` | Saisie du temps, consultation des statistiques et export |

Le premier compte administrateur est créé au démarrage de l'application à l'aide d'un code de configuration.

### Gestion des bénévoles et tâches

L'application maintient deux listes :

- bénévoles;
- tâches / activités.

Lorsqu'un nouveau nom ou une nouvelle tâche est saisi, l'application peut l'ajouter automatiquement aux listes.

### Statistiques

La page statistiques permet de consulter :

- heures totales;
- nombre de saisies;
- nombre de bénévoles distincts;
- nombre de tâches distinctes;
- heures par année;
- heures par saison;
- heures par mois;
- Pareto des heures par bénévole;
- Pareto des heures par tâche.

### Rapport PDF

La page statistiques inclut un bouton :

```text
Exporter le rapport PDF
```

Le rapport contient :

- résumé des filtres appliqués;
- indicateurs principaux;
- top bénévoles;
- top tâches;
- Pareto par bénévole;
- Pareto par tâche;
- graphique des heures par année / saison;
- graphique des heures par mois.

Le rapport respecte les filtres sélectionnés dans l'application.

### Import / export Excel

L'application permet :

- l'export complet des données en Excel;
- l'import de l'ancien fichier Excel Norcycle;
- la conservation des bénévoles, tâches et saisies dans Supabase.

## Technologies utilisées

- [Streamlit](https://streamlit.io/)
- [Supabase](https://supabase.com/)
- PostgreSQL
- Pandas
- OpenPyXL
- Altair
- Matplotlib
- ReportLab

## Structure du projet

```text
norcycle-temps-benevole/
├── app.py
├── requirements.txt
└── README.md
```

## Dépendances

Le fichier `requirements.txt` doit contenir :

```txt
streamlit
supabase
pandas
openpyxl
altair
reportlab
matplotlib
```

## Installation locale

Cloner le dépôt :

```bash
git clone https://github.com/bujos/norcycle-temps-benevole.git
cd norcycle-temps-benevole
```

Créer un environnement virtuel :

```bash
python -m venv .venv
```

Activer l'environnement virtuel.

Sur Windows :

```bash
.venv\Scripts\activate
```

Sur macOS / Linux :

```bash
source .venv/bin/activate
```

Installer les dépendances :

```bash
pip install -r requirements.txt
```

Lancer l'application :

```bash
streamlit run app.py
```

## Configuration Supabase

L'application utilise Supabase comme base de données persistante.

### 1. Créer un projet Supabase

Créer un projet dans Supabase, puis ouvrir le tableau de bord du projet.

### 2. Créer les tables

Dans Supabase :

```text
SQL Editor → New query
```

Exécuter le script suivant :

```sql
create table if not exists public.app_users (
    id text primary key,
    username text unique not null,
    display_name text not null,
    password_hash text not null,
    role text not null default 'user' check (role in ('admin', 'user')),
    active boolean not null default true,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

create table if not exists public.volunteers (
    id text primary key,
    name text unique not null,
    active boolean not null default true,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

create table if not exists public.tasks (
    id text primary key,
    name text unique not null,
    active boolean not null default true,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

create table if not exists public.volunteer_hours (
    id text primary key,
    volunteer_name text not null,
    task_name text not null,
    hours numeric not null check (hours > 0),
    work_date date not null,
    note text,
    created_by text,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

create index if not exists idx_volunteer_hours_work_date
on public.volunteer_hours(work_date);

create index if not exists idx_volunteer_hours_volunteer_name
on public.volunteer_hours(volunteer_name);

create index if not exists idx_volunteer_hours_task_name
on public.volunteer_hours(task_name);

alter table public.app_users enable row level security;
alter table public.volunteers enable row level security;
alter table public.tasks enable row level security;
alter table public.volunteer_hours enable row level security;
```

## Configuration des secrets Streamlit

L'application utilise des secrets pour accéder à Supabase et pour créer le premier administrateur.

### En local

Créer un fichier :

```text
.streamlit/secrets.toml
```

Avec le contenu suivant :

```toml
SUPABASE_URL = "https://xxxxxxxxxxxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "sb_secret_xxxxxxxxxxxxxxxxxxxxxxxxx"

ADMIN_SETUP_KEY = "choisis-un-code-initial-secret"
```

### Sur Streamlit Community Cloud

Dans l'application Streamlit Cloud :

```text
App settings → Secrets
```

Ajouter :

```toml
SUPABASE_URL = "https://xxxxxxxxxxxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "sb_secret_xxxxxxxxxxxxxxxxxxxxxxxxx"

ADMIN_SETUP_KEY = "choisis-un-code-initial-secret"
```

Ne jamais inscrire ces valeurs directement dans `app.py`.

## Où trouver les valeurs Supabase

### `SUPABASE_URL`

Dans Supabase :

```text
Project Settings → Data API
```

ou :

```text
Project Settings → API
```

Copier la valeur :

```text
Project URL
```

Elle doit ressembler à :

```text
https://xxxxxxxxxxxx.supabase.co
```

Important : utiliser l'URL racine du projet.

```text
Bon :
https://xxxxxxxxxxxx.supabase.co

Mauvais :
https://xxxxxxxxxxxx.supabase.co/rest/v1

Mauvais :
https://supabase.com/dashboard/project/xxxx

Mauvais :
postgresql://postgres:...
```

### `SUPABASE_SERVICE_ROLE_KEY`

Dans Supabase :

```text
Project Settings → API Keys
```

Utiliser la clé dans :

```text
Secret keys → default
```

Elle commence généralement par :

```text
sb_secret_...
```

Cette clé donne un accès serveur privilégié. Elle ne doit jamais être publiée dans GitHub.

### `ADMIN_SETUP_KEY`

Valeur choisie manuellement.

Exemple :

```toml
ADMIN_SETUP_KEY = "Norcycle-Admin-2026!"
```

Ce code sert seulement à créer le premier administrateur lorsque la table `app_users` est vide.

## Création du premier administrateur

Lors du premier démarrage, si aucun compte n'existe, l'application affiche une page de configuration.

Champs demandés :

- code de configuration;
- nom affiché;
- nom d'utilisateur;
- mot de passe admin;
- confirmation du mot de passe.

Le code de configuration correspond à :

```toml
ADMIN_SETUP_KEY = "..."
```

Après la création du premier administrateur, l'application affiche la page de connexion normale.

## Utilisation

### Connexion

Chaque utilisateur se connecte avec :

- son nom d'utilisateur;
- son mot de passe.

### Saisie d'une entrée

Dans la page `Saisie` :

1. Choisir le nom de la personne.
2. Choisir la date.
3. Saisir le nombre d'heures.
4. Choisir la tâche.
5. Ajouter une note optionnelle.
6. Cliquer sur `Enregistrer le temps`.

### Nouvelle personne ou nouvelle tâche

Si une personne ou une tâche n'existe pas, l'utilisateur peut choisir :

```text
➕ Nouveau bénévole
```

ou :

```text
➕ Nouvelle tâche
```

L'application ajoute alors automatiquement cette valeur aux listes.

## Administration

La page `Administration` est réservée aux administrateurs.

Elle permet :

- de créer des comptes;
- de choisir le rôle `admin` ou `user`;
- d'activer ou désactiver un compte;
- de réinitialiser un mot de passe;
- d'ajouter des bénévoles;
- d'ajouter des tâches;
- de consulter les listes;
- de supprimer une saisie.

## Mot de passe temporaire

Lors de l'import initial, les comptes usagers peuvent être créés avec un mot de passe temporaire.

Exemple :

```text
norcycle2026
```

La version actuelle de l'application permet à l'administrateur de réinitialiser un mot de passe.

### Changement obligatoire à la première connexion

Dans la version actuelle, le changement obligatoire du mot de passe à la première connexion n'est pas encore activé dans le code.

Pour l'ajouter plus tard, prévoir les colonnes suivantes :

```sql
alter table public.app_users
add column if not exists must_change_password boolean not null default false;

alter table public.app_users
add column if not exists password_changed_at timestamp with time zone;

alter table public.app_users
add column if not exists last_login_at timestamp with time zone;
```

Puis marquer les comptes usagers importés :

```sql
update public.app_users
set must_change_password = true
where role = 'user';
```

Et exclure les administrateurs :

```sql
update public.app_users
set must_change_password = false
where role = 'admin';
```

L'application devra ensuite être modifiée pour forcer l'écran de changement de mot de passe lorsque `must_change_password = true`.

## Statistiques

La page `Statistiques` offre des filtres :

- par année;
- par saison.

Les saisons sont calculées selon le mois :

| Mois | Saison |
|---|---|
| Décembre, janvier, février | Hiver |
| Mars, avril, mai | Printemps |
| Juin, juillet, août | Été |
| Septembre, octobre, novembre | Automne |

Les indicateurs affichés sont :

- heures totales;
- nombre de saisies;
- bénévoles distincts;
- tâches distinctes.

Les graphiques disponibles sont :

- résumé par année et saison;
- Pareto des heures par bénévole;
- Pareto des heures par tâche;
- heures par mois.

## Rapport PDF

Dans la page `Statistiques`, le bouton suivant génère un PDF :

```text
Exporter le rapport PDF
```

Le rapport contient les données filtrées selon les années et saisons sélectionnées.

Le fichier généré est :

```text
norcycle_rapport_temps_benevole.pdf
```

Contenu du rapport :

- titre;
- date de génération;
- filtres appliqués;
- résumé;
- top 10 bénévoles;
- top 10 tâches;
- graphique Pareto par bénévole;
- graphique Pareto par tâche;
- graphique par année / saison;
- graphique par mois.

## Import / export Excel

La page `Import / export` permet d'exporter toutes les données.

Le fichier généré contient plusieurs feuilles :

```text
Temps benevole
Benevoles
Taches
Usagers
```

Les mots de passe ne sont pas exportés.

### Import de l'ancien fichier Excel

L'import est réservé aux administrateurs.

L'application détecte la feuille :

```text
Inscription
```

si elle existe.

Colonnes recherchées :

- nom;
- activité / tâche;
- nombre d'heures;
- date.

Les lignes incomplètes ou invalides sont ignorées.

## Déploiement sur Streamlit Community Cloud

1. Créer un dépôt GitHub contenant :

```text
app.py
requirements.txt
README.md
```

2. Aller dans Streamlit Community Cloud.

3. Choisir :

```text
Deploy a public app from GitHub
```

4. Configurer :

```text
Repository: bujos/norcycle-temps-benevole
Branch: main
Main file path: app.py
```

5. Ajouter les secrets :

```toml
SUPABASE_URL = "https://xxxxxxxxxxxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "sb_secret_xxxxxxxxxxxxxxxxxxxxxxxxx"

ADMIN_SETUP_KEY = "choisis-un-code-initial-secret"
```

6. Déployer l'application.

## Import SQL initial

Un import SQL peut être utilisé pour charger :

- les tâches uniques;
- les bénévoles;
- les saisies de temps;
- les comptes usagers.

Le script SQL peut être exécuté dans :

```text
Supabase → SQL Editor → New query
```

Si les comptes sont créés avec un mot de passe temporaire, il est recommandé de forcer ou demander un changement de mot de passe après la première connexion dans une version future.

## Sécurité

Ne jamais publier dans GitHub :

- `SUPABASE_SERVICE_ROLE_KEY`;
- `ADMIN_SETUP_KEY`;
- fichier `.streamlit/secrets.toml`;
- mots de passe;
- exports contenant des données sensibles.

Les secrets doivent être configurés dans Streamlit Cloud ou dans `.streamlit/secrets.toml` en local.

## Dépannage

### Erreur liée à `SUPABASE_URL`

Vérifier que `SUPABASE_URL` ressemble à :

```text
https://xxxxxxxxxxxx.supabase.co
```

et non à :

```text
https://xxxxxxxxxxxx.supabase.co/rest/v1
```

Le client Python Supabase ajoute lui-même les chemins nécessaires.

### Erreur de table inexistante

Vérifier que les tables suivantes existent dans le schéma `public` :

```text
app_users
volunteers
tasks
volunteer_hours
```

### Aucun administrateur

Si aucun utilisateur n'existe dans `app_users`, l'application affiche automatiquement l'écran de création du premier administrateur.

### Import Excel impossible

Vérifier que l'ancien fichier contient une feuille `Inscription` ou une feuille avec des colonnes pouvant être reconnues :

```text
Nom
Activités
NB Heures
Date
```

### Les graphiques PDF ne s'affichent pas

Vérifier que `matplotlib` et `reportlab` sont bien dans `requirements.txt`.

## Évolution possible

Améliorations futures possibles :

- changement obligatoire du mot de passe à la première connexion;
- page "Mon profil";
- export PDF par personne;
- export PDF par saison;
- validation des doublons;
- modification d'une saisie par l'utilisateur;
- approbation des heures par un administrateur;
- rôles plus détaillés;
- historique des modifications;
- notifications courriel;
- tableau de bord public anonymisé.

## Licence

Projet interne / communautaire Norcycle.
