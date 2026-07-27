# Retrieval metadata

`topic-coverage.v1.json` is versioned, non-factual retrieval metadata. It
defines only the subject boundaries used to match an already-approved runtime
topic; it is not official administrative data and does not replace the
ACTIVE/OFFICIAL knowledge projection.

The file must not contain administrative facts, source URLs, office details,
deadlines, legal conclusions, or answer content. Runtime code intersects its
governed IDs with the current `KnowledgeRecord` projection, so metadata alone
can never publish a topic.
