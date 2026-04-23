# Admin bridge (mode automatique)

Objectif: permettre au bouton Admin de lancer automatiquement les workflows GitHub avec le club saisi dans l'app.

## 1) Déployer le worker
- Utiliser `scripts/github_admin_bridge_worker.js` sur Cloudflare Workers.
- Variables à configurer:
  - `GITHUB_OWNER` = `djeunit74`
  - `GITHUB_REPO` = `seynod-live-ianseo`
  - `GITHUB_REF` = `main`
  - `GITHUB_TOKEN` = PAT GitHub avec droit `repo` + `workflow`

## 2) Brancher l'app
- Éditer `data/admin_config.json`:

```json
{
  "adminBridgeUrl": "https://<ton-worker>.workers.dev"
}
```

## 3) Utilisation
- Dans l'Admin:
  - remplir `Club à suivre`
  - cliquer `Tout en 1 : Démarrer compétition` pour trouver la prochaine compétition et basculer la source live automatiquement
  - ou cliquer `Chercher prochaine compétition ...` pour une recherche seule
- Si la passerelle est configurée, l'app déclenche automatiquement les workflows et attend les nouveaux fichiers.

## 4) Pilotage public partagé
- L'admin pousse aussi un état partagé dans `data/admin_state.json` via le workflow `save-admin-state.yml`.
- Cet état est relu par l'app publique (club, pays, tournois suivis, phase, contrôle public, archers surveillés).
- Résultat: la vue publique suit le pilotage admin même sur un autre appareil/navigateur.
