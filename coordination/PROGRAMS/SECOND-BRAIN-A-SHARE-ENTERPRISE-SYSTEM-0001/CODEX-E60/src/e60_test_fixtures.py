"""Fixed public test vectors for the E60 synthetic attestation boundary.

These records are signed once outside the repository.  They are deliberately
replayable only for their exact synthetic payloads: no signing private key,
issuer, or runtime bootstrap helper is present in this repository.
"""

BASE_ATTESTATION = {
    "authority_id": "synthetic-authority-1",
    "domain": "SYNTHETIC_EXTERNAL_ATTESTATION_ONLY",
    "key_id": "E60-SYNTHETIC-TEST-ONLY-RSA-RAW-SHA256-V1",
    "lifecycle": "SYNTHETIC_FIXTURE_ACCEPTED",
    "provider_evidence_aggregate_digest": "1941d43bd620de30c43150e57b8e642e0eb596308149af04e1f24767ce4ebd4f",
    "receipt_head": "4444444444444444444444444444444444444444",
    "receipt_parent": "1111111111111111111111111111111111111111",
    "receipt_tree": "5555555555555555555555555555555555555555",
    "reviewer_acceptance_ref": "SYNTHETIC_FIXTURE_NO_EXTERNAL_REVIEW",
    "runtime_identity_digest": "346291bfd67a3421a74b487a019c35d4fb8ecb466228d7b1697c2602cab12048",
    "signature_hex": "5aa55db0d40186658e96fc0989c20d51d1f4e83939e6f375a959a95a678f36c312f11e0a660d02391adad3588081cde62b403901154e9a269f4ba5db163e569",
    "source_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "tested_head": "1111111111111111111111111111111111111111",
    "tested_parent": "2222222222222222222222222222222222222222",
    "tested_tree": "3333333333333333333333333333333333333333",
}

BASE_SOURCE_SPAN = {
    "attestation_id": "6f74cc9b89dd3dc8a9d58d1b1f4379f55aa4a52bf6726f84b60463c7b5e0a97d",
    "decoded_digest": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    "end_byte": 5,
    "signature_hex": "4dbe7d8a4d5467671bf40cfe98f6be2b38250b7fadbd43a12058fa9a3fd6ce948c0524627dcebc8f46a69672a715aa0c061c4d88988cd800af01d0085c981dbb",
    "source_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "start_byte": 0,
}

PENDING_ATTESTATION = {
    **BASE_ATTESTATION,
    "lifecycle": "PENDING_EXTERNAL",
    "reviewer_acceptance_ref": "PENDING_EXTERNAL",
    "signature_hex": "23597e0764533c6b6f6baa3f55e337974eec06667c8e1eedb7b86317617867d948aa4b91ca2001c570aaf1aa6923ed64e44faf249fc3fc52a185f3ae3c95f4c9",
}

RUNTIME_MISMATCH_ATTESTATION = {
    **BASE_ATTESTATION,
    "runtime_identity_digest": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "signature_hex": "2ab79c0992709cca462243ed40861631e0fdd459dda453af4613da53987d343e7f9788b199b518ddd834a0e9dcae8b5b0124cb4cdace468f33ff28efb3fadf24",
}

PROVIDER_MAPPING = {
    "schema_version": "1.0",
    "task_id": "E60-test",
    "provider_run_id": "123",
    "tested_head": "1111111111111111111111111111111111111111",
    "tested_parent": "2222222222222222222222222222222222222222",
    "tested_tree": "3333333333333333333333333333333333333333",
    "jobs": [
        {"python_minor": "3.11", "job_id": "457", "artifact_id": "790", "artifact_content_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"},
        {"python_minor": "3.13", "job_id": "456", "artifact_id": "789", "artifact_content_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"},
    ],
}

TOPOLOGY_MISMATCH_PROVIDER_MAPPING = {
    **PROVIDER_MAPPING,
    "tested_tree": "ffffffffffffffffffffffffffffffffffffffff",
}

TOPOLOGY_MISMATCH_ATTESTATION = {
    **BASE_ATTESTATION,
    "provider_evidence_aggregate_digest": "7e1bd6302736b1a15870846c762a2d15f836cd12c8edc251ccd4d414fe432558",
    "signature_hex": "1184ec1c50a816a2388a9c048a8ea0852f2d4d91db7aa7d06f653a0af06a1ecd40c2ec0e86aeaa3d7181c7062b2c35228c616be9817cfc3715299a67e07b39a8",
}
