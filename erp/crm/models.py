from django.db import models

# Create your models here.
class Client(models.Model):
    client_name = models.CharField(max_length=200)
    client_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True, verbose_name="ZIP Code")
    country = models.CharField(max_length=100, blank=True)
    birthday = models.DateField(null=True, blank=True)
    company_name = models.CharField(max_length=255, blank=True, verbose_name="Company Name")
    job_title = models.CharField(max_length=100, blank=True, verbose_name="Job Title")

    def __str__(self):
        return self.client_name
    
    class Meta:
        verbose_name_plural = "Clients"

class Company(models.Model):
    company_name = models.CharField(max_length=255, verbose_name="Company Name (Required)")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True, verbose_name="ZIP Code")
    country = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    clients = models.ManyToManyField(Client)

    def __str__(self):
        return self.company_name
    
    class Meta:
        verbose_name_plural = "Companies"