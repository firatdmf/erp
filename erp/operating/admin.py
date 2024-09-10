from django.contrib import admin
from .models import RawMaterialCategory, RawMaterial, UnitCategory, Machine, Product

# Register your models here.


admin.site.register(RawMaterialCategory)
admin.site.register(RawMaterial)
admin.site.register(UnitCategory)
admin.site.register(Machine)
admin.site.register(Product)
