from django.db import models


# To store array field use this
from django.contrib.postgres.fields import ArrayField
from django.forms import ValidationError

# Create your models here.


class Company(models.Model):
    name = models.CharField(max_length=255, verbose_name="Company Name (required)")
    email = models.EmailField(blank=True)
    backgroundInfo = models.CharField(
        max_length=400,
        verbose_name="Background info",
        blank=True,
    )
    phone = models.CharField(max_length=15, blank=True)
    # website = models.URLField(blank=True)
    website = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=255, blank=True)
    # city = models.CharField(max_length=100, blank=True)
    # state = models.CharField(max_length=100, blank=True)
    # zip_code = models.CharField(max_length=10, blank=True, verbose_name="Zip")
    country = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Companies"


class Contact(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True, verbose_name="ZIP Code")
    country = models.CharField(max_length=100, blank=True)
    birthday = models.DateField(null=True, blank=True)
    company_name = models.CharField(
        max_length=255, blank=True, verbose_name="Company Name"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True
    )
    job_title = models.CharField(max_length=100, blank=True, verbose_name="Job Title")
    # notes = ArrayField(ArrayField(models.TextField(blank=True)))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Contacts"

class Supplier(models.Model):
    # the company name or contact name should be unique, I'll set that up later.
    company_name = models.CharField(max_length=300, null=True,blank=True)
    contact_name = models.CharField(max_length=300,null=True,blank=True)
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
        return(f"{self.company_name}")


class Note(models.Model):
    # If I delete the contact, then delete the notes associated to it.
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, blank=True, null=True
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    # below is for admin view
    def __str__(self):
        if self.contact:
            return f"Note for {self.contact}"
        return f"Note for {self.company}"
