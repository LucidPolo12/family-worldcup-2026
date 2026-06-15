/**
 * Family World Cup — picks receiver (Google Apps Script).
 *
 * Setup: open your "Picks" Google Sheet → Extensions → Apps Script → paste this →
 * Deploy → New deployment → type "Web app" → Execute as: Me → Who has access: Anyone →
 * Deploy. Copy the Web App URL into WorldCupPicks.html (SCRIPT_URL) and tell Claude.
 *
 * It appends one row per submitted pick: timestamp | name | match | predH | predA.
 * The site sends the whole batch each time; the picks Action keeps the latest pick per
 * person+match (and ignores any submitted after that game's kickoff).
 *
 * INSTANT PUBLISH: after saving, this pings GitHub (repository_dispatch) so the
 * "Picks refresh (fast)" workflow runs immediately and the pick is live in ~30-60s,
 * instead of waiting on GitHub's (throttled, every-few-hours) cron.
 *   1. Create a fine-grained Personal Access Token on GitHub scoped to the
 *      LucidPolo12/family-worldcup-2026 repo with "Contents: Read and write".
 *   2. In this Apps Script editor: Project Settings (gear) → Script properties →
 *      add property  GITHUB_TOKEN  = <the token>.   (Never paste the token in code.)
 * If GITHUB_TOKEN is missing the script still saves picks fine; it just falls back
 * to the scheduled refresh.
 */

var GITHUB_REPO = 'LucidPolo12/family-worldcup-2026';
var DISPATCH_EVENT = 'picks-submitted';

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
    // Champion & Podium picks (the "final four"). Stored in the SAME Picks sheet
    // using text codes in the "match" column; the team name goes in predH.
    var f4 = data.final4;
    if (f4) {
      [['CHAMP', f4.champ], ['RUN', f4.run], ['THIRD', f4.third], ['FOURTH', f4.fourth]]
        .forEach(function (pair) {
          if (pair[1]) rows.push([now, name, pair[0], pair[1], '']);
        });
    }
    if (rows.length) {
      sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, 5).setValues(rows);
      triggerPublish_();   // tell GitHub to publish now (best-effort)
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

/**
 * Fire a repository_dispatch so the picks workflow runs right away.
 * Best-effort: any failure here is swallowed so a pick submission never fails
 * just because the publish ping didn't go through (the cron is the safety net).
 */
function triggerPublish_() {
  try {
    var token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
    if (!token) { Logger.log('triggerPublish_: no GITHUB_TOKEN script property set'); return; }
    var resp = UrlFetchApp.fetch('https://api.github.com/repos/' + GITHUB_REPO + '/dispatches', {
      method: 'post',
      contentType: 'application/json',
      headers: {
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
      },
      payload: JSON.stringify({ event_type: DISPATCH_EVENT }),
      muteHttpExceptions: true
    });
    // 204 = success (event accepted). Anything else is logged for debugging.
    Logger.log('triggerPublish_: GitHub responded ' + resp.getResponseCode() + ' ' + resp.getContentText());
  } catch (err) {
    Logger.log('triggerPublish_ error: ' + err);
  }
}

// Lets you open the Web App URL in a browser to confirm it's live.
function doGet() {
  return ContentService.createTextOutput('Family World Cup picks receiver is running.');
}
