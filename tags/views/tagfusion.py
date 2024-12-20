from django.http import JsonResponse
from django.shortcuts import render,redirect

# Create your views here.
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import connections
import json
from collections import Counter
from tags.models import CardInfo,CardKV
from django.core.cache import cache


TAG_VERSION = 'tag1.0'
CACHE_KEYS_LIST = 'all_cache_keys'

@csrf_exempt
@require_POST
def create_info(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        bio = request.POST.get('bio')
        address = request.POST.get('address')
        link = request.POST.get('link')
        profile_image = request.FILES.get('profile_image')
        if username and address and len(CardInfo.objects.filter(address = address)) == 0 : # 简单验证必填字段
            card_info = CardInfo(
                username=username,
                bio=bio,
                address=address,
                link=link,
                profile_image=profile_image
            )
            card_info.save()
            result_content = {
                "code":0,
                "message":"Created successfully"
            }
            return JsonResponse(result_content)
        else:
            result_content = {
                "code":1,
                "message":"Card has been created"
            }
            return JsonResponse(result_content)

@csrf_exempt
def get_info(request):
    if request.method == 'GET':
        address = request.GET.get('address')
        my_tags = []
        verify_tags = []
        json_list_tags = []

        with connections['default'].cursor() as cursor:

            cursor.execute("SELECT username,bio,profile_image,link FROM tags_cardinfo WHERE address = %s", [address])
            user_row = cursor.fetchone()

            if user_row:
                username = user_row[0],
                bio = user_row[1],
                profile_image = user_row[2],
                link = user_row[3],
            else:
                result_content = 		{
                    "code":1,
                    "message":"Card not created"
                }

                return JsonResponse(result_content)

            # select my tags
            cursor.execute("""
                SELECT from_address,tag_version,tag_type,category_name,tag_name
                FROM transaction_data
                WHERE from_address = %s
                 and from_address = to_address
            """, [address])
            tag_transactions = cursor.fetchall()
            for row in tag_transactions:
                tag_version = row[1]
                type_ = row[2]
                category_name = row[3]
                tag_name = row[4]
                if tag_version != TAG_VERSION or type_ != 'addTag':
                    continue
                category_data = cache.get(category_name)
                if(category_data is None or tag_name not in category_data.get(category_name)):
                    continue
                my_tags.append(tag_name)
            my_tags = list(set(my_tags))
            # verify tags
            cursor.execute("""
                SELECT to_address,tag_version,tag_type,tag_name
                FROM transaction_data
                WHERE to_address = %s
                 and from_address != to_address
            """, [address])
            verify_transaction = cursor.fetchall()
            for row in verify_transaction:
                tag_version = row[1]
                type_ = row[2]
                tag_name = row[3]

                if tag_version != TAG_VERSION or type_ != 'verifyTag':
                    continue

                if tag_name in my_tags:
                    verify_tags.append(tag_name)
            counter = Counter(verify_tags)

            for tag_name, verify_num in counter.items():
                status = verify_num >= 1
                json_list_tags.append({
                    "tag_name": str(tag_name),
                    "status": status,
                    "verify_num": verify_num
                })
            for tag_name in list(set(my_tags) - set(verify_tags)) :
                json_list_tags.append({
                    "tag_name": str(tag_name),
                    "status": False,
                    "verify_num": 0
                })
            result_content ={
                "code":0,
                "info":
                    {
                        "address":address,
                        "username":username,
                        "bio":bio,
                        "profile_image":profile_image,
                        "link":link,
                        "tags":json_list_tags
                    }
                }
            return JsonResponse(result_content)



@csrf_exempt
def get_cards(request):
    keys_list = cache.get(CACHE_KEYS_LIST, [])
    tags_list = []
    for key in keys_list:
        value = cache.get(key)

        if value is not None:
            tags_list.append({"category_name":key,"tags" :value.get(key)} )

    result_json = {
        "code":0,
        "data":tags_list
    }

    return JsonResponse(result_json)











