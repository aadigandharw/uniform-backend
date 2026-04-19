# utils/notification_helper.py
from .models import Notification

def create_notification(user, title, message, notification_type, order_id=None, order_type=None, task_id=None):
    """
    Create a notification for a user
    """
    try:
        notification = Notification.objects.create(
            user=user if user else None,
            title=title,
            message=message,
            notification_type=notification_type,
            order_id=order_id,
            order_type=order_type,
            task_id=task_id,
            is_read=False
        )
        return notification
    except Exception as e:
        print(f"Error creating notification: {e}")
        return None


def create_system_notification(title, message, notification_type='system'):
    """
    Create a system-wide notification (for all users or no specific user)
    """
    try:
        notification = Notification.objects.create(
            user=None,
            title=title,
            message=message,
            notification_type=notification_type,
            is_read=False
        )
        return notification
    except Exception as e:
        print(f"Error creating system notification: {e}")
        return None


def notify_order_ready(user, order_id, order_type):
    """Notify that order is ready"""
    return create_notification(
        user=user,
        title="Order Ready",
        message=f"Order {order_id} is READY!",
        notification_type='order_ready',
        order_id=order_id,
        order_type=order_type
    )


def notify_order_delivered(user, order_id, order_type):
    """Notify that order is delivered"""
    return create_notification(
        user=user,
        title="Order Delivered",
        message=f"Order {order_id} has been DELIVERED!",
        notification_type='order_delivered',
        order_id=order_id,
        order_type=order_type
    )


def notify_order_delayed(user, order_id, order_type, late_days):
    """Notify that order is delayed"""
    return create_notification(
        user=user,
        title="⚠️ Order Delayed",
        message=f"Order {order_id} is {late_days} days late. Please take action.",
        notification_type='order_delayed',
        order_id=order_id,
        order_type=order_type
    )


def notify_task_completed(user, task_number, task_type, order_id):
    """Notify that task is completed"""
    return create_notification(
        user=user,
        title="Task Completed",
        message=f"Task {task_number} ({task_type}) has been completed for order {order_id}",
        notification_type='task_updated',
        order_id=order_id,
        task_id=None
    )