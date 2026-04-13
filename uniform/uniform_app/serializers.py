# serializers.py - Top pe import add karo

from rest_framework import serializers

from .models import User, Customer, RMOrder , MSOrder , MSOrderItem , RMOrderItem# ✅ RMOrder import karo

# Rest of your serializers...
class RegisterSerializer(serializers.ModelSerializer):
    confirmPassword = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'full_name', 'password', 'confirmPassword']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data['password'] != data['confirmPassword']:
            raise serializers.ValidationError("Passwords do not match")
        return data

    def create(self, validated_data):
        validated_data.pop('confirmPassword')
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

# serializers.py - Customer Serializer

from rest_framework import serializers
from .models import Customer

class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model"""
    
    # Read-only formatted fields
    formatted_total_value = serializers.SerializerMethodField()
    rm_orders = serializers.SerializerMethodField()
    ms_orders = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'phone', 'email', 'city',
            'rm_orders', 'ms_orders', 'total_value', 'formatted_total_value',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_formatted_total_value(self, obj):
        """Return total value in Lakhs/K format"""
        if obj.total_value >= 100000:
            return f"₹{obj.total_value/100000:.1f}L"
        elif obj.total_value >= 1000:
            return f"₹{obj.total_value/1000:.0f}K"
        return f"₹{obj.total_value}"
    
    def get_rm_orders(self, obj):
        """Get RM orders count"""
        return getattr(obj, 'rm_orders_count', 0)
    
    def get_ms_orders(self, obj):
        """Get MS orders count"""
        return getattr(obj, 'ms_orders_count', 0)
    
    def validate_phone(self, value):
        """Validate phone number"""
        if not value:
            raise serializers.ValidationError("Phone number is required")
        
        # Check for uniqueness
        instance = self.instance
        if Customer.objects.exclude(pk=instance.pk if instance else None).filter(phone=value).exists():
            raise serializers.ValidationError("Customer with this phone number already exists")
        
        return value

# serializers.py - Fix RMOrderSerializer
# serializers.py - RMOrderSerializer (Simplified)
# serializers.py - Fix RMOrderSerializer (customer_id optional karo)

class RMOrderSerializer(serializers.ModelSerializer):
    """RM Order Serializer with customer details"""
    
    # Read-only fields for frontend compatibility
    cust = serializers.SerializerMethodField()
    cat = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    orderDate = serializers.SerializerMethodField()
    deliveryDate = serializers.SerializerMethodField()
    orderBy = serializers.SerializerMethodField()
    amt = serializers.SerializerMethodField()
    qty = serializers.IntegerField(source='quantity', read_only=True)
    
    # ✅ FIX: customer_id ko optional banao (required=False)
    customer_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = RMOrder
        fields = [
            'id', 'order_id', 'customer_id', 'customer', 'cust',
            'category', 'cat', 'time', 'order_date', 'delivery_date',
            'orderDate', 'deliveryDate', 'ordered_by', 'orderBy',
            'amount', 'amt', 'quantity', 'qty', 'status',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'order_id', 'created_at', 'updated_at', 'customer']
    
    def get_cust(self, obj):
        return obj.customer.name if obj.customer else ''
    
    def get_cat(self, obj):
        return obj.category
    
    def get_time(self, obj):
        return obj.time_display
    
    def get_orderDate(self, obj):
        return obj.order_date_display
    
    def get_deliveryDate(self, obj):
        return obj.delivery_date_display
    
    def get_orderBy(self, obj):
        return obj.ordered_by or ''
    
    def get_amt(self, obj):
        return float(obj.amount)
    
    def validate_customer_id(self, value):
        """Validate customer exists - only if value is provided"""
        if value is None:
            return value
        try:
            customer = Customer.objects.get(id=value, is_active=True)
            return value
        except Customer.DoesNotExist:
            raise serializers.ValidationError(f"Customer with id {value} does not exist")
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value
    
    def create(self, validated_data):
        customer_id = validated_data.pop('customer_id', None)
        if customer_id:
            customer = Customer.objects.get(id=customer_id)
            validated_data['customer'] = customer
        return RMOrder.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        # ✅ FIX: Agar customer_id hai toh update karo, nahi toh mat karo
        if 'customer_id' in validated_data:
            customer_id = validated_data.pop('customer_id')
            if customer_id:
                customer = Customer.objects.get(id=customer_id)
                instance.customer = customer
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance
    
# serializers.py - Add MSOrderSerializer

# serializers.py - Fix MSOrderSerializer

class MSOrderSerializer(serializers.ModelSerializer):
    """MS Order Serializer with customer details"""
    
    # Read-only fields for frontend compatibility
    cust = serializers.SerializerMethodField()
    cat = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    orderDate = serializers.SerializerMethodField()
    deliveryDate = serializers.SerializerMethodField()
    orderBy = serializers.SerializerMethodField()
    amt = serializers.SerializerMethodField()
    qty = serializers.IntegerField(source='quantity', read_only=True)
    deadline = serializers.SerializerMethodField()
    
    # ✅ FIX: customer_id ko optional banao
    customer_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = MSOrder
        fields = [
            'id', 'order_id', 'customer_id', 'customer', 'cust',
            'gender', 'category', 'cat', 'time', 'order_date', 'delivery_date',
            'orderDate', 'deliveryDate', 'deadline', 'ordered_by', 'orderBy',
            'tailor', 'amount', 'amt', 'quantity', 'qty', 'status',
            'chest', 'waist', 'hip', 'shoulder', 'length', 'sleeve_length',
            'armhole', 'neck', 'collar', 'bicep', 'elbow', 'cuff', 'thigh',
            'knee', 'bottom', 'rise', 'inseam', 'bust', 'under_bust', 'waist_hip',
            'shoulder_to_waist', 'waist_to_knee', 'waist_to_floor', 'arm_length',
            'wrist', 'front_neck_depth', 'back_neck_depth', 'dart_length', 'dart_depth',
            'special_notes',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'order_id', 'created_at', 'updated_at', 'customer']
    
    def get_cust(self, obj):
        return obj.customer.name if obj.customer else ''
    
    def get_cat(self, obj):
        return obj.category
    
    def get_time(self, obj):
        return obj.time_display
    
    def get_orderDate(self, obj):
        return obj.order_date_display
    
    def get_deliveryDate(self, obj):
        return obj.delivery_date_display
    
    def get_deadline(self, obj):
        return obj.delivery_date_display
    
    def get_orderBy(self, obj):
        return obj.ordered_by or ''
    
    def get_amt(self, obj):
        return float(obj.amount)
    
    def validate_customer_id(self, value):
        """Validate customer exists - only if value is provided"""
        if value is None:
            return value
        try:
            customer = Customer.objects.get(id=value, is_active=True)
            return value
        except Customer.DoesNotExist:
            raise serializers.ValidationError(f"Customer with id {value} does not exist")
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value
    
    def create(self, validated_data):
        customer_id = validated_data.pop('customer_id', None)
        if customer_id:
            customer = Customer.objects.get(id=customer_id)
            validated_data['customer'] = customer
        return MSOrder.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        # ✅ FIX: Agar customer_id hai toh update karo
        if 'customer_id' in validated_data:
            customer_id = validated_data.pop('customer_id')
            if customer_id:
                customer = Customer.objects.get(id=customer_id)
                instance.customer = customer
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance
    
# serializers.py - Add MSOrderItemSerializer

# serializers.py - Update MSOrderItemSerializer

class MSOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for MS Order Items - Each item is a PERSON"""
    
    class Meta:
        model = MSOrderItem
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class MSOrderWithItemsSerializer(serializers.ModelSerializer):
    """MS Order Serializer with items"""
    items = MSOrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = MSOrder
        fields = '__all__'

# serializers.py - Add after MSOrderItemSerializer

class RMOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for RM Order Items"""
    
    class Meta:
        model = RMOrderItem
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class RMOrderWithItemsSerializer(serializers.ModelSerializer):
    """RM Order Serializer with items"""
    items = RMOrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = RMOrder
        fields = '__all__'