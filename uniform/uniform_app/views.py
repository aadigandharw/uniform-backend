from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    RegisterSerializer, LoginSerializer, CustomerSerializer,
    MSOrderSerializer, MSOrderWithItemsSerializer, MSOrderItemSerializer,
    RMOrderItemSerializer, RMOrderWithItemsSerializer, RMOrderSerializer
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User, Customer, MSOrder, MSOrderItem, RMOrder, RMOrderItem
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum
import json
import re


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
        return Response({"message": "Customer deleted"}, status=status.HTTP_200_OK)


class CustomerStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_customers = Customer.objects.filter(is_active=True).count()
        total_value = Customer.objects.filter(is_active=True).aggregate(
            total=Sum('total_value'))['total'] or 0
        top_customers = Customer.objects.filter(is_active=True).order_by('-total_value')[:5]
        top_customers_data = CustomerSerializer(top_customers, many=True).data
        formatted_value = f"₹{total_value/100000:.1f}L" if total_value >= 100000 else f"₹{total_value/1000:.0f}K"
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
            "message": f"Customer {status_text}",
            "is_active": customer.is_active
        })


class CustomerOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        orders = RMOrder.objects.filter(customer=customer).order_by('-created_at')
        serializer = RMOrderWithItemsSerializer(orders, many=True)
        return Response({
            "customer": CustomerSerializer(customer).data,
            "orders": serializer.data,
            "total_orders": orders.count()
        })


# ============= HELPER FUNCTION =============

def update_customer_stats_safe(customer):
    if not customer:
        return
    try:
        customer.rm_orders_count = RMOrder.objects.filter(
            customer=customer, is_active=True
        ).count()
        customer.ms_orders_count = MSOrder.objects.filter(
            customer=customer, is_active=True
        ).count()
        rm_total = RMOrder.objects.filter(
            customer=customer, is_active=True
        ).aggregate(total=Sum('amount'))['total'] or 0
        ms_total = MSOrder.objects.filter(
            customer=customer, is_active=True
        ).aggregate(total=Sum('amount'))['total'] or 0
        customer.total_value = rm_total + ms_total
        customer.save(update_fields=[
            'rm_orders_count', 'ms_orders_count', 'total_value'
        ])
    except Exception as e:
        print(f"⚠️ Customer stats update warning: {e}")


# ============= RM ORDER VIEWS =============

class RMOrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = RMOrder.objects.filter(is_active=True)
        filter_status = request.query_params.get('status', None)
        if filter_status and filter_status != 'all':
            queryset = queryset.filter(status=filter_status)
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(order_id__icontains=search) |
                Q(customer__name__icontains=search) |
                Q(category__icontains=search)
            )
        serializer = RMOrderWithItemsSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        items_data = []
        
        # ✅ Handle FormData without using .copy()
        if request.content_type and 'multipart' in request.content_type:
            # Get order fields from POST
            customer_id = request.POST.get('customer_id')
            category = request.POST.get('category')
            order_date = request.POST.get('order_date')
            delivery_date = request.POST.get('delivery_date')
            ordered_by = request.POST.get('ordered_by')
            status_val = request.POST.get('status', 'pending')
            
            # Get items JSON string
            items_str = request.POST.get('items', '[]')
            try:
                items_data = json.loads(items_str)
            except json.JSONDecodeError:
                items_data = []
            
            # Handle file uploads
            for key, file_obj in request.FILES.items():
                match = re.search(r'items\[(\d+)\]\.reference_image', key)
                if match:
                    idx = int(match.group(1))
                    if idx < len(items_data):
                        items_data[idx]['reference_image'] = file_obj
        else:
            # JSON request
            customer_id = request.data.get('customer_id')
            category = request.data.get('category')
            order_date = request.data.get('order_date')
            delivery_date = request.data.get('delivery_date')
            ordered_by = request.data.get('ordered_by')
            status_val = request.data.get('status', 'pending')
            items_data = request.data.get('items', [])

        # Calculate totals
        total_amount = 0
        total_quantity = 0
        
        for item_data in items_data:
            try:
                if isinstance(item_data, str):
                    item_data = json.loads(item_data)
                qty = int(item_data.get('quantity', 1))
                amt_per_piece = float(item_data.get('amount_per_piece', 0))
                total_quantity += qty
                total_amount += qty * amt_per_piece
            except (TypeError, ValueError, json.JSONDecodeError):
                continue

        order_data = {
            'customer_id': customer_id,
            'category': category,
            'order_date': order_date,
            'delivery_date': delivery_date,
            'ordered_by': ordered_by,
            'amount': total_amount,
            'quantity': total_quantity,
            'status': status_val
        }

        order_serializer = RMOrderSerializer(data=order_data)
        if order_serializer.is_valid():
            order = order_serializer.save(created_by=request.user)

            for item_data in items_data:
                try:
                    if isinstance(item_data, str):
                        item_data = json.loads(item_data)
                    
                    quantity = int(item_data.get('quantity', 1))
                    amount_per_piece = float(item_data.get('amount_per_piece', 0))
                    amount = quantity * amount_per_piece
                    
                    reference_image = None
                    if 'reference_image' in item_data and item_data['reference_image']:
                        if hasattr(item_data['reference_image'], 'name'):
                            reference_image = item_data['reference_image']
                        elif isinstance(item_data['reference_image'], str):
                            reference_image = item_data['reference_image']
                    
                    RMOrderItem.objects.create(
                        order=order,
                        customer_id=order.customer.id,
                        gender=item_data.get('gender', 'Gents'),
                        uniform_item=item_data.get('uniform_item', 'Shirt'),
                        color=item_data.get('color', 'White'),
                        size=item_data.get('size', 'M'),
                        quantity=quantity,
                        amount_per_piece=amount_per_piece,
                        amount=amount,
                        special_notes=item_data.get('special_notes', ''),
                        reference_image=reference_image
                    )
                except Exception as e:
                    print(f"Error creating item: {e}")
                    continue

            update_customer_stats_safe(order.customer)
            response_serializer = RMOrderWithItemsSerializer(order)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(order_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RMOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(RMOrder, pk=pk, is_active=True)
        serializer = RMOrderWithItemsSerializer(order)
        return Response(serializer.data)

    def put(self, request, pk):
        order = get_object_or_404(RMOrder, pk=pk)
        items_data = []
        
        # ✅ Handle FormData without using .copy()
        if request.content_type and 'multipart' in request.content_type:
            # Get order fields from POST
            customer_id = request.POST.get('customer_id')
            category = request.POST.get('category')
            order_date = request.POST.get('order_date')
            delivery_date = request.POST.get('delivery_date')
            ordered_by = request.POST.get('ordered_by')
            status_val = request.POST.get('status')
            
            # Get items JSON string
            items_str = request.POST.get('items', '[]')
            try:
                items_data = json.loads(items_str)
            except json.JSONDecodeError:
                items_data = []
            
            # Handle file uploads
            for key, file_obj in request.FILES.items():
                match = re.search(r'items\[(\d+)\]\.reference_image', key)
                if match:
                    idx = int(match.group(1))
                    if idx < len(items_data):
                        items_data[idx]['reference_image'] = file_obj
        else:
            # JSON request
            customer_id = request.data.get('customer_id')
            category = request.data.get('cat', request.data.get('category'))
            order_date = request.data.get('orderDate', request.data.get('order_date'))
            delivery_date = request.data.get('deliveryDate', request.data.get('delivery_date'))
            ordered_by = request.data.get('orderBy', request.data.get('ordered_by'))
            status_val = request.data.get('status')
            items_data = request.data.get('items', [])

        # Use existing values if not provided
        if customer_id is None:
            customer_id = order.customer.id
        if category is None:
            category = order.category
        if order_date is None:
            order_date = str(order.order_date)
        if ordered_by is None:
            ordered_by = order.ordered_by
        if status_val is None:
            status_val = order.status

        try:
            customer_id = int(customer_id)
        except (TypeError, ValueError):
            customer_id = order.customer.id

        # Calculate totals
        total_amount = 0
        total_quantity = 0
        
        for item_data in items_data:
            try:
                if isinstance(item_data, str):
                    item_data = json.loads(item_data)
                qty = int(item_data.get('quantity', 1))
                amt_per_piece = float(item_data.get('amount_per_piece', 0))
                total_quantity += qty
                total_amount += qty * amt_per_piece
            except (TypeError, ValueError, json.JSONDecodeError):
                continue

        serializer_data = {
            'customer_id': customer_id,
            'category': category,
            'order_date': order_date,
            'delivery_date': delivery_date,
            'ordered_by': ordered_by,
            'amount': total_amount,
            'quantity': total_quantity,
            'status': status_val
        }

        serializer = RMOrderSerializer(order, data=serializer_data)
        if serializer.is_valid():
            updated_order = serializer.save()
            
            # Delete old items
            RMOrderItem.objects.filter(order=order).delete()
            
            # Create new items
            for item_data in items_data:
                try:
                    if isinstance(item_data, str):
                        item_data = json.loads(item_data)
                    
                    quantity = int(item_data.get('quantity', 1))
                    amount_per_piece = float(item_data.get('amount_per_piece', 0))
                    amount = quantity * amount_per_piece
                    
                    reference_image = None
                    if 'reference_image' in item_data and item_data['reference_image']:
                        if hasattr(item_data['reference_image'], 'name'):
                            reference_image = item_data['reference_image']
                        elif isinstance(item_data['reference_image'], str):
                            reference_image = item_data['reference_image']
                    
                    RMOrderItem.objects.create(
                        order=order,
                        customer_id=order.customer.id,
                        gender=item_data.get('gender', 'Gents'),
                        uniform_item=item_data.get('uniform_item', 'Shirt'),
                        color=item_data.get('color', 'White'),
                        size=item_data.get('size', 'M'),
                        quantity=quantity,
                        amount_per_piece=amount_per_piece,
                        amount=amount,
                        special_notes=item_data.get('special_notes', ''),
                        reference_image=reference_image
                    )
                except Exception as e:
                    print(f"Error creating item: {e}")
                    continue

            update_customer_stats_safe(order.customer)
            response_serializer = RMOrderWithItemsSerializer(updated_order)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        order = get_object_or_404(RMOrder, pk=pk)
        data = request.data
        serializer_data = {}

        field_map = {
            'customer_id': 'customer_id', 'cat': 'category', 'category': 'category',
            'orderDate': 'order_date', 'order_date': 'order_date',
            'deliveryDate': 'delivery_date', 'delivery_date': 'delivery_date',
            'orderBy': 'ordered_by', 'ordered_by': 'ordered_by',
            'amt': 'amount', 'amount': 'amount',
            'qty': 'quantity', 'quantity': 'quantity',
            'status': 'status',
        }

        for frontend, backend in field_map.items():
            if frontend in data:
                serializer_data[backend] = data[frontend]

        if not serializer_data:
            return Response({"error": "No valid fields"}, status=400)

        serializer = RMOrderSerializer(order, data=serializer_data, partial=True)
        if serializer.is_valid():
            updated_order = serializer.save()
            response_serializer = RMOrderWithItemsSerializer(updated_order)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        order = get_object_or_404(RMOrder, pk=pk)
        customer = order.customer
        order.is_active = False
        order.save(update_fields=['is_active'])
        update_customer_stats_safe(customer)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RMOrderStatsView(APIView):
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
            "total": total, "pending": pending, "approved": approved,
            "ready": ready, "shipped": shipped, "delivered": delivered,
            "totalRevenue": total_revenue, "totalQuantity": total_quantity,
        })


