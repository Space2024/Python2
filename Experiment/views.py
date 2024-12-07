# views.py
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Voucher, ConcernBranchMaster, UserRoleMaster, DivisionMaster,CustomerMaster,UTRVoucher,ChitsUser
import json
import math
import random
import requests
import base64
from datetime import datetime, timedelta
import os
import boto3
import jwt
import re
import pytz
from django.conf import settings
from django.db.models import Q
from django.db.models import Count, Sum, Max, F
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum, F
from django.db import transaction
from dotenv import load_dotenv
import logging

load_dotenv() 

# Global dictionary to store OTPs
OTPS = {}

@csrf_exempt
def post_branch_details(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        voucher_id = data.get('voucherid')
        branch = data.get('branch')
        concern = data.get('concern')
        
        formatted_date = timezone.now()
        
        updated = Voucher.objects.filter(VocId=voucher_id).update(
            Branch=branch,
            concern=concern,
            status='R',
            Redeemed_Date=formatted_date
        )
        
        if updated:
            return JsonResponse({'message': 'Update successful'})
        return JsonResponse({'message': 'Voucher not found'}, status=404)
        
    except Exception as error:
        return JsonResponse({'message': 'An error occurred', 'error': str(error)}, status=500)

@csrf_exempt
def gift_voucher_api(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        voucher_type = data.get('voucherType')
        voucher_id = data.get('voucherid')
        concern = data.get('concern')
        branch = data.get('branch')
        division = data.get('division')
        
        formatted_date = timezone.now()
        
        try:
            voucher = Voucher.objects.get(VocId=voucher_id)
        except Voucher.DoesNotExist:
            return JsonResponse({'message': 'Voucher not found'}, status=404)
            
        if voucher.status == 'R':
            return JsonResponse({'message': 'Voucher already redeemed'}, status=400)
            
        if voucher_type == 'GV':
            updated = Voucher.objects.filter(VocId=voucher_id, status='P').update(
                status='R',
                Redeemed_Date=formatted_date,
                concern=concern,
                Branch=branch,
                division=division
            )
        else:
            updated = Voucher.objects.filter(VocId=voucher_id, status='P').update(
                status='R',
                Redeemed_Date=formatted_date
            )
            
        if updated:
            return JsonResponse({'message': 'Voucher Redeemed Successfully'})
        return JsonResponse({'message': 'Failed to redeem voucher'}, status=400)
        
    except Exception as error:
        return JsonResponse({'message': 'Internal server error!'}, status=500)
    

# Configure logging
logger = logging.getLogger(__name__)

# Global dictionary for OTP storage
OTPS = {}

@csrf_exempt
@require_http_methods(["GET"])
def redeem_otp(request):
    """
    API endpoint to generate and send OTP for voucher redemption
    """
    try:
        # Extract and validate user_id
        user_id = request.GET.get('userId')
        if not user_id:
            logger.error("Missing userId parameter")
            return JsonResponse({
                'status': 'error',
                'message': 'userId parameter is required'
            }, status=400)

        # Fetch voucher details with error handling
        try:
            voucher_details = Voucher.objects.get(id=user_id)
        except Voucher.DoesNotExist:
            logger.error(f"Voucher not found for ID: {user_id}")
            return JsonResponse({
                'status': 'error',
                'message': 'Voucher not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Database error while fetching voucher: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Database error occurred'
            }, status=500)

        # Check voucher status
        if voucher_details.status == 'R':
            logger.info(f"Voucher already redeemed: {user_id}")
            return JsonResponse({
                'status': 'error',
                'message': 'Voucher already redeemed'
            }, status=400)

        # Generate OTP
        otp = str(math.floor(100000 + random.random() * 900000))
        
        # Validate mobile number
        if not voucher_details.Mobile or len(str(voucher_details.Mobile)) != 10:
            logger.error(f"Invalid mobile number for voucher: {user_id}")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid mobile number'
            }, status=400)

        # Prepare SMS message
        message_text = (
            f'Dear Customer, Kindly update REFCODE: {otp} with our manager to '
            f'adjust your Gift Voucher for billing. Voucher No: {voucher_details.VocId}. '
            f'Thank U!.SKTM'
        )

        # Prepare SMS API request
        sms_data = {
            'customerId': os.getenv('SMS_CUSTOMER_ID'),
            'destinationAddress': str(voucher_details.Mobile),
            'message': message_text,
            'sourceAddress': 'SPCTXL',
            'messageType': 'SERVICE_IMPLICIT',
            'dltTemplateId': '1007436813327464092',
            'entityId': '1701158071847889480',
            'otp': True,
            'metaData': {}
        }

        # Send SMS with timeout and error handling
        try:
            response = requests.post(
                'https://iqsms.airtel.in/api/v1/send-sms',
                json=sms_data,
                auth=(os.getenv('SMS_USERNAME'), os.getenv('SMS_PASSWORD')),
                headers={'Content-Type': 'application/json'},
                timeout=10  # Add timeout
            )
            
            response.raise_for_status()  # Raise exception for non-200 status codes
            
        except requests.RequestException as e:
            logger.error(f"SMS API error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to send SMS. Please try again.'
            }, status=502)

        # Store OTP with timestamp
        OTPS[user_id] = {
            'otp': otp,
            'timestamp': datetime.now().timestamp()
        }

        logger.info(f"OTP sent successfully for voucher: {user_id}")
        return JsonResponse({
            'status': 'success',
            'message': 'OTP sent successfully'
        })

    except Exception as e:
        logger.error(f"Unexpected error in redeem_otp: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': 'An internal server error occurred'
        }, status=500)

