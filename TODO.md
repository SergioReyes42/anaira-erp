# TODO - Fix Gemini Smart Scanner IA

- [x] Refactor `accounting/utils.py` to remove hardcoded API key and load `GEMINI_API_KEY` safely from environment.
- [x] Add robust Gemini initialization and explicit error messages in `accounting/utils.py`.
- [x] Update `accounting/views.py` to remove hardcoded Gemini configuration block and reuse scanner utility flow.
- [x] Validate imports for Gemini-related usage in `accounting/views.py`.
- [x] Provide diagnostic summary and required environment/dependency actions.
