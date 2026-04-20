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
  - cliquer `Chercher prochaine compétition ...`
- Si la passerelle est configurée, l'app déclenche automatiquement le workflow et attend le nouveau résultat.
