"""Plain-language explainer for tool calls — beginners must understand BEFORE approving.

Two layers (defense in depth):
1. Deterministic explainer (this file): always available, no LLM needed, bilingual (en/fa).
2. Model-provided purpose: the agent states WHY in its own words (attached when present).

The approval card shows: what it does + reversible? + risk + model purpose.
Language follows the dashboard/OS locale (fa/en).
"""

from __future__ import annotations

from typing import Any, Dict


def _is_fa(lang: str) -> bool:
    return (lang or "en").lower().startswith("fa")


def explain_tool_call(tool_name: str, args: Dict[str, Any] | None = None,
                      lang: str = "en") -> Dict[str, Any]:
    """Explain a pending tool call in plain language. Pure function."""
    args = args or {}
    fa = _is_fa(lang)

    def T(en: str, f: str) -> str:
        return f if fa else en

    if tool_name == "file_read":
        return {
            "summary": T(f"Read the file {args.get('path', '?')}",
                         f"خواندن فایل {args.get('path', '؟')}"),
            "details": T("Read-only. Nothing changes on your system.",
                         "فقط خواندن است. هیچ چیزی در سیستم شما تغییر نمی‌کند."),
            "reversible": True,
        }
    if tool_name == "file_list":
        return {
            "summary": T(f"List files in {args.get('path', '.')}",
                         f"نمایش فایل‌های مسیر {args.get('path', '.')}"),
            "details": T("Read-only directory listing.",
                         "فقط نمایش فهرست پوشه است."),
            "reversible": True,
        }
    if tool_name == "file_write":
        path = str(args.get("path", "?"))
        size = len(str(args.get("content", "")))
        return {
            "summary": T(f"Write {size} characters to {path}",
                         f"نوشتن {size} نویسه در {path}"),
            "details": T("Creates or OVERWRITES the file. Overwritten content cannot be auto-restored unless versioned.",
                         "فایل را می‌سازد یا بازنویسی می‌کند. محتوای بازنویسی‌شده بدون نسخه‌پشتیبان برنمی‌گردد."),
            "reversible": False,
        }
    if tool_name in ("bash_exec", "python_exec"):
        cmd = str(args.get("command", args.get("code", "")))
        short = (cmd[:160] + "…") if len(cmd) > 160 else cmd
        return {
            "summary": T(f"Run this command: {short}",
                         f"اجرای این دستور: {short}"),
            "details": _explain_command(cmd, fa),
            "reversible": False,
        }
    if tool_name == "web_search":
        return {
            "summary": T(f"Search the web for: {args.get('query', '?')}",
                         f"جستجوی وب برای: {args.get('query', '؟')}"),
            "details": T("Sends your query to a search engine. No changes to your system.",
                         "عبارت شما به موتور جستجو ارسال می‌شود. تغییری در سیستم ایجاد نمی‌شود."),
            "reversible": True,
        }
    if tool_name == "web_fetch":
        return {
            "summary": T(f"Download content from: {args.get('url', '?')}",
                         f"دریافت محتوا از: {args.get('url', '؟')}"),
            "details": T("Fetches a web page for the agent to read. The page itself is external and untrusted.",
                         "صفحه وب را برای خواندن ایجنت دریافت می‌کند. خود صفحه خارجی و غیرقابل اعتماد است."),
            "reversible": True,
        }
    return {
        "summary": T(f"Run tool '{tool_name}'", f"اجرای ابزار «{tool_name}»"),
        "details": T("Custom tool. Review its arguments carefully before approving.",
                     "ابزار سفارشی. قبل از تایید، ورودی‌های آن را با دقت بررسی کنید."),
        "reversible": False,
    }


def _explain_command(cmd: str, fa: bool) -> str:
    """One-line plain-language gloss for common commands."""
    c = cmd.strip()
    glossary = [
        ("ls", "lists files in a folder", "نمایش فایل‌های یک پوشه"),
        ("pwd", "shows the current folder", "نمایش پوشه جاری"),
        ("cat ", "prints a file's content", "چاپ محتوای یک فایل"),
        ("echo", "prints text", "چاپ متن"),
        ("git status", "shows changed files (safe, read-only)", "نمایش فایل‌های تغییریافته (امن، فقط خواندن)"),
        ("git diff", "shows code differences (safe, read-only)", "نمایش تفاوت کدها (امن، فقط خواندن)"),
        ("git log", "shows commit history (safe, read-only)", "نمایش تاریخچه کامیت‌ها (امن، فقط خواندن)"),
        ("git add", "stages files for the next commit", "آماده‌سازی فایل‌ها برای کامیت بعدی"),
        ("git commit", "saves a snapshot of staged changes", "ذخیره نسخه‌ای از تغییرات آماده‌شده"),
        ("git push", "uploads commits to the remote server (hard to undo)", "آپلود کامیت‌ها به سرور (برگرداندن سخت)"),
        ("npm install", "downloads packages from the internet and runs install scripts", "دانلود پکیج‌ها از اینترنت و اجرای اسکریپت نصب"),
        ("pip install", "downloads Python packages from the internet", "دانلود پکیج‌های پایتون از اینترنت"),
        ("pytest", "runs the test suite", "اجرای مجموعه تست‌ها"),
        ("mkdir", "creates a folder", "ساخت پوشه"),
        ("cp ", "copies files", "کپی فایل‌ها"),
        ("mv ", "moves/renames files", "جابه‌جایی/تغییرنام فایل‌ها"),
        ("rm ", "DELETES files (usually not recoverable)", "حذف فایل‌ها (معمولاً غیرقابل بازگشت)"),
        ("chmod", "changes file permissions", "تغییر دسترسی‌های فایل"),
        ("curl", "downloads data from the internet", "دانلود داده از اینترنت"),
        ("docker", "controls containers on this machine", "کنترل کانتینرهای این ماشین"),
    ]
    for prefix, en, f in glossary:
        if c.startswith(prefix):
            return f if fa else en
    if ">" in c or ">>" in c:
        return "writes command output into a file (modifies files)" if not fa else "خروجی دستور را در فایل می‌نویسد (تغییر فایل)"
    if "|" in c:
        return "chains multiple commands together (check each part)" if not fa else "چند دستور را به هم زنجیر می‌کند (هر بخش را بررسی کنید)"
    return ("Runs a terminal command. It can change files, install software, or access the network — "
            "approve only if you understand it.") if not fa else (
            "یک دستور ترمینال اجرا می‌کند. می‌تواند فایل‌ها را تغییر دهد، نرم‌افزار نصب کند یا به شبکه وصل شود — "
            "فقط اگر آن را می‌فهمید تایید کنید.")
