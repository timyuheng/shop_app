import uuid

from django.core.cache import cache
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template import loader

from django.urls import reverse
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView

from App.models import MainWheel, MainNav, MainMustBuy, MainShop, MainShow, FoodType, Goods, UserModel

from App.viewhelper import get_user, send_mail_to

ALL_TYPE = '0'
TOTAL_RULE = '0'
PRICE_UP = '1'
PRICE_DOWN = '2'


def home(request):
    ip = request.META.get('REMOTE_ADDR')
    result = cache.get(ip + 'home')

    if result:
        # print('从缓存中加载')
        return HttpResponse(result)

    wheels = MainWheel.objects.all()

    navs = MainNav.objects.all()

    mustbuys = MainMustBuy.objects.all()

    shops = MainShop.objects.all()

    shop0 = shops[0:1]

    shop1_3 = shops[1:3]

    shop3_7 = shops[3:7]

    shop7_11 = shops[7:11]

    mainshows = MainShow.objects.all()

    data = {
        "title": "首页",
        "wheels": wheels,
        "navs": navs,
        "mustbuys": mustbuys,
        "shop0": shop0,
        "shop1_3": shop1_3,
        "shop3_7": shop3_7,
        "shop7_11": shop7_11,
        "mainshows": mainshows
    }

    # 添加到缓存
    temp = loader.get_template('home/home.html')
    # 渲染
    result = temp.render(context=data)
    # print(result)
    cache.set(ip + 'home', result)
    return HttpResponse(result)


def market(request):
    return redirect(reverse("axf:marketWithParams", kwargs={"typeid": "104749", "cid": "0", "sort_rule": "0"}))


@cache_page(120)
def marketWithParams(request, typeid, cid, sort_rule):
    foodtypes = FoodType.objects.all()

    if cid == ALL_TYPE:
        goodsList = Goods.objects.filter(categoryid=typeid)
    else:
        goodsList = Goods.objects.filter(categoryid=typeid).filter(childcid=cid)

    """
    全部分类:0#进口水果:110#国产水果:120
    全部分类   进口水果  国产水果
    数字是它名字的标识
    
    """

    foodtype = FoodType.objects.get(typeid=typeid)

    childtypenames = foodtype.childtypenames

    childtypename_list = childtypenames.split('#')

    child_type_name_list = []
    for child_type_name in childtypename_list:
        child_type_name_list.append(child_type_name.split(':'))
    # print(child_type_name_list)

    """
    综合排序
        对筛选结果进行一个order_by
        1.服务器能接收对应的排序字段
        2.客户端发送排序字段
        3.两端有一个约定
            0：综合排序
            1：价格升序
            2：价格降序
            3：....
        
    """
    if sort_rule == TOTAL_RULE:
        pass
    elif sort_rule == PRICE_UP:
        goodsList = goodsList.order_by("price")
    elif sort_rule == PRICE_DOWN:
        goodsList = goodsList.order_by("-price")

    data = {
        "title": "闪购",
        "foodtypes": foodtypes,
        "goodsList": goodsList,
        "typeid": int(typeid),
        "child_type_name_list": child_type_name_list,
        "cid": cid,
        "sort_rule": sort_rule,
    }

    return render(request, 'market/market.html', context=data)


def cart(request):
    data = {
        "title": "购物车"
    }

    return render(request, 'cart/cart.html', context=data)


def mine(request):
    user_id = request.session.get('user_id')

    data = {
        "title": "我的",
        "is_login": False,
    }
    if user_id:
        user = UserModel.objects.get(pk=user_id)
        data['is_login'] = True
        data['username'] = user.u_name
        data['icon'] = '/static/upload/' + user.u_icon.url

    return render(request, 'mine/mine.html', context=data)


def add_to_cart(request):
    goodsid = request.GET.get('goodsid')
    return JsonResponse({'msg': 'ok', 'goodsid': goodsid})


class UserView(View):

    def get(self, request):
        return render(request, 'user/user_register.html')

    def post(self, request):
        u_username = request.POST.get('u_username')
        u_email = request.POST.get('u_email')
        u_password = request.POST.get('u_password')
        u_icon = request.FILES.get('u_icon')
        user = UserModel.objects.create(u_name=u_username, u_email=u_email, u_password=u_password, u_icon=u_icon)

        # 生成token  
        # uuid
        token = str(uuid.uuid4())

        cache.set(token, user.id, timeout=60 * 60 * 24)

        active_url = "http://localhost:8000/axf/active/?token=" + token

        send_mail_to(u_username, active_url, u_email)

        # request.session['user_id'] = user.id
        return redirect(reverse("axf:user_login"))


class UserLoginView(TemplateView):
    template_name = 'user/user_login.html'

    def get(self, request, *args, **kwargs):

        msg = request.session.get('login_msg')

        data = {}

        if msg:
            data['msg'] = msg
            del request.session['login_msg']
        return render(request, self.template_name, context=data)

    def post(self, request):
        username = request.POST.get('u_username')
        password = request.POST.get('u_password')

        user = get_user(username)
        if user:
            if user.check_password(password):
                # 用户名和密码都对,跳转个人中心
                if user.is_active:

                    request.session['user_id'] = user.id
                    return redirect(reverse('axf:mine'))
                else:
                    # 未激活
                    request.session['login_msg'] = '用户未激活'
                    return redirect(reverse('axf:user_login'))
            else:
                request.session['login_msg'] = '用户名或密码错误'
                return redirect(reverse("axf:user_login"))
        # 用户不存在
        request.session['login_msg'] = '用户不存在'
        return redirect(reverse('axf:user_login'))


def logout(request):
    request.session.flush()
    return redirect(reverse('axf:mine'))


def check_user(request):
    username = request.GET.get('username')

    user = get_user(username)

    data = {
        'msg': '<span style="color: green">用户名可用</span>'
    }
    if user:
        data['status'] = '900'
        data['msg'] = '<span style="color: red">用户名已存在</span>'
    else:
        data['status'] = '200'
    return JsonResponse(data)


def active(request):
    token = request.GET.get('token')

    user_id = cache.get(token)

    if user_id:
        cache.delete(token)
        user = UserModel.objects.get(pk=user_id)
        user.is_active = True
        user.save()
        return HttpResponse("激活成功")
    else:
        return HttpResponse("激活信息过期，请重新激活")