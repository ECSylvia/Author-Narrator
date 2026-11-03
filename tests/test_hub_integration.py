from hub_integration.contracts import HubPrincipal, HubProjectContext
from hub_integration.security import check_project_context, mock_identity_is_disabled_in_production

def test_authorized_project_context():
    p = HubPrincipal(subject="user-1", workspace_id="w1")
    c = HubProjectContext(hub_project_id="p1", workspace_id="w1")
    assert check_project_context(p, c, entitled=True).allowed

def test_cross_workspace_rejected():
    p = HubPrincipal(subject="user-1", workspace_id="w1")
    c = HubProjectContext(hub_project_id="p1", workspace_id="w2")
    assert not check_project_context(p, c, entitled=True).allowed

def test_missing_entitlement_rejected():
    p = HubPrincipal(subject="user-1", workspace_id="w1")
    c = HubProjectContext(hub_project_id="p1", workspace_id="w1")
    assert not check_project_context(p, c, entitled=False).allowed

def test_wrong_product_rejected():
    p = HubPrincipal(subject="user-1", workspace_id="w1")
    c = HubProjectContext(hub_project_id="p1", workspace_id="w1", product_slug="harbor")
    assert not check_project_context(p, c, entitled=True).allowed

def test_mock_auth_cannot_be_used_in_production():
    assert not mock_identity_is_disabled_in_production("production", "mock")
    assert mock_identity_is_disabled_in_production("development", "mock")
