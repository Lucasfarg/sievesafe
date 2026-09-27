// Print paper/build/*.html to PDF with Chromium (Playwright). Run after build.py.
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const { chromium } = createRequire(import.meta.url)("playwright");
const here = path.dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch();
for (const name of ["sievesafe-preprint", "tripod-llm-checklist"]) {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(path.join(here, "build", `${name}.html`)).href);
  await page.pdf({ path: path.join(here, `${name}.pdf`), format: "A4", printBackground: true,
                   displayHeaderFooter: true, headerTemplate: "<span></span>",
                   footerTemplate: '<div style="font-size:8pt;width:100%;text-align:center;color:#666"><span class="pageNumber"></span></div>',
                   margin: { top: "20mm", bottom: "20mm", left: "20mm", right: "20mm" } });
}
await browser.close();
