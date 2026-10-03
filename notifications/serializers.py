from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from .models import Notification, NotificationSound, NotificationPreference, NotificationDevice

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info for notifications"""
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email', 'avatar_url']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_avatar_url(self, obj):
        return getattr(obj, 'avatar_url', None) or '/static/images/default-avatar.png'
    

class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info for notifications"""
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email', 'avatar_url']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_avatar_url(self, obj):
        return getattr(obj, 'avatar_url', None) or '/static/images/default-avatar.png'


class NotificationSerializer(serializers.ModelSerializer):
    """Main notification serializer with computed fields"""
    
    sender = UserBasicSerializer(read_only=True)
    recipient = UserBasicSerializer(read_only=True)
    
    formatted_message = serializers.SerializerMethodField()
    icon_class = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    related_data = serializers.SerializerMethodField()
    
    # Related object IDs - using the correct field names from model
    property_id = serializers.UUIDField(source='property_ref.id', read_only=True)
    job_id = serializers.UUIDField(source='job.id', read_only=True)
    booking_id = serializers.UUIDField(source='booking.id', read_only=True)
    maintenance_id = serializers.UUIDField(source='maintenance.id', read_only=True)
    post_id = serializers.UUIDField(source='post.id', read_only=True)
    comment_id = serializers.UUIDField(source='comment.id', read_only=True)
    
    # Related object titles
    property_title = serializers.CharField(source='property_ref.title', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)
    post_title = serializers.CharField(source='post.title', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'sender', 'notification_type',
            'title', 'message', 'formatted_message',
            'is_read', 'is_clicked', 'is_dismissed',
            'action_url', 'action_label',
            'image_url', 'icon_class', 'color',
            'priority', 'metadata',
            'property_id', 'job_id', 'booking_id', 
            'maintenance_id', 'post_id', 'comment_id',
            'property_title', 'job_title', 'post_title',
            'created_at', 'updated_at', 'read_at', 'time_ago',
            'related_data'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'read_at', 'time_ago']
    
    def get_formatted_message(self, obj):
        """Get formatted message with HTML"""
        return obj.get_formatted_message()
    
    def get_icon_class(self, obj):
        """Get icon class"""
        return obj.get_icon_class()
    
    def get_color(self, obj):
        """Get color"""
        return obj.get_color()
    
    def get_time_ago(self, obj):
        """Get human-readable time ago"""
        return obj.time_ago
    
    def get_related_data(self, obj):
        """Get related object data for quick access"""
        data = {}
        
        # Property data
        if obj.property_ref:
            data['property'] = {
                'id': str(obj.property_ref.id),
                'title': obj.property_ref.title,
                'image': obj.property_ref.get_main_image_url() if hasattr(obj.property_ref, 'get_main_image_url') else None,
                'price': str(obj.property_ref.base_price) if hasattr(obj.property_ref, 'base_price') and obj.property_ref.base_price else None,
                'status': getattr(obj.property_ref, 'status', None),
                'city': getattr(obj.property_ref, 'city', None),
            }
        
        # Job data
        if obj.job:
            data['job'] = {
                'id': str(obj.job.id),
                'title': obj.job.title,
                'company': obj.job.company_name if hasattr(obj.job, 'company_name') else None,
                'location': obj.job.location if hasattr(obj.job, 'location') else None,
                'salary': obj.job.salary_range if hasattr(obj.job, 'salary_range') else None,
                'status': obj.job.status if hasattr(obj.job, 'status') else None,
            }
        
        # Booking data
        if obj.booking:
            data['booking'] = {
                'id': str(obj.booking.id),
                'reference': obj.booking.booking_reference if hasattr(obj.booking, 'booking_reference') else None,
                'total': str(obj.booking.total_amount) if hasattr(obj.booking, 'total_amount') else None,
                'status': obj.booking.status if hasattr(obj.booking, 'status') else None,
                'check_in': obj.booking.check_in.isoformat() if hasattr(obj.booking, 'check_in') and obj.booking.check_in else None,
                'check_out': obj.booking.check_out.isoformat() if hasattr(obj.booking, 'check_out') and obj.booking.check_out else None,
            }
        
        # Maintenance data
        if obj.maintenance:
            data['maintenance'] = {
                'id': str(obj.maintenance.id),
                'title': obj.maintenance.title if hasattr(obj.maintenance, 'title') else None,
                'status': obj.maintenance.status if hasattr(obj.maintenance, 'status') else None,
                'priority': obj.maintenance.priority if hasattr(obj.maintenance, 'priority') else None,
            }
        
        # Post data
        if obj.post:
            data['post'] = {
                'id': str(obj.post.id),
                'title': obj.post.title,
                'type': obj.post.post_type if hasattr(obj.post, 'post_type') else None,
                'views': obj.post.views if hasattr(obj.post, 'views') else None,
            }
        
        return data


