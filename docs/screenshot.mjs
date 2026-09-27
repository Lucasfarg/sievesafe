// Screenshots of `sievesafe serve` for the README, light and dark, at the confirm step (nothing is spent).
//
//   sievesafe serve --no-browser --port 8765 --dir /tmp/sievesafe-shot &
//   NODE_PATH=<dir containing playwright> node docs/screenshot.mjs [http://127.0.0.1:8765/]
//
// Uses the fictional fixture tests/fixtures/pubmed.nbib; writes docs/serve-light.png and docs/serve-dark.png.
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";

const { chromium } = createRequire(import.meta.url)("playwright");  // CommonJS resolution, so NODE_PATH works
const here = path.dirname(fileURLToPath(import.meta.url));
const url = process.argv[2] || "http://127.0.0.1:8765/";
const criteria = [
  "Inclusion: randomised or non-randomised studies of emicizumab prophylaxis in people with haemophilia A, reporting bleeding rates or pharmacokinetics.",
  "Exclusion: letters, editorials, case reports and studies without original data.",
].join("\n");

const browser = await chromium.launch();
for (const scheme of ["light", "dark"]) {
  const page = await browser.newPage({ viewport: { width: 900, height: 1200 }, colorScheme: scheme, deviceScaleFactor: 1 });
  await page.goto(url);
  await page.setInputFiles("#file", path.join(here, "..", "tests", "fixtures", "pubmed.nbib"));
  await page.fill("#title", "Emicizumab prophylaxis in people with haemophilia A");
  await page.fill("#criteria", criteria);
  await page.click("#estimate");
  await page.waitForSelector("#confirm:not([hidden])");
  await page.screenshot({ path: path.join(here, `serve-${scheme}.png`), fullPage: true });
  await page.close();
}
await browser.close();
