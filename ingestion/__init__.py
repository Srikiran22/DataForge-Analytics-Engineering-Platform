"""Ingestion engine: source-faithful extraction into the raw layer.

Hard rules enforced by this package:
- no business logic here (integrity gating and metadata assignment only);
- raw tables preserve source fidelity plus ingestion metadata columns;
- batches are transactional: a batch is fully loaded or not at all;
- watermarks advance only after successful batch commit;
- re-running a batch is safe (replace-by-batch-id semantics).
"""

__version__ = "0.1.0"
