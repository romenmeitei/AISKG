# Third-party bibliographic data notice

The deterministic manuscript snapshot contains fields derived from
bibliographic databases, including article titles and abstracts. Copyright and
redistribution rights for those fields may belong to authors, publishers, or
database providers.

## Public-release decision

Before leaving the frozen input bundles publicly accessible, the repository
owner and institution should verify the applicable terms for:

1. PubMed-indexed titles and abstracts;
2. Scopus Search/Abstract APIs and institutional subscription access;
3. Web of Science Starter or Expanded APIs; and
4. any publisher full text or supplementary content.

Where unrestricted redistribution is not permitted, keep the software, exact
queries, hashes, schemas, and derived non-infringing outputs public, but place
the affected frozen snapshot in an institutional or controlled-access data
repository. The manuscript data statement should explain the restriction and
how qualified researchers can obtain or reconstruct the source records.

The optional `LIVE_REFRESH` route in Section 1 allows authorized users to
retrieve a current corpus using their own credentials. A live refresh may not
match the historical manuscript snapshot because databases and indexing change.

The frozen manuscript snapshot also preserves published corresponding-author
contact fields, including e-mail addresses, where those fields were present in
the source bibliographic records. These are third-party published metadata—not
software credentials and not the private document-property address removed from
the reviewer workbooks. Institutions requiring additional data minimization
should place the affected frozen bundles in controlled access rather than
silently modifying this version, because the bundle hashes and 285 expected-
result assertions define the v3.1.2 reproducibility record.

This notice is a reproducibility and rights-management warning, not legal
advice.
