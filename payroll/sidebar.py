"""
payroll/sidebar.py

"""

from django.apps import apps
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from skylinx.menu import settings_menu

MENU = _("Payroll")
IMG_SRC = "images/ui/wallet-outline.svg"

SUBMENUS = [
    {
        "menu": _("Pay Register"),
        "redirect": reverse("view-contract"),
        "accessibility": "payroll.sidebar.dasbhoard_accessibility",
    },
    {
        "menu": _("Allowances"),
        "redirect": reverse("view-allowance"),
        "accessibility": "payroll.sidebar.allowance_accessibility",
    },
    {
        "menu": _("Deductions"),
        "redirect": reverse("view-deduction"),
        "accessibility": "payroll.sidebar.deduction_accessibility",
    },
    {
        "menu": _("Payslips"),
        "redirect": reverse("view-payslip"),
        "accessibility": "payroll.sidebar.payslip_accessibility",
    },
    {
        "menu": _("Expenses"),
        "redirect": reverse("view-reimbursement"),
        "accessibility": "payroll.sidebar.expense_accessibility",
    },
    # Income Tax (TDS) hidden per product decision — the filing-status pages
    # still exist at payroll/filling-status-view for direct links, just no
    # sidebar entry.
    {
        "menu": _("Form 16"),
        "redirect": reverse("form16-list"),
        "accessibility": "payroll.sidebar.form16_accessibility",
    },
]


def dasbhoard_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("payroll.view_contract")


def allowance_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("payroll.view_allowance")


def deduction_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("payroll.view_deduction")


def loan_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("payroll.view_loanaccount")


def federal_tax_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("payroll.view_filingstatus")


def payslip_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Payslips is a self-service page. Everyone with view_payslip can access.
    """
    return request.user.has_perm("payroll.view_payslip")


def expense_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Expenses is a self-service page for submitting reimbursement requests.
    """
    return request.user.has_perm("payroll.view_reimbursement")


def form16_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("payroll.view_payslip")


# ---------------------------------------------------------------------------
# Settings menu registrations
# ---------------------------------------------------------------------------


def payslip_auto_generation_accessibility(
    request, submenu, user_perms, *args, **kwargs
):
    return request.user.has_perm("payroll.view_payslipautogenerate")


@settings_menu.register
class PayrollSettings:
    title = _("Payroll")
    order = 7
    condition = lambda self, request: apps.is_installed("payroll")
    items = [
        {
            "label": _("Payslip Auto Generation"),
            "url": reverse_lazy("auto-payslip-settings-view"),
            "accessibility": payslip_auto_generation_accessibility,
        },
    ]
