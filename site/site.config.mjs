import { guidePage } from "../tools/port-catalog.mjs";

// One source for the Pages URL, repository links and mapped documentation routes.
export const site = "https://deancochran.github.io";
export const base = "/ftms";
export const repository = "https://github.com/deancochran/ftms";
export const sourceBranch = "main";
export const sitePath = (route = "") => `${base}/${route ? `${route}/` : ""}`;

// Only these public files are rendered. Historical audits remain linked on GitHub.
export const pages = [
  { source: "site/landing.md", slug: "", title: "FTMS Protocol Libraries", group: null },
  {
    source: "docs/ftms-explained.md",
    slug: "start/ftms-explained",
    title: "What is FTMS?",
    group: "Getting started",
  },
  {
    source: "packages/README.md",
    slug: "start/choose-language",
    title: "Choose a language",
    group: "Getting started",
  },
  ...["c", "csharp", "dart", "go", "kotlin", "python", "rust", "swift", "typescript"].map(
    guidePage,
  ),
  {
    source: "docs/install.md",
    slug: "start/installation",
    title: "Installation and upgrades",
    group: "Getting started",
  },
  {
    source: "docs/integration.md",
    slug: "integration/cookbook",
    title: "TypeScript and C cookbook",
    group: "Guides",
  },
  {
    source: "docs/transport-recipes.md",
    slug: "integration/transports",
    title: "Transport recipes",
    group: "Guides",
  },
  {
    source: "docs/troubleshooting.md",
    slug: "integration/troubleshooting",
    title: "Troubleshooting",
    group: "Guides",
  },
  { source: "docs/api.md", slug: "reference/api", title: "API index", group: "Reference" },
  {
    source: "packages/typescript/README.md",
    slug: "reference/typescript",
    title: "TypeScript guide",
    group: "Reference",
  },
  { source: "packages/c/README.md", slug: "reference/c", title: "C guide", group: "Reference" },
  {
    source: "packages/c/INSTALL.md",
    slug: "reference/c-install",
    title: "C installation options",
    group: "Reference",
  },
  {
    source: "docs/coverage.md",
    slug: "reference/coverage",
    title: "Protocol coverage",
    group: "Reference",
  },
  {
    source: "docs/support-profiles.md",
    slug: "reference/support-profiles",
    title: "Support profiles",
    group: "Reference",
  },
  {
    source: "shared/protocol/capability-discovery.md",
    slug: "reference/capabilities",
    title: "Capability evidence",
    group: "Reference",
  },
  {
    source: "docs/released-packages.md",
    slug: "project/releases",
    title: "Current releases and evidence",
    group: "Releases",
  },
  {
    source: "CONTRIBUTING.md",
    slug: "project/contributing",
    title: "Contributing",
    group: "Contributing",
  },
  { source: "docs/roadmap.md", slug: "project/roadmap", title: "Roadmap", group: "Contributing" },
  {
    source: "docs/README.md",
    slug: "project/documentation",
    title: "Documentation map",
    group: "Reference",
  },
  { source: "SECURITY.md", slug: "project/security", title: "Security", group: "Releases" },
  {
    source: "docs/releasing.md",
    slug: "project/releasing",
    title: "Release process",
    group: "Contributing",
  },
  {
    source: "docs/release-1.0.md",
    slug: "project/release-one-zero",
    title: "1.0 release milestone",
    group: "Contributing",
  },
  {
    source: "docs/versioning.md",
    slug: "project/versioning",
    title: "Versioning",
    group: "Releases",
  },
  {
    source: "docs/evidence.md",
    slug: "project/evidence",
    title: "Historical audits and evidence",
    group: "Contributing",
  },
  {
    source: "docs/architecture.md",
    slug: "project/architecture",
    title: "Architecture",
    group: "Contributing",
  },
  {
    source: "docs/equipment-testing.md",
    slug: "project/equipment-testing",
    title: "Equipment testing",
    group: "Contributing",
  },
];

export const sidebar = [
  // Starlight prefixes sidebar links with Astro's base; Markdown/hero links are explicit.
  { label: "Overview", link: "/" },
  ...["Getting started", "Guides", "Reference", "Releases", "Contributing"].map((label) => ({
    label,
    items: pages
      .filter((page) => page.group === label)
      .map((page) => ({ label: page.title, slug: page.slug })),
  })),
  { label: "Generated TypeScript API", link: "/api/typescript/" },
];
