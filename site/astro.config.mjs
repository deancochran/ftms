import starlight from "@astrojs/starlight";
import { defineConfig } from "astro/config";
import { canonicalDocs } from "./scripts/content.mjs";
import { base, repository, sidebar, site } from "./site.config.mjs";

// Official configuration: https://starlight.astro.build/manual-setup/
// Pages base path: https://docs.astro.build/en/guides/deploy/github/
export default defineConfig({
  site,
  base,
  trailingSlash: "always",
  output: "static",
  integrations: [
    canonicalDocs(),
    starlight({
      title: "FTMS",
      description: "Transport-independent Fitness Machine Service codecs for TypeScript and C.",
      social: [{ icon: "github", label: "GitHub", href: repository }],
      customCss: ["./src/styles/custom.css"],
      sidebar,
    }),
  ],
});
