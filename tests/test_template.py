"""infra/template.yaml: the Environment parameter (#44).

The default, live, must keep every live resource and name as it is; trial must leave out
everything that claims the custom domain and give the alarm a per-stack name, so a second
stack can deploy beside the live one.
"""

from pathlib import Path

import pytest
import yaml

TEMPLATE = Path(__file__).resolve().parent.parent / "infra" / "template.yaml"
DOMAIN_RESOURCES = ["ApiDomainName", "ApiMapping", "ApiCertificate"]
LIVE_ALARM_NAME = "TariffService-5xx-Errors"


class CfnLoader(yaml.SafeLoader):
    """Reads CloudFormation short-form tags (!Ref, !If, ...) as {"Ref": ...} / {"Fn::If": ...}."""


def _cfn_tag(loader: yaml.SafeLoader, suffix: str, node: yaml.Node) -> dict:
    name = "Ref" if suffix == "Ref" else f"Fn::{suffix}"
    if isinstance(node, yaml.ScalarNode):
        return {name: loader.construct_scalar(node)}
    if isinstance(node, yaml.SequenceNode):
        return {name: loader.construct_sequence(node, deep=True)}
    return {name: loader.construct_mapping(node, deep=True)}


CfnLoader.add_multi_constructor("!", _cfn_tag)


@pytest.fixture(scope="module")
def template() -> dict:
    return yaml.load(TEMPLATE.read_text(), Loader=CfnLoader)


def test_environment_parameter_defaults_to_live(template):
    param = template["Parameters"]["Environment"]
    assert param["Default"] == "live"
    assert param["AllowedValues"] == ["live", "trial"]


def test_is_live_condition_tests_environment(template):
    assert template["Conditions"]["IsLive"] == {"Fn::Equals": [{"Ref": "Environment"}, "live"]}


@pytest.mark.parametrize("name", DOMAIN_RESOURCES)
def test_custom_domain_resources_are_live_only(template, name):
    assert template["Resources"][name]["Condition"] == "IsLive"


def test_custom_domain_output_is_live_only(template):
    assert template["Outputs"]["CustomDomainUrl"]["Condition"] == "IsLive"


def test_alarm_keeps_live_name_and_is_per_stack_otherwise(template):
    assert template["Resources"]["ErrorAlarm"]["Properties"]["AlarmName"] == {
        "Fn::If": ["IsLive", LIVE_ALARM_NAME, {"Fn::Sub": "${AWS::StackName}-5xx-Errors"}]
    }


def test_no_other_resource_is_conditional(template):
    conditional = sorted(n for n, r in template["Resources"].items() if "Condition" in r)
    assert conditional == sorted(DOMAIN_RESOURCES)