@csrf_exempt
def verify_otp(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        user_id = data.get('userId')
        submitted_otp = data.get('otps')
        
        if user_id not in OTPS:
            return JsonResponse({'message': 'No OTP found for this user'}, status=400)
            
        stored_otp = OTPS[user_id]
        is_valid = (
            int(stored_otp['otp']) == int(submitted_otp) and
            (datetime.now().timestamp() - stored_otp['timestamp']) < 120
        )
        
        if is_valid:
            return JsonResponse({'message': 'OTP verified'})
        return JsonResponse({'message': 'Invalid or expired OTP'}, status=401)
        
    except Exception as error:
        return JsonResponse({'error': 'An error occurred while validating OTP'}, status=500)

@require_http_methods(["GET"])
def get_concern_details(request):
    try:
        # Fetch distinct concerns from the database
        concerns = ConcernBranchMaster.objects.values_list('concern', flat=True).distinct()
        
        # Format the data into a list of dictionaries
        concern_data = [{'value': concern, 'label': concern} for concern in concerns if concern]
        
        # Return the data as a JSON response
        return JsonResponse(concern_data, safe=False, status=200)
    
    except ConcernBranchMaster.DoesNotExist:
        # Handle the case where the table does not have any data
        return JsonResponse(
            {'error': 'No concerns found'},
            status=404
        )
    
    except Exception as error:
        # Catch unexpected errors
        return JsonResponse(
            {'error': 'An error occurred while fetching concern details', 'details': str(error)},
            status=500
        )

def get_branch_details(request, selected_option):
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
        
    try:
        branches = ConcernBranchMaster.objects.filter(concern=selected_option)
        sorted_branches = sorted(
            branches,
            key=lambda x: (
                ''.join(filter(str.isalpha, x.Branchid)),
                int(''.join(filter(str.isdigit, x.Branchid)))
            )
        )
        
        data = [
            {'value': branch.Branchname, 'label': branch.Branchname}
            for branch in sorted_branches
        ]
        return JsonResponse(data, safe=False)
        
    except Exception as error:
        return JsonResponse(
            {'error': 'An error occurred while fetching branch details'},
            status=500
        )

def user_role_mas(request):
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
        
    try:
        allowed_roles = [
            "Admin", "Executive_Director", "A/C_Manager", "A/C_Executive",
            "Branch_Manager", "Branch_EDP", "Branch_IA", "HO_IA"
        ]
        
        roles = UserRoleMaster.objects.values_list('RoleName', flat=True).distinct()
        filtered_roles = [role for role in roles if role in allowed_roles]
        role_data = [{'value': role, 'label': role} for role in filtered_roles]
        
        return JsonResponse(role_data, safe=False)
        
    except Exception as error:
        return JsonResponse({'error': 'An error occurred while fetching details'}, status=500)

def get_concern_details_division(request):
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
        
    try:
        concerns = DivisionMaster.objects.values_list('Cocern', flat=True).distinct()
        concern_data = [{'value': concern, 'label': concern} for concern in concerns]
        return JsonResponse(concern_data, safe=False)
        
    except Exception as error:
        return JsonResponse(
            {'error': 'An error occurred while fetching concern details'},
            status=500
        )

def get_branch_location(request, selected_option):
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
        
    try:
        branches = DivisionMaster.objects.filter(Cocern=selected_option).values_list(
            'Branch_Location', flat=True
        ).distinct()
        branch_data = [{'value': branch, 'label': branch} for branch in branches]
        
        return JsonResponse({
            'branch': branch_data,
            'message': 'Division Data fetched'
        })
        
    except Exception as error:
        return JsonResponse({'error': str(error), 'message': 'Internal server Error'}, status=500)

def get_division(request, selected_option):
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
        
    try:
        divisions = DivisionMaster.objects.filter(
            Branch_Location=selected_option,
            Status='Active'
        ).values_list('Division', flat=True).distinct()
        
        division_data = [{'value': div, 'label': div} for div in divisions]
        
        return JsonResponse({
            'division': division_data,
            'message': 'Division Data fetched'
        })
        
    except Exception as error:
        return JsonResponse({'error': str(error), 'message': 'Internal server Error'}, status=500)

def redeemed_voucher_details(request, voc_id):
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
        
    try:
        decoded_id = base64.b64decode(voc_id).decode('utf-8')
        
        try:
            redeemed_details = Voucher.objects.filter(VocId=decoded_id)
            
            if not redeemed_details:
                return JsonResponse({'message': 'Voucher details not available'}, status=404)
                
            status = redeemed_details[0].status
            
            if status == 'R':
                return JsonResponse({
                    'message': 'Voucher redeemed successfully',
                    'redeemedDetails': list(redeemed_details.values())
                })
            elif status == 'P':
                return JsonResponse({'message': 'Voucher is not redeemed'})
            elif status == 'B':
                return JsonResponse({'message': 'Voucher is already Billed'})
            else:
                return JsonResponse({'message': 'Voucher details are not available'})
                
        except Voucher.DoesNotExist:
            return JsonResponse({'message': 'Voucher details not available'}, status=404)
            
    except Exception as error:
        return JsonResponse(
            {'message': 'An error occurred while retrieving details'},
            status=500
        )
        
# Store OTP sessions in memory (consider using cache/database for production)
ia_otps = {}
sessions = {}

@require_http_methods(["PUT"])
def update_voucher_details(request):
    try:
        data = json.loads(request.body)
        voc_id = data.get('VocId')
        invoice_no = data.get('invoice_no')
        invoice_date = data.get('invoice_Date')

        decoded_string = base64.b64decode(voc_id).decode('utf-8')
        regex = r'^\d{4}-(0[1-9]|1[0-2])-\d{2}$'
        valid_date_format = bool(re.match(regex, invoice_date))

        if not valid_date_format:
            return JsonResponse({"message": "Invoice Date must be YYYY-MM-DD"}, status=400)

        voucher = Voucher.objects.filter(VocId=decoded_string).first()
        if not voucher:
            return JsonResponse({"message": "Voucher not found"}, status=400)

        if voucher.status == 'R' and voucher.Redeemed_Date:
            if invoice_no and invoice_date:
                Voucher.objects.filter(
                    VocId=decoded_string, 
                    status='R'
                ).update(
                    bill_no=invoice_no,
                    bill_date=invoice_date,
                    status='B'
                )
                return JsonResponse({"message": "Voucher details updated successfully"})
            else:
                return JsonResponse({"message": "All Fields are required"}, status=400)
        elif voucher.status == 'B':
            return JsonResponse({"message": "Voucher is already Billed"}, status=201)
        elif voucher.status == 'P':
            return JsonResponse({"message": "Voucher is not Redeemed"})
        else:
            return JsonResponse({"message": "Voucher details are not available"}, status=400)

    except Exception as error:
        print(f"Error updating voucher details: {error}")
        return JsonResponse(
            {"message": "An error occurred while updating voucher details"},
            status=500
        )

@require_http_methods(["PUT"])
def delete_voucher_details(request):
    try:
        data = json.loads(request.body)
        voc_id = data.get('VocId')
        invoice_no = data.get('invoice_no')
        invoice_date = data.get('invoice_Date')
        
        decoded_string = base64.b64decode(voc_id).decode('utf-8')
        
        delete_voucher = None
        if invoice_no == "" and invoice_date == "":
            delete_voucher = Voucher.objects.filter(VocId=decoded_string).first()

        if not delete_voucher:
            return JsonResponse({"message": "Voucher not found"}, status=404)

        if delete_voucher.status == 'B':
            formatted_date = timezone.now().astimezone(
                pytz.timezone('Asia/Kolkata')
            ).strftime('%Y-%m-%d %H:%M:%S')
            
            Voucher.objects.filter(
                VocId=decoded_string, 
                status='B'
            ).update(
                bill_no="",
                bill_date="",
                status='P',
                delete_Date=formatted_date
            )
            return JsonResponse({"message": "Voucher details deleted successfully"})
        elif delete_voucher.status == 'R':
            return JsonResponse({"message": "Voucher is not Billed"})
        else:
            return JsonResponse({"message": "Voucher is not available"})

    except Exception as error:
        print(f"Error updating voucher details: {error}")
        return JsonResponse(
            {"message": "An error occurred while updating voucher details"}, 
            status=500
        )

@require_http_methods(["GET"])
def voucher_report(request):
    try:
        branch = request.GET.get('Branch')
        concern = request.GET.get('concern')

        if not concern:
            return JsonResponse(
                {"message": "Missing required query parameter: concern"}, 
                status=400
            )

        filters = {
            'concern': concern,
            'status__in': ['B', 'V']
        }

        if branch:
            filters['Branch'] = branch

        report_details = list(Voucher.objects.filter(**filters).values())
        return JsonResponse(report_details, safe=False)

    except Exception as error:
        print(error)
        return JsonResponse(
            {"message": "An error occurred while retrieving the report details."}, 
            status=500
        )

@require_http_methods(["GET"])
def voucher_report(request):
    try:
        branch = request.GET.get('Branch')
        concern = request.GET.get('concern')

        if not concern:
            return JsonResponse({"message": "Missing required query parameter: concern"}, status=400)

        query = Q(concern=concern) & Q(status__in=['B', 'V'])
        if branch:
            query &= Q(Branch=branch)

        report_details = list(Voucher.objects.filter(query).values())
        return JsonResponse(report_details, safe=False)

    except Exception as e:
        return JsonResponse({"message": f"An error occurred: {str(e)}"}, status=500)

# Dictionary to store OTPs (In production, use Redis or similar)
ia_otps = {}

def generate_otp():
    return random.randint(100000, 999999)

@csrf_exempt
def send_ia_otp(request, concern, branch):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # Decode base64 and convert to uppercase
        concern = base64.b64decode(concern).decode('utf-8').upper()
        branch = base64.b64decode(branch).decode('utf-8').upper()
        user_id = request.GET.get('userId')

        if not user_id:
            return JsonResponse({'error': 'userId is required'}, status=400)

        # Generate OTP
        otp = generate_otp()

        # Fetch voucher details
        try:
            voucher_details = Voucher.objects.get(id=user_id)
            if voucher_details.status == 'R':
                return JsonResponse({'error': 'Voucher already redeemed'}, status=404)
        except Voucher.DoesNotExist:
            return JsonResponse({'error': 'Voucher not found'}, status=404)

        # Fetch concern ConcernBranchMaster details
        try:
            concern_branch = ConcernBranchMaster.objects.get(Concern=concern, Branchname=branch)
        except ConcernBranchMaster.DoesNotExist:
            return JsonResponse({'error': 'Concern branch not found'}, status=404)

        # Prepare SMS message
        message_text = f"Dear Internal Auditor, Verification Gift Voucher ({voucher_details.VocId}) Code :{otp}. By SPCTXL"

        # SMS data payload
        sms_data = {
            "customerId": settings.SMS_CUSTOMER_ID,
            "destinationAddress": concern_branch.IAmobile,
            "message": message_text,
            "sourceAddress": "SPCTXL",
            "messageType": "SERVICE_IMPLICIT",
            "dltTemplateId": "1007497871054360223",
            "entityId": "1701158071847889480",
            "otp": True,
            "metaData": {}
        }

        # Send SMS
        response = requests.post(
            'https://iqsms.airtel.in/api/v1/send-sms',
            json=sms_data,
            auth=(settings.SMS_USERNAME, settings.SMS_PASSWORD),
            headers={'Content-Type': 'application/json'}
        )

        # Store OTP
        ia_otps[user_id] = {
            'otp': otp,
            'timestamp': timezone.now().timestamp()
        }

        return JsonResponse({'message': 'OTP sent successfully'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def verify_ia_otp(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        user_id = data.get('id')
        submitted_otp = data.get('otps')

        if not ia_otps.get(user_id):
            return JsonResponse({'message': 'No OTP found for this user'}, status=400)

        stored_otp = ia_otps[user_id]
        current_time = timezone.now().timestamp()
        
        # Check if OTP is valid and not expired (2 minutes)
        is_valid = (str(stored_otp['otp']) == str(submitted_otp) and 
                   current_time - stored_otp['timestamp'] < 120)

        if is_valid:
            # Update voucher status
            Voucher.objects.filter(
                id=user_id, 
                status='B'
            ).update(
                status='V',
                Verified_Date=timezone.now()
            )
            return JsonResponse({'message': 'OTP verified'})
        else:
            return JsonResponse({'message': 'Invalid or expired OTP'}, status=401)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def get_ia_report(request, voucher):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        decoded_voucher = base64.b64decode(voucher).decode('utf-8')
        
        if not decoded_voucher:
            return JsonResponse({'message': 'Voucher details not found'}, status=400)

        voucher_details = list(Voucher.objects.filter(
            VocId=decoded_voucher
        ).values())

        if not voucher_details:
            return JsonResponse({'message': 'Voucher not found'}, status=404)

        return JsonResponse(voucher_details, safe=False)

    except Exception as e:
        return JsonResponse({'message': 'Internal Server Error'}, status=500)

@csrf_exempt
def voucher_reports(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        concern = request.GET.get('concern')
        branch = request.GET.get('Branch')

        if not concern:
            return JsonResponse({'error': 'Missing required query parameter: concern'}, 
                              status=400)

        # Build filter conditions
        filters = {'concern': concern}
        if branch:
            filters['Branch'] = branch

        # Fetch report details
        report_details = list(Voucher.objects.filter(**filters).values())
        
        return JsonResponse(report_details, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Dictionary to store sessions (In production, use Redis or similar)
sessions = {}

@csrf_exempt  # Add this if testing with Postman without CSRF token
@require_http_methods(["GET"])
def verify_list(request):
    try:
        # Get query parameters
        concern = request.GET.get('concern')
        voucher_type = request.GET.get('voucherType')

        # Validate required parameters
        if not voucher_type:
            return JsonResponse({
                'error': 'VoucherType parameter is required',
                'status': 'error'
            }, status=400)

        # Set default concern if not provided
        resolved_concern = concern or 'SPACE'

        # Define conditions based on voucher type
        if voucher_type == "IV":
            join_key = "branchDetails"
            status_condition = Q(status='V') | Q(status='G') | Q(status='U')
        elif voucher_type == "GV":
            join_key = "branchDetails1"
            status_condition = Q(status='R') | Q(status='G') | Q(status='U')
        else:
            return JsonResponse({
                'error': 'Invalid voucher type. Must be either "IV" or "GV"',
                'status': 'error'
            }, status=400)

        # Fetch pending list with error handling
        try:
            pending_list = Voucher.objects.filter(
                status_condition,
                voucherType=voucher_type,
                concern=resolved_concern
            ).select_related(join_key).values(
                'id', 
                'VocId', 
                'status', 
                'voucherType', 
                'concern',
                f'{join_key}__Branchname', 
                f'{join_key}__Bankaccname',
                f'{join_key}__Bankaccountnumber',
                f'{join_key}__Bankbranch',
                f'{join_key}__Bankname',
                f'{join_key}__Bankifsc',
                f'{join_key}__Branchaddress',
                f'{join_key}__Branchcity'
            )

            # Convert QuerySet to list and filter out SDH data
            filtered_data = [
                data for data in pending_list 
                if not data['VocId'] or 'SD' not in data['VocId']
            ]

            return JsonResponse({
                'status': 'success',
                'data': filtered_data,
                'count': len(filtered_data)
            }, safe=False)

        except Exception as db_error:
            return JsonResponse({
                'error': f'Database error: {str(db_error)}',
                'status': 'error'
            }, status=500)

    except Exception as e:
        return JsonResponse({
            'error': f'Server error: {str(e)}',
            'status': 'error'
        }, status=500)

@csrf_exempt
def verify(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        voc_id = data.get('VocId')
        
        if not voc_id:
            return JsonResponse({'error': 'VocId is required'}, status=400)

        # Get voucher details
        try:
            voc_details = Voucher.objects.get(VocId=voc_id)
        except Voucher.DoesNotExist:
            return JsonResponse({'error': 'Voucher not found'}, status=404)

        formatted_date = timezone.now()
        rows_updated = 0

        if voc_details.voucherType == "IV":
            rows_updated = Voucher.objects.filter(
                VocId=voc_id, 
                status='V'
            ).update(
                status='I',
                Acc_mng_Verify_date=formatted_date
            )
        elif voc_details.voucherType == "GV":
            rows_updated = Voucher.objects.filter(
                VocId=voc_id, 
                status='R'
            ).update(
                status='I',
                Acc_mng_Verify_date=formatted_date
            )

        if rows_updated > 0:
            return JsonResponse({
                'message': 'Verified successfully',
                'success': True
            })
        else:
            return JsonResponse({
                'message': 'Not verified',
                'success': False
            })

    except Exception as e:
        return JsonResponse({
            'message': 'Internal Server Error',
            'error': str(e)
        }, status=500)

@csrf_exempt
def update_record(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        voc_id = data.get('VocId')
        utr_no = data.get('UTR_No')
        utr_date = data.get('UTR_date')

        if not all([voc_id, utr_no, utr_date]):
            return JsonResponse({
                'error': 'VocId, UTR_No, and UTR_date are required'
            }, status=400)

        rows_updated = Voucher.objects.filter(
            VocId=voc_id,
            status='G'
        ).update(
            status='U',
            UTR_No=utr_no,
            UTR_date=utr_date
        )

        if rows_updated > 0:
            return JsonResponse({
                'message': 'Record updated successfully'
            })
        else:
            return JsonResponse({
                'error': 'No matching record found or already updated'
            }, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def generate_otp(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        session_id = data.get('sessionId')
        selected_vouchers = data.get('selectedVouchers')
        total_processing_amount = data.get('totalProcessingAmount')
        concern = data.get('concern')
        voucher_type = data.get('voucherType')

        if not all([session_id, selected_vouchers, total_processing_amount, concern]):
            return JsonResponse({
                'error': 'Missing required parameters'
            }, status=400)

        # Generate OTP
        otp = str(random.randint(100000, 999999))

        # Store session data
        sessions[session_id] = {
            'otp': otp,
            'timestamp': timezone.now().timestamp(),
            'selectedVouchers': selected_vouchers
        }

        # Get account manager details
        try:
            acc_manager_report = ConcernBranchMaster.objects.get(Concern=concern)
        except ConcernBranchMaster.DoesNotExist:
            return JsonResponse({
                'error': f'No branch found for concern: {concern}'
            }, status=404)

        # Prepare SMS message
        message_text = (f"Dear Sir, Total Payment for {total_processing_amount}-"
                       f"{concern} concern. Use this code {otp} for payment "
                       f"request. By SPCTXL")

        # SMS data payload
        sms_data = {
            "customerId": settings.SMS_CUSTOMER_ID,
            "destinationAddress": acc_manager_report.AccmanagerPhone,
            "message": message_text,
            "sourceAddress": "SPCTXL",
            "messageType": "SERVICE_IMPLICIT",
            "dltTemplateId": "1007470193982935312",
            "entityId": "1701158071847889480",
            "otp": True,
            "metaData": {}
        }

        # Send SMS
        response = requests.post(
            'https://iqsms.airtel.in/api/v1/send-sms',
            json=sms_data,
            auth=(settings.SMS_USERNAME, settings.SMS_PASSWORD),
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            return JsonResponse({'message': 'OTP sent successfully'})
        else:
            return JsonResponse({
                'error': 'Failed to send SMS'
            }, status=500)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Session storage (you might want to use Django's cache framework in production)
sessions = {}

async def send_whatsapp_message(message_data):
    # Implement your WhatsApp sending logic here
    pass

@require_http_methods(["POST"])
def verify_otp(request):
    try:
        data = json.loads(request.body)
        session_id = data.get('sessionId')
        otp = data.get('otp')
        total_processing_amount = data.get('totalProcessingAmount')
        voucher_type = data.get('voucherType')

        session = sessions.get(session_id)
        current_time = datetime.now().timestamp() * 1000

        if (session and session['otp'] == otp and 
            current_time - session['timestamp'] < 300000):
            
            selected_vouchers = session['selectedVouchers']
            sessions.pop(session_id, None)

            director_approval = ConcernBranchMaster.objects.first()
            link = "https://voc.spacetextiles.net/App"
            
            whatsapp_message = {
                "templateId": "01j6eq1gxdvp2rhsgh1x52tbvs",
                "recipients": [director_approval.IT_head],
                "from": os.getenv('WHATSAPP_SENDER'),
                "message": {
                    "text": f"Dear Sir, Kindly Approve the Leave Request From Our Concern {link}",
                    "variables": [link],
                    "payload": ["payload1"]
                }
            }
            
            send_whatsapp_message(whatsapp_message)
            return JsonResponse({"success": True, "selectedVouchers": selected_vouchers})
        else:
            return JsonResponse(
                {"success": False, "message": "Invalid or expired OTP"},
                status=400
            )
            
    except Exception as error:
        print(f"Error verifying OTP: {error}")
        return JsonResponse(
            {"success": False, "message": "Internal server error"},
            status=500
        )

@require_http_methods(["GET"])
def report_list(request):
    try:
        pending_list = Voucher.objects.filter(
            Q(status='R') | Q(status='B') | Q(status='V')
        )
        return JsonResponse(list(pending_list.values()), safe=False)
    except Exception as error:
        print(f'Error fetching pending list: {error}')
        return JsonResponse(
            {"error": 'Internal Server Error'},
            status=500
        )

@require_http_methods(["GET"])
def consolidate_list(request, voucher_type):
    try:
        status_choices = ['R', 'B', 'V', 'G', 'I', 'C', 'U']
        consolidate = Voucher.objects.filter(
            voucherType=voucher_type,
            status__in=status_choices
        )
        return JsonResponse(list(consolidate.values()), safe=False)
    except Exception as error:
        print(f'Error fetching consolidate list: {error}')
        return JsonResponse(
            {"error": 'Internal Server Error'},
            status=500
        )

@require_http_methods(["GET"])
def consolidate_voucher_reports(request, voucher_type):
    try:
        filters = Q(voucherType=voucher_type)
        
        # Get query parameters
        branch = request.GET.get('Branch')
        concern = request.GET.get('concern')
        status = request.GET.get('status')
        location = request.GET.get('location')
        division = request.GET.get('division')

        # Status mapping
        status_mapping = {
            'Redeemed': 'R',
            'Billed': 'B',
            'Verified': 'V',
            'IAChecked': 'I',
            'Approved': 'C',
            'fileGenerated': 'G',
            'Completed': 'U'
        }

        if voucher_type == "IV":
            if concern:
                filters &= Q(concern=concern)
            if branch:
                filters &= Q(Branch=branch)
        elif voucher_type == "GV":
            if concern:
                filters &= Q(concern=concern)
            if location:
                filters &= Q(Branch=location)
            if division:
                filters &= Q(division=division)

        if status:
            actual_status = status_mapping.get(status)
            if actual_status:
                filters &= Q(status=actual_status)

        report_details = Voucher.objects.filter(filters)
        
        if not report_details.exists():
            return JsonResponse({"message": "No records found"}, status=400)
            
        return JsonResponse(list(report_details.values()), safe=False)
        
    except Exception as error:
        print(f"Error retrieving report details: {error}")
        return JsonResponse(
            {"error": "An error occurred while retrieving the report details."},
            status=500
        )

@require_http_methods(["GET"])
def get_gv_concerns(request):
    try:
        db_concerns = DivisionMaster.objects.all()
        
        # Use set comprehension to remove duplicates
        concerns = list({
            'value': concern.Cocern,
            'label': concern.Cocern
        } for concern in db_concerns)
        
        branch_locations = list({
            'value': concern.Branch_Location,
            'label': concern.Branch_Location
        } for concern in db_concerns)
        
        divisions = list({
            'value': concern.Division,
            'label': concern.Division
        } for concern in db_concerns)

        return JsonResponse({
            'Concern': concerns,
            'Branch_Location': branch_locations,
            'division': divisions
        })
        
    except Exception as error:
        return JsonResponse({"error": str(error)}, status=500)

@require_http_methods(["GET"])
def approval_list(request):
    try:
        pending_list = Voucher.objects.filter(status='I').values('concern').annotate(
            vocidCount=Count('VocId'),
            totalAmount=Sum('amount'),
            lastVerifiedDate=Max('Verified_Date'),
            invoiceNumbers=F('bill_no')  # Note: GROUP_CONCAT equivalent might need custom implementation
        )
        
        return JsonResponse(list(pending_list), safe=False)
    except Exception as error:
        print(f'Error fetching pending list: {error}')
        return JsonResponse({"error": 'Internal Server Error'}, status=500)

# Store OTP data (in production, use cache or database)
concerns = {}

@csrf_exempt
@require_http_methods(["POST"])
def generate_approval_otp(request):
    try:
        data = json.loads(request.body)
        concern = data.get('concern')
        total_amount = data.get('totalAmount')
        session_id = data.get('sessionId')
        
        otp = str(math.floor(100000 + random.random() * 900000))
        concerns[session_id] = {
            'otp': otp,
            'timestamp': timezone.now().timestamp()
        }
        
        director_approval = ConcernBranchMaster.objects.first()
        message_text = f"Dear Sir, Total Payment for {total_amount}-{concern} concern. Use this code {otp} for payment approval. By SPCTXL"
        
        sms_data = {
            "customerId": settings.SMS_CUSTOMER_ID,
            "destinationAddress": director_approval.Directorphonenumber,
            "message": message_text,
            "sourceAddress": "SPCTXL",
            "messageType": "SERVICE_IMPLICIT",
            "dltTemplateId": "1007734047292136430",
            "entityId": "1701158071847889480",
            "otp": True,
            "metaData": {}
        }
        
        response = requests.post(
            'https://iqsms.airtel.in/api/v1/send-sms',
            json=sms_data,
            auth=(settings.SMS_USERNAME, settings.SMS_PASSWORD),
            headers={'Content-Type': 'application/json'}
        )
        
        return JsonResponse({'message': 'OTP sent successfully'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def verify_approval_otp(request):
    try:
        data = json.loads(request.body)
        session_id = data.get('sessionid')
        otp = data.get('otp')
        concern = data.get('concern')
        
        session = concerns.get(session_id)
        current_time = timezone.now().timestamp()
        
        if (session and 
            session['otp'] == otp and 
            current_time - session['timestamp'] < 300000):  # 5 minutes
            
            formatted_date = timezone.now().astimezone(
                pytz.timezone('Asia/Kolkata')
            ).strftime('%Y-%m-%d %H:%M:%S')
            
            updated = Voucher.objects.filter(
                concern=concern,
                status="I"
            ).update(
                status='C',
                Ed_Approved_date=formatted_date
            )
            
            if updated > 0:
                return JsonResponse({
                    'success': True,
                    'message': 'verified successfully'
                })
            
        return JsonResponse({
            'success': False,
            'message': 'Invalid or expired OTP'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Internal server error',
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def verify_record(request):
    try:
        data = json.loads(request.body)
        payment_voc = data.get('paymentVoc', [])
        
        if not payment_voc:
            return JsonResponse({'error': 'ID is required'}, status=400)
        
        now = timezone.now().astimezone(pytz.timezone('Asia/Kolkata'))
        formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
        formatted_date_ddmm = now.strftime('%d%m')
        
        processed_data = []
        
        for voc_id in payment_voc:
            voucher = Voucher.objects.select_related(
                'BranchData'
            ).filter(
                VocId=voc_id,
                status='C'
            ).first()
            
            if not voucher:
                continue
                
            branch_name = voucher.Branch
            if 'TCS' not in branch_name and voucher.voucherType == 'GV':
                branch_name = f'SKTM-{branch_name}'
            
            branch = ConcernBranchMaster.objects.filter(Branchname=branch_name).first()
            if not branch:
                continue
                
            sanitized_voc_id = ''.join(c for c in voc_id if c.isalnum())
            branch_id_voc_id = f'{branch.Branchid}-{sanitized_voc_id}'
            
            data_row = [
                'N', '', branch.Bankaccountnumber, str(voucher.amount),
                branch.Bankaccname[:20], '', '', '', '', '', '', '', '',
                branch_id_voc_id, '', '', '', '', '', '', '', '',
                now.strftime('%d/%m/%Y'), '', branch.Bankifsc,
                branch.Bankname, branch.Branchname, 'payment.ktm@scmts.net'
            ]
            
            processed_data.append(','.join(data_row))
            
        if not processed_data:
            return JsonResponse({'error': 'No valid records found to process'}, status=404)
            
        base_name = f'SPACETEX_SPA311_SPA311{formatted_date_ddmm}'
        unique_id = generate_unique_s3_id(base_name)
        file_name = unique_id.replace('/', '-')
        file_content = '\n'.join(processed_data)
        
        # Upload to S3
        s3_client = boto3.client('s3')
        s3_client.put_object(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            Key=file_name,
            Body=file_content,
            ContentType='text/plain'
        )
        
        # Update voucher status
        Voucher.objects.filter(
            VocId__in=payment_voc,
            status='C'
        ).update(
            status='G',
            payment_date=formatted_date
        )
        
        response = HttpResponse(
            file_content,
            content_type='text/plain'
        )
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response
        
    except Exception as e:
        error_message = str(e)
        if 'AllAccessDisabled' in error_message:
            return JsonResponse({
                'error': 'Access to S3 bucket is disabled. Please check your Connections.'
            }, status=403)
        elif 'NoSuchBucket' in error_message:
            return JsonResponse({
                'error': 'S3 bucket not found. Please check your bucket configuration.'
            }, status=404)
        return JsonResponse({'error': 'Internal Server Error'}, status=500)

def generate_unique_s3_id(base_name):
    try:
        s3_client = boto3.client('s3')
        s3_client.head_bucket(Bucket=settings.AWS_S3_BUCKET_NAME)
        
        response = s3_client.list_objects_v2(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            Prefix=base_name
        )
        
        max_number = 99
        if 'Contents' in response:
            for obj in response['Contents']:
                if match := obj['Key'].split('.')[-1].isdigit():
                    file_number = int(match)
                    max_number = max(max_number, file_number)
        
        new_number = str(max_number + 1).zfill(3)
        return f'{base_name}.{new_number}'
        
    except Exception as e:
        if e.response['Error']['Code'] in ['AllAccessDisabled', 'NoSuchBucket']:
            raise Exception(f"S3 bucket error: {e.response['Error']['Code']}")
        raise

@require_http_methods(["GET"])
def get_full_details(request, voucher_type):
    try:
        voucher_details = Voucher.objects.filter(voucherType=voucher_type)
        return JsonResponse(list(voucher_details.values()), safe=False)
    except Exception as e:
        return JsonResponse({'error': 'Internal Server Error'}, status=500)

@require_http_methods(["GET"])
def get_payment_file_generator(request, voucher_type):
    try:
        if voucher_type == "IV":
            payment_details = Voucher.objects.filter(
                status="C",
                voucherType=voucher_type
            ).select_related('branchDetails')
        else:  # voucher_type == "GV"
            payment_details = Voucher.objects.filter(
                status="C",
                voucherType=voucher_type
            ).select_related('branchDetails1')
            
        data = []
        for detail in payment_details:
            branch_data = detail.branchDetails if voucher_type == "IV" else detail.branchDetails1
            data.append({
                'id': detail.id,
                'VocId': detail.VocId,
                'amount': detail.amount,
                'branch': {
                    'Branchname': branch_data.Branchname,
                    'Bankaccname': branch_data.Bankaccname,
                    'Bankaccountnumber': branch_data.Bankaccountnumber,
                    'Bankbranch': branch_data.Bankbranch,
                    'Bankname': branch_data.Bankname,
                    'Bankifsc': branch_data.Bankifsc,
                    'Branchaddress': branch_data.Branchaddress,
                    'Branchcity': branch_data.Branchcity,
                }
            })
            
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)

@csrf_exempt
def create_voucher(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    data = json.loads(request.body)
    try:
        with transaction.atomic():
            branch_code = data['decodedBranch'].split('-')[0]
            
            if data['voucherType'] == 'GV':
                last_gv = Voucher.objects.filter(
                    voucher_type='GV',
                    voc_id__startswith=f"{branch_code}2425{data['decodedBranch'].split('-')[1]}GV"
                ).order_by('-voc_id').first()

                if last_gv:
                    next_number = int(last_gv.voc_id[-2:]) + 1
                else:
                    next_number = 53

                voc_id = f"{branch_code}2425{data['decodedBranch'].split('-')[1]}GV{str(next_number).zfill(2)}"

            elif data['voucherType'] == 'IV':
                last_iv = Voucher.objects.filter(
                    voucher_type='IV',
                    voc_id__startswith=f"{branch_code}2425AG"
                ).order_by('-voc_id').first()

                if last_iv:
                    next_number = int(last_iv.voc_id[-5:]) + 1
                else:
                    next_number = 227

                voc_id = f"{branch_code}2425AG{str(next_number).zfill(5)}"

                customer = CustomerMaster.objects.filter(mobile_no=data['mobileNo']).first()
                if not customer:
                    customer = CustomerMaster.objects.create(
                        customer_name=data['customerName'],
                        mobile_no=data['mobileNo'],
                        door_no=data['doorNo'],
                        street=data['street'],
                        pincode=data['pincode'],
                        area=data['area'],
                        taluk=data['taluk'],
                        city=data['city'],
                        state=data['state'],
                        customer_title='Mr',
                        purchase_with_sktm='yes',
                        status='V'
                    )

            voucher_data = {
                'voc_id': voc_id,
                'company_name': data['companyName'],
                'amount': data['amount'],
                'issue_date': data['issueDate'],
                'valid_date': data['validDate'],
                'voucher_type': data['voucherType'],
                'creation_utr_no': data['utrNo'],
                'branch': data['decodedBranch'],
                'concern': data['decodedConcern']
            }

            if data['voucherType'] == 'IV':
                voucher_data['customer'] = data['customerName']
                voucher_data['mobile'] = data['mobileNo']

            voucher = Voucher.objects.create(**voucher_data)

            return JsonResponse({
                'message': 'Voucher created successfully',
                'voucher': voucher_data,
                'customer': customer.id if data['voucherType'] == 'IV' else None
            }, status=201)

    except Exception as e:
        return JsonResponse({'message': 'Error creating voucher', 'error': str(e)}, status=500)

@csrf_exempt
def offline_gv_insert(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        voucher = Voucher.objects.create(
            voc_id=data['VocId'],
            voucher_type=data['voucherType'],
            company_name=data['companyname'],
            customer=data['customer'],
            mobile=data['Mobile'],
            amount=data['amount'],
            issue_date=data['issue_date'],
            valid_date=data['valid_date'],
            status='P'
        )
        return JsonResponse({"id": voucher.voc_id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def pending_list(request):
    try:
        pending_list = list(Voucher.objects.all().values())
        return JsonResponse(pending_list, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def update_utr(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        utr, created = UTRVoucher.objects.update_or_create(
            utr_no=data['utrNo'],
            defaults={
                'company_name': data['companyName'],
                'utr_date': data['utrDate'],
                'amount': data['amount']
            }
        )
        return JsonResponse({
            'message': 'UTR updated successfully',
            'utr': {
                'id': utr.id,
                'company_name': utr.company_name,
                'utr_no': utr.utr_no,
                'utr_date': utr.utr_date,
                'amount': str(utr.amount)
            }
        })
    except Exception as e:
        return JsonResponse({'message': 'Error updating UTR', 'error': str(e)}, status=500)

def valid_utr(request):
    utr_no = request.GET.get('utrNo')
    if not utr_no:
        return JsonResponse({'error': 'UTR number is required'}, status=400)

    try:
        utr_record = UTRVoucher.objects.filter(utr_no=utr_no).first()
        if not utr_record:
            return JsonResponse({'isValid': False, 'message': 'UTR number not found'}, status=404)

        total_voucher_amount = Voucher.objects.filter(
            creation_utr_no=utr_no
        ).aggregate(total=Sum('amount'))['total'] or 0

        remaining_amount = float(utr_record.amount) - float(total_voucher_amount)

        if remaining_amount <= 0:
            return JsonResponse({'isValid': False, 'message': 'UTR fully utilized', 'remainingAmount': 0}, status=400)

        return JsonResponse({'isValid': True, 'remainingAmount': remaining_amount})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def utr_detail(request):
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    u.id, 
                    u.company_name, 
                    u.utr_no, 
                    u.utr_date, 
                    u.amount, 
                    u.amount - COALESCE(SUM(v.amount), 0) AS remaining_amount 
                FROM 
                    Service_utr AS u
                LEFT JOIN 
                    ONLINE_voucherdata AS v ON u.utr_no = v.creation_utr_no
                GROUP BY 
                    u.id 
                HAVING 
                    remaining_amount > 0
            """)
            columns = [col[0] for col in cursor.description]
            utr_details = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return JsonResponse(utr_details, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def pending_utr_list(request):
    try:
        pending_list = UTRVoucher.objects.all()
        return JsonResponse(list(pending_list.values()), safe=False)
    except Exception as error:
        print('Error fetching pending list:', str(error))
        return JsonResponse({'error': 'Internal Server Error'}, status=500)

def utr_detail(request, utr_no):
    try:
        if not utr_no:
            return JsonResponse({'error': 'Missing required parameter: utr_no'}, status=400)

        pending_item = UTRVoucher.objects.filter(utr_no=utr_no).first()
        
        # Debug logging
        print('Requested UTR:', utr_no)
        print('Found UTR:', pending_item.utr_no if pending_item else None)

        if not pending_item:
            return JsonResponse({
                'error': 'UTR not found',
                'requestedUTR': utr_no
            }, status=404)

        return JsonResponse(pending_item.to_dict())
    except Exception as error:
        print('Error fetching UTR by utr_no:', str(error))
        return JsonResponse({'error': 'Internal Server Error'}, status=500)

@csrf_exempt
def approve_utr(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        id = data.get('id')
        
        if not id:
            return JsonResponse({'error': 'Missing ID'}, status=400)

        Voucher.objects.filter(id=id).update(status='Y')
        print(f'Record with ID {id} approved successfully')
        return JsonResponse({'message': 'Record approved successfully'})
    except Exception as error:
        print('Error updating record:', str(error))
        return JsonResponse({'error': 'Internal Server Error'}, status=500)

@csrf_exempt
def print_complete(request, id):
    if request.method != 'PUT':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        status = data.get('status')

        if not status:
            return JsonResponse({'error': 'Missing required parameters'}, status=400)

        updated = Voucher.objects.filter(voc_id=id).update(
            status=status,
            print_date=timezone.now()
        )

        if not updated:
            return JsonResponse({'error': 'Voucher not found'}, status=404)

        updated_voucher = Voucher.objects.get(voc_id=id)
        return JsonResponse({
            'message': 'Voucher status updated successfully',
            'updatedVoucher': updated_voucher.to_dict()
        })
    except Exception as error:
        print('Error updating voucher status:', str(error))
        return JsonResponse({
            'error': 'Internal Server Error',
            'message': str(error)
        }, status=500)

@csrf_exempt
def utr_check(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        id = data.get('id')
        
        if not id:
            return JsonResponse({'error': 'Missing ID'}, status=400)

        UTRVoucher.objects.filter(id=id).update(status='A')
        print(f'Record with ID {id} approved successfully')
        return JsonResponse({'message': 'Record approved successfully'})
    except Exception as error:
        print('Error updating record:', str(error))
        return JsonResponse({'error': 'Internal Server Error'}, status=500)

def print_approval(request):
    try:
        utr_no = request.GET.get('utrNo')
        query = {'status': 'W'}
        
        if utr_no:
            query['creation_utr_no'] = utr_no

        pending_list = Voucher.objects.filter(**query)
        
        utr_amount = None
        if utr_no:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT amount FROM Service.UTRVOUCHER
                    WHERE utrNo = %s
                """, [utr_no])
                row = cursor.fetchone()
                if row:
                    utr_amount = row[0]

        return JsonResponse({
            'pendingList': list(pending_list.values()),
            'utrAmount': utr_amount
        })
    except Exception as error:
        print('Error fetching pending list:', str(error))
        return JsonResponse({'error': 'Internal Server Error'}, status=500)

def generate_otp():
    return str(random.randint(100000, 999999))

@csrf_exempt
def send_otp(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        user_type = data.get('userType')
        concern = data.get('concern')
        branch = data.get('branch')

        print('Received request:', {'userType': user_type, 'concern': concern, 'branch': branch})

        # Check authorization
        user_role = UserRoleMaster.objects.filter(
            role_name=user_type,
            voucher='Y'
        ).first()

        if not user_role:
            return JsonResponse({
                'success': False,
                'message': 'User is not authorized to access voucher functionality'
            }, status=403)

        where_clause = {'user_type': user_type, 'concern': concern}
        mobile_no = None
        branch_value = None

        branch_required_types = ['Branch_Manager', 'Branch_EDP', 'Branch_IA']
        ho_types = ['Admin', 'Executive_Director', 'A/C_Manager', 'A/C_Executive', 'HO_IA']

        if user_type not in branch_required_types and user_type not in ho_types:
            return JsonResponse({
                'success': False,
                'message': 'Invalid user type'
            }, status=400)

        # Handle branch specific users
        if user_type in branch_required_types:
            if not branch:
                return JsonResponse({
                    'success': False,
                    'message': 'Branch is required for this user type'
                }, status=400)

            where_clause['branch'] = branch
            branch_value = branch

            concern_master = ConcernBranchMaster.objects.filter(
                concern=concern,
                branch_name=branch
            ).first()

            if not concern_master:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid branch or concern'
                }, status=400)

            mobile_map = {
                'Branch_Manager': concern_master.branch_manager,
                'Branch_EDP': concern_master.branch_edp,
                'Branch_IA': concern_master.branch_ia
            }
            mobile_no = mobile_map.get(user_type)

        # Handle HO users
        elif user_type in ho_types:
            concern_master = ConcernBranchMaster.objects.filter(concern=concern).first()

            if not concern_master:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid concern for Admin'
                }, status=400)

            branch_value = 'HO'
            where_clause['branch'] = branch_value

            mobile_map = {
                'Admin': concern_master.it_head,
                'Executive_Director': concern_master.director_phone_number,
                'A/C_Manager': concern_master.acc_manager_phone,
                'A/C_Executive': concern_master.acc_executive,
                'HO_IA': concern_master.ia_mobile
            }
            mobile_no = mobile_map.get(user_type)

        if not mobile_no:
            return JsonResponse({
                'success': False,
                'message': 'Unable to retrieve mobile number'
            }, status=400)

        print('Retrieved mobile number:', mobile_no)

        # Generate OTP
        otp = generate_otp()
        print('Generated OTP:', otp)

        # Prepare WhatsApp message
        whatsapp_message = {
            'templateId': '01jd44t9znn6ev1h54dy5kfyx1',
            'to': f'+91{mobile_no}',
            'from': settings.WHATSAPP_SENDER,
            'message': {
                'text': f'Dear User, Kindly Update Your(Concern:{concern} | Branch:{branch_value} | Type:{user_type}) Login OTP:{otp}.',
                'variables': [concern, branch_value, user_type, otp],
                'payload': ['payload1', 'payload2', 'payload3', 'payload4']
            }
        }

        # Send WhatsApp message
        send_whatsapp_message(whatsapp_message)

        # Update or create user record
        ChitsUser.objects.update_or_create(
            defaults={
                'otp': otp,
                'mobile_no': mobile_no,
                'name': 'Voucher_Portal',
                'email': '',
                'city': '',
                'pincode': '',
            },
            **where_clause
        )

        return JsonResponse({'success': True, 'message': 'OTP sent successfully'})

    except Exception as error:
        print('Error in OTP send process:', str(error))
        return JsonResponse({
            'success': False,
            'message': 'Failed to send OTP',
            'error': str(error)
        }, status=500)

def send_whatsapp_message(message):
    try:
        response = requests.post(
            'https://iqwhatsapp.airtel.in/gateway/airtel-xchange/basic/whatsapp-manager/v1/template/send',
            json=message,
            auth=(settings.WHATSAPP_USER, settings.WHATSAPP_PASS),
            headers={'Content-Type': 'application/json'}
        )
        print("WhatsApp Message Response:", response.json())
        return response.json()
    except Exception as error:
        print("WhatsApp Message Error:", str(error))
        raise
    
    # S3 client setup
s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)

def get_kolkata_time():
    """Helper function to get current time in Kolkata timezone"""
    tz = pytz.timezone('Asia/Kolkata')
    return timezone.now().astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')

@csrf_exempt
def vc_login(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        user_type = data.get('userType')
        concern = data.get('concern')
        otp = data.get('OTP')
        branch = data.get('branch')
        ip_details = data.get('ipDetails')
        ip_city = data.get('ipcity')

        # Debug logging
        print('Login attempt:', {
            'userType': user_type,
            'concern': concern,
            'OTP': otp,
            'branch': branch
        })

        # Validate required fields
        if not all([user_type, concern, otp]):
            return JsonResponse({
                'success': False,
                'message': 'Missing required fields'
            }, status=400)

        # Convert OTP to string
        provided_otp = str(otp)

        # Validate branch requirement
        branch_required_types = ['Branch_Manager', 'Branch_EDP', 'Branch_IA']
        if user_type in branch_required_types and not branch:
            return JsonResponse({
                'success': False,
                'message': 'Branch is required for this user type'
            }, status=400)

        # Build query for user lookup
        query = {
            'user_type': user_type,
            'concern': concern,
            'branch': branch if user_type in branch_required_types else 'HO'
        }

        # Find user
        try:
            user = ChitsUser.objects.get(**query)
        except ChitsUser.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invalid user credentials. Please check your concern, branch (if applicable), and user type.'
            }, status=401)

        # Debug log for user lookup
        print('User found:', {
            'userType': user.user_type,
            'concern': user.concern,
            'branch': user.branch,
            'storedOTP': user.otp,
            'providedOTP': provided_otp
        })

        # Validate OTP
        if user.otp != provided_otp:
            return JsonResponse({
                'success': False,
                'message': 'Invalid OTP. Please try again.'
            }, status=401)

        # Handle login time updates
        is_login_time_updated = False
        if user.status not in ['P', 'D']:
            login_time = get_kolkata_time()
            try:
                login_times = json.loads(user.login_time) if user.login_time else []
                if not isinstance(login_times, list):
                    login_times = []
            except json.JSONDecodeError:
                login_times = []

            login_times.append({'logintime': login_time})
            user.login_time = json.dumps(login_times)
            is_login_time_updated = True

        # Update user information
        user.otp = ''  # Clear OTP after successful login
        user.is_active = is_login_time_updated
        user.ip_address = ip_details
        user.location = ip_city
        user.save()

        # Generate JWT token
        token = jwt.encode(
            {
                'mobile_no': user.mobile_no,
                'user_type': user.user_type
            },
            settings.AUTH_SECRET,
            algorithm='HS256'
        )

        # Handle response based on status
        status_responses = {
            'A': {
                'success': True,
                'redirectTo': '/dashboard',
                'Status': user.status,
                'token': token,
                'userType': user.user_type,
                'MobileNo': user.mobile_no
            },
            'P': {
                'success': False,
                'error': 'Your approval is still pending',
                'Status': user.status
            },
            'D': {
                'success': False,
                'error': 'Your account has been deactivated. Please contact support.',
                'Status': user.status
            }
        }

        response_data = status_responses.get(
            user.status,
            {
                'success': False,
                'error': 'Invalid account status. Please contact support.',
                'Status': user.status
            }
        )

        return JsonResponse(response_data)

    except Exception as error:
        print('Error during login:', str(error))
        return JsonResponse({
            'success': False,
            'error': 'Internal Server Error. Please try again later.'
        }, status=500)

@csrf_exempt
def c_logout(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        mobile_no = data.get('mobileNo')

        if not mobile_no:
            return JsonResponse({'error': 'Mobile number is required'}, status=400)

        try:
            user = ChitsUser.objects.get(mobile_no=mobile_no)
        except ChitsUser.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invalid mobile number'
            }, status=401)

        # Update logout time if status allows
        if user.status not in ['P', 'D']:
            logout_time = get_kolkata_time()
            try:
                logout_times = json.loads(user.logout_time) if user.logout_time else []
                logout_times.append({'logoutTime': logout_time})
                user.logout_time = json.dumps(logout_times)
            except json.JSONDecodeError:
                user.logout_time = json.dumps([{'logoutTime': logout_time}])

        user.is_active = False
        user.save()

        return JsonResponse({'success': True, 'message': 'Logout successful'})

    except Exception as error:
        print('Error during logout:', str(error))
        return JsonResponse({'error': 'Internal Server Error'}, status=500)

def s3_download(request):
    try:
        file_name = request.GET.get('fileName')
        bucket_name = request.GET.get('bucketName')

        if not all([file_name, bucket_name]):
            return JsonResponse({
                'error': 'Missing required parameters'
            }, status=400)

        # Get object from S3
        s3_object = s3_client.get_object(
            Bucket=bucket_name,
            Key=file_name
        )

        # Create response with appropriate headers
        response = HttpResponse(s3_object['Body'].read())
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        
        return response

    except Exception as error:
        print('Error downloading from S3:', str(error))
        return JsonResponse({
            'error': 'Failed to download file from S3'
        }, status=500)

def s3_list_files(request):
    try:
        prefix = request.GET.get('prefix')
        bucket_name = request.GET.get('bucketName')

        if not all([prefix, bucket_name]):
            return JsonResponse({
                'error': 'Missing required parameters'
            }, status=400)

        # List objects from S3
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix
        )

        # Filter files by prefix
        files = [
            obj['Key'] for obj in response.get('Contents', [])
            if obj['Key'].startswith(prefix)
        ]

        return JsonResponse({'files': files})

    except Exception as error:
        print('Error listing S3 files:', str(error))
        return JsonResponse({
            'error': 'Failed to list files from S3',
            'details': str(error)
        }, status=500)
