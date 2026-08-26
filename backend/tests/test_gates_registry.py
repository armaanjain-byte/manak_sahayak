from app.gates.registry import GateRegistry
from app.gates.status import WorkflowStatus

def test_workflow_with_zero_metrics() -> None:
    registry = GateRegistry()
    # No metrics loaded
    assert registry.is_ready("workflow_1") is False
    assert registry.get_status("workflow_1") == WorkflowStatus.SPEC
    
    # Empty metrics loaded
    registry.update_metrics("workflow_1", {})
    assert registry.is_ready("workflow_1") is False
    # Even if empty dict is present, the logic considers it not having met targets.
    # However, get_status logic: if not current, return SPEC. 
    # Let's ensure empty dict gives SPEC.
    assert registry.get_status("workflow_1") == WorkflowStatus.SPEC

def test_workflow_with_partial_metrics() -> None:
    registry = GateRegistry()
    # Target for A1: canonical_concepts=25, aliases=75, validated_standard_mappings=20, validated_qco_mappings=10
    partial_metrics = {
        "canonical_concepts": 25,
        "aliases": 75,
        "validated_standard_mappings": 20,
        "validated_qco_mappings": 9,  # Below target by 1
    }
    registry.update_metrics("workflow_1", partial_metrics)
    
    assert registry.is_ready("workflow_1") is False
    assert registry.get_status("workflow_1") == WorkflowStatus.PARTIAL
    
    status_obj = registry.get_gate_status("workflow_1")
    assert status_obj.is_passed is False
    assert status_obj.status == WorkflowStatus.PARTIAL

def test_workflow_meeting_all_targets() -> None:
    registry = GateRegistry()
    passing_metrics = {
        "canonical_concepts": 30,  # Exceeds target
        "aliases": 75,  # Meets target
        "validated_standard_mappings": 20,  # Meets target
        "validated_qco_mappings": 10,  # Meets target
    }
    registry.update_metrics("workflow_1", passing_metrics)
    
    assert registry.is_ready("workflow_1") is True
    assert registry.get_status("workflow_1") == WorkflowStatus.BUILD
    
    status_obj = registry.get_gate_status("workflow_1")
    assert status_obj.is_passed is True
    assert status_obj.status == WorkflowStatus.BUILD
