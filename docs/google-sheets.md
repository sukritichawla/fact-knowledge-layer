# Google Sheets integration

FactLayer keeps Google Sheets optional so the repository does not contain service-account credentials. The application sends the final validated fact/relationship layer to a configured HTTPS webhook.

## Configuration

Set this in `.env`:

```text
GOOGLE_SHEETS_WEBHOOK_URL=https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec
```

The Streamlit **Export** tab then exposes **Push to Google Sheets**.

## Minimal Apps Script receiver

Create a Google Sheet, open **Extensions → Apps Script**, and use a receiver like this:

```javascript
function doPost(e) {
  const body = JSON.parse(e.postData.contents);
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Facts");
  const rows = body.facts || [];

  sheet.clearContents();
  if (!rows.length) {
    return ContentService.createTextOutput("No facts");
  }

  const headers = Object.keys(rows[0]);
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  sheet.getRange(2, 1, rows.length, headers.length)
       .setValues(rows.map(row => headers.map(h => row[h] ?? "")));

  return ContentService.createTextOutput("OK");
}
```

Deploy it as a web app and use the deployment URL as `GOOGLE_SHEETS_WEBHOOK_URL`.

For a production deployment, protect the endpoint with authentication or a secret token and avoid exposing a write-only endpoint publicly.
