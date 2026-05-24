"""
SaaS Technical Support Knowledge Base
--------------------------------------
This module contains structured troubleshooting data for the most common
SaaS technical support issues. The agent uses this as its "tool" to look
up resolution steps instead of hallucinating answers.
"""

KNOWLEDGE_BASE = {
    "authentication": {
        "category": "Authentication & Login Issues",
        "common_issues": [
            {
                "issue": "User cannot log in - password rejected",
                "severity": "high",
                "troubleshooting_steps": [
                    "Verify the user is entering the correct email address associated with their account.",
                    "Check if Caps Lock is enabled on the user's keyboard.",
                    "Attempt a password reset via the 'Forgot Password' link.",
                    "Confirm the password reset email is not landing in spam/junk folders.",
                    "Check if the account has been locked due to too many failed attempts (typically 5+).",
                    "Verify the account has not been deactivated by an admin."
                ],
                "resolution_methods": [
                    "Reset password through admin console if user cannot self-serve.",
                    "Unlock the account in the admin panel under User Management > Account Status.",
                    "If SSO is enabled, verify the IdP configuration and SAML assertion mapping.",
                    "Clear browser cookies and cache, then retry login."
                ],
                "escalation_trigger": "If the issue persists after password reset and account unlock, escalate to Tier 2 for IdP/SSO investigation."
            },
            {
                "issue": "SSO/SAML authentication failure",
                "severity": "critical",
                "troubleshooting_steps": [
                    "Confirm the SSO configuration is active in Admin Settings > Authentication.",
                    "Verify the IdP metadata URL is reachable and the certificate has not expired.",
                    "Check the SAML assertion for correct NameID format (usually email).",
                    "Review IdP logs for rejected authentication attempts.",
                    "Confirm the user exists in both the IdP and the SaaS application."
                ],
                "resolution_methods": [
                    "Re-upload the IdP metadata XML if the certificate has rotated.",
                    "Update the ACS (Assertion Consumer Service) URL if the application domain changed.",
                    "Manually provision the user in the SaaS app if JIT provisioning is disabled.",
                    "Test with an incognito/private browser window to rule out cached credentials."
                ],
                "escalation_trigger": "If SAML assertions look correct but authentication still fails, escalate to Engineering with full SAML trace logs."
            },
            {
                "issue": "Two-factor authentication (2FA) not working",
                "severity": "high",
                "troubleshooting_steps": [
                    "Verify the user's authenticator app time is synced (clock drift causes code rejection).",
                    "Confirm the user is scanning the correct QR code for this specific application.",
                    "Check if backup/recovery codes were issued during 2FA setup.",
                    "Verify SMS-based 2FA: confirm the phone number on file and carrier delivery status."
                ],
                "resolution_methods": [
                    "Admin can disable 2FA for the user's account, allowing them to re-enroll.",
                    "Issue a temporary bypass code with a 15-minute expiration.",
                    "If using an authenticator app, have the user delete and re-add the account entry.",
                    "Switch the user from SMS to app-based 2FA if carrier delivery is unreliable."
                ],
                "escalation_trigger": "If 2FA reset does not resolve and user is locked out of recovery codes, escalate to Security team."
            }
        ]
    },
    "integration": {
        "category": "Integration & API Issues",
        "common_issues": [
            {
                "issue": "API returning 401 Unauthorized errors",
                "severity": "high",
                "troubleshooting_steps": [
                    "Verify the API key or OAuth token has not expired.",
                    "Confirm the API key has the required scopes/permissions for the endpoint being called.",
                    "Check if the API key was regenerated recently (old keys are immediately invalidated).",
                    "Verify the Authorization header format: 'Bearer <token>' (not 'Token <token>').",
                    "Check if IP allowlisting is enabled and the client IP is on the list."
                ],
                "resolution_methods": [
                    "Generate a new API key from Settings > Developer > API Keys.",
                    "Update OAuth token refresh logic to handle token expiration gracefully.",
                    "Add the client's IP address to the API allowlist in Security Settings.",
                    "Review API rate limit headers to ensure the key has not been throttled."
                ],
                "escalation_trigger": "If valid credentials are returning 401, escalate to Engineering with request/response headers and timestamps."
            },
            {
                "issue": "Webhook events not being received",
                "severity": "medium",
                "troubleshooting_steps": [
                    "Verify the webhook endpoint URL is correct and publicly accessible (not localhost).",
                    "Check that the endpoint returns a 200 status code within 5 seconds.",
                    "Review the webhook delivery log in Settings > Integrations > Webhooks.",
                    "Confirm the webhook subscription includes the correct event types.",
                    "Test the endpoint with a manual curl request to verify it accepts POST requests."
                ],
                "resolution_methods": [
                    "Fix the endpoint to return 200 OK within the timeout window.",
                    "Re-register the webhook if the signing secret has been rotated.",
                    "Implement retry logic on your server for transient failures.",
                    "Check firewall rules to ensure the SaaS platform's IP range is not blocked."
                ],
                "escalation_trigger": "If webhook delivery logs show successful sends but the customer's server never receives them, escalate to Networking/Infrastructure."
            },
            {
                "issue": "Third-party integration sync failures",
                "severity": "medium",
                "troubleshooting_steps": [
                    "Check the integration status page for the third-party service (e.g., Salesforce, Slack).",
                    "Verify OAuth tokens for the integration have not expired or been revoked.",
                    "Review sync logs for specific error messages or failed record IDs.",
                    "Confirm field mapping between systems has not changed due to schema updates.",
                    "Check if the third-party API has rate limits that are being exceeded."
                ],
                "resolution_methods": [
                    "Re-authenticate the integration by disconnecting and reconnecting in Settings.",
                    "Update field mappings to reflect any schema changes in either system.",
                    "Implement incremental sync instead of full sync to reduce API call volume.",
                    "Contact the third-party vendor if their API status page shows degraded performance."
                ],
                "escalation_trigger": "If re-authentication and field mapping updates do not resolve, escalate with sync error logs and timestamps."
            }
        ]
    },
    "performance": {
        "category": "Performance & Reliability Issues",
        "common_issues": [
            {
                "issue": "Application loading slowly or timing out",
                "severity": "high",
                "troubleshooting_steps": [
                    "Check the application status page for any ongoing incidents or maintenance.",
                    "Have the user test from a different browser or device to rule out client-side issues.",
                    "Run a speed test on the user's internet connection.",
                    "Check if the issue is isolated to a specific page/feature or the entire application.",
                    "Review browser developer tools (Network tab) for slow or failed requests.",
                    "Verify if the user's organization has an unusually large dataset that could affect load times."
                ],
                "resolution_methods": [
                    "Clear browser cache and cookies for the application domain.",
                    "Disable browser extensions that may interfere (especially ad blockers and VPN extensions).",
                    "If dataset-related, recommend archiving old records or enabling pagination.",
                    "Switch to a supported browser (Chrome, Firefox, Edge) if using an unsupported one.",
                    "If server-side, check application logs for slow database queries or resource contention."
                ],
                "escalation_trigger": "If performance issues affect multiple users across different networks, escalate to Infrastructure with HAR file captures."
            },
            {
                "issue": "Data export failing or incomplete",
                "severity": "medium",
                "troubleshooting_steps": [
                    "Check if the export exceeds the maximum row limit for the file format (CSV: typically 1M rows, Excel: 65K-1M rows).",
                    "Verify the user has export permissions in their role settings.",
                    "Check available disk space in the user's download location.",
                    "Review if filters applied to the export are excluding expected data.",
                    "Test with a smaller date range or subset of data to isolate the issue."
                ],
                "resolution_methods": [
                    "Break the export into smaller chunks using date range filters.",
                    "Use the API bulk export endpoint for datasets exceeding UI export limits.",
                    "Grant export permissions to the user's role in Admin > Roles & Permissions.",
                    "Switch export format from Excel to CSV for larger datasets.",
                    "Schedule the export during off-peak hours if it is resource-intensive."
                ],
                "escalation_trigger": "If exports fail consistently regardless of size, escalate to Engineering with export job IDs."
            }
        ]
    },
    "billing": {
        "category": "Billing & Account Issues",
        "common_issues": [
            {
                "issue": "Unexpected charges or billing discrepancies",
                "severity": "medium",
                "troubleshooting_steps": [
                    "Review the invoice line items in Billing > Invoice History.",
                    "Check if additional users were added during the billing cycle (per-seat pricing).",
                    "Verify if the account was upgraded to a higher tier mid-cycle (prorated charges).",
                    "Confirm whether usage-based features (API calls, storage, emails) exceeded the plan limits.",
                    "Check for any add-on features that were activated."
                ],
                "resolution_methods": [
                    "Provide a detailed invoice breakdown showing each charge with its source.",
                    "If an error is confirmed, issue a credit memo for the next billing cycle.",
                    "Adjust the subscription tier if the customer was on an incorrect plan.",
                    "Set up usage alerts to notify the customer before overage charges occur.",
                    "Review and remove any unused add-on features to reduce future charges."
                ],
                "escalation_trigger": "If the billing system shows charges that do not match plan configuration, escalate to Finance with invoice ID and account details."
            }
        ]
    },
    "permissions": {
        "category": "User Permissions & Access Control",
        "common_issues": [
            {
                "issue": "User cannot access a feature or page they should have access to",
                "severity": "medium",
                "troubleshooting_steps": [
                    "Check the user's role assignment in Admin > Users > [User] > Role.",
                    "Review the role's permission set to confirm the feature is included.",
                    "Verify if the feature is available on the customer's subscription tier.",
                    "Check if the feature has been toggled off at the organization level.",
                    "Confirm the user is not in a restricted group or organizational unit."
                ],
                "resolution_methods": [
                    "Update the user's role to include the required permissions.",
                    "Create a custom role if existing roles do not match the needed permission set.",
                    "Enable the feature at the organization level in Admin > Feature Management.",
                    "If tier-restricted, inform the customer about the upgrade path to access the feature.",
                    "Clear the user's session (force logout/login) to refresh their permission token."
                ],
                "escalation_trigger": "If permissions appear correct but access is still denied, escalate to Engineering with the user ID, role ID, and specific permission being denied."
            }
        ]
    }
}