# views.py - Update RMOrderStatusUpdateView

from .models import Notification  # ✅ Add this import at top

class RMOrderStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        order = get_object_or_404(RMOrder, pk=pk)
        old_status = order.status
        new_status = request.data.get('status')
        
        if not new_status:
            return Response({"error": "Status is required"}, status=400)
        
        order.status = new_status
        order.save()
        
        # ✅ CREATE NOTIFICATION WHEN ORDER BECOMES READY
        if new_status == 'ready' and old_status != 'ready':
            Notification.objects.create(
                user=order.customer.created_by,  # Notify the user who created order
                title="Order Ready",
                message=f"✅ Order {order.order_id} is READY!",
                notification_type='order_ready',
                order_id=order.order_id,
                order_type='RM',
                is_read=False
            )
        
        # ✅ CREATE NOTIFICATION WHEN ORDER IS DELIVERED
        if new_status == 'delivered' and old_status != 'delivered':
            Notification.objects.create(
                user=order.customer.created_by,
                title="Order Delivered",
                message=f"🎉 Order {order.order_id} has been DELIVERED!",
                notification_type='order_delivered',
                order_id=order.order_id,
                order_type='RM',
                is_read=False
            )
        
        return Response({"message": f"Status updated to {new_status}", "status": order.status})


# ============= MS ORDER VIEWS =============

class MSOrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = MSOrder.objects.filter(is_active=True)
        filter_status = request.query_params.get('status', None)
        if filter_status and filter_status != 'all':
            queryset = queryset.filter(status=filter_status)
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(order_id__icontains=search) |
                Q(customer__name__icontains=search) |
                Q(tailor__icontains=search)
            )
        serializer = MSOrderWithItemsSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data
        items_data = data.pop('items', [])

        order_data = {
            'customer_id': data.get('customer_id'),
            'gender': data.get('gender', 'Gents'),
            'category': data.get('category', 'School'),
            'order_date': data.get('order_date'),
            'delivery_date': data.get('delivery_date'),
            'ordered_by': data.get('ordered_by', ''),
            'tailor': data.get('tailor', ''),
            'amount': sum(float(item.get('amount', 0)) for item in items_data),
            'quantity': sum(int(item.get('quantity', 0)) for item in items_data),
            'status': data.get('status', 'pending')
        }

        order_serializer = MSOrderSerializer(data=order_data)
        if order_serializer.is_valid():
            order = order_serializer.save(created_by=request.user)

            for item_data in items_data:
                MSOrderItem.objects.create(
                    order=order,
                    customer_id=order.customer.id,
                    person_name=item_data.get('person_name', ''),
                    gender=item_data.get('gender', 'Gents'),
                    quantity=item_data.get('quantity', 1),
                    amount=item_data.get('amount', 0),
                    chest=item_data.get('chest'), shoulder=item_data.get('shoulder'),
                    sleeve_length=item_data.get('sleeve_length'), armhole=item_data.get('armhole'),
                    neck=item_data.get('neck'), length=item_data.get('length'),
                    collar=item_data.get('collar'), bicep=item_data.get('bicep'),
                    elbow=item_data.get('elbow'), cuff=item_data.get('cuff'),
                    bust=item_data.get('bust'), under_bust=item_data.get('under_bust'),
                    arm_length=item_data.get('arm_length'), wrist=item_data.get('wrist'),
                    front_neck_depth=item_data.get('front_neck_depth'),
                    back_neck_depth=item_data.get('back_neck_depth'),
                    dart_length=item_data.get('dart_length'), dart_depth=item_data.get('dart_depth'),
                    waist=item_data.get('waist'), hip=item_data.get('hip'),
                    thigh=item_data.get('thigh'), knee=item_data.get('knee'),
                    bottom=item_data.get('bottom'), rise=item_data.get('rise'),
                    inseam=item_data.get('inseam'), waist_hip=item_data.get('waist_hip'),
                    shoulder_to_waist=item_data.get('shoulder_to_waist'),
                    waist_to_knee=item_data.get('waist_to_knee'),
                    waist_to_floor=item_data.get('waist_to_floor'),
                    special_notes=item_data.get('special_notes', '')
                )

            response_serializer = MSOrderWithItemsSerializer(order)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(order_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MSOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(MSOrder, pk=pk, is_active=True)
        serializer = MSOrderWithItemsSerializer(order)
        return Response(serializer.data)

    def put(self, request, pk):
        order = get_object_or_404(MSOrder, pk=pk)
        data = request.data
        items_data = data.pop('items', None)

        serializer_data = {
            'customer_id': data.get('customer_id', order.customer.id),
            'gender': data.get('gender', order.gender),
            'category': data.get('cat', data.get('category', order.category)),
            'order_date': data.get('orderDate', data.get('order_date', str(order.order_date))),
            'delivery_date': data.get('deliveryDate', data.get('delivery_date', str(order.delivery_date) if order.delivery_date else None)),
            'ordered_by': data.get('orderBy', data.get('ordered_by', order.ordered_by)),
            'tailor': data.get('tailor', order.tailor),
            'amount': data.get('amt', data.get('amount', float(order.amount))),
            'quantity': data.get('qty', data.get('quantity', order.quantity)),
            'status': data.get('status', order.status),
        }

        serializer = MSOrderSerializer(order, data=serializer_data)
        if serializer.is_valid():
            updated_order = serializer.save()

            if items_data and len(items_data) > 0:
                MSOrderItem.objects.filter(order=order).delete()
                for item_data in items_data:
                    MSOrderItem.objects.create(
                        order=order,
                        customer_id=order.customer.id,
                        person_name=item_data.get('person_name', ''),
                        gender=item_data.get('gender', 'Gents'),
                        quantity=item_data.get('quantity', 1),
                        amount=item_data.get('amount', 0),
                        chest=item_data.get('chest'), shoulder=item_data.get('shoulder'),
                        sleeve_length=item_data.get('sleeve_length'), armhole=item_data.get('armhole'),
                        neck=item_data.get('neck'), length=item_data.get('length'),
                        collar=item_data.get('collar'), bicep=item_data.get('bicep'),
                        elbow=item_data.get('elbow'), cuff=item_data.get('cuff'),
                        bust=item_data.get('bust'), under_bust=item_data.get('under_bust'),
                        arm_length=item_data.get('arm_length'), wrist=item_data.get('wrist'),
                        front_neck_depth=item_data.get('front_neck_depth'),
                        back_neck_depth=item_data.get('back_neck_depth'),
                        dart_length=item_data.get('dart_length'), dart_depth=item_data.get('dart_depth'),
                        waist=item_data.get('waist'), hip=item_data.get('hip'),
                        thigh=item_data.get('thigh'), knee=item_data.get('knee'),
                        bottom=item_data.get('bottom'), rise=item_data.get('rise'),
                        inseam=item_data.get('inseam'), waist_hip=item_data.get('waist_hip'),
                        shoulder_to_waist=item_data.get('shoulder_to_waist'),
                        waist_to_knee=item_data.get('waist_to_knee'),
                        waist_to_floor=item_data.get('waist_to_floor'),
                        special_notes=item_data.get('special_notes', '')
                    )

            response_serializer = MSOrderWithItemsSerializer(updated_order)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=400)

    def patch(self, request, pk):
        order = get_object_or_404(MSOrder, pk=pk)
        data = request.data
        serializer_data = {}

        field_mapping = {
            'customer_id': 'customer_id', 'gender': 'gender',
            'cat': 'category', 'category': 'category',
            'orderDate': 'order_date', 'order_date': 'order_date',
            'deliveryDate': 'delivery_date', 'delivery_date': 'delivery_date',
            'orderBy': 'ordered_by', 'ordered_by': 'ordered_by',
            'tailor': 'tailor', 'amt': 'amount', 'amount': 'amount',
            'qty': 'quantity', 'quantity': 'quantity', 'status': 'status',
        }

        for frontend_field, backend_field in field_mapping.items():
            if frontend_field in data:
                serializer_data[backend_field] = data[frontend_field]

        serializer = MSOrderSerializer(order, data=serializer_data, partial=True)
        if serializer.is_valid():
            updated_order = serializer.save()
            response_serializer = MSOrderWithItemsSerializer(updated_order)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        order = get_object_or_404(MSOrder, pk=pk)
        customer = order.customer
        order.is_active = False
        order.save(update_fields=['is_active'])
        update_customer_stats_safe(customer)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MSOrderStatsView(APIView):
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
            "total": total, "pending": pending, "inProgress": in_progress,
            "qc": qc, "delivered": delivered,
            "totalRevenue": total_revenue, "totalQuantity": total_quantity,
        })


# views.py - Update MSOrderStatusUpdateView

class MSOrderStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        order = get_object_or_404(MSOrder, pk=pk)
        old_status = order.status
        new_status = request.data.get('status')
        
        if not new_status:
            return Response({"error": "Status is required"}, status=400)
        
        order.status = new_status
        order.save()
        
        # ✅ CREATE NOTIFICATION WHEN ORDER BECOMES READY
        if new_status == 'ready' and old_status != 'ready':
            Notification.objects.create(
                user=order.customer.created_by,
                title="Order Ready",
                message=f"✅ Order {order.order_id} is READY!",
                notification_type='order_ready',
                order_id=order.order_id,
                order_type='MS',
                is_read=False
            )
        
        # ✅ CREATE NOTIFICATION WHEN ORDER IS DELIVERED
        if new_status == 'delivered' and old_status != 'delivered':
            Notification.objects.create(
                user=order.customer.created_by,
                title="Order Delivered",
                message=f"🎉 Order {order.order_id} has been DELIVERED!",
                notification_type='order_delivered',
                order_id=order.order_id,
                order_type='MS',
                is_read=False
            )
        
        return Response({"message": f"Status updated to {new_status}", "status": order.status})
    

