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


class RMOrderStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        order = get_object_or_404(RMOrder, pk=pk)
        new_status = request.data.get('status')
        if not new_status:
            return Response({"error": "Status is required"}, status=400)
        order.status = new_status
        order.save()
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


class MSOrderStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        order = get_object_or_404(MSOrder, pk=pk)
        new_status = request.data.get('status')
        if not new_status:
            return Response({"error": "Status is required"}, status=400)
        order.status = new_status
        order.save()
        return Response({"message": f"Status updated to {new_status}", "status": order.status})