class NotificationListSerializer(serializers.Serializer):
    """Serializer for notification list with pagination"""
    notifications = NotificationSerializer(many=True)
    total_count = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    pagination = serializers.DictField()


class NotificationSoundSerializer(serializers.ModelSerializer):
    """Serializer for sound preferences"""
    
    class Meta:
        model = NotificationSound
        fields = ['id', 'user', 'sound_enabled', 'sound_volume', 'selected_sound', 'updated_at']
        read_only_fields = ['id', 'user', 'updated_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 
            'email_notifications', 'email_application_updates', 'email_bursary_updates',
            'email_university_updates', 'email_school_updates', 'email_job_alerts',
            'email_property_updates', 'in_app_notifications', 'in_app_application_updates',
            'in_app_bursary_updates', 'in_app_university_updates', 'in_app_school_updates',
            'in_app_job_alerts', 'in_app_property_updates', 'push_notifications',
            'sound_enabled', 'sound_volume', 'selected_sound',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class NotificationDeviceSerializer(serializers.ModelSerializer):
    """Serializer for notification devices"""
    
    class Meta:
        model = NotificationDevice
        fields = [
            'id', 'user', 'device_type', 'device_id',
            'registration_token', 'endpoint', 'p256dh', 'auth',
            'is_active', 'last_used', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'last_used', 'created_at']


class CreateNotificationSerializer(serializers.Serializer):
    """Serializer for creating notifications"""
    
    recipient_id = serializers.UUIDField(required=True)
    sender_id = serializers.UUIDField(required=False, allow_null=True)
    notification_type = serializers.CharField(required=True)
    title = serializers.CharField(required=True, max_length=255)
    message = serializers.CharField(required=True)
    action_url = serializers.CharField(required=False, allow_blank=True, max_length=500)
    image_url = serializers.CharField(required=False, allow_blank=True, max_length=500)
    priority = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'urgent'],
        default='medium'
    )
    metadata = serializers.JSONField(required=False, default=dict)
    
    # Related object IDs
    property_id = serializers.UUIDField(required=False, allow_null=True)
    job_id = serializers.UUIDField(required=False, allow_null=True)
    booking_id = serializers.UUIDField(required=False, allow_null=True)
    maintenance_id = serializers.UUIDField(required=False, allow_null=True)
    post_id = serializers.UUIDField(required=False, allow_null=True)
    comment_id = serializers.UUIDField(required=False, allow_null=True)
    
    def validate_recipient_id(self, value):
        """Validate recipient exists"""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Recipient does not exist")
        return value
    
    def validate_sender_id(self, value):
        """Validate sender exists if provided"""
        if value:
            try:
                User.objects.get(id=value)
            except User.DoesNotExist:
                raise serializers.ValidationError("Sender does not exist")
        return value
    
    def create(self, validated_data):
        """Create notification from validated data"""
        from .services import NotificationService
        
        recipient = User.objects.get(id=validated_data['recipient_id'])
        sender = User.objects.get(id=validated_data['sender_id']) if validated_data.get('sender_id') else None
        
        # Get related objects if IDs provided
        related_objects = {}
        
        if validated_data.get('property_id'):
            from django.apps import apps
            Property = apps.get_model('realestate', 'Property')
            try:
                related_objects['property_ref'] = Property.objects.get(id=validated_data['property_id'])
            except Property.DoesNotExist:
                pass
        
        if validated_data.get('job_id'):
            from django.apps import apps
            JobListing = apps.get_model('hiring', 'JobListing')
            try:
                related_objects['job'] = JobListing.objects.get(id=validated_data['job_id'])
            except JobListing.DoesNotExist:
                pass
        
        if validated_data.get('booking_id'):
            from django.apps import apps
            Booking = apps.get_model('realestate', 'Booking')
            try:
                related_objects['booking'] = Booking.objects.get(id=validated_data['booking_id'])
            except Booking.DoesNotExist:
                pass
        
        if validated_data.get('maintenance_id'):
            from django.apps import apps
            MaintenanceRequest = apps.get_model('realestate', 'MaintenanceRequest')
            try:
                related_objects['maintenance'] = MaintenanceRequest.objects.get(id=validated_data['maintenance_id'])
            except MaintenanceRequest.DoesNotExist:
                pass
        
        if validated_data.get('post_id'):
            from django.apps import apps
            Post = apps.get_model('hiring', 'Post')
            try:
                related_objects['post'] = Post.objects.get(id=validated_data['post_id'])
            except Post.DoesNotExist:
                pass
        
        if validated_data.get('comment_id'):
            from django.apps import apps
            Comment = apps.get_model('hiring', 'Comment')
            try:
                related_objects['comment'] = Comment.objects.get(id=validated_data['comment_id'])
            except Comment.DoesNotExist:
                pass
        
        # Send notification using service
        notification = NotificationService.send_notification(
            recipient=recipient,
            sender=sender,
            notification_type=validated_data['notification_type'],
            title=validated_data['title'],
            message=validated_data['message'],
            action_url=validated_data.get('action_url', ''),
            image_url=validated_data.get('image_url', ''),
            priority=validated_data.get('priority', 'medium'),
            metadata=validated_data.get('metadata', {}),
            **related_objects
        )
        
        return notification


