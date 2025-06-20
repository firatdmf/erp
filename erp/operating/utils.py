from .models import MachineCredential

def get_machine_from_api_key(api_key):
    try:
        machine = MachineCredential.objects.get(api_key=api_key, is_active=True)
        return machine
    except MachineCredential.DoesNotExist:
        return None