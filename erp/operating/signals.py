from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import (
    Order,
    OrderItem,
    OrderItemUnit,
    RawMaterialGoodItem,
    RawMaterialGoodReceipt,
)


from django.db import transaction

# from .models import generate_machine_qr_for_order


@receiver([post_save, post_delete], sender=OrderItem)
def sync_order_status(sender, instance, **kwargs):
    order = instance.order
    order.update_status_from_items()


@receiver(post_save, sender=OrderItemUnit)
def sync_order_item_unit_status(sender, instance, **kwargs):
    print("this has been called for OrderItemUnit")
    order_item = instance.order_item
    order_item.update_status_from_units()


# update the RawMaterialGoodReceipt when adding raw material items to the receipt, so it also updates the A/P in accounting.
@receiver(post_save, sender=RawMaterialGoodItem)
@receiver(post_delete, sender=RawMaterialGoodItem)
def update_receipt_liability(sender, instance, **kwargs):
    if instance.receipt:
        instance.receipt.save()


# create liability accounts payable when we create a receipt with items.
@receiver(post_save, sender=RawMaterialGoodReceipt)
def create_or_update_liability_for_receipt(sender, instance, created, **kwargs):
    from accounting.models import LiabilityAccountsPayable

    """
    Sync LiabilityAccountsPayable whenever a RawMaterialGoodReceipt is saved.
    """
    # only process if receipt has items
    if not instance.items.exists():
        return
    
    print("your instance amount is: ", instance.amount)

    with transaction.atomic():
        liability_accounts_payable, created = (
            LiabilityAccountsPayable.objects.update_or_create(
                raw_material_good_receipt=instance,
                defaults={
                    "book": instance.book,
                    "paid":False,
                    "amount": "%.2f" % instance.amount, #2 decimal fields only.
                    "supplier": instance.supplier,
                },
            )
        )
