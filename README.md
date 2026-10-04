# ArcLive

Suivi des compétitions publiques IANSEO par club ou par sélection d'archers.
Vue spectateur distincte des commandes d'administration, recherche dans les
inscriptions publiées, résultats et suivi des changements de scores.

## Fonctionnalités

- Recherche de noms sans accents, avec prénom et nom dans l'ordre souhaité.
- Sélection précise d'un nom et club depuis une compétition publiée.
- Plusieurs clubs suivis, résolution des noms connus vers leurs codes.
- Catalogue des compétitions du jour et à venir avec indication de couverture
  et erreurs de lecture, limité au pays choisi.
- Lecture HTML, protection contre le changement involontaire de concours,
  conservation de la dernière lecture valide par source.
- Différenciation 60 flèches en salle / 72 en TAE standard, sans déduire une
  fin à partir du simple début de la deuxième série. Les formats spéciaux
  sans état final publié nécessitent des métadonnées de format adaptées.
- Deltas marqués comme volées seulement si le nombre de flèches observé
  confirme exactement une volée ; les mises à jour groupées restent distinctes.
- Heure du contrôle et heure de récupération des données séparées.

L'accès complet aux licenciés FFTA n'est pas implémenté ni requis pour ces
fonctions publiques. Un résultat de recherche vide n'indique pas une absence
de licence ou d'inscription.

## Configuration

Voir [la passerelle sécurisée](docs/admin-bridge.md) pour Cloudflare et
l'authentification. Les champs vides de `data/admin_config.json` doivent être
remplis après déploiement du Worker pour activer l'administration distante
et le proxy HTML à faible délai. GitHub Pages ne peut pas exécuter le Worker.

Les scripts Python utilisent la bibliothèque standard. Les variables GitHub
`IANSEO_URLS` / `IANSEO_URL`, si renseignées, sont des overrides explicites ;
sinon `data/competition_sources.json` détermine les sources du flux JSON.

## Vérification

À exécuter depuis la racine :

```sh
python -m unittest discover -s tests -v
node tests/frontend.test.cjs
node tests/worker.test.mjs
```

Le workflow `Validate ArcLive` ajoute un test Chromium de l'interface avec
des fixtures interceptées, sans appeler IANSEO ni publier d'état. Les tests
couvrent les recherches, homonymes de clubs différents, sources en erreur,
formats 60/72, compétitions du jour, authentification, CORS et URLs du proxy.
