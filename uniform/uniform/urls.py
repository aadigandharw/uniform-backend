"""
URL configuration for uniform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# uniform/urls.py

from django.contrib import admin
from django.urls import path
from uniform_app import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Auth URLs
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('users/', views.UserListView.as_view(), name='users'),
    path('approve-user/<int:id>/', views.ApproveUserView.as_view(), name='approve-user'),
    path('update-user/<int:id>/', views.UpdateUserView.as_view(), name='update-user'),
    path('me/', views.MeView.as_view(), name='me'),
    
    # ✅ Toggle User Status (Yeh add karna mat bhoolna)
    path('toggle-user-status/<int:id>/', views.ToggleUserStatusView.as_view(), name='toggle-user-status'),
    
    # Customer URLs
    path('customer/', views.CustomerListView.as_view(), name='customer-list'),
    path('customer/<int:pk>/', views.CustomerDetailView.as_view(), name='customer-detail'),
    path('customer/stats/', views.CustomerStatsView.as_view(), name='customer-stats'),
    path('customer/<int:pk>/toggle-status/', views.CustomerToggleStatusView.as_view(), name='customer-toggle-status'),
    path('customer/<int:pk>/orders/', views.CustomerOrdersView.as_view(), name='customer-orders'),

    # RM Order URLs
    path('rm-orders/', views.RMOrderListView.as_view(), name='rm-order-list'),
    path('rm-orders/<int:pk>/', views.RMOrderDetailView.as_view(), name='rm-order-detail'),
    path('rm-orders/stats/', views.RMOrderStatsView.as_view(), name='rm-order-stats'),
    path('rm-orders/<int:pk>/status/', views.RMOrderStatusUpdateView.as_view(), name='rm-order-status'),

    # MS Orders - 🔥 YEH ADD KARO
    path('ms-orders/', views.MSOrderListView.as_view()),
    path('ms-orders/<int:pk>/', views.MSOrderDetailView.as_view()),
    path('ms-orders/stats/', views.MSOrderStatsView.as_view()),
    path('ms-orders/<int:pk>/status/', views.MSOrderStatusUpdateView.as_view()),

    
    # ============ QUOTATION URLs ============
    path('quotations/', views.QuotationListView.as_view(), name='quotation-list'),
    path('quotations/<int:pk>/', views.QuotationDetailView.as_view(), name='quotation-detail'),
    path('quotations/<int:pk>/convert-to-order/', views.QuotationConvertToOrderView.as_view(), name='quotation-convert-to-order'),
    path('quotations/<int:pk>/update-status/', views.QuotationUpdateStatusView.as_view(), name='quotation-update-status'),
    path('quotations/stats/', views.QuotationStatsView.as_view(), name='quotation-stats'),


    # Vendor URLs
    path('vendors/', views.VendorListView.as_view(), name='vendor-list'),
    path('vendors/<int:pk>/', views.VendorDetailView.as_view(), name='vendor-detail'),
    path('vendors/<int:pk>/toggle-status/', views.VendorToggleStatusView.as_view(), name='vendor-toggle-status'),
    path('vendors/stats/', views.VendorStatsView.as_view(), name='vendor-stats'),
    path('vendors/<int:pk>/purchase-history/', views.VendorPurchaseHistoryView.as_view(), name='vendor-purchase-history'),
    path('vendor-categories/', views.VendorCategoryListView.as_view(), name='vendor-categories'),

    # Purchase Order URLs
    path('purchase-orders/', views.PurchaseOrderListView.as_view(), name='purchase-order-list'),
    path('purchase-orders/<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='purchase-order-detail'),
    path('purchase-orders/<int:pk>/status/', views.PurchaseOrderStatusUpdateView.as_view(), name='purchase-order-status'),
    path('purchase-orders/stats/', views.PurchaseOrderStatsView.as_view(), name='purchase-order-stats'),
    # ============= PRODUCT CATALOG URLs =============

    # Product Categories
    path('product-categories/', views.ProductCategoryListView.as_view(), name='product-categories'),
    path('product-categories/<int:pk>/', views.ProductCategoryDetailView.as_view(), name='product-category-detail'),

    # Products
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('products/<int:pk>/toggle-status/', views.ProductToggleStatusView.as_view(), name='product-toggle-status'),
    path('products/stats/', views.ProductStatsView.as_view(), name='product-stats'),

    # School Product Pricing
    path('products/<int:product_id>/school-prices/', views.SchoolProductPriceView.as_view(), name='product-school-prices'),

        # Employees
    path('employees/', views.EmployeeListView.as_view(), name='views.employee-list'),
    path('employees/<int:pk>/', views.EmployeeDetailView.as_view(), name='employee-detail'),
    path('employees/stats/', views.EmployeeStatsView.as_view(), name='employee-stats'),
    
    # Tasks
    path('tasks/', views.TaskListView.as_view(), name='task-list'),
    path('tasks/<int:pk>/', views.TaskDetailView.as_view(), name='task-detail'),
    path('tasks/<int:pk>/update-status/', views.TaskUpdateStatusView.as_view(), name='task-update-status'),
    path('tasks/<int:pk>/update-progress/', views.TaskUpdateProgressView.as_view(), name='task-update-progress'),
    path('tasks/<int:pk>/progress-history/', views.TaskProgressHistoryView.as_view(), name='task-progress-history'),
    path('tasks/stats/', views.TaskStatsView.as_view(), name='task-stats'),
    path('tasks/dashboard/', views.TaskDashboardView.as_view(), name='task-dashboard'),
    
    # Order Tasks
    path('orders/<str:order_type>/<str:order_id>/tasks/', views.OrderTasksView.as_view(), name='order-tasks'),
    
    # My Tasks (Employee Portal)
    path('my-tasks/', views.MyTasksView.as_view(), name='my-tasks'),

    # urls.py - Add these URLs

    # ============= NOTIFICATION URLs =============
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),
    path('notifications/stats/', views.NotificationStatsView.as_view(), name='notification-stats'),
    path('notifications/mark-all-read/', views.MarkAllNotificationsReadView.as_view(), name='notification-mark-all-read'),
    path('notifications/clear-read/', views.ClearReadNotificationsView.as_view(), name='notification-clear-read'),
]


# ✅ Add this at the end
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
