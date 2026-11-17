# Website admin — staff privacy and acceptable-use notice (DRAFT v0.1)

> **This is not legal advice; a licensed Ontario lawyer should review before use.** Drafted 2026-11-17 by `legal-compliance-specialist` (not a lawyer) for `coo`. Based on `origin/docs/website-admin-plan`: `docs/plans/website-admin.md` §3–§5 and draft ADRs 0011 (auth) and 0013 (log). **The plan is not approved yet, and nothing is built.** Issue this notice to each admin user before their first sign-in; re-check it whenever the plan or schema changes. Employer: **[LEGAL ENTITY]**. Contact: **[PRIVACY OFFICER NAME], [CONTACT EMAIL]**.

**1. What we record about you.** *Account:* email, display name, role (admin, editor or author), who created it and when, password hash (argon2id), encrypted MFA secret, hashed recovery codes, failed sign-ins, lock-outs, password-change date, and when the account was disabled or deleted. *Sessions:* start, last activity, expiry, MFA and step-up times, shortened IP (IPv4 /24, IPv6 /48) and browser family. *Security log:* each sign-in (successful or failed), MFA event, user/role/key change, content action (draft, review, publish, schedule), log export and error. Each entry holds the time, your account, the action, its target, the result, your shortened IP and your browser family. *Content:* who created each post revision, who published or validated it, and who uploaded each image. If you are a named author, your author profile (name, title, credentials, bio, photo) is **public** on the blog. *Never recorded:* passwords, MFA codes, API keys, keystrokes, screen content, or your location beyond the shortened IP.

**2. Why.** We use these records to secure the site, to show which human published what (every publication is a logged human action), and to investigate incidents. We do not use them to measure your performance. If that ever changes, we will tell you first.

**3. How long.** Security log: 60 days, then deleted automatically. Sessions: removed after they expire, at the daily clean-up. One-time invite and reset links: removed once used or expired. Account: kept while active. On deletion we remove your credentials, sessions, MFA and email, but keep your account ID and display name, so past revisions still show who made them. Post revisions and published author credits last as long as the content.

**4. Who can see it.** Only users with the `admin` role can view or export the security log. Editors and authors cannot. Railway (United States) hosts the database until Canadian hosting is live. Nobody else sees these records unless the law requires it.

**5. Your rights.** You can ask [CONTACT EMAIL] to see your records or correct your account details. We reply within 30 days. Which privacy law covers your records depends on your status. PIPEDA covers employee information only for federal works, undertakings or businesses (PIPEDA s. 4(1)(b)). Ontario has no general private-sector privacy statute for employees. Contractor information may fall under PIPEDA as commercial activity (counsel to confirm). We give these rights to everyone either way. Ontario's written policy on electronic monitoring (Employment Standards Act s. 41.1.1) applies only to employers with 25 or more Ontario employees on 1 January. We are below that, but this notice describes our monitoring anyway.

**6. Rules (acceptable use).**
- Use only your own account. Never share passwords, MFA devices or recovery codes. Store recovery codes offline.
- MFA is required at first sign-in for every role. Sensitive actions ask for a fresh code. Do not try to get around MFA, roles, rate limits or the log.
- The admin area has no access to farmer data (pilot requests, site measurement, web-app data). Do not bring that data in by other means. No farmer names, contacts, farm or field details in posts, drafts, images, alt text, tags or log exports, and none pasted into any AI tool.
- Export the log only to investigate a specific incident. Keep the file in [APPROVED LOCATION] and delete it when the investigation ends (at most 60 days unless counsel advises otherwise).
- Never copy, screenshot or send an API key. Enter keys only on the providers page.
- Follow the content rules: no agronomic rate or number without a named human agronomist's recorded validation, and never present AI as an author, reviewer or approver.
- Sign out on shared devices. Keep your device locked and your browser up to date.

**7. Report incidents the same day** to [PRIVACY OFFICER NAME] / [SECURITY CONTACT]. Examples: a lost or stolen device, a suspected phishing attempt, an MFA prompt you did not trigger, a log entry that is not yours, an exposed key, or farmer data in a post. Do not delete evidence and do not contact affected people yourself. We record every breach and keep the record at least 24 months (PIPEDA breach regulations).

I have read this notice: name ______ date ______

---
Sources (checked 2026-11-17): PIPEDA s. 4(1) https://laws-lois.justice.gc.ca/eng/acts/P-8.6/page-1.html (fetched). Ontario ESA guide, electronic monitoring https://www.ontario.ca/document/your-guide-employment-standards-act-0/written-policy-electronic-monitoring-employees (search summary only). Breach records: privacy-notice.md S5. Facts about our systems: the plan and ADRs above.

**Needs licensed counsel:** (1) which law governs staff and contractor records (PIPEDA s. 4(1)(a) vs (b)) and whether common-law intrusion upon seclusion affects log access; (2) whether this notice must be signed or acknowledged, and how it fits employment and contractor agreements; (3) the retention period for incident exports and the "display name kept after deletion" rule; (4) the ESA s. 41.1.1 head count once the team grows, including whether contractors count.