# Quotation Views
# ============= QUOTATION VIEWS =============
# ✅ CORRECT
from .models import Quotation, QuotationItem
from .serializers import QuotationSerializer, QuotationListSerializer, QuotationItemSerializer
class QuotationListView(APIView):
    """
    Get all quotations or create new quotation
    GET: /api/quotations/ (with optional filters)
    POST: /api/quotations/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Quotation.objects.filter(is_active=True)
        
        # Filter by status
        status_filter = request.query_params.get('status', None)
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        # Search by customer name or quotation number
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(quotation_no__icontains=search) |
                Q(customer__name__icontains=search) |
                Q(customer_name__icontains=search)
            )
        
        # Order by latest first
        queryset = queryset.order_by('-created_at')
        
        serializer = QuotationListSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        
        print("=" * 50)
        print("📥 RECEIVED DATA:", data)
        print("=" * 50)
        
        if not data.get('status'):
            data['status'] = 'Draft'
        
        # Handle customer data
        if data.get('customer_id'):
            try:
                customer = Customer.objects.get(id=data['customer_id'], is_active=True)
                data['customer_name'] = customer.name
                data['customer_phone'] = customer.phone
                data['customer_email'] = customer.email or ''
                data['customer_address'] = customer.city or ''
                print("✅ Customer found:", customer.name)
            except Customer.DoesNotExist:
                return Response({"error": "Customer not found"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if not data.get('customer_name'):
                return Response({"error": "Customer name is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ DON'T pop items here - let serializer handle it
        # items_data = data.pop('items', [])  # ← REMOVE THIS LINE
        
        print("📤 Serializer Data:", data)
        
        serializer = QuotationSerializer(data=data)
        
        if serializer.is_valid():
            quotation = serializer.save(created_by=request.user)
            response_serializer = QuotationSerializer(quotation)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        print("❌ SERIALIZER ERRORS:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuotationDetailView(APIView):
    """
    Get, update or delete a specific quotation
    GET: /api/quotations/<id>/
    PUT: /api/quotations/<id>/
    PATCH: /api/quotations/<id>/
    DELETE: /api/quotations/<id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk, is_active=True)
        serializer = QuotationSerializer(quotation)
        return Response(serializer.data)

    def put(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        data = request.data.copy()
        
        # Handle customer data update
        if data.get('customer_id') and str(data.get('customer_id')) != str(quotation.customer_id):
            try:
                customer = Customer.objects.get(id=data['customer_id'], is_active=True)
                data['customer_name'] = customer.name
                data['customer_phone'] = customer.phone
                data['customer_email'] = customer.email
                data['customer_address'] = customer.address
            except Customer.DoesNotExist:
                return Response({"error": "Customer not found"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract items
        items_data = data.pop('items', [])
        
        # Update quotation
        serializer = QuotationSerializer(quotation, data=data)
        if serializer.is_valid():
            updated_quotation = serializer.save()
            
            # Delete old items and create new ones
            QuotationItem.objects.filter(quotation=quotation).delete()
            for item_data in items_data:
                QuotationItem.objects.create(
                    quotation=quotation,
                    product_name=item_data.get('product_name', ''),
                    gender=item_data.get('gender', 'Gents'),
                    size=item_data.get('size', 'M'),
                    quantity=item_data.get('quantity', 1),
                    unit_price=item_data.get('unit_price', 0),
                    discount_percent=item_data.get('discount_percent', 0),
                    amount=item_data.get('amount', 0),
                    notes=item_data.get('notes', '')
                )
            
            # Recalculate totals
            updated_quotation = recalculate_quotation_totals(updated_quotation)
            
            response_serializer = QuotationSerializer(updated_quotation)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        data = request.data
        
        # Field mapping for partial updates
        field_mapping = {
            'customer_id': 'customer_id', 'customer_name': 'customer_name',
            'customer_phone': 'customer_phone', 'customer_email': 'customer_email',
            'customer_address': 'customer_address', 'subject': 'subject',
            'message': 'message', 'discount_percent': 'discount_percent',
            'gst_percent': 'gst_percent', 'status': 'status',
            'payment_terms': 'payment_terms', 'delivery_time': 'delivery_time',
            'warranty': 'warranty', 'validity': 'validity', 'notes': 'notes',
            'date': 'date', 'valid_till': 'valid_till'
        }
        
        update_data = {}
        for frontend, backend in field_mapping.items():
            if frontend in data:
                update_data[backend] = data[frontend]
        
        # Handle customer_id separately
        if 'customer_id' in update_data:
            try:
                customer = Customer.objects.get(id=update_data['customer_id'], is_active=True)
                update_data['customer_name'] = customer.name
                update_data['customer_phone'] = customer.phone
                update_data['customer_email'] = customer.email
                update_data['customer_address'] = customer.address
            except Customer.DoesNotExist:
                return Response({"error": "Customer not found"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = QuotationSerializer(quotation, data=update_data, partial=True)
        if serializer.is_valid():
            updated_quotation = serializer.save()
            
            # If status changed to Converted, handle conversion
            if update_data.get('status') == 'Converted' and quotation.status != 'Converted':
                # You can add auto-conversion logic here
                pass
            
            response_serializer = QuotationSerializer(updated_quotation)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        quotation.is_active = False
        quotation.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuotationConvertToOrderView(APIView):
    """
    Convert quotation to order (RMOrder)
    POST: /api/quotations/<id>/convert-to-order/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk, is_active=True)
        
        if quotation.status != 'Approved':
            return Response(
                {"error": "Only approved quotations can be converted to orders"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already converted
        if quotation.status == 'Converted':
            return Response(
                {"error": "Quotation already converted to order"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create RM Order
            rm_order = RMOrder.objects.create(
                customer_id=quotation.customer_id,
                category='School',  # You can determine from items
                amount=quotation.total_amount,
                quantity=sum(item.quantity for item in quotation.items.all()),
                status='pending',
                created_by=request.user
            )
            
            # Create RM Order Items
            for item in quotation.items.all():
                RMOrderItem.objects.create(
                    order=rm_order,
                    customer_id=quotation.customer_id,
                    gender=item.gender,
                    product_type='Uniform',
                    uniform_item=item.product_name,
                    size=item.size,
                    quantity=item.quantity,
                    amount_per_piece=item.unit_price,
                    amount=item.amount,
                    special_notes=item.notes or ''
                )
            
            # Update quotation status
            quotation.status = 'Converted'
            quotation.save(update_fields=['status'])
            
            # Update customer stats
            update_customer_stats_safe(quotation.customer)
            
            return Response({
                "message": "Quotation converted to order successfully",
                "order_id": rm_order.order_id,
                "order_type": "RMOrder",
                "order": RMOrderWithItemsSerializer(rm_order).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to convert: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QuotationUpdateStatusView(APIView):
    """
    Update quotation status
    POST: /api/quotations/<id>/update-status/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk, is_active=True)
        new_status = request.data.get('status')
        
        if not new_status:
            return Response(
                {"error": "Status is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_statuses = ['Draft', 'Sent', 'Approved', 'Rejected', 'Converted']
        if new_status not in valid_statuses:
            return Response(
                {"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If converting to Approved, you might want to add validation
        if new_status == 'Approved' and quotation.status == 'Draft':
            # Optional: Add approval validation
            pass
        
        quotation.status = new_status
        quotation.save(update_fields=['status'])
        
        return Response({
            "message": f"Status updated to {new_status} successfully",
            "status": quotation.status,
            "quotation_no": quotation.quotation_no
        })


class QuotationStatsView(APIView):
    """
    Get quotation statistics
    GET: /api/quotations/stats/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Quotation.objects.filter(is_active=True)
        
        total = queryset.count()
        draft = queryset.filter(status='Draft').count()
        sent = queryset.filter(status='Sent').count()
        approved = queryset.filter(status='Approved').count()
        rejected = queryset.filter(status='Rejected').count()
        converted = queryset.filter(status='Converted').count()
        
        total_value = queryset.aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Recent quotations (last 5)
        recent = queryset.order_by('-created_at')[:5]
        recent_data = QuotationListSerializer(recent, many=True).data
        
        return Response({
            "total": total,
            "draft": draft,
            "sent": sent,
            "approved": approved,
            "rejected": rejected,
            "converted": converted,
            "total_value": total_value,
            "formatted_total_value": f"₹{total_value/100000:.1f}L" if total_value >= 100000 else f"₹{total_value/1000:.0f}K",
            "recent_quotations": recent_data
        })


# ============= HELPER FUNCTION FOR QUOTATION =============

def recalculate_quotation_totals(quotation):
    """Recalculate subtotal, discount, GST, and total for a quotation"""
    items = quotation.items.all()
    
    subtotal = sum(item.amount for item in items)
    discount_amount = subtotal * (quotation.discount_percent / 100)
    taxable_value = subtotal - discount_amount
    gst_amount = taxable_value * (quotation.gst_percent / 100)
    total_amount = taxable_value + gst_amount
    
    quotation.subtotal = subtotal
    quotation.discount_amount = discount_amount
    quotation.gst_amount = gst_amount
    quotation.total_amount = total_amount
    quotation.save(update_fields=['subtotal', 'discount_amount', 'gst_amount', 'total_amount'])
    
    return quotation



# ============= VENDOR MANAGEMENT VIEWS =============

from .models import VendorCategory , Vendor  , PurchaseOrder 
from .serializers import VendorCategorySerializer , VendorListSerializer , VendorSerializer  , PurchaseOrder , PurchaseOrderSerializer

class VendorCategoryListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        categories = VendorCategory.objects.filter(is_active=True)
        serializer = VendorCategorySerializer(categories, many=True)
        return Response(serializer.data)


class VendorListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        queryset = Vendor.objects.all()
        
        # Search
        search = request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(phone__icontains=search) |
                Q(contact_person__icontains=search) |
                Q(vendor_code__icontains=search)
            )
        
        # Filter by status
        status_filter = request.query_params.get('status', '')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Filter by category
        category = request.query_params.get('category', '')
        if category:
            queryset = queryset.filter(category__name=category)
        
        serializer = VendorListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = VendorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VendorDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        vendor = get_object_or_404(Vendor, pk=pk)
        serializer = VendorSerializer(vendor)
        return Response(serializer.data)
    
    def put(self, request, pk):
        vendor = get_object_or_404(Vendor, pk=pk)
        serializer = VendorSerializer(vendor, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        vendor = get_object_or_404(Vendor, pk=pk)
        serializer = VendorSerializer(vendor, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        vendor = get_object_or_404(Vendor, pk=pk)
        vendor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VendorToggleStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, pk):
        vendor = get_object_or_404(Vendor, pk=pk)
        vendor.is_active = not vendor.is_active
        vendor.save()
        status_text = "activated" if vendor.is_active else "deactivated"
        return Response({"message": f"Vendor {status_text} successfully", "is_active": vendor.is_active})


class VendorStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        total_vendors = Vendor.objects.count()
        active_vendors = Vendor.objects.filter(is_active=True).count()
        inactive_vendors = Vendor.objects.filter(is_active=False).count()
        total_purchases = Vendor.objects.aggregate(total=Sum('total_purchases'))['total'] or 0
        
        # Category wise count
        category_stats = []
        categories = VendorCategory.objects.filter(is_active=True)
        for cat in categories:
            count = Vendor.objects.filter(category=cat, is_active=True).count()
            category_stats.append({
                'name': cat.name,
                'count': count
            })
        
        return Response({
            'total_vendors': total_vendors,
            'active_vendors': active_vendors,
            'inactive_vendors': inactive_vendors,
            'total_purchases': total_purchases,
            'formatted_total_purchases': f"₹{total_purchases/100000:.1f}L" if total_purchases >= 100000 else f"₹{total_purchases/1000:.0f}K",
            'category_stats': category_stats
        })


class VendorPurchaseHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        vendor = get_object_or_404(Vendor, pk=pk)
        purchase_orders = PurchaseOrder.objects.filter(vendor=vendor).order_by('-order_date')
        serializer = PurchaseOrderSerializer(purchase_orders, many=True)
        return Response({
            'vendor': VendorSerializer(vendor).data,
            'purchase_history': serializer.data,
            'total_orders': purchase_orders.count(),
            'total_amount': purchase_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        })
    

# ============= PURCHASE ORDER VIEWS =============

from .serializers import PurchaseOrderListSerializer
class PurchaseOrderListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        queryset = PurchaseOrder.objects.all().order_by('-created_at')
        
        # Filter by status
        status_filter = request.query_params.get('status', '')
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        # Filter by vendor
        vendor_id = request.query_params.get('vendor', '')
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
        
        # Search by PO number or vendor name
        search = request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(po_number__icontains=search) |
                Q(vendor__name__icontains=search)
            )
        
        serializer = PurchaseOrderListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = PurchaseOrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PurchaseOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
        serializer = PurchaseOrderSerializer(purchase_order)
        return Response(serializer.data)
    
    def put(self, request, pk):
        purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
        serializer = PurchaseOrderSerializer(purchase_order, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
        serializer = PurchaseOrderSerializer(purchase_order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
        purchase_order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PurchaseOrderStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, pk):
        purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
        new_status = request.data.get('status')
        
        if not new_status:
            return Response({"error": "Status is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_statuses = ['draft', 'ordered', 'partial', 'received', 'cancelled']
        if new_status not in valid_statuses:
            return Response({"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        purchase_order.status = new_status
        
        # If status is received, set actual_delivery_date
        if new_status == 'received' and not purchase_order.actual_delivery_date:
            from django.utils import timezone
            purchase_order.actual_delivery_date = timezone.now().date()
        
        purchase_order.save()
        
        # Update vendor stats
        vendor = purchase_order.vendor
        vendor.total_purchases += purchase_order.total_amount
        vendor.total_orders += 1
        vendor.last_purchase_date = purchase_order.order_date
        vendor.save()
        
        return Response({
            "message": f"Status updated to {new_status} successfully",
            "status": purchase_order.status,
            "po_number": purchase_order.po_number
        })


class PurchaseOrderStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        queryset = PurchaseOrder.objects.all()
        
        total_orders = queryset.count()
        draft = queryset.filter(status='draft').count()
        ordered = queryset.filter(status='ordered').count()
        partial = queryset.filter(status='partial').count()
        received = queryset.filter(status='received').count()
        cancelled = queryset.filter(status='cancelled').count()
        
        total_amount = queryset.aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Recent orders
        recent = queryset.order_by('-created_at')[:5]
        recent_data = PurchaseOrderListSerializer(recent, many=True).data
        
        return Response({
            "total_orders": total_orders,
            "draft": draft,
            "ordered": ordered,
            "partial": partial,
            "received": received,
            "cancelled": cancelled,
            "total_amount": total_amount,
            "formatted_total_amount": f"₹{total_amount/100000:.1f}L" if total_amount >= 100000 else f"₹{total_amount/1000:.0f}K",
            "recent_orders": recent_data
        })

# ============= PRODUCT CATALOG VIEWS =============
from .models import ProductCategory , Product , SchoolProductPrice , ProductVariant
from .serializers import ProductCategorySerializer ,ProductListSerializer ,ProductSerializer , SchoolProductPriceSerializer

class ProductCategoryListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        categories = ProductCategory.objects.filter(is_active=True)
        serializer = ProductCategorySerializer(categories, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = ProductCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductCategoryDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        category = get_object_or_404(ProductCategory, pk=pk)
        serializer = ProductCategorySerializer(category)
        return Response(serializer.data)
    
    def put(self, request, pk):
        category = get_object_or_404(ProductCategory, pk=pk)
        serializer = ProductCategorySerializer(category, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        category = get_object_or_404(ProductCategory, pk=pk)
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        queryset = Product.objects.all()
        
        # Filter by status
        status_filter = request.query_params.get('status', '')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Filter by category
        category = request.query_params.get('category', '')
        if category:
            queryset = queryset.filter(category__name=category)
        
        # Search by name or product code
        search = request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(product_code__icontains=search)
            )
        
        serializer = ProductListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        serializer = ProductSerializer(product)
        return Response(serializer.data)
    
    def put(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        serializer = ProductSerializer(product, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductToggleStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.is_active = not product.is_active
        product.save()
        status_text = "activated" if product.is_active else "deactivated"
        return Response({"message": f"Product {status_text} successfully", "is_active": product.is_active})


class ProductStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        total_products = Product.objects.count()
        active_products = Product.objects.filter(is_active=True).count()
        inactive_products = Product.objects.filter(is_active=False).count()
        low_stock_products = Product.objects.filter(
            variants__stock_quantity__lt=10,
            is_active=True
        ).distinct().count()
        
        # Category wise count
        category_stats = []
        categories = ProductCategory.objects.filter(is_active=True)
        for cat in categories:
            count = Product.objects.filter(category=cat, is_active=True).count()
            category_stats.append({'name': cat.name, 'count': count})
        
        return Response({
            'total_products': total_products,
            'active_products': active_products,
            'inactive_products': inactive_products,
            'low_stock_products': low_stock_products,
            'category_stats': category_stats
        })


class SchoolProductPriceView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        prices = SchoolProductPrice.objects.filter(product=product)
        serializer = SchoolProductPriceSerializer(prices, many=True)
        return Response(serializer.data)
    
    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        data = request.data
        data['product'] = product.id
        serializer = SchoolProductPriceSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============= EMPLOYEE TASK MANAGEMENT VIEWS =============
# Add this at the end of your views.py file

from .models import Employee, Task, TaskProgress
from .serializers import (
    EmployeeSerializer, EmployeeListSerializer,
    TaskSerializer, TaskListSerializer, CreateTaskSerializer,
    TaskProgressSerializer, UpdateTaskStatusSerializer, UpdateTaskProgressSerializer,
    TaskStatsSerializer, OrderTasksSerializer, EmployeeStatsSerializer
)
from django.utils import timezone 
from django.db.models import Count


# ============= EMPLOYEE VIEWS =============

class EmployeeListView(APIView):
    """
    Get all employees or create new employee
    GET: /api/employees/ (with optional filters)
    POST: /api/employees/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Employee.objects.filter(is_active=True)
        
        # Filter by designation
        designation = request.query_params.get('designation', '')
        if designation:
            queryset = queryset.filter(designation=designation)
        
        # Search by name or employee code or phone
        search = request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(user__full_name__icontains=search) |
                Q(employee_code__icontains=search) |
                Q(phone__icontains=search)
            )
        
        serializer = EmployeeListSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Create Employee from existing User or Create New User
        from .models import User
        
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user exists
        user = User.objects.filter(email=email).first()
        
        if not user:
            # Create new user
            full_name = request.data.get('full_name', '')
            password = request.data.get('password', '')
            
            if not password:
                return Response({"error": "Password is required for new user"}, status=status.HTTP_400_BAD_REQUEST)
            
            user = User.objects.create_user(
                email=email,
                password=password,
                full_name=full_name
            )
            user.is_active = True
            user.save()
        
        # Create employee
        employee_data = {
            'user': user.id,
            'designation': request.data.get('designation'),
            'phone': request.data.get('phone', ''),
            'address': request.data.get('address', ''),
            'salary': request.data.get('salary', 0),
        }
        
        serializer = EmployeeSerializer(data=employee_data)
        if serializer.is_valid():
            employee = serializer.save()
            
            # Update employee stats
            employee.total_tasks = 0
            employee.completed_tasks = 0
            employee.pending_tasks = 0
            employee.in_progress_tasks = 0
            employee.save()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmployeeDetailView(APIView):
    """
    Get, update or delete a specific employee
    GET: /api/employees/<id>/
    PATCH: /api/employees/<id>/
    DELETE: /api/employees/<id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        serializer = EmployeeSerializer(employee)
        return Response(serializer.data)

    def patch(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        serializer = EmployeeSerializer(employee, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        employee.is_active = False
        employee.save()
        return Response({"message": "Employee deactivated successfully"})


class EmployeeStatsView(APIView):
    """
    Get employee statistics
    GET: /api/employees/stats/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_employees = Employee.objects.filter(is_active=True).count()
        
        # Designation wise count
        designation_wise = {}
        for designation, label in Employee.DESIGNATION_CHOICES:
            count = Employee.objects.filter(designation=designation, is_active=True).count()
            designation_wise[designation] = count
        
        # Current workload (employees with pending/in_progress tasks)
        current_workload = Employee.objects.filter(is_active=True).values(
            'id', 'user__full_name', 'designation'
        ).annotate(
            pending_count=Count('tasks', filter=Q(tasks__status='pending')),
            in_progress_count=Count('tasks', filter=Q(tasks__status='in_progress')),
            total_active_tasks=Count('tasks', filter=Q(tasks__status__in=['pending', 'in_progress']))
        ).filter(total_active_tasks__gt=0)
        
        return Response({
            'total_employees': total_employees,
            'designation_wise': designation_wise,
            'current_workload': list(current_workload)
        })


# ============= TASK VIEWS =============

class TaskListView(APIView):
    """
    Get all tasks or create new task
    GET: /api/tasks/ (with optional filters)
    POST: /api/tasks/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Task.objects.all()
        
        # Filter by status
        status_filter = request.query_params.get('status', '')
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        # Filter by task type
        task_type = request.query_params.get('task_type', '')
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        
        # Filter by assigned employee
        employee_id = request.query_params.get('employee_id', '')
        if employee_id:
            queryset = queryset.filter(assigned_to_id=employee_id)
        
        # Filter by order (RM or MS)
        order_id = request.query_params.get('order_id', '')
        if order_id:
            queryset = queryset.filter(
                Q(rm_order__order_id=order_id) |
                Q(ms_order__order_id=order_id)
            )
        
        # Filter by priority
        priority = request.query_params.get('priority', '')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Search by task number or title
        search = request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(task_number__icontains=search) |
                Q(title__icontains=search) |
                Q(assigned_to__user__full_name__icontains=search)
            )
        
        # Overdue filter
        overdue = request.query_params.get('overdue', '')
        if overdue == 'true':
            queryset = queryset.filter(
                due_date__lt=timezone.now().date(),
                status__in=['pending', 'in_progress']
            )
        
        # Order by priority and due date
        queryset = queryset.order_by('-priority', 'due_date', '-created_at')
        
        serializer = TaskListSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CreateTaskSerializer(data=request.data)
        if serializer.is_valid():
            task = serializer.save(assigned_by=request.user)
            
            # Update employee stats
            employee = task.assigned_to
            employee.pending_tasks += 1
            employee.total_tasks += 1
            employee.save()
            
            response_serializer = TaskSerializer(task)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskDetailView(APIView):
    """
    Get, update or delete a specific task
    GET: /api/tasks/<id>/
    PATCH: /api/tasks/<id>/
    DELETE: /api/tasks/<id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        serializer = TaskSerializer(task)
        return Response(serializer.data)

    def patch(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        serializer = TaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        
        # Update employee stats
        employee = task.assigned_to
        if task.status == 'pending':
            employee.pending_tasks -= 1
        elif task.status == 'in_progress':
            employee.in_progress_tasks -= 1
        elif task.status == 'completed':
            employee.completed_tasks -= 1
        
        employee.total_tasks -= 1
        employee.save()
        
        task.delete()
        return Response({"message": "Task deleted successfully"})


class TaskUpdateStatusView(APIView):
    """
    Update task status
    PATCH: /api/tasks/<id>/update-status/
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        serializer = UpdateTaskStatusSerializer(data=request.data)
        
        if serializer.is_valid():
            old_status = task.status
            new_status = serializer.validated_data['status']
            
            # Update task status
            task.status = new_status
            
            if new_status == 'completed':
                task.completed_at = timezone.now()
                task.completed_quantity = task.total_quantity
            
            task.save()
            
            # Update employee stats
            employee = task.assigned_to
            
            # Remove from old status
            if old_status == 'pending':
                employee.pending_tasks -= 1
            elif old_status == 'in_progress':
                employee.in_progress_tasks -= 1
            
            # Add to new status
            if new_status == 'in_progress':
                employee.in_progress_tasks += 1
            elif new_status == 'completed':
                employee.completed_tasks += 1
            elif new_status == 'pending':
                employee.pending_tasks += 1
            elif new_status == 'rejected':
                # Rejected task - remove from counts
                pass
            
            employee.save()
            
            # Add progress log if remarks provided
            remarks = serializer.validated_data.get('remarks', '')
            if remarks:
                TaskProgress.objects.create(
                    task=task,
                    completed_quantity=task.completed_quantity,
                    remarks=remarks,
                    updated_by=request.user
                )
            
            return Response({
                "message": f"Task status updated to {new_status}",
                "status": task.status,
                "progress_percent": task.progress_percent
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskUpdateProgressView(APIView):
    """
    Update task progress (completed quantity)
    PATCH: /api/tasks/<id>/update-progress/
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        serializer = UpdateTaskProgressSerializer(data=request.data)
        
        if serializer.is_valid():
            completed_qty = serializer.validated_data['completed_quantity']
            
            # Validate quantity
            if task.completed_quantity + completed_qty > task.total_quantity:
                return Response(
                    {"error": f"Cannot exceed total quantity. Max allowed: {task.total_quantity - task.completed_quantity}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            old_completed = task.completed_quantity
            task.completed_quantity += completed_qty
            
            # Check if task is completed
            was_completed = (old_completed == task.total_quantity)
            is_now_completed = (task.completed_quantity == task.total_quantity)
            
            # Update status if needed
            if is_now_completed and not was_completed:
                task.status = 'completed'
                task.completed_at = timezone.now()
                
                # Update employee stats
                employee = task.assigned_to
                if task.status == 'in_progress':
                    employee.in_progress_tasks -= 1
                employee.completed_tasks += 1
                employee.save()
            elif task.status == 'pending' and task.completed_quantity > 0:
                task.status = 'in_progress'
                
                # Update employee stats
                employee = task.assigned_to
                employee.pending_tasks -= 1
                employee.in_progress_tasks += 1
                employee.save()
            
            task.save()
            
            # Log progress
            TaskProgress.objects.create(
                task=task,
                completed_quantity=completed_qty,
                remarks=serializer.validated_data.get('remarks', ''),
                updated_by=request.user
            )
            
            return Response({
                "message": "Progress updated successfully",
                "completed_quantity": task.completed_quantity,
                "remaining_quantity": task.total_quantity - task.completed_quantity,
                "progress_percent": task.progress_percent,
                "status": task.status
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskProgressHistoryView(APIView):
    """
    Get task progress history
    GET: /api/tasks/<id>/progress-history/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        progress_logs = task.progress_logs.all()
        serializer = TaskProgressSerializer(progress_logs, many=True)
        return Response(serializer.data)


class TaskStatsView(APIView):
    """
    Get task statistics for dashboard
    GET: /api/tasks/stats/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Task.objects.all()
        
        total_tasks = queryset.count()
        pending = queryset.filter(status='pending').count()
        in_progress = queryset.filter(status='in_progress').count()
        completed = queryset.filter(status='completed').count()
        rejected = queryset.filter(status='rejected').count()
        
        # Overdue tasks
        overdue = queryset.filter(
            due_date__lt=timezone.now().date(),
            status__in=['pending', 'in_progress']
        ).count()
        
        # Completion rate
        completion_rate = round((completed / total_tasks * 100), 1) if total_tasks > 0 else 0
        
        # Task type wise stats
        task_type_stats = {}
        for task_type, label in Task.TASK_TYPE_CHOICES:
            count = queryset.filter(task_type=task_type).count()
            completed_count = queryset.filter(task_type=task_type, status='completed').count()
            task_type_stats[task_type] = {
                'total': count,
                'completed': completed_count,
                'pending': count - completed_count,
                'completion_rate': round((completed_count / count * 100), 1) if count > 0 else 0
            }
        
        # Priority wise stats
        priority_stats = {}
        for priority, label in Task.PRIORITY_CHOICES:
            count = queryset.filter(priority=priority).count()
            priority_stats[priority] = count
        
        # Employee performance (top 5)
        employee_performance = Employee.objects.filter(is_active=True).values(
            'id', 'user__full_name', 'designation'
        ).annotate(
            completed=Count('tasks', filter=Q(tasks__status='completed')),
            total=Count('tasks')
        ).order_by('-completed')[:5]
        
        # Recent tasks (last 10)
        recent_tasks = queryset.order_by('-created_at')[:10]
        recent_tasks_data = TaskListSerializer(recent_tasks, many=True).data
        
        return Response({
            'total_tasks': total_tasks,
            'pending': pending,
            'in_progress': in_progress,
            'completed': completed,
            'rejected': rejected,
            'overdue': overdue,
            'completion_rate': completion_rate,
            'task_type_stats': task_type_stats,
            'priority_stats': priority_stats,
            'employee_performance': list(employee_performance),
            'recent_tasks': recent_tasks_data
        })


# ============= ORDER TASKS VIEWS =============

class OrderTasksView(APIView):
    """
    Get tasks for a specific order (RM or MS)
    GET: /api/orders/<order_type>/<order_id>/tasks/
    POST: /api/orders/<order_type>/<order_id>/tasks/ (auto-create tasks)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_type, order_id):
        if order_type.upper() == 'RM':
            order = get_object_or_404(RMOrder, order_id=order_id, is_active=True)
            tasks = Task.objects.filter(rm_order=order)
        elif order_type.upper() == 'MS':
            order = get_object_or_404(MSOrder, order_id=order_id, is_active=True)
            tasks = Task.objects.filter(ms_order=order)
        else:
            return Response({"error": "Invalid order type. Use 'RM' or 'MS'"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = TaskListSerializer(tasks, many=True)
        
        # Calculate order progress
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status='completed').count()
        progress = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0
        
        return Response({
            'order_id': order.order_id,
            'order_type': order_type.upper(),
            'customer': order.customer.name if order.customer else '',
            'total_quantity': order.quantity,
            'tasks': serializer.data,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': tasks.filter(status='pending').count(),
            'in_progress_tasks': tasks.filter(status='in_progress').count(),
            'progress': progress
        })

    def post(self, request, order_type, order_id):
        """
        Auto-create all tasks for an order
        """
        if order_type.upper() == 'RM':
            order = get_object_or_404(RMOrder, order_id=order_id, is_active=True)
            order_ref = order
        elif order_type.upper() == 'MS':
            order = get_object_or_404(MSOrder, order_id=order_id, is_active=True)
            order_ref = order
        else:
            return Response({"error": "Invalid order type. Use 'RM' or 'MS'"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if tasks already exist
        existing_tasks = Task.objects.filter(
            Q(rm_order=order_ref) | Q(ms_order=order_ref)
        )
        
        if existing_tasks.exists():
            return Response({
                "warning": "Tasks already exist for this order",
                "existing_tasks": TaskListSerializer(existing_tasks, many=True).data
            }, status=status.HTTP_409_CONFLICT)
        
        # Get employee assignments from request or use defaults
        employee_assignments = request.data.get('employee_assignments', {})
        
        # Default due date (7 days from now)
        default_due_date = timezone.now().date() + timezone.timedelta(days=7)
        
        created_tasks = []
        task_types = ['cutting', 'stitching', 'finishing', 'packing', 'qc']
        
        for task_type in task_types:
            # Get assigned employee for this task type
            assigned_to_id = employee_assignments.get(task_type)
            
            if assigned_to_id:
                assigned_to = get_object_or_404(Employee, id=assigned_to_id, is_active=True)
            else:
                # Try to find employee by designation
                designation_map = {
                    'cutting': 'cutter',
                    'stitching': 'stitcher',
                    'finishing': 'finisher',
                    'packing': 'packer',
                    'qc': 'supervisor'
                }
                designation = designation_map.get(task_type)
                assigned_to = Employee.objects.filter(designation=designation, is_active=True).first()
                
                if not assigned_to:
                    # Skip if no employee found
                    continue
            
            # Create task
            task = Task.objects.create(
                rm_order=order_ref if order_type.upper() == 'RM' else None,
                ms_order=order_ref if order_type.upper() == 'MS' else None,
                task_type=task_type,
                title=f"{task_type.capitalize()} for {order.order_id}",
                description=f"Auto-created task for {task_type} of order {order.order_id}",
                assigned_to=assigned_to,
                assigned_by=request.user,
                total_quantity=order.quantity,
                due_date=default_due_date,
                priority='medium'
            )
            
            # Update employee stats
            assigned_to.pending_tasks += 1
            assigned_to.total_tasks += 1
            assigned_to.save()
            
            created_tasks.append(task)
        
        if not created_tasks:
            return Response({
                "error": "No employees available for task assignment"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = TaskListSerializer(created_tasks, many=True)
        return Response({
            "message": f"Created {len(created_tasks)} tasks for order {order.order_id}",
            "tasks": serializer.data
        }, status=status.HTTP_201_CREATED)


# ============= MY TASKS VIEW (For Employee Portal) =============

class MyTasksView(APIView):
    """
    Get tasks assigned to logged-in user's employee profile
    GET: /api/my-tasks/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get employee profile for logged-in user
        try:
            employee = Employee.objects.get(user=request.user, is_active=True)
        except Employee.DoesNotExist:
            return Response({"error": "No employee profile found"}, status=status.HTTP_404_NOT_FOUND)
        
        queryset = Task.objects.filter(assigned_to=employee)
        
        # Filter by status
        status_filter = request.query_params.get('status', '')
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        # Filter by overdue
        overdue = request.query_params.get('overdue', '')
        if overdue == 'true':
            queryset = queryset.filter(
                due_date__lt=timezone.now().date(),
                status__in=['pending', 'in_progress']
            )
        
        queryset = queryset.order_by('-priority', 'due_date', '-created_at')
        
        serializer = TaskListSerializer(queryset, many=True)
        
        # Stats for this employee
        stats = {
            'total': queryset.count(),
            'pending': queryset.filter(status='pending').count(),
            'in_progress': queryset.filter(status='in_progress').count(),
            'completed': queryset.filter(status='completed').count(),
            'overdue': queryset.filter(
                due_date__lt=timezone.now().date(),
                status__in=['pending', 'in_progress']
            ).count()
        }
        
        return Response({
            'employee': {
                'id': employee.id,
                'employee_code': employee.employee_code,
                'name': employee.user.full_name,
                'designation': employee.designation
            },
            'stats': stats,
            'tasks': serializer.data
        })


# ============= TASK DASHBOARD SUMMARY VIEW =============

class TaskDashboardView(APIView):
    """
    Get complete task dashboard summary
    GET: /api/tasks/dashboard/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Overall stats
        total_tasks = Task.objects.count()
        pending = Task.objects.filter(status='pending').count()
        in_progress = Task.objects.filter(status='in_progress').count()
        completed = Task.objects.filter(status='completed').count()
        overdue = Task.objects.filter(
            due_date__lt=timezone.now().date(),
            status__in=['pending', 'in_progress']
        ).count()
        
        # High priority tasks
        high_priority_tasks = Task.objects.filter(
            priority__in=['high', 'urgent'],
            status__in=['pending', 'in_progress']
        ).order_by('-priority', 'due_date')[:10]
        
        # Recent completed tasks
        recent_completed = Task.objects.filter(
            status='completed'
        ).order_by('-completed_at')[:10]
        
        # Employee workload
        employee_workload = Employee.objects.filter(is_active=True).values(
            'id', 'user__full_name', 'designation'
        ).annotate(
            pending_count=Count('tasks', filter=Q(tasks__status='pending')),
            in_progress_count=Count('tasks', filter=Q(tasks__status='in_progress')),
            total_active=Count('tasks', filter=Q(tasks__status__in=['pending', 'in_progress']))
        ).order_by('-total_active')[:10]
        
        # Today's due tasks
        today = timezone.now().date()
        today_due = Task.objects.filter(
            due_date=today,
            status__in=['pending', 'in_progress']
        ).count()
        
        return Response({
            'overview': {
                'total_tasks': total_tasks,
                'pending': pending,
                'in_progress': in_progress,
                'completed': completed,
                'overdue': overdue,
                'today_due': today_due,
                'completion_rate': round((completed / total_tasks * 100), 1) if total_tasks > 0 else 0
            },
            'high_priority_tasks': TaskListSerializer(high_priority_tasks, many=True).data,
            'recent_completed': TaskListSerializer(recent_completed, many=True).data,
            'employee_workload': list(employee_workload)
        })
    

# views.py - Add after Task views

# ============= NOTIFICATION VIEWS =============

from .models import Notification
from .serializers import NotificationSerializer, NotificationListSerializer

class NotificationListView(APIView):
    """
    Get all notifications for current user
    GET: /api/notifications/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(
            Q(user=request.user) | Q(user__isnull=True)
        ).order_by('-created_at')
        
        # Filter by read/unread
        read_filter = request.query_params.get('read', '')
        if read_filter == 'true':
            notifications = notifications.filter(is_read=True)
        elif read_filter == 'false':
            notifications = notifications.filter(is_read=False)
        
        # Filter by type
        notif_type = request.query_params.get('type', '')
        if notif_type:
            notifications = notifications.filter(notification_type=notif_type)
        
        serializer = NotificationListSerializer(notifications, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a notification (for system use)"""
        serializer = NotificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationDetailView(APIView):
    """
    Get, update or delete a specific notification
    GET: /api/notifications/<id>/
    PATCH: /api/notifications/<id>/ (mark as read)
    DELETE: /api/notifications/<id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        
        # Mark as read
        if request.data.get('is_read') is not None:
            notification.is_read = request.data['is_read']
            notification.save()
            return Response({"message": "Notification marked as read"})
        
        return Response({"error": "No valid fields"}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationStatsView(APIView):
    """
    Get notification statistics
    GET: /api/notifications/stats/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(
            Q(user=request.user) | Q(user__isnull=True)
        )
        
        total = notifications.count()
        unread = notifications.filter(is_read=False).count()
        read = notifications.filter(is_read=True).count()
        
        # Type wise counts
        type_stats = {}
        for notif_type, label in Notification.NOTIFICATION_TYPES:
            count = notifications.filter(notification_type=notif_type).count()
            if count > 0:
                type_stats[notif_type] = count
        
        return Response({
            'total': total,
            'unread': unread,
            'read': read,
            'type_stats': type_stats
        })


class MarkAllNotificationsReadView(APIView):
    """
    Mark all notifications as read for current user
    POST: /api/notifications/mark-all-read/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(
            Q(user=request.user) | Q(user__isnull=True),
            is_read=False
        ).update(is_read=True)
        return Response({"message": "All notifications marked as read"})


class ClearReadNotificationsView(APIView):
    """
    Delete all read notifications for current user
    DELETE: /api/notifications/clear-read/
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        Notification.objects.filter(
            Q(user=request.user) | Q(user__isnull=True),
            is_read=True
        ).delete()
        return Response({"message": "Read notifications cleared"})