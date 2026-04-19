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

# serializers.py - Update RMOrderItemSerializer

class RMOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for RM Order Items"""
    
    # ✅ Add image URL field
    reference_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = RMOrderItem
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_reference_image_url(self, obj):
        if obj.reference_image:
            return obj.reference_image.url
        return None


class RMOrderWithItemsSerializer(serializers.ModelSerializer):
    """RM Order Serializer with items"""
    items = RMOrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = RMOrder
        fields = '__all__'
    
# Quotation Serializer
# serializers.py
# from rest_framework import serializers
from .models import Quotation, QuotationItem, Customer

# serializers.py
from rest_framework import serializers
from .models import Quotation, QuotationItem, Customer


class QuotationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationItem
        fields = ['id', 'product_name', 'gender', 'size', 'quantity', 
                  'unit_price', 'discount_percent', 'amount', 'notes']


class QuotationSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True, required=False)
    customer_name_display = serializers.CharField(source='customer.name', read_only=True)
    customer_phone_display = serializers.CharField(source='customer.phone', read_only=True)
    customer_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    customer = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_no', 'date', 'valid_till',
            'customer', 'customer_id',
            'customer_name', 'customer_phone', 'customer_email', 'customer_address',
            'customer_name_display', 'customer_phone_display',
            'subject', 'message',
            'subtotal', 'discount_percent', 'discount_amount',
            'gst_percent', 'gst_amount', 'total_amount',
            'status', 'payment_terms', 'delivery_time', 'warranty', 'validity', 'notes',
            'items', 'created_by', 'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'quotation_no', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        customer_id = validated_data.pop('customer_id', None)
        
        # Handle customer
        if customer_id:
            try:
                from .models import Customer
                customer = Customer.objects.get(id=customer_id, is_active=True)
                validated_data['customer'] = customer
                validated_data['customer_name'] = customer.name
                validated_data['customer_phone'] = customer.phone
                validated_data['customer_email'] = customer.email or ''
                validated_data['customer_address'] = customer.city or ''
            except Customer.DoesNotExist:
                raise serializers.ValidationError({"customer_id": "Customer not found"})
        elif validated_data.get('customer_name'):
            from .models import Customer
            customer = Customer.objects.create(
                name=validated_data.get('customer_name'),
                phone=validated_data.get('customer_phone', ''),
                email=validated_data.get('customer_email', ''),
                city=validated_data.get('customer_address', ''),
            )
            validated_data['customer'] = customer
        
        quotation = Quotation.objects.create(**validated_data)
        
        for item_data in items_data:
            unit_price = item_data.get('unit_price', 0)
            if isinstance(unit_price, str):
                unit_price = float(unit_price)
            
            QuotationItem.objects.create(
                quotation=quotation,
                product_name=item_data.get('product_name', ''),
                gender=item_data.get('gender', 'Gents'),
                size=item_data.get('size', 'M'),
                quantity=int(item_data.get('quantity', 1)),
                unit_price=unit_price,
                discount_percent=float(item_data.get('discount_percent', 0)),
                amount=float(item_data.get('amount', 0)),
                notes=item_data.get('notes', '')
            )
        
        quotation = self.recalculate_totals(quotation)
        return quotation
    
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        customer_id = validated_data.pop('customer_id', None)
        
        if customer_id:
            try:
                from .models import Customer
                customer = Customer.objects.get(id=customer_id, is_active=True)
                validated_data['customer'] = customer
                validated_data['customer_name'] = customer.name
                validated_data['customer_phone'] = customer.phone
                validated_data['customer_email'] = customer.email or ''
                validated_data['customer_address'] = customer.city or ''
            except Customer.DoesNotExist:
                raise serializers.ValidationError({"customer_id": "Customer not found"})
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update items
        instance.items.all().delete()
        for item_data in items_data:
            unit_price = item_data.get('unit_price', 0)
            if isinstance(unit_price, str):
                unit_price = float(unit_price)
            
            QuotationItem.objects.create(
                quotation=instance,
                product_name=item_data.get('product_name', ''),
                gender=item_data.get('gender', 'Gents'),
                size=item_data.get('size', 'M'),
                quantity=int(item_data.get('quantity', 1)),
                unit_price=unit_price,
                discount_percent=float(item_data.get('discount_percent', 0)),
                amount=float(item_data.get('amount', 0)),
                notes=item_data.get('notes', '')
            )
        
        instance = self.recalculate_totals(instance)
        return instance
    
    def recalculate_totals(self, quotation):
        items = quotation.items.all()
        
        subtotal = sum(float(item.amount) for item in items)
        discount_amount = subtotal * (float(quotation.discount_percent) / 100)
        taxable_value = subtotal - discount_amount
        gst_amount = taxable_value * (float(quotation.gst_percent) / 100)
        total_amount = taxable_value + gst_amount
        
        quotation.subtotal = subtotal
        quotation.discount_amount = discount_amount
        quotation.gst_amount = gst_amount
        quotation.total_amount = total_amount
        quotation.save(update_fields=['subtotal', 'discount_amount', 'gst_amount', 'total_amount'])
        
        return quotation


class QuotationListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list view with items included"""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    customer_address = serializers.CharField(source='customer.city', read_only=True)
    items = QuotationItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_no', 'date', 'valid_till',
            'customer_name', 'customer_phone', 'customer_email', 'customer_address',
            'subject', 'subtotal', 'discount_percent', 'discount_amount',
            'gst_percent', 'gst_amount', 'total_amount',
            'status', 'payment_terms', 'delivery_time', 'warranty', 'validity', 'notes',
            'items', 'items_count', 'created_at', 'updated_at'
        ]
    
    def get_items_count(self, obj):
        return obj.items.count()
    
