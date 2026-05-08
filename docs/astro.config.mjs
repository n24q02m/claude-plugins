import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://mcp.n24q02m.com',
  integrations: [
    starlight({
      title: 'MCP n24q02m',
      description: 'Unified docs for 8 MCP servers + mcp-core foundation library',
      logo: {
        light: './src/assets/logo.svg',
        dark: './src/assets/logo-dark.svg',
        alt: 'MCP n24q02m logo',
        replacesTitle: false,
      },
      favicon: '/favicon.svg',
      head: [
        { tag: 'link', attrs: { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' } },
        { tag: 'link', attrs: { rel: 'apple-touch-icon', href: '/apple-touch-icon.png' } },
        { tag: 'meta', attrs: { property: 'og:type', content: 'website' } },
        { tag: 'meta', attrs: { property: 'og:image', content: 'https://mcp.n24q02m.com/og-image.png' } },
        { tag: 'meta', attrs: { name: 'twitter:card', content: 'summary_large_image' } },
        { tag: 'meta', attrs: { name: 'twitter:image', content: 'https://mcp.n24q02m.com/og-image.png' } },
      ],
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/n24q02m/claude-plugins' },
      ],
      editLink: {
        baseUrl: 'https://github.com/n24q02m/claude-plugins/edit/main/docs/',
      },
      sidebar: [
        { label: 'Get Started', items: [{ autogenerate: { directory: 'get-started' } }] },
        {
          label: 'Servers',
          items: [
            { label: 'mcp-core (Foundation)', items: [{ autogenerate: { directory: 'servers/mcp-core' } }] },
            { label: 'wet-mcp', items: [{ autogenerate: { directory: 'servers/wet-mcp' } }] },
            { label: 'mnemo-mcp', items: [{ autogenerate: { directory: 'servers/mnemo-mcp' } }] },
            { label: 'better-code-review-graph', items: [{ autogenerate: { directory: 'servers/better-code-review-graph' } }] },
            { label: 'imagine-mcp', items: [{ autogenerate: { directory: 'servers/imagine-mcp' } }] },
            { label: 'better-telegram-mcp', items: [{ autogenerate: { directory: 'servers/better-telegram-mcp' } }] },
            { label: 'better-notion-mcp', items: [{ autogenerate: { directory: 'servers/better-notion-mcp' } }] },
            { label: 'better-email-mcp', items: [{ autogenerate: { directory: 'servers/better-email-mcp' } }] },
            { label: 'better-godot-mcp', items: [{ autogenerate: { directory: 'servers/better-godot-mcp' } }] },
          ],
        },
        { label: 'Reference', items: [{ autogenerate: { directory: 'reference' } }] },
      ],
    }),
    sitemap(),
  ],
});