def search_knowledge_base(category: str) -> dict:
    """
    Search the knowledge base by category.
    Returns the full troubleshooting data for that category.
    """
    category_lower = category.lower().strip()

    # Map common variations to our category keys
    category_mapping = {
        "authentication": "authentication",
        "login": "authentication",
        "password": "authentication",
        "sso": "authentication",
        "saml": "authentication",
        "2fa": "authentication",
        "mfa": "authentication",
        "integration": "integration",
        "api": "integration",
        "webhook": "integration",
        "sync": "integration",
        "performance": "performance",
        "slow": "performance",
        "timeout": "performance",
        "loading": "performance",
        "export": "performance",
        "billing": "billing",
        "charge": "billing",
        "invoice": "billing",
        "payment": "billing",
        "permission": "permissions",
        "permissions": "permissions",
        "access": "permissions",
        "role": "permissions",
    }

    matched_key = category_mapping.get(category_lower)

    if matched_key and matched_key in KNOWLEDGE_BASE:
        return KNOWLEDGE_BASE[matched_key]

    # Fuzzy match: check if any keyword appears in the query
    for keyword, key in category_mapping.items():
        if keyword in category_lower:
            return KNOWLEDGE_BASE[key]

    return {"error": f"No knowledge base entry found for category: '{category}'"}


def get_all_categories() -> list:
    """Return a list of all available categories."""
    return [v["category"] for v in KNOWLEDGE_BASE.values()]
