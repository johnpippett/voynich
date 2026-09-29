# Historical keys and script comparisons

Date: 2026-09-29.
This study asks whether other manuscripts supply fixed sign values for Voynich text.
A key for another manuscript does not, by itself, give a Voynich key.
The relation between the two sets of signs also needs evidence.

## Fontana: a historical cipher alphabet

The [BSB record for Cod.icon. 242](https://api.digitale-sammlungen.de/iiif/presentation/v2/bsb00013084/manifest) dates *Bellicorum instrumentorum* to 1420–1430.
Its [folio 1r](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00013084_00006/full/full/0/default.jpg) shows an ordered row of cipher signs.
[Folio 1v](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00013084_00007/full/full/0/default.jpg) has Latin-script and cipher paragraphs.
Their position on one page does not establish that both paragraphs contain the same text.

The [BnF record for NAL 635](https://gallica.bnf.fr/iiif/ark:/12148/btv1b10023795x/manifest.json) dates *Secretum de thesauro* to 1420–1440.
It describes signs made from circles and straight lines, with exceptions.
It also places the abbreviation bar below words.
These details give a historical script example. They do not assign values to Voynich signs.

The primary image check did not establish every Latin assignment in the alphabet row.
No Voynich decoding or Fontana transcription was performed.

The [1984 edition record](https://books.google.com/books/about/Le_macchine_cifrate_di_Giovanni_Fontana.html?id=no1IAQAAIAAJ) states that the book gives decryptions of both manuscripts.
The available record does not show the key pages. The first request to a separate source website failed.
The source check covers folios 1r–2v in each manuscript and the listed records.
It does not show that Fontana's key is unavailable elsewhere.

An [archived copy of Philip Neal's page](https://web.archive.org/web/20180215201648/http://philipneal.net:80/voynichsources/fontana_cipher_manuscripts) was readable during a later check.
It calls Fontana's cipher a simple substitution cipher but gives no sign values or complete decoding rules.
Further requests to the 1984 edition returned metadata or access errors, without readable book pages.
Pages 35–38 remain a search lead, not a confirmed key location.

## Meister: complete printed tables and an unresolved date

[Meister's 1902 book, pages 30–31](https://books.google.com/books?id=tI_k5mqTS2IC&pg=PA30), gives another source to examine.
The first search excerpt contained the date 14 March 1448 but did not preserve cipher signs reliably.
That page image request returned a placeholder. The first check therefore covered no complete key image.

A later check downloaded the [complete scan from ULB Münster](https://sammlungen.ulb.uni-muenster.de/download/pdf/3075984.pdf).
The [library record](https://sammlungen.ulb.uni-muenster.de/id/3075984) identifies the 1902 edition.
The primary agent examined printed pages 25–31, which are PDF pages 38–44 in this download.
The PDF page numbers differ from the canvas positions in the library's image manifest.

| Printed page | Printed key heading | Evidence limit |
| --- | --- | --- |
| [30](https://sammlungen.ulb.uni-muenster.de/download/webcache/1000/3076036) | Key 1; Duchess of Milan and King Ferdinand; 14 March 1448 | The complete printed table is readable. Its date needs a separate check. |
| [31](https://sammlungen.ulb.uni-muenster.de/download/webcache/1000/3076037) | Key 2; Count Hieronimo; 10 January 1483 | This is a different key. Its rules must not be assigned to key 1. |

Page 30 contains letter assignments, null signs, two-character plaintext entries, and a nomenclator.
The letter table gives more than one cipher form for some plaintext letters.
A nomenclator assigns codes to complete names or terms.
The page also contains a row of short words and abbreviations without a complete set of separate code assignments.
Footnote 2 says that the writer included this usual row but did not require its customary replacements in this key.
This row does not authorize invented assignments.

Page 31 gives a rule that makes text between two specified signs null.
That rule belongs to the 1483 key. Meister's discussion on page 28 also assigns it to that example.
The earlier search excerpts must not be combined into one key.

Page 30 cites the historical archive reference: “Mailand, Staatsarchiv. Pot. Est. Cifre Fasc. 2 Nr. 5.”
The current archive reference and original document were not checked.
Meister repeats the 1448 date in the discussion on pages 26–28.
Thus, the date is not only an error in automated text recognition.

A bounded archive search did not supply the original sheet or a current catalogue record.
The checked archive routes returned access errors. These failures do not show that the sources are absent.

However, the nomenclator includes “Hippolita duchesse de Calabria.”
If this means Ippolita Maria Sforza, the title is later than the printed 1448 date.
[Treccani's biography](https://www.treccani.it/enciclopedia/ippolita-sforza_%28Dizionario-Biografico%29/) dates her birth to 1445 and her marriage to Alfonso II to 1465.
[Alfonso's biography](https://www.treccani.it/enciclopedia/alfonso-ii-d-aragona-re-di-napoli_%28Dizionario-Biografico%29/) dates his Calabria title and Ferrante's kingship to 1458.
If the heading's King Ferdinand means Ferrante, that title is also later than 1448.

These are conditional historical inferences, not a corrected date.
The check does not establish the persons' identities, an annotation history, or a copying history.
Keep 1448 as the printed date, with these limits.
Do not use this table as evidence for cipher practice in 1448 until a source establishes its date.

This check supplies a complete printed historical key table, not a Voynich key.
The check did not assign cipher signs to Voynich forms or fit a manuscript model.
A fixed transcription and separate evidence of a relation to Voynich signs are still necessary before any decoding test.

## Pahlavi: partial relations and reading choices

[Herrmann's version 2 paper](https://arxiv.org/pdf/1709.01634v2) proposes relations between Voynich forms and Pahlavi letters.
Section 2 uses rotations, reflection, and added marks. It also uses proposed separator functions and phonetic readings.
Section 3 adds comparisons with known names and vocabulary.
Thus, a single geometric operation does not determine the proposed values.

Tables 1 and 2, pages 4 and 6, retain alternatives and unresolved combinations.
Appendix B, page 15, gives selected glosses for a passage from f1r.
Its caption states that the transliteration has inconsistencies and treats initial `o` as absent in some readings and meaningful in another.
Appendix A, page 13, marks two zodiac readings as questionable after initial letters are ignored.

These source limits do not reject Pahlavi or the tables' partial constraints.
They leave reading choices unresolved before a new passage can be tested.
The reviewed examples do not supply a reproducible continuous translation.
No added sign values, word search, or manuscript decoder followed this review.

The review covers twelve PDF pages: 1–8, 10, and 13–15.
It includes image checks of both mapping tables and the text example.

## Verification and limits

The [source record](historical-key-comparisons-2026-09-29.sources.json) gives the source versions, URLs, byte counts, hashes, and review limits.
Source bodies and local working records remain outside the public repository.
Separate AI tasks checked the sources. These checks are not external scholarly validation.

The project suite passed all 85 tests. Those tests do not assess the historical readings.
The study supplies no Voynich key or translation.

The later access check keeps the first failed requests and adds hashes for the complete scan and new source captures.
It records each printed key with its own date and rules, and gives the conditional date problem.
The source record gives the reviewed pages; the unexamined book pages supply no claims here.

Before a decoding test, obtain the complete source key.
Fix its relation to Voynich forms from other evidence.
For a method with several possible readings, specify the permitted choices.
State how evidence can select among those choices.
Do not fill a source gap with values chosen to produce a desired word.
