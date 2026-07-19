# Decisions

1. Use environment variables first, then a machine-local JSON file, instead of keeping any hardcoded secret fallback in source.
2. Keep credential lookup compatible with current local operator patterns by preserving WorkBuddy credential-file reading where applicable.
3. Make missing credentials fail before network use, so tests can validate safe behavior without contacting live services.
4. Add safe placeholder templates to support a future clean Git baseline without introducing real values.
5. Keep the implementation scoped to the four approved source files plus templates, tests, and this result bundle.
