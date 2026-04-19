from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, full_name=None):  # ✅ FIX
        if not email:
            raise ValueError("Email required")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            full_name=full_name  # ✅ FIX
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, full_name=None):
        if not full_name:
            full_name = email.split("@")[0]  # 🔥 AUTO NAME

        user = self.create_user(email, password, full_name)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()
        return user

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)

    is_active = models.BooleanField(default=False)  # 🔥 IMPORTANT CHANGE
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.email
    

class Customer(models.Model):
    """
    Customer Model for managing client/customer information
    """
    # Basic Information
    name = models.CharField(max_length=255, verbose_name="Customer Name")
    phone = models.CharField(max_length=20, unique=True, verbose_name="Phone Number")
    email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="Email Address")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="City")
    
    # Order Statistics (calculated fields - can be updated via signals or manual updates)
    rm_orders_count = models.IntegerField(default=0, verbose_name="RM Orders Count")
    ms_orders_count = models.IntegerField(default=0, verbose_name="MS Orders Count")
    
    # Financial
    total_value = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total Value (₹)")
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_customers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    
    class Meta:
        db_table = 'customers'
        ordering = ['-created_at']
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
    
    def __str__(self):
        return f"{self.name} - {self.phone}"
    
    @property
    def formatted_total_value(self):
        """Return total value in Lakhs format"""
        if self.total_value >= 100000:
            return f"₹{self.total_value/100000:.1f}L"
        return f"₹{self.total_value/1000:.0f}K"
    
    # models.py - Fix Customer model's update_order_counts

def update_order_counts(self):
    """Update RM and MS order counts from related orders"""
    from .models import RMOrder, MSOrder
    
    # RM orders count
    self.rm_orders_count = RMOrder.objects.filter(
        customer=self, 
        is_active=True
    ).count()
    
    # MS orders count
    self.ms_orders_count = MSOrder.objects.filter(
        customer=self, 
        is_active=True
    ).count()
    
    # Total value from both
    from django.db.models import Sum
    rm_total = RMOrder.objects.filter(customer=self, is_active=True).aggregate(total=Sum('amount'))['total'] or 0
    ms_total = MSOrder.objects.filter(customer=self, is_active=True).aggregate(total=Sum('amount'))['total'] or 0
    
    self.total_value = rm_total + ms_total
    
    self.save(update_fields=['rm_orders_count', 'ms_orders_count', 'total_value'])


# models.py - Add this after Customer model

