# Documentation website

Private Astro + Starlight workspace. It builds static files for GitHub Pages at
`https://deancochran.github.io/ftms/`; it is not an npm library or a server application.

## Develop and verify

Use Node **22.12+** (Node 24 in the site workflow) and pnpm 10.33.0. This site
toolchain does not raise the published TypeScript library's Node 20 requirement.
From the repository root:

```sh
pnpm install --frozen-lockfile --ignore-scripts
pnpm site:dev
```

Open the printed URL with `/ftms/`. Canonical Markdown changes are watched and
regenerated during development. Changes to TypeScript API source require restarting
`site:dev` to regenerate TypeDoc. Use the production build to exercise search:

```sh
pnpm site:verify
pnpm site:preview
```

`site:verify` runs Biome, repository documentation checks, content/link tests,
TypeDoc generation, Astro type checking, the static build and output verification.
Generated content, API HTML, `.astro/`, and `dist/` are ignored, never committed.
Set `ASTRO_TELEMETRY_DISABLED=1` in your shell to opt out of Astro CLI telemetry;
the Pages workflow sets it explicitly.

Browser smoke checks use the production build, not the development server:

```sh
pnpm --filter @ftms/site exec playwright install chromium
pnpm site:test:browser
```

CI installs Chromium's Linux dependencies with `--with-deps`. Tests cover desktop
and mobile navigation, search, theme selection and the generated API reference.

## Content ownership

- `site.config.mjs`: URL/base, explicit source-to-route map and sidebar.
- `landing.md`: website-only introduction. Guides remain in `docs/`, package
  READMEs and `examples/`; never maintain a second editable copy here.
- `scripts/content.mjs`: a small Astro integration stages those canonical files
  into ignored `src/content/docs/`. Markdown is parsed, not rewritten with regex;
  code fences and GFM tables are preserved. Local links/reference definitions are
  resolved against the original file. Mapped pages become base-aware site links;
  other public files link to GitHub. Missing/private paths fail the build.
- Generated page edit links point to the canonical source, not the staged copy.
- `packages/typescript/docs/api/` is rebuilt with TypeDoc and copied into the
  ignored `public/api/typescript/` directory. It has its own reference UI/search;
  no API-theme bridge plugin is required.
- `packages/typescript/typedoc.markdown.json` runs the same authoritative TypeDoc
  entry point and exclusions through `typedoc-plugin-markdown`. `scripts/ai-docs.mjs`
  then stages `llms.txt`, `llms-full.txt`, each explicit page's
  `<route>/index.md`, and API Markdown beneath `.generated/ai-docs/`. The static
  build copies that staging tree into its ignored `dist/` output. The index records
  the exact Git revision and scope. The full corpus includes only those explicit
  pages and generated public TypeScript API signatures; it deliberately excludes
  `.context/`, unlisted files, HTML, and device/private material. Re-running at
  the same revision is deterministic, and the generated manifest removes only
  formerly generated stale Markdown paths.
- Every rendered page exposes an **AI documentation** link and a **View Markdown**
  link, plus `rel="describedby"` and `rel="alternate"` metadata for the curated
  index and that page's Markdown representation.

Do not add broad filesystem discovery: only explicitly mapped public documents
are rendered. Historical audits remain reachable through the evidence index but
are not promoted into the primary navigation. No private `.context` data is loaded.

## Customize without another framework

Use `src/styles/custom.css` for documented Starlight color and layout variables.
Use `astro.config.mjs` for site title, social links and Starlight options. Sidebar
links are base-relative because Starlight prefixes them; Markdown and hero links
are generated with `sitePath()` and include the Pages base explicitly.

The initial site uses Starlight's built-in documentation UI only. There is no
React/Svelte runtime, Tailwind dependency or custom component system. If a future
interactive tool needs custom UI components, use **shadcn/ui**, scoped to that
feature, rather than building another design system. Do not replace accessible
Starlight navigation/search merely to introduce a component library.

Biome is the sole formatting/linting tool for supported authored JS/TS/JSON/CSS.
Markdown is checked for links and rendered by Astro. No Prettier or ESLint setup
is introduced; Astro's checker handles its framework-specific types.

## GitHub Pages deployment

[The reusable workflow](../.github/workflows/docs.yml) builds/tests when selected
by [CI](../.github/workflows/ci.yml) on PRs and main pushes, or on manual dispatch.
PRs never receive deployment permissions or publish artifacts. Main deployment
also requires repository variable `PAGES_ENABLED=true` so merely merging the
workflow does not activate a public site unexpectedly.

With explicit maintainer authorization:

1. Set **Settings → Pages → Source → GitHub Actions**.
2. Configure the `github-pages` environment to allow main deployments; add
   required reviewers if manual approval is desired.
3. Set repository Actions variable **`PAGES_ENABLED` to `true`**.
4. Run **Documentation site** on main, or merge the next approved update.
5. Verify the live homepage, quickstarts, search, assets and API link beneath
   `/ftms/`. A passing local build is not evidence that publication succeeded.

Only the deployment job gets `pages: write` and `id-token: write`; the build job
has `contents: read`. Official GitHub actions are pinned to commit SHAs. No PAT,
generated branch, committed HTML, backend, CMS or third-party hosting is needed.
Package-publishing workflows and tags are unchanged. Set `PAGES_ENABLED=false`
to stop future deployments without changing the last published site.

For a custom domain, update `site` and `base` together in `site.config.mjs`, adjust
browser-test URLs, add the required domain/DNS configuration separately, and
re-run output checks. Do not edit generated HTML or scatter literal base paths.

## Official references used

- [Starlight manual setup](https://starlight.astro.build/manual-setup/)
- [Starlight styling](https://starlight.astro.build/guides/css-and-tailwind/)
- [Starlight component customization](https://starlight.astro.build/guides/overriding-components/)
- [Static Pagefind search](https://starlight.astro.build/guides/site-search/)
- [Astro GitHub Pages deployment and base URL](https://docs.astro.build/en/guides/deploy/github/)
- [GitHub custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

Versions were selected against the package registry and these guides, then pinned
in the existing pnpm lockfile. GitHub's explicit build/upload/deploy steps are
used instead of an opaque build wrapper so repository checks and the TypeDoc
prerequisite run through the same commands locally and in CI.
