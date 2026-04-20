export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return cors(new Response(null, { status: 204 }));
    if (request.method !== "POST") return cors(json({ error: "Method not allowed" }, 405));

    const body = await request.json().catch(() => ({}));
    const action = String(body.action || "");
    const clubKeywords = String(body.club_keywords || "").trim();

    if (!env.GITHUB_OWNER || !env.GITHUB_REPO || !env.GITHUB_TOKEN) {
      return cors(json({ error: "Missing required env vars" }, 500));
    }

    let workflowFile = "";
    if (action === "find_next") workflowFile = "find-next-competition.yml";
    else if (action === "update_live") workflowFile = "update-live.yml";
    else if (action === "reset_live") workflowFile = "reset-live.yml";
    else return cors(json({ error: "Unsupported action" }, 400));

    const url = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${workflowFile}/dispatches`;
    const payload = {
      ref: env.GITHUB_REF || "main",
      inputs: {}
    };
    if (clubKeywords) payload.inputs.club_keywords = clubKeywords;

    const ghRes = await fetch(url, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "seynod-admin-bridge"
      },
      body: JSON.stringify(payload)
    });

    if (!ghRes.ok) {
      const txt = await ghRes.text();
      return cors(json({ ok: false, status: ghRes.status, error: txt.slice(0, 3000) }, 500));
    }

    return cors(json({ ok: true, workflow: workflowFile, club_keywords: clubKeywords || null }, 200));
  }
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" }
  });
}

function cors(response) {
  const headers = new Headers(response.headers);
  headers.set("Access-Control-Allow-Origin", "*");
  headers.set("Access-Control-Allow-Methods", "POST, OPTIONS");
  headers.set("Access-Control-Allow-Headers", "Content-Type");
  return new Response(response.body, { status: response.status, headers });
}