class RMOrder(models.Model):
    """
    RM Order Model - Ready Made Orders
    Customer foreign key ke saath
    """
    
    # Order Status Choices
    STATUS_CHOICES = [
        ('pending', '⏳ Pending'),
        ('approved', '👍 Approved'),
        ('ready', '🎯 Ready'),
        ('shipped', '🚚 Shipped'),
        ('delivered', '📦 Delivered'),
    ]
    
    CATEGORY_CHOICES = [
        ('School', 'School'),
        ('Corporate', 'Corporate'),
        ('Hospital', 'Hospital'),
        ('Security', 'Security'),
        ('Business & Corporate', 'Business & Corporate'),
        ('institutional', 'Institutional'),
        ('House keeping', 'House Keeping'),
        ('Medical', 'Medical'),
        ('Industrial', 'Industrial'),
        ('Multi Purpose', 'Multi Purpose'),
    ]
    
    # Basic Information
    order_id = models.CharField(max_length=50, unique=True, editable=False, verbose_name="Order ID")
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE, 
        related_name='rm_orders',
        verbose_name="Customer"
    )
    
    # Order Details
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='School', verbose_name="Category")
    order_date = models.DateField(auto_now_add=True, verbose_name="Order Date")
    delivery_date = models.DateField(null=True, blank=True, verbose_name="Delivery Date")
    ordered_by = models.CharField(max_length=255, blank=True, null=True, verbose_name="Order By")
    
    # Financial
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Amount (₹)")
    quantity = models.IntegerField(default=0, verbose_name="Quantity")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_rm_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    
    class Meta:
        db_table = 'rm_orders'
        ordering = ['-created_at']
        verbose_name = 'RM Order'
        verbose_name_plural = 'RM Orders'
    
    def __str__(self):
        return f"{self.order_id} - {self.customer.name} - {self.status}"
    
    def save(self, *args, **kwargs):
        """Auto-generate order ID and update customer stats"""
        if not self.order_id:
            # Generate Order ID: RM-YYYYMMDD-XXXX
            import datetime
            from django.utils import timezone
            
            today = timezone.now().strftime('%Y%m%d')
            last_order = RMOrder.objects.filter(order_id__startswith=f'RM-{today}').order_by('-order_id').first()
            
            if last_order:
                last_num = int(last_order.order_id.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.order_id = f'RM-{today}-{new_num:04d}'
        
        super().save(*args, **kwargs)
        
        # Update customer order counts and total value
        self.update_customer_stats()
    
    def update_customer_stats(self):
        """Update customer's order counts and total value"""
        if self.customer:
            # Update RM orders count
            self.customer.rm_orders_count = RMOrder.objects.filter(
                customer=self.customer, 
                is_active=True
            ).count()
            
            # Update total value
            from django.db.models import Sum
            total = RMOrder.objects.filter(
                customer=self.customer, 
                is_active=True
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            self.customer.total_value = total
            self.customer.save(update_fields=['rm_orders_count', 'total_value'])
    
    @property
    def formatted_amount(self):
        """Return formatted amount"""
        if self.amount >= 100000:
            return f"₹{self.amount/100000:.1f}L"
        elif self.amount >= 1000:
            return f"₹{self.amount/1000:.0f}K"
        return f"₹{self.amount}"
    
    @property
    def time_display(self):
        """Return time in HH:MM format"""
        return self.created_at.strftime('%H:%M')
    
    @property
    def order_date_display(self):
        """Return order date in DD/MM/YYYY format"""
        return self.order_date.strftime('%d/%m/%Y') if self.order_date else '-'
    
    @property
    def delivery_date_display(self):
        """Return delivery date in DD/MM/YYYY format"""
        return self.delivery_date.strftime('%d/%m/%Y') if self.delivery_date else '-'



    # models.py - Add this after RMOrder model

# models.py - RMOrderItem model (Find this and update)
# models.py - Update RMOrderItem model

# models.py - Update RMOrderItem model

class RMOrderItem(models.Model):
    """
    RM Order Item Model - Individual items in an RM order
    """
    
    GENDER_CHOICES = [
        ('Gents', '👨 Gents'),
        ('Ladies', '👩 Ladies'),
        ('Kids', '🧒 Kids'),
    ]
    
    SIZE_CHOICES = [
        ('XS', 'Extra Small'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', 'XX Large'),
        ('XXXL', 'XXX Large'),
        ('Custom', 'Custom Size'),
    ]
    
    # Relationships
    order = models.ForeignKey(RMOrder, on_delete=models.CASCADE, related_name='items')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True)
    
    # Item Details
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Gents', verbose_name="Gender")
    product_type = models.CharField(max_length=100, default='Uniform', verbose_name="Product Type")
    uniform_item = models.CharField(max_length=100, default='Shirt', verbose_name="Uniform Item")
    color = models.CharField(max_length=50, blank=True, null=True, verbose_name="Color")
    size = models.CharField(max_length=20, choices=SIZE_CHOICES, default='M', verbose_name="Size")
    quantity = models.IntegerField(default=1, verbose_name="Quantity")
    amount_per_piece = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Amount per Piece (₹)")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total Amount (₹)")
    
    # ✅ IMAGE FIELD - Add this
    reference_image = models.ImageField(upload_to='rm_items/', blank=True, null=True, verbose_name="Reference Image")
    
    # Stock tracking
    stock_available = models.BooleanField(default=True, verbose_name="Stock Available")
    stock_check_note = models.CharField(max_length=255, blank=True, null=True, verbose_name="Stock Check Note")
    
    # Additional
    special_notes = models.TextField(blank=True, null=True, verbose_name="Special Instructions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rm_order_items'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        """Auto-calculate total amount from quantity and amount_per_piece"""
        if self.amount_per_piece and self.quantity:
            self.amount = self.amount_per_piece * self.quantity
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.gender} - {self.uniform_item} ({self.size}) x{self.quantity} - ₹{self.amount_per_piece}/pc"
# models.py - Add this after RMOrder model

class MSOrder(models.Model):
    """
    MS Order Model - Measurement Orders (Made to Measure)
    Customer foreign key with separate measurements for Ladies & Gents
    """
    
    # Order Status Choices
    STATUS_CHOICES = [
        ('pending', '⏳ Pending'),
        ('approved', '👍 Approved'),
        ('In Cutting', '✂️ In Cutting'),
        ('In Stitching', '🪡 In Stitching'),
        ('qc', '✅ Quality Check'),
        ('ready', '🎯 Ready'),
        ('shipped', '🚚 Shipped'),
        ('delivered', '📦 Delivered'),
    ]
    
    CATEGORY_CHOICES = [
        ('School', 'School'),
        ('Corporate', 'Corporate'),
        ('Hospital', 'Hospital'),
        ('Security', 'Security'),
        ('Business & Corporate', 'Business & Corporate'),
        ('institutional', 'Institutional'),
        ('House keeping', 'House Keeping'),
        ('Medical', 'Medical'),
        ('Industrial', 'Industrial'),
        ('Multi Purpose', 'Multi Purpose'),
    ]
    
    GENDER_CHOICES = [
        ('Ladies', '👩 Ladies'),
        ('Gents', '👨 Gents'),
    ]
    
    # Basic Information
    order_id = models.CharField(max_length=50, unique=True, editable=False, verbose_name="Order ID")
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE, 
        related_name='ms_orders',
        verbose_name="Customer"
    )
    
    # Order Details
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Gents', verbose_name="Gender")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='School', verbose_name="Category")
    order_date = models.DateField(auto_now_add=True, verbose_name="Order Date")
    delivery_date = models.DateField(null=True, blank=True, verbose_name="Delivery Date")
    ordered_by = models.CharField(max_length=255, blank=True, null=True, verbose_name="Order By")
    tailor = models.CharField(max_length=255, blank=True, null=True, verbose_name="Tailor Name")
    
    # Financial
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Amount (₹)")
    quantity = models.IntegerField(default=0, verbose_name="Quantity")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    
    # ============= COMMON MEASUREMENTS (Both Ladies & Gents) =============
    chest = models.FloatField(null=True, blank=True, verbose_name="Chest (inches)")
    waist = models.FloatField(null=True, blank=True, verbose_name="Waist (inches)")
    hip = models.FloatField(null=True, blank=True, verbose_name="Hip (inches)")
    shoulder = models.FloatField(null=True, blank=True, verbose_name="Shoulder (inches)")
    length = models.FloatField(null=True, blank=True, verbose_name="Length (inches)")
    sleeve_length = models.FloatField(null=True, blank=True, verbose_name="Sleeve Length (inches)")
    armhole = models.FloatField(null=True, blank=True, verbose_name="Armhole (inches)")
    neck = models.FloatField(null=True, blank=True, verbose_name="Neck (inches)")
    
    # ============= GENTS ONLY MEASUREMENTS =============
    collar = models.FloatField(null=True, blank=True, verbose_name="Collar (inches)")
    bicep = models.FloatField(null=True, blank=True, verbose_name="Bicep (inches)")
    elbow = models.FloatField(null=True, blank=True, verbose_name="Elbow (inches)")
    cuff = models.FloatField(null=True, blank=True, verbose_name="Cuff (inches)")
    thigh = models.FloatField(null=True, blank=True, verbose_name="Thigh (inches)")
    knee = models.FloatField(null=True, blank=True, verbose_name="Knee (inches)")
    bottom = models.FloatField(null=True, blank=True, verbose_name="Bottom (inches)")
    rise = models.FloatField(null=True, blank=True, verbose_name="Rise (inches)")
    inseam = models.FloatField(null=True, blank=True, verbose_name="Inseam (inches)")
    
    # ============= LADIES ONLY MEASUREMENTS =============
    bust = models.FloatField(null=True, blank=True, verbose_name="Bust (inches)")
    under_bust = models.FloatField(null=True, blank=True, verbose_name="Under Bust (inches)")
    waist_hip = models.FloatField(null=True, blank=True, verbose_name="Waist to Hip (inches)")
    shoulder_to_waist = models.FloatField(null=True, blank=True, verbose_name="Shoulder to Waist (inches)")
    waist_to_knee = models.FloatField(null=True, blank=True, verbose_name="Waist to Knee (inches)")
    waist_to_floor = models.FloatField(null=True, blank=True, verbose_name="Waist to Floor (inches)")
    arm_length = models.FloatField(null=True, blank=True, verbose_name="Arm Length (inches)")
    wrist = models.FloatField(null=True, blank=True, verbose_name="Wrist (inches)")
    front_neck_depth = models.FloatField(null=True, blank=True, verbose_name="Front Neck Depth (inches)")
    back_neck_depth = models.FloatField(null=True, blank=True, verbose_name="Back Neck Depth (inches)")
    dart_length = models.FloatField(null=True, blank=True, verbose_name="Dart Length (inches)")
    dart_depth = models.FloatField(null=True, blank=True, verbose_name="Dart Depth (inches)")
    
    # Additional Notes
    special_notes = models.TextField(blank=True, null=True, verbose_name="Special Instructions")
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_ms_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    
    class Meta:
        db_table = 'ms_orders'
        ordering = ['-created_at']
        verbose_name = 'MS Order'
        verbose_name_plural = 'MS Orders'
    
    def __str__(self):
        return f"{self.order_id} - {self.customer.name} - {self.gender} - {self.status}"
    
    def save(self, *args, **kwargs):
        """Auto-generate order ID and update customer stats"""
        if not self.order_id:
            import datetime
            from django.utils import timezone
            
            today = timezone.now().strftime('%Y%m%d')
            last_order = MSOrder.objects.filter(order_id__startswith=f'MS-{today}').order_by('-order_id').first()
            
            if last_order:
                last_num = int(last_order.order_id.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.order_id = f'MS-{today}-{new_num:04d}'
        
        super().save(*args, **kwargs)
        
        # Update customer stats
        self.update_customer_stats()
    
    def update_customer_stats(self):
        """Update customer's MS order counts and total value"""
        if self.customer:
            # Update MS orders count
            self.customer.ms_orders_count = MSOrder.objects.filter(
                customer=self.customer, 
                is_active=True
            ).count()
            
            # Update total value (combine RM + MS)
            from django.db.models import Sum
            
            rm_total = RMOrder.objects.filter(
                customer=self.customer, 
                is_active=True
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            ms_total = MSOrder.objects.filter(
                customer=self.customer, 
                is_active=True
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            self.customer.total_value = rm_total + ms_total
            self.customer.save(update_fields=['ms_orders_count', 'total_value'])
    
    @property
    def formatted_amount(self):
        """Return formatted amount"""
        if self.amount >= 100000:
            return f"₹{self.amount/100000:.1f}L"
        elif self.amount >= 1000:
            return f"₹{self.amount/1000:.0f}K"
        return f"₹{self.amount}"
    
    @property
    def time_display(self):
        """Return time in HH:MM format"""
        return self.created_at.strftime('%H:%M')
    
    @property
    def order_date_display(self):
        """Return order date in DD/MM/YYYY format"""
        return self.order_date.strftime('%d/%m/%Y') if self.order_date else '-'
    
    @property
    def delivery_date_display(self):
        """Return delivery date in DD/MM/YYYY format"""
        return self.delivery_date.strftime('%d/%m/%Y') if self.delivery_date else '-'
    
    @property
    def is_delayed(self):
        """Check if order is delayed"""
        from django.utils import timezone
        if self.delivery_date and self.status != 'delivered':
            return self.delivery_date < timezone.now().date()
        return False
    

# models.py - Add this after MSOrder model

# models.py - Replace MSOrderItem with this
# models.py - MSOrderItem (Final Version)

class MSOrderItem(models.Model):
    """
    MS Order Item Model - Each item represents a PERSON
    """
    
    GENDER_CHOICES = [
        ('Ladies', '👩 Ladies'),
        ('Gents', '👨 Gents'),
    ]
    
    # Relationships
    order = models.ForeignKey(MSOrder, on_delete=models.CASCADE, related_name='items')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True)
    
    # Person Details (NO product_type)
    person_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Person Name")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Gents')
    quantity = models.IntegerField(default=1)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Upper Body Measurements
    chest = models.FloatField(null=True, blank=True)
    shoulder = models.FloatField(null=True, blank=True)
    sleeve_length = models.FloatField(null=True, blank=True)
    armhole = models.FloatField(null=True, blank=True)
    neck = models.FloatField(null=True, blank=True)
    length = models.FloatField(null=True, blank=True)
    collar = models.FloatField(null=True, blank=True)
    bicep = models.FloatField(null=True, blank=True)
    elbow = models.FloatField(null=True, blank=True)
    cuff = models.FloatField(null=True, blank=True)
    bust = models.FloatField(null=True, blank=True)
    under_bust = models.FloatField(null=True, blank=True)
    arm_length = models.FloatField(null=True, blank=True)
    wrist = models.FloatField(null=True, blank=True)
    front_neck_depth = models.FloatField(null=True, blank=True)
    back_neck_depth = models.FloatField(null=True, blank=True)
    dart_length = models.FloatField(null=True, blank=True)
    dart_depth = models.FloatField(null=True, blank=True)
    
    # Lower Body Measurements
    waist = models.FloatField(null=True, blank=True)
    hip = models.FloatField(null=True, blank=True)
    thigh = models.FloatField(null=True, blank=True)
    knee = models.FloatField(null=True, blank=True)
    bottom = models.FloatField(null=True, blank=True)
    rise = models.FloatField(null=True, blank=True)
    inseam = models.FloatField(null=True, blank=True)
    waist_hip = models.FloatField(null=True, blank=True)
    shoulder_to_waist = models.FloatField(null=True, blank=True)
    waist_to_knee = models.FloatField(null=True, blank=True)
    waist_to_floor = models.FloatField(null=True, blank=True)
    
    # Additional
    special_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ms_order_items'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.person_name or 'Person'} - {self.gender}"



# models.py - Add these models for Quotation Management

class Quotation(models.Model):
    """
    Quotation Model - Main quotation table
    """
    
    # Status Choices
    STATUS_CHOICES = [
        ('Draft', '📄 Draft'),
        ('Sent', '📨 Sent'),
        ('Approved', '✅ Approved'),
        ('Rejected', '❌ Rejected'),
        ('Converted', '🔄 Converted'),
    ]
    
    # Basic Information
    quotation_no = models.CharField(max_length=50, unique=True, editable=False, verbose_name="Quotation Number")
    date = models.DateField(auto_now_add=True, verbose_name="Quotation Date")
    valid_till = models.DateField(null=True, blank=True, verbose_name="Valid Till")
    
    # Customer Information (Foreign Key to Customer model)
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE, 
        related_name='quotations',
        verbose_name="Customer"
    )
    
    # Store customer details at time of quotation (for historical record)
    customer_name = models.CharField(max_length=255, verbose_name="Customer Name")
    customer_phone = models.CharField(max_length=20, verbose_name="Phone Number")
    customer_email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="Email")
    customer_address = models.TextField(blank=True, null=True, verbose_name="Address")
    
    # Quotation Details
    subject = models.CharField(max_length=500, default="Quotation for Uniform Supply", verbose_name="Subject")
    message = models.TextField(blank=True, null=True, verbose_name="Message/Body")
    
    # Financial Information
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Subtotal (₹)")
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Discount %")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Discount Amount (₹)")
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18, verbose_name="GST %")
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="GST Amount (₹)")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total Amount (₹)")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft', verbose_name="Status")
    
    # Terms & Conditions
    payment_terms = models.TextField(default="50% advance, 50% before dispatch", verbose_name="Payment Terms")
    delivery_time = models.CharField(max_length=255, default="15-20 working days", verbose_name="Delivery Time")
    warranty = models.CharField(max_length=255, default="6 months against manufacturing defects", verbose_name="Warranty")
    validity = models.CharField(max_length=100, default="30 days", verbose_name="Validity")
    notes = models.TextField(blank=True, null=True, verbose_name="Additional Notes")
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_quotations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    
    class Meta:
        db_table = 'quotations'
        ordering = ['-created_at']
        verbose_name = 'Quotation'
        verbose_name_plural = 'Quotations'
    
    def __str__(self):
        return f"{self.quotation_no} - {self.customer_name} - {self.status}"
    
    def save(self, *args, **kwargs):
        """Auto-generate quotation number"""
        if not self.quotation_no:
            from django.utils import timezone
            today = timezone.now().strftime('%Y%m%d')
            last_quotation = Quotation.objects.filter(
                quotation_no__startswith=f'QT-{today}'
            ).order_by('-quotation_no').first()
            
            if last_quotation:
                last_num = int(last_quotation.quotation_no.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.quotation_no = f'QT-{today}-{new_num:04d}'
        
        super().save(*args, **kwargs)
    
    @property
    def formatted_total(self):
        """Return formatted total amount"""
        if self.total_amount >= 100000:
            return f"₹{self.total_amount/100000:.1f}L"
        elif self.total_amount >= 1000:
            return f"₹{self.total_amount/1000:.0f}K"
        return f"₹{self.total_amount}"

# Quotation Table
# Quotation Table
class QuotationItem(models.Model):
    """
    Quotation Item Model - Individual items in a quotation
    """
    
    GENDER_CHOICES = [
        ('Gents', '👨 Gents'),
        ('Ladies', '👩 Ladies'),
        ('Kids', '🧒 Kids'),
    ]
    
    SIZE_CHOICES = [
        ('XS', 'XS'), ('S', 'S'), ('M', 'M'), ('L', 'L'),
        ('XL', 'XL'), ('XXL', 'XXL'), ('XXXL', 'XXXL'), ('Custom', 'Custom'),
    ]
    
    # Relationships
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    
    # Item Details
    product_name = models.CharField(max_length=255, verbose_name="Product Name")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Gents', verbose_name="Gender")
    size = models.CharField(max_length=20, choices=SIZE_CHOICES, default='M', verbose_name="Size")
    quantity = models.IntegerField(default=1, verbose_name="Quantity")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Unit Price (₹)")
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Discount %")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Amount (₹)")
    
    # Additional
    notes = models.CharField(max_length=255, blank=True, null=True, verbose_name="Item Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'quotation_items'
        ordering = ['id']
    
    def save(self, *args, **kwargs):
        """Auto-calculate amount from quantity, unit_price, and discount"""
        if self.quantity and self.unit_price:
            from decimal import Decimal
            
            # ✅ Convert to Decimal properly
            qty = Decimal(str(self.quantity))
            price = Decimal(str(self.unit_price))
            discount_percent = Decimal(str(self.discount_percent))
            
            subtotal = qty * price
            discount = subtotal * (discount_percent / Decimal('100'))
            self.amount = subtotal - discount
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.product_name} - {self.quantity} x {self.unit_price}"


