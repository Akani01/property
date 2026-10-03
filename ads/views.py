from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly, IsAdminUser
from rest_framework.response import Response
from django.db.models import Q, Sum, Count, Avg, F
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Ad, AdImpression, AdClick, AdConversion, AdCategory
from .serializers import (
    AdSerializer, AdImpressionSerializer, AdClickSerializer, 
    AdConversionSerializer, AdStatsSerializer, AdCategorySerializer
)
from hiring.models import *
from realestate.models import *
from django.http import Http404
import uuid
from datetime import date
import logging

logger = logging.getLogger(__name__)


class AdViewSet(viewsets.ModelViewSet):
    """ViewSet for ad management"""
    queryset = Ad.objects.all()
    serializer_class = AdSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'pk'
    
    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs.get(lookup_url_kwarg)
        
        if lookup_value is None:
            raise Http404("No ad ID provided")
        
        try:
            uuid_obj = uuid.UUID(lookup_value)
            obj = queryset.get(pk=uuid_obj)
            self.check_object_permissions(self.request, obj)
            return obj
        except (ValueError, AttributeError, TypeError, Ad.DoesNotExist):
            try:
                obj = queryset.filter(
                    Q(id=lookup_value) | 
                    Q(title__iexact=lookup_value)
                ).first()
                if obj:
                    self.check_object_permissions(self.request, obj)
                    return obj
            except (Ad.DoesNotExist, AttributeError):
                pass
            
            raise Http404(f"No ad found with identifier: {lookup_value}")
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.is_staff and not user.is_superuser:
            if user.is_authenticated:
                queryset = queryset.filter(
                    Q(advertiser=user) | 
                    (Q(status=Ad.STATUS_ACTIVE) & Q(is_active=True))
                )
            else:
                queryset = queryset.filter(
                    status=Ad.STATUS_ACTIVE,
                    is_active=True
                )
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        position = self.request.query_params.get('position')
        if position:
            queryset = queryset.filter(
                Q(position=position) | Q(position=Ad.PLACEMENT_BOTH)
            )
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        
        ad_type = self.request.query_params.get('ad_type')
        if ad_type:
            queryset = queryset.filter(ad_type=ad_type)
        
        show_active = self.request.query_params.get('active', 'false').lower() == 'true'
        if show_active:
            now = timezone.now()
            queryset = queryset.filter(
                status=Ad.STATUS_ACTIVE,
                is_active=True,
                start_date__lte=now
            ).exclude(
                end_date__lt=now
            ).exclude(
                max_impressions__lte=F('impressions')
            ).exclude(
                max_clicks__lte=F('clicks')
            )
        
        featured = self.request.query_params.get('featured', 'false').lower() == 'true'
        if featured:
            queryset = queryset.filter(is_featured=True)
        
        queryset = queryset.order_by('-priority', '-created_at')
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(
            advertiser=self.request.user,
            status=Ad.STATUS_PENDING
        )
    
    def get_user_age(self, user):
        if not user or not user.is_authenticated:
            return None
        
        if hasattr(user, 'birth_date') and user.birth_date:
            today = date.today()
            return today.year - user.birth_date.year - ((today.month, today.day) < (user.birth_date.month, user.birth_date.day))
        
        if hasattr(user, 'applicantprofile') and user.applicantprofile:
            profile = user.applicantprofile
            if hasattr(profile, 'birth_date') and profile.birth_date:
                today = date.today()
                return today.year - profile.birth_date.year - ((today.month, today.day) < (profile.birth_date.month, profile.birth_date.day))
        
        if hasattr(user, 'age') and user.age:
            return user.age
        
        return None
    
    # ============================================
    # PUBLIC ENDPOINTS - Allow Anyone
    # ============================================
    
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def record_impression(self, request, pk=None):
        """Record an ad impression - Public endpoint"""
        try:
            logger.info(f"Recording impression for ad: {pk}")
            
            try:
                ad = self.get_object()
            except Http404 as e:
                logger.error(f"Ad not found: {pk}")
                return Response({
                    'success': False,
                    'message': f'Ad not found with identifier: {pk}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            try:
                if not ad.is_valid():
                    logger.warning(f"Ad is not valid: {pk}")
                    return Response({
                        'success': False,
                        'message': 'Ad is not valid or has expired'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except AttributeError:
                pass
            
            user = request.user if request.user.is_authenticated else None
            
            session_id = request.data.get('session_id')
            if not session_id:
                session_id = request.session.get('ad_session_id')
            
            if not session_id:
                session_id = str(uuid.uuid4())
                request.session['ad_session_id'] = session_id
            
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR', '0.0.0.0')
            
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            try:
                impression = ad.record_impression(
                    user=user,
                    session_id=session_id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                logger.info(f"Impression recorded successfully: {impression.id}")
                
                return Response({
                    'success': True,
                    'message': 'Impression recorded',
                    'impression_id': str(impression.id)
                }, status=status.HTTP_201_CREATED)
                
            except AttributeError as e:
                logger.error(f"record_impression method error: {str(e)}")
                try:
                    ad.impressions = (ad.impressions or 0) + 1
                    ad.save(update_fields=['impressions'])
                    logger.info(f"Manually incremented impressions for ad: {pk}")
                    return Response({
                        'success': True,
                        'message': 'Impression recorded (manual)',
                        'impression_id': None
                    }, status=status.HTTP_201_CREATED)
                except Exception as manual_error:
                    logger.error(f"Manual impression increment failed: {str(manual_error)}")
                    raise
            
        except Exception as e:
            logger.error(f"Error in record_impression: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error recording impression: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def record_click(self, request, pk=None):
        """Record an ad click - Public endpoint"""
        try:
            logger.info(f"Recording click for ad: {pk}")
            
            try:
                ad = self.get_object()
            except Http404 as e:
                logger.error(f"Ad not found: {pk}")
                return Response({
                    'success': False,
                    'message': f'Ad not found with identifier: {pk}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            try:
                if not ad.is_valid():
                    return Response({
                        'success': False,
                        'message': 'Ad is not valid or has expired'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except AttributeError:
                pass
            
            user = request.user if request.user.is_authenticated else None
            session_id = request.data.get('session_id') or request.session.get('ad_session_id')
            
            if not session_id:
                session_id = str(uuid.uuid4())
                request.session['ad_session_id'] = session_id
            
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR', '0.0.0.0')
            
            try:
                click = ad.record_click(
                    user=user,
                    session_id=session_id,
                    ip_address=ip_address,
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            except AttributeError:
                ad.clicks = (ad.clicks or 0) + 1
                ad.save(update_fields=['clicks'])
                click = None
            
            redirect_url = '/'
            if hasattr(ad, 'cta_link') and ad.cta_link:
                redirect_url = ad.cta_link
            elif hasattr(ad, 'property') and ad.property:
                if hasattr(ad.property, 'get_absolute_url'):
                    redirect_url = ad.property.get_absolute_url()
            
            return Response({
                'success': True,
                'message': 'Click recorded',
                'click_id': str(click.id) if click else None,
                'redirect_url': redirect_url
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error in record_click: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error recording click: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def record_conversion(self, request, pk=None):
        """Record a conversion from an ad - Public endpoint"""
        try:
            logger.info(f"Recording conversion for ad: {pk}")
            
            try:
                ad = self.get_object()
            except Http404 as e:
                logger.error(f"Ad not found: {pk}")
                return Response({
                    'success': False,
                    'message': f'Ad not found with identifier: {pk}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            user = request.user if request.user.is_authenticated else None
            
            session_id = request.data.get('session_id') or request.session.get('ad_session_id')
            
            if not session_id:
                return Response({
                    'success': False,
                    'message': 'Session ID required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            conversion_type = request.data.get('conversion_type', '')
            if not conversion_type:
                return Response({
                    'success': False,
                    'message': 'Conversion type required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                conversion = ad.record_conversion(
                    user=user,
                    session_id=session_id,
                    conversion_type=conversion_type,
                    value=request.data.get('value', 0)
                )
            except AttributeError:
                ad.conversions = (ad.conversions or 0) + 1
                ad.save(update_fields=['conversions'])
                conversion = None
            
            return Response({
                'success': True,
                'message': 'Conversion recorded',
                'conversion_id': str(conversion.id) if conversion else None
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error in record_conversion: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error recording conversion: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def get_active_ads(self, request):
        """Get active ads for a specific position and targeting - Public endpoint"""
        try:
            position = request.query_params.get('position', Ad.PLACEMENT_FEED)
            limit = int(request.query_params.get('limit', 10))
            
            now = timezone.now()
            queryset = Ad.objects.filter(
                status=Ad.STATUS_ACTIVE,
                is_active=True,
                start_date__lte=now
            ).exclude(
                end_date__lt=now
            ).exclude(
                max_impressions__lte=F('impressions')
            ).exclude(
                max_clicks__lte=F('clicks')
            )
            
            queryset = queryset.filter(
                Q(position=position) | Q(position=Ad.PLACEMENT_BOTH)
            )
            
            if request.user.is_authenticated:
                user = request.user
                
                if hasattr(user, 'user_type') and user.user_type:
                    queryset = queryset.filter(
                        Q(target_user_types__contains=[user.user_type]) | 
                        Q(target_user_types__isnull=True) |
                        Q(target_user_types=[])
                    )
                
                user_age = self.get_user_age(user)
                if user_age is not None:
                    queryset = queryset.filter(
                        Q(target_min_age__lte=user_age) | Q(target_min_age__isnull=True)
                    ).filter(
                        Q(target_max_age__gte=user_age) | Q(target_max_age__isnull=True)
                    )
            
            queryset = queryset.order_by('-priority', '?')[:limit]
            
            serializer = self.get_serializer(queryset, many=True)
            
            return Response({
                'success': True,
                'count': len(serializer.data),
                'ads': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error in get_active_ads: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error fetching active ads: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # ============================================
    # AUTHENTICATED ENDPOINTS - Users Only
    # ============================================
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def stats(self, request):
        """Get ad statistics for the current advertiser - Authenticated only"""
        try:
            ads = Ad.objects.filter(advertiser=request.user)
            
            total_impressions = ads.aggregate(Sum('impressions'))['impressions__sum'] or 0
            total_clicks = ads.aggregate(Sum('clicks'))['clicks__sum'] or 0
            total_conversions = ads.aggregate(Sum('conversions'))['conversions__sum'] or 0
            total_spent = sum(float(ad.get_spent()) for ad in ads) if ads else 0
            total_revenue = ads.aggregate(Sum('conversion_value'))['conversion_value__sum'] or 0
            
            stats_data = {
                'total_ads': ads.count(),
                'active_ads': ads.filter(status=Ad.STATUS_ACTIVE).count(),
                'pending_ads': ads.filter(status=Ad.STATUS_PENDING).count(),
                'rejected_ads': ads.filter(status=Ad.STATUS_REJECTED).count(),
                'expired_ads': ads.filter(status=Ad.STATUS_EXPIRED).count(),
                'total_impressions': total_impressions,
                'total_clicks': total_clicks,
                'total_conversions': total_conversions,
                'click_through_rate': (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
                'conversion_rate': (total_conversions / total_clicks * 100) if total_clicks > 0 else 0,
                'total_spent': float(total_spent),
                'total_revenue': float(total_revenue),
                'roi': ((total_revenue - total_spent) / total_spent * 100) if total_spent > 0 else 0,
                'cost_per_click': (total_spent / total_clicks) if total_clicks > 0 else 0,
                'cost_per_impression': (total_spent / total_impressions) if total_impressions > 0 else 0,
                'revenue_per_click': (total_revenue / total_clicks) if total_clicks > 0 else 0,
            }
            
            return Response(stats_data)
            
        except Exception as e:
            logger.error(f"Error in stats: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error fetching stats: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def categories(self, request):
        """Get all ad categories - Authenticated only"""
        try:
            categories = AdCategory.objects.filter(is_active=True)
            serializer = AdCategorySerializer(categories, many=True)
            return Response({
                'success': True,
                'categories': serializer.data
            })
        except Exception as e:
            logger.error(f"Error in categories: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error fetching categories: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # ============================================
    # ADMIN ONLY ENDPOINTS - Staff/Superuser Only
    # ============================================
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve an ad - Admin only"""
        try:
            ad = self.get_object()
            
            if ad.status == Ad.STATUS_ACTIVE:
                return Response({
                    'success': False,
                    'message': 'Ad is already approved'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            ad.status = Ad.STATUS_ACTIVE
            ad.approved_at = timezone.now()
            ad.approved_by = request.user
            ad.is_verified = True
            ad.save()
            
            return Response({
                'success': True,
                'message': 'Ad approved successfully'
            })
            
        except Ad.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Ad not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in approve: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error approving ad: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        """Reject an ad - Admin only"""
        try:
            ad = self.get_object()
            
            if ad.status == Ad.STATUS_REJECTED:
                return Response({
                    'success': False,
                    'message': 'Ad is already rejected'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            notes = request.data.get('notes', '')
            if not notes:
                return Response({
                    'success': False,
                    'message': 'Rejection notes are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            ad.status = Ad.STATUS_REJECTED
            ad.review_notes = notes
            ad.reviewed_at = timezone.now()
            ad.save()
            
            return Response({
                'success': True,
                'message': 'Ad rejected',
                'notes': notes
            })
            
        except Ad.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Ad not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in reject: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error rejecting ad: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def pause(self, request, pk=None):
        """Pause an ad - Admin only"""
        try:
            ad = self.get_object()
            
            if ad.status == Ad.STATUS_PAUSED:
                return Response({
                    'success': False,
                    'message': 'Ad is already paused'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            ad.status = Ad.STATUS_PAUSED
            ad.is_active = False
            ad.save()
            
            return Response({
                'success': True,
                'message': 'Ad paused successfully'
            })
            
        except Ad.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Ad not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in pause: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error pausing ad: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def unpause(self, request, pk=None):
        """Unpause an ad - Admin only"""
        try:
            ad = self.get_object()
            
            if ad.status != Ad.STATUS_PAUSED:
                return Response({
                    'success': False,
                    'message': 'Ad is not paused'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            ad.status = Ad.STATUS_ACTIVE
            ad.is_active = True
            ad.save()
            
            return Response({
                'success': True,
                'message': 'Ad unpaused successfully'
            })
            
        except Ad.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Ad not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in unpause: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error unpausing ad: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAdminUser])
    def soft_delete(self, request, pk=None):
        """Soft delete an ad - Admin only"""
        try:
            ad = self.get_object()
            ad.is_active = False
            ad.status = Ad.STATUS_DELETED
            ad.save()
            
            return Response({
                'success': True,
                'message': 'Ad soft deleted successfully'
            })
            
        except Ad.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Ad not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in soft_delete: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error deleting ad: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdImpressionViewSet(viewsets.ModelViewSet):
    queryset = AdImpression.objects.all()
    serializer_class = AdImpressionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.queryset.filter(ad__advertiser=self.request.user)


class AdClickViewSet(viewsets.ModelViewSet):
    queryset = AdClick.objects.all()
    serializer_class = AdClickSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.queryset.filter(ad__advertiser=self.request.user)


class AdConversionViewSet(viewsets.ModelViewSet):
    queryset = AdConversion.objects.all()
    serializer_class = AdConversionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.queryset.filter(ad__advertiser=self.request.user)