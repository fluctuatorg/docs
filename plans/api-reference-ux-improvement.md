# API Reference UX improvement plan

## Context

The "Create a Payment Request" page at `/api-reference/payment-request/create-a-payment-request` is hard to understand because it shows 4 `oneOf` schema variants as tabs with raw schema names (`Payments_API_Pay`, `Payments_API_PayAndSave`, etc.) instead of human-readable labels.

Mintlify renders `oneOf` schemas as tabbed containers and uses the `title` field of each schema as the tab label. Without titles, it falls back to the raw schema reference name.

## Key finding

**Only `payments.yaml` has this problem.** The other specs already have titles:
- `payouts.yaml` — 25 schemas in oneOf, all have titles (e.g., `title: "API Validation Error"`)
- `accounts.yaml` — 3 schemas in oneOf, all have titles
- `balance-transaction.yaml` — 1 oneOf, no schemas missing titles
- `others.yaml` — 1 oneOf, no schemas missing titles

**`payments.yaml` is missing titles on 32 schemas:**
- 4 request body schemas (the ones causing the confusing tabs on the Create Payment Request page)
- 28 error response schemas (shown in error response tabs)

## Recommended approach: Fix upstream + local enrichment fallback

### Step 1: Fix upstream (recommended, permanent fix)

Since the other specs already have `title` fields and `payments.yaml` is the outlier, the upstream Payments API spec generator should add `title` to these 32 schemas. This is the same pattern already used by Payouts and Accounts.

**Request body schemas — suggested titles:**

| Schema | Suggested `title` |
|--------|-------------------|
| `Payments_API_Pay` | `One-time payment` |
| `Payments_API_PayAndSave` | `Pay and save token` |
| `Payments_API_PayWithToken` | `Pay with saved token` |
| `Payments_API_ReusablePaymentCode` | `Reusable payment code` |

**Error schemas — suggested titles (derive from schema name):**

| Schema | Suggested `title` |
|--------|-------------------|
| `Payments_API_Http400ApiValidationError` | `API validation error` |
| `Payments_API_Http400CaptureAmountExceeded` | `Capture amount exceeded` |
| `Payments_API_Http400CardExpired` | `Card expired` |
| ... (28 total, same pattern: strip prefix, humanize) | |

### Step 2: Local enrichment script (bridge until upstream is fixed)

Create `scripts/enrich_openapi.py` that:
1. Reads each YAML spec from `openapi/`
2. For any schema used in a `oneOf` that lacks a `title`, adds one from a mapping file
3. Writes enriched specs to `openapi/enriched/`
4. `docs.json` points to `openapi/enriched/` instead of `openapi/`

The mapping lives in `scripts/openapi-titles.yaml`:
```yaml
Payments_API_Pay: "One-time payment"
Payments_API_PayAndSave: "Pay and save token"
Payments_API_PayWithToken: "Pay with saved token"
Payments_API_ReusablePaymentCode: "Reusable payment code"
Payments_API_Http400ApiValidationError: "API validation error"
# ... etc
```

Script is re-runnable after every upstream sync. Once upstream adds titles, the script becomes a no-op (it skips schemas that already have titles).

### Step 3: Explicit navigation in docs.json

Replace the current auto-generated sidebar with explicit endpoint listings grouped by API product:

```json
{
  "tab": "API Reference",
  "icon": "square-terminal",
  "groups": [
    { "group": "Overview", "pages": ["api-reference/overview", "api-reference/rate-limits", "api-reference/webhook-behavior"] },
    { "group": "Payment Request", "pages": ["POST /v3/payment_requests", "GET /v3/payment_requests/{payment_request_id}", ...] },
    { "group": "Refund", "pages": ["POST /refunds", ...] },
    ...
  ],
  "openapi": ["openapi/enriched/payments.yaml", "openapi/enriched/payouts.yaml", ...]
}
```

This gives a clean, organized sidebar and lets us control ordering and grouping.

## Files to create/modify

| File | Action |
|------|--------|
| `scripts/openapi-titles.yaml` | Create — title mapping for 32 payments schemas |
| `scripts/enrich_openapi.py` | Create — enrichment script |
| `openapi/enriched/` | Create — output directory for enriched specs |
| `docs.json` | Modify — point to enriched specs, add explicit navigation |

## Verification

1. Run `python3 scripts/enrich_openapi.py`
2. Verify enriched specs have titles: `grep "title:" openapi/enriched/payments.yaml | head`
3. Restart dev server: `npx mintlify dev`
4. Check `/api-reference/payment-request/create-a-payment-request` — tabs should show human-readable labels
5. Check sidebar — endpoints should be grouped logically
