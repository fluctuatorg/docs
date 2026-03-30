> Keep this file updated as product naming, supported markets, and documentation scope evolve.
> For Mintlify product knowledge (components, configuration, writing standards), use the Mintlify skill: `npx skills add https://mintlify.com/docs`

# Documentation project instructions

## About this project

- This is a documentation site built on [Mintlify](https://mintlify.com)
- Pages are MDX files with YAML frontmatter
- Configuration lives in `docs.json`
- Run `mint dev` to preview locally
- Run `mint broken-links` to check links

## Terminology

- Use `merchant` for the business integrating with Xendit.
- Use `customer` for the person paying the merchant.
- Use `end user` only when describing API objects or flows that use that exact term.
- Use `business` for account, onboarding, and verification context.
- Use `Xendit Dashboard` when referring to the UI.
- Keep mode names as `Test Mode` and `Live Mode` (exact capitalization).
- Use `payment products` for integration options (for example: Payments API, Subscriptions, Payment Sessions, Plug-ins).
- Use `payment channels` for rails/providers (for example: cards, virtual accounts, e-wallets, QR).
- Use `sub-account` (hyphenated) and preserve `xenPlatform` casing exactly.
- Default to `payouts` for send-money content; use `disbursement` only when matching API or product naming.

## Style preferences

- Use active voice and second person ("you")
- Keep sentences concise — one idea per sentence
- Use sentence case for headings
- Bold for UI elements: Click **Settings**
- Code formatting for file names, commands, paths, and code references
- Start pages with a short overview sentence before details or procedures.
- For procedural pages, prefer `<Steps>` or numbered lists with clear action-first instructions.
- For country or use-case variants, prefer `<Tabs>` and clearly label each option.
- Define acronyms on first use (for example: `2FA`, `TOTP`, `MIT`).
- Use root-relative internal links (for example: `/get-started/your-dashboard`) and avoid `../` links.
- Prefer concise tables for comparisons (products, flows, channel behavior), then link out for full API detail.
- Keep references to support channels explicit when users must contact Xendit (for example: `help@xendit.co`).

## Content boundaries

- Document merchant-facing capabilities available in Dashboard and published API references.
- Cover onboarding, verification, integration setup, payments, payouts, and xenPlatform use cases.
- Keep country/channel guidance aligned to currently supported markets shown in docs navigation.
- Do not document internal admin tools, manual review playbooks, or internal risk/compliance decision logic.
- Do not publish secrets or operationally sensitive details (API keys, webhook tokens, internal endpoints).
- Do not provide legal, tax, or regulatory advice beyond listing required documents and official requirements.
- Avoid duplicating low-level API reference fields in guides when a link to API reference is sufficient.
- Mark legacy content clearly and prefer current product paths when both legacy and new flows exist.
