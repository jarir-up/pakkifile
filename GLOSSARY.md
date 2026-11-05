# PakkiFile

PakkiFile turns what an authority requires, and what an applicant can prove, into one consistent file the authority can judge.

## Requirements

**Authority**:
One institution that judges an applicant's file: a specific embassy or consulate, a bank, a landlord, a government scheme, a tax or registration body. The German Embassy Islamabad and the Consulate General of Germany, Karachi are two authorities.
_Avoid_: Institution, provider, embassy (when the authority is not one), Schengen (that is an authority class)

**Authority class**:
A family of authorities that judge files in a similar way, such as Schengen missions or banks offering car finance.
_Avoid_: Sector, vertical

**Application**:
A specific thing an applicant asks an authority for, such as a German study visa (D) or a car-finance facility. For visas, the category (short-stay C or national long-stay D) is part of the application.
_Avoid_: Case, request, visa (when generic)

**Applicant profile**:
The facts about an applicant that change which requirements apply, such as freelancer, sponsored or student.
_Avoid_: Persona (reserved for synthetic data), user type

**Requirement**:
One thing an authority expects in a file for an application and profile, typed as mandatory, conditional or optional.
_Avoid_: Document (a requirement may be met by several), rule

**Condition**:
The fact that makes a conditional requirement apply.

**Source**:
A published document or page that requirements cite, recorded once with its URL, publication date, retrieval date and source authority.

**Citation**:
A requirement's reference to one source: which source, which section, and whether it supports or conflicts with the requirement.
_Avoid_: Reference, link

**Source authority**:
The rank of a source: official checklist above consulate page above service-provider page above agent above community story.

**Confidence**:
A computed measure of how sure the registry is about a requirement, from source authority, recency and agreement across sources.
_Avoid_: Score, approval odds

**Auto-publish**:
A requirement published without a maintainer's review because it passes the approved rule; every other requirement needs review.
_Avoid_: Approve (reserved for the owner's decisions)

**Registry**:
The public, versioned collection of requirements across authorities.
_Avoid_: Knowledge base, database

**Community story**:
An applicant's report of what an authority asked, approved or refused. It adjusts confidence but never overrides an official source.

## Evidence

**Evidence item**:
One document an applicant holds, such as a bank statement, ePRC, tax return, invoice, contract or letter.
_Avoid_: Upload, attachment

**Vault**:
The applicant's local store of evidence items and the figures computed from them.

**Figure**:
A number computed from evidence by SQL and linked to the rows and pages it came from.
_Avoid_: Amount (when it is computed), stat

**ePRC**:
The electronic Proceeds Realization Certificate a Pakistani bank issues for a foreign remittance. S-PRC is a statement of several.

**Sponsor**:
A person who funds an applicant's application and must evidence the source of those funds.

**Counterparty**:
A client or platform the applicant earns from.
_Avoid_: Employer

## Checks and output

**Mismatch**:
A gap or contradiction that would make a reviewing officer doubt a file. Every mismatch has one kind:
- **M1 Format**: the evidence exists but not in the form expected.
- **M2 Continuity**: weak account history, unexplained lump sums, unclear sponsor funds.
- **M3 Identity**: income or accounts in someone else's name.
- **M4 Classification**: a process that assumes an employer.
- **M5 Legitimacy**: no paper trail tying income to real counterparties.
- **M6 Rule conflict**: the applicant's activity conflicts with the application's legal conditions.
_Avoid_: Error, issue, red flag

**Readiness check**:
A run of the mismatch engine and drafting for one application.
_Avoid_: Score, assessment, eligibility

**Dossier**:
The exported, indexed file ordered for the reviewing officer, with every figure cited.
_Avoid_: Passport, report, package

**Reviewing officer**:
The person at an authority who reads the dossier.
_Avoid_: Reviewer (that is the maintainer's queue role), user
