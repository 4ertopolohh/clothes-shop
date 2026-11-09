import { readFile, writeFile, mkdir } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import { resolve, dirname } from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const snapshot = resolve(root, ".cache/public.json");
execFileSync(
  "poetry",
  ["run", "python", "manage.py", "export_public", "--output", snapshot],
  { cwd: resolve(root, "../backend"), stdio: "inherit" },
);
const { data, site_url: exportedSiteUrl } = JSON.parse(await readFile(snapshot, "utf8"));
const site_url = process.env.PUBLIC_SITE_URL || exportedSiteUrl;
const { render } = await import(
  pathToFileURL(resolve(root, ".ssr/entry-server.js")).href
);
const template = await readFile(resolve(root, "dist/index.html"), "utf8");
const settings = data["/settings/"];
const routes = [
  ["/", "ATELIER NOIR — Contemporary Uniform", settings.hero_text],
  ["/catalog", "Каталог · ATELIER NOIR", "Коллекция ATELIER NOIR."],
  [
    "/contacts",
    "Контакты · ATELIER NOIR",
    "Связаться с магазином ATELIER NOIR.",
  ],
];
for (const [key, value] of Object.entries(data)) {
  if (key.startsWith("/products/"))
    routes.push([
      "/product/" + value.slug,
      value.name + " · ATELIER NOIR",
      value.description,
    ]);
  if (key.startsWith("/pages/")) {
    const slug = key.split("/")[2];
    routes.push([
      slug === "delivery" ? "/delivery" : "/documents/" + slug,
      value.title + " · ATELIER NOIR",
      value.description,
    ]);
  }
}
const escape = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const json = (value) => JSON.stringify(value).replace(/</g, "\\u003c");
for (const [route, title, description] of routes) {
  const subset = { "/settings/": settings };
  if (route === "/") subset["/catalog/?new=1&page=1"] = data["/catalog/?new=1&page=1"];
  if (route === "/catalog") {
    subset["/catalog/facets/"] = data["/catalog/facets/"];
    subset["/catalog/?&page=1"] = data["/catalog/?&page=1"];
  }
  if (route.startsWith("/product/")) {
    const key = "/products/" + route.split("/")[2] + "/";
    subset[key] = data[key];
  }
  const pageKey =
    "/pages/" +
    (route === "/delivery" ? "delivery" : route.split("/")[2]) +
    "/";
  if (data[pageKey]) subset[pageKey] = data[pageKey];
  const canonical = site_url.replace(/\/$/, "") + route;
  const body = render(route, subset);
  let html = template.replace(
    /<title>.*?<\/title>/s,
    "<title>" + escape(title) + "</title>",
  );
  html = html.replace(
    /<meta\s+name="description"[\s\S]*?>/,
    '<meta name="description" content="' + escape(description) + '">',
  );
  html = html.replace(
    "</head>",
    `<link rel="canonical" href="${escape(canonical)}"><meta property="og:title" content="${escape(title)}"><meta property="og:description" content="${escape(description)}"><meta property="og:type" content="website"><meta property="og:url" content="${escape(canonical)}"><meta property="og:image" content="${escape(site_url.replace(/\/$/, "") + settings.hero_image)}"></head>`,
  );
  html = html.replace(
    '<div id="root"></div>',
    '<div id="root">' +
      body +
      '</div><script id="public-data" type="application/json">' +
      json(subset) +
      "</script>",
  );
  const output = resolve(
    root,
    "dist",
    route === "/" ? "index.html" : route.slice(1) + "/index.html",
  );
  await mkdir(dirname(output), { recursive: true });
  await writeFile(output, html);
}
const notFound = template.replace(
  '<div id="root"></div>',
  '<div id="root">' +
    render("/not-found", { "/settings/": settings }) +
    "</div>",
);
await writeFile(resolve(root, "dist/404.html"), notFound);
await writeFile(
  resolve(root, "dist/robots.txt"),
  "User-agent: *\nAllow: /\nDisallow: /checkout\nDisallow: /order/\nDisallow: /payment/\nDisallow: /api/\nDisallow: /admin/\nSitemap: " +
    site_url.replace(/\/$/, "") +
    "/sitemap.xml\n",
);
await writeFile(
  resolve(root, "dist/sitemap.xml"),
  '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
    routes
      .map(
        ([route]) =>
          "<url><loc>" +
          escape(site_url.replace(/\/$/, "") + route) +
          "</loc></url>",
      )
      .join("") +
    "</urlset>",
);
console.log(
  `Предрендеринг: ${routes.length} публичных страниц, sitemap и 404.`,
);
