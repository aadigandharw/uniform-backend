from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegisterSerializer, LoginSerializer, CustomerSerializer ,MSOrderSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User, Customer , MSOrder
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum

# ============= AUTH VIEWS =============

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"msg": "User created"}, status=201)
        return Response(serializer.errors, status=400)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        user = User.objects.filter(email=email).first()

        if not user:
            return Response({"error": "User not found"}, status=400)

        if not user.is_active:
            return Response({"error": "Wait for admin approval"}, status=403)

        if not user.check_password(password):
            return Response({"error": "Invalid credentials"}, status=400)

        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Login successful",
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        })


class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.all().order_by('-id')
        data = []
        for u in users:
            data.append({
                "id": u.id,
                "name": u.full_name,
                "email": u.email,
                "status": "present" if u.is_active else "absent",
                "role": "User",
                "dept": "App User",
                "phone": "N/A",
                "sal": 0,
                "join": "New",
                "jobs": 0
            })
        return Response(data)


class ApproveUserView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):
        if not request.user.is_staff:
            return Response({"error": "Only admin can approve users"}, status=403)
        user = get_object_or_404(User, id=id)
        user.is_active = True
        user.save()
        return Response({"msg": "User approved successfully"})


class UpdateUserView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):
        if not request.user.is_staff:
            return Response({"error": "Only admin can edit users"}, status=403)
        user = get_object_or_404(User, id=id)
        user.full_name = request.data.get("name", user.full_name)
        user.save()
        return Response({"msg": "User updated successfully"})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "id": request.user.id,
            "email": request.user.email,
            "full_name": request.user.full_name,
            "is_staff": request.user.is_staff,
            "is_active": request.user.is_active
        })


# ✅ TOGGLE USER STATUS (ADD THIS - MISSING THA)
class ToggleUserStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):
        if not request.user.is_staff:
            return Response({"error": "Only admin can change user status"}, status=403)

        user = get_object_or_404(User, id=id)
        
        if user.id == request.user.id:
            return Response({"error": "You cannot change your own status"}, status=400)

        is_active = request.data.get('is_active')
        
        if is_active is None:
            return Response({"error": "is_active field is required"}, status=400)

        user.is_active = is_active
        user.save()

        status_text = "activated" if is_active else "deactivated"
        
        return Response({
            "msg": f"User {status_text} successfully",
            "is_active": user.is_active,
            "user_id": user.id,
            "user_name": user.full_name
        })


# ============= CUSTOMER VIEWS =============

class CustomerListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Customer.objects.filter(is_active=True)
        
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(phone__icontains=search) |
                Q(city__icontains=search) |
                Q(email__icontains=search)
            )
        
        serializer = CustomerSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CustomerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk, is_active=True)
        serializer = CustomerSerializer(customer)
        return Response(serializer.data)

    def put(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        serializer = CustomerSerializer(customer, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        serializer = CustomerSerializer(customer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        customer.is_active = False
        customer.save()
        return Response({
            "message": "Customer deleted successfully",
            "customer_id": customer.id,
            "customer_name": customer.name
        }, status=status.HTTP_200_OK)


class CustomerStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_customers = Customer.objects.filter(is_active=True).count()
        total_value = Customer.objects.filter(is_active=True).aggregate(
            total=Sum('total_value')
        )['total'] or 0
        
        top_customers = Customer.objects.filter(is_active=True).order_by('-total_value')[:5]
        top_customers_data = CustomerSerializer(top_customers, many=True).data
        
        if total_value >= 100000:
            formatted_value = f"₹{total_value/100000:.1f}L"
        else:
            formatted_value = f"₹{total_value/1000:.0f}K"
        
        return Response({
            "total_customers": total_customers,
            "total_value": total_value,
            "formatted_total_value": formatted_value,
            "top_customers": top_customers_data
        })


class CustomerToggleStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        customer.is_active = not customer.is_active
        customer.save()
        status_text = "activated" if customer.is_active else "deactivated"
        return Response({
            "message": f"Customer {status_text} successfully",
            "is_active": customer.is_active,
            "customer_id": customer.id,
            "customer_name": customer.name
        })


class CustomerOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        from .models import RMOrder
        from .serializers import RMOrderSerializer
        
        orders = RMOrder.objects.filter(customer=customer).order_by('-created_at')
        serializer = RMOrderSerializer(orders, many=True)
        
        return Response({
            "customer": CustomerSerializer(customer).data,
            "orders": serializer.data,
            "total_orders": orders.count()
        })
    

# views.py - Add RMOrder views

from .models import RMOrder
from .serializers import RMOrderSerializer

# views.py - Fix RMOrderListView POST method
# views.py - Complete RMOrderListView

class RMOrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all active RM orders with filters"""
        queryset = RMOrder.objects.filter(is_active=True)
        
        # Filter by status
        status = request.query_params.get('status', None)
        if status and status != 'all':
            queryset = queryset.filter(status=status)
        
        # Search functionality
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(order_id__icontains=search) |
                Q(customer__name__icontains=search) |
                Q(category__icontains=search)
            )
        
        serializer = RMOrderSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create new RM order"""
        print("=" * 50)
        print("RECEIVED DATA:", request.data)
        print("=" * 50)
        
        # Extract data from request
        data = request.data
        
        # Prepare data for serializer
        serializer_data = {
            'customer_id': data.get('customer_id'),
            'category': data.get('category'),
            'order_date': data.get('order_date'),
            'delivery_date': data.get('delivery_date'),
            'ordered_by': data.get('ordered_by'),
            'amount': data.get('amount'),
            'quantity': data.get('quantity', 0),
            'status': data.get('status', 'pending')
        }
        
        print("PREPARED DATA:", serializer_data)
        
        serializer = RMOrderSerializer(data=serializer_data)
        
        if serializer.is_valid():
            order = serializer.save(created_by=request.user)
            print("ORDER CREATED:", order.order_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        print("SERIALIZER ERRORS:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# views.py - RMOrderDetailView ko aise change karo

class RMOrderDetailView(APIView):
    """GET, PUT, PATCH, DELETE single RM order"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(RMOrder, pk=pk, is_active=True)
        serializer = RMOrderSerializer(order)
        return Response(serializer.data)

    def put(self, request, pk):
        """Full update of RM order - Map frontend fields to backend fields"""
        order = get_object_or_404(RMOrder, pk=pk)
        
        print("=" * 50)
        print("RAW PUT DATA:", request.data)
        print("=" * 50)
        
        data = request.data
        
        # 🔥 Map frontend field names to backend field names
        serializer_data = {
            'customer_id': data.get('customer_id', order.customer.id if order.customer else None),
            'category': data.get('cat', data.get('category', order.category)),
            'order_date': data.get('orderDate', data.get('order_date', str(order.order_date))),
            'delivery_date': data.get('deliveryDate', data.get('delivery_date', str(order.delivery_date) if order.delivery_date else None)),
            'ordered_by': data.get('orderBy', data.get('ordered_by', order.ordered_by)),
            'amount': data.get('amt', data.get('amount', float(order.amount))),
            'quantity': data.get('qty', data.get('quantity', order.quantity)),
            'status': data.get('status', order.status)
        }
        
        print("MAPPED DATA:", serializer_data)
        
        serializer = RMOrderSerializer(order, data=serializer_data)
        
        if serializer.is_valid():
            serializer.save()
            print("ORDER UPDATED SUCCESSFULLY")
            return Response(serializer.data)
        
        print("SERIALIZER ERRORS:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        """Partial update of RM order - Map frontend fields to backend fields"""
        order = get_object_or_404(RMOrder, pk=pk)
        
        print("=" * 50)
        print("RAW PATCH DATA:", request.data)
        print("=" * 50)
        
        data = request.data
        serializer_data = {}
        
        # 🔥 Map frontend field names to backend field names
        if 'customer_id' in data:
            serializer_data['customer_id'] = data['customer_id']
        elif 'cust' in data and order.customer:
            try:
                customer = Customer.objects.get(name=data['cust'], is_active=True)
                serializer_data['customer_id'] = customer.id
            except Customer.DoesNotExist:
                pass
        
        if 'cat' in data:
            serializer_data['category'] = data['cat']
        elif 'category' in data:
            serializer_data['category'] = data['category']
        
        if 'orderDate' in data:
            serializer_data['order_date'] = data['orderDate']
        elif 'order_date' in data:
            serializer_data['order_date'] = data['order_date']
        
        if 'deliveryDate' in data:
            serializer_data['delivery_date'] = data['deliveryDate']
        elif 'delivery_date' in data:
            serializer_data['delivery_date'] = data['delivery_date']
        
        if 'orderBy' in data:
            serializer_data['ordered_by'] = data['orderBy']
        elif 'ordered_by' in data:
            serializer_data['ordered_by'] = data['ordered_by']
        
        if 'amt' in data:
            serializer_data['amount'] = data['amt']
        elif 'amount' in data:
            serializer_data['amount'] = data['amount']
        
        if 'qty' in data:
            serializer_data['quantity'] = data['qty']
        elif 'quantity' in data:
            serializer_data['quantity'] = data['quantity']
        
        if 'status' in data:
            serializer_data['status'] = data['status']
        
        print("MAPPED PATCH DATA:", serializer_data)
        
        if not serializer_data:
            return Response({"error": "No valid fields to update"}, status=400)
        
        serializer = RMOrderSerializer(order, data=serializer_data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            print("ORDER UPDATED SUCCESSFULLY")
            return Response(serializer.data)
        
        print("SERIALIZER ERRORS:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        order = get_object_or_404(RMOrder, pk=pk)
        order.is_active = False
        order.save()
        order.update_customer_stats()
        
        return Response({
            "message": "Order deleted successfully",
            "order_id": order.order_id
        }, status=status.HTTP_200_OK)

class RMOrderStatsView(APIView):
    """Get RM order statistics"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = RMOrder.objects.filter(is_active=True)
        
        total = queryset.count()
        pending = queryset.filter(status='pending').count()
        approved = queryset.filter(status='approved').count()
        ready = queryset.filter(status='ready').count()
        shipped = queryset.filter(status='shipped').count()
        delivered = queryset.filter(status='delivered').count()
        
        total_revenue = queryset.aggregate(total=Sum('amount'))['total'] or 0
        total_quantity = queryset.aggregate(total=Sum('quantity'))['total'] or 0
        
        return Response({
            "total": total,
            "pending": pending,
            "approved": approved,
            "ready": ready,
            "shipped": shipped,
            "delivered": delivered,
            "totalRevenue": total_revenue,
            "totalQuantity": total_quantity,
            "formattedRevenue": f"₹{total_revenue/100000:.1f}L" if total_revenue >= 100000 else f"₹{total_revenue/1000:.0f}K"
        })


class RMOrderStatusUpdateView(APIView):
    """Update order status only"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        order = get_object_or_404(RMOrder, pk=pk)
        new_status = request.data.get('status')
        
        if not new_status:
            return Response({"error": "Status is required"}, status=400)
        
        order.status = new_status
        order.save()
        
        return Response({
            "message": f"Order status updated to {new_status}",
            "order_id": order.order_id,
            "status": order.status
        })
    
# views.py - Add MSOrder views

class MSOrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all active MS orders with filters"""
        queryset = MSOrder.objects.filter(is_active=True)
        
        # Filter by status
        status = request.query_params.get('status', None)
        if status and status != 'all':
            queryset = queryset.filter(status=status)
        
        # Search functionality
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(order_id__icontains=search) |
                Q(customer__name__icontains=search) |
                Q(tailor__icontains=search)
            )
        
        serializer = MSOrderSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create new MS order"""
        print("=" * 50)
        print("RECEIVED MS ORDER DATA:", request.data)
        print("=" * 50)
        
        serializer = MSOrderSerializer(data=request.data)
        
        if serializer.is_valid():
            order = serializer.save(created_by=request.user)
            print("MS ORDER CREATED:", order.order_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        print("SERIALIZER ERRORS:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# views.py - MSOrderDetailView mein bhi same mapping karo

class MSOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(MSOrder, pk=pk, is_active=True)
        serializer = MSOrderSerializer(order)
        return Response(serializer.data)

    def put(self, request, pk):
        """Full update - Map frontend fields to backend fields"""
        order = get_object_or_404(MSOrder, pk=pk)
        
        data = request.data
        
        serializer_data = {
            'customer_id': data.get('customer_id', order.customer.id if order.customer else None),
            'gender': data.get('gender', order.gender),
            'category': data.get('cat', data.get('category', order.category)),
            'order_date': data.get('orderDate', data.get('order_date', str(order.order_date))),
            'delivery_date': data.get('deliveryDate', data.get('delivery_date', str(order.delivery_date) if order.delivery_date else None)),
            'ordered_by': data.get('orderBy', data.get('ordered_by', order.ordered_by)),
            'tailor': data.get('tailor', order.tailor),
            'amount': data.get('amt', data.get('amount', float(order.amount))),
            'quantity': data.get('qty', data.get('quantity', order.quantity)),
            'status': data.get('status', order.status),
            # Measurements
            'chest': data.get('chest', order.chest),
            'waist': data.get('waist', order.waist),
            'hip': data.get('hip', order.hip),
            'shoulder': data.get('shoulder', order.shoulder),
            'length': data.get('length', order.length),
            'sleeve_length': data.get('sleeve_length', order.sleeve_length),
            'armhole': data.get('armhole', order.armhole),
            'neck': data.get('neck', order.neck),
        }
        
        serializer = MSOrderSerializer(order, data=serializer_data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        print("ERRORS:", serializer.errors)
        return Response(serializer.errors, status=400)

    def patch(self, request, pk):
        """Partial update - Map frontend fields to backend fields"""
        order = get_object_or_404(MSOrder, pk=pk)
        
        data = request.data
        serializer_data = {}
        
        # Field mappings
        field_mapping = {
            'customer_id': 'customer_id', 'cust': 'customer_id',
            'gender': 'gender', 'cat': 'category', 'category': 'category',
            'orderDate': 'order_date', 'order_date': 'order_date',
            'deliveryDate': 'delivery_date', 'delivery_date': 'delivery_date',
            'orderBy': 'ordered_by', 'ordered_by': 'ordered_by',
            'tailor': 'tailor', 'amt': 'amount', 'amount': 'amount',
            'qty': 'quantity', 'quantity': 'quantity', 'status': 'status',
            'chest': 'chest', 'waist': 'waist', 'hip': 'hip', 'shoulder': 'shoulder',
            'length': 'length', 'sleeve_length': 'sleeve_length', 'armhole': 'armhole',
            'neck': 'neck', 'collar': 'collar', 'bicep': 'bicep', 'elbow': 'elbow',
            'cuff': 'cuff', 'thigh': 'thigh', 'knee': 'knee', 'bottom': 'bottom',
            'rise': 'rise', 'inseam': 'inseam', 'bust': 'bust', 'under_bust': 'under_bust',
            'waist_hip': 'waist_hip', 'shoulder_to_waist': 'shoulder_to_waist',
            'waist_to_knee': 'waist_to_knee', 'waist_to_floor': 'waist_to_floor',
            'arm_length': 'arm_length', 'wrist': 'wrist', 'front_neck_depth': 'front_neck_depth',
            'back_neck_depth': 'back_neck_depth', 'dart_length': 'dart_length',
            'dart_depth': 'dart_depth', 'special_notes': 'special_notes'
        }
        
        for frontend_field, backend_field in field_mapping.items():
            if frontend_field in data:
                serializer_data[backend_field] = data[frontend_field]
        
        serializer = MSOrderSerializer(order, data=serializer_data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        print("ERRORS:", serializer.errors)
        return Response(serializer.errors, status=400)

class MSOrderStatsView(APIView):
    """Get MS order statistics"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = MSOrder.objects.filter(is_active=True)
        
        total = queryset.count()
        pending = queryset.filter(status='pending').count()
        in_progress = queryset.filter(status__in=['In Cutting', 'In Stitching']).count()
        qc = queryset.filter(status='qc').count()
        delivered = queryset.filter(status='delivered').count()
        
        total_revenue = queryset.aggregate(total=Sum('amount'))['total'] or 0
        total_quantity = queryset.aggregate(total=Sum('quantity'))['total'] or 0
        
        return Response({
            "total": total,
            "pending": pending,
            "inProgress": in_progress,
            "qc": qc,
            "delivered": delivered,
            "totalRevenue": total_revenue,
            "totalQuantity": total_quantity,
            "formattedRevenue": f"₹{total_revenue/100000:.1f}L" if total_revenue >= 100000 else f"₹{total_revenue/1000:.0f}K"
        })


class MSOrderStatusUpdateView(APIView):
    """Update MS order status only"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        order = get_object_or_404(MSOrder, pk=pk)
        new_status = request.data.get('status')
        
        if not new_status:
            return Response({"error": "Status is required"}, status=400)
        
        order.status = new_status
        order.save()
        
        return Response({
            "message": f"Order status updated to {new_status}",
            "order_id": order.order_id,
            "status": order.status
        })