# ============= VENDOR SERIALIZERS =============
from .models import Vendor , VendorCategory , PurchaseOrderItem , PurchaseOrder

class VendorCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorCategory
        fields = ['id', 'name', 'description', 'is_active']


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = ['id', 'product_name', 'quantity', 'unit_price', 'total_price', 'received_quantity', 'notes']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'vendor', 'vendor_name', 'order_date',
            'expected_delivery_date', 'actual_delivery_date',
            'subtotal', 'tax_amount', 'total_amount',
            'status', 'notes', 'items', 'created_at'
        ]


class VendorSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    purchase_orders = PurchaseOrderSerializer(many=True, read_only=True)
    
    class Meta:
        model = Vendor
        fields = '__all__'
        read_only_fields = ['id', 'vendor_code', 'created_at', 'updated_at']


class VendorListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Vendor
        fields = [
            'id', 'vendor_code', 'name', 'category_name', 'vendor_type',
            'contact_person', 'phone', 'email', 'city', 'total_purchases',
            'total_orders', 'last_purchase_date', 'is_active', 'rating',
            'address_line1', 'address_line2', 'state', 'pincode',
            'gst_number', 'payment_terms', 'credit_limit', 'notes',
            'bank_name', 'account_number', 'ifsc_code'
        ]


# ============= PURCHASE ORDER SERIALIZERS =============

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = ['id', 'product_name', 'quantity', 'unit_price', 'total_price', 'received_quantity', 'notes']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=False)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    vendor_phone = serializers.CharField(source='vendor.phone', read_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'vendor', 'vendor_name', 'vendor_phone',
            'order_date', 'expected_delivery_date', 'actual_delivery_date',
            'subtotal', 'tax_amount', 'total_amount', 'status', 'notes',
            'items', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'po_number', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        from decimal import Decimal
        
        items_data = validated_data.pop('items', [])
        
        # Calculate subtotal
        subtotal = Decimal('0')
        for item_data in items_data:
            quantity = Decimal(str(item_data.get('quantity', 0)))
            unit_price = Decimal(str(item_data.get('unit_price', 0)))
            subtotal += quantity * unit_price
        
        # ✅ Calculate GST (18%)
        tax_amount = subtotal * Decimal('0.18')
        total_amount = subtotal + tax_amount
        
        validated_data['subtotal'] = subtotal
        validated_data['tax_amount'] = tax_amount
        validated_data['total_amount'] = total_amount
        
        purchase_order = PurchaseOrder.objects.create(**validated_data)
        
        for item_data in items_data:
            PurchaseOrderItem.objects.create(purchase_order=purchase_order, **item_data)
        
        return purchase_order
    
    def update(self, instance, validated_data):
        from decimal import Decimal
        
        items_data = validated_data.pop('items', [])
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Recalculate totals if items changed
        if items_data:
            subtotal = Decimal('0')
            for item_data in items_data:
                quantity = Decimal(str(item_data.get('quantity', 0)))
                unit_price = Decimal(str(item_data.get('unit_price', 0)))
                subtotal += quantity * unit_price
            
            instance.subtotal = subtotal
            instance.tax_amount = subtotal * Decimal('0.18')
            instance.total_amount = instance.subtotal + instance.tax_amount
        
        instance.save()
        
        # Update items (delete old, create new)
        instance.items.all().delete()
        for item_data in items_data:
            PurchaseOrderItem.objects.create(purchase_order=instance, **item_data)
        
        return instance


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list view with items"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'vendor_name', 'order_date', 
            'expected_delivery_date', 'actual_delivery_date',
            'subtotal', 'tax_amount', 'total_amount', 'status', 
            'items', 'items_count', 'notes'
        ]
    
    def get_items_count(self, obj):
        return obj.items.count()
    

