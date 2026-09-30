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
    source: "examples/typescript-quickstart/README.md",
    slug: "start/typescript",
    title: "TypeScript / JavaScript",
    group: "Getting started",
  },
  {
    source: "examples/c-client/README.md",
    slug: "start/c",
    title: "C / C++",
    group: "Getting started",
  },
  {
    source: "docs/integration.md",
    slug: "integration/cookbook",
    title: "Cookbook",
    group: "Integration",
  },
  {
    source: "docs/transport-recipes.md",
    slug: "integration/transports",
    title: "Transport recipes",
    group: "Integration",
  },
  {
    source: "docs/troubleshooting.md",
    slug: "integration/troubleshooting",
    title: "Troubleshooting",
    group: "Integration",
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
    source: "shared/protocol/capability-discovery.md",
    slug: "reference/capabilities",
    title: "Capability evidence",
    group: "Reference",
  },
  {
    source: "docs/released-packages.md",
    slug: "project/releases",
    title: "Releases and support",
    group: "Project",
  },
  {
    source: "CONTRIBUTING.md",
    slug: "project/contributing",
    title: "Contributing",
    group: "Project",
  },
  { source: "docs/roadmap.md", slug: "project/roadmap", title: "Roadmap", group: "Project" },
  {
    source: "docs/README.md",
    slug: "project/documentation",
    title: "Documentation and evidence",
    group: "Project",
  },
  { source: "SECURITY.md", slug: "project/security", title: "Security", group: "Project" },
];

export const sidebar = [
  // Starlight prefixes sidebar links with Astro's base; Markdown/hero links are explicit.
  { label: "Overview", link: "/" },
  ...["Getting started", "Integration", "Reference", "Project"].map((label) => ({
    label,
    items: pages
      .filter((page) => page.group === label)
      .map((page) => ({ label: page.title, slug: page.slug })),
  })),
  { label: "Generated TypeScript API", link: "/api/typescript/" },
];
