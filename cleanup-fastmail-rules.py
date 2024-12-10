# Fastmail rules are encoded as JSON in a format like
#
# ```json
# [
#   {
#     "search": "from:franthony-dormitionchurch.org@shared1.ccsend.com",
#     "name": "",
#     "combinator": "all",
#     "conditions": null,
#     "markRead": false,
#     "markFlagged": false,
#     "showNotification": false,
#     "redirectTo": null,
#     "fileIn": "Inbox/Sender: Medium",
#     "skipInbox": true,
#     "snoozeUntil": null,
#     "discard": false,
#     "markSpam": false,
#     "stop": true,
#     "updated": "2024-10-05T11:56:55Z",
#     "previousFileInName": null,
#     "created": "2024-10-05T11:56:55Z"
#   },
# ]
# ```
#
# we want to find all the rules that have the same "fileIn"
# and which have a "search"
# that looks like "from:$EMAIL_ADDRESS" for some email address (or multiple)
# and then collapse them into a single rule that looks like
# "from:$EMAIL_ADDRESS1 OR from:$EMAIL_ADDRESS2"
# All other rules should be passed through.

import json
import sys
import re
from typing import List, Dict, Any

def is_from_rule(rule: Dict[str, Any]) -> bool:
    """Check if a rule contains only 'from:' email searches."""
    search = rule.get('search')
    if not search:  # Handle None or empty string
        return False
    # Split by OR and check each term is a from: clause
    terms = [t.strip() for t in search.split(' OR ')]
    return all(re.match(r'^from:[^\s]+$', term) for term in terms)

def extract_emails(search: str) -> List[str]:
    """Extract all email addresses from a search string that may contain multiple 'from:' clauses."""
    terms = [t.strip() for t in search.split(' OR ')]
    return [term[5:] for term in terms]  # Remove 'from:' prefix from each term

def combine_rules_for_folder(rules: List[Dict[str, Any]], target_folder: str) -> List[Dict[str, Any]]:
    """Combine rules that have matching fileIn values and are 'from:' rules."""
    # Separate rules into those we want to combine and others
    to_combine = []
    other_rules = []
    
    for rule in rules:
        if (rule.get('fileIn') == target_folder and 
            is_from_rule(rule)):
            to_combine.append(rule)
        else:
            other_rules.append(rule)
    
    if len(to_combine) <= 1:
        return rules
    
    # Create combined rule from the first matching rule
    template_rule = to_combine[0].copy()
    # Extract all emails from all rules
    all_emails = []
    for rule in to_combine:
        all_emails.extend(extract_emails(rule['search']))
    # Remove duplicates while preserving order
    unique_emails = list(dict.fromkeys(all_emails))
    template_rule['search'] = ' OR '.join(f'from:{email}' for email in unique_emails)
    
    # Return combined rule plus all other rules
    return [template_rule] + other_rules

def combine_all_folders(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find all folders with multiple matching rules and combine them."""
    # Find all folders that have from: rules
    folders = set()
    for rule in rules:
        if rule.get('fileIn') and is_from_rule(rule):
            folders.add(rule['fileIn'])
    
    # Process each folder in sequence
    result = rules
    for folder in sorted(folders):
        result = combine_rules_for_folder(result, folder)
    
    return result

def main():
    # Read JSON from stdin
    try:
        rules = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("Error: Invalid JSON input", file=sys.stderr)
        sys.exit(1)
    
    # Process and combine rules for all folders
    new_rules = combine_all_folders(rules)
    
    # Output the result
    json.dump(new_rules, sys.stdout, indent=2)

if __name__ == '__main__':
    main()