class BulkNotificationSerializer(serializers.Serializer):
    """Serializer for bulk notifications"""
    
    recipient_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True
    )
    notification_type = serializers.CharField(required=True)
    title = serializers.CharField(required=True, max_length=255)
    message = serializers.CharField(required=True)
    action_url = serializers.CharField(required=False, allow_blank=True, max_length=500)
    image_url = serializers.CharField(required=False, allow_blank=True, max_length=500)
    priority = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'urgent'],
        default='medium'
    )
    metadata = serializers.JSONField(required=False, default=dict)
    exclude_self = serializers.BooleanField(default=True)
    sender_id = serializers.UUIDField(required=False, allow_null=True)
    
    def validate_recipient_ids(self, value):
        """Validate recipients exist"""
        if not value:
            raise serializers.ValidationError("At least one recipient is required")
        
        existing_users = User.objects.filter(id__in=value)
        if existing_users.count() != len(value):
            raise serializers.ValidationError("One or more recipients do not exist")
        
        return value
    
    def create(self, validated_data):
        """Create bulk notifications"""
        from .services import NotificationService
        
        recipient_ids = validated_data['recipient_ids']
        sender = User.objects.get(id=validated_data['sender_id']) if validated_data.get('sender_id') else None
        exclude_self = validated_data.get('exclude_self', True)
        
        notifications = []
        errors = []
        
        for recipient_id in recipient_ids:
            # Skip self if exclude_self enabled
            if exclude_self and sender and str(sender.id) == str(recipient_id):
                continue
            
            try:
                recipient = User.objects.get(id=recipient_id)
                
                notification = NotificationService.send_notification(
                    recipient=recipient,
                    sender=sender,
                    notification_type=validated_data['notification_type'],
                    title=validated_data['title'],
                    message=validated_data['message'],
                    action_url=validated_data.get('action_url', ''),
                    image_url=validated_data.get('image_url', ''),
                    priority=validated_data.get('priority', 'medium'),
                    metadata=validated_data.get('metadata', {})
                )
                
                if notification:
                    notifications.append(notification)
                    
            except User.DoesNotExist:
                errors.append(f"User {recipient_id} does not exist")
                continue
            except Exception as e:
                errors.append(f"Error for user {recipient_id}: {str(e)}")
                continue
        
        return {
            'notifications': notifications,
            'errors': errors,
            'total_sent': len(notifications)
        }


class UpdateNotificationStatusSerializer(serializers.Serializer):
    """Serializer for updating notification status"""
    
    action = serializers.ChoiceField(
        choices=['mark_read', 'mark_unread', 'dismiss', 'click'],
        required=True
    )