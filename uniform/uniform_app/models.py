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