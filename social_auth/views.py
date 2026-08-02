import json
import jwt
import requests
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

def verify_google_token(token):
    """Verify Google ID token and return user info"""
    try:
        # Decode without verification to get the kid
        unverified = jwt.decode(token, options={"verify_signature": False})
        
        # Get Google's public keys
        response = requests.get('https://www.googleapis.com/oauth2/v3/certs', timeout=5)
        certs = response.json()
        
        # Find the right key
        key = None
        if 'kid' in unverified:
            for k in certs.get('keys', []):
                if k.get('kid') == unverified['kid']:
                    key = k
                    break
        
        if not key and certs.get('keys'):
            key = certs['keys'][0]
        
        if not key:
            return None, 'Could not find public key'
        
        # Verify the token
        decoded = jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            audience=settings.GOOGLE_CLIENT_ID,
            options={
                'verify_aud': True,
                'verify_signature': True,
                'require': ['aud', 'iss', 'exp', 'sub']
            }
        )
        
        # Check issuer
        if decoded.get('iss') not in ['accounts.google.com', 'https://accounts.google.com']:
            return None, 'Invalid token issuer'
        
        return decoded, None
        
    except jwt.ExpiredSignatureError:
        return None, 'Token has expired'
    except jwt.InvalidTokenError as e:
        return None, f'Invalid token: {str(e)}'
    except requests.RequestException as e:
        return None, f'Network error: {str(e)}'
    except Exception as e:
        return None, f'Error verifying token: {str(e)}'

def get_or_create_user(email, user_info, is_business=False):
    """Get existing user or create new one"""
    try:
        user = User.objects.get(email=email)
        return user, False  # Existing user
    except User.DoesNotExist:
        # Create new user
        username = email.split('@')[0]
        base_username = username
        counter = 1
        
        # Make username unique
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        # Create user
        user = User.objects.create(
            username=username,
            email=email,
            first_name=user_info.get('given_name', ''),
            last_name=user_info.get('family_name', ''),
            password=make_password(User.objects.make_random_password())
        )
        
        # Add to appropriate group
        if is_business:
            business_group, _ = Group.objects.get_or_create(name='Business')
            user.groups.add(business_group)
            user.is_staff = True
            user.user_type = 'business'  # If you have this field
        else:
            user_group, _ = Group.objects.get_or_create(name='Users')
            user.groups.add(user_group)
            user.user_type = 'user'  # If you have this field
        
        user.save()
        return user, True  # New user

@csrf_exempt
def google_login(request):
    """Handle Google Login"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        token = data.get('credential')
        
        if not token:
            return JsonResponse({'success': False, 'error': 'No token provided'}, status=400)
        
        # Verify Google token
        user_info, error = verify_google_token(token)
        
        if error:
            return JsonResponse({'success': False, 'error': error}, status=400)
        
        email = user_info.get('email')
        if not email:
            return JsonResponse({'success': False, 'error': 'No email in token'}, status=400)
        
        # Get or create user
        user, is_new = get_or_create_user(email, user_info, is_business=False)
        
        # Log the user in
        login(request, user)
        
        return JsonResponse({
            'success': True,
            'is_new': is_new,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'user_type': getattr(user, 'user_type', 'user'),
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Google login error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def google_signup(request):
    """Handle Google Sign Up"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        token = data.get('credential')
        
        if not token:
            return JsonResponse({'success': False, 'error': 'No token provided'}, status=400)
        
        # Verify Google token
        user_info, error = verify_google_token(token)
        
        if error:
            return JsonResponse({'success': False, 'error': error}, status=400)
        
        email = user_info.get('email')
        if not email:
            return JsonResponse({'success': False, 'error': 'No email in token'}, status=400)
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False, 
                'error': 'An account with this email already exists. Please login instead.'
            }, status=400)
        
        # Create new user
        user, is_new = get_or_create_user(email, user_info, is_business=False)
        
        if not is_new:
            return JsonResponse({
                'success': False,
                'error': 'Account already exists. Please login.'
            }, status=400)
        
        # Log the user in
        login(request, user)
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_type': getattr(user, 'user_type', 'user'),
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Google signup error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def google_business_signup(request):
    """Handle Google Sign Up for Business"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        token = data.get('credential')
        
        if not token:
            return JsonResponse({'success': False, 'error': 'No token provided'}, status=400)
        
        # Verify Google token
        user_info, error = verify_google_token(token)
        
        if error:
            return JsonResponse({'success': False, 'error': error}, status=400)
        
        email = user_info.get('email')
        if not email:
            return JsonResponse({'success': False, 'error': 'No email in token'}, status=400)
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False, 
                'error': 'An account with this email already exists. Please login instead.'
            }, status=400)
        
        # Create new business user
        user, is_new = get_or_create_user(email, user_info, is_business=True)
        
        if not is_new:
            return JsonResponse({
                'success': False,
                'error': 'Account already exists. Please login.'
            }, status=400)
        
        # Log the user in
        login(request, user)
        
        return JsonResponse({
            'success': True,
            'redirect_to': '/admin-portal/',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_type': getattr(user, 'user_type', 'business'),
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Google business signup error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)