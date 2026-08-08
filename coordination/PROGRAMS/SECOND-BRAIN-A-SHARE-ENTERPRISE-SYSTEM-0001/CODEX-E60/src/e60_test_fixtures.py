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
    "runtime_identity_digest": "61cf55a391c146a54b96cc8f22b3642a47a2dbde4bd720720f56cb5f35368104",
    "signature_hex": "548f3cbdab6b304226d57b8a15484ae5ef9369c28c2af663fe1551e3e87f5c89c65d25aedf70d1daaa49dbffe1b1fe1c3771325b07b8142b7991faae52308259",
    "source_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "tested_head": "1111111111111111111111111111111111111111",
    "tested_parent": "2222222222222222222222222222222222222222",
    "tested_tree": "3333333333333333333333333333333333333333",
}

BASE_SOURCE_SPAN = {
    "attestation_id": "87ddd6a813af10498ad4b1d13ee1548a373dffeca4e26175c56fa360665de461",
    "decoded_digest": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    "end_byte": 5,
    "signature_hex": "4d54d2e9798271ecd0662500b371bb53104e2da2ca5f1f7bc660efa4bea0a45c6499c0636c70159cd663e1aba0989a0eaab93461e0ec14a1fd767c0ee6328e33",
    "source_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "start_byte": 0,
}

PENDING_ATTESTATION = {
    **BASE_ATTESTATION,
    "lifecycle": "PENDING_EXTERNAL",
    "reviewer_acceptance_ref": "PENDING_EXTERNAL",
    "signature_hex": "27ef7ebe30e2b63d047b85f1e2ec8bc704691ff44075842ba34193aaa6b22e0c51c51354e9040a52a7ba9bd624258e23ce1032a3899587d1cdbc97d72c21b19e",
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
    "signature_hex": "518575aec8824dd00b20344b0090619eaeb27004f2fa0238a0dca690b87b5caba522cba2c1e15c5589bdd0c4119d61fb86ceaa2d9c963ba04003a43b322b3e31",
}
