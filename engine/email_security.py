"""Email Security — check email client configuration and detect compromises."""

import subprocess
import winreg
from pathlib import Path
from datetime import datetime


class EmailAccount:
    """Represents a detected email account."""
    def __init__(self, client: str, email: str, protocol: str = "", encryption: str = ""):
        self.client = client
        self.email = email
        self.protocol = protocol
        self.encryption = encryption
        self.issues = []


def _detect_outlook_accounts() -> list[EmailAccount]:
    """Detect Outlook/Thunderbird email accounts."""
    accounts = []

    try:
        # Check Outlook registry (Windows Mail)
        outlook_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Office\16.0\Outlook\Profiles")

        for i in range(winreg.QueryInfoKey(outlook_key)[0]):
            try:
                profile_name = winreg.EnumKey(outlook_key, i)
                profile_key = winreg.OpenKey(outlook_key, profile_name)

                for j in range(winreg.QueryInfoKey(profile_key)[0]):
                    try:
                        account_name = winreg.EnumKey(profile_key, j)
                        low = account_name.lower()
                        if "@" in account_name or "pop" in low or "imap" in low:
                            # Protocol is inferable from the account/key name.
                            if "imap" in low:
                                proto = "IMAP"
                            elif "pop" in low:
                                proto = "POP3"
                            elif "smtp" in low:
                                proto = "SMTP"
                            elif "exchange" in low or "outlook" in low:
                                proto = "Exchange"
                            else:
                                proto = ""
                            account = EmailAccount("Outlook", account_name,
                                                   protocol=proto)
                            accounts.append(account)
                    except Exception:
                        pass
            except Exception:
                pass

    except Exception:
        pass

    # Check Thunderbird (Mozilla)
    try:
        thunderbird_dir = Path.home() / "AppData" / "Roaming" / "Thunderbird"
        if thunderbird_dir.exists():
            for profile_dir in thunderbird_dir.glob("*/"):
                prefs_file = profile_dir / "prefs.js"
                if prefs_file.exists():
                    try:
                        with open(prefs_file, "r", encoding="utf-8") as f:
                            content = f.read()
                            if "mail.accountmanager.accounts" in content:
                                account = EmailAccount("Thunderbird", profile_dir.name)
                                accounts.append(account)
                    except Exception:
                        pass
    except Exception:
        pass

    return accounts


def _check_outlook_encryption() -> list[str]:
    """Check Outlook encryption settings."""
    issues = []

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Office\16.0\Outlook")

        # Check for TLS requirement
        try:
            tls_required = winreg.QueryValueEx(key, "RequireTLS")[0]
            if not tls_required:
                issues.append("Outlook: TLS encryption not required for outgoing mail")
        except Exception:
            pass

        # Check for SSL support
        try:
            ssl_support = winreg.QueryValueEx(key, "SSLSupport")[0]
            if not ssl_support:
                issues.append("Outlook: SSL/TLS support disabled")
        except Exception:
            pass

    except Exception:
        pass

    return issues


def _detect_saved_passwords() -> list[str]:
    """Check for saved passwords in browsers/clients."""
    issues = []

    # Chrome password storage location
    chrome_pwd = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Login Data"
    if chrome_pwd.exists():
        issues.append("Chrome: Saved passwords found in browser profile")

    # Edge password storage
    edge_pwd = Path.home() / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data" / "Default" / "Login Data"
    if edge_pwd.exists():
        issues.append("Edge: Saved passwords found in browser profile")

    # Outlook stored passwords (AutoDiscover)
    try:
        outlook_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Office\16.0\Outlook")
        try:
            winreg.QueryValueEx(outlook_key, "RememberPassword")
            issues.append("Outlook: Password caching enabled (disable for security)")
        except Exception:
            pass
    except Exception:
        pass

    return issues


def _check_breach_database(email: str) -> bool:
    """Check if email appears in known breach databases (simplified)."""
    # This would require HaveIBeenPwned API key in production
    # For now, return False (no breach detected)
    return False


def check_email_security() -> tuple[list[EmailAccount], list[str]]:
    """Check overall email security configuration."""
    accounts = _detect_outlook_accounts()
    all_issues = []

    # Check encryption
    all_issues.extend(_check_outlook_encryption())

    # Check saved passwords
    all_issues.extend(_detect_saved_passwords())

    # Check for 2FA configuration (simplified)
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\OneDrive")
        try:
            mfa_enabled = winreg.QueryValueEx(key, "MFAEnabled")[0]
            if not mfa_enabled:
                all_issues.append("Microsoft Account: Two-factor authentication not enabled")
        except Exception:
            pass
    except Exception:
        pass

    return (accounts, all_issues)


def get_email_recommendations() -> list[str]:
    """Get recommendations for email security."""
    recommendations = []
    accounts, issues = check_email_security()

    if not accounts:
        recommendations.append("No email accounts detected")
        return recommendations

    if len(issues) > 0:
        recommendations.append(f"Found {len(issues)} email security issue(s) — review settings")

    if any("TLS" in issue for issue in issues):
        recommendations.append("Enable TLS encryption for all email accounts")

    if any("Password" in issue for issue in issues):
        recommendations.append("Use credential manager instead of saving passwords directly")

    if any("2FA" in issue or "Two-factor" in issue for issue in issues):
        recommendations.append("Enable two-factor authentication on email accounts")

    if not issues:
        recommendations.append("Email security configuration looks good!")

    return recommendations


def get_email_clients() -> list[str]:
    """Detect installed email clients."""
    clients = []

    # Check Outlook
    try:
        outlook_exe = Path("C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE")
        if outlook_exe.exists():
            clients.append("Outlook")
    except Exception:
        pass

    # Check Thunderbird
    thunderbird_dir = Path.home() / "AppData" / "Roaming" / "Thunderbird"
    if thunderbird_dir.exists():
        clients.append("Thunderbird")

    # Check Mail (Windows)
    try:
        mail_exe = Path("C:\\Program Files\\WindowsApps")
        if mail_exe.exists():
            clients.append("Windows Mail")
    except Exception:
        pass

    return clients


def get_account_security_details(email: str) -> dict:
    """Get security details for a specific email account."""
    details = {
        "email": email,
        "client": "Unknown",
        "encryption": "Unknown",
        "saved_password": False,
        "breach_detected": False,
        "2fa_enabled": False,
    }

    # Check if password is saved
    details["saved_password"] = any(email in issue for issue in _detect_saved_passwords())

    # Check breach
    details["breach_detected"] = _check_breach_database(email)

    return details
