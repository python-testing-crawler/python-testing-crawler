
from python_testing_crawler.rules import Rule, Request, Allow
from python_testing_crawler.constants import ANCHOR, AREA, FORM, LINK
from python_testing_crawler.constants import GET, POST


ALL_ELEMENTS_RULE_SET = [
    Rule('.*', '/.*', GET, Request())
]

HYPERLINKS_ONLY_RULE_SET = [
    Rule(ANCHOR, '/.*', GET, Request()),
    Rule(AREA, '/.*', GET, Request()),
]

REQUEST_ONLY_EXTERNAL_RULE_SET = [
    Rule(ANCHOR, '.*', GET, Request(only=True)),
    Rule(AREA, '.*', GET, Request(only=True)),
]

SUBMIT_GET_FORMS_RULE_SET = [
    Rule(FORM, '.*', GET, Request())
]

SUBMIT_POST_FORMS_RULE_SET = [
    Rule(FORM, '.*', POST, Request())
]

PERMISSIVE_RULE_SET = [
    Rule('.*', '.*', GET, Allow([*range(400, 600)])),
    Rule('.*', '.*', POST, Allow([*range(400, 600)]))
]

PERMISSIVE_ALL_ELEMENTS_RULE_SET = ALL_ELEMENTS_RULE_SET + PERMISSIVE_RULE_SET
PERMISSIVE_HYPERLINKS_ONLY_RULE_SET = HYPERLINKS_ONLY_RULE_SET + PERMISSIVE_RULE_SET


REQUEST_EXTERNAL_RESOURCE_LINKS_RULE_SET = [
    Rule(LINK, '.*', GET, Request()),
]
