from skylinx.validators import SafeMimeValidator
"""
tax_models.py

This module contains the models for the tax calculation of taxable income.
"""

import math

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from base.skylinx_company_manager import SkylinxCompanyManager
from base.models import Company
from skylinx.models import SkylinxModel
from payroll.models.models import FilingStatus


class PayrollSettings(SkylinxModel):
    """
    Payroll settings model
    """

    choices = [
        ("prefix", _("Prefix")),
        ("postfix", _("Suffix")),
    ]

    currency_symbol = models.CharField(null=True, default="₹", max_length=5)
    position = models.CharField(
        max_length=15, null=True, choices=choices, default="prefix"
    )

    company_id = models.ForeignKey(Company, null=True, on_delete=models.CASCADE)
    objects = SkylinxCompanyManager("company_id")

    class Meta:
        verbose_name = _("Payroll Settings")
        verbose_name_plural = _("Payroll Settings")

    def __str__(self):
        return f"Payroll Settings {self.currency_symbol}"


class TaxBracket(SkylinxModel):
    """
    TaxBracket model
    """

    company_id = models.ForeignKey("base.Company", on_delete=models.CASCADE, null=True, blank=True)
    objects = SkylinxCompanyManager()

    filing_status_id = models.ForeignKey(
        FilingStatus,
        on_delete=models.CASCADE,
        verbose_name=_("Tax Regime"),
    )
    min_income = models.FloatField(
        null=False, blank=False, verbose_name=_("Min. Income")
    )
    max_income = models.FloatField(null=True, blank=True, verbose_name=_("Max. Income"))
    tax_rate = models.FloatField(
        null=False, blank=False, default=0.0, verbose_name=_("Tax Rate")
    )
#     objects = models.Manager()

    def __str__(self):
        if self.max_income != math.inf:
            return (
                f"{self.filing_status_id}"
                f"{self.tax_rate}% tax rate on "
                f"{self.min_income} and {self.max_income}"
            )
        return (
            f"{self.tax_rate}% tax rate on taxable income equal or above "
            f"{self.min_income} for {self.filing_status_id}"
        )

    def get_display_max_income(self):
        """
        Retrieves the maximum income.
        Returns:
            float or None: The maximum income if it is a finite value, otherwise None.
        """
        if self.max_income != math.inf:
            return self.max_income
        return None

    def get_update_url(self):
        """
        Returns the URL for updating the tax bracket.
        """

        return reverse("tax-bracket-update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """
        Returns the URL for updating the tax bracket.
        """

        return reverse("tax-bracket-delete", kwargs={"tax_bracket_id": self.pk})

    def clean(self):
        super().clean()

        existing_bracket = TaxBracket.objects.filter(
            filing_status_id=self.filing_status_id,
            min_income=self.min_income,
            max_income=self.max_income,
            tax_rate=self.tax_rate,
        ).exclude(pk=self.pk)
        if existing_bracket.exists():
            raise ValidationError(_("This tax bracket already exists"))

        if self.max_income is None:
            self.max_income = math.inf

        if self.min_income >= self.max_income:
            raise ValidationError(
                {"max_income": _("Maximum income must be greater than minimum income.")}
            )

        existing_brackets = TaxBracket.objects.filter(
            filing_status_id=self.filing_status_id
        ).exclude(pk=self.pk)
        if existing_brackets.filter(max_income__gte=self.min_income).exists():
            tax_bracket = existing_brackets.filter(
                max_income__gte=self.min_income
            ).first()
            if tax_bracket.min_income <= self.max_income:
                raise ValidationError(
                    {
                        "min_income": format_lazy(
                            "The minimum income of this tax bracket must be \
                                greater than the maximum income of {}.",
                            tax_bracket,
                        )
                    }
                )

    class Meta:
        verbose_name = _("Income Slab")
        verbose_name_plural = _("Income Slabs")

class Form16Document(SkylinxModel):
    """
    Form 16 uploaded documents model
    """

    company_id = models.ForeignKey("base.Company", on_delete=models.CASCADE, null=True, blank=True)
    objects = SkylinxCompanyManager()
    from employee.models import Employee  # Local import or add to top
    
    employee = models.ForeignKey("employee.Employee", on_delete=models.CASCADE, verbose_name=_("Employee"))
    financial_year = models.CharField(max_length=9, verbose_name=_("Financial Year"), help_text="e.g., 2023-2024")
    document = models.FileField(upload_to="payroll/form16/", verbose_name=_("Form 16 Document"), validators=[SafeMimeValidator()])

    class Meta:
        unique_together = ("employee", "financial_year")
        verbose_name = _("Form 16 Document")
        verbose_name_plural = _("Form 16 Documents")

    def __str__(self):
        return f"Form 16 for {self.employee} ({self.financial_year})"

