/**
 * Foreign Auto 5280: invoice backend (Google Apps Script).
 *
 * Paste this whole file into Extensions -> Apps Script of the shop's
 * "Foreign Auto Invoices" Google Sheet, then run setup() once and deploy
 * it as a web app (Execute as: Me, Who has access: Anyone).
 *
 * What it does for every invoice sent from foreignauto.shop/invoice/:
 *   - checks the shop PIN,
 *   - gives the next number (FA-0001, FA-0002, ...),
 *   - adds a row to the "Invoices" sheet (all invoices),
 *   - adds a row to the "Cash" or "Card" sheet by how it was paid
 *     (cash + card: a row in each, with that part of the amount),
 *   - saves the PDF to the "Foreign Auto Invoices" folder on Google Drive,
 *   - emails the PDF to the shop (and to the customer when asked).
 */

// ====== Settings: change these two lines, then run setup() ======
var PIN = '1234';                 // PIN the staff type on the invoice page
var SHOP_EMAIL = '';              // where invoices go; empty = this Google account's email
// =================================================================

var SHEET = 'Invoices';
var FOLDER = 'Foreign Auto Invoices';
var PREFIX = 'FA-';
var PAY_SHEETS = { cash: 'Cash', card: 'Card' };
var PAY_HEAD = ['Number', 'Date', 'Customer', 'Phone', 'Vehicle', 'Amount', 'Invoice total', 'Paid how', 'Technician', 'PDF'];
var HEAD = ['Number', 'Date', 'Warranty until', 'Customer', 'Phone', 'Email', 'Address',
  'Vehicle', 'VIN', 'Mileage', 'Plate', 'Work and parts', 'Labor', 'Parts', 'Other',
  'Tax', 'Total', 'Cash', 'Card', 'Payment', 'Technician', 'Notes', 'PDF', 'Saved at', 'ID'];

/** Run once from the editor: saves the settings, creates the sheet and the Drive folder. */
function setup() {
  var p = PropertiesService.getScriptProperties();
  p.setProperty('PIN', String(PIN));
  p.setProperty('SHOP_EMAIL', SHOP_EMAIL || Session.getEffectiveUser().getEmail());
  if (!p.getProperty('NEXT')) p.setProperty('NEXT', '1');
  sheet_();
  paySheet_('cash');
  paySheet_('card');
  folder_();
  Logger.log('Ready. Invoices go to ' + p.getProperty('SHOP_EMAIL') + '. Next number: ' + PREFIX + pad_(p.getProperty('NEXT')));
}

function doGet() {
  return ContentService.createTextOutput('Foreign Auto 5280 invoice service is running.');
}

function doPost(e) {
  try {
    var req = JSON.parse(e.postData.contents);
    var p = PropertiesService.getScriptProperties();
    if (!p.getProperty('PIN')) return out_({ ok: false, error: 'setup() was not run' });
    if (String(req.pin) !== p.getProperty('PIN')) return out_({ ok: false, error: 'pin' });
    if (req.action === 'ping') return out_({ ok: true });
    if (req.action === 'save') return out_(save_(req, p));
    return out_({ ok: false, error: 'unknown action' });
  } catch (err) {
    return out_({ ok: false, error: String(err && err.message || err) });
  }
}

function save_(req, p) {
  var d = req.data || {};
  var sh = sheet_();
  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  var no;
  try {
    // A resend of the same invoice (the network dropped after it was saved) gets the same number.
    if (req.uid) {
      var hit = sh.getRange(1, HEAD.length, Math.max(sh.getLastRow(), 1), 1)
        .createTextFinder(String(req.uid)).matchEntireCell(true).findNext();
      if (hit) return { ok: true, no: sh.getRange(hit.getRow(), 1).getValue(), repeat: true };
    }
    var n = Number(p.getProperty('NEXT') || '1');
    no = PREFIX + pad_(n);
    p.setProperty('NEXT', String(n + 1));
    sh.appendRow(row_(no, d, '', req.uid));
    SpreadsheetApp.flush();
  } finally {
    lock.releaseLock();
  }

  var r = findRow_(sh, no);
  var html = String(req.html || '').replace(/\{\{NO\}\}/g, no);
  var pdf = Utilities.newBlob(html, 'text/html', no + '.html').getAs('application/pdf').setName(no + '.pdf');
  var file = folder_().createFile(pdf);
  if (r) sh.getRange(r, HEAD.indexOf('PDF') + 1).setValue(file.getUrl());
  payRows_(no, d, file.getUrl());

  var total = money_(d.sum && d.sum.total);
  var shopEmail = p.getProperty('SHOP_EMAIL');
  MailApp.sendEmail({
    to: shopEmail,
    subject: 'Invoice ' + no + ' · ' + (d.c_name || '') + ' · ' + (d.v_car || '') + ' · ' + total,
    htmlBody: html,
    attachments: [pdf],
    name: 'Foreign Auto 5280'
  });

  var sentClient = false;
  if (d.emailClient && d.c_email && req.clientHtml) {
    var chtml = String(req.clientHtml).replace(/\{\{NO\}\}/g, no);
    var cpdf = Utilities.newBlob(chtml, 'text/html', no + '.html').getAs('application/pdf').setName('Foreign-Auto-5280-' + no + '.pdf');
    var ru = d.lang === 'ru';
    MailApp.sendEmail({
      to: d.c_email,
      replyTo: shopEmail,
      name: 'Foreign Auto 5280',
      subject: ru ? 'Ваш инвойс ' + no + ' и гарантия · Foreign Auto 5280' : 'Your invoice ' + no + ' and warranty · Foreign Auto 5280',
      htmlBody: chtml,
      attachments: [cpdf]
    });
    sentClient = true;
  }
  return { ok: true, no: no, pdf: file.getUrl(), sentClient: sentClient };
}

