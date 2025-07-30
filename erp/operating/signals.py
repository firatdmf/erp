from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Order, OrderItem, OrderItemUnit
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


# @receiver(post_save, sender=Order)
# def create_qr_on_order_creation(sender, instance, created, **kwargs):
#     if created and not instance.qr_code_url:
#         generate_qr_for_order(instance)


# @receiver(post_save, sender=Order)
# def create_qr_on_order_creation(sender, instance, created, **kwargs):
#     if created and not instance.qr_code_url:
#         generate_machine_qr_for_order(instance)
