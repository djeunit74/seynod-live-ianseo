# Passerelle ArcLive : HTML public et administration sécurisée

Le site statique peut rechercher dans les inscriptions déjà publiées sans accès
FFTA. La publication partagée et la lecture HTML à faible délai utilisent le
Worker fourni dans `scripts/github_admin_bridge_worker.js`.

## Déploiement Cloudflare

1. Créer un Worker et y déposer ce fichier JavaScript (module ES).
2. Configurer les variables :
   - `GITHUB_OWNER` : `djeunit74`
   - `GITHUB_REPO` : `seynod-live-ianseo`
   - `GITHUB_REF` : `main`
   - `ALLOWED_ORIGINS` : les origines exactes des sites autorisés, séparées par
     des virgules, par exemple `https://djeunit74.github.io` et, si utilisé,
     `https://jourdecompette.pages.dev`.
3. Créer deux **secrets Cloudflare**, jamais dans le dépôt :
   - `GITHUB_TOKEN` : token GitHub limité à ce dépôt avec la permission Actions
     en écriture pour déclencher ses workflows.
   - `ADMIN_TOKEN` : clé privée aléatoire pour l'administrateur.
4. Remplacer les champs vides de `data/admin_config.json` par l'URL réelle :

```json
{
  "adminBridgeUrl": "https://TON-WORKER.workers.dev",
  "ianseoProxyUrl": "https://TON-WORKER.workers.dev"
}
```

Aucune URL de Worker ni clé n'est inventée. Tant que cette configuration n'est
pas faite, le proxy Jina reste un secours dont la fraîcheur n'est pas garantie,
et l'administration distante est fermée.

## Utilisation

- Vue spectateur : URL du site sans paramètre admin ; aucune recherche visible.
- Administration : URL du site avec `?admin=1`, puis saisie de la clé privée.
  La clé n'est conservée que dans la mémoire de la page. Un rechargement impose
  une nouvelle authentification.
- Les anciens paramètres publics et la session `slc_admin_ok` n'accordent plus
  d'accès. Sur `localhost`, l'édition locale est possible sans serveur ; une
  publication distante exige toujours la clé.
- Choisir le mode **clubs** pour tous leurs participants, ou **archers** pour
  une sélection exacte de noms et clubs dans les inscriptions du catalogue.
- La sélection d'un archer ajoute aussi la compétition choisie. Les homonymes
  de clubs différents restent séparés. Un nom et club identiques sans
  identifiant officiel restent une ambiguïté des données publiques.
- **Actualiser le catalogue** demande une reconstruction GitHub pour le pays
  choisi. Attendre sa fin puis relancer la recherche.
- **Publier l'état partagé** sauvegarde les clubs, le mode, les archers, les
  tournois et les réglages. Le contrôle public ON publie automatiquement les
  modifications ; OFF suspend ces publications automatiques.

## Fraîcheur et erreurs

`GET /ianseo?url=...` accepte uniquement les pages HTML autorisées de
`https://www.ianseo.net`. Le cache du proxy dure 15 secondes au maximum. Les
redirections ne sont pas suivies. Le navigateur contrôle à une cadence cible
de 30 secondes pendant un départ actif, sans lectures concurrentes ; une
lecture dépassant la cadence peut la retarder. Hors tir, la découverte est
espacée à cinq minutes. Les résultats observés comme terminés arrêtent le
suivi, sauf si un départ sélectionné reste à venir.

L'heure affichée est celle de récupération HTTP, **pas** une garantie que
l'organisateur a saisi ses derniers scores. Le flux JSON de secours est
produit par GitHub Actions, dont la cadence programmée de cinq minutes peut
subir des retards. Les snapshots sans changement ne déclenchent plus de
commits et de reconstruction Pages ; leur horodatage reste celui du snapshot
conservé.

Les erreurs sont indiquées par source et les derniers scores de cette source
sont conservés. Le catalogue distingue lecture impossible, inscriptions
non détectées et inscriptions publiées. Une panne ne devient pas une preuve
d'absence d'inscription. Les PDF et les essais d'identifiants de concours
voisins ne sont plus utilisés pour les scores live.

## Limite FFTA

Ce catalogue n'est pas un annuaire des licenciés. Il ne peut retrouver que les
archers présents dans les publications IANSEO analysées. Un accès autorisé à
la FFTA pourrait confirmer les identités et effectifs actuels ; un annuaire de
licenciés seul ne fournirait ni toutes les inscriptions ni les scores live.