# ============= VENDOR MANAGEMENT MODELS =============

class VendorCategory(models.Model):
    """Vendor Category - Fabric, Accessories, Thread, etc."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vendor_categories'
        verbose_name = 'Vendor Category'
        verbose_name_plural = 'Vendor Categories'
    
    def __str__(self):
        return self.name


class Vendor(models.Model):
    """Vendor Model for managing suppliers"""
    
    VENDOR_TYPE_CHOICES = [
        ('fabric', '🧵 Fabric Supplier'),
        ('accessories', '🔘 Accessories Supplier'),
        ('thread', '🪡 Thread Supplier'),
        ('packaging', '📦 Packaging Supplier'),
        ('machinery', '⚙️ Machinery Supplier'),
        ('other', '📌 Other'),
    ]
    
    # Basic Information
    vendor_code = models.CharField(max_length=50, unique=True, editable=False)
    name = models.CharField(max_length=255)
    category = models.ForeignKey(VendorCategory, on_delete=models.SET_NULL, null=True, related_name='vendors')
    vendor_type = models.CharField(max_length=20, choices=VENDOR_TYPE_CHOICES, default='other')
    
    # Contact Details
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    # Address
    address_line1 = models.TextField()
    address_line2 = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default='India')
    
    # Business Details
    gst_number = models.CharField(max_length=50, blank=True, null=True)
    pan_number = models.CharField(max_length=50, blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Payment Terms
    payment_terms = models.CharField(max_length=255, default='30 days')
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Statistics
    total_purchases = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_orders = models.IntegerField(default=0)
    last_purchase_date = models.DateField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    rating = models.IntegerField(default=3, choices=[(1, '⭐'), (2, '⭐⭐'), (3, '⭐⭐⭐'), (4, '⭐⭐⭐⭐'), (5, '⭐⭐⭐⭐⭐')])
    
    # Metadata
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_vendors')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vendors'
        ordering = ['-created_at']
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'
    
    def __str__(self):
        return f"{self.name} - {self.phone}"
    
    def save(self, *args, **kwargs):
        if not self.vendor_code:
            from django.utils import timezone
            today = timezone.now().strftime('%Y%m%d')
            last_vendor = Vendor.objects.filter(
                vendor_code__startswith=f'VEN-{today}'
            ).order_by('-vendor_code').first()
            
            if last_vendor:
                last_num = int(last_vendor.vendor_code.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.vendor_code = f'VEN-{today}-{new_num:04d}'
        
        super().save(*args, **kwargs)
    
    @property
    def full_address(self):
        address = self.address_line1
        if self.address_line2:
            address += f", {self.address_line2}"
        address += f", {self.city}, {self.state} - {self.pincode}"
        return address


class PurchaseOrder(models.Model):
    """Purchase Order Model"""
    
    STATUS_CHOICES = [
        ('draft', '📄 Draft'),
        ('ordered', '📨 Ordered'),
        ('partial', '📦 Partially Received'),
        ('received', '✅ Fully Received'),
        ('cancelled', '❌ Cancelled'),
    ]
    
    po_number = models.CharField(max_length=50, unique=True, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='purchase_orders')
    order_date = models.DateField(auto_now_add=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_pos')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'purchase_orders'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.po_number} - {self.vendor.name}"
    
    def save(self, *args, **kwargs):
        if not self.po_number:
            from django.utils import timezone
            today = timezone.now().strftime('%Y%m%d')
            last_po = PurchaseOrder.objects.filter(
                po_number__startswith=f'PO-{today}'
            ).order_by('-po_number').first()
            
            if last_po:
                last_num = int(last_po.po_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.po_number = f'PO-{today}-{new_num:04d}'
        
        super().save(*args, **kwargs)


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    received_quantity = models.IntegerField(default=0)
    notes = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = 'purchase_order_items'
    
    def save(self, *args, **kwargs):
        from decimal import Decimal
        # ✅ Convert to Decimal properly
        qty = Decimal(str(self.quantity))
        price = Decimal(str(self.unit_price))
        self.total_price = qty * price
        super().save(*args, **kwargs)


# ============= PRODUCT CATALOG MODELS =============

class ProductCategory(models.Model):
    """Product categories like Shirt, Pant, Blazer, etc."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)  # For UI
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_categories'
        ordering = ['name']
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Categories'
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Main Product Model"""
    
    GENDER_CHOICES = [
        ('Gents', '👨 Gents'),
        ('Ladies', '👩 Ladies'),
        ('Kids', '🧒 Kids'),
        ('Unisex', '👥 Unisex'),
    ]
    
    # Basic Information
    product_code = models.CharField(max_length=50, unique=True, editable=False)
    name = models.CharField(max_length=255)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='products')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Unisex')
    description = models.TextField(blank=True, null=True)
    
    # Images
    main_image = models.ImageField(upload_to='products/', blank=True, null=True)
    additional_images = models.JSONField(default=list, blank=True)  # List of image URLs
    
    # Pricing
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_in_stock = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
    
    def __str__(self):
        return f"{self.product_code} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.product_code:
            from django.utils import timezone
            import random
            # Generate unique product code: PRD-YYYYMMDD-XXXX
            today = timezone.now().strftime('%Y%m%d')
            last_product = Product.objects.filter(
                product_code__startswith=f'PRD-{today}'
            ).order_by('-product_code').first()
            
            if last_product:
                last_num = int(last_product.product_code.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.product_code = f'PRD-{today}-{new_num:04d}'
        
        super().save(*args, **kwargs)
    
    @property
    def formatted_price(self):
        return f"₹{self.base_price:,.2f}"


class ProductVariant(models.Model):
    """Product variants like Size, Color, Fabric"""
    
    SIZE_CHOICES = [
        ('XS', 'XS'), ('S', 'S'), ('M', 'M'), ('L', 'L'),
        ('XL', 'XL'), ('XXL', 'XXL'), ('XXXL', 'XXXL'), ('Custom', 'Custom'),
    ]
    
    COLOR_CHOICES = [
        ('White', '⚪ White'), ('Black', '⚫ Black'), ('Blue', '🔵 Blue'),
        ('Red', '🔴 Red'), ('Green', '🟢 Green'), ('Yellow', '🟡 Yellow'),
        ('Maroon', '🔴 Maroon'), ('Grey', '⬜ Grey'), ('Navy', '🔵 Navy'),
        ('Other', '🎨 Other'),
    ]
    
    FABRIC_CHOICES = [
        ('Cotton', 'Cotton'), ('Polyester', 'Polyester'), ('Linen', 'Linen'),
        ('Silk', 'Silk'), ('Wool', 'Wool'), ('Velvet', 'Velvet'),
        ('Denim', 'Denim'), ('Other', 'Other'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=10, choices=SIZE_CHOICES, default='M')
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, default='White')
    fabric = models.CharField(max_length=20, choices=FABRIC_CHOICES, default='Cotton')
    
    # Pricing (can override base price)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Stock
    stock_quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10)
    
    # Additional
    sku = models.CharField(max_length=100, blank=True, null=True)  # Unique SKU for variant
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'product_variants'
        unique_together = ['product', 'size', 'color', 'fabric']
    
    def __str__(self):
        return f"{self.product.name} - {self.size}/{self.color}/{self.fabric}"
    
    @property
    def effective_price(self):
        return self.price if self.price else self.product.base_price


class SchoolProductPrice(models.Model):
    """School/Client specific pricing for products"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='school_prices')
    school = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='product_prices')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'school_product_prices'
        unique_together = ['product', 'school']
    
    def __str__(self):
        return f"{self.product.name} - {self.school.name}: ₹{self.price}"


