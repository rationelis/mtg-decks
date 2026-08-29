import "./style.css";
import { getMeta } from "./data";
import { navigate } from "./router";

const root = document.getElementById("app");
if (!root) throw new Error("#app not found");

window.addEventListener("hashchange", () => void navigate(root));
void navigate(root);

// Data-quality banner: fetched in the background and never blocks the
// initial render of any view.
void showStatusBanner();

async function showStatusBanner(): Promise<void> {
  const banner = document.getElementById("status-banner");
  if (!banner) return;

  try {
    const meta = await getMeta();
    if (meta.unresolvedCount === 0 && meta.warnings.length === 0) return;

    banner.hidden = false;
    banner.textContent = `⚠ ${meta.unresolvedCount} unresolved card(s), ${meta.warnings.length} build warning(s) — data generated ${new Date(meta.generatedAt).toLocaleString()}`;
    banner.title = meta.warnings.join("\n");
  } catch {
    // If meta.json itself can't be loaded, silently skip the banner -
    // this is a nice-to-have, not something that should ever break a view.
  }
}
