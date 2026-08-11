# Batch 002 — Mixed Document (Knowledge + Secrets)
## Source: synthetic test for redaction + atomization pipeline

### Public Knowledge

Knowledge atomization is the process of decomposing source material into
minimum complete semantic units. The pipeline must satisfy losslessness,
determinism, and traceability invariants.

### Configuration Example (contains secrets that MUST be redacted)

The deployment configuration looks like this:

```yaml
api_key: "sk-proj-1234567890abcdef1234567890abcdef"
database_url: "mysql://admin:realPass123@db.internal:3306/knowledge_store"
github_token: "ghp_9876543210abcdef9876543210abcdef9876"
```

However, the API endpoint structure is public knowledge:
- Base URL: https://api.example.com/v2
- Rate limit: 1000 requests/minute per API key
- Endpoints: /atoms, /relations, /packets

### Safe Configuration Values

These are safe example values that should NOT be redacted:
- `api_key = 'your_key_here'` (placeholder)
- `token = 'example_token_placeholder'` (example)
- The function accepts an api_key parameter of type string

### Redaction Protocol

When a document contains both knowledge and secret values:
1. Identify all secret patterns matching the SECRET_PATTERNS catalog
2. Replace each secret with [REDACTED:secret_type] marker
3. Preserve all surrounding knowledge content intact
4. Record each redaction in a parse_report with location, type, and hash
5. Run verify_zero_secrets() after redaction to confirm zero remaining secrets
6. Reject the entire document ONLY if all content is secrets (no knowledge to preserve)

Exception: documents that contain ONLY secret values with no accompanying
knowledge are rejected entirely rather than producing empty output.