# backend/api/models/task_models.py
class Employee(models.Model):
    """Employee Model - Staff members who get tasks assigned"""
    
    DESIGNATION_CHOICES = [
        ('cutter', '✂️ Cutter'),
        ('stitcher', '🪡 Stitcher'),
        ('finisher', '✨ Finisher'),
        ('packer', '📦 Packer'),
        ('supervisor', '👔 Supervisor'),
        ('tailor', '👕 Tailor'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    employee_code = models.CharField(max_length=50, unique=True, editable=False)
    designation = models.CharField(max_length=20, choices=DESIGNATION_CHOICES)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    joining_date = models.DateField(auto_now_add=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    
    # Statistics
    total_tasks = models.IntegerField(default=0)
    completed_tasks = models.IntegerField(default=0)
    pending_tasks = models.IntegerField(default=0)
    in_progress_tasks = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'employees'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.get_designation_display()}"
    
    def save(self, *args, **kwargs):
        if not self.employee_code:
            from django.utils import timezone
            today = timezone.now().strftime('%Y%m%d')
            last_emp = Employee.objects.filter(
                employee_code__startswith=f'EMP-{today}'
            ).order_by('-employee_code').first()
            
            if last_emp:
                last_num = int(last_emp.employee_code.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.employee_code = f'EMP-{today}-{new_num:04d}'
        
        super().save(*args, **kwargs)
    
    @property
    def completion_rate(self):
        if self.total_tasks == 0:
            return 0
        return round((self.completed_tasks / self.total_tasks) * 100, 1)


class Task(models.Model):
    """Task Model - Tasks created from Orders"""
    
    TASK_TYPE_CHOICES = [
        ('cutting', '✂️ Cutting'),
        ('stitching', '🪡 Stitching'),
        ('finishing', '✨ Finishing'),
        ('packing', '📦 Packing'),
        ('qc', '✅ Quality Check'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '⏳ Pending'),
        ('in_progress', '🔄 In Progress'),
        ('completed', '✅ Completed'),
        ('rejected', '❌ Rejected'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', '🟢 Low'),
        ('medium', '🟡 Medium'),
        ('high', '🔴 High'),
        ('urgent', '⚠️ Urgent'),
    ]
    
    # Order Reference (either RM or MS order)
    rm_order = models.ForeignKey(RMOrder, on_delete=models.CASCADE, null=True, blank=True, related_name='tasks')
    ms_order = models.ForeignKey(MSOrder, on_delete=models.CASCADE, null=True, blank=True, related_name='tasks')
    
    # Task Details
    task_number = models.CharField(max_length=50, unique=True, editable=False)
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Assignment
    assigned_to = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='tasks')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_tasks')
    
    # Quantity tracking
    total_quantity = models.IntegerField(default=1)
    completed_quantity = models.IntegerField(default=0)
    
    # Timeline
    start_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Status & Priority
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Additional
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tasks'
        ordering = ['-priority', 'due_date', '-created_at']
    
    def __str__(self):
        order_ref = self.rm_order.order_id if self.rm_order else (self.ms_order.order_id if self.ms_order else 'N/A')
        return f"{self.task_number} - {self.get_task_type_display()} - {order_ref}"
    
    def save(self, *args, **kwargs):
        if not self.task_number:
            from django.utils import timezone
            today = timezone.now().strftime('%Y%m%d')
            last_task = Task.objects.filter(
                task_number__startswith=f'TASK-{today}'
            ).order_by('-task_number').first()
            
            if last_task:
                last_num = int(last_task.task_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.task_number = f'TASK-{today}-{new_num:04d}'
        
        super().save(*args, **kwargs)
    
    @property
    def progress_percent(self):
        if self.total_quantity == 0:
            return 0
        return round((self.completed_quantity / self.total_quantity) * 100, 1)
    
    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.due_date < timezone.now().date() and self.status != 'completed'
    
    @property
    def order_reference(self):
        if self.rm_order:
            return {
                'type': 'RM',
                'order_id': self.rm_order.order_id,
                'customer': self.rm_order.customer.name
            }
        elif self.ms_order:
            return {
                'type': 'MS',
                'order_id': self.ms_order.order_id,
                'customer': self.ms_order.customer.name
            }
        return None


class TaskProgress(models.Model):
    """Task Progress Log - Track progress updates"""
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='progress_logs')
    completed_quantity = models.IntegerField()
    remarks = models.TextField(blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'task_progress_logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.task.task_number} - +{self.completed_quantity}"


# models.py - Add this after Task model

class Notification(models.Model):
    """
    Notification Model for system notifications
    """
    
    NOTIFICATION_TYPES = [
        ('order_ready', 'Order Ready'),
        ('order_delivered', 'Order Delivered'),
        ('order_delayed', 'Order Delayed'),
        ('task_updated', 'Task Updated'),
        ('system', 'System Notification'),
    ]
    
    # Basic Info
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='system')
    
    # Related Objects
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    order_id = models.CharField(max_length=50, null=True, blank=True)
    order_type = models.CharField(max_length=10, null=True, blank=True)  # RM or MS
    task_id = models.IntegerField(null=True, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        return f"{self.title} - {self.user.email if self.user else 'System'}"
    
    @property
    def time_ago(self):
        from django.utils import timezone
        diff = timezone.now() - self.created_at
        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        
        if days > 0:
            return f"{days} day{'s' if days > 1 else ''} ago"
        elif hours > 0:
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif minutes > 0:
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"