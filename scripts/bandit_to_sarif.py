import json
import sys
from datetime import datetime

with open('bandit.json') as f:
    bandit_data = json.load(f)

sarif = {
    "version": "2.1.0",
    "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
    "runs": [{
        "tool": {
            "driver": {
                "name": "Bandit",
                "informationUri": "https://bandit.readthedocs.io/",
                "rules": []
            }
        },
        "results": []
    }]
}

rules_index = {}

for issue in bandit_data.get("results", []):
    rule_id = issue["test_id"]
    if rule_id not in rules_index:
        rules_index[rule_id] = len(sarif["runs"][0]["tool"]["driver"]["rules"])
        sarif["runs"][0]["tool"]["driver"]["rules"].append({
            "id": rule_id,
            "name": issue["test_name"],
            "shortDescription": {
                "text": issue["issue_text"]
            },
            "fullDescription": {
                "text": issue["issue_text"]
            },
            "helpUri": "https://bandit.readthedocs.io/en/latest/plugins/index.html"
        })

    sarif["runs"][0]["results"].append({
        "ruleId": rule_id,
        "ruleIndex": rules_index[rule_id],
        "message": {
            "text": issue["issue_text"]
        },
        "locations": [{
            "physicalLocation": {
                "artifactLocation": {
                    "uri": issue["filename"]
                },
                "region": {
                    "startLine": issue["line_number"]
                }
            }
        }]
    })

with open('bandit-results.sarif', 'w') as f:
    json.dump(sarif, f, indent=2)

print("✅ Bandit SARIF gerado com sucesso.")