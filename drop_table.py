#!/usr/bin/env python
import os
import sys
import django

# Add project directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'erp'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from django.db import connection

# Drop table
with connection.cursor() as cursor:
    cursor.execute('DROP TABLE IF EXISTS marketing_productattribute CASCADE')
    print('✅ Table marketing_productattribute dropped successfully')
    
print('\nNow run: .\\vir_env\\Scripts\\python.exe erp/manage.py migrate marketing')