# ============= PRODUCT CATALOG SERIALIZERS =============
from .models import ProductCategory , ProductVariant ,SchoolProductPrice , Product
from django.db.models import Sum

class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'description', 'icon', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductVariantSerializer(serializers.ModelSerializer):
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'size', 'color', 'fabric', 'price', 'effective_price',
            'stock_quantity', 'reorder_level', 'sku', 'is_active'
        ]


class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, read_only=False)
    category_name = serializers.CharField(source='category.name', read_only=True)
    formatted_price = serializers.CharField(read_only=True)
    total_stock = serializers.SerializerMethodField()
    variants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'product_code', 'name', 'category', 'category_name',
            'gender', 'description', 'main_image', 'additional_images',
            'base_price', 'formatted_price', 'is_active', 'is_in_stock',
            'variants', 'total_stock', 'variants_count',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'product_code', 'created_at', 'updated_at']
    
    def get_total_stock(self, obj):
        return obj.variants.aggregate(total=Sum('stock_quantity'))['total'] or 0
    
    def get_variants_count(self, obj):
        return obj.variants.count()
    
    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
        product = Product.objects.create(**validated_data)
        
        for variant_data in variants_data:
            ProductVariant.objects.create(product=product, **variant_data)
        
        return product
    
    def update(self, instance, validated_data):
        variants_data = validated_data.pop('variants', [])
        
        # Update product fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update variants (delete old, create new)
        instance.variants.all().delete()
        for variant_data in variants_data:
            ProductVariant.objects.create(product=instance, **variant_data)
        
        return instance


class ProductListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list view"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    total_stock = serializers.SerializerMethodField()
    variants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'product_code', 'name', 'category_name', 'gender',
            'base_price', 'is_active', 'is_in_stock', 'total_stock', 'variants_count'
        ]
    
    def get_total_stock(self, obj):
        return obj.variants.aggregate(total=Sum('stock_quantity'))['total'] or 0
    
    def get_variants_count(self, obj):
        return obj.variants.count()


class SchoolProductPriceSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    
    class Meta:
        model = SchoolProductPrice
        fields = ['id', 'product', 'product_name', 'school', 'school_name', 'price', 'created_at', 'updated_at']


# ============= EMPLOYEE TASK MANAGEMENT SERIALIZERS =============
# Add this at the end of your serializers.py file

from .models import Employee, Task, TaskProgress
from django.db.models import Sum, Count


# ============= EMPLOYEE SERIALIZERS =============

class EmployeeSerializer(serializers.ModelSerializer):
    """Complete Employee Serializer"""
    
    # Read-only fields for frontend
    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    designation_display = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_code', 'user', 'user_name', 'user_email',
            'designation', 'designation_display', 'phone', 'address',
            'joining_date', 'salary', 'is_active',
            'total_tasks', 'completed_tasks', 'pending_tasks', 'in_progress_tasks',
            'completion_rate', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'employee_code', 'created_at', 'updated_at']
    
    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else ''
    
    def get_user_email(self, obj):
        return obj.user.email if obj.user else ''
    
    def get_designation_display(self, obj):
        return dict(Employee.DESIGNATION_CHOICES).get(obj.designation, obj.designation)
    
    def get_completion_rate(self, obj):
        return obj.completion_rate
    
    def validate_phone(self, value):
        if value and len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits")
        return value


class EmployeeListSerializer(serializers.ModelSerializer):
    """Simplified Employee Serializer for list views"""
    
    user_name = serializers.SerializerMethodField()
    designation_display = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_code', 'user_name', 'designation', 'designation_display',
            'phone', 'is_active', 'total_tasks', 'completed_tasks',
            'pending_tasks', 'in_progress_tasks', 'completion_rate'
        ]
    
    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else ''
    
    def get_designation_display(self, obj):
        return dict(Employee.DESIGNATION_CHOICES).get(obj.designation, obj.designation)
    
    def get_completion_rate(self, obj):
        return obj.completion_rate


# ============= TASK PROGRESS SERIALIZER =============

