# Domain schema — Grocery supply and recall notices

## Entity

`GroceryNotice` represents a public notice about a grocery product's availability,
distribution, or safety.

| Field | Type | Required | Description |
|---|---|---:|---|
| `productName` | string | yes | Product or food item affected |
| `noticeSource` | string | yes | Manufacturer, retailer, or bulletin source |
| `submitterEmail` | email string | yes | Email address of the submitter |
| `noticeDescription` | string | yes | Details about the recall or supply event; must exceed 25 characters |
| `noticeCategory` | enum | yes | Notice classification |
| `terms` | boolean | yes | Submitter accepted the terms |
| `submissionDate` | ISO-8601 string | generated | Time of successful submission |

## Category values

- `recall` — Product recall
- `shortage` — Supply shortage
- `contamination` — Contamination warning
- `distribution` — Distribution update
