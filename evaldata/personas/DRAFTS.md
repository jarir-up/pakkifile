# Persona drafts for owner review

22 personas: the 3 built ones and 19 sketches. After the owner approves, each sketch becomes a YAML file beside this one, and this file is deleted. Every name, number and counterparty will be synthetic (R-28).

**Split.** `dev` personas tune the rules. `test` personas are read only by the evaluation (R-26). They use other people, amounts and memo wording, so the scores show how the rules do on memos they weren't tuned on (ADR-0029).

**Formats.** "Not read yet" means a parser has to be built before that persona's evidence can be scored.

| # | id | Who | Target | Evidence and formats | Seeded mismatch | Tests | Split |
|---|---|---|---|---|---|---|---|
| 1 | syn-dev-payoneer | Upwork developer, paid through Payoneer | DE tourist | Payoneer PDF, Meezan PDF | M2 cash deposit; M4 salary slips; M5 no contract | built | dev |
| 2 | syn-designer-direct | Designer paid directly by foreign clients | DE tourist | Meezan PDF, e-PRC | M5 client pays through its director; M1 SWIFT with no PRC; M5 FBR under-declared | built | dev |
| 3 | syn-student-sponsored | Student, father sponsors | DE study | Meezan PDF, Payoneer PDF | M2 sponsor lump sum; M6 freelancing from Germany | built | dev |
| 4 | syn-va-wise | Virtual assistant, clients pay through Wise | DE tourist | Meezan PDF; Wise statement (not read yet) | M5 many small clients, no contracts | another platform's memos | dev |
| 5 | syn-editor-fiverr | Video editor on Fiverr, irregular months | DE tourist | Payoneer PDF, Meezan PDF | M2 one December spike three times the usual | uneven income; Fiverr memos | test |
| 6 | syn-youtuber | YouTube creator, AdSense paid by SWIFT | DE tourist | Meezan PDF, e-PRC | M4 salary slips asked; M5 income shown only by platform | an unusual remitter; every row has a PRC | dev |
| 7 | syn-amazon-seller | Amazon seller, payouts through Payoneer | DE business | Payoneer PDF (USD and EUR), Meezan PDF | M5 gross sales against net payouts | refunds, fees, two currencies | dev |
| 8 | syn-remote-employee | Salaried remote employee of a foreign firm, via Deel | DE tourist | Meezan PDF, e-PRC, contract, payslips | none: the clean control | false alarms: nothing should be flagged | dev |
| 9 | syn-doctor-clinic | Hospital doctor with a private clinic paid in cash | DE conference | Meezan PDF, salary slips | M2 regular cash deposits | local salary alongside cash income | test |
| 10 | syn-pensioner | Retired, pension plus money from a son abroad | DE family visit | Meezan PDF | M3 the son's transfers fund the trip | home remittances from a relative | test |
| 11 | syn-spouse-sponsored | No income; husband sponsors | DE family visit | husband's Meezan PDF | M3 funds in the husband's name | the vault's sponsor person | dev |
| 12 | syn-student-hbl | Student, parents bank with HBL | DE study | HBL statement (not read yet), blocked-account letter | M3 parents' account; M2 blocked-account deposit | a second bank's layout | dev |
| 13 | syn-translator-joint | Translator with a joint account | DE tourist | Meezan PDF (joint title) | M3 income into a joint account | two-name account titles | test |
| 14 | syn-it-company-owner | Sole owner of a small IT company | DE business | Meezan PDF in the company's name, FBR return | M3 company account; M5 invoices missing | account titled with a company | dev |
| 15 | syn-dormant-then-busy | Freelancer, quiet for 4 months, then busy just before applying | DE tourist | Payoneer PDF, Meezan PDF | M2 history built up just before applying | gaps in the account history | test |
| 16 | syn-wallet-earner | Freelancer paid into JazzCash/Easypaisa, moved to the bank | DE tourist | Meezan PDF; wallet statements (not read yet) | M1 income shows only as own transfers | own transfers against income | dev |
| 17 | syn-agency-subcontractor | Runs a small Upwork agency and pays subcontractors from Payoneer | DE business | Payoneer PDF, Meezan PDF | M5 money out looks like spending | "Payment to" rows on a platform | test |
| 18 | syn-overlapping-downloads | Ordinary freelancer who downloads overlapping statements | DE tourist | 3 overlapping Meezan PDFs, one duplicate file | none | dedupe: each row stored once | dev |
| 19 | syn-locked-statements | Every statement password-protected; one password given wrong | DE tourist | Meezan PDF (locked), Payoneer PDF (locked) | none | password asked; a wrong one stores nothing | dev |
| 20 | syn-tutor-employed | School teacher with online tutoring income | DE tourist | Meezan PDF, Payoneer PDF, salary slips | M4 employer letter covers only the salary | salary and freelance income together | dev |
| 21 | syn-artist-commissions | Artist paid by many individuals abroad | DE tourist | Meezan PDF, some e-PRCs | M1 a few payments without a PRC; names in memos | redaction; certificate matching | test |
| 22 | syn-tourist-overstay-risk | Freelancer whose plans and income cover far more than the trip | DE tourist | Payoneer PDF, Meezan PDF | M6 a stated client meeting in Germany on a tourist visa | rule-conflict wording (R-23) | dev |

## For the owner
1. Keep, cut or change rows. A 23rd to 25th persona can fill any gap you see.
2. Personas 4, 12 and 16 need formats that aren't read yet (Wise, HBL, mobile wallets). Keep them and add those parsers, or swap them for personas whose evidence the vault already reads.
3. The test split is personas 5, 9, 10, 13, 15, 17 and 21. Choose others if you'd rather.
