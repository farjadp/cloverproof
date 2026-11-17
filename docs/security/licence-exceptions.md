# Licence exceptions register (named, pending lawyer review)

Owner: `ciso`. Rule (CLAUDE.md "Licences"): no GPL/AGPL/EUPL dependencies; LGPL and other copyleft only **by name**, each with an ADR and a lawyer's review. CI enforces the package-level entries (`.github/workflows/security.yml`, job `licenses`). System libraries are not visible to CI and are tracked here only.

| Component | Licence (as used) | How it reaches us | Use | CI-enforced | ADR | Lawyer review |
|---|---|---|---|---|---|---|
| `psycopg`, `psycopg-binary`, `psycopg-pool` | LGPL-3.0-only | Python dependency (Postgres driver) | unmodified, dynamically imported, hosted service (no distribution) | yes (exact string) | pending (CLAUDE.md rule) | **pending** |
| libvips (`@img/sharp-libvips-*`) | LGPL-3.0-or-later | npm, via Next.js → `sharp` | unmodified binary, server-side image processing | yes (jq check) | pending | **pending** |
| `certifi` | MPL-2.0 | Python dependency (Mozilla CA bundle) | unmodified data file | yes (exact string) | — (S2 CISO decision) | **pending** |
| `pyphen` | elected MPL-1.1 (of GPL-2.0+/LGPL-2.1+/MPL-1.1) | Python, hard dependency of WeasyPrint | unmodified; no hyphenation dictionaries loaded (English, no `hyphens: auto`) | yes (exact tri-licence string) | ADR 0011 (Accepted, CISO ACCEPT) | **pending** |
| pango | LGPL (2.0-or-later per upstream COPYING — verify on the version in the image) | OS system library loaded by WeasyPrint at run time (cffi) | unmodified shared library, hosted service | **no** (system package) | ADR 0011 Consequences | **pending** |
| HarfBuzz | "Old MIT" (permissive) | OS system library, via pango | unmodified | no | — | not needed (listed for completeness) |

Also loaded by WeasyPrint at run time; their licences are to be confirmed when the production image is fixed (S4): GLib/GObject (LGPL-2.1-or-later), FriBidi (LGPL-2.1-or-later), fontconfig (MIT-style), FreeType (FTL or GPL-2.0, choose FTL). Any of them confirmed as LGPL joins the lawyer review together with pango. **Action (S4, `cp-platform` + `ciso`):** produce the package list of the production image (`dpkg -l` or `apk info`) with licences, and append it here.

## Lawyer question (one review for all rows)
Is it acceptable to use these unmodified LGPL/MPL components, dynamically linked or imported, in a hosted SaaS that does not distribute the software? What notices must we keep (third-party notices file, source offers)? Does the pyphen MPL-1.1 election hold given the tri-licence?
