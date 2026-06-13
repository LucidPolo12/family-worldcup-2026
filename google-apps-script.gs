/**
 * Family World Cup — picks receiver (Google Apps Script).
 *
 * Setup: open your "Picks" Google Sheet → Extensions → Apps Script → paste this →
 * Deploy → New deployment → type "Web app" → Execute as: Me → Who has access: Anyone →
 * Deploy. Copy the Web App URL into WorldCupPicks.html (SCRIPT_URL) and tell Claude.
 *
 * It appends one row per submitted pick: timestamp | name | match | predH | predA.
 * The site sends the whole batch each time; the daily Action keeps the latest pick per
 * person+match (and ignores any submitted after that game's kickoff).
 */
function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var data = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName('Picks') || ss.insertSheet('Picks');
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(['timestamp', 'name', 'match', 'predH', 'predA']);
    }
    var name = (data.name || '').toString().trim();
    var picks = data.picks || [];
    var now = new Date();
    var rows = picks.map(function (p) {
      return [now, name, p.n, p.ph, p.pa];
    });
    if (rows.length) {
      sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, 5).setValues(rows);
    }
    return ContentService
      .createTextOutput(JSON.stringify({ ok: true, saved: rows.length }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: String(err) }))
      .setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}

// Lets you open the Web App URL in a browser to confirm it's live.
function doGet() {
  return ContentService.createTextOutput('Family World Cup picks receiver is running.');
}