class TaskProgressSerializer(serializers.ModelSerializer):
    """Task Progress Log Serializer"""
    
    updated_by_name = serializers.SerializerMethodField()
    formatted_created_at = serializers.SerializerMethodField()
    
    class Meta:
        model = TaskProgress
        fields = [
            'id', 'task', 'completed_quantity', 'remarks',
            'updated_by', 'updated_by_name', 'created_at', 'formatted_created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_updated_by_name(self, obj):
        return obj.updated_by.full_name if obj.updated_by else 'System'
    
    def get_formatted_created_at(self, obj):
        return obj.created_at.strftime('%d %b %Y, %I:%M %p') if obj.created_at else ''


# ============= TASK SERIALIZERS =============
# serializers.py - TaskSerializer (FIXED)

class TaskSerializer(serializers.ModelSerializer):
    """Complete Task Serializer"""
    
    # Read-only display fields
    task_type_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()
    
    # Related fields
    assigned_to_name = serializers.SerializerMethodField()
    assigned_by_name = serializers.SerializerMethodField()
    assigned_to_details = serializers.SerializerMethodField()
    
    # Calculated fields
    progress_percent = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    
    # Order reference details
    order_reference = serializers.SerializerMethodField()
    # ✅ INCLUDE THESE IN fields list - YAHI PROBLEM THI
    rm_order_detail = serializers.SerializerMethodField()  # ← YEH
    ms_order_detail = serializers.SerializerMethodField()  # ← YEH
    
    # Timestamps
    formatted_due_date = serializers.SerializerMethodField()
    formatted_completed_at = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'task_number', 'rm_order', 'ms_order', 'order_reference',
            'task_type', 'task_type_display', 'title', 'description',
            'assigned_to', 'assigned_to_name', 'assigned_to_details',
            'assigned_by', 'assigned_by_name',
            'total_quantity', 'completed_quantity', 'progress_percent',
            'start_date', 'due_date', 'formatted_due_date',
            'completed_at', 'formatted_completed_at',
            'status', 'status_display', 'priority', 'priority_display',
            'is_overdue', 'remarks',
            'rm_order_detail',    # ✅ ADD THIS
            'ms_order_detail',    # ✅ ADD THIS
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'task_number', 'created_at', 'updated_at', 'completed_at']
    
    def get_task_type_display(self, obj):
        return dict(Task.TASK_TYPE_CHOICES).get(obj.task_type, obj.task_type)
    
    def get_status_display(self, obj):
        return dict(Task.STATUS_CHOICES).get(obj.status, obj.status)
    
    def get_priority_display(self, obj):
        return dict(Task.PRIORITY_CHOICES).get(obj.priority, obj.priority)
    
    def get_assigned_to_name(self, obj):
        return obj.assigned_to.user.full_name if obj.assigned_to else ''
    
    def get_assigned_by_name(self, obj):
        return obj.assigned_by.full_name if obj.assigned_by else ''
    
    def get_assigned_to_details(self, obj):
        if obj.assigned_to:
            return {
                'id': obj.assigned_to.id,
                'employee_code': obj.assigned_to.employee_code,
                'name': obj.assigned_to.user.full_name,
                'designation': obj.assigned_to.designation,
                'designation_display': dict(Employee.DESIGNATION_CHOICES).get(obj.assigned_to.designation, '')
            }
        return None
    
    def get_progress_percent(self, obj):
        return obj.progress_percent
    
    def get_is_overdue(self, obj):
        return obj.is_overdue
    
    def get_order_reference(self, obj):
        if obj.rm_order:
            return {
                'type': 'RM',
                'order_id': obj.rm_order.order_id,
                'customer': obj.rm_order.customer.name if obj.rm_order.customer else ''
            }
        elif obj.ms_order:
            return {
                'type': 'MS',
                'order_id': obj.ms_order.order_id,
                'customer': obj.ms_order.customer.name if obj.ms_order.customer else ''
            }
        return None
    
    def get_rm_order_detail(self, obj):
        if obj.rm_order:
            from .serializers import RMOrderSerializer
            return RMOrderSerializer(obj.rm_order).data
        return None
    
    def get_ms_order_detail(self, obj):
        if obj.ms_order:
            from .serializers import MSOrderSerializer
            return MSOrderSerializer(obj.ms_order).data
        return None
    
    def get_formatted_due_date(self, obj):
        return obj.due_date.strftime('%d %b %Y') if obj.due_date else ''
    
    def get_formatted_completed_at(self, obj):
        return obj.completed_at.strftime('%d %b %Y, %I:%M %p') if obj.completed_at else ''


