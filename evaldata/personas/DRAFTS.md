# Persona drafts for owner review

The 3 built personas plus 21 sketches, revised after the owner's review of 2026-11-13. Once the owner approves, each sketch becomes a YAML file beside this one and this file is deleted. Every name, number and counterparty is synthetic (R-28). Numbers follow the first draft, so the owner's review can still refer to them: 9 is now a different persona and 10 is cut.

**Split.** `dev` personas tune the rules. `test` personas are read only by the evaluation (R-26), with other people, amounts and memo wording. ADR-0059 (Proposed) adds a held-out template change of a bank the vault already reads, such as an older Meezan layout.

| # | id | Who | Target | Evidence and formats | Seeded mismatch | Tests | Split |
|---|---|---|---|---|---|---|---|
| 1 | syn-dev-payoneer | Upwork developer, paid through Payoneer | DE tourist | Payoneer PDF, Meezan PDF | M2 cash deposit; M4 salary slips; M5 no contract | built | dev |
| 2 | syn-designer-direct | Designer paid directly by foreign clients | DE tourist | Meezan PDF, e-PRC | M5 client pays through its director; M1 SWIFT with no PRC; M5 FBR under-declared | built | dev |
| 3 | syn-student-sponsored | Student, father sponsors | DE study | Meezan PDF, Payoneer PDF | M2 sponsor lump sum; M6 freelancing from Germany | built | dev |
| 4 | syn-va-wise | Virtual assistant; clients pay through Wise, which lands in Meezan as PKR | DE tourist | Meezan PDF only | M1/M5 a Wise payout looks like a home remittance, with no e-PRC behind it | a payout that isn't recorded as service-export income | dev |
| 5 | syn-editor-fiverr | Video editor on Fiverr, irregular months | IT tourist | Payoneer PDF, Meezan PDF | M2 one December spike three times the usual | uneven income; Fiverr memos | test |
| 6 | syn-youtuber | YouTube creator, AdSense paid by SWIFT | DE tourist | Meezan PDF, e-PRC | M4 salary slips asked; M5 income shown only by platform | an unusual remitter; every row has a PRC | dev |
| 7 | syn-amazon-seller | Amazon seller, payouts through Payoneer | IT business | Payoneer PDF (USD and EUR), Meezan PDF | M5 gross sales against net payouts | refunds, fees, two currencies | dev |
| 8 | syn-remote-employee | Salaried remote employee of a foreign firm, via Deel | DE tourist | Meezan PDF, e-PRC, contract, payslips | none: a clean control | false alarms | dev |
| 9 | syn-student-france | Student paying their own way from freelance income | FR study | Meezan PDF, Payoneer PDF, e-PRC | M2 tuition savings built in the last 3 months | the French mission's study checklist | dev |
| 11 | syn-spouse-sponsored | No income; husband is a freelancer and sponsors | DE family visit | husband's Payoneer PDF and Meezan PDF | M3 funds in the husband's name | sponsor evidence through the same parsers | dev |
| 12 | syn-student-hbl | Student, parents bank with HBL | DE study | HBL statement (parser to build), blocked-account letter | M3 parents' account; M2 blocked-account deposit | a second bank's layout | dev |
| 13 | syn-translator-joint | Translator with a joint account | FR tourist | Meezan PDF (joint title) | M3 income into a joint account | two-name account titles | test |
| 14 | syn-it-company-owner | Sole owner of a small IT company | DE business | Meezan PDF in the company's name, FBR return | M3 company account; M5 invoices missing | an account titled with a company | dev |
| 15 | syn-dormant-then-busy | Freelancer, quiet for 4 months, then busy just before applying | DE tourist | Payoneer PDF, Meezan PDF | M2 history built up just before applying | gaps in the account history | test |
| 16 | syn-wallet-earner | Freelancer paid into JazzCash/Easypaisa, then moved to the bank | DE tourist | Meezan PDF only (no wallet parser yet) | M1 income shows only as own transfers; the engine asks for the wallet statement | a missing document noticed | dev |
| 17 | syn-agency-subcontractor | Runs a small Upwork agency and pays subcontractors from Payoneer | DE business | Payoneer PDF, Meezan PDF | M5 money out looks like spending | "Payment to" rows on a platform | test |
| 18 | syn-overlapping-downloads | Ordinary freelancer who downloads overlapping statements | DE tourist | 3 overlapping Meezan PDFs, one duplicate file | none | dedupe: each row stored once | dev |
| 19 | syn-locked-statements | Every statement password-protected; one password given wrong | DE tourist | Meezan PDF (locked), Payoneer PDF (locked) | none | password asked; a wrong one stores nothing | dev |
| 20 | syn-tutor-employed | School teacher with online tutoring income | DE tourist | Meezan PDF, Payoneer PDF, salary slips | M4 employer letter covers only the salary | salary and freelance income together | test |
| 21 | syn-artist-commissions | Artist paid by many individuals abroad | FR tourist | Meezan PDF, some e-PRCs | M1 a few payments without a PRC; names in memos | redaction; certificate matching | test |
| 22 | syn-purpose-mismatch | Freelancer who states a client meeting in Germany | DE tourist | Payoneer PDF, Meezan PDF, invitation letter | M6 declared tourism, stated business activity | rule-conflict wording (R-23) | test |
| 23 | syn-clean-file | Freelancer with a complete file: PSEB-registered, on the active taxpayer list, e-PRCs match the statements, contracts in place | DE tourist | Meezan PDF, Payoneer PDF, e-PRCs, contracts, FBR return | none: a second clean control | false alarms on held-out data | test |
| 24 | syn-usdt-p2p | Freelancer who cashes out in USDT, peer to peer | DE tourist | Meezan PDF | M2/M5 many PKR transfers from unrelated individuals | stating it plainly, without coaching (R-23) | test |
| 25 | syn-non-filer | Freelancer who files no tax return | DE tourist | Payoneer PDF, Meezan PDF, e-PRCs | M5 no FBR return, not on the active taxpayer list | the commonest legitimacy gap | dev |

**Coverage.** Germany 18, Italy 2, France 4. Study 4 (3, 9, 12 and a DE one). Test split 9: 5, 13, 15, 17, 20, 21, 22, 23, 24, with M4 (20), M6 (22) and a clean control (23). The dev split keeps M4 in 1 and 6, and M6 in 3.

## For the owner
1. **An HBL statement layout:** paste one row and the header lines from `pdftotext -layout`, values replaced, for persona 12's parser.
2. **ADR-0059:** approve it, or edit it.
