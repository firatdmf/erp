from django.db import models

# To store array field use this
from django.contrib.postgres.fields import ArrayField
from django.forms import ValidationError

# Create your models here.


class Company(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, verbose_name="Company Name (required)")
    email = models.EmailField(blank=True)
    backgroundInfo = models.TextField(
        max_length=200,
        verbose_name="Background info",
        blank=True,
    )
    phone = models.CharField(max_length=15, blank=True)
    # website = models.URLField(blank=True)
    website = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True)
    # city = models.CharField(max_length=100, blank=True)
    # state = models.CharField(max_length=100, blank=True)
    # zip_code = models.CharField(max_length=10, blank=True, verbose_name="Zip")
    country = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Companies"


class Contact(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=50, verbose_name="Contact Name (required)")
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True
    )
    job_title = models.CharField(max_length=25, blank=True, verbose_name="Job Title")
    email = models.EmailField(blank=True)
    backgroundInfo = models.TextField(
        max_length=200,
        verbose_name="Background info",
        blank=True,
    )
    phone = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=50, blank=True)
    birthday = models.DateField(null=True, blank=True)

    def __str__(self):
        if self.company:
            return f"{self.name} | {self.company.name}"
        else:
            return self.name

    class Meta:
        verbose_name_plural = "Contacts"


class Supplier(models.Model):
    # the company name or contact name should be unique, I'll set that up later.
    company_name = models.CharField(max_length=300, null=True, blank=True)
    contact_name = models.CharField(max_length=300, null=True, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    website = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Ensure that you call super().clean() to maintain the default validation behavior.
        super().clean()
        if not self.company_name and not self.contact_name:
            raise ValidationError(
                "You have to enter either, company name or contact name."
            )

    def __str__(self):
        return f"{self.company_name}"


class Note(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    # If I delete the contact, then delete the notes associated to it.
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, blank=True, null=True, related_name="notes"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True, related_name="notes"
    )
    content = models.TextField()

    # set a rule for not allowing a note to be associated with both the contact, and company at the same time.
    def clean(self):
        super().clean()
        if (self.contact and self.company) or (not self.contact and not self.company):
            raise ValidationError(
                "A note must be associated with either a contact or a company, but not both."
            )

    def save(self, *args, **kwargs):
        self.clean()  # Ensure validation runs on save
        super().save(*args, **kwargs)

    # below is for admin view
    def __str__(self):
        if self.contact:
            return f"Note for {self.contact}"
        elif self.company:
            return f"Note for {self.company}"
        else:
            return ("Unassociated Note")
