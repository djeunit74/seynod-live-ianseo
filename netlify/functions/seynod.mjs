export default async () => {
  const sourceUrl = "https://www.ianseo.net/TourData/2026/27251/IC.php";
  try {
    const res = await fetch(sourceUrl, {
      headers: { "user-agent": "Mozilla/5.0 (compatible; NetlifyFunction/1.0; +https://www.netlify.com/)" }
    });
    if (!res.ok) return json({ error: `Source IANSEO inaccessible (${res.status})` }, 502);
    const raw = await res.text();
    const data = extractSeynod(raw);
    data.sourceUrl = sourceUrl;
    return json(data, 200);
  } catch (err) {
    return json({ error: err.message || "Erreur serveur" }, 500);
  }
};

function json(payload, status = 200) {
  return new Response(JSON.stringify(payload, null, 2), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" }
  });
}

function decodeEntities(s) {
  return s.replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">");
}

function htmlToText(html) {
  return decodeEntities(
    html
      .replace(/<script[\s\S]*?<\/script>/gi, " ")
      .replace(/<style[\s\S]*?<\/style>/gi, " ")
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/(div|p|tr|table|section|article|header|footer|li|h1|h2|h3|h4|h5|h6|tbody|thead)>/gi, "\n")
      .replace(/<[^>]+>/g, " ")
  )
    .replace(/\u00a0/g, " ")
    .replace(/\r/g, "")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function cleanCategory(line) { return line.replace(/\s+/g, " ").replace(/\s+\[/, " [").trim(); }
function parseProgress(category) { const m = category.match(/\[(.+)\]$/); return m ? m[1] : "Progression non trouvée"; }
function baseCategory(category) { return category.replace(/\s*\[.+\]$/, "").trim(); }
function latestCategoryArrows(progress) {
  const arr = [...progress.matchAll(/Après\s+(\d+)\s+flèches/gi)].map(m => Number(m[1]));
  return arr.length ? arr[arr.length - 1] : null;
}

function parseArcherLine(line) {
  const rx = /^(\d+)\s+(.+?)\s+(\d{7}\s*-\s*Seynod)\s+(\d+)\/\s*(\d+)\s+(\d+)\/\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$/i;
  const m = line.match(rx);
  if (!m) return null;
  return {
    position: m[1],
    name: m[2].replace(/\s+/g, " ").trim(),
    club: m[3].replace(/\s+/g, " ").trim(),
    series1: Number(m[4]),
    series1_aux: Number(m[5]),
    series2: Number(m[6]),
    series2_aux: Number(m[7]),
    total: Number(m[8]),
    tens: Number(m[9]),
    xs: Number(m[10]),
  };
}

function parseDetail(detail) {
  const matches = [...detail.matchAll(/([0-9]+m)-([12]):\s*(\d+)/gi)];
  return matches.map(m => ({ distance: m[1], series: Number(m[2]), score: Number(m[3]) }));
}

function isJohannaLive(name, category, categoryProgress) {
  return /KOZUCHOWICZ\s+Johanna/i.test(name)
    && /Arc Classique/i.test(category)
    && /Départ:\s*3/i.test(categoryProgress)
    && (latestCategoryArrows(categoryProgress) || 0) < 72;
}

function inferFinished(parsed, name, category, categoryProgress) {
  if (isJohannaLive(name, category, categoryProgress)) return false;
  return parsed.series1 > 0 && parsed.series2 > 0;
}

function inferRowArrows(parsed, name, category, categoryProgress) {
  if (isJohannaLive(name, category, categoryProgress)) {
    const catArrows = latestCategoryArrows(categoryProgress);
    if (catArrows !== null) return catArrows;
  }
  if (parsed.series1 > 0 && parsed.series2 > 0) return 72;
  const catArrows = latestCategoryArrows(categoryProgress);
  return catArrows !== null ? catArrows : null;
}

function makeScoreLabel(total, arrows) {
  return arrows ? `${total} (après ${arrows} flèches)` : String(total);
}

function makeProgressLabel(finished, arrows, categoryProgress, name, category) {
  if (isJohannaLive(name, category, categoryProgress) && arrows) return `En cours (${arrows} flèches)`;
  if (finished) return "Terminé (72 flèches)";
  if (arrows) return `En cours (${arrows} flèches)`;
  return "Progression non trouvée";
}

function extractSeynod(rawHtml) {
  const text = htmlToText(rawHtml);
  const lines = text.split("\n").map(s => s.trim()).filter(Boolean);

  let currentCategory = "";
  let currentProgress = "";
  const archers = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (/^(Arc Classique|Arc à Poulies|Arc Nu|Barebow|Recurve|Compound)/i.test(line) && /\[.*\]$/.test(line)) {
      currentCategory = cleanCategory(line);
      currentProgress = parseProgress(currentCategory);
      continue;
    }

    if (!/Seynod/i.test(line) || !/^\d+\s+/.test(line)) continue;

    const parsed = parseArcherLine(line);
    if (!parsed) continue;

    let detail = "Détail non trouvé";
    if (i + 2 < lines.length && /^\d{7}\s*-\s*Seynod$/i.test(lines[i + 1]) && /m-1:/.test(lines[i + 2])) {
      detail = lines[i + 2].replace(/,\s*/g, " • ");
    } else {
      for (let j = i + 1; j <= Math.min(i + 4, lines.length - 1); j++) {
        if (/m-1:/.test(lines[j])) { detail = lines[j].replace(/,\s*/g, " • "); break; }
      }
    }

    const category = baseCategory(currentCategory) || "Catégorie non trouvée";
    const progress = currentProgress || "Progression non trouvée";
    const finished = inferFinished(parsed, parsed.name, category, progress);
    const arrows = inferRowArrows(parsed, parsed.name, category, progress);

    archers.push({
      name: parsed.name,
      club: parsed.club,
      position: parsed.position,
      score: parsed.total,
      scoreLabel: makeScoreLabel(parsed.total, arrows),
      category,
      progress: makeProgressLabel(finished, arrows, progress, parsed.name, category),
      detail,
      finished
    });
  }

  const unique = dedupeArchers(archers);
  const categories = [...new Set(unique.map(a => a.category))].filter(Boolean);
  unique.sort((a, b) => {
    if (a.finished !== b.finished) return a.finished ? -1 : 1;
    const c = a.category.localeCompare(b.category, "fr");
    if (c) return c;
    return Number(a.position) - Number(b.position);
  });
  return { archers: unique, categories };
}

function dedupeArchers(items) {
  const out = [], seen = new Set();
  for (const a of items) {
    const key = [a.name, a.category, a.position, a.score, a.detail, a.finished, a.progress].join("|");
    if (!seen.has(key)) { seen.add(key); out.push(a); }
  }
  return out;
}
