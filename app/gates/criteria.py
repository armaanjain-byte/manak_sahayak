from pydantic import BaseModel

class GateCriteria(BaseModel):
    pass

class A1Criteria(GateCriteria):
    canonical_concepts: int = 25
    aliases: int = 75
    validated_standard_mappings: int = 20
    validated_qco_mappings: int = 10

class A2Criteria(GateCriteria):
    standards_with_validated_scope_mappings: int = 20
    eligible_standard_lab_relationships: int = 25
    labs_minimum: int = 8
    demo_recommended_labs_checked_percent: int = 100
    successful_e2e_lab_queries: int = 10

class A3Criteria(GateCriteria):
    validated_huid_flows: int = 6
    authoritative_evidence_records_mapped: int = 15
    successful_e2e_consumer_queries: int = 10
    verified_official_handoffs: int = 2

A1_TARGETS = A1Criteria()
A2_TARGETS = A2Criteria()
A3_TARGETS = A3Criteria()
