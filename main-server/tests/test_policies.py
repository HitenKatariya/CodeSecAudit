"""Unit tests for tenant security policy enforcement."""

from app.api.schemas import SecurityPolicySchema
from app.reviews.risk import decide_verdict, filter_findings_by_policy


def test_default_policy_enforcement():
    # Critical finding defaults to REQUEST_CHANGES
    findings_crit = [{"cwe_id": "CWE-89", "severity": "critical", "title": "SQL Injection"}]
    assert decide_verdict(9.4, findings=findings_crit, policy=None) == "REQUEST_CHANGES"

    # Medium finding without custom policy triggers WARNING
    findings_med = [{"cwe_id": "CWE-328", "severity": "medium", "title": "Weak Hash"}]
    assert decide_verdict(3.5, findings=findings_med, policy=None) == "WARNING"

    # Clean code returns APPROVE
    assert decide_verdict(0.0, findings=[], policy=None) == "APPROVE"


def test_block_secrets_policy():
    policy = SecurityPolicySchema(block_secrets=True)
    findings = [{"cwe_id": "CWE-798", "severity": "low", "title": "Hardcoded AWS secret"}]
    # Even if severity is labeled low, block_secrets forces REQUEST_CHANGES
    assert decide_verdict(2.0, findings=findings, policy=policy) == "REQUEST_CHANGES"

    # When block_secrets is disabled and risk is low
    policy_no_secrets = SecurityPolicySchema(block_secrets=False, min_security_score=50)
    assert decide_verdict(2.0, findings=findings, policy=policy_no_secrets) == "APPROVE"


def test_block_medium_policy():
    # By default, block_medium is False -> returns WARNING
    policy_default = SecurityPolicySchema(block_medium=False, min_security_score=50)
    findings = [{"cwe_id": "CWE-79", "severity": "medium", "title": "XSS in template"}]
    assert decide_verdict(3.0, findings=findings, policy=policy_default) == "WARNING"

    # When block_medium is enabled -> returns REQUEST_CHANGES
    policy_strict = SecurityPolicySchema(block_medium=True, min_security_score=50)
    assert decide_verdict(3.0, findings=findings, policy=policy_strict) == "REQUEST_CHANGES"


def test_dynamic_policy_filters_and_warning_threshold():
    policy = SecurityPolicySchema(
        block_critical=False, block_high=False, block_secrets=False,
        block_medium=False, min_security_score=70, warn_security_score=90,
        confidence_threshold=80, secret_detection=False,
    )
    findings = [
        {"cwe_id": "CWE-798", "severity": "low", "title": "Hardcoded secret", "confidence": 0.95},
        {"cwe_id": "CWE-79", "severity": "medium", "title": "Reflected XSS", "confidence": 0.95},
        {"cwe_id": "CWE-20", "severity": "low", "title": "Low confidence noise", "confidence": 0.4},
    ]
    active = filter_findings_by_policy(findings, policy)
    assert [f["cwe_id"] for f in active] == ["CWE-79"]

    # Score 85 sits in the dynamic warning band 70..90.
    assert decide_verdict(1.5, findings=active, policy=policy) == "WARNING"
    policy.warn_security_score = 70
    assert decide_verdict(1.5, findings=[], policy=policy) == "APPROVE"


def test_min_security_score_threshold():
    # If risk is 2.5, security score is 100 - 25 = 75
    # If min_security_score is 80, 75 < 80 -> REQUEST_CHANGES
    policy_high_threshold = SecurityPolicySchema(
        block_critical=False,
        block_high=False,
        block_secrets=False,
        block_medium=False,
        min_security_score=80,
    )
    assert decide_verdict(2.5, findings=[], policy=policy_high_threshold) == "REQUEST_CHANGES"

    # If min_security_score is 70, 75 >= 70 -> APPROVE
    policy_low_threshold = SecurityPolicySchema(
        block_critical=False,
        block_high=False,
        block_secrets=False,
        block_medium=False,
        min_security_score=70,
    )
    assert decide_verdict(2.5, findings=[], policy=policy_low_threshold) == "APPROVE"
