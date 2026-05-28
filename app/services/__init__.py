"""Service layer for business logic.

Services contain all business logic and orchestrate repositories, external APIs, etc.
Never called directly from routes; routes call services.
Same naming pattern as models/, schemas/, and repositories/:
- services.auth → Authentication logic
- services.clients → Client business logic
- services.firms → Firm business logic
- services.summaries → Summarization logic
"""
