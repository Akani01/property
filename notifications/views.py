from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404, render
from django.db.models import Count
from django.utils import timezone
from django.core.cache import cache
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Notification, NotificationPreference, NotificationDevice, NotificationSound
from .serializers import (
    NotificationSerializer, 
    NotificationSoundSerializer, NotificationPreferenceSerializer,
    CreateNotificationSerializer, BulkNotificationSerializer,
    UpdateNotificationStatusSerializer, NotificationDeviceSerializer,
)
import logging

logger = logging.getLogger(__name__)

# Get User model
User = get_user_model()


class NotificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NotificationPagination
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        unread_count = cache.get(f"notif_unread_{request.user.id}")
        if unread_count is None:
            unread_count = Notification.objects.filter(
                recipient=request.user,
                is_read=False
            ).count()
            cache.set(f"notif_unread_{request.user.id}", unread_count, 60 * 5)
        
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'status': 'success',
                'data': {
                    'notifications': serializer.data,
                    'total_count': queryset.count(),
                    'unread_count': unread_count,
                }
            })
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': 'success',
            'data': {
                'notifications': serializer.data,
                'total_count': queryset.count(),
                'unread_count': unread_count,
            }
        })
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        notifications = self.get_queryset().filter(is_read=False)
        page = self.paginate_queryset(notifications)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'status': 'success',
                'data': {
                    'notifications': serializer.data,
                    'total_count': notifications.count(),
                    'has_unread': notifications.exists()
                }
            })
        
        serializer = self.get_serializer(notifications, many=True)
        return Response({
            'status': 'success',
            'data': {
                'notifications': serializer.data,
                'total_count': notifications.count(),
                'has_unread': notifications.exists()
            }
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        queryset = self.get_queryset()
        days = request.query_params.get('days', 30)
        
        try:
            days = int(days)
        except ValueError:
            days = 30
        
        since = timezone.now() - timezone.timedelta(days=days)
        notifications = queryset.filter(created_at__gte=since)
        
        total = notifications.count()
        unread = notifications.filter(is_read=False).count()
        read = notifications.filter(is_read=True).count()
        dismissed = notifications.filter(is_dismissed=True).count()
        
        by_type = notifications.values('notification_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        by_type_dict = {}
        for item in by_type:
            by_type_dict[item['notification_type']] = item['count']
        
        by_priority = notifications.values('priority').annotate(
            count=Count('id')
        ).order_by('-count')
        
        by_priority_dict = {}
        for item in by_priority:
            by_priority_dict[item['priority']] = item['count']
        
        recent = notifications.order_by('-created_at')[:10]
        recent_serializer = self.get_serializer(recent, many=True)
        
        return Response({
            'status': 'success',
            'data': {
                'total': total,
                'unread': unread,
                'read': read,
                'dismissed': dismissed,
                'by_type': by_type_dict,
                'by_priority': by_priority_dict,
                'recent': recent_serializer.data,
                'days': days
            }
        })
    
    @action(detail=False, methods=['get'])
    def realtime(self, request):
        """Get real-time notifications for the user - FIXED: No cache dependency"""
        try:
            # Get unread count directly from database
            unread_count = Notification.objects.filter(
                recipient=request.user, 
                is_read=False
            ).count()
            
            # Get recent notifications for realtime display (last 5)
            recent = Notification.objects.filter(
                recipient=request.user
            ).order_by('-created_at')[:5]
            
            # Serialize the notifications
            serializer = self.get_serializer(recent, many=True)
            
            return Response({
                'status': 'success',
                'data': {
                    'notifications': serializer.data,
                    'unread_count': unread_count
                }
            })
        except Exception as e:
            logger.error(f"Error getting realtime notifications: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count - FIXED: No cache dependency"""
        try:
            # Get count directly from database
            count = Notification.objects.filter(
                recipient=request.user, 
                is_read=False
            ).count()
            
            return Response({
                'status': 'success',
                'data': {
                    'count': count
                }
            })
        except Exception as e:
            logger.error(f"Error getting unread count: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_as_read()
        cache.delete(f"notif_unread_{request.user.id}")
        serializer = self.get_serializer(notification)
        return Response({
            'status': 'success',
            'message': 'Notification marked as read',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def mark_unread(self, request, pk=None):
        notification = self.get_object()
        notification.mark_as_unread()
        cache.delete(f"notif_unread_{request.user.id}")
        serializer = self.get_serializer(notification)
        return Response({
            'status': 'success',
            'message': 'Notification marked as unread',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        notification = self.get_object()
        notification.dismiss()
        cache.delete(f"notif_unread_{request.user.id}")
        serializer = self.get_serializer(notification)
        return Response({
            'status': 'success',
            'message': 'Notification dismissed',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def click(self, request, pk=None):
        notification = self.get_object()
        notification.mark_as_clicked()
        serializer = self.get_serializer(notification)
        return Response({
            'status': 'success',
            'message': 'Notification marked as clicked',
            'data': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        count = self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        cache.delete(f"notif_unread_{request.user.id}")
        return Response({
            'status': 'success',
            'message': f'{count} notifications marked as read',
            'data': {'count': count}
        })
    
    @action(detail=False, methods=['post'])
    def clear_all(self, request):
        count = self.get_queryset().count()
        self.get_queryset().delete()
        cache.delete(f"notif_unread_{request.user.id}")
        return Response({
            'status': 'success',
            'message': f'{count} notifications cleared',
            'data': {'count': count}
        })
    
    @action(detail=False, methods=['post'])
    def create_test_notification(self, request):
        """Create a test notification for the current user"""
        try:
            notification = Notification.objects.create(
                recipient=request.user,
                sender=request.user,
                notification_type='system',
                title='✅ Test Notification',
                message='This is a **test notification**. Your notifications are working!',
                formatted_message='This is a <strong>test notification</strong>. Your notifications are working!',
                action_url='/profile/',
                priority='medium',
                metadata={'test': True}
            )
            
            serializer = self.get_serializer(notification)
            return Response({
                'status': 'success',
                'message': 'Test notification created successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating test notification: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def create_notification(self, request):
        serializer = CreateNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            recipient = User.objects.get(id=serializer.validated_data['recipient_id'])
            sender = None
            if serializer.validated_data.get('sender_id'):
                sender = User.objects.get(id=serializer.validated_data['sender_id'])
            
            # Get related objects
            property_ref = None
            job = None
            booking = None
            maintenance = None
            post = None
            comment = None
            
            if serializer.validated_data.get('property_id'):
                from django.apps import apps
                Property = apps.get_model('realestate', 'Property')
                try:
                    property_ref = Property.objects.get(id=serializer.validated_data['property_id'])
                except Property.DoesNotExist:
                    pass
            
            if serializer.validated_data.get('job_id'):
                from django.apps import apps
                JobListing = apps.get_model('hiring', 'JobListing')
                try:
                    job = JobListing.objects.get(id=serializer.validated_data['job_id'])
                except JobListing.DoesNotExist:
                    pass
            
            if serializer.validated_data.get('booking_id'):
                from django.apps import apps
                Booking = apps.get_model('realestate', 'Booking')
                try:
                    booking = Booking.objects.get(id=serializer.validated_data['booking_id'])
                except Booking.DoesNotExist:
                    pass
            
            if serializer.validated_data.get('maintenance_id'):
                from django.apps import apps
                MaintenanceRequest = apps.get_model('realestate', 'MaintenanceRequest')
                try:
                    maintenance = MaintenanceRequest.objects.get(id=serializer.validated_data['maintenance_id'])
                except MaintenanceRequest.DoesNotExist:
                    pass
            
            if serializer.validated_data.get('post_id'):
                from django.apps import apps
                Post = apps.get_model('hiring', 'Post')
                try:
                    post = Post.objects.get(id=serializer.validated_data['post_id'])
                except Post.DoesNotExist:
                    pass
            
            if serializer.validated_data.get('comment_id'):
                from django.apps import apps
                Comment = apps.get_model('hiring', 'Comment')
                try:
                    comment = Comment.objects.get(id=serializer.validated_data['comment_id'])
                except Comment.DoesNotExist:
                    pass
            
            notification = Notification.objects.create(
                recipient=recipient,
                sender=sender,
                notification_type=serializer.validated_data['notification_type'],
                title=serializer.validated_data['title'],
                message=serializer.validated_data['message'],
                action_url=serializer.validated_data.get('action_url', ''),
                image_url=serializer.validated_data.get('image_url', ''),
                priority=serializer.validated_data.get('priority', 'medium'),
                metadata=serializer.validated_data.get('metadata', {}),
                property_ref=property_ref,
                job=job,
                booking=booking,
                maintenance=maintenance,
                post=post,
                comment=comment
            )
            
            # Clear unread count cache for recipient
            cache.delete(f"notif_unread_{recipient.id}")
            
            response_serializer = self.get_serializer(notification)
            return Response({
                'status': 'success',
                'message': 'Notification created successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except User.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Recipient or sender not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        serializer = BulkNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            recipient_ids = serializer.validated_data['recipient_ids']
            sender = None
            if serializer.validated_data.get('sender_id'):
                sender = User.objects.get(id=serializer.validated_data['sender_id'])
            
            exclude_self = serializer.validated_data.get('exclude_self', True)
            notifications = []
            errors = []
            
            for recipient_id in recipient_ids:
                if exclude_self and sender and str(sender.id) == str(recipient_id):
                    continue
                
                try:
                    recipient = User.objects.get(id=recipient_id)
                    notification = Notification.objects.create(
                        recipient=recipient,
                        sender=sender,
                        notification_type=serializer.validated_data['notification_type'],
                        title=serializer.validated_data['title'],
                        message=serializer.validated_data['message'],
                        action_url=serializer.validated_data.get('action_url', ''),
                        image_url=serializer.validated_data.get('image_url', ''),
                        priority=serializer.validated_data.get('priority', 'medium'),
                        metadata=serializer.validated_data.get('metadata', {})
                    )
                    notifications.append(notification)
                    
                    # Clear unread count cache for each recipient
                    cache.delete(f"notif_unread_{recipient.id}")
                    
                except Exception as e:
                    errors.append(f"Error for user {recipient_id}: {str(e)}")
            
            return Response({
                'status': 'success',
                'message': f'Successfully sent {len(notifications)} notifications',
                'data': {
                    'total_sent': len(notifications),
                    'errors': errors
                }
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating bulk notifications: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)
    
    def get_object(self):
        obj, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj
    
    def list(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'status': 'success',
            'data': serializer.data
        })
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'status': 'success',
            'data': serializer.data
        })
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'status': 'success',
            'message': 'Preferences updated successfully',
            'data': serializer.data
        })
    
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'])
    def reset_defaults(self, request):
        instance = self.get_object()
        default_pref = NotificationPreference()
        
        for field in instance._meta.fields:
            if field.name not in ['id', 'user', 'created_at', 'updated_at']:
                setattr(instance, field.name, getattr(default_pref, field.name))
        
        instance.save()
        serializer = self.get_serializer(instance)
        return Response({
            'status': 'success',
            'message': 'Preferences reset to defaults',
            'data': serializer.data
        })


class NotificationDeviceViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationDeviceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return NotificationDevice.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        device_id = request.data.get('device_id')
        if device_id:
            existing = NotificationDevice.objects.filter(
                user=request.user,
                device_id=device_id
            ).first()
            
            if existing:
                for key, value in request.data.items():
                    if key in ['registration_token', 'endpoint', 'p256dh', 'auth']:
                        setattr(existing, key, value)
                existing.is_active = True
                existing.save()
                serializer = self.get_serializer(existing)
                return Response({
                    'status': 'success',
                    'message': 'Device updated successfully',
                    'data': serializer.data
                })
        
        serializer.save(user=request.user)
        return Response({
            'status': 'success',
            'message': 'Device registered successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def unregister(self, request):
        device_id = request.data.get('device_id')
        if not device_id:
            return Response({
                'status': 'error',
                'message': 'device_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            device = NotificationDevice.objects.get(
                user=request.user,
                device_id=device_id
            )
            device.delete()
            return Response({
                'status': 'success',
                'message': 'Device unregistered successfully'
            })
        except NotificationDevice.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Device not found'
            }, status=status.HTTP_404_NOT_FOUND)


class NotificationSoundViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSoundSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return NotificationSound.objects.filter(user=self.request.user)
    
    def get_object(self):
        obj, created = NotificationSound.objects.get_or_create(
            user=self.request.user
        )
        return obj
    
    def list(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'status': 'success',
            'data': serializer.data
        })
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'status': 'success',
            'data': serializer.data
        })
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'status': 'success',
            'message': 'Sound preferences updated successfully',
            'data': serializer.data
        })
    
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


# ============================================================
# HTML PAGE VIEWS
# ============================================================

@login_required
def notifications_page(request):
    """Render the notifications page"""
    return render(request, 'notifications/notifications.html', {
        'user': request.user,
        'page_title': 'Notifications'
    })


@login_required
def notification_preferences_page(request):
    """Render the notification preferences page"""
    # Get user preferences
    preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
    sound_pref, created = NotificationSound.objects.get_or_create(user=request.user)
    
    # Get unread count
    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    # Get all notification types for the dropdown
    notification_types = [
        {'value': 'job_application', 'label': 'Job Application'},
        {'value': 'job_alert', 'label': 'Job Alert'},
        {'value': 'post_like', 'label': 'Post Like'},
        {'value': 'post_comment', 'label': 'Post Comment'},
        {'value': 'comment_reply', 'label': 'Comment Reply'},
        {'value': 'mention', 'label': 'Mention'},
        {'value': 'follow', 'label': 'Follow'},
        {'value': 'property_created', 'label': 'Property Created'},
        {'value': 'property_booked', 'label': 'Property Booked'},
        {'value': 'property_inquiry', 'label': 'Property Inquiry'},
        {'value': 'property_review', 'label': 'Property Review'},
        {'value': 'maintenance_request', 'label': 'Maintenance Request'},
        {'value': 'booking_confirmation', 'label': 'Booking Confirmation'},
        {'value': 'booking_cancellation', 'label': 'Booking Cancellation'},
        {'value': 'system', 'label': 'System'},
        {'value': 'message', 'label': 'Message'},
    ]
    
    return render(request, 'notifications/preferences.html', {
        'user': request.user,
        'preferences': preferences,
        'sound_pref': sound_pref,
        'unread_count': unread_count,
        'notification_types': notification_types,
        'page_title': 'Notification Preferences'
    })


# ============================================================
# HELPER FUNCTIONS FOR OTHER APPS TO USE
# ============================================================

def send_notification(recipient, sender=None, notification_type='system', 
                     title='', message='', action_url=None, 
                     image_url=None, priority='medium', 
                     metadata=None, **kwargs):
    """
    Helper function to send a notification from any app
    """
    try:
        notification = Notification.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
            image_url=image_url,
            priority=priority,
            metadata=metadata or {}
        )
        
        # Clear unread count cache
        cache.delete(f"notif_unread_{recipient.id}")
        
        return notification
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        return None


def send_notification_bulk(recipients, sender=None, notification_type='system',
                          title='', message='', action_url=None,
                          image_url=None, priority='medium',
                          metadata=None):
    """
    Helper function to send bulk notifications
    """
    notifications = []
    for recipient in recipients:
        notif = send_notification(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
            image_url=image_url,
            priority=priority,
            metadata=metadata
        )
        if notif:
            notifications.append(notif)
    return notifications