# serializers.py
from rest_framework import serializers
from .models import ConcernBranchMaster
from .models import DivisionMaster
from .models import CustomerMaster
from .models import UTRVoucher
from .models import ChitsUser
from .models import UserRoleMaster
from .models import Voucher

class ConcernBranchMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConcernBranchMaster
        fields = '__all__'  # Serialize all fields in the model

class DivisionMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = DivisionMaster
        fields = '__all__'

class CustomerMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerMaster
        fields = '__all__'

class UTRVoucherSerializer(serializers.ModelSerializer):
    class Meta:
        model = UTRVoucher
        fields = '__all__'

class ChitsUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChitsUser
        fields = '__all__'

class UserRoleMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRoleMaster
        fields = '__all__'

class VoucherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voucher
        fields = '__all__'  # Serialize all fields in the model
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Convert datetime fields to string format
        datetime_fields = ['created_at', 'expires_at']  # adjust field names as needed
        for field in datetime_fields:
            if field in representation and representation[field] is not None:
                representation[field] = representation[field].isoformat()
        return representation

