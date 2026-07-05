"""Starter FAQ content seeded for every company (see signals in apps.py)."""

DEFAULT_FAQS = {
    "Getting Started": [
        (
            "How do I log in for the first time?",
            "Use the email address and password shared by your HR. On first "
            "login you'll be asked to accept the terms. Use 'Forgot password' "
            "on the login page if you need to reset — a 6-digit code is sent "
            "to your email.",
        ),
        (
            "How do I change my password or username?",
            "Click your profile picture (top-right) → Change Password or "
            "Change Username.",
        ),
        (
            "Why can't I see some menus other people have?",
            "Menus depend on your role and your company's subscription plan. "
            "Employees see their own data; managers and HR see more. If you "
            "believe something is missing, ask your HR admin.",
        ),
    ],
    "Attendance & Check-in": [
        (
            "How do I check in?",
            "Use the green Check In button in the top bar (web) or the "
            "check-in screen in the mobile app. If your company enables face "
            "verification, the app will ask for a selfie that must match "
            "your enrolled photo.",
        ),
        (
            "Why does check-in say 'outside shift hours'?",
            "Check-in opens 30 minutes before your shift starts and closes "
            "when your shift ends. If you have no shift scheduled today, "
            "check-in is blocked — contact your manager if that's wrong.",
        ),
        (
            "My check-in/check-out time looks wrong. Why?",
            "Times are recorded in your company's timezone. If something "
            "still looks off, raise a ticket under Support with a screenshot.",
        ),
        (
            "How do I request a shift change?",
            "Employee → Shift Requests → Create. Your reporting manager or "
            "HR approves it; permanent changes apply immediately on approval, "
            "date-ranged ones apply from the requested date.",
        ),
    ],
    "Leave": [
        (
            "How do I apply for leave?",
            "Leave → My Leave Requests → Create. Pick the leave type, dates "
            "and reason. Your reporting manager/HR gets notified and you'll "
            "get a notification when it's approved or rejected.",
        ),
        (
            "How are my available leave days calculated?",
            "Each leave type has rules set by HR (accrual, carry-forward, "
            "maximums). Your current balance is shown when you apply and "
            "under Leave → My Available Leave.",
        ),
    ],
    "Payroll": [
        (
            "When is my payslip available?",
            "HR generates payslips per pay period. You'll get a notification "
            "when yours is ready — view or download it under Payroll → "
            "Payslips.",
        ),
        (
            "Why is my payslip missing or not generating?",
            "A payslip needs an ACTIVE contract with a wage set for the "
            "period. If HR sees an error naming a missing contract, it must "
            "be created under Payroll → Pay Register first.",
        ),
        (
            "Where do I find my Form 16 / tax documents?",
            "Payroll → Form 16. Pick the financial year; documents your HR "
            "uploaded for you appear there.",
        ),
        (
            "How do I claim an expense/reimbursement?",
            "Payroll → Expenses → Create. Attach the receipt, pick a "
            "category, and submit — HR approves and pays it with payroll.",
        ),
    ],
    "Mobile App": [
        (
            "I'm not getting notifications on the app.",
            "Open the app at least once after installing and allow "
            "notifications when prompted. Check Android Settings → Apps → "
            "Emplinx → Notifications is enabled.",
        ),
        (
            "Why does the app ask for camera/location permission?",
            "Camera is used for face-verification check-in; location is only "
            "captured at check-in/out if your company enables it. Neither is "
            "used in the background.",
        ),
    ],
}
