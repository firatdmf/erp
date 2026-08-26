/* Diacritic-insensitive folding for client-side searches.
 *
 * Mirrors erp/search_utils.py — and therefore Postgres `unaccent()` —
 * so a filter that runs in the browser behaves like one that runs in
 * the database: ş→s, ğ→g, ç→c, ö→o, ü→u, and the whole Turkish I
 * family (I, ı, İ, i) collapses onto "i".
 *
 * Fold both the haystack and the needle before comparing:
 *     if (foldText(row.textContent).indexOf(foldText(query)) < 0) …
 */
(function (global) {
  function foldText(s) {
    // tr-TR lowercasing maps I→ı and İ→i; NFD + mark-stripping takes
    // care of the rest, and the trailing replace folds the dotless ı
    // (which has no decomposition) onto a plain i.
    return (s == null ? '' : String(s))
      .toLocaleLowerCase('tr-TR')
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .replace(/ı/g, 'i');
  }

  global.foldText = foldText;
})(window);