class TaskListSerializer(serializers.ModelSerializer):
    """Simplified Task Serializer for list views"""
    
    task_type_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    order_reference = serializers.SerializerMethodField()
    formatted_due_date = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'task_number', 'task_type', 'task_type_display',
            'title', 'assigned_to', 'assigned_to_name',
            'status', 'status_display', 'priority', 'priority_display',
            'total_quantity', 'completed_quantity', 'progress_percent',
            'due_date', 'formatted_due_date', 'is_overdue',
            'order_reference'
        ]
    
    def get_task_type_display(self, obj):
        return dict(Task.TASK_TYPE_CHOICES).get(obj.task_type, obj.task_type)
    
    def get_status_display(self, obj):
        return dict(Task.STATUS_CHOICES).get(obj.status, obj.status)
    
    def get_priority_display(self, obj):
        return dict(Task.PRIORITY_CHOICES).get(obj.priority, obj.priority)
    
    def get_assigned_to_name(self, obj):
        return obj.assigned_to.user.full_name if obj.assigned_to else ''
    
    def get_progress_percent(self, obj):
        return obj.progress_percent
    
    def get_is_overdue(self, obj):
        return obj.is_overdue
    
    def get_order_reference(self, obj):
        if obj.rm_order:
            return {'type': 'RM', 'order_id': obj.rm_order.order_id}
        elif obj.ms_order:
            return {'type': 'MS', 'order_id': obj.ms_order.order_id}
        return None
    
    def get_formatted_due_date(self, obj):
        return obj.due_date.strftime('%d %b %Y') if obj.due_date else ''


class CreateTaskSerializer(serializers.ModelSerializer):
    """Serializer for creating new tasks"""
    
    class Meta:
        model = Task
        fields = [
            'rm_order', 'ms_order', 'task_type', 'title', 'description',
            'assigned_to', 'total_quantity', 'due_date', 'priority'
        ]
    
    def validate(self, data):
        # Either rm_order or ms_order should be provided, not both
        if not data.get('rm_order') and not data.get('ms_order'):
            raise serializers.ValidationError("Either RM Order or MS Order is required")
        
        if data.get('rm_order') and data.get('ms_order'):
            raise serializers.ValidationError("Cannot assign to both RM and MS order")
        
        # Validate due date is not in past
        from django.utils import timezone
        if data.get('due_date') and data['due_date'] < timezone.now().date():
            raise serializers.ValidationError({"due_date": "Due date cannot be in the past"})
        
        # Validate total quantity
        if data.get('total_quantity', 0) <= 0:
            raise serializers.ValidationError({"total_quantity": "Quantity must be greater than 0"})
        
        return data


class UpdateTaskStatusSerializer(serializers.Serializer):
    """Serializer for updating task status"""
    
    status = serializers.ChoiceField(choices=Task.STATUS_CHOICES)
    remarks = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate_status(self, value):
        # Add custom validation if needed
        return value


class UpdateTaskProgressSerializer(serializers.Serializer):
    """Serializer for updating task progress"""
    
    completed_quantity = serializers.IntegerField(min_value=1)
    remarks = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate_completed_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Completed quantity must be greater than 0")
        return value


# ============= TASK STATS SERIALIZER =============

class TaskStatsSerializer(serializers.Serializer):
    """Serializer for task statistics"""
    
    total_tasks = serializers.IntegerField()
    pending = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    completed = serializers.IntegerField()
    rejected = serializers.IntegerField()
    overdue = serializers.IntegerField()
    completion_rate = serializers.FloatField()
    task_type_stats = serializers.DictField()
    employee_performance = serializers.ListField()


# ============= ORDER TASKS SERIALIZER =============

class OrderTasksSerializer(serializers.Serializer):
    """Serializer for tasks grouped by order"""
    
    order_id = serializers.CharField()
    order_type = serializers.CharField()
    tasks = TaskListSerializer(many=True)
    total_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    progress = serializers.FloatField()


# ============= EMPLOYEE STATS SERIALIZER =============

class EmployeeStatsSerializer(serializers.Serializer):
    """Serializer for employee statistics"""
    
    total_employees = serializers.IntegerField()
    designation_wise = serializers.DictField()
    current_workload = serializers.ListField()

# serializers.py - Add after Task serializers

# ============= NOTIFICATION SERIALIZERS =============
from .models import Notification
class NotificationSerializer(serializers.ModelSerializer):
    """Notification Serializer"""
    
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type', 'user',
            'order_id', 'order_type', 'task_id', 'is_read',
            'time_ago', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'time_ago']
    
    def get_time_ago(self, obj):
        return obj.time_ago


class NotificationListSerializer(serializers.ModelSerializer):
    """Simplified Notification Serializer for list view"""
    
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type',
            'order_id', 'is_read', 'time_ago', 'created_at'
        ]
    
    def get_time_ago(self, obj):
        return obj.time_ago