function row_(no, d, pdfUrl, uid) {
  var s = d.sum || {};
  var pays = { cash: 'Cash', card: 'Card', cash_card: 'Cash + card' };
  var items = (d.items || []).map(function (i) {
    return '[' + i.type + '] ' + i.desc + ' × ' + (i.qty || 1) + ' = ' + money_(i.amount);
  }).join('\n');
  var date = d.date ? new Date(d.date + 'T12:00:00') : new Date();
  var until = new Date(date); until.setFullYear(until.getFullYear() + 1);
  return [no, date, until, d.c_name, "'" + (d.c_phone || ''), d.c_email, d.c_addr,
    d.v_car, d.v_vin, d.v_miles, d.v_plate, items, s.labor, s.parts, s.other,
    s.tax, s.total, paid_(d).cash, paid_(d).card, pays[d.pay] || d.pay, d.tech, d.notes, pdfUrl, new Date(), uid || ''];
}

function sheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(SHEET);
  if (!sh) {
    sh = ss.insertSheet(SHEET, 0);
    sh.appendRow(HEAD);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, HEAD.length).setFontWeight('bold').setBackground('#E4ECF5');
    sh.getRange('B:C').setNumberFormat('mm/dd/yyyy');
    sh.getRange('M:S').setNumberFormat('$#,##0.00');
    sh.getRange('X:X').setNumberFormat('mm/dd/yyyy hh:mm');
    sh.setColumnWidth(12, 320);
    sh.hideColumns(HEAD.length);
  }
  return sh;
}

/** Cash and card amounts of an invoice. */
function paid_(d) {
  var total = Number(d.sum && d.sum.total || 0);
  if (d.paid) return { cash: Number(d.paid.cash || 0), card: Number(d.paid.card || 0) };
  return d.pay === 'card' ? { cash: 0, card: total } : { cash: total, card: 0 };
}

/** One row on the Cash sheet and/or the Card sheet, with the part paid that way. */
function payRows_(no, d, pdfUrl) {
  var p = paid_(d);
  var how = { cash: 'Cash', card: 'Card', cash_card: 'Cash + card' }[d.pay] || d.pay;
  var date = d.date ? new Date(d.date + 'T12:00:00') : new Date();
  ['cash', 'card'].forEach(function (k) {
    if (p[k] > 0) {
      paySheet_(k).appendRow([no, date, d.c_name, "'" + (d.c_phone || ''), d.v_car, p[k],
        d.sum && d.sum.total, how, d.tech, pdfUrl]);
    }
  });
}

function paySheet_(k) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(PAY_SHEETS[k]);
  if (!sh) {
    sh = ss.insertSheet(PAY_SHEETS[k], k === 'cash' ? 1 : 2);
    sh.appendRow(PAY_HEAD);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, PAY_HEAD.length).setFontWeight('bold').setBackground(k === 'cash' ? '#E5F4E4' : '#E7F1FB');
    sh.getRange('B:B').setNumberFormat('mm/dd/yyyy');
    sh.getRange('F:G').setNumberFormat('$#,##0.00');
  }
  return sh;
}

function folder_() {
  var p = PropertiesService.getScriptProperties();
  var id = p.getProperty('FOLDER_ID');
  if (id) { try { return DriveApp.getFolderById(id); } catch (e) {} }
  var it = DriveApp.getFoldersByName(FOLDER);
  var f = it.hasNext() ? it.next() : DriveApp.createFolder(FOLDER);
  p.setProperty('FOLDER_ID', f.getId());
  return f;
}

function findRow_(sh, no) {
  var hit = sh.getRange(1, 1, sh.getLastRow(), 1).createTextFinder(no).matchEntireCell(true).findNext();
  return hit ? hit.getRow() : 0;
}

function pad_(n) { return ('0000' + n).slice(-Math.max(4, String(n).length)); }
function money_(n) { return '$' + Number(n || 0).toFixed(2); }
function out_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
