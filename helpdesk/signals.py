from django.db.models.signals import post_save
from django.dispatch import receiver

from base.models import Company
from helpdesk.faq_defaults import DEFAULT_FAQS


@receiver(post_save, sender=Company)
def seed_default_faqs(sender, instance, created, **kwargs):
    """Give every new company the starter FAQ set so Help isn't empty."""
    if not created:
        return
    from helpdesk.models import FAQ, FAQCategory

    for cat_title, faqs in DEFAULT_FAQS.items():
        category = FAQCategory.objects.entire().filter(
            title=cat_title, company_id=instance
        ).first()
        if category is None:
            category = FAQCategory(title=cat_title, company_id=instance)
            category.save()
        for question, answer in faqs:
            if not FAQ.objects.entire().filter(
                question=question, company_id=instance
            ).exists():
                FAQ(
                    question=question,
                    answer=answer,
                    category=category,
                    company_id=instance,
                ).save()
