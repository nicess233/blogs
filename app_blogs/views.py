from django.shortcuts import render,redirect,HttpResponse,reverse

# Create your views here.
import os
import json
from django.db import transaction
from django.db.models import Count,Avg,Max,Min,F,Q
from django.http import JsonResponse
from bs4 import BeautifulSoup
from django.contrib import auth
from blogs import settings
from app_blogs.models import *
from utlis.code import check_code


def login(request):
    if request.method == 'GET':
        return render(request, 'login.html')

    user = request.POST.get('user')
    pwd = request.POST.get('pwd')
    code = request.POST.get('code')
    if code.upper() != request.session['random_code'].upper():
        return render(request,'login.html',{'msg':'验证码错误'})
    user = auth.authenticate(username=user,password=pwd)
    if user:
        auth.login(request,user)
        return redirect('/index/')


def logout(request):
    auth.logout(request)
    return redirect('/index/')

def index(request):
    article_list = Article.objects.all()
    return render(request,'index.html',locals())

def homesite(request,username,**kwargs):
    user = UserInfo.objects.filter(username=username).first()
    if not user:
        return render(request,'not_found.html')
    blog = user.blog
    if not kwargs:
        article_list = Article.objects.filter(user__username=username)
    else:
        condition = kwargs.get('condition')
        params = kwargs.get('params')

        if condition == 'category':
            article_list = Article.objects.filter(user__username=username,category__title=params)
        elif condition == 'tag':
            article_list = Article.objects.filter(user__username=username,tags__title=params)
        else:
            year,month = params.split('/')
            article_list = Article.objects.filter(user__username=username,create_time__year=year,create_time__month=month)
    if not article_list:
        return render(request,'not_found.html')
    return render(request,'homesite.html',locals())

def article_detail(request,username,article_id):
    user = UserInfo.objects.filter(username=username).first()
    blog = user.blog
    article_obj = Article.objects.filter(pk=article_id).first()
    comment_list = Comment.objects.filter(article_id=article_id)
    return render(request,'article_detail.html',locals())

def digg(request):
    is_up = json.loads(request.POST.get('is_up'))
    article_id = request.POST.get('article_id')
    user_id = request.user.pk
    response = {'state':True,'msg':None}

    obj = ArticleUpDown.objects.filter(user_id=user_id,article_id=article_id).first()
    if obj:
        response['state'] = False
        response['handled'] = obj.is_up
    else:
        with transaction.atomic(): #事物，如果在这个过程中遇到error就会回滚（将两个事件绑定在一起，例如转钱）
            new_obj = ArticleUpDown.objects.create(user_id=user_id,article_id=article_id,is_up=is_up)
            if is_up:
                Article.objects.filter(pk=article_id).update(up_count=F('up_count')+1)
            else:
                Article.objects.filter(pk=article_id).update(down_count=F('down_count')+1)

    return JsonResponse(response) #能够将数据发送给ajax,js不用反序列化

def comment(request):
    #获取数据
    user_id = request.user.pk
    article_id = request.POST.get('article_id')
    content = request.POST.get('content')
    pid = request.POST.get('pid')
    #生成评论对象
    with transaction.atomic():
        comment = Comment.objects.create(user_id=user_id,article_id=article_id,content=content,parent_comment_id=pid)
        Article.objects.filter(pk=article_id).update(comment_count=F('comment_count')+1)

    response = {'state':True}
    response['timer'] = comment.create_time.strftime('%Y-%m-%d %X')
    response['content'] = comment.content
    response['user'] = request.user.username

    return JsonResponse(response)

def backend(request):
    user = request.user
    article_list = Article.objects.filter(user=user)
    return render(request,'backend/backend.html',locals())

def add_article(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        user = request.user
        cate_pk = request.POST.get('cate')
        tags_pk_list = request.POST.getlist('tags')

        soup = BeautifulSoup(content,'html.parser')
        for tag in soup.find_all():
            if tag.name in ['script',]:
                tag.decompose()

        desc = soup.text[0:150]

        article_obj = Article.objects.create(title=title,content=str(soup),user=user,category_id=cate_pk,desc=desc)

        for tag_pk in tags_pk_list:
            Article2Tag.objects.create(article_id=article_obj.pk,tag_id=tag_pk)

        return redirect('/backend/')

    else:
        blog = request.user.blog
        cate_list = Category.objects.filter(blog=blog)
        tags = Tag.objects.filter(blog=blog)
        return render(request,'backend/add_article.html',locals())


def upload(request):
    obj = request.FILES.get('upload_img')
    name = obj.name
    path = os.path.join(settings.BASE_DIR,'static','upload',name)
    with open(path,'wb')as f:
        for line in obj:
            f.write(line)

    res = {
        'error':0,
        'url':'/static/upload/'+name
    }

    return HttpResponse(json.dumps(res))

def delete_article(request,article_id):
    article = Article.objects.filter(pk=article_id).first()
    article.delete()
    return redirect('/backend/')

def update_article(request,article_id):
    article = Article.objects.filter(pk=article_id).first()
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        user = request.user
        cate_pk = request.POST.get('cate')
        tags_pk_list = request.POST.getlist('tags')

        soup = BeautifulSoup(content,'html.parser')
        for tag in soup.find_all():
            if tag.name in ['script',]:
                tag.decompose()

        desc = soup.text[0:150]

        Article.objects.filter(pk=article_id).update(title=title,content=str(soup),user=user,category_id=cate_pk,desc=desc)

        Article2Tag.objects.filter(article_id=article_id).all().delete()
        for i in tags_pk_list:
            Article2Tag.objects.create(article_id=article_id,tag_id=i)
        return redirect('/backend/')

    else:
        blog = request.user.blog
        cate_list = Category.objects.filter(blog=blog)
        tags = Tag.objects.filter(blog=blog)
        cate_id = cate_list.filter(blog=blog,article__pk=article_id).values_list('pk').first()[0]
        tag_list = []
        tag_obj = tags.filter(article__pk=article_id).values_list('pk')
        for i in tag_obj:
            tag_list.append(i[0])

        return render(request,'backend/add_article.html',locals())

def code(request):
    img,random_code = check_code()
    request.session['random_code'] = random_code
    from io import BytesIO
    stream = BytesIO()
    img.save(stream,'png')
    return HttpResponse(stream.getvalue())
