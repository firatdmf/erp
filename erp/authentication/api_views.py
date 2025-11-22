from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.hashers import make_password, check_password
from .models import WebClient, ClientAddress, Favorite
import json


@csrf_exempt
def create_web_client(request):
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    """Create a new web client account"""
    try:
        data = json.loads(request.body)
        
        # Validation
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        
        if not all([username, email, password, name]):
            return JsonResponse({
                'error': 'All fields (username, email, password, name) are required'
            }, status=400)
        
        # Check if username already exists
        if WebClient.objects.filter(username=username).exists():
            return JsonResponse({
                'error': 'Username already taken'
            }, status=409)
        
        # Check if email already exists
        if WebClient.objects.filter(email=email).exists():
            return JsonResponse({
                'error': 'Email already registered'
            }, status=409)
        
        # Hash password
        hashed_password = make_password(password)
        
        # Create web client
        web_client = WebClient.objects.create(
            username=username,
            email=email,
            password=hashed_password,
            name=name
        )
        
        return JsonResponse({
            'message': 'Account created successfully',
            'user': {
                'id': web_client.id,
                'username': web_client.username,
                'email': web_client.email,
                'name': web_client.name,
                'created_at': web_client.created_at.isoformat()
            }
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
def add_client_address(request, user_id):
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    """Add a new address for client"""
    try:
        data = json.loads(request.body)
        
        web_client = WebClient.objects.get(id=user_id)
        
        # Validate required fields
        if not all([data.get('title'), data.get('address'), data.get('city'), data.get('country')]):
            return JsonResponse({
                'error': 'Title, address, city, and country are required'
            }, status=400)
        
        # Check if this should be the first/default address
        is_first = not ClientAddress.objects.filter(client=web_client).exists()
        
        address = ClientAddress.objects.create(
            client=web_client,
            title=data['title'],
            address=data['address'],
            city=data['city'],
            country=data['country'],
            is_default=is_first or data.get('isDefault', False)
        )
        
        response = JsonResponse({
            'message': 'Address added successfully',
            'address': {
                'id': str(address.id),
                'title': address.title,
                'address': address.address,
                'city': address.city,
                'country': address.country,
                'isDefault': address.is_default,
            }
        }, status=201)
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    except WebClient.DoesNotExist:
        return JsonResponse({
            'error': 'User not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
def set_default_address(request, user_id, address_id):
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    """Set an address as default"""
    try:
        web_client = WebClient.objects.get(id=user_id)
        address = ClientAddress.objects.get(id=address_id, client=web_client)
        
        # Set as default (save method will handle unsetting others)
        address.is_default = True
        address.save()
        
        response = JsonResponse({
            'message': 'Default address updated successfully'
        }, status=200)
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    except WebClient.DoesNotExist:
        return JsonResponse({
            'error': 'User not found'
        }, status=404)
    except ClientAddress.DoesNotExist:
        return JsonResponse({
            'error': 'Address not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
def delete_client_address(request, user_id, address_id):
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    """Delete a client address"""
    try:
        web_client = WebClient.objects.get(id=user_id)
        address = ClientAddress.objects.get(id=address_id, client=web_client)
        
        # Check if it's the default address
        was_default = address.is_default
        address.delete()
        
        # If deleted address was default, set another as default
        if was_default:
            first_address = ClientAddress.objects.filter(client=web_client).first()
            if first_address:
                first_address.is_default = True
                first_address.save()
        
        response = JsonResponse({
            'message': 'Address deleted successfully'
        }, status=200)
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    except WebClient.DoesNotExist:
        return JsonResponse({
            'error': 'User not found'
        }, status=404)
    except ClientAddress.DoesNotExist:
        return JsonResponse({
            'error': 'Address not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
def login_web_client(request):
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    """Login web client"""
    try:
        data = json.loads(request.body)
        
        username = data.get('username')
        password = data.get('password')
        
        if not all([username, password]):
            return JsonResponse({
                'error': 'Username and password are required'
            }, status=400)
        
        # Get user
        try:
            web_client = WebClient.objects.get(username=username)
        except WebClient.DoesNotExist:
            return JsonResponse({
                'error': 'Invalid credentials'
            }, status=401)
        
        # Check if account is active
        if not web_client.is_active:
            return JsonResponse({
                'error': 'Account is inactive'
            }, status=403)
        
        # Verify password
        if not check_password(password, web_client.password):
            return JsonResponse({
                'error': 'Invalid credentials'
            }, status=401)
        
        return JsonResponse({
            'message': 'Login successful',
            'user': {
                'id': web_client.id,
                'username': web_client.username,
                'email': web_client.email,
                'name': web_client.name
            }
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def check_web_client_email(request):
    """Check if email exists (for Google OAuth)"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        
        if not email:
            return JsonResponse({
                'error': 'Email is required'
            }, status=400)
        
        exists = WebClient.objects.filter(email=email).exists()
        
        if exists:
            web_client = WebClient.objects.get(email=email)
            return JsonResponse({
                'exists': True,
                'user': {
                    'id': web_client.id,
                    'username': web_client.username,
                    'email': web_client.email,
                    'name': web_client.name
                }
            }, status=200)
        else:
            return JsonResponse({
                'exists': False
            }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_google_client(request):
    """Create web client from Google OAuth"""
    try:
        data = json.loads(request.body)
        
        email = data.get('email')
        name = data.get('name')
        
        if not email:
            return JsonResponse({
                'error': 'Email is required'
            }, status=400)
        
        # Check if already exists
        if WebClient.objects.filter(email=email).exists():
            web_client = WebClient.objects.get(email=email)
            return JsonResponse({
                'message': 'User already exists',
                'user': {
                    'id': web_client.id,
                    'username': web_client.username,
                    'email': web_client.email,
                    'name': web_client.name
                }
            }, status=200)
        
        # Create username from email
        username = email.split('@')[0]
        counter = 1
        original_username = username
        while WebClient.objects.filter(username=username).exists():
            username = f"{original_username}_{counter}"
            counter += 1
        
        # Create web client (no password needed for OAuth users)
        web_client = WebClient.objects.create(
            username=username,
            email=email,
            password=make_password(None),  # Dummy password
            name=name or 'Google User'
        )
        
        return JsonResponse({
            'message': 'Account created successfully',
            'user': {
                'id': web_client.id,
                'username': web_client.username,
                'email': web_client.email,
                'name': web_client.name
            }
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
def get_web_client_profile(request, user_id):
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    """Get web client profile information"""
    try:
        web_client = WebClient.objects.get(id=user_id)
        
        # Get all addresses for this client
        addresses = ClientAddress.objects.filter(client=web_client)
        addresses_data = [{
            'id': str(addr.id),
            'title': addr.title,
            'address': addr.address,
            'city': addr.city,
            'country': addr.country,
            'isDefault': addr.is_default,
        } for addr in addresses]
        
        response = JsonResponse({
            'id': web_client.id,
            'username': web_client.username,
            'email': web_client.email,
            'name': web_client.name or '',
            'phone': web_client.phone or '',
            'birthdate': web_client.birthdate.isoformat() if web_client.birthdate else '',
            'addresses': addresses_data,
        }, status=200)
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    except WebClient.DoesNotExist:
        return JsonResponse({
            'error': 'User not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
def update_web_client_profile(request, user_id):
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, PUT, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method not in ['POST', 'PUT']:
        response = JsonResponse({'error': 'Method not allowed'}, status=405)
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    """Update web client profile information"""
    try:
        data = json.loads(request.body)
        
        web_client = WebClient.objects.get(id=user_id)
        
        # Update fields if provided
        if 'name' in data:
            web_client.name = data['name']
        if 'phone' in data:
            web_client.phone = data['phone']
        if 'birthdate' in data:
            # Handle birthdate - can be empty string, None, or a date
            birthdate_value = data['birthdate']
            if birthdate_value and birthdate_value != '':
                # Parse date string to ensure valid format
                from datetime import datetime
                try:
                    # Try parsing ISO format (YYYY-MM-DD)
                    parsed_date = datetime.strptime(birthdate_value, '%Y-%m-%d').date()
                    web_client.birthdate = parsed_date
                except ValueError as e1:
                    # If parsing fails, try datetime.fromisoformat
                    try:
                        parsed_date = datetime.fromisoformat(birthdate_value.replace('Z', '+00:00')).date()
                        web_client.birthdate = parsed_date
                    except Exception as e2:
                        # If all parsing fails, return error
                        print(f"Error parsing birthdate: {birthdate_value}, Error1: {e1}, Error2: {e2}")
                        response = JsonResponse({
                            'error': f'Invalid birthdate format. Expected YYYY-MM-DD, got: {birthdate_value}'
                        }, status=400)
                        response["Access-Control-Allow-Origin"] = "*"
                        return response
            else:
                web_client.birthdate = None
        
        web_client.save()
        
        response = JsonResponse({
            'message': 'Profile updated successfully',
            'user': {
                'id': web_client.id,
                'name': web_client.name,
                'phone': web_client.phone,
                'birthdate': web_client.birthdate.isoformat() if web_client.birthdate else None,
            }
        }, status=200)
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    except WebClient.DoesNotExist:
        response = JsonResponse({
            'error': 'User not found'
        }, status=404)
        response["Access-Control-Allow-Origin"] = "*"
        return response
    except json.JSONDecodeError:
        response = JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
        response["Access-Control-Allow-Origin"] = "*"
        return response
    except Exception as e:
        import traceback
        print(f"Error updating profile: {str(e)}")
        print(traceback.format_exc())
        response = JsonResponse({
            'error': str(e)
        }, status=500)
        response["Access-Control-Allow-Origin"] = "*"
        return response


@csrf_exempt
def change_password(request, user_id):
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    """Change web client password"""
    try:
        data = json.loads(request.body)
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not all([current_password, new_password]):
            return JsonResponse({
                'error': 'Current password and new password are required'
            }, status=400)
        
        web_client = WebClient.objects.get(id=user_id)
        
        # Verify current password
        if not check_password(current_password, web_client.password):
            return JsonResponse({
                'error': 'Current password is incorrect'
            }, status=401)
        
        # Update password
        web_client.password = make_password(new_password)
        web_client.save()
        
        response = JsonResponse({
            'message': 'Password changed successfully'
        }, status=200)
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    except WebClient.DoesNotExist:
        return JsonResponse({
            'error': 'User not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


# ==================== FAVORITE API ENDPOINTS ====================

@csrf_exempt
def get_user_favorites(request, user_id):
    """Get all favorites for a user"""
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        web_client = WebClient.objects.get(id=user_id)
        favorites = Favorite.objects.filter(client=web_client)
        
        favorite_list = [{
            'id': fav.id,
            'product_sku': fav.product_sku,
            'created_at': fav.created_at.isoformat()
        } for fav in favorites]
        
        response = JsonResponse({
            'favorites': favorite_list
        }, status=200)
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    except WebClient.DoesNotExist:
        return JsonResponse({
            'error': 'User not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
def toggle_favorite(request, user_id):
    """Add or remove a product from favorites"""
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        product_sku = data.get('product_sku')
        
        if not product_sku:
            return JsonResponse({
                'error': 'product_sku is required'
            }, status=400)
        
        web_client = WebClient.objects.get(id=user_id)
        
        # Check if already favorited
        favorite = Favorite.objects.filter(client=web_client, product_sku=product_sku).first()
        
        if favorite:
            # Remove from favorites
            favorite.delete()
            response = JsonResponse({
                'message': 'Removed from favorites',
                'is_favorited': False
            }, status=200)
        else:
            # Add to favorites
            Favorite.objects.create(client=web_client, product_sku=product_sku)
            response = JsonResponse({
                'message': 'Added to favorites',
                'is_favorited': True
            }, status=201)
        
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    except WebClient.DoesNotExist:
        return JsonResponse({
            'error': 'User not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
def check_favorite(request, user_id, product_sku):
    """Check if a product is favorited by user"""
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        web_client = WebClient.objects.get(id=user_id)
        is_favorited = Favorite.objects.filter(client=web_client, product_sku=product_sku).exists()
        
        response = JsonResponse({
            'is_favorited': is_favorited
        }, status=200)
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    except WebClient.DoesNotExist:
        return JsonResponse({
            'error': 'User not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


# ==================== CART API ENDPOINTS ====================

@csrf_exempt
def get_cart(request, user_id):
    """Get all cart items for a user"""
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from .models import CartItem
        web_client = WebClient.objects.get(id=user_id)
        cart_items = CartItem.objects.filter(client=web_client)
        
        cart_list = [{
            'id': item.id,
            'product_sku': item.product_sku,
            'variant_sku': item.variant_sku,
            'quantity': str(item.quantity),
            'is_custom_curtain': item.is_custom_curtain,
            'custom_attributes': item.custom_attributes,
            'custom_price': str(item.custom_price) if item.custom_price else None,
            'created_at': item.created_at.isoformat(),
            'updated_at': item.updated_at.isoformat()
        } for item in cart_items]
        
        response = JsonResponse({
            'cart_items': cart_list
        }, status=200)
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    except WebClient.DoesNotExist:
        return JsonResponse({
            'error': 'User not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
def add_to_cart(request, user_id):
    """Add or update item in cart"""
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from .models import CartItem
        from decimal import Decimal
        
        data = json.loads(request.body)
        product_sku = data.get('product_sku')
        variant_sku = data.get('variant_sku', None)
        quantity = data.get('quantity', '1.0')
        
        # Custom Curtain fields
        is_custom_curtain = data.get('is_custom_curtain', False)
        custom_attributes = data.get('custom_attributes', None)
        custom_price = data.get('custom_price', None)
        
        if not product_sku:
            return JsonResponse({
                'error': 'product_sku is required'
            }, status=400)
        
        # Convert quantity to Decimal
        try:
            quantity = Decimal(str(quantity))
            if quantity <= 0:
                return JsonResponse({
                    'error': 'Quantity must be positive'
                }, status=400)
        except:
            return JsonResponse({
                'error': 'Invalid quantity format'
            }, status=400)
        
        # Convert custom_price to Decimal if provided
        if custom_price is not None:
            try:
                custom_price = Decimal(str(custom_price))
            except:
                return JsonResponse({
                    'error': 'Invalid custom_price format'
                }, status=400)
        
        web_client = WebClient.objects.get(id=user_id)
        
        # For custom curtains, always create a new item (each is unique)
        if is_custom_curtain:
            cart_item = CartItem.objects.create(
                client=web_client,
                product_sku=product_sku,
                variant_sku=variant_sku,
                quantity=quantity,
                is_custom_curtain=True,
                custom_attributes=custom_attributes,
                custom_price=custom_price
            )
            message = 'Custom curtain added to cart'
        else:
            # Check if regular item already exists
            cart_item = CartItem.objects.filter(
                client=web_client, 
                product_sku=product_sku,
                variant_sku=variant_sku,
                is_custom_curtain=False
            ).first()
            
            if cart_item:
                # Update quantity (add to existing)
                cart_item.quantity += quantity
                cart_item.save()
                message = 'Cart item updated'
            else:
                # Create new cart item
                cart_item = CartItem.objects.create(
                    client=web_client,
                    product_sku=product_sku,
                    variant_sku=variant_sku,
                    quantity=quantity
                )
                message = 'Added to cart'
        
        response = JsonResponse({
            'message': message,
            'cart_item': {
                'id': cart_item.id,
                'product_sku': cart_item.product_sku,
                'variant_sku': cart_item.variant_sku,
                'quantity': str(cart_item.quantity),
                'is_custom_curtain': cart_item.is_custom_curtain,
                'custom_attributes': cart_item.custom_attributes,
                'custom_price': str(cart_item.custom_price) if cart_item.custom_price else None
            }
        }, status=201)
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    except WebClient.DoesNotExist:
        return JsonResponse({
            'error': 'User not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
def update_cart_item(request, user_id, item_id):
    """Update cart item quantity"""
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "PUT, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method != 'PUT':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from .models import CartItem
        from decimal import Decimal
        
        data = json.loads(request.body)
        quantity = data.get('quantity')
        
        if not quantity:
            return JsonResponse({
                'error': 'quantity is required'
            }, status=400)
        
        # Convert quantity to Decimal
        try:
            quantity = Decimal(str(quantity))
            if quantity <= 0:
                return JsonResponse({
                    'error': 'Quantity must be positive'
                }, status=400)
        except:
            return JsonResponse({
                'error': 'Invalid quantity format'
            }, status=400)
        
        web_client = WebClient.objects.get(id=user_id)
        cart_item = CartItem.objects.get(id=item_id, client=web_client)
        
        cart_item.quantity = quantity
        cart_item.save()
        
        response = JsonResponse({
            'message': 'Cart item updated',
            'cart_item': {
                'id': cart_item.id,
                'product_sku': cart_item.product_sku,
                'variant_sku': cart_item.variant_sku,
                'quantity': str(cart_item.quantity)
            }
        }, status=200)
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    except WebClient.DoesNotExist:
        return JsonResponse({
            'error': 'User not found'
        }, status=404)
    except CartItem.DoesNotExist:
        return JsonResponse({
            'error': 'Cart item not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
def remove_from_cart(request, user_id, item_id):
    """Remove item from cart"""
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from .models import CartItem
        
        web_client = WebClient.objects.get(id=user_id)
        cart_item = CartItem.objects.get(id=item_id, client=web_client)
        
        cart_item.delete()
        
        response = JsonResponse({
            'message': 'Removed from cart'
        }, status=200)
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    except WebClient.DoesNotExist:
        return JsonResponse({
            'error': 'User not found'
        }, status=404)
    except CartItem.DoesNotExist:
        return JsonResponse({
            'error': 'Cart item not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
def clear_cart(request, user_id):
    """Clear all items from user's cart"""
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from .models import CartItem
        
        web_client = WebClient.objects.get(id=user_id)
        deleted_count, _ = CartItem.objects.filter(client=web_client).delete()
        
        response = JsonResponse({
            'message': 'Cart cleared successfully',
            'deleted_items': deleted_count
        }, status=200)
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    except WebClient.DoesNotExist:
        return JsonResponse({
            'error': 'User not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)
