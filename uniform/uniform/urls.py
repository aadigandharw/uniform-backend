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